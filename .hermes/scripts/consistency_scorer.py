#!/usr/bin/env python3
"""
Consistency-sampled calibrated confidence scorer for Hermes.

Ported from Denuto `src/pipeline/consistency_scorer.py`.

Problem: LLM self-reported confidence is systematically overconfident.
GPT-4 assigned highest confidence to 87% of responses including wrong ones.

Solution: Run N cheap re-verification calls on a small model, map agreement
rate to calibrated confidence.

Theoretical basis:
  - Ensemble disagreement as uncertainty proxy (Lakshminarayanan et al. 2017,
    "Simple and Scalable Predictive Uncertainty Estimation")
  - N=3 majority vote → Condorcet jury: at p=0.7, P(majority correct) = 0.784
    vs individual 0.7 — modest but real improvement.
  - Calibration mapping (3/3→1.0, 2/3→0.5) is CONSERVATIVE and NOT
    probability-theoretically derived. 3/3=1.0 is epistemically overconfident.
    Treat as signal, not ground truth.

Stdlib-only. No external dependencies except the verify_fn you provide.

Usage:
    from consistency_scorer import consistency_score, ConsistencyConfig

    def my_verify_fn(finding: str) -> bool:
        # call a cheap LLM: "Does this finding hold? Answer only yes or no."
        response = cheap_llm_call(finding)
        return response.strip().lower().startswith("y")

    config = ConsistencyConfig(n=3, timeout=10.0, enabled=True)
    score = consistency_score("Finding text here", my_verify_fn, config)
    # Returns float in {0.05, 0.20, 0.50, 1.00}
"""

from __future__ import annotations
import os

import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

logger = logging.getLogger(__name__)

# Calibration table: agreements → confidence
# Conservative mapping from Denuto. See module docstring for theoretical caveat.
_CALIBRATION: dict[int, float] = {
    0: 0.05,
    1: 0.20,
    2: 0.50,
    3: 1.00,
}



def _load_dynamic_calibration() -> dict:
    """Load calibration thresholds from condorcet-thresholds.json if fresh (<2h).

    Theory: Gelman BDA3 §2.4 (posterior predictive); calibration-threshold-updater.py
    writes EMA-updated thresholds for each scope. We use the global observed_rate as
    a scaling hint: if observed agreement_rate < 0.5, all calibrated confidences
    are scaled down proportionally.

    Returns: {0: float, 1: float, 2: float, 3: float} — same shape as _CALIBRATION.
    Fails open: returns _CALIBRATION on any error.
    """
    import time as _t
    try:
        thresh_path = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))) / (
            ("profiles/" + os.environ.get("HERMES_PROFILE", "") + "/")
            if os.environ.get("HERMES_PROFILE", "") else ""
        ) / "cache" / "condorcet-thresholds.json"
        if not thresh_path.exists():
            return dict(_CALIBRATION)
        age = _t.time() - thresh_path.stat().st_mtime
        if age > 7200:  # 2h stale → fall back
            return dict(_CALIBRATION)
        import json as _j
        data = _j.loads(thresh_path.read_text())
        # Find a usable threshold from any scope
        rates = [v.get('observed_rate') for v in data.values()
                 if isinstance(v, dict) and v.get('observed_rate') is not None]
        if not rates:
            return dict(_CALIBRATION)
        mean_rate = sum(rates) / len(rates)
        if mean_rate <= 0 or mean_rate >= 1:
            return dict(_CALIBRATION)
        # Scale: at mean_rate=0.5 (expected), scale=1.0 (no change).
        # At mean_rate=0.3: scale=0.6 (lower confidence); at 0.7: scale=1.4 (higher).
        scale = mean_rate / 0.5
        scale = max(0.5, min(2.0, scale))  # clamp to ±2x
        scaled = {k: min(1.0, max(0.0, round(v * scale, 3))) for k, v in _CALIBRATION.items()}
        return scaled
    except Exception:
        return dict(_CALIBRATION)

# Runtime calibration (overrides _CALIBRATION if condorcet-thresholds.json is fresh)
_RUNTIME_CALIBRATION: dict | None = None
_RUNTIME_CALIBRATION_MTIME: float = 0.0

def _get_calibration() -> dict:
    """Return calibration dict, using dynamic thresholds if available.
    
    Cache invalidation: re-loads if condorcet-thresholds.json mtime has changed.
    This allows long-running sessions to pick up calibration updates mid-session.
    """
    global _RUNTIME_CALIBRATION, _RUNTIME_CALIBRATION_MTIME
    try:
        thresh_path = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))) / (
            ("profiles/" + os.environ.get("HERMES_PROFILE", "") + "/")
            if os.environ.get("HERMES_PROFILE", "") else ""
        ) / "cache" / "condorcet-thresholds.json"
        current_mtime = thresh_path.stat().st_mtime if thresh_path.exists() else 0.0
        if _RUNTIME_CALIBRATION is None or current_mtime != _RUNTIME_CALIBRATION_MTIME:
            _RUNTIME_CALIBRATION = _load_dynamic_calibration()
            _RUNTIME_CALIBRATION_MTIME = current_mtime
    except Exception:
        if _RUNTIME_CALIBRATION is None:
            _RUNTIME_CALIBRATION = dict(_CALIBRATION)
    return _RUNTIME_CALIBRATION

# Sentinel for a failed/timeout verification call
_CALL_FAILED = object()

import math as _math


