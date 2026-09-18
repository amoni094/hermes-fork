#!/usr/bin/env python3
"""
calibration_loop.py — Session-level calibration loop for Jev verification infrastructure.

Theoretical basis:
  - Gelman BDA3 §6.3 (Posterior Predictive Checks):
      A calibrated model's predicted probabilities should match empirical frequencies.
      The reliability diagram is the standard graphical PPC for binary outcomes.
      If the fitted model deviates systematically (ECE > threshold), refit.

  - Jaynes Ch.13 (Operational Calibration):
      Calibration is testable: for all p, the empirical frequency of outcomes
      where the forecaster announced p should approach p. ECE < 0.05 with N > 50
      is a reasonable operational criterion.

  - Niculescu-Mizil & Caruana (2005):
      Isotonic regression (PAV algorithm) is the non-parametric calibrator that
      minimises Brier score without assuming a parametric form.

Usage:
    python3 calibration_loop.py             # auto: refit if ECE > 0.10
    python3 calibration_loop.py --report    # print reliability diagram + ECE
    python3 calibration_loop.py --force-refit
    python3 calibration_loop.py --demo      # synthetic data demo (exit 0)

Reads:  ~/.hermes/cache/calibration-log.jsonl
Writes: ~/.hermes/cache/calibration-map.json  (if refit)
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import statistics
import sys
import time
from pathlib import Path
from typing import Optional

# ── paths ─────────────────────────────────────────────────────────────────────
HERMES_HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
CACHE_DIR = HERMES_HOME / "cache"
LOG_PATH = CACHE_DIR / "calibration-log.jsonl"
CAL_MAP_PATH = CACHE_DIR / "calibration-map.json"

# ── tuning constants ──────────────────────────────────────────────────────────
N_BINS = 10
ECE_REFIT_THRESHOLD = 0.10   # if ECE > this, refit calibrator
ECE_OK_THRESHOLD = 0.05      # if ECE < this and N > MIN_N, log OK
MIN_N_OK = 50                # minimum N for "calibration OK" verdict
PRIOR_ALPHA = 1.0            # Beta prior α (BDA3 §2.4 uniform)
PRIOR_BETA = 1.0             # Beta prior β


# ── data loading ──────────────────────────────────────────────────────────────

def load_calibration_log(path: Path) -> list[dict]:
    """Load (predicted_confidence, actual_outcome) pairs from JSONL log."""
    if not path.exists():
        return []
    records = []
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                # Accept records that have both required fields
                if "predicted_confidence" in rec and "actual_outcome" in rec:
                    records.append(rec)
            except json.JSONDecodeError:
                pass
    return records


# ── reliability diagram (BDA3 PPC) ───────────────────────────────────────────

def reliability_diagram(
    predictions: list[float],
    outcomes: list[int],
    n_bins: int = N_BINS,
) -> list[dict]:
    """
    Compute reliability diagram data: for each bin, expected vs actual frequency.

    Gelman BDA3 §6.3: the reliability diagram is the canonical posterior
    predictive check for binary probability forecasts.

    Returns list of dicts with keys: bin_lo, bin_hi, mean_conf, mean_acc, n, gap
    """
    bin_size = 1.0 / n_bins
    bins: list[list[tuple[float, int]]] = [[] for _ in range(n_bins)]

    for p, y in zip(predictions, outcomes):
        idx = min(int(p / bin_size), n_bins - 1)
        bins[idx].append((p, y))

    diagram = []
    for b in range(n_bins):
        lo = b * bin_size
        hi = (b + 1) * bin_size
        if not bins[b]:
            diagram.append({
                "bin_lo": round(lo, 2),
                "bin_hi": round(hi, 2),
                "mean_conf": None,
                "mean_acc": None,
                "n": 0,
                "gap": None,
            })
            continue
        mean_conf = statistics.mean(p for p, _ in bins[b])
        mean_acc = statistics.mean(y for _, y in bins[b])
        gap = abs(mean_acc - mean_conf)
        diagram.append({
            "bin_lo": round(lo, 2),
            "bin_hi": round(hi, 2),
            "mean_conf": round(mean_conf, 4),
            "mean_acc": round(mean_acc, 4),
            "n": len(bins[b]),
            "gap": round(gap, 4),
        })
    return diagram


def compute_ece(diagram: list[dict], total_n: int) -> float:
    """
    ECE = Σ_b (n_b / N) * |acc_b - conf_b|

    Expected Calibration Error (Naeini et al. 2015). Weighted average of
    per-bin gaps, where weights are bin sample fractions.
    """
    if total_n == 0:
        return float("nan")
    ece = 0.0
    for b in diagram:
        if b["n"] == 0 or b["gap"] is None:
            continue
        ece += (b["n"] / total_n) * b["gap"]
    return ece


def compute_mce(diagram: list[dict]) -> float:
    """MCE = max_b |acc_b - conf_b| over non-empty bins."""
    gaps = [b["gap"] for b in diagram if b["gap"] is not None]
    if not gaps:
        return float("nan")
    return max(gaps)


# ── isotonic calibrator (PAV, minimises Brier score) ─────────────────────────

def _pav(predictions: list[float], outcomes: list[int]) -> list[tuple[float, float]]:
    """
    Pool Adjacent Violators — fits isotonic regression to (p, y) pairs.

    Minimises Σ (f(p_i) - y_i)^2 subject to f non-decreasing.
    Theoretical guarantee: unique minimiser of Brier score under isotonicity
    (Niculescu-Mizil & Caruana 2005; see also proper_scoring.isotonic_calibrate).

    Returns sorted list of (input_threshold, calibrated_prob) breakpoints.
    """
    if not predictions:
        return [(0.0, 0.5), (1.0, 0.5)]

    pairs = sorted(zip(predictions, outcomes), key=lambda x: x[0])
    xs = [p for p, _ in pairs]
    ys = [float(y) for _, y in pairs]

    # N05 fix: stack-based PAV — O(N). Each element pushed/popped once → O(N) total.
    # Replaces the while-changed outer loop (O(N^2) worst case).
    def _pav_stack(y: list[float]) -> tuple[list[list[float]], list[list[float]]]:
        """Returns (y_blocks, x_blocks) using stack-based merge."""
        y_blks: list[list[float]] = []
        x_blks: list[list[float]] = []
        for i_s, (xi, yi) in enumerate(zip(xs, y)):
            y_blks.append([yi])
            x_blks.append([xi])
            while len(y_blks) >= 2 and (sum(y_blks[-2]) / len(y_blks[-2])) > (sum(y_blks[-1]) / len(y_blks[-1])):
                yb2 = y_blks.pop()
                yb1 = y_blks.pop()
                xb2 = x_blks.pop()
                xb1 = x_blks.pop()
                y_blks.append(yb1 + yb2)
                x_blks.append(xb1 + xb2)
        return y_blks, x_blks

    def mean(lst: list[float]) -> float:
        return sum(lst) / len(lst)

    blocks, xs_blocks = _pav_stack(ys)

    # Build breakpoints: for each block use its max x as the threshold
    breakpoints: list[tuple[float, float]] = []
    for blk_x, blk_y in zip(xs_blocks, blocks):
        threshold = max(blk_x)
        cal_p = mean(blk_y)
        breakpoints.append((threshold, cal_p))

    # Ensure coverage [0, 1]
    # F05 fix: deduplicate breakpoints by merging entries with identical x values
    # (average their y). sorted(set(...)) on tuples keeps both (x,y1) and (x,y2)
    # when y1 != y2, causing silent wrong output in apply_calibrator's binary search.
    # Deduplicate and enforce monotonicity (W3-F06 fix):
    # After dedup by averaging y for identical x, breakpoints can be non-monotone
    # if two merged blocks share the same max-x but have y values that decrease.
    # Enforce monotonicity with a forward pass to restore the PAV guarantee.
    bp_map: dict[float, list[float]] = {}
    for x, y in breakpoints:
        bp_map.setdefault(x, []).append(y)
    breakpoints = sorted((x, float(sum(bp_ys) / len(bp_ys))) for x, bp_ys in bp_map.items())
    # Forward-pass monotone enforcement
    for k in range(1, len(breakpoints)):
        if breakpoints[k][1] < breakpoints[k - 1][1]:
            breakpoints[k] = (breakpoints[k][0], breakpoints[k - 1][1])
    if breakpoints[0][0] > 0.0:
        breakpoints = [(0.0, breakpoints[0][1])] + breakpoints
    if breakpoints[-1][0] < 1.0:
        breakpoints = breakpoints + [(1.0, breakpoints[-1][1])]

    return breakpoints


def apply_calibrator(p: float, breakpoints: list[tuple[float, float]]) -> float:
    """Apply fitted isotonic calibrator via linear interpolation between breakpoints."""
    if not breakpoints:
        return p
    if p <= breakpoints[0][0]:
        return breakpoints[0][1]
    if p >= breakpoints[-1][0]:
        return breakpoints[-1][1]
    for i in range(len(breakpoints) - 1):
        x0, y0 = breakpoints[i]
        x1, y1 = breakpoints[i + 1]
        if x0 <= p <= x1:
            if x1 == x0:
                return y0
            t = (p - x0) / (x1 - x0)
            return y0 + t * (y1 - y0)
    return breakpoints[-1][1]


# ── BDA3 Posterior Predictive Check ──────────────────────────────────────────

def bda3_ppc_summary(
    predictions: list[float],
    outcomes: list[int],
    diagram: list[dict],
    ece: float,
    mce: float,
) -> dict:
    """
    Gelman BDA3 §6.3 posterior predictive check summary.

    Reports: whether model is calibrated (BDA3 operational criterion),
    the number of bins with significant gaps, and an overall verdict.
    """
    n = len(predictions)
    non_empty_bins = [b for b in diagram if b["n"] > 0]
    significant_gaps = [b for b in non_empty_bins if b["gap"] is not None and b["gap"] > 0.10]

    if n < 10:
        verdict = "insufficient_data"
    elif math.isnan(ece):
        verdict = "insufficient_data"
    elif ece < ECE_OK_THRESHOLD and n >= MIN_N_OK:
        verdict = "calibration_OK"
    elif ece > ECE_REFIT_THRESHOLD:
        verdict = "needs_refit"
    else:
        verdict = "marginal"

    # Beta-Binomial posterior predictive check: expected successes vs observed
    # (BDA3 §6.3: T(y) = #{successes} should be consistent with T(y_rep))
    expected_successes = sum(predictions)
    observed_successes = sum(outcomes)
    bb_check = abs(expected_successes - observed_successes) / max(n, 1)

    return {
        "n": n,
        "ece": round(ece, 5) if not math.isnan(ece) else None,
        "mce": round(mce, 5) if not math.isnan(mce) else None,
        "n_bins_significant_gap": len(significant_gaps),
        "expected_successes": round(expected_successes, 2),
        "observed_successes": observed_successes,
        "bb_discrepancy": round(bb_check, 4),
        "verdict": verdict,
    }


# ── calibration map I/O ───────────────────────────────────────────────────────

def write_calibration_map(
    breakpoints: list[tuple[float, float]],
    metadata: dict,
) -> None:
    """Write fitted calibrator to ~/.hermes/cache/calibration-map.json."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "fitted_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "breakpoints": [[x, y] for x, y in breakpoints],
        "metadata": metadata,
    }
    # N10 fix: write atomically via tempfile + os.replace to prevent corrupt JSON
    # if process is killed between open(truncate) and flush/close.
    import tempfile, os as _os
    tmp_fd, tmp_path = tempfile.mkstemp(dir=CACHE_DIR, prefix=".cal_map_", suffix=".json.tmp")
    try:
        with _os.fdopen(tmp_fd, "w") as f:
            json.dump(payload, f, indent=2)
        _os.replace(tmp_path, CAL_MAP_PATH)  # POSIX atomic rename
    except Exception:
        try:
            _os.unlink(tmp_path)
        except OSError:
            pass
        raise
    print(f"[calibration_loop] calibration map written → {CAL_MAP_PATH}", file=sys.stderr)


