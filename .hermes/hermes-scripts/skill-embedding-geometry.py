#!/usr/bin/env python3
"""
skill-embedding-geometry.py — VIL-1 + VIL-4
Treats skill TF token histograms as points in a probability simplex and
computes W2 geometry using ot_utils.py.

Subcommands:
  nearest   <skill-name>           Find 5 nearest skills in W2 distance.
  barycenter <skill1> [skill2...]  Iterative Sinkhorn barycenter of TF vectors
                                   (2-4 skills). Output top-20 tokens.
  curvature                        Sample 20 triplets, compute triangle
                                   inequality slack. Top-5 most curved triplets.

Usage:
  python skill-embedding-geometry.py nearest peyre-cuturi-optimal-transport
  python skill-embedding-geometry.py barycenter khalil-nonlinear-systems hatcher-algebraic-topology
  python skill-embedding-geometry.py curvature
"""

import sys
import os
import random
import argparse
from pathlib import Path

# ── Path setup ────────────────────────────────────────────────────────────────
SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))
from ot_utils import build_tf, tf_to_vec, w1_distance, sinkhorn  # noqa: E402

import numpy as np

HERMES_HOME = Path.home() / ".hermes"
DEFAULT_SKILLS_DIR = HERMES_HOME / "skills"
FORK_SKILLS_DIR = HERMES_HOME / "profiles" / "fork" / "skills"


# ── Skill loading ─────────────────────────────────────────────────────────────

def _load_skill_tfs(skills_dir: Path | None = None) -> dict[str, dict[str, float]]:
    """Load all SKILL.md files and build TF dicts.  Returns {name: tf_dict}."""
    roots = []
    if skills_dir is not None:
        roots.append(Path(skills_dir))
    else:
        # Search both default and fork skill trees; deduplicate by name (fork wins)
        for d in (DEFAULT_SKILLS_DIR, FORK_SKILLS_DIR):
            if d.is_dir():
                roots.append(d)

    seen: dict[str, dict[str, float]] = {}
    for root in roots:
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


def _w2_distance(tf_a: dict, tf_b: dict, reg: float = 0.05) -> float:
    """Approximate W2 between two TF dicts using Sinkhorn on squared binary cost."""
    a, b, C = tf_to_vec(tf_a, tf_b)
    # W2 with squared cost → cost matrix C² (binary→binary, so C²==C here)
    C2 = C * C
    _, cost = sinkhorn(a, b, C2, reg=reg, max_iter=100)
    return float(cost)


# ── nearest ───────────────────────────────────────────────────────────────────

def cmd_nearest(skill_name: str, skills_dir=None, top_k: int = 5) -> None:
    """Find top_k nearest skills in W2 distance to the given skill."""
    tfs = _load_skill_tfs(skills_dir)

    # Resolve skill name (exact, then fuzzy)
    if skill_name not in tfs:
        candidates = [k for k in tfs if skill_name in k]
        if candidates:
            skill_name = candidates[0]
            print(f"[nearest] Resolved to: {skill_name}", file=sys.stderr)
        else:
            print(f"[nearest] Skill '{skill_name}' not found.", file=sys.stderr)
            print(f"  Available ({len(tfs)}): {', '.join(sorted(tfs)[:10])} ...", file=sys.stderr)
            sys.exit(1)

    query_tf = tfs[skill_name]
    others = {k: v for k, v in tfs.items() if k != skill_name}

    distances = []
    for name, tf in others.items():
        d = _w2_distance(query_tf, tf)
        distances.append((d, name))

    distances.sort()
    nearest = distances[:top_k]

    print(f"\n=== W2 Nearest Skills to '{skill_name}' ===")
    for rank, (dist, name) in enumerate(nearest, 1):
        print(f"  {rank}. {name:<50s}  W2 = {dist:.6f}")
    print()


# ── barycenter ────────────────────────────────────────────────────────────────

def _iterative_barycenter(
    vecs: list[np.ndarray],
    vocab: list[str],
    reg: float = 0.05,
    n_iter: int = 10,
) -> np.ndarray:
    """Fixed-point Sinkhorn barycenter over a shared vocabulary.

    Each vector is a probability vector over the common vocab.
    Algorithm: initialise b_bar = uniform; iterate:
        b_bar_new[j] = prod_k (sum_i T_k[i,j]) ^ (1/K)
    where T_k is the OT plan between b_bar and vec_k.
    """
    K = len(vecs)
    V = len(vocab)
    w = 1.0 / K  # uniform weights

    # Shared cost matrix: binary (0 on diagonal, 1 elsewhere) — same vocab
    C = 1.0 - np.eye(V, dtype=np.float64)

    # Initialise barycenter as uniform
    b_bar = np.ones(V, dtype=np.float64) / V

    for _it in range(n_iter):
        log_b_new = np.zeros(V, dtype=np.float64)
        for vec in vecs:
            a = b_bar.copy()
            b = vec.copy()
            a /= a.sum() + 1e-300
            b /= b.sum() + 1e-300
            P, _ = sinkhorn(a, b, C, reg=reg, max_iter=100)
            # Column marginals of plan give transport to each vocab token
            col_marginal = P.sum(axis=0)
            col_marginal = np.maximum(col_marginal, 1e-300)
            log_b_new += w * np.log(col_marginal)
        b_bar = np.exp(log_b_new)
        b_bar /= b_bar.sum() + 1e-300

    return b_bar