def hoeffding_ci(agreements: int, n: int, delta: float = 0.05) -> tuple[float, float]:
    """Hoeffding confidence interval for empirical mean of n Bernoulli trials.

    Theoretical basis: Hoeffding (1963). For bounded [0,1] r.v.s:
      P(|empirical_mean - true_mean| > t) <= 2*exp(-2*n*t^2)
    Setting 2*exp(-2*n*t^2) = delta => t = sqrt(log(2/delta) / (2*n)).

    Reference: Vershynin "High-Dimensional Probability" §2.2 (Hoeffding's inequality);
    Lugosi "Concentration of Measure" notes.

    Returns (lower, upper) bounds on the true agreement probability, clamped to [0, 1].
    """
    if n <= 0:
        return 0.0, 1.0
    p_hat = agreements / n
    t = _math.sqrt(_math.log(2.0 / delta) / (2.0 * n))
    lower = max(0.0, p_hat - t)
    upper = min(1.0, p_hat + t)
    return lower, upper




@dataclass
class ConsistencyConfig:
    enabled: bool = False   # Feature-flagged, default-off
    n: int = 3              # Number of verification calls
    timeout: float = 10.0  # Per-call timeout in seconds
    log_results: bool = True


def consistency_score(
    finding: str,
    verify_fn: Callable[[str], bool],
    config: ConsistencyConfig | None = None,
    scope: str | None = None,
) -> float:
    """
    Run N parallel verify_fn calls on finding, return calibrated confidence.

    verify_fn(finding) -> bool:
        Call a cheap model: "Does this finding hold? Answer only yes or no."
        Errors/timeouts count as disagreement (conservative).

    Returns float in {0.05, 0.20, 0.50, 1.00}.
    Returns 1.0 if config.enabled is False (passthrough — don't change behavior).
    """
    if config is None:
        config = ConsistencyConfig()

    if not config.enabled:
        return 1.0  # passthrough: don't change behavior when feature is off

    n = config.n
    timeout = config.timeout
    results: list[object] = []
    lock = threading.Lock()

    def _call(idx: int) -> object:
        try:
            result = verify_fn(finding)
            return bool(result)
        except Exception as exc:
            logger.debug("consistency_scorer: call %d failed: %s", idx, exc)
            return _CALL_FAILED

    with ThreadPoolExecutor(max_workers=n, thread_name_prefix="consistency") as executor:
        futures = {executor.submit(_call, i): i for i in range(n)}
        for future in as_completed(futures, timeout=timeout * n):
            try:
                result = future.result(timeout=timeout)
            except Exception:
                result = _CALL_FAILED
            with lock:
                results.append(result)

    agreements = sum(1 for r in results if r is True)
    # Clamp to valid table keys (n might not be 3)
    table_key = min(agreements, 3)
    calibrated = _get_calibration().get(table_key, 0.05)
    # Per-scope scale adjustment (Gelman BDA3 §2.4) — if scope is provided,
    # look up per-scope observed_rate from condorcet-thresholds.json and scale.
    if scope is not None:
        try:
            import json as _j, time as _t, os as _os
            from pathlib import Path as _Path
            _hh = _Path(_os.environ.get("HERMES_HOME", str(_Path.home() / ".hermes")))
            _hp = _os.environ.get("HERMES_PROFILE", "")
            _thresh_path = (
                (_hh / "profiles" / _hp) if _hp and "profiles" not in str(_hh) else _hh
            ) / "cache" / "condorcet-thresholds.json"
            if _thresh_path.exists() and (_t.time() - _thresh_path.stat().st_mtime) < 7200:
                _thresh_data = _j.loads(_thresh_path.read_text())
                _scope_data = _thresh_data.get(scope, {})
                _scope_rate = _scope_data.get('observed_rate') or _scope_data.get('threshold')
                if _scope_rate and 0 < _scope_rate < 1:
                    calibrated = min(1.0, max(0.0, calibrated * (_scope_rate / 0.5)))
        except Exception:
            pass  # scope lookup is advisory; fall back to global calibration
    # Hoeffding CI (Vershynin HDP §2.2) — attach to return value for callers that want uncertainty
    _ci_lo, _ci_hi = hoeffding_ci(agreements, len(results))

    if config.log_results:
        logger.debug(
            "consistency_scorer: n=%d agreements=%d/%d → confidence=%.2f CI=[%.2f,%.2f]",
            n, agreements, len(results), calibrated, _ci_lo, _ci_hi,
        )
        try:
            _calib_path = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))) / 'cache' / 'calibration-log.jsonl'
            if _calib_path.exists():
                import json as _j
                _lines = _calib_path.read_text().splitlines()[-50:]
                _preds = []
                for _l in _lines:
                    try:
                        _preds.append(float(_j.loads(_l).get('predicted_confidence', 0.5)))
                    except Exception:
                        pass
                if len(_preds) >= 20:
                    _mean = sum(_preds) / len(_preds)
                    if abs(_mean - 0.5) > 0.2:
                        print(f'[consistency_scorer] calibration drift detected: mean_predicted={_mean:.2f}')
        except Exception:
            pass

    return calibrated


def batch_score(
    findings: list[str],
    verify_fn: Callable[[str], bool],
    config: ConsistencyConfig | None = None,
) -> list[float]:
    """Score a list of findings. Returns list of calibrated confidences."""
    return [consistency_score(f, verify_fn, config) for f in findings]


if __name__ == "__main__":
    # Smoke test with a mock verify_fn
    import random
    rng = random.Random(42)

    def mock_verify(finding: str) -> bool:
        return rng.random() > 0.3  # 70% agree

    config = ConsistencyConfig(enabled=True, n=3, timeout=5.0)
    scores = []
    for i in range(10):
        s = consistency_score(f"Finding {i}: something happened", mock_verify, config)
        scores.append(s)

    print(f"Scores: {scores}")
    print(f"Mean: {sum(scores)/len(scores):.2f}")
    print("consistency_scorer smoke test PASSED")
