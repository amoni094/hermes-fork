#!/usr/bin/env python3
"""
proper_scoring.py — Calibration predicates grounded in formal scoring-rule theory.

Theoretical basis:
  - Jaynes, Probability Theory: The Logic of Science, Ch.13 (honest weatherman):
      A probability announcement q is calibrated iff it maximises expected score
      under the log-scoring rule. The unique optimal q = p (true probability).
      Any q ≠ p loses expected score. Calibration is NOT a lookup table.

  - Savage (1971), "Elicitation of Personal Probabilities and Expectations":
      A scoring rule S(q, y) is STRICTLY PROPER iff E_p[S(q,y)] is uniquely
      maximised at q = p. Log-loss and Brier score are both strictly proper.

  - Gelman et al., BDA3, §2.4 (Beta-Binomial conjugate):
      After k agreements in n trials with Beta(α, β) prior:
        posterior mean = (α + k) / (α + β + n)
      This is the correct calibrated probability for small N, NOT a lookup table.
      The lookup table (3/3→1.0) violates BDA3: it assigns probability 1 to a
      hypothesis with only 3 confirmations — infinite evidence claim.

  - Niculescu-Mizil & Caruana (2005), "Predicting good probabilities with
    supervised learning": isotonic regression is the non-parametric calibrator
    that minimises Brier score without assuming a functional form.

  - Platt (1999): sigmoid calibration — parametric alternative; better for
    SVM-style monotone miscalibration, worse for non-monotone.

All functions are stdlib-only. No numpy/scipy (use the pure-Python fallbacks).

Usage:
    from proper_scoring import (
        beta_binomial_confidence,   # BDA3 posterior mean — replaces lookup table
        brier_score,                # Brier 1950 strictly proper scoring rule
        log_loss,                   # log-scoring rule (Jaynes Ch.13)
        is_calibrated,              # predicate: empirically calibrated?
        isotonic_calibrate,         # fit isotonic calibrator from (p, outcome) pairs
        apply_calibrator,           # apply fitted calibrator to new p
    )
"""
from __future__ import annotations

import math
import statistics
from typing import Sequence


# ── 1. Beta-Binomial posterior mean (BDA3 §2.4) ──────────────────────────────

def beta_binomial_confidence(
    agreements: int,
    total: int,
    *,
    prior_alpha: float = 1.0,
    prior_beta: float = 1.0,
) -> float:
    """
    Calibrated confidence from k agreements in n trials via Beta-Binomial model.

    Replaces the heuristic lookup table (3/3→1.0, 2/3→0.5, ...) used in
    consistency_scorer.py. The lookup table is NOT probability-theoretically
    derived and assigns confidence=1.0 to 3/3 agreements — which implies
    certainty from 3 trials (BDA3 §2.4 violation).

    Theorem (BDA3 §2.4): with Beta(α, β) prior over p, observing k successes
    in n trials gives posterior Beta(α+k, β+n-k), with posterior mean:
        E[p | k, n] = (α + k) / (α + β + n)

    Default prior: Beta(1,1) = uniform (principle of indifference, Jaynes Ch.6).
    The Jeffreys prior Beta(0.5, 0.5) is also defensible for binomial estimation
    (invariant under reparametrization, Ch.12), and gives slightly lower
    confidence for 3/3 (0.857 vs 0.800 with uniform).

    Examples (uniform prior):
        beta_binomial_confidence(3, 3) → 0.800   (not 1.0)
        beta_binomial_confidence(2, 3) → 0.600   (not 0.5)
        beta_binomial_confidence(1, 3) → 0.400   (not 0.2)
        beta_binomial_confidence(0, 3) → 0.200   (not 0.05)

    Args:
        agreements: number of verify_fn calls that returned True
        total:      total verify_fn calls made (including failures)
        prior_alpha: Beta prior α parameter (default 1.0 = uniform)
        prior_beta:  Beta prior β parameter (default 1.0 = uniform)

    Returns:
        Posterior mean ∈ (0, 1), strictly inside open interval.
    """
    if total < 0:
        raise ValueError(f"total must be >= 0, got {total}")
    k = max(0, min(agreements, total))  # clamp to [0, total]
    alpha_post = prior_alpha + k
    beta_post = prior_beta + (total - k)
    return alpha_post / (alpha_post + beta_post)


# ── 2. Strictly proper scoring rules ─────────────────────────────────────────

