#!/usr/bin/env python3
"""
gate_audit.py — Audit calibrated gate decisions for consistency and error rates.

Theoretical basis:
  - Gelman BDA3 §2.4 (Beta-Binomial posterior):
      For each gate (act/flag/escalate), we compute the posterior probability
      that the gate's false-escalation or false-act rate exceeds an acceptable
      threshold. With a Beta(1,1) prior, k false decisions in n gate invocations
      yields posterior mean (1 + k) / (2 + n) — never 0 or 1.

  - Wald Ch.3 (SPRT):
      A sequential test for whether the error rate is below acceptable threshold.
      If the posterior probability of H0: error_rate < 0.10 exceeds 0.95,
      the gate's behaviour is acceptable.

  - Jaynes Ch.13 (calibrated gate):
      A gate is consistent iff its decisions match the calibrated thresholds:
      - act: confidence >= act_threshold
      - flag: flag_threshold <= confidence < act_threshold
      - escalate: confidence < flag_threshold
      Inconsistency = acted when confidence was too low, or escalated when high.

Gate threshold defaults (from jev_verify_fn.py GateConfig, medium stakes):
    act_threshold  = 0.90
    flag_threshold = 0.50

Usage:
    python3 gate_audit.py               # audit calibration-log.jsonl
    python3 gate_audit.py --demo        # synthetic data demo (exit 0)
    python3 gate_audit.py --report      # human-readable report to stdout

Reads:  ~/.hermes/cache/calibration-log.jsonl
Writes: ~/.hermes/cache/gate-audit.json
"""
from __future__ import annotations

import argparse
import json
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
AUDIT_PATH = CACHE_DIR / "gate-audit.json"

# ── gate threshold defaults (medium stakes) ───────────────────────────────────
DEFAULT_ACT_THRESHOLD = 0.90
DEFAULT_FLAG_THRESHOLD = 0.50

# ── BDA3 priors ───────────────────────────────────────────────────────────────
PRIOR_ALPHA = 1.0   # Beta(1,1) uniform prior (Jeffreys uninformative for binomial)
PRIOR_BETA = 1.0

# ── acceptable error rate thresholds ─────────────────────────────────────────
ACCEPTABLE_FALSE_ESCALATION = 0.10   # escalated even though confidence was high
ACCEPTABLE_FALSE_ACT = 0.10          # acted even though confidence was low


# ── Beta-Binomial posterior (BDA3 §2.4) ──────────────────────────────────────

def beta_binomial_posterior(
    k: int,
    n: int,
    alpha: float = PRIOR_ALPHA,
    beta: float = PRIOR_BETA,
) -> dict:
    """
    Beta-Binomial posterior for k successes in n trials.

    BDA3 §2.4: posterior is Beta(alpha+k, beta+n-k).
    Returns posterior mean, 5th and 95th percentiles (via Wilson-Hilferty approx).
    Replaces the heuristic lookup table (k/n → rate) used in naive auditing.

    posterior_mean = (alpha + k) / (alpha + beta + n)
    """
    alpha_post = alpha + k
    beta_post = beta + (n - k)
    total_post = alpha_post + beta_post
    mean = alpha_post / total_post

    # Mode (MAP estimator): valid for alpha_post, beta_post > 1
    if alpha_post > 1 and beta_post > 1:
        mode = (alpha_post - 1) / (total_post - 2)
    else:
        mode = mean  # uniform or J-shaped: use mean

    # Approximate 90% credible interval via Beta quantiles (no scipy)
    # Use Wald-style approximation: mean ± 1.645 * sqrt(var)
    var = (alpha_post * beta_post) / (total_post ** 2 * (total_post + 1))
    import math
    std = math.sqrt(var)
    ci_lo = max(0.0, mean - 1.645 * std)
    ci_hi = min(1.0, mean + 1.645 * std)

    return {
        "k": k,
        "n": n,
        "posterior_mean": round(mean, 5),
        "posterior_mode": round(mode, 5),
        "ci_90_lo": round(ci_lo, 5),
        "ci_90_hi": round(ci_hi, 5),
        "alpha_post": alpha_post,
        "beta_post": beta_post,
    }


# ── consistency check ─────────────────────────────────────────────────────────