def load_calibration_map() -> Optional[list[tuple[float, float]]]:
    """Load fitted calibrator breakpoints from cache, or None if missing."""
    if not CAL_MAP_PATH.exists():
        return None
    try:
        with open(CAL_MAP_PATH) as f:
            data = json.load(f)
        return [(x, y) for x, y in data["breakpoints"]]
    except Exception:
        return None


# ── report printer ────────────────────────────────────────────────────────────

def print_report(diagram: list[dict], ppc: dict, ece: float, mce: float) -> None:
    """Print human-readable reliability diagram and ECE/MCE summary."""
    print("\n── Reliability Diagram (BDA3 Posterior Predictive Check) ──────────────")
    print(f"{'Bin':<12} {'ConfRange':<14} {'MeanConf':>9} {'MeanAcc':>9} {'Gap':>7} {'N':>5}")
    print("─" * 62)
    for b in diagram:
        if b["n"] == 0:
            continue
        conf_range = f"[{b['bin_lo']:.1f},{b['bin_hi']:.1f})"
        flag = " ◄ LARGE" if b["gap"] is not None and b["gap"] > 0.10 else ""
        print(
            f"  {conf_range:<12} {b['mean_conf']:>9.4f} {b['mean_acc']:>9.4f} "
            f"{b['gap']:>7.4f} {b['n']:>5}{flag}"
        )
    print("─" * 62)
    ece_str = f"{ece:.5f}" if not math.isnan(ece) else "N/A"
    mce_str = f"{mce:.5f}" if not math.isnan(mce) else "N/A"
    print(f"ECE = {ece_str}  (threshold: refit>{ECE_REFIT_THRESHOLD}, OK<{ECE_OK_THRESHOLD})")
    print(f"MCE = {mce_str}")
    print(f"N   = {ppc['n']}")
    print(f"Expected successes: {ppc['expected_successes']}  "
          f"Observed: {ppc['observed_successes']}  "
          f"BB discrepancy: {ppc['bb_discrepancy']:.4f}")
    print(f"Verdict: {ppc['verdict'].upper()}")
    print()


