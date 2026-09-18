#!/usr/bin/env python3
"""
skill-gw-compare.py — OT-7
Gromov-Wasserstein comparison of skill ecosystems.

Algorithm:
  Sample up to 20 skills from each directory.
  Build TF vectors, then pairwise W1 cost matrix C (NxN via ot_utils.w1_distance).
  Implement linearized GW: alternate Sinkhorn where
    M_ij = sum_kl (C_A_ik - C_B_jl)^2 * T_kl
  Update T via sinkhorn(M, reg=0.1). Run 3 alternating rounds.

Subcommands:
  compare <dir1> <dir2>    Output GW distance and top-5 matched skill pairs.
  self-compare             Compare ~/.hermes/skills vs ~/.hermes/profiles/fork/skills.

Usage:
  python skill-gw-compare.py self-compare
  python skill-gw-compare.py compare ~/.hermes/skills ~/.hermes/profiles/fork/skills
"""

import sys
import os
import random
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

MAX_SAMPLE = 20
GW_ROUNDS = 3
GW_REG = 0.1
TOP_PAIRS = 5


# ── Skill loading ─────────────────────────────────────────────────────────────

def _load_skills_from_dir(skills_dir: Path, max_sample: int = MAX_SAMPLE, seed: int = 42) -> dict[str, dict]:
    """Load up to max_sample skill TF dicts from a skills directory.

    Returns {skill_name: tf_dict}.
    """
    skills_dir = Path(skills_dir)
    if not skills_dir.is_dir():
        print(f"[gw-compare] Directory not found: {skills_dir}", file=sys.stderr)
        return {}

    all_skills = []
    for skill_md in skills_dir.rglob("SKILL.md"):
        if ".archive" in skill_md.parts:
            continue
        name = skill_md.parent.name
        try:
            text = skill_md.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        tf = build_tf(text)
        if tf:
            all_skills.append((name, tf))

    if not all_skills:
        return {}

    # Sample deterministically
    rng = random.Random(seed)
    if len(all_skills) > max_sample:
        all_skills = rng.sample(all_skills, max_sample)

    return dict(all_skills)


# ── Pairwise W1 cost matrix ───────────────────────────────────────────────────

def _build_cost_matrix(skill_tfs: dict[str, dict]) -> tuple[np.ndarray, list[str]]:
    """Build NxN pairwise W1 cost matrix.  Returns (C, names_list)."""
    names = list(skill_tfs.keys())
    N = len(names)
    C = np.zeros((N, N), dtype=np.float64)
    for i in range(N):
        for j in range(i + 1, N):
            d = w1_distance(skill_tfs[names[i]], skill_tfs[names[j]])
            C[i, j] = d
            C[j, i] = d
    return C, names


# ── Linearized Gromov-Wasserstein ─────────────────────────────────────────────

def _gw_distance(
    C_A: np.ndarray,
    C_B: np.ndarray,
    names_A: list[str],
    names_B: list[str],
    n_rounds: int = GW_ROUNDS,
    reg: float = GW_REG,
) -> tuple[float, np.ndarray]:
    """Linearized GW via alternating Sinkhorn.

    M_ij = sum_kl (C_A[i,k] - C_B[j,l])^2 * T[k,l]
    T <- sinkhorn(uniform_A, uniform_B, M, reg)
    Repeat n_rounds times.

    Returns (gw_cost, T_final).
    """
    n_A = len(names_A)
    n_B = len(names_B)

    a = np.ones(n_A, dtype=np.float64) / n_A
    b = np.ones(n_B, dtype=np.float64) / n_B

    # Initialise T as outer product (independent coupling)
    T = np.outer(a, b)

    ones_B = np.ones(n_B, dtype=np.float64)
    ones_A = np.ones(n_A, dtype=np.float64)
    CA2 = C_A ** 2
    CB2 = C_B ** 2
    # Initialise M so it is always bound even if n_rounds == 0
    M = np.zeros((n_A, n_B), dtype=np.float64)

    for round_idx in range(n_rounds):
        # M_ij = sum_kl (C_A[i,k] - C_B[j,l])^2 * T[k,l]
        # Efficient computation:
        #   M = C_A^2 @ T @ ones + ones @ T^T @ C_B^2 - 2 * C_A @ T @ C_B^T
        term1 = CA2 @ (T @ ones_B)           # shape (n_A,)  → broadcast to (n_A, n_B)
        term2 = (ones_A @ (T @ CB2.T))       # shape (n_B,)  → broadcast to (n_A, n_B)
        term3 = 2.0 * (C_A @ T @ C_B.T)     # shape (n_A, n_B)

        M = term1[:, None] + term2[None, :] - term3
        # Clamp to non-negative (numerical safety)
        M = np.maximum(M, 0.0)

        T, _ = sinkhorn(a, b, M, reg=reg, max_iter=100)

    # GW cost = <M_final, T_final>
    gw_cost = float(np.sum(M * T))

    return gw_cost, T


