#!/usr/bin/python3
"""
bound-hierarchy-monitor.py

Detects when procedural memory or context layers have become too lossy
or mismatched by checking a hierarchy of information-theoretic bounds:
packing radius ≤ covering radius, extended to entropy and capacity bounds.

Math basis: Hierarchical bound chain (wave9)
  For a metric space of skills/memory blocks:
    r_pack(k) ≤ r_cover(k)  for all granularities k
  Extended chain:
    H_min ≤ H_avg ≤ H_max    (entropy bounds on skill distribution)
    C_block ≤ C_session       (block-level ≤ session-level capacity)
  
  Alarm when any bound in the chain is violated:
    - Packing > Covering  (impossible: indicates corrupted index)
    - H_avg outside [H_min, H_max] band (entropy anomaly)
    - Block capacity exceeds session capacity (overflow)

Usage:
  python3 bound-hierarchy-monitor.py

Runs as a monitor in the suite.
"""
from __future__ import annotations

import json
import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

HOME       = Path.home()
SKILLS_DIR = HOME / ".hermes/profiles/fork/skills"
ALT_SKILLS = HOME / ".hermes/skills"
CACHE_DIR  = HOME / ".hermes/cache/monitors"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE   = CACHE_DIR / "bound-hierarchy.json"

MAX_SKILLS   = 60
H_MIN_FLOOR  = 0.5    # entropy must be at least this (not too concentrated)
H_MAX_CEIL   = 6.0    # entropy must be at most this (not too diffuse)
BLOCK_CAP    = 4096   # max chars per context block
SESSION_CAP  = 200000 # max chars per session (200K)


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z]{4,}", text.lower()))


def _load_skills(n: int) -> list[dict]:
    skills = []
    for base in [SKILLS_DIR, ALT_SKILLS]:
        if not base.exists():
            continue
        for md in list(base.rglob("SKILL.md"))[:n - len(skills)]:
            try:
                text   = md.read_text()[:500]
                tokens = _tokenize(text)
                if tokens:
                    skills.append({"name": md.parent.name, "tokens": tokens,
                                   "chars": len(text)})
            except Exception:
                pass
        if len(skills) >= n:
            break
    return skills[:n]


def _packing_radius(skills: list[dict]) -> float:
    """
    Packing radius ≈ min pairwise Jaccard distance / 2.
    (Largest r s.t. all skill balls of radius r are disjoint.)
    """
    if len(skills) < 2:
        return 0.0
    min_dist = float("inf")
    for i in range(min(len(skills), 20)):
        for j in range(i + 1, min(len(skills), 20)):
            ti, tj = skills[i]["tokens"], skills[j]["tokens"]
            jacc   = len(ti & tj) / max(len(ti | tj), 1)
            dist   = 1.0 - jacc
            min_dist = min(min_dist, dist)
    return min_dist / 2.0


def _covering_radius(skills: list[dict]) -> float:
    """
    Covering radius ≈ max over skills of min distance to any other skill.
    (Smallest r s.t. all skills are covered by some ball of radius r.)
    """
    if len(skills) < 2:
        return 1.0
    max_min = 0.0
    for i in range(min(len(skills), 20)):
        min_d = float("inf")
        for j in range(min(len(skills), 20)):
            if i == j:
                continue
            ti, tj = skills[i]["tokens"], skills[j]["tokens"]
            jacc   = len(ti & tj) / max(len(ti | tj), 1)
            min_d  = min(min_d, 1.0 - jacc)
        max_min = max(max_min, min_d)
    return max_min


def _skill_entropy(skills: list[dict]) -> float:
    """Entropy of the skill token-size distribution."""
    sizes = np.array([len(s["tokens"]) for s in skills], dtype=float)
    if sizes.sum() == 0:
        return 0.0
    p = sizes / sizes.sum()
    return float(-np.sum(p * np.log2(p + 1e-12)))


def run() -> int:
    now    = datetime.now(timezone.utc).isoformat()
    skills = _load_skills(MAX_SKILLS)

    if len(skills) < 4:
        print("[bound-hierarchy] Too few skills")
        print("ALARM: no — insufficient data")
        return 0

    r_pack  = _packing_radius(skills)
    r_cover = _covering_radius(skills)
    H_avg   = _skill_entropy(skills)

    # Block vs session capacity check
    total_block_chars = sum(min(s["chars"], BLOCK_CAP) for s in skills)
    block_overflow    = total_block_chars > SESSION_CAP

    # Bound checks
    pack_cover_ok = r_pack <= r_cover + 1e-9   # must hold; allow float slack
    entropy_ok    = H_MIN_FLOOR <= H_avg <= H_MAX_CEIL
    capacity_ok   = not block_overflow

    violations = []
    if not pack_cover_ok:
        violations.append(f"pack({r_pack:.4f}) > cover({r_cover:.4f}) — corrupted index")
    if not entropy_ok:
        violations.append(f"H_avg={H_avg:.4f} outside [{H_MIN_FLOOR}, {H_MAX_CEIL}]")
    if not capacity_ok:
        violations.append(f"block_total={total_block_chars} > session_cap={SESSION_CAP}")

    print(f"\n=== Bound Hierarchy Monitor — {now[:10]} ===")
    print(f"Skills: {len(skills)}\n")
    print(f"  Packing radius r_pack  = {r_pack:.6f}")
    print(f"  Covering radius r_cover = {r_cover:.6f}")
    print(f"  r_pack ≤ r_cover?       {'✓' if pack_cover_ok else '✗ VIOLATED'}")
    print(f"\n  Entropy H_avg          = {H_avg:.4f}  [{H_MIN_FLOOR}, {H_MAX_CEIL}]")
    print(f"  Entropy in range?        {'✓' if entropy_ok else '✗ VIOLATED'}")
    print(f"\n  Block total chars      = {total_block_chars}")
    print(f"  Session capacity       = {SESSION_CAP}")
    print(f"  Capacity OK?           {'✓' if capacity_ok else '✗ VIOLATED'}")

    alarm = bool(violations)
    print()
    if alarm:
        print(f"ALARM: yes — bound hierarchy violated: {'; '.join(violations)}")
    else:
        print("ALARM: no — all bound hierarchy checks pass")

    OUT_FILE.write_text(json.dumps({
        "ts": now, "skills": len(skills),
        "r_pack": round(r_pack, 6), "r_cover": round(r_cover, 6),
        "H_avg": round(H_avg, 4), "violations": violations,
    }, indent=2))

    return 1 if alarm else 0


if __name__ == "__main__":
    sys.exit(run())