# ── synthetic demo data ───────────────────────────────────────────────────────

def generate_demo_data(n: int = 120, seed: int = 42) -> list[dict]:
    """
    Generate synthetic calibration log with mild miscalibration (overconfidence).

    Overconfidence: announced p is systematically 0.10 higher than true p.
    This produces ECE ≈ 0.08–0.12, triggering a refit demonstration.
    """
    rng = random.Random(seed)
    records = []
    for _ in range(n):
        true_p = rng.uniform(0.3, 0.95)
        announced_p = min(1.0, true_p + rng.gauss(0.08, 0.03))  # overconfident
        outcome = 1 if rng.random() < true_p else 0
        records.append({
            "predicted_confidence": round(announced_p, 4),
            "actual_outcome": outcome,
            "tool_name": rng.choice(["verify_fn", "gate", "logprob_classify"]),
            "timestamp": time.time() - rng.uniform(0, 86400),
        })
    return records


# ── main entry point ──────────────────────────────────────────────────────────

def run(
    records: list[dict],
    force_refit: bool = False,
    report: bool = False,
    dry_run: bool = False,
) -> dict:
    """
    Core calibration loop logic. Importable as a module.

    Args:
        records: list of calibration log entries with predicted_confidence + actual_outcome
        force_refit: bypass ECE threshold and always refit
        report: print human-readable reliability diagram
        dry_run: compute but do not write calibration map

    Returns:
        dict with keys: verdict, ece, mce, n, refit_done, breakpoints
    """
    if not records:
        return {"verdict": "no_data", "ece": None, "mce": None, "n": 0,
                "refit_done": False, "breakpoints": None}

    predictions = [r["predicted_confidence"] for r in records]
    outcomes = [int(r["actual_outcome"]) for r in records]
    n = len(records)

    diagram = reliability_diagram(predictions, outcomes, N_BINS)
    ece = compute_ece(diagram, n)
    mce = compute_mce(diagram)
    ppc = bda3_ppc_summary(predictions, outcomes, diagram, ece, mce)

    if report:
        print_report(diagram, ppc, ece, mce)

    refit_done = False
    breakpoints = None

    should_refit = force_refit or (not math.isnan(ece) and ece > ECE_REFIT_THRESHOLD)

    if should_refit:
        print(f"[calibration_loop] ECE={ece:.4f} > {ECE_REFIT_THRESHOLD} → refitting isotonic calibrator",
              file=sys.stderr)
        breakpoints = _pav(predictions, outcomes)
        meta = {
            "n": n,
            "ece_before_refit": round(ece, 5),
            "mce_before_refit": round(mce, 5) if not math.isnan(mce) else None,
            "force_refit": force_refit,
        }
        if not dry_run:
            write_calibration_map(breakpoints, meta)
        refit_done = True

    elif not math.isnan(ece) and ece < ECE_OK_THRESHOLD and n > MIN_N_OK:
        print(f"[calibration_loop] calibration OK (ECE={ece:.4f} < {ECE_OK_THRESHOLD}, N={n})",
              file=sys.stderr)

    else:
        print(f"[calibration_loop] marginal calibration (ECE={ece:.4f}, N={n}); "
              f"no action (threshold: refit>{ECE_REFIT_THRESHOLD})", file=sys.stderr)

    return {
        "verdict": ppc["verdict"],
        "ece": ece,
        "mce": mce,
        "n": n,
        "refit_done": refit_done,
        "breakpoints": breakpoints,
        "diagram": diagram,
        "ppc": ppc,
    }


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Session-level calibration loop for Jev verification infrastructure."
    )
    parser.add_argument("--force-refit", action="store_true",
                        help="Refit calibrator regardless of ECE value")
    parser.add_argument("--report", action="store_true",
                        help="Print reliability diagram and ECE/MCE summary")
    parser.add_argument("--demo", action="store_true",
                        help="Run with synthetic data (no real log required)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Compute but do not write calibration map")
    parser.add_argument("--log", default=str(LOG_PATH),
                        help=f"Path to calibration log (default: {LOG_PATH})")
    args = parser.parse_args(argv)

    if args.demo:
        print("[calibration_loop] DEMO MODE — using synthetic overconfident data", file=sys.stderr)
        records = generate_demo_data(n=120)
        result = run(records, force_refit=args.force_refit or True,
                     report=True, dry_run=args.dry_run)
        summary = {k: v for k, v in result.items() if k not in ("breakpoints", "diagram", "ppc")}
        if result["breakpoints"]:
            summary["n_breakpoints"] = len(result["breakpoints"])
        print(json.dumps(summary, indent=2))
        return 0

    log_path = Path(args.log)
    records = load_calibration_log(log_path)

    if not records:
        print(f"[calibration_loop] no calibration data found at {log_path}; nothing to do.",
              file=sys.stderr)
        print("  Tip: run with --demo to see a demonstration, or accumulate verify calls first.")
        return 0

    result = run(records, force_refit=args.force_refit, report=args.report,
                 dry_run=args.dry_run)
    summary = {k: v for k, v in result.items() if k not in ("breakpoints", "diagram", "ppc")}
    if result.get("breakpoints"):
        summary["n_breakpoints"] = len(result["breakpoints"])
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
