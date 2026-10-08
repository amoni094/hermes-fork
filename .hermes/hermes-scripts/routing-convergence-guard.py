#!/usr/bin/env python3
"""
routing-convergence-guard.py — VIL-2 + VIL-7
JKO-inspired iterative skill distribution update.

Algorithm:
  Start with uniform p over all skills.
  Each JKO step:
    (a) KL gradient step toward skill_prior: p ← p * skill_prior / Z
    (b) W1 projection step: build pairwise cost matrix for skills,
        run sinkhorn() to project p onto the simplex neighboured by prior.
  Stop when span(p_new - p_old) < 0.01 or after 20 iterations.

Subcommands:
  flow <query>     Run JKO flow from uniform to converged routing distribution.
                   Output convergence trajectory: iter, top-3 skills, W1 to prev step.
  jko-step <query> Single JKO proximal step for a given query; output top-5.

Usage:
  python routing-convergence-guard.py flow 'memory consolidation'
  python routing-convergence-guard.py jko-step 'memory consolidation'
"""

import sys
import os
import re
import argparse
from pathlib import Path

# ── Path setup ────────────────────────────────────────────────────────────────
SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))
from ot_utils import build_tf, w1_distance, sinkhorn  # noqa: E402

import numpy as np

HERMES_HOME = Path.home() / ".hermes"
DEFAULT_SKILLS_DIR = HERMES_HOME / "skills"
FORK_SKILLS_DIR = HERMES_HOME / "profiles" / "fork" / "skills"

MAX_ITER = 20
CONV_SPAN = 0.01
SINKHORN_REG = 0.05


# ── Skill TF loading ──────────────────────────────────────────────────────────

def _load_skill_tfs() -> dict[str, dict[str, float]]:
    """Load all SKILL.md files; return {skill_name: tf_dict}."""
    seen: dict[str, dict[str, float]] = {}
    for root in (DEFAULT_SKILLS_DIR, FORK_SKILLS_DIR):
        if not root.is_dir():
            continue
        for skill_md in root.rglob("SKILL.md"):
            if ".archive" in skill_md.parts:
                continue
            name = skill_md.parent.name
            try:
                text = skill_md.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            tf = build_tf(text)
            if tf:
                seen[name] = tf
    return seen


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z]{2,}", text.lower())


# ── Skill prior ───────────────────────────────────────────────────────────────

def _build_skill_prior(query_tf: dict[str, float], skill_tfs: dict[str, dict]) -> np.ndarray:
    """Build skill_prior vector: cosine-like overlap between query and each skill's TF.

    prior[k] = sum_{token} min(query_tf[token], skill_tf[token]) / Z
    This is the histogram intersection kernel — positive, sums to 1 after norm.
    Falls back to uniform if all zeros.
    """
    names = list(skill_tfs.keys())
    N = len(names)
    # Normalise query TF
    q_total = sum(query_tf.values()) or 1.0
    q_norm = {t: v / q_total for t, v in query_tf.items()}

    scores = np.zeros(N, dtype=np.float64)
    for i, name in enumerate(names):
        sk = skill_tfs[name]
        sk_total = sum(sk.values()) or 1.0
        sk_norm = {t: v / sk_total for t, v in sk.items()}
        overlap = sum(
            min(q_norm.get(t, 0.0), sk_norm.get(t, 0.0))
            for t in set(q_norm) | set(sk_norm)
        )
        scores[i] = max(overlap, 1e-12)

    total = scores.sum()
    if total <= 0:
        scores = np.ones(N) / N
    else:
        scores /= total
    return scores


# ── JKO step ──────────────────────────────────────────────────────────────────

def _w1_to_prior(p: np.ndarray, skill_prior: np.ndarray, reg: float = SINKHORN_REG) -> float:
    """Approximate W1 from current distribution p to skill_prior on the N-simplex.

    Since skills are discrete tokens (no metric between them), we use the
    L1 cost matrix: C[i,j] = |i-j|/(N-1) to give a graded cost.
    """
    N = len(p)
    if N < 2:
        return 0.0
    # Build cost matrix: C[i,j] = |i - j| / (N-1)
    idx = np.arange(N, dtype=np.float64)
    C = np.abs(idx[:, None] - idx[None, :]) / max(N - 1, 1)
    _, cost = sinkhorn(p, skill_prior, C, reg=reg, max_iter=100)
    return float(cost)


