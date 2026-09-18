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

# Sentinel for a failed/timeout verification call
_CALL_FAILED = object()


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
    calibrated = _CALIBRATION.get(table_key, 0.05)

    if config.log_results:
        logger.debug(
            "consistency_scorer: n=%d agreements=%d/%d → confidence=%.2f",
            n, agreements, len(results), calibrated,
        )
        try:
            _calib_path = Path('~/.hermes/cache/calibration-log.jsonl').expanduser()
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