def is_consistent_decision(
    gate_decision: str,
    confidence: float,
    act_threshold: float = DEFAULT_ACT_THRESHOLD,
    flag_threshold: float = DEFAULT_FLAG_THRESHOLD,
) -> tuple[bool, str]:
    """
    Check whether a gate decision is consistent with the calibrated thresholds.

    Jaynes Ch.13: a gate is consistent iff its discrete decision matches the
    region the confidence falls into:
      confidence >= act_threshold  → expected: "act"
      flag_threshold <= conf < act → expected: "flag"
      confidence < flag_threshold  → expected: "escalate"

    Returns (consistent, expected_decision).
    """
    if confidence >= act_threshold:
        expected = "act"
    elif confidence >= flag_threshold:
        expected = "flag"
    else:
        expected = "escalate"

    consistent = gate_decision.lower() == expected
    return consistent, expected


def classify_error(
    gate_decision: str,
    expected_decision: str,
    confidence: float,
    act_threshold: float = DEFAULT_ACT_THRESHOLD,
) -> Optional[str]:
    """
    Classify the type of gate error.

    false_escalation: escalated when confidence was high (≥ act_threshold).
                      Cost: unnecessary human interruption.
    false_act:        acted when confidence was low (< flag_threshold).
                      Cost: autonomous action under uncertainty — higher risk.
    mismatch:         other inconsistency (flag vs act/escalate swap).

    Returns error type string, or None if consistent.
    """
    if gate_decision == expected_decision:
        return None
    # P5B-04 fix: no ground truth → unclassifiable; don't generate spurious error counts.
    if expected_decision is None:
        return None
    if gate_decision == "escalate" and confidence >= act_threshold:
        return "false_escalation"
    # F03 fix: false_act means "acted when confidence was BELOW flag_threshold".
    # Acting when confidence is in the flag zone [flag_threshold, act_threshold) is
    # a calibration mismatch, not a false_act — it inflated false_act_rate previously.
    if gate_decision == "act" and expected_decision == "escalate":
        # Confidence was sub-flag-threshold (< flag_threshold): genuine false_act.
        return "false_act"
    if gate_decision == "act" and expected_decision == "flag":
        # Confidence in flag zone — wrong tier but not dangerous; count as mismatch.
        return "mismatch"
    return "mismatch"


# ── data loading ──────────────────────────────────────────────────────────────

def load_gate_records(path: Path) -> list[dict]:
    """
    Load calibration log records that have a 'gate' field.

    gate field must be one of: act, flag, escalate.
    Records without a gate field are skipped (they are raw confidence logs).
    """
    if not path.exists():
        return []
    records = []
    # P4B-08 fix: explicit UTF-8 + replace errors (matches write path in __init__.py).
    # Without this, a single non-UTF-8 byte aborts the whole audit (UnicodeDecodeError
    # not caught in the per-line try/except block).
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                if (
                    "gate" in rec
                    and "predicted_confidence" in rec
                    and isinstance(rec["predicted_confidence"], (int, float))  # P5B-09: skip non-numeric
                    and rec["gate"] in ("act", "flag", "escalate")
                ):
                    records.append(rec)
            except json.JSONDecodeError:
                pass
    return records


# ── per-gate analysis ─────────────────────────────────────────────────────────

def analyse_gate_decisions(
    records: list[dict],
    act_threshold: float = DEFAULT_ACT_THRESHOLD,
    flag_threshold: float = DEFAULT_FLAG_THRESHOLD,
) -> dict:
    """
    For each gate name (or 'all'), compute:
      - n_decisions: total gate invocations
      - n_consistent: gate decision matched calibrated thresholds
      - n_false_escalation: escalated when confidence was high
      - n_false_act: acted when confidence was low
      - n_mismatch: other inconsistencies
      - false_escalation_rate: Beta-Binomial posterior mean
      - false_act_rate: Beta-Binomial posterior mean
      - posterior: BDA3 posteriors for each error type

    Groups results by gate_name if present; also computes aggregate 'all'.
    """
    # Group by gate_name
    by_gate: dict[str, list[dict]] = {}
    for rec in records:
        gate_name = rec.get("gate_name", "default")
        by_gate.setdefault(gate_name, []).append(rec)

    def analyse_group(group_records: list[dict]) -> dict:
        n = len(group_records)
        counts = {
            "consistent": 0,
            "false_escalation": 0,
            "false_act": 0,
            "mismatch": 0,
        }
        decisions: list[dict] = []

        for rec in group_records:
            conf = rec["predicted_confidence"]
            gate_dec = rec["gate"].lower()
            consistent, expected = is_consistent_decision(
                gate_dec, conf, act_threshold, flag_threshold
            )
            err_type = classify_error(gate_dec, expected, conf, act_threshold)

            if consistent:
                counts["consistent"] += 1
            elif err_type:
                counts[err_type] = counts.get(err_type, 0) + 1

            decisions.append({
                "gate": gate_dec,
                "expected": expected,
                "confidence": conf,
                "consistent": consistent,
                "error_type": err_type,
            })

        # Beta-Binomial posteriors (BDA3 §2.4)
        fe_post = beta_binomial_posterior(counts["false_escalation"], n)
        fa_post = beta_binomial_posterior(counts["false_act"], n)
        mm_post = beta_binomial_posterior(counts["mismatch"], n)

        # SPRT-style acceptability: posterior mean < acceptable threshold → OK
        fe_ok = fe_post["posterior_mean"] < ACCEPTABLE_FALSE_ESCALATION
        fa_ok = fa_post["posterior_mean"] < ACCEPTABLE_FALSE_ACT

        consistency_rate = counts["consistent"] / max(n, 1)
        verdict = "OK" if (fe_ok and fa_ok and consistency_rate > 0.85) else "REVIEW"

        return {
            "n_decisions": n,
            "n_consistent": counts["consistent"],
            "n_false_escalation": counts["false_escalation"],
            "n_false_act": counts["false_act"],
            "n_mismatch": counts["mismatch"],
            "consistency_rate": round(consistency_rate, 4),
            "false_escalation_posterior": fe_post,
            "false_act_posterior": fa_post,
            "mismatch_posterior": mm_post,
            "false_escalation_acceptable": fe_ok,
            "false_act_acceptable": fa_ok,
            "verdict": verdict,
        }

    gate_results: dict[str, dict] = {}
    for gate_name, group in sorted(by_gate.items()):
        gate_results[gate_name] = analyse_group(group)

    # Aggregate "all"
    if len(by_gate) > 1:
        gate_results["_all"] = analyse_group(records)

    return gate_results


