"""
Occam's Razor / model-evidence audit for the jev-compaction retention policy.

Grounded in MacKay (2003) 'Information Theory, Inference, and Learning
Algorithms', Ch.28 (Occam's Razor and the Evidence Framework):

    The preferred model is the one with higher marginal likelihood P(D|M),
    or equivalently, higher log-evidence  log P(D|M).

In the compaction context:
    D = observed demotion outcomes (score, decision, actual_quality_delta)
    M1 = threshold model: retain if score > 0.5
    M2 = Jev model:       retain per the stored 'decision' field

Log-evidence is computed as the sum of log P(outcome | model) over all
outcomes, where P(outcome | model) is derived from a simple Gaussian
likelihood on the quality delta:

    For each outcome:
        predicted_delta(M) = +score  if model says RETAIN
                           = -score  if model says DEMOTE
        log p(outcome | M) = log N(actual_quality_delta;
                                   predicted_delta(M), sigma=1.0)

Bayes factor BF = exp(log_evidence_M2 - log_evidence_M1):
    BF > 3   → Jev model preferred
    BF < 1/3 → Threshold model preferred
    else     → Inconclusive

Public API
----------
occam_evidence_audit(outcomes: list[dict]) -> dict

    Parameters
    ----------
    outcomes : list of dict
        Each dict has:
            score              : float   (0–1 retention score)
            decision           : str     ('RETAIN' or 'DEMOTE', Jev decision)
            actual_quality_delta : float (positive = quality improved)

    Returns
    -------
    dict with keys:
        m1_log_evidence   : float
        m2_log_evidence   : float
        preferred_model   : str ('M1_threshold' | 'M2_jev' | 'inconclusive')
        bayes_factor      : float
"""

from __future__ import annotations

import math
import sys
from typing import Dict, List

# ---------------------------------------------------------------------------
# Gaussian log-likelihood helper
# ---------------------------------------------------------------------------

_SIGMA = 1.0   # noise standard deviation for quality-delta model


def _log_gaussian(x: float, mu: float, sigma: float = _SIGMA) -> float:
    """log N(x; mu, sigma) — up to additive constant."""
    return -0.5 * ((x - mu) / sigma) ** 2 - math.log(sigma * math.sqrt(2 * math.pi))


# ---------------------------------------------------------------------------
# Per-model predicted quality delta
# ---------------------------------------------------------------------------

def _m1_predict(score: float) -> float:
    """Threshold model M1: retain if score > 0.5."""
    return score if score > 0.5 else -score


def _m2_predict(score: float, decision: str) -> float:
    """Jev model M2: uses the stored Jev decision."""
    return score if decision.upper() == "RETAIN" else -score


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def occam_evidence_audit(outcomes: List[Dict]) -> Dict:
    """
    Compute log-evidence for M1 (threshold) and M2 (Jev model).

    Parameters
    ----------
    outcomes : list of dict
        Each entry must have:
            'score'                : float
            'decision'             : str  ('RETAIN' or 'DEMOTE')
            'actual_quality_delta' : float

    Returns
    -------
    dict with m1_log_evidence, m2_log_evidence, preferred_model, bayes_factor.
    """
    if not outcomes:
        return {
            "m1_log_evidence": 0.0,
            "m2_log_evidence": 0.0,
            "preferred_model": "inconclusive",
            "bayes_factor": 1.0,
        }

    m1_log_ev = 0.0
    m2_log_ev = 0.0

    for o in outcomes:
        score  = float(o["score"])
        decision = str(o.get("decision", "RETAIN"))
        # P8B-07 fix: missing 'decision' key defaults to "RETAIN", biasing M2 evidence upward.
        # Warn when the key is genuinely absent (not just defaulting) so log-format issues are visible.
        if "decision" not in o:
            import warnings as _w2; _w2.warn(
                "occam_audit: record missing 'decision' key; defaulting to RETAIN", RuntimeWarning, stacklevel=2
            )
        actual = float(o["actual_quality_delta"])
        # P7B-08 fix: NaN/Inf from a corrupt calibration log entry propagates through
        # _log_gaussian → NaN bayes_factor → json.dumps raises ValueError.  Skip entries
        # that are not finite so one bad record doesn't abort the whole audit.
        if not (math.isfinite(score) and math.isfinite(actual)):
            import warnings as _w; _w.warn(f"occam_audit: skipping non-finite entry score={score} actual={actual}", RuntimeWarning, stacklevel=2)
            continue

        mu1 = _m1_predict(score)
        mu2 = _m2_predict(score, decision)

        m1_log_ev += _log_gaussian(actual, mu1)
        m2_log_ev += _log_gaussian(actual, mu2)

    diff = m2_log_ev - m1_log_ev
    # P4B-02 fix: math.exp() overflows at diff > ~709 (OverflowError on large log files).
    # P5B-02 fix: float('inf') is not JSON-serializable (json.dump raises ValueError).
    # Use 1e308 (max finite float) as the sentinel — still > 3.0, serializes cleanly.
    if diff > 700:
        bayes_factor = 1e308
    elif diff < -700:
        bayes_factor = 0.0
    else:
        bayes_factor = math.exp(diff)

    if bayes_factor > 3.0:
        preferred = "M2_jev"
    elif bayes_factor < 1.0 / 3.0:
        preferred = "M1_threshold"
    else:
        preferred = "inconclusive"

    return {
        "m1_log_evidence": m1_log_ev,
        "m2_log_evidence": m2_log_ev,
        "preferred_model": preferred,
        "bayes_factor":    bayes_factor,
    }