def log_loss(p_predicted: float, outcome: int) -> float:
    """
    Log-scoring rule (Jaynes Ch.13 'honest weatherman').

    S_log(q, y) = y * log(q) + (1-y) * log(1-q)

    Strictly proper: E_p[S_log(q,y)] is uniquely maximised at q=p.
    Under log-loss, honesty (reporting q=p) is the Bayes-optimal strategy.

    Args:
        p_predicted: announced probability ∈ (0, 1)
        outcome: 1 if event occurred, 0 otherwise

    Returns:
        Log-score (negative; higher = better; range (-∞, 0])
    """
    eps = 1e-12
    p = max(eps, min(1 - eps, p_predicted))
    if outcome == 1:
        return math.log(p)
    else:
        return math.log(1 - p)


def brier_score(p_predicted: float, outcome: int) -> float:
    """
    Brier (1950) score: mean squared error of probability forecast.

    S_Brier(q, y) = -(q - y)^2

    Strictly proper. Decomposed as:
        Brier = -(calibration + resolution - uncertainty)
    where calibration is the squared gap between announced and empirical.
    Lower MSE = better calibrated.

    Returns negative MSE (higher = better, consistent with log_loss sign).
    """
    return -(p_predicted - outcome) ** 2


def expected_log_loss(p_true: float, p_announced: float) -> float:
    """
    Expected log-loss penalty for announcing q when true probability is p.

    E_p[S_log(p, Y)] - E_p[S_log(q, Y)]
      = p*log(p/q) + (1-p)*log((1-p)/(1-q))
      = KL(Bernoulli(p) || Bernoulli(q))

    This is the KL divergence between the true and announced Bernoullis.
    Always >= 0 (information inequality, Cover-Thomas §2.3).
    Equals 0 iff p = q. This is the formal proof of strict propriety.

    Uses: checking how much log-loss is lost by using a heuristic p_announced
    instead of the true posterior mean.
    """
    eps = 1e-12
    p = max(eps, min(1 - eps, p_true))
    q = max(eps, min(1 - eps, p_announced))
    return p * math.log(p / q) + (1 - p) * math.log((1 - p) / (1 - q))


# ── 3. Calibration predicate ──────────────────────────────────────────────────

def is_calibrated(
    predicted: Sequence[float],
    outcomes: Sequence[int],
    *,
    alpha: float = 0.05,
    n_bins: int = 5,
) -> tuple[bool, float, str]:
    """
    Empirical calibration check: are events tagged with p occurring at rate ≈ p?

    Uses the reliability diagram approach: bin predicted probabilities, check
    whether observed frequency in each bin matches mean prediction.

    Jaynes Ch.13 operational definition: a forecaster is calibrated iff for
    every probability announcement p, the empirical frequency of the event
    is p. This is testable with enough data.

    Hosmer-Lemeshow statistic (chi-squared, df = n_bins - 2):
        HL = Σ_b [ (O_b - E_b)^2 / (n_b * p̄_b * (1-p̄_b)) ]

    We use a simpler max-bin-error test (ECE proxy) suitable for small N:
        ECE = Σ_b (n_b/n) * |acc_b - conf_b|
    Calibrated iff ECE < threshold (default 0.15 for 5 bins, = 3*alpha with alpha=0.05).
    Note: alpha controls the ECE threshold (3*alpha) but this is NOT a proper
    statistical hypothesis test — no chi-squared or HL statistic is computed.
    Use for rough calibration screening only.

    Gelman BDA3 §6.3 caveat: with n < 50 per bin, the chi-squared approximation
    is unreliable. Use posterior predictive checks instead (see gelman-bda3 skill).

    Args:
        predicted: sequence of predicted probabilities
        outcomes:  sequence of binary outcomes (0 or 1)
        alpha:     alpha controls the ECE threshold (threshold = 3*alpha) but this
                   is NOT a proper statistical hypothesis test at level alpha — no
                   chi-squared or HL statistic is computed. Use only for rough
                   calibration screening.
        n_bins:    number of calibration bins

    Returns:
        (is_calibrated, ece, explanation)
    """
    if len(predicted) != len(outcomes):
        raise ValueError("predicted and outcomes must have the same length")
    n = len(predicted)
    if n < 10:
        return True, float("nan"), f"too_few_samples (n={n} < 10); cannot assess calibration"

    # Build bins
    bin_size = 1.0 / n_bins
    bins: list[list[tuple[float, int]]] = [[] for _ in range(n_bins)]
    for p, y in zip(predicted, outcomes):
        idx = min(int(p / bin_size), n_bins - 1)
        bins[idx].append((p, y))

    ece = 0.0
    details = []
    for b, items in enumerate(bins):
        if not items:
            continue
        conf = statistics.mean(p for p, _ in items)
        acc = statistics.mean(y for _, y in items)
        weight = len(items) / n
        gap = abs(acc - conf)
        ece += weight * gap
        details.append(f"bin{b}(n={len(items)}): conf={conf:.2f} acc={acc:.2f} gap={gap:.2f}")

    threshold = 3 * alpha  # ECE threshold: 3x significance level
    calibrated = ece < threshold
    explanation = f"ECE={ece:.3f} threshold={threshold:.3f}; " + "; ".join(details)
    return calibrated, ece, explanation


