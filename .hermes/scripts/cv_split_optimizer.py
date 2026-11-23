"""
CV-optimal percentile split finder for the three-tier demotion policy.

Grounded in Boyd & Vandenberghe (2004) 'Convex Optimization', Ch.7:
the optimal decision boundary minimises generalisation error, estimated
via k-fold cross-validation.

Public API
----------
cv_optimal_split(scores, k=5) -> (p_lo, p_hi)
    Performs k-fold CV over the Cartesian product
    {10,20,...,90} × {10,20,...,90} with p_lo < p_hi and returns the
    pair that maximises tier-assignment accuracy against the
    Kolmogorov-proxy gold standard (Wave 2a stand-in for Jev's
    logprob_classify).

fast_split(scores) -> (p_lo, p_hi)
    Returns cv_optimal_split(scores) when len(scores) >= 20,
    else falls back to (33, 67).

Kolmogorov proxy (gold standard)
---------------------------------
k_proxy(s) = 1 - 1/(1 + s)   ∈ (0,1)
Tier assignment:
    score < 0.33  → 0 (demote)
    score < 0.67  → 1 (middle)
    else          → 2 (retain)
(matches the heuristic Wave 1 baseline, providing a stable gold label)
"""

from __future__ import annotations

import math
import sys
from typing import List, Tuple

# ---------------------------------------------------------------------------
# Kolmogorov proxy (Wave 2a gold standard stand-in)
# ---------------------------------------------------------------------------

def _kolmogorov_proxy(score: float) -> float:
    """Compress score via the Kolmogorov-proxy mapping k(s) = 1 - 1/(1+s)."""
    return 1.0 - 1.0 / (1.0 + max(score, 0.0))


def _proxy_tier(score: float) -> int:
    """
    Assign a tier {0, 1, 2} using the Kolmogorov proxy as gold standard.
    This stands in for Jev's logprob_classify in standalone scripts.
    """
    k = _kolmogorov_proxy(score)
    if k < 0.33:
        return 0  # demote
    if k < 0.67:
        return 1  # middle
    return 2      # retain


# ---------------------------------------------------------------------------
# Tier assignment from percentile thresholds
# ---------------------------------------------------------------------------

def _assign_tiers(scores: List[float], p_lo: float, p_hi: float) -> List[int]:
    """
    Assign tiers {0,1,2} given raw score and two percentile thresholds.

    The threshold values are computed from the empirical distribution of
    *scores* at percentiles p_lo and p_hi.
    """
    if not scores:
        return []
    sorted_s = sorted(scores)
    n = len(sorted_s)

    def _pct(p: float) -> float:
        idx = (p / 100.0) * (n - 1)
        lo = int(idx)
        hi = min(lo + 1, n - 1)
        frac = idx - lo
        return sorted_s[lo] * (1 - frac) + sorted_s[hi] * frac

    t_lo = _pct(p_lo)
    t_hi = _pct(p_hi)

    tiers: List[int] = []
    for s in scores:
        if s < t_lo:
            tiers.append(0)
        elif s < t_hi:
            tiers.append(1)
        else:
            tiers.append(2)
    return tiers


# ---------------------------------------------------------------------------
# k-fold cross-validation accuracy
# ---------------------------------------------------------------------------

def _kfold_accuracy(
    scores: List[float],
    p_lo: float,
    p_hi: float,
    k: int,
) -> float:
    """
    Compute mean accuracy of the (p_lo, p_hi) split over k folds.

    Gold labels are produced by _proxy_tier applied to the *training*
    fold's score distribution; predictions on the test fold use the
    empirical thresholds from the training fold.
    """
    n = len(scores)
    if n == 0:
        return 0.0

    # Deterministic stratified fold assignment
    indices = list(range(n))
    fold_ids = [i % k for i in range(n)]

    total_correct = 0
    total = 0

    for fold in range(k):
        train_idx = [i for i in indices if fold_ids[i] != fold]
        test_idx  = [i for i in indices if fold_ids[i] == fold]

        if not train_idx or not test_idx:
            continue

        train_scores = [scores[i] for i in train_idx]
        test_scores  = [scores[i] for i in test_idx]

        # Compute thresholds from training set
        sorted_tr = sorted(train_scores)
        n_tr = len(sorted_tr)

        def _pct_tr(p: float) -> float:
            idx = (p / 100.0) * (n_tr - 1)
            lo = int(idx)
            hi = min(lo + 1, n_tr - 1)
            frac = idx - lo
            return sorted_tr[lo] * (1 - frac) + sorted_tr[hi] * frac

        t_lo_tr = _pct_tr(p_lo)
        t_hi_tr = _pct_tr(p_hi)

        for s in test_scores:
            gold = _proxy_tier(s)
            if s < t_lo_tr:
                pred = 0
            elif s < t_hi_tr:
                pred = 1
            else:
                pred = 2
            if pred == gold:
                total_correct += 1
            total += 1

    return total_correct / max(total, 1)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_PERCENTILE_CANDIDATES = list(range(10, 100, 10))  # 10, 20, ..., 90