# ── Top matched pairs ─────────────────────────────────────────────────────────

def _top_matched_pairs(T: np.ndarray, names_A: list[str], names_B: list[str], top_k: int = 5):
    """Return top_k (name_A, name_B, transport_mass) matched pairs."""
    n_A, n_B = T.shape
    pairs = []
    for i in range(n_A):
        for j in range(n_B):
            pairs.append((T[i, j], names_A[i], names_B[j]))
    pairs.sort(reverse=True)
    return pairs[:top_k]


# ── compare ───────────────────────────────────────────────────────────────────

def cmd_compare(dir1: str, dir2: str) -> None:
    """Compare two skill directories via GW distance."""
    path1 = Path(dir1).expanduser()
    path2 = Path(dir2).expanduser()

    print(f"\n[skill-gw-compare] Loading skills from:")
    print(f"  Dir A: {path1}")
    print(f"  Dir B: {path2}\n")

    tfs_A = _load_skills_from_dir(path1, seed=42)
    tfs_B = _load_skills_from_dir(path2, seed=42)

    if not tfs_A or not tfs_B:
        print("[compare] One or both directories yielded no skills.", file=sys.stderr)
        sys.exit(1)

    print(f"  Sampled {len(tfs_A)} skills from A, {len(tfs_B)} from B")
    print(f"  Building pairwise W1 cost matrices…")

    C_A, names_A = _build_cost_matrix(tfs_A)
    C_B, names_B = _build_cost_matrix(tfs_B)

    print(f"  Running linearized GW ({GW_ROUNDS} rounds, reg={GW_REG})…\n")

    gw_cost, T = _gw_distance(C_A, C_B, names_A, names_B, n_rounds=GW_ROUNDS, reg=GW_REG)

    print(f"=== GW Distance: {gw_cost:.6f} ===\n")
    print(f"  (Lower = more structurally similar skill ecosystems)\n")

    top_pairs = _top_matched_pairs(T, names_A, names_B, top_k=TOP_PAIRS)
    print(f"  Top-{TOP_PAIRS} matched skill pairs (by transport mass):")
    for rank, (mass, na, nb) in enumerate(top_pairs, 1):
        print(f"  {rank}. {na:<45s}  ↔  {nb:<45s}  mass={mass:.6f}")
    print()


# ── self-compare ──────────────────────────────────────────────────────────────

