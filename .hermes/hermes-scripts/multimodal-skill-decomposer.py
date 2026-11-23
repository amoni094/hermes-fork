#!/usr/bin/python3
"""
multimodal-skill-decomposer.py

Automatically identifies which multi-modal skill pairs should be fused
vs. kept separate, using Partial Information Decomposition (PID) to
measure redundancy, synergy, and unique information between skill pairs.

Math basis: PID (Williams & Beer 2010)
  I(X,Y;Z) = Red(X,Y→Z) + Uniq(X→Z) + Uniq(Y→Z) + Syn(X,Y→Z)
  where X,Y = two skills' keyword sets, Z = a target task query.
  
  Proxy (set-theoretic PID):
    kw_X, kw_Y = keyword sets for skills X, Y
    kw_T = task query keywords
    Red = |kw_X ∩ kw_Y ∩ kw_T| / |kw_T|      (shared coverage)
    Uniq_X = |kw_X ∩ kw_T - kw_Y| / |kw_T|   (X-unique coverage)
    Uniq_Y = |kw_Y ∩ kw_T - kw_X| / |kw_T|   (Y-unique coverage)
    Syn = |(kw_X ∪ kw_Y) ∩ kw_T| - Red - Uniq_X - Uniq_Y  (joint gain)
  
  FUSE recommendation: Syn > SYNERGY_THRESHOLD and Red < REDUNDANCY_THRESHOLD
  SEPARATE: Red > REDUNDANCY_THRESHOLD (high overlap = wasteful to call both)

Usage:
  python3 multimodal-skill-decomposer.py --query "memory compression" --skills A B
  python3 multimodal-skill-decomposer.py --dry-run
"""
from __future__ import annotations
import os

import argparse
import json
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
OUT_FILE   = CACHE_DIR / "multimodal-decomposition.json"

SYNERGY_THRESHOLD    = 0.10   # fuse if synergy > 10% of task coverage
REDUNDANCY_THRESHOLD = 0.40   # separate if redundancy > 40%


def _load_skill(skill_name: str) -> set[str]:
    for base in [SKILLS_DIR, ALT_SKILLS]:
        # Try direct match
        md = base / skill_name / "SKILL.md"
        if md.exists():
            text = md.read_text()[:600]
            return set(re.findall(r"[a-z]{4,}", text.lower()))
        # Try fuzzy: find skill dir whose name contains skill_name stem
        stem = skill_name.replace("-", "").replace("_", "").lower()
        for child in base.iterdir():
            if child.is_dir() and stem in child.name.replace("-", "").replace("_", "").lower():
                md2 = child / "SKILL.md"
                if md2.exists():
                    text = md2.read_text()[:600]
                    return set(re.findall(r"[a-z]{4,}", text.lower()))
    # Fallback: expand name into keyword set
    expanded = skill_name.replace("-", " ").replace("_", " ").lower()
    return set(re.findall(r"[a-z]{3,}", expanded))


def _pid(kw_x: set, kw_y: set, kw_t: set) -> dict:
    if not kw_t:
        return {"red": 0.0, "uniq_x": 0.0, "uniq_y": 0.0, "syn": 0.0}
    n   = len(kw_t)
    red = len(kw_x & kw_y & kw_t) / n
    ux  = len((kw_x & kw_t) - kw_y)  / n
    uy  = len((kw_y & kw_t) - kw_x)  / n
    syn = max(0.0, len((kw_x | kw_y) & kw_t) / n - red - ux - uy)
    return {"red": round(red,4), "uniq_x": round(ux,4), "uniq_y": round(uy,4), "syn": round(syn,4)}


def decompose(skill_a: str, skill_b: str, query: str) -> dict:
    kw_a = _load_skill(skill_a)
    kw_b = _load_skill(skill_b)
    kw_t = set(re.findall(r"[a-z]{3,}", query.lower()))

    pid = _pid(kw_a, kw_b, kw_t)
    recommend = (
        "FUSE"     if pid["syn"] > SYNERGY_THRESHOLD and pid["red"] < REDUNDANCY_THRESHOLD else
        "SEPARATE" if pid["red"] > REDUNDANCY_THRESHOLD else
        "NEUTRAL"
    )

    return {
        "skill_a":    skill_a,
        "skill_b":    skill_b,
        "query":      query[:60],
        "pid":        pid,
        "recommend":  recommend,
        "rationale": (
            f"synergy={pid['syn']:.3f}>{SYNERGY_THRESHOLD} → joint gain" if recommend == "FUSE" else
            f"redundancy={pid['red']:.3f}>{REDUNDANCY_THRESHOLD} → wasteful overlap" if recommend == "SEPARATE" else
            "no strong signal"
        ),
    }


def run(skill_a: str | None, skill_b: str | None, query: str, dry_run: bool) -> int:
    now = datetime.now(timezone.utc).isoformat()

    if skill_a and skill_b:
        cases = [(skill_a, skill_b, query)]
    else:
        # Demo pairs covering common use-cases
        cases = [
            ("obsidian",         "notion",             "store and retrieve session notes"),
            ("hermes-research",  "arxiv",              "find recent papers on agent memory"),
            ("github",           "github-issues",      "create and manage pull requests"),
            ("hermes-agent",     "hermes-fork",        "configure hermes agent settings"),
            ("academic-literature-review", "domain-research-synthesis", "survey agent memory literature"),
        ]

    print(f"\n=== Multimodal Skill Decomposer — {now[:10]} ===")
    print(f"  {'Pair':<40} {'Rec':<9} Red    UniqA  UniqB  Syn")
    print("  " + "-" * 80)

    results   = []
    fuse_recs = 0
    sep_recs  = 0
    for a, b, q in cases:
        r = decompose(a, b, q)
        p = r["pid"]
        print(f"  {a[:18]}+{b[:18]:<20} {r['recommend']:<9} "
              f"{p['red']:.3f}  {p['uniq_x']:.3f}  {p['uniq_y']:.3f}  {p['syn']:.3f}")
        print(f"      Query: \"{q[:55]}\"")
        results.append(r)
        if r["recommend"] == "FUSE":     fuse_recs += 1
        elif r["recommend"] == "SEPARATE": sep_recs += 1

    print(f"\nFUSE: {fuse_recs}  SEPARATE: {sep_recs}  NEUTRAL: {len(results)-fuse_recs-sep_recs}")

    if not dry_run:
        _tmp_out_file = OUT_FILE.with_suffix('.tmp')
        _tmp_out_file.write_text(json.dumps({"ts": now, "results": results}, indent=2))
        _tmp_out_file.replace(OUT_FILE)
        print(f"Written: {OUT_FILE}")

    return 0


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--skill-a", default=None)
    p.add_argument("--skill-b", default=None)
    p.add_argument("--query",   default="agent task routing")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    sys.exit(run(args.skill_a, args.skill_b, args.query, args.dry_run))


if __name__ == "__main__":
    main()
