#!/usr/bin/env python3
"""ESL-5: nonnegative stacking weights on LOO skill predictions.

Usage:
  python3 skill-stacking.py --predictions '{"skill_a":[0.8,0.6,0.9,0.4,0.7],"skill_b":[0.7,0.8,0.6,0.9,0.5]}' --outcomes '[1,0,1,1,0]'

OT-12 Bregman barycenter (--ot-stack):
  python3 skill-stacking.py --predictions '...' --outcomes '[...]' --ot-stack
  python3 skill-stacking.py --ot-stack  (standalone, uses built-in demo skills)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def mse(pred, y):
    return sum((a - b) ** 2 for a, b in zip(pred, y)) / len(y)


def fallback_weights(preds, y):
    skills = list(preds)
    raw = {s: 1.0 / (mse(preds[s], y) + 0.01) for s in skills}
    total = sum(raw.values()) or 1.0
    return {s: raw[s] / total for s in skills}


def scipy_weights(preds, y):
    import numpy as np
    from scipy.optimize import minimize

    skills = list(preds)
    P = np.column_stack([preds[s] for s in skills])
    yy = np.asarray(y, dtype=float)
    k = len(skills)

    def loss(w):
        return float(np.mean((yy - P @ w) ** 2))

    cons = {"type": "eq", "fun": lambda w: float(np.sum(w) - 1.0)}
    res = minimize(
        loss, np.ones(k) / k, bounds=[(0.0, 1.0)] * k,
        constraints=cons, method="SLSQP",
    )
    w = np.clip(res.x, 0.0, 1.0)
    w = w / w.sum() if w.sum() else np.ones(k) / k
    return {s: float(w[i]) for i, s in enumerate(skills)}


def stack(preds, y):
    skills = list(preds)
    n = len(y)
    if n == 0 or not skills:
        raise SystemExit("empty predictions/outcomes")
    if any(len(preds[s]) != n for s in skills):
        raise SystemExit("prediction length mismatch")
    try:
        weights = scipy_weights(preds, y)
    except Exception:
        weights = fallback_weights(preds, y)
    stacked = [sum(weights[s] * preds[s][i] for s in skills) for i in range(n)]
    sl = mse(stacked, y)
    best = min(mse(preds[s], y) for s in skills)
    uni = [sum(preds[s][i] for s in skills) / len(skills) for i in range(n)]
    return {
        "weights": weights,
        "stacked_predictions": stacked,
        "stacked_loss": sl,
        "vs_best_single": sl - best,
        "vs_uniform": sl - mse(uni, y),
    }


# --------------------------------------------------------------------------- #
# OT-12: Bregman / Sinkhorn barycenter over skill TF vectors
# --------------------------------------------------------------------------- #

# Built-in demo skill texts used when --ot-stack is run standalone
_DEMO_SKILLS = {
    "semantic-search": (
        "semantic search retrieval query embedding vector similarity cosine "
        "distance recall precision index lookup nearest neighbour dense sparse"
    ),
    "temporal-routing": (
        "temporal time date timestamp history timeline recent latest earliest "
        "before after since until session memory query routing retrieval"
    ),
    "graph-memory": (
        "graph node edge entity relationship traversal knowledge facts memory "
        "graphiti relational association connection link parent child belongs"
    ),
    "skill-stacking": (
        "skill stacking ensemble prediction weight loss optimise nonnegative "
        "constrained convex scipy barycenter transport marginal distribution"
    ),
    "optimal-transport": (
        "optimal transport sinkhorn wasserstein barycenter marginal distribution "
        "cost matrix earth mover distance regularisation entropic plan"
    ),
}


def compute_ot_barycenter(skill_texts: dict[str, str]) -> dict:
    """Compute iterative Sinkhorn barycenter over skill TF vectors.

    Algorithm (OT-12 / Bregman fixed-point):
      1. Build TF dict for each skill.
      2. Project all TFs onto a shared vocabulary.
      3. Initialise barycenter b = uniform average of all TF vecs.
      4. For 5 iterations:
           for each skill TF vec p_k:
               build pairwise cost C on union vocab of (b_dict, p_k_dict)
               P_k, _ = sinkhorn(b_marginal, p_k_marginal, C, reg=0.05)
               collect T_k = P_k
           b = normalised(sum_k T_k.sum(axis=1))
      5. Return top-20 tokens by barycenter weight.
    """
    import numpy as np
    import ot_utils

    skills = list(skill_texts)
    if not skills:
        return {"error": "no skills provided"}

    # Build TF dicts
    tf_dicts: dict[str, dict[str, float]] = {
        s: ot_utils.build_tf(skill_texts[s]) for s in skills
    }

    # Build shared vocabulary (union of all skill TF dicts)
    vocab = sorted(set().union(*[set(tf) for tf in tf_dicts.values()]))
    V = len(vocab)
    if V == 0:
        return {"error": "empty vocabulary"}

    # Project each TF dict onto the shared vocab
    def to_vec(tf: dict[str, float]) -> np.ndarray:
        v = np.array([tf.get(t, 0.0) for t in vocab], dtype=np.float64)
        s = v.sum()
        return v / s if s > 0 else np.ones(V) / V

    tf_vecs: list[np.ndarray] = [to_vec(tf_dicts[s]) for s in skills]

    # Binary cost matrix on shared vocab: C[i,j] = 0 if i==j else 1
    C = 1.0 - np.eye(V, dtype=np.float64)

    # Initialise barycenter as uniform average
    b = np.mean(tf_vecs, axis=0)
    b_sum = b.sum()
    b = b / b_sum if b_sum > 0 else np.ones(V) / V

    # Iterative Bregman fixed-point (5 iterations)
    for _iter in range(5):
        transport_row_sums: list[np.ndarray] = []
        for p_k in tf_vecs:
            T_k, _ = ot_utils.sinkhorn(b, p_k, C, reg=0.05)
            transport_row_sums.append(T_k.sum(axis=1))
        b_new = np.sum(transport_row_sums, axis=0)
        b_total = b_new.sum()
        b = b_new / b_total if b_total > 0 else np.ones(V) / V

    # Top-20 tokens by barycenter weight
    top_idx = np.argsort(b)[::-1][:20]
    top_tokens = [{"token": vocab[i], "weight": float(b[i])} for i in top_idx]

    return {
        "n_skills": len(skills),
        "vocab_size": V,
        "iterations": 5,
        "top_20_tokens": top_tokens,
    }


def main():
    p = argparse.ArgumentParser(
        description="Skill stacking (ESL-5) with optional OT-12 Bregman barycenter."
    )
    p.add_argument("--predictions", help="JSON dict of skill→prediction list")
    p.add_argument("--outcomes", help="JSON list of ground-truth outcomes")
    p.add_argument(
        "--ot-stack",
        action="store_true",
        help="Compute OT-12 Sinkhorn barycenter over skill TF vectors",
    )
    a = p.parse_args()

    result: dict = {}

    # Standard stacking (requires --predictions and --outcomes)
    if a.predictions or a.outcomes:
        if not (a.predictions and a.outcomes):
            p.error("--predictions and --outcomes must be provided together")
        preds = json.loads(a.predictions)
        y = [float(v) for v in json.loads(a.outcomes)]
        result = stack(preds, y)

    # OT-12: Bregman barycenter
    if a.ot_stack:
        # Use skill names from --predictions keys as skill texts (if provided),
        # otherwise fall back to built-in demo skill descriptions.
        if a.predictions:
            preds_dict = json.loads(a.predictions)
            skill_texts = {s: s.replace("-", " ").replace("_", " ") for s in preds_dict}
        else:
            skill_texts = _DEMO_SKILLS

        barycenter_result = compute_ot_barycenter(skill_texts)
        result["ot_stack_barycenter"] = barycenter_result

    if not result:
        p.print_help()
        sys.exit(1)

    json.dump(result, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