# ── 4. Isotonic calibration (non-parametric, minimises Brier score) ───────────

def isotonic_calibrate(
    predictions: Sequence[float],
    outcomes: Sequence[int],
) -> list[tuple[float, float]]:
    """
    Fit an isotonic regression calibrator to (prediction, outcome) pairs.

    Isotonic regression finds a non-decreasing step function f such that
    Σ (f(p_i) - y_i)^2 is minimised. This minimises Brier score without
    assuming a parametric form (Niculescu-Mizil & Caruana 2005).

    The result is a list of (threshold, calibrated_p) breakpoints.
    Apply with apply_calibrator().

    Algorithm: Pool Adjacent Violators (PAV) — O(N) stack-based (N05 fix).
    Stdlib only; no numpy.

    Theoretical guarantee: the PAV solution is the unique minimiser of
    Σ (f(p_i) - y_i)^2 subject to f non-decreasing (isotonicity constraint).
    This is a convex QP with closed-form solution via PAV.

    Returns:
        List of (input_threshold, calibrated_output) pairs, sorted ascending.
        Boundaries: first threshold is 0.0, last is 1.0.
    """
    if len(predictions) != len(outcomes):
        raise ValueError("predictions and outcomes must have the same length")
    if not predictions:
        return [(0.0, 0.5), (1.0, 0.5)]
    # P5B-07 fix: degenerate input (all outcomes identical) produces a flat calibrator
    # that maps every input to the single observed value (e.g. all-1.0 → always retain).
    # Return a neutral calibrator instead — the gate has no discriminative information.
    if len(set(outcomes)) < 2:
        return [(0.0, 0.5), (1.0, 0.5)]

    # Sort by prediction
    pairs = sorted(zip(predictions, outcomes), key=lambda x: x[0])
    xs = [p for p, _ in pairs]
    ys = [float(y) for _, y in pairs]

    # N05 fix: stack-based PAV — O(N). Each element pushed/popped once → O(N) total.
    # Replaces the while-changed outer loop (O(N^2) worst case).
    def _pav_stack(y: list[float]) -> list[float]:
        blocks = []  # list of [mean, count]
        for yi in y:
            blocks.append([yi, 1])
            while len(blocks) >= 2 and blocks[-2][0] > blocks[-1][0]:
                # Merge last two blocks (violation of non-decreasing constraint)
                m2, c2 = blocks.pop()
                m1, c1 = blocks.pop()
                merged_mean = (m1 * c1 + m2 * c2) / (c1 + c2)
                blocks.append([merged_mean, c1 + c2])
        result: list[float] = []
        for mean, count in blocks:
            result.extend([mean] * count)
        return result

    calibrated = _pav_stack(ys)

    # Build breakpoint table
    breakpoints: list[tuple[float, float]] = [(0.0, calibrated[0])]
    for x, c in zip(xs, calibrated):
        if not breakpoints or abs(c - breakpoints[-1][1]) > 1e-9:
            breakpoints.append((x, c))
    # W3-F08: append boundary only if not already present (avoids duplicate x=1.0 entry
    # when a training prediction of exactly 1.0 is already in the breakpoints list).
    if not breakpoints or breakpoints[-1][0] < 1.0:
        breakpoints.append((1.0, calibrated[-1]))

    return breakpoints


