#!/usr/bin/python3
"""
radius-hierarchy-monitor.py

Early detection of memory coherence breakdown by monitoring the geometric
duality between packing and covering radii across Hermes skill embeddings
— detects when skill representations become incoherent.

Math basis: packing/covering radius duality
  For a set S of skill vectors in metric space (M, d):
    packing radius r_pack = max distance s.t. balls of radius r_pack are disjoint
    covering radius r_cov  = min radius s.t. balls of radius r_cov cover M
  
  Invariant: r_pack ≤ r_cov ≤ 2·r_pack  (always holds in any metric space)
  
  Proxy using skill name/keyword Jaccard similarity as distance:
    d(s_i, s_j) = 1 - Jaccard(keywords(s_i), keywords(s_j))
    r_pack_proxy = max_{i≠j} min_{k≠i} d(s_i, s_k)   (nearest-neighbour distance)
    r_cov_proxy  = max_i min_j d(s_i, s_j)             (same — max of min distances)
  
  Alarm when r_cov > 2·r_pack (duality violated → incoherent skill space).

Usage:
  python3 radius-hierarchy-monitor.py          # audit skill graph
  python3 radius-hierarchy-monitor.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

HOME       = Path.home()
SKILLS_DIR = HOME / ".hermes/profiles/fork/skills"
ALT_SKILLS = HOME / ".hermes/skills"
CACHE_DIR  = HOME / ".hermes/cache/monitors"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE   = CACHE_DIR / "radius-hierarchy-report.json"

DUALITY_SLACK = 2.0   # alarm when r_cov > DUALITY_SLACK × r_pack
MIN_SKILLS    = 5


def _keywords(skill_path: Path) -> set[str]:
    """Extract keyword tokens from skill name + first 500 chars of content."""
    text = skill_path.stem.replace("-", " ").replace("_", " ")
    try:
        text += " " + skill_path.read_text()[:500]
    except Exception:
        pass
    return set(re.findall(r"[a-z]{3,}", text.lower()))


def _jaccard_dist(a: set, b: set) -> float:
    u = a | b
    return 1.0 - (len(a & b) / len(u)) if u else 0.0


def run(dry_run: bool) -> int:
    now = datetime.now(timezone.utc).isoformat()

    # Collect skill paths from both locations
    paths: list[Path] = []
    for d in [SKILLS_DIR, ALT_SKILLS]:
        if d.exists():
            paths.extend(d.rglob("SKILL.md"))
    paths = list(set(paths))

    if len(paths) < MIN_SKILLS:
        print(f"[radius-monitor] Only {len(paths)} skills found (min {MIN_SKILLS})")
        print("ALARM: no — insufficient skills to evaluate")
        return 0

    # Build keyword sets
    skills     = [(p.parent.name, _keywords(p)) for p in paths]
    n          = len(skills)

    # Compute pairwise distances (nearest-neighbour for each)
    nn_dists = []
    for i, (name_i, kw_i) in enumerate(skills):
        dists = [_jaccard_dist(kw_i, kw_j) for j, (_, kw_j) in enumerate(skills) if j != i]
        nn_dists.append(min(dists) if dists else 0.0)

    r_pack = max(nn_dists)   # largest min-distance (packing radius proxy)
    # r_cov proxy: max pairwise distance / 2 (smallest enclosing ball radius upper bound)
    all_dists = []
    for i in range(n):
        for j in range(i+1, n):
            all_dists.append(_jaccard_dist(skills[i][1], skills[j][1]))

    max_dist = max(all_dists) if all_dists else 0.0
    r_cov    = max_dist / 2.0  # covering radius ≤ max_pairwise/2
    ratio    = r_cov / r_pack if r_pack > 0 else 0.0
    alarm    = ratio > DUALITY_SLACK

    print(f"\n=== Radius Hierarchy Monitor — {now[:10]} ===")
    print(f"Skills analysed: {n}")
    print(f"Packing radius:  {r_pack:.4f}")
    print(f"Covering radius: {r_cov:.4f}  (max_pairwise/2)")
    print(f"Duality ratio:   {ratio:.4f}  (r_cov/r_pack, threshold ≤ {DUALITY_SLACK})")

    # Most isolated skills
    top_isolated = sorted(zip(nn_dists, [s[0] for s in skills]), reverse=True)[:5]
    print(f"\nMost isolated skills (high NN distance):")
    for dist, name in top_isolated:
        print(f"  {dist:.4f}  {name}")

    if alarm:
        print(f"\nALARM: yes — skill space duality violated (ratio={ratio:.3f} > {DUALITY_SLACK})")
        print("       Skill embeddings are incoherent — consolidation recommended")
        rc = 1
    else:
        print(f"\nALARM: no — packing/covering duality holds")
        rc = 0

    if not dry_run:
        OUT_FILE.write_text(json.dumps({
            "ts": now, "n_skills": n,
            "r_pack": round(r_pack, 4), "max_dist": round(max_dist, 4),
            "ratio": round(ratio, 4), "alarm": alarm,
            "top_isolated": [{"name": n, "nn_dist": round(d, 4)}
                             for d, n in top_isolated],
        }, indent=2))

    return rc


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    sys.exit(run(args.dry_run))


if __name__ == "__main__":
    main()
