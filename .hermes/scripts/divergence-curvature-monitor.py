#!/usr/bin/python3
"""
divergence-curvature-monitor.py

Adaptive skill routing and memory-state compression by quantifying which
semantic/procedural distinctions carry the most information curvature.

Math basis: Fisher information rate as KL curvature
  I(θ) = lim_{ε→0} (2/ε²) · KL(p(x|θ+ε) || p(x|θ))
  High curvature → nearby skills are sharply distinguishable.
  Low curvature → skill space is flat → routing is ambiguous.
  
  Applied to skill routing: estimate KL curvature between adjacent
  skill-topic distributions. High curvature pairs are well-separated
  (easy routing). Low curvature → skills too similar → merge candidates.
  
  Alarm if mean KL curvature across all skill pairs < CURVATURE_FLOOR.

Usage:
  python3 divergence-curvature-monitor.py [--top N]

Runs as a monitor in the suite.
"""
from __future__ import annotations
import os

import json
import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

HOME       = Path.home()
_HH = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_HP = os.environ.get("HERMES_PROFILE", "fork")
_RT = _HH / "profiles" / _HP if _HP else _HH
SKILLS_DIR = _RT / "skills"
ALT_SKILLS = HOME / ".hermes/skills"
CACHE_DIR  = HOME / ".hermes/cache/monitors"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE   = CACHE_DIR / "divergence-curvature.json"

MAX_SKILLS     = 40
CURVATURE_FLOOR = 0.02   # alarm if mean KL curvature below this
EPS            = 0.05    # perturbation for finite-difference curvature


def _tokenize(text: str) -> dict[str, int]:
    """Return token frequency dict from text."""
    tokens = re.findall(r"[a-z]{3,}", text.lower())
    freq: dict[str, int] = {}
    for t in tokens:
        freq[t] = freq.get(t, 0) + 1
    return freq


def _load_skills(n: int = MAX_SKILLS) -> list[dict]:
    skills = []
    seen_names: set[str] = set()
    for base in [SKILLS_DIR, ALT_SKILLS]:
        if not base.exists():
            continue
        for md in list(base.rglob("SKILL.md"))[:n]:
            name = md.parent.name
            if name in seen_names:
                continue
            try:
                freq = _tokenize(md.read_text()[:600])
                if freq:
                    skills.append({"name": name, "freq": freq})
                    seen_names.add(name)
            except Exception:
                pass
            if len(skills) >= n:
                break
        if len(skills) >= n:
            break
    return skills[:n]


def _to_prob(freq: dict[str, int], vocab: list[str]) -> np.ndarray:
    """Convert freq dict to probability vector over vocab."""
    v = np.array([freq.get(t, 0) for t in vocab], dtype=float)
    v += 0.5   # Laplace smoothing
    return v / v.sum()


def _kl(p: np.ndarray, q: np.ndarray) -> float:
    """KL divergence D(p||q), clipped."""
    mask = p > 0
    return float(np.sum(p[mask] * np.log(p[mask] / q[mask])))


def _kl_curvature(p: np.ndarray, q: np.ndarray, eps: float = EPS) -> float:
    """
    Finite-difference estimate of KL curvature along p→q direction.
    C = (KL(p+ε·d || q) - 2·KL(p||q) + KL(p-ε·d || q)) / ε²
    where d = (q-p)/||q-p|| (unit perturbation direction).

    Note: this is a directional KL curvature proxy, not Fisher information.
    Negative values (can occur near boundaries after clipping) are kept as-is
    and indicate the distribution pair is at a flat or non-convex region.
    """
    d_raw = q - p
    norm  = np.linalg.norm(d_raw)
    if norm < 1e-12:
        return 0.0
    d  = d_raw / norm                                          # unit direction

    pp = np.clip(p + eps * d, 1e-10, None); pp /= pp.sum()
    pm = np.clip(p - eps * d, 1e-10, None); pm /= pm.sum()
    q_ = np.clip(q, 1e-10, None); q_ /= q_.sum()

    kl_0  = _kl(p,  q_)
    kl_pp = _kl(pp, q_)
    kl_pm = _kl(pm, q_)
    curv  = (kl_pp - 2 * kl_0 + kl_pm) / (eps ** 2)
    return float(curv)   # keep sign — negative = flat/boundary region


def run(top_n: int = 10) -> int:
    now    = datetime.now(timezone.utc).isoformat()
    skills = _load_skills()

    if len(skills) < 4:
        print("[divergence-curvature] Too few skills loaded")
        print("ALARM: no — insufficient data")
        return 0

    # Build shared vocabulary (top 200 tokens by total frequency)
    all_freq: dict[str, int] = {}
    for s in skills:
        for t, c in s["freq"].items():
            all_freq[t] = all_freq.get(t, 0) + c
    vocab = sorted(all_freq, key=lambda t: -all_freq[t])[:200]

    # Compute probability vectors
    probs = [_to_prob(s["freq"], vocab) for s in skills]

    # Compute pairwise KL curvatures (sample up to top_n² pairs)
    curvatures = []
    pairs      = []
    for i in range(len(skills)):
        for j in range(i + 1, len(skills)):
            c = _kl_curvature(probs[i], probs[j])
            curvatures.append(c)
            pairs.append((skills[i]["name"], skills[j]["name"], c))

    if not curvatures:
        print("ALARM: no — no pairs to evaluate")
        return 0

    mean_curv = float(np.mean(curvatures))
    low_pairs = [(a, b, c) for a, b, c in pairs if c < CURVATURE_FLOOR]

    print(f"\n=== Divergence Curvature Monitor — {now[:10]} ===")
    print(f"Skills: {len(skills)}  Pairs: {len(pairs)}  "
          f"Mean curvature: {mean_curv:.6f}  Floor: {CURVATURE_FLOOR}\n")

    # Show top-N highest and lowest curvature pairs
    pairs_sorted = sorted(pairs, key=lambda x: x[2])
    print(f"  Lowest curvature (most ambiguous routing):")
    for a, b, c in pairs_sorted[:5]:
        print(f"    {a:<30} ↔ {b:<30} C={c:.6f}")
    print(f"\n  Highest curvature (sharpest distinction):")
    for a, b, c in pairs_sorted[-5:][::-1]:
        print(f"    {a:<30} ↔ {b:<30} C={c:.6f}")

    print(f"\nLow-curvature pairs (C < {CURVATURE_FLOOR}): {len(low_pairs)}")

    alarm = mean_curv < CURVATURE_FLOOR
    if alarm:
        print(f"ALARM: yes — mean KL curvature {mean_curv:.6f} below floor {CURVATURE_FLOOR}")
        print("  Recommendation: audit and split low-curvature skill pairs")
    else:
        print(f"ALARM: no — mean curvature {mean_curv:.6f} above floor")

    _tmp_out_file = OUT_FILE.with_suffix('.tmp')
    _tmp_out_file.write_text(json.dumps({
        "ts": now, "skills": len(skills), "pairs": len(pairs),
        "mean_curvature": round(mean_curv, 8),
        "low_pairs": len(low_pairs),
        "worst5": [(a, b, round(c, 8)) for a, b, c in pairs_sorted[:5]],
    }, indent=2))
    _tmp_out_file.replace(OUT_FILE)

    return 1 if alarm else 0


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--top", type=int, default=10)
    p.add_argument("--dry-run", action="store_true")  # accepted but no-op (writes by default)
    args = p.parse_args()
    sys.exit(run(args.top))