def cmd_barycenter(skill_names: list[str], skills_dir=None, top_k: int = 20) -> None:
    """Compute Sinkhorn barycenter of 2-4 skills; output top_k tokens."""
    if not (2 <= len(skill_names) <= 4):
        print("[barycenter] Provide 2-4 skill names.", file=sys.stderr)
        sys.exit(1)

    tfs = _load_skill_tfs(skills_dir)

    # Resolve names
    resolved = []
    for name in skill_names:
        if name in tfs:
            resolved.append(name)
        else:
            candidates = [k for k in tfs if name in k]
            if candidates:
                resolved.append(candidates[0])
                print(f"[barycenter] '{name}' → '{candidates[0]}'", file=sys.stderr)
            else:
                print(f"[barycenter] Skill '{name}' not found.", file=sys.stderr)
                sys.exit(1)

    # Build shared vocabulary (union of all TF dicts)
    all_tf_dicts = [tfs[n] for n in resolved]
    vocab = sorted(set().union(*[set(tf.keys()) for tf in all_tf_dicts]))
    V = len(vocab)

    # Build probability vectors over shared vocab
    vecs = []
    for tf in all_tf_dicts:
        v = np.array([tf.get(t, 0.0) for t in vocab], dtype=np.float64)
        s = v.sum()
        v = v / s if s > 0 else np.ones(V) / V
        vecs.append(v)

    print(f"\n[barycenter] Computing Sinkhorn barycenter of {len(resolved)} skills over vocab size {V}…")
    barycenter = _iterative_barycenter(vecs, vocab, reg=0.05, n_iter=15)

    # Rank tokens by barycenter weight
    ranked = sorted(zip(vocab, barycenter), key=lambda x: -x[1])[:top_k]

    print(f"\n=== Sinkhorn Barycenter of: {', '.join(resolved)} ===")
    print(f"  Top-{top_k} tokens (token: weight):")
    for i, (token, weight) in enumerate(ranked, 1):
        print(f"  {i:3}. {token:<25s}  {weight:.6f}")
    print()


# ── curvature ─────────────────────────────────────────────────────────────────

def cmd_curvature(skills_dir=None, n_triplets: int = 20, top_k: int = 5, seed: int = 42) -> None:
    """Sample triplets and measure triangle inequality slack (non-Euclidean curvature).

    Slack = W2(A,C) - W2(A,B) - W2(B,C).  Positive = violates metric triangle ineq
    (curvature in the metric space).  We sort by |slack| descending.
    """
    tfs = _load_skill_tfs(skills_dir)
    names = sorted(tfs.keys())

    if len(names) < 3:
        print("[curvature] Need at least 3 skills.", file=sys.stderr)
        sys.exit(1)

    rng = random.Random(seed)
    # Precompute a pool of distances to avoid redundant Sinkhorn calls
    dist_cache: dict[tuple[str, str], float] = {}

    def w2(a: str, b: str) -> float:
        key = (min(a, b), max(a, b))
        if key not in dist_cache:
            dist_cache[key] = _w2_distance(tfs[a], tfs[b])
        return dist_cache[key]

    triplets_results = []
    attempts = 0
    max_attempts = n_triplets * 10
    seen_triplets: set[tuple] = set()

    while len(triplets_results) < n_triplets and attempts < max_attempts:
        attempts += 1
        A, B, C = rng.sample(names, 3)
        key = tuple(sorted([A, B, C]))
        if key in seen_triplets:
            continue
        seen_triplets.add(key)

        d_AC = w2(A, C)
        d_AB = w2(A, B)
        d_BC = w2(B, C)
        slack = d_AC - d_AB - d_BC
        triplets_results.append((slack, A, B, C, d_AB, d_BC, d_AC))

    # Sort by absolute slack descending (positive slack = most curved)
    triplets_results.sort(key=lambda x: -x[0])

    print(f"\n=== Triangle Inequality Slack (W2 Curvature) — top {top_k} of {len(triplets_results)} triplets ===")
    print(f"  Slack = W2(A,C) - W2(A,B) - W2(B,C)  [positive → non-Euclidean curvature]\n")
    for rank, (slack, A, B, C, d_AB, d_BC, d_AC) in enumerate(triplets_results[:top_k], 1):
        print(f"  {rank}. Slack = {slack:+.6f}")
        print(f"     A = {A}")
        print(f"     B = {B}")
        print(f"     C = {C}")
        print(f"     W2(A,B)={d_AB:.4f}  W2(B,C)={d_BC:.4f}  W2(A,C)={d_AC:.4f}")
    print()


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="skill-embedding-geometry.py",
        description="W2 geometry over skill TF probability simplices (VIL-1, VIL-4)",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_nearest = sub.add_parser("nearest", help="Find 5 nearest skills in W2 distance")
    p_nearest.add_argument("skill", help="Target skill name")
    p_nearest.add_argument("--top", type=int, default=5)
    p_nearest.add_argument("--skills-dir", default=None)

    p_bary = sub.add_parser("barycenter", help="Sinkhorn barycenter of 2-4 skills")
    p_bary.add_argument("skills", nargs="+", metavar="SKILL", help="2-4 skill names")
    p_bary.add_argument("--top", type=int, default=20)
    p_bary.add_argument("--skills-dir", default=None)

    p_curv = sub.add_parser("curvature", help="Sample 20 triplets; top-5 triangle inequality slacks")
    p_curv.add_argument("--n-triplets", type=int, default=20)
    p_curv.add_argument("--top", type=int, default=5)
    p_curv.add_argument("--seed", type=int, default=42)
    p_curv.add_argument("--skills-dir", default=None)

    args = parser.parse_args()

    if args.cmd == "nearest":
        cmd_nearest(args.skill, args.skills_dir, args.top)
    elif args.cmd == "barycenter":
        cmd_barycenter(args.skills, args.skills_dir, args.top)
    elif args.cmd == "curvature":
        cmd_curvature(args.skills_dir, args.n_triplets, args.top, args.seed)


if __name__ == "__main__":
    main()