def cmd_self_compare() -> None:
    """Compare default ~/.hermes/skills vs fork ~/.hermes/profiles/fork/skills.

    If the fork skills dir is empty (fork profile uses bundled manifest),
    falls back to comparing two non-overlapping random halves of the default
    skills dir so the GW geometry is still exercised meaningfully.
    """
    path1 = DEFAULT_SKILLS_DIR
    path2 = FORK_SKILLS_DIR

    if not path1.is_dir():
        print(f"[self-compare] Default skills dir not found: {path1}", file=sys.stderr)
        sys.exit(1)

    print(f"\n[skill-gw-compare] Self-compare:")
    print(f"  Default: {path1}")
    print(f"  Fork:    {path2}\n")

    tfs_A = _load_skills_from_dir(path1, seed=42)

    # Try fork dir; if empty, split default into two halves for comparison
    tfs_B = {}
    if path2.is_dir():
        tfs_B = _load_skills_from_dir(path2, seed=99)

    if not tfs_B:
        print(f"  [Note] Fork skills dir empty or absent — comparing two disjoint halves of default skills dir.", file=sys.stderr)
        # Load full default set, split into two halves by odd/even alphabetical index
        all_default = _load_skills_from_dir(path1, max_sample=40, seed=42)
        all_names = sorted(all_default.keys())
        half = len(all_names) // 2
        half_A_names = all_names[:half]
        half_B_names = all_names[half:]
        # Trim to MAX_SAMPLE each
        half_A_names = half_A_names[:MAX_SAMPLE]
        half_B_names = half_B_names[:MAX_SAMPLE]
        tfs_A = {n: all_default[n] for n in half_A_names}
        tfs_B = {n: all_default[n] for n in half_B_names}
        print(f"  [Fallback] Half-A: {len(tfs_A)} skills, Half-B: {len(tfs_B)} skills")

    if not tfs_A or not tfs_B:
        print("[self-compare] Could not load skills from either dir.", file=sys.stderr)
        sys.exit(1)

    print(f"  Sampled {len(tfs_A)} from default, {len(tfs_B)} from fork")

    # Check overlap
    shared = set(tfs_A) & set(tfs_B)
    only_A = set(tfs_A) - set(tfs_B)
    only_B = set(tfs_B) - set(tfs_A)
    print(f"  Shared names: {len(shared)},  only-default: {len(only_A)},  only-fork: {len(only_B)}")

    print(f"  Building pairwise W1 cost matrices…")
    C_A, names_A = _build_cost_matrix(tfs_A)
    C_B, names_B = _build_cost_matrix(tfs_B)

    print(f"  Running linearized GW ({GW_ROUNDS} rounds, reg={GW_REG})…\n")
    gw_cost, T = _gw_distance(C_A, C_B, names_A, names_B, n_rounds=GW_ROUNDS, reg=GW_REG)

    print(f"=== GW Distance (default vs fork): {gw_cost:.6f} ===\n")
    print(f"  (0 = identical structure; higher = more divergence between profiles)\n")

    top_pairs = _top_matched_pairs(T, names_A, names_B, top_k=TOP_PAIRS)
    print(f"  Top-{TOP_PAIRS} skill pairs with highest transport mass (most structurally matched):")
    for rank, (mass, na, nb) in enumerate(top_pairs, 1):
        print(f"  {rank}. {na:<45s}  ↔  {nb:<45s}  mass={mass:.6f}")

    # Also highlight divergent pairs (skills with low transport mass to their name-twin)
    print(f"\n  Shared skills with divergent content (high W1 between same-name skill in each profile):")
    divergent = []
    for name in sorted(shared):
        if name in tfs_A and name in tfs_B:
            d = w1_distance(tfs_A[name], tfs_B[name])
            divergent.append((d, name))
    divergent.sort(reverse=True)
    for d, name in divergent[:5]:
        print(f"    {name:<50s}  W1 = {d:.6f}")
    print()


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="skill-gw-compare.py",
        description="Gromov-Wasserstein skill ecosystem comparison (OT-7)",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_cmp = sub.add_parser("compare", help="Compare two skill directories")
    p_cmp.add_argument("dir1", help="First skills directory")
    p_cmp.add_argument("dir2", help="Second skills directory")

    sub.add_parser("self-compare", help="Compare default vs fork skill profiles")

    args = parser.parse_args()

    if args.cmd == "compare":
        cmd_compare(args.dir1, args.dir2)
    elif args.cmd == "self-compare":
        cmd_self_compare()


if __name__ == "__main__":
    main()