# ── consistency summary ───────────────────────────────────────────────────────

def consistency_summary(gate_results: dict) -> dict:
    """
    Overall summary: any gate with REVIEW verdict → overall_verdict = REVIEW.
    """
    all_ok = all(g["verdict"] == "OK" for g in gate_results.values())
    review_gates = [n for n, g in gate_results.items() if g["verdict"] == "REVIEW"]
    return {
        "overall_verdict": "OK" if all_ok else "REVIEW",
        "review_gates": review_gates,
        "n_gates": len(gate_results),
    }


# ── human-readable report ─────────────────────────────────────────────────────

def print_report(gate_results: dict, summary: dict) -> None:
    """Print human-readable gate audit report."""
    print("\n── Gate Audit Report (BDA3 Beta-Binomial, Jaynes Ch.13) ────────────────")
    for gate_name, res in sorted(gate_results.items()):
        print(f"\n  Gate: {gate_name!r}  N={res['n_decisions']}  "
              f"Verdict: {res['verdict']}")
        print(f"    Consistent:        {res['n_consistent']:3d} / {res['n_decisions']} "
              f"({res['consistency_rate']:.1%})")
        fe = res["false_escalation_posterior"]
        fa = res["false_act_posterior"]
        print(f"    False escalations: {res['n_false_escalation']:3d}  "
              f"posterior_mean={fe['posterior_mean']:.4f}  "
              f"90%CI=[{fe['ci_90_lo']:.3f},{fe['ci_90_hi']:.3f}]  "
              f"{'OK' if res['false_escalation_acceptable'] else 'REVIEW'}")
        print(f"    False acts:        {res['n_false_act']:3d}  "
              f"posterior_mean={fa['posterior_mean']:.4f}  "
              f"90%CI=[{fa['ci_90_lo']:.3f},{fa['ci_90_hi']:.3f}]  "
              f"{'OK' if res['false_act_acceptable'] else 'REVIEW'}")
        print(f"    Mismatches:        {res['n_mismatch']:3d}")

    print(f"\n── Overall: {summary['overall_verdict']} ─────────────────────────────")
    if summary["review_gates"]:
        print(f"  Gates requiring review: {summary['review_gates']}")
    print()


# ── synthetic demo data ───────────────────────────────────────────────────────