# ---------------------------------------------------------------------------
# CLI demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    print("=== Occam Evidence Audit Demo (MacKay ITILA Ch.28) ===\n")

    # Scenario A: Jev model clearly better
    # score=0.4 (below threshold 0.5): M1 predicts DEMOTE (mu=-0.4),
    # Jev correctly says RETAIN (mu=+0.4); actual delta is positive.
    outcomes_jev_wins = []
    for _ in range(30):
        outcomes_jev_wins.append({
            "score": 0.4,
            "decision": "RETAIN",       # Jev correctly retains
            "actual_quality_delta": 0.4, # confirms RETAIN was right
        })

    result_a = occam_evidence_audit(outcomes_jev_wins)
    print("Scenario A – Jev model clearly better:")
    print(f"  m1_log_evidence = {result_a['m1_log_evidence']:.4f}")
    print(f"  m2_log_evidence = {result_a['m2_log_evidence']:.4f}")
    print(f"  bayes_factor    = {result_a['bayes_factor']:.4f}")
    print(f"  preferred_model = {result_a['preferred_model']}")

    # Scenario B: threshold model better (Jev deviates from quality)
    outcomes_threshold_wins = []
    for i in range(20):
        score = 0.3 + (i % 2) * 0.5
        # Threshold correct (retain>0.5 matches quality)
        threshold_correct_retain = score > 0.5
        # Jev randomly wrong
        decision = "DEMOTE" if threshold_correct_retain else "RETAIN"
        actual_delta = 0.5 if threshold_correct_retain else -0.5
        outcomes_threshold_wins.append({
            "score": score,
            "decision": decision,
            "actual_quality_delta": actual_delta,
        })

    result_b = occam_evidence_audit(outcomes_threshold_wins)
    print("\nScenario B – Threshold model better:")
    print(f"  m1_log_evidence = {result_b['m1_log_evidence']:.4f}")
    print(f"  m2_log_evidence = {result_b['m2_log_evidence']:.4f}")
    print(f"  bayes_factor    = {result_b['bayes_factor']:.4f}")
    print(f"  preferred_model = {result_b['preferred_model']}")

    # Scenario C: empty outcomes
    result_c = occam_evidence_audit([])
    print(f"\nScenario C – empty outcomes:")
    print(f"  preferred_model = {result_c['preferred_model']}")
    assert result_c["preferred_model"] == "inconclusive"

    # Assertions
    assert result_a["preferred_model"] == "M2_jev", (
        f"Expected M2_jev for scenario A, got {result_a['preferred_model']}"
    )
    assert result_b["preferred_model"] == "M1_threshold", (
        f"Expected M1_threshold for scenario B, got {result_b['preferred_model']}"
    )

    print("\nAll assertions passed. Exit 0.")


if __name__ == "__main__":
    if "--demo" in sys.argv:
        _demo()
        sys.exit(0)
    print("Usage: python occam_audit.py --demo")
    sys.exit(1)