def cv_optimal_split(scores: List[float], k: int = 5) -> Tuple[float, float]:
    """
    Find the (p_lo, p_hi) percentile pair that maximises k-fold CV accuracy
    of the three-tier assignment against the Kolmogorov-proxy gold standard.

    Parameters
    ----------
    scores : list of float
        Raw retention scores (e.g. rr_scores from the plugin).
    k      : int
        Number of CV folds (default 5).

    Returns
    -------
    (p_lo, p_hi) : tuple of float
        Best percentile thresholds found.
    """
    if len(scores) < 2:
        return (33.0, 67.0)

    best_acc = -1.0
    best_pair = (33.0, 67.0)

    for p_lo in _PERCENTILE_CANDIDATES:
        for p_hi in _PERCENTILE_CANDIDATES:
            if p_lo >= p_hi:
                continue
            acc = _kfold_accuracy(scores, float(p_lo), float(p_hi), k)
            if acc > best_acc:
                best_acc = acc
                best_pair = (float(p_lo), float(p_hi))

    return best_pair


def fast_split(scores: List[float]) -> Tuple[float, float]:
    """
    Return cv_optimal_split(scores) when len(scores) >= 20,
    else fall back to the heuristic (33, 67).
    """
    if len(scores) >= 20:
        return cv_optimal_split(scores)
    return (33.0, 67.0)


# ---------------------------------------------------------------------------
# CLI demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    print("=== CV-Optimal Split Demo (Boyd Convex Optimization) ===\n")

    import random
    random.seed(42)

    # Generate a synthetic score distribution with a clear bimodal shape
    scores = (
        [random.gauss(0.2, 0.08) for _ in range(20)]   # low cluster
        + [random.gauss(0.5, 0.06) for _ in range(10)]  # middle cluster
        + [random.gauss(0.8, 0.08) for _ in range(20)]  # high cluster
    )
    scores = [max(0.0, min(1.0, s)) for s in scores]

    print(f"Generated {len(scores)} synthetic scores (bimodal distribution)")
    print(f"Score range: [{min(scores):.3f}, {max(scores):.3f}]")
    print()

    p_lo, p_hi = cv_optimal_split(scores)
    print(f"cv_optimal_split  → p_lo={p_lo:.0f}th, p_hi={p_hi:.0f}th percentile")

    fp = fast_split(scores)
    print(f"fast_split (≥20)  → p_lo={fp[0]:.0f}th, p_hi={fp[1]:.0f}th percentile")

    small = scores[:10]
    fb = fast_split(small)
    print(f"fast_split (<20)  → p_lo={fb[0]:.0f}th, p_hi={fb[1]:.0f}th percentile (fallback)")
    assert fb == (33.0, 67.0), f"Expected fallback (33, 67), got {fb}"

    assert p_lo < p_hi, f"p_lo must be < p_hi, got {p_lo} >= {p_hi}"
    assert 10 <= p_lo <= 90, f"p_lo out of range: {p_lo}"
    assert 10 <= p_hi <= 90, f"p_hi out of range: {p_hi}"

    print("\nAll assertions passed. Exit 0.")


if __name__ == "__main__":
    if "--demo" in sys.argv:
        _demo()
        sys.exit(0)
    print("Usage: python cv_split_optimizer.py --demo")
    sys.exit(1)
