#!/usr/bin/env python3
"""
ot_utils.py — Shared Optimal Transport utility for Hermes scripts.

Provides:
  sinkhorn(a, b, C, reg=0.05, max_iter=100) -> (P, cost)
  tf_to_vec(tf_dict_a, tf_dict_b) -> (a, b, C)
  w1_distance(tf_a, tf_b) -> float

Used by: skill_prune_audit.py (OT-4), rr_compaction_spike.py (OT-9),
         hermes-memory-drift-audit.py (OT-11), skill-yield-tracker.py (OT-14).
"""

import re
from typing import Dict, Tuple

import numpy as np


def sinkhorn(
    a: np.ndarray,
    b: np.ndarray,
    C: np.ndarray,
    reg: float = 0.05,
    max_iter: int = 100,
) -> Tuple[np.ndarray, float]:
    """Sinkhorn–Knopp regularised optimal transport.

    Parameters
    ----------
    a : 1-D array, shape (m,)  — source marginal (must sum to 1)
    b : 1-D array, shape (n,)  — target marginal (must sum to 1)
    C : 2-D array, shape (m,n) — cost matrix
    reg : float                — entropic regularisation parameter (ε)
    max_iter : int             — maximum Sinkhorn iterations

    Returns
    -------
    P    : optimal transport plan, shape (m, n)
    cost : scalar transport cost  sum(P * C)
    """
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    C = np.asarray(C, dtype=np.float64)

    # Normalise marginals (guard against floating-point sum != 1)
    a = a / a.sum()
    b = b / b.sum()

    # Gibbs kernel
    K = np.exp(-C / reg)

    # Initialise scaling vectors
    u = np.ones_like(a)
    v = np.ones_like(b)

    for _ in range(max_iter):
        v = b / (K.T @ u + 1e-300)
        u = a / (K @ v + 1e-300)

    P = np.diag(u) @ K @ np.diag(v)
    cost = float(np.sum(P * C))
    return P, cost


def tf_to_vec(
    tf_dict_a: Dict[str, float],
    tf_dict_b: Dict[str, float],
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Convert two TF token dicts to Sinkhorn-ready (a, b, C).

    Marginals are normalised frequency vectors over the union vocabulary.
    Cost matrix: C[i,j] = 0 if token_i == token_j, else 1  (binary / Hamming).

    Returns
    -------
    a : marginal for tf_dict_a, shape (V,)
    b : marginal for tf_dict_b, shape (V,)
    C : binary cost matrix, shape (V, V)
    """
    vocab = sorted(set(tf_dict_a) | set(tf_dict_b))
    if not vocab:
        # Degenerate case — return trivial 1×1 problem
        return np.array([1.0]), np.array([1.0]), np.array([[0.0]])

    V = len(vocab)
    a = np.array([tf_dict_a.get(t, 0.0) for t in vocab], dtype=np.float64)
    b = np.array([tf_dict_b.get(t, 0.0) for t in vocab], dtype=np.float64)

    # Normalise (avoid zero-sum)
    a_sum = a.sum()
    b_sum = b.sum()
    a = a / a_sum if a_sum > 0 else np.ones(V) / V
    b = b / b_sum if b_sum > 0 else np.ones(V) / V

    # Binary cost: 0 on diagonal, 1 elsewhere
    C = 1.0 - np.eye(V, dtype=np.float64)

    return a, b, C


def build_tf(text: str) -> Dict[str, float]:
    """Build a term-frequency dict from raw text.

    Tokens: lower-cased alpha sequences of length >= 2.
    Values: raw counts (caller may normalise if desired).
    """
    tokens = re.findall(r"[a-z]{2,}", text.lower())
    tf: Dict[str, float] = {}
    for t in tokens:
        tf[t] = tf.get(t, 0.0) + 1.0
    return tf


def w1_distance(tf_a: Dict[str, float], tf_b: Dict[str, float], reg: float = 0.05) -> float:
    """Approximate W1 (earth-mover) distance between two TF histograms.

    Uses Sinkhorn with a binary cost matrix.  Lower = better vocabulary match.

    Parameters
    ----------
    tf_a, tf_b : token-frequency dicts (raw counts; normalised internally)
    reg        : Sinkhorn entropic regularisation (default 0.05)

    Returns
    -------
    float in [0, 1]  — 0 means identical vocabulary distribution, 1 means
                        completely disjoint with maximum transport cost.
    """
    a, b, C = tf_to_vec(tf_a, tf_b)
    _, cost = sinkhorn(a, b, C, reg=reg, max_iter=100)
    return float(cost)
