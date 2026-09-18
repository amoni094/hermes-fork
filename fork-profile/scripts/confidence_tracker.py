#!/usr/bin/env python3
"""
confidence_tracker.py — Confidence trajectory tracking and drift detection.

Theoretical basis:
  - Shalev-Shwartz Ch.4 (online gradient descent):
      EMA is OGD with fixed step alpha. It is NOT FTRL-L2 — FTRL-L2 gives a
      uniformly-weighted ridge estimator (mean with shrinkage), not exponential
      weighting. DRIFT_THRESHOLD=0.15 is an empirical threshold with no
      closed-form OGD stability bound. Tune by observing false-positive rate
      on held-out sessions.

  - Jaynes Ch.13 (operational calibration):
      Overconfidence (mean announced p >> empirical frequency) is diagnosable
      from ECE. If ECE > 0.08 and mean confidence > 0.85, the forecaster is
      systematically overconfident — the honest action is to lower announced p.

Usage:
    python3 confidence_tracker.py              # analyse calibration log
    python3 confidence_tracker.py --window 30  # use 30-call rolling window
    python3 confidence_tracker.py --demo       # synthetic data demo (exit 0)

Reads:  ~/.hermes/cache/calibration-log.jsonl
Writes: ~/.hermes/cache/confidence-trajectory.json
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import sys
import time
from pathlib import Path
from typing import Optional

# ── paths ─────────────────────────────────────────────────────────────────────
HERMES_HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
CACHE_DIR = HERMES_HOME / "cache"
LOG_PATH = CACHE_DIR / "calibration-log.jsonl"
TRAJECTORY_PATH = CACHE_DIR / "confidence-trajectory.json"

# ── tuning constants ──────────────────────────────────────────────────────────
DEFAULT_WINDOW = 20
EMA_ALPHA_DEFAULT = None          # auto: 2/(W+1)
DRIFT_THRESHOLD = 0.15            # Empirical threshold; no closed-form stability bound from OGD theory. Tune by observing false-positive rate on held-out sessions.
OVERCONF_MEAN_THRESHOLD = 0.85    # mean confidence above which we check ECE
OVERCONF_ECE_THRESHOLD = 0.08     # ECE above which overconfidence is flagged
N_BINS_ECE = 10


# ── data loading ──────────────────────────────────────────────────────────────

def load_records(path: Path) -> list[dict]:
    """Load all calibration log records, requiring predicted_confidence field."""
    if not path.exists():
        return []
    records = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                if "predicted_confidence" in rec:
                    records.append(rec)
            except json.JSONDecodeError:
                pass
    return records


def group_by_tool(records: list[dict]) -> dict[str, list[dict]]:
    """Group records by tool_name. Records without tool_name go into '_unknown'."""
    groups: dict[str, list[dict]] = {}
    for rec in records:
        tool = rec.get("tool_name", "_unknown")
        groups.setdefault(tool, []).append(rec)
    return groups


# ── EMA (online gradient descent, fixed step size) ───────────────────────────

def ema_series(values: list[float], alpha: float) -> list[float]:
    """
    Compute exponential moving average series.

    EMA_t = α * x_t + (1 - α) * EMA_{t-1}

    EMA is online gradient descent (OGD) with fixed step alpha. It is NOT
    FTRL-L2 — FTRL-L2 gives a uniformly-weighted ridge estimator (mean with
    shrinkage), not exponential weighting.

    The stability bound: |EMA_t - EMA_{t-k}| < ε_stab for stationary distributions.
    A violation (Δ > DRIFT_THRESHOLD = 0.15) is the operational drift signal.
    """
    if not values:
        return []
    result = [values[0]]
    for x in values[1:]:
        result.append(alpha * x + (1 - alpha) * result[-1])
    return result


def detect_drift(
    ema_vals: list[float],
    window: int,
    threshold: float = DRIFT_THRESHOLD,
) -> tuple[bool, float, str]:
    """
    Check if EMA confidence dropped > threshold in last `window` calls.

    OGD stability heuristic: in a stationary environment, |EMA_t - EMA_{t-W}|
    should remain small. If Δ > DRIFT_THRESHOLD = 0.15 (an empirical threshold
    with no closed-form OGD bound), we flag a possible distribution shift.

    Returns:
        (drift_detected, delta, explanation)
    """
    if len(ema_vals) < 2:
        return False, 0.0, "insufficient_data"

    recent = ema_vals[-min(window, len(ema_vals)):]
    delta = recent[-1] - recent[0]   # signed: positive = rising, negative = falling

    drift = delta < -threshold   # only care about drops (falling confidence)
    explanation = (
        f"EMA drop={delta:.4f} over last {len(recent)} calls "
        f"(threshold={threshold})"
    )
    return drift, delta, explanation


def detect_overconfidence(
    predictions: list[float],
    outcomes: list[int],
    n_bins: int = N_BINS_ECE,
) -> tuple[bool, float, float, str]:
    """
    Detect overconfidence: mean p >> empirical frequency, ECE > threshold.

    Jaynes Ch.13: if the forecaster's announced p is systematically higher than
    the empirical frequency of outcomes, the forecaster is overconfident.
    We check: mean(p) > OVERCONF_MEAN_THRESHOLD and ECE > OVERCONF_ECE_THRESHOLD.

    Returns:
        (overconfident, mean_conf, ece, explanation)
    """
    if not predictions or not outcomes:
        return False, 0.0, float("nan"), "insufficient_data"

    mean_conf = sum(predictions) / len(predictions)

    # Compute ECE
    n = len(predictions)
    bin_size = 1.0 / n_bins
    bins: list[list[tuple[float, int]]] = [[] for _ in range(n_bins)]
    for p, y in zip(predictions, outcomes):
        idx = min(int(p / bin_size), n_bins - 1)
        bins[idx].append((p, y))

    ece = 0.0
    for b in bins:
        if not b:
            continue
        mc = sum(p for p, _ in b) / len(b)
        ma = sum(y for _, y in b) / len(b)
        ece += (len(b) / n) * abs(ma - mc)

    overconf = (mean_conf > OVERCONF_MEAN_THRESHOLD) and (ece > OVERCONF_ECE_THRESHOLD)
    explanation = (
        f"mean_conf={mean_conf:.4f} (threshold>{OVERCONF_MEAN_THRESHOLD}), "
        f"ECE={ece:.4f} (threshold>{OVERCONF_ECE_THRESHOLD})"
    )
    return overconf, mean_conf, ece, explanation


# ── per-tool trajectory analysis ──────────────────────────────────────────────

def analyse_tool(
    tool_name: str,
    records: list[dict],
    window: int,
    alpha: Optional[float] = None,
) -> dict:
    """
    Compute EMA trajectory, drift detection, and overconfidence check for one tool.

    Returns dict with: tool_name, n, ema_current, ema_start, drift_detected,
    drift_delta, overconfident, mean_conf, ece, warnings.
    """
    # Sort by timestamp if available
    # P9A-07 fix: missing-timestamp records previously sorted to 0.0 (front), contaminating
    # EMA start and producing phantom drift. Sort them to the END with float('inf').
    records_sorted = sorted(records, key=lambda r: r.get("timestamp", float("inf")))
    predictions = [r["predicted_confidence"] for r in records_sorted]
    # Note: `outcomes` variable removed (NEW-BUG-02) — superseded by labeled_pairs below.

    n = len(predictions)
    effective_alpha = alpha if alpha is not None else (2.0 / (window + 1))

    # W3-F07 fix: compute EMA series on labeled records only (when labels exist) so
    # drift and overconfidence operate on the same population. Pre-F02 logs lack
    # actual_outcome on many records; mixing labeled and unlabeled in ema_vals inflates
    # the series relative to the labeled subset, making drift/overconfidence incomparable.
    # NEW-BUG-02: removed the now-dead `outcomes` variable (lines formerly 196-197);
    # outcomes_aligned/labeled_pairs below supersede it entirely.
    outcomes_aligned = [
        int(r["actual_outcome"]) if "actual_outcome" in r else None
        for r in records_sorted
    ]
    labeled_pairs = [
        (p, o) for p, o in zip(predictions, outcomes_aligned) if o is not None
    ]
    if labeled_pairs:
        labeled_predictions = [p for p, _ in labeled_pairs]
        ema_vals = ema_series(labeled_predictions, effective_alpha)
    else:
        ema_vals = ema_series(predictions, effective_alpha)

    warnings: list[str] = []

    # Drift detection
    drift, delta, drift_expl = detect_drift(ema_vals, window)
    if drift:
        warnings.append(f"WARNING: confidence drift detected for tool={tool_name!r}: "
                        f"EMA dropped {abs(delta):.3f} in last {window} calls "
                        f"(empirical drift threshold = {DRIFT_THRESHOLD}). "
                        "Possible distribution shift — recalibrate.")

    # Overconfidence detection (only if we have outcomes)
    overconf = False
    mean_conf = 0.0
    tool_ece = float("nan")
    # F06/W3-F07 fix: labeled_pairs already computed above for EMA alignment.
    if labeled_pairs:
        lp_preds, lp_outcomes = zip(*labeled_pairs)
        overconf, mean_conf, tool_ece, oc_expl = detect_overconfidence(list(lp_preds), list(lp_outcomes))
        if overconf:
            warnings.append(f"WARNING: overconfidence detected for tool={tool_name!r}: "
                            f"{oc_expl}. "
                            "Announcements are systematically higher than empirical frequency "
                            "(Jaynes Ch.13). Run calibration_loop.py --force-refit.")
    else:
        mean_conf = sum(predictions) / max(n, 1)

    result = {
        "tool_name": tool_name,
        "n": n,
        "ema_alpha": round(effective_alpha, 4),
        "ema_current": round(ema_vals[-1], 4) if ema_vals else None,
        "ema_start": round(ema_vals[0], 4) if ema_vals else None,
        "ema_window_start": round(ema_vals[-min(window, len(ema_vals))], 4) if ema_vals else None,
        "drift_detected": drift,
        "drift_delta": round(delta, 4),
        "drift_explanation": drift_expl,
        "overconfident": overconf,
        "mean_conf": round(mean_conf, 4),
        "ece": round(tool_ece, 5) if not math.isnan(tool_ece) else None,
        "warnings": warnings,
    }
    return result


# ── synthetic demo data ───────────────────────────────────────────────────────

def generate_demo_data(n: int = 80, seed: int = 42) -> list[dict]:
    """
    Synthetic demo: one drifting tool ('verify_fn') and one stable tool ('gate').
    verify_fn: starts confident (0.85), drops to 0.60 at end → drift warning.
    gate: stable around 0.70 but overconfident (ECE > 0.08) → overconf warning.
    """
    rng = random.Random(seed)
    records = []
    t0 = time.time() - n * 60  # spread over last n minutes

    for i in range(n):
        ts = t0 + i * 60

        # verify_fn: linearly drifting confidence
        frac = i / max(n - 1, 1)
        true_p_vf = 0.85 - 0.30 * frac  # drops from 0.85 to 0.55
        conf_vf = min(0.99, true_p_vf + rng.gauss(0.02, 0.02))
        out_vf = 1 if rng.random() < true_p_vf else 0
        records.append({
            "predicted_confidence": round(conf_vf, 4),
            "actual_outcome": out_vf,
            "tool_name": "verify_fn",
            "timestamp": ts,
        })

        # gate: stable but overconfident (announces 0.90, true ~0.72)
        true_p_g = 0.72 + rng.gauss(0.0, 0.05)
        conf_g = min(0.99, true_p_g + rng.gauss(0.18, 0.03))  # systematic +0.18 bias
        out_g = 1 if rng.random() < max(0, min(1, true_p_g)) else 0
        records.append({
            "predicted_confidence": round(conf_g, 4),
            "actual_outcome": out_g,
            "tool_name": "gate",
            "timestamp": ts + 1,
        })

    return records


# ── main ──────────────────────────────────────────────────────────────────────

def run(
    records: list[dict],
    window: int = DEFAULT_WINDOW,
    alpha: Optional[float] = None,
) -> dict:
    """
    Core trajectory tracking logic. Importable as a module.

    Returns:
        dict with keys: tools, global_warnings, generated_at
    """
    if not records:
        return {
            "tools": {},
            "global_warnings": [],
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "note": "no_data",
        }

    groups = group_by_tool(records)
    tool_reports = {}
    all_warnings: list[str] = []

    for tool_name, tool_records in sorted(groups.items()):
        report = analyse_tool(tool_name, tool_records, window, alpha)
        tool_reports[tool_name] = report
        all_warnings.extend(report["warnings"])

    output = {
        "tools": tool_reports,
        "global_warnings": all_warnings,
        "n_tools": len(tool_reports),
        "n_records": len(records),
        "window": window,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    return output


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Confidence trajectory tracker for Jev verification infrastructure."
    )
    parser.add_argument("--window", type=int, default=DEFAULT_WINDOW,
                        help=f"Rolling window size for drift detection (default: {DEFAULT_WINDOW})")
    parser.add_argument("--alpha", type=float, default=None,
                        help="EMA alpha override (default: 2/(window+1))")
    parser.add_argument("--demo", action="store_true",
                        help="Run with synthetic drift+overconfidence demo data (exit 0)")
    parser.add_argument("--log", default=str(LOG_PATH),
                        help=f"Path to calibration log (default: {LOG_PATH})")
    parser.add_argument("--out", default=str(TRAJECTORY_PATH),
                        help=f"Output JSON path (default: {TRAJECTORY_PATH})")
    parser.add_argument("--quiet", action="store_true",
                        help="Suppress warnings from stderr")
    args = parser.parse_args(argv)

    if args.demo:
        print("[confidence_tracker] DEMO MODE — synthetic drift + overconfidence data",
              file=sys.stderr)
        records = generate_demo_data(n=80)
    else:
        records = load_records(Path(args.log))
        if not records:
            print(f"[confidence_tracker] no data found at {args.log}; nothing to do.",
                  file=sys.stderr)
            print("  Tip: run with --demo to see a demonstration.")
            return 0

    result = run(records, window=args.window, alpha=args.alpha)

    # Print warnings to stderr
    if not args.quiet:
        for w in result.get("global_warnings", []):
            print(w, file=sys.stderr)

    # Write JSON report — use tempfile+os.replace for atomicity (P7A-08 fix).
    # open('w') truncates immediately; a crash mid-write leaves an empty/corrupt file.
    # tempfile+replace is atomic on POSIX — matches calibration_loop.py's pattern.
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    import tempfile as _tf, os as _os
    fd, tmp = _tf.mkstemp(dir=out_path.parent, prefix=".ct_tmp_", suffix=".json")
    try:
        with _os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        _os.replace(tmp, out_path)
    except Exception:
        try:
            _os.unlink(tmp)
        except OSError:
            pass
        raise
    print(f"[confidence_tracker] report written → {out_path}", file=sys.stderr)

    # Print compact summary to stdout
    summary = {
        "n_records": result["n_records"],
        "n_tools": result["n_tools"],
        "window": result["window"],
        "n_warnings": len(result["global_warnings"]),
        "tools_with_drift": [
            t for t, r in result["tools"].items() if r.get("drift_detected")
        ],
        "tools_overconfident": [
            t for t, r in result["tools"].items() if r.get("overconfident")
        ],
        "generated_at": result["generated_at"],
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