def generate_demo_data(n: int = 60, seed: int = 42) -> list[dict]:
    """
    Synthetic gate log with:
    - 'default' gate: mostly consistent, small false_escalation rate
    - 'high_stakes' gate: systematic false_act errors (acted when confidence low)
    """
    rng = random.Random(seed)
    records = []
    t0 = time.time() - n * 60

    for i in range(n):
        ts = t0 + i * 60

        # default gate: well-behaved but ~8% false escalation
        conf = rng.uniform(0.40, 0.99)
        if conf >= DEFAULT_ACT_THRESHOLD:
            # Should be "act"; ~8% chance of spurious escalation
            gate = "escalate" if rng.random() < 0.08 else "act"
        elif conf >= DEFAULT_FLAG_THRESHOLD:
            gate = "flag"
        else:
            gate = "escalate"
        records.append({
            "predicted_confidence": round(conf, 4),
            "gate": gate,
            "gate_name": "default",
            "actual_outcome": 1 if rng.random() < conf else 0,
            "timestamp": ts,
        })

        # high_stakes gate: systematic false_act (~20% rate — acts at low confidence)
        conf2 = rng.uniform(0.30, 0.85)
        if conf2 < DEFAULT_FLAG_THRESHOLD:
            # Should be "escalate" or "flag"; ~20% chance of spurious "act"
            gate2 = "act" if rng.random() < 0.20 else "escalate"
        elif conf2 < DEFAULT_ACT_THRESHOLD:
            gate2 = "flag"
        else:
            gate2 = "act"
        records.append({
            "predicted_confidence": round(conf2, 4),
            "gate": gate2,
            "gate_name": "high_stakes",
            "actual_outcome": 1 if rng.random() < conf2 else 0,
            "timestamp": ts + 1,
        })

    return records


# ── main ──────────────────────────────────────────────────────────────────────

def run(
    records: list[dict],
    act_threshold: float = DEFAULT_ACT_THRESHOLD,
    flag_threshold: float = DEFAULT_FLAG_THRESHOLD,
    report: bool = False,
) -> dict:
    """
    Core gate audit logic. Importable as a module.

    Args:
        records: gate-decision records from calibration log
        act_threshold: confidence above which "act" is expected
        flag_threshold: confidence below which "escalate" is expected
        report: print human-readable report

    Returns:
        dict with keys: gates, summary, generated_at, thresholds
    """
    if not records:
        return {
            "gates": {},
            "summary": {"overall_verdict": "no_data", "n_gates": 0, "review_gates": []},
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "thresholds": {"act": act_threshold, "flag": flag_threshold},
        }

    gate_results = analyse_gate_decisions(records, act_threshold, flag_threshold)
    summary = consistency_summary(gate_results)

    if report:
        print_report(gate_results, summary)

    return {
        "gates": gate_results,
        "summary": summary,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "thresholds": {"act": act_threshold, "flag": flag_threshold},
        "n_records": len(records),
    }


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Gate audit script for Jev verification infrastructure."
    )
    parser.add_argument("--demo", action="store_true",
                        help="Run with synthetic gate decision demo data (exit 0)")
    parser.add_argument("--report", action="store_true",
                        help="Print human-readable audit report")
    parser.add_argument("--act-threshold", type=float, default=DEFAULT_ACT_THRESHOLD,
                        help=f"Act threshold (default: {DEFAULT_ACT_THRESHOLD})")
    parser.add_argument("--flag-threshold", type=float, default=DEFAULT_FLAG_THRESHOLD,
                        help=f"Flag threshold (default: {DEFAULT_FLAG_THRESHOLD})")
    parser.add_argument("--log", default=str(LOG_PATH),
                        help=f"Path to calibration log (default: {LOG_PATH})")
    parser.add_argument("--out", default=str(AUDIT_PATH),
                        help=f"Output JSON path (default: {AUDIT_PATH})")
    args = parser.parse_args(argv)

    if args.demo:
        print("[gate_audit] DEMO MODE — synthetic gate decisions", file=sys.stderr)
        records = generate_demo_data(n=60)
    else:
        records = load_gate_records(Path(args.log))
        if not records:
            print(
                f"[gate_audit] no gate records found in {args.log} "
                "(records need a 'gate' field: act|flag|escalate).",
                file=sys.stderr,
            )
            print("  Tip: run with --demo to see a demonstration.")
            return 0

    result = run(
        records,
        act_threshold=args.act_threshold,
        flag_threshold=args.flag_threshold,
        report=args.report or args.demo,  # always show report in demo
    )

    # Write JSON output
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # P8A-08 fix: atomic write via tempfile+os.replace (matches calibration_loop.py pattern).
    import tempfile as _tempfile
    fd, tmp_path = _tempfile.mkstemp(dir=out_path.parent, prefix=".gate_audit_tmp_", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        os.replace(tmp_path, out_path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
    print(f"[gate_audit] audit written → {out_path}", file=sys.stderr)

    # Print compact summary
    compact = {
        "overall_verdict": result["summary"]["overall_verdict"],
        "n_records": result["n_records"],
        "n_gates": result["summary"]["n_gates"],
        "review_gates": result["summary"]["review_gates"],
        "generated_at": result["generated_at"],
    }
    print(json.dumps(compact, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