def _jko_step(p: np.ndarray, skill_prior: np.ndarray) -> np.ndarray:
    """One JKO proximal step:
      (a) KL gradient step: p *= skill_prior / Z
      (b) W1 projection: renormalise via sinkhorn marginal.
    """
    # (a) KL gradient step toward prior: multiply elementwise
    p_new = p * skill_prior
    z = p_new.sum()
    if z <= 0:
        p_new = skill_prior.copy()
    else:
        p_new /= z

    # (b) W1 projection: run sinkhorn between p_new and skill_prior;
    #     take the target marginal of the transport plan as the new distribution.
    N = len(p_new)
    if N >= 2:
        idx = np.arange(N, dtype=np.float64)
        C = np.abs(idx[:, None] - idx[None, :]) / max(N - 1, 1)
        P_plan, _ = sinkhorn(p_new, skill_prior, C, reg=SINKHORN_REG, max_iter=100)
        # Source marginal of plan (row sums) is our projected distribution
        projected = P_plan.sum(axis=1)
        projected = np.maximum(projected, 1e-300)
        projected /= projected.sum()
        p_new = projected

    return p_new


# ── flow ──────────────────────────────────────────────────────────────────────

def cmd_flow(query: str) -> None:
    """Run JKO flow from uniform to converged; output trajectory."""
    print(f"\n[routing-convergence-guard] JKO flow for query: '{query}'\n")

    skill_tfs = _load_skill_tfs()
    names = list(skill_tfs.keys())
    N = len(names)
    if N == 0:
        print("[flow] No skills found.", file=sys.stderr)
        sys.exit(1)

    query_tf = build_tf(query)
    if not query_tf:
        # If no meaningful tokens, use uniform prior
        skill_prior = np.ones(N) / N
    else:
        skill_prior = _build_skill_prior(query_tf, skill_tfs)

    # Start from uniform
    p = np.ones(N, dtype=np.float64) / N
    p_old = p.copy()

    print(f"  Skills loaded: {N}")
    print(f"  Stopping: span(p_new - p_old) < {CONV_SPAN} or {MAX_ITER} iterations\n")
    print(f"  {'Iter':>4}  {'Top-3 skills':<70}  {'W1-to-prev':>12}")
    print(f"  {'----':>4}  {'-'*70}  {'----------':>12}")

    for iteration in range(1, MAX_ITER + 1):
        p_new = _jko_step(p, skill_prior)

        # W1 from p_old to p_new
        w1_prev = _w1_to_prior(p_old, p_new)

        # Top-3
        top3_idx = np.argsort(p_new)[-3:][::-1]
        top3 = [(names[i], p_new[i]) for i in top3_idx]
        top3_str = "  ".join(f"{n}({v:.4f})" for n, v in top3)

        print(f"  {iteration:>4}  {top3_str:<70}  {w1_prev:>12.6f}")

        # Convergence check
        span = float(np.max(p_new - p_old) - np.min(p_new - p_old))
        p_old = p.copy()
        p = p_new

        if span < CONV_SPAN:
            print(f"\n  [Converged at iteration {iteration}: span={span:.6f} < {CONV_SPAN}]")
            break
    else:
        print(f"\n  [Stopped at max_iter={MAX_ITER}]")

    # Final distribution top-10
    top10_idx = np.argsort(p)[-10:][::-1]
    print("\n  === Final Routing Distribution (top-10) ===")
    for rank, i in enumerate(top10_idx, 1):
        print(f"  {rank:>3}. {names[i]:<50s}  p = {p[i]:.6f}")
    print()


# ── jko-step ──────────────────────────────────────────────────────────────────

def cmd_jko_step(query: str) -> None:
    """Single JKO step for a query; output top-5 distribution."""
    skill_tfs = _load_skill_tfs()
    names = list(skill_tfs.keys())
    N = len(names)
    if N == 0:
        print("[jko-step] No skills found.", file=sys.stderr)
        sys.exit(1)

    query_tf = build_tf(query)
    skill_prior = _build_skill_prior(query_tf, skill_tfs) if query_tf else np.ones(N) / N

    p0 = np.ones(N, dtype=np.float64) / N
    p1 = _jko_step(p0, skill_prior)

    top5_idx = np.argsort(p1)[-5:][::-1]
    print(f"\n=== Single JKO Step — query: '{query}' ===")
    print(f"  Uniform start → 1 JKO step (top-5 skills):\n")
    for rank, i in enumerate(top5_idx, 1):
        print(f"  {rank}. {names[i]:<50s}  p = {p1[i]:.6f}")
    print()


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="routing-convergence-guard.py",
        description="JKO-inspired iterative skill routing distribution (VIL-2, VIL-7)",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_flow = sub.add_parser("flow", help="Run JKO flow from uniform to convergence")
    p_flow.add_argument("query", help="Query string to route")

    p_jko = sub.add_parser("jko-step", help="Single JKO proximal step")
    p_jko.add_argument("query", help="Query string to route")

    args = parser.parse_args()

    if args.cmd == "flow":
        cmd_flow(args.query)
    elif args.cmd == "jko-step":
        cmd_jko_step(args.query)


if __name__ == "__main__":
    main()