def apply_calibrator(
    p: float,
    breakpoints: list[tuple[float, float]],
) -> float:
    """
    Apply a fitted isotonic calibrator to a new prediction p.

    Linear interpolation between breakpoints. O(log n) binary search.

    If p is outside the range of fitted predictions, clamps to boundary value.
    This is conservative: extrapolation from isotonic regression is not valid
    (Niculescu-Mizil & Caruana 2005 §4.2).
    """
    if not breakpoints:
        return p
    if p <= breakpoints[0][0]:
        return breakpoints[0][1]
    if p >= breakpoints[-1][0]:
        return breakpoints[-1][1]

    # Binary search for the interval containing p
    lo, hi = 0, len(breakpoints) - 1
    while lo + 1 < hi:
        mid = (lo + hi) // 2
        if breakpoints[mid][0] <= p:
            lo = mid
        else:
            hi = mid

    x0, y0 = breakpoints[lo]
    x1, y1 = breakpoints[hi]
    if abs(x1 - x0) < 1e-12:
        return y0
    # Linear interpolation
    t = (p - x0) / (x1 - x0)
    return y0 + t * (y1 - y0)


# ── 5. CALIBRATION TABLE DEPRECATION ─────────────────────────────────────────
#
# The original consistency_scorer.py lookup table:
#   _CALIBRATION = {0: 0.05, 1: 0.20, 2: 0.50, 3: 1.00}
#
# This violates BDA3 §2.4 because:
#   - 3/3 → 1.0: claims certainty from 3 samples (requires infinite evidence)
#   - 0/3 → 0.05: claims near-impossibility from 3 failures
#   - Values are ad-hoc round numbers, not derivable from any proper scoring rule
#
# Replacement: beta_binomial_confidence(agreements, total)
#   - 3/3 → Beta(4,1) posterior mean = 0.800
#   - 2/3 → Beta(3,2) posterior mean = 0.600
#   - 1/3 → Beta(2,3) posterior mean = 0.400
#   - 0/3 → Beta(1,4) posterior mean = 0.200
#
# The KL divergence penalty (expected_log_loss) for using the old table vs
# the BDA3 posterior (p_true = posterior mean):
#   - 3/3: KL(0.8 || 1.0) = 0.8*log(0.8/1.0) + 0.2*log(0.2/0.0) = ∞  [undefined!]
#   - 0/3: KL(0.2 || 0.05) = 0.2*log(4) + 0.8*log(1.067) ≈ 0.33 nats
#
# The 3/3→1.0 entry is UNDEFINED under log-loss (log(0) = -∞). It is not just
# suboptimal — it is formally incoherent under Jaynes Ch.13.


# ── 6. Diagnostics ────────────────────────────────────────────────────────────

def calibration_gap_table(n: int = 3, prior_alpha: float = 1.0, prior_beta: float = 1.0) -> None:
    """Print comparison: old lookup table vs BDA3 posterior mean."""
    old_table = {0: 0.05, 1: 0.20, 2: 0.50, 3: 1.00}
    print(f"Calibration comparison (n={n}, Beta({prior_alpha},{prior_beta}) prior):")
    print(f"{'agreements':>10}  {'old_table':>10}  {'bda3_post':>10}  {'kl_penalty':>12}")
    for k in range(n + 1):
        bda3 = beta_binomial_confidence(k, n, prior_alpha=prior_alpha, prior_beta=prior_beta)
        old = old_table.get(min(k, 3), 0.05)
        try:
            kl = expected_log_loss(bda3, old)
        except Exception:
            kl = float("inf")
        print(f"{k:>10}  {old:>10.3f}  {bda3:>10.3f}  {kl:>12.4f}")


if __name__ == "__main__":
    calibration_gap_table()
    print()

    # Smoke tests
    assert abs(beta_binomial_confidence(3, 3) - 0.8) < 1e-9, "BDA3 3/3 should be 0.8"
    assert abs(beta_binomial_confidence(0, 3) - 0.2) < 1e-9, "BDA3 0/3 should be 0.2"
    assert log_loss(0.9, 1) > log_loss(0.5, 1), "higher confidence for correct outcome = better score"
    assert brier_score(0.9, 1) > brier_score(0.5, 1), "brier: closer = better"
    assert expected_log_loss(0.5, 0.5) < 1e-12, "KL(p||p) = 0"
    assert expected_log_loss(0.8, 0.5) > 0, "KL(p||q) > 0 for p != q"

    # Isotonic calibration on synthetic data
    import random
    rng = random.Random(42)
    preds = [rng.random() for _ in range(100)]
    outcomes = [1 if rng.random() < p else 0 for p in preds]
    bps = isotonic_calibrate(preds, outcomes)
    cal = apply_calibrator(0.7, bps)
    assert 0.0 <= cal <= 1.0, f"calibrated value out of range: {cal}"

    ok, ece, msg = is_calibrated(preds, outcomes)
    print(f"is_calibrated: {ok}, ECE={ece:.3f}")
    print("proper_scoring.py smoke tests PASSED")
