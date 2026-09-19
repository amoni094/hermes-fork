#!/usr/bin/python3
"""
priority-intersection-matcher.py

Multi-policy stable matching for Hermes skill routing: given two or more
priority orderings over skills (e.g., "base routing" vs "adjusted/context-aware"),
find the matching that is weakly stable under their intersection.

Math basis (priority intersection stability from matching theory):
  A matching μ is weakly stable under priority intersection iff:
    ∀ (task t, skill s) not matched: either
      - s is not preferred to μ(t) under ALL priority orderings, OR
      - t is not preferred to μ(s) under ALL priority orderings.

  Equivalently: no blocking pair exists under the intersection ordering
  (a pair blocks only if BOTH orderings agree it should be matched).

  This prevents routing instability when two policies disagree:
  e.g., recency-weighted routing wants skill A, but content-similarity
  routing wants skill B — the intersection match picks the one that
  satisfies both orderings as much as possible.

Usage:
  python3 priority-intersection-matcher.py [--query "some task"] [--dry-run]
  python3 priority-intersection-matcher.py --list-skills
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

HOME       = Path.home()
SKILLS_DIR = HOME / ".hermes/skills"
CACHE_DIR  = _HH / "cache" / "monitors"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE   = CACHE_DIR / "priority-intersection-matches.json"


def _load_skills(max_skills: int = 30) -> dict[str, str]:
    skills: dict[str, str] = {}
    for sd in SKILLS_DIR.rglob("SKILL.md"):
        try:
            text = sd.read_text()
            m = re.search(r"description:\s*['\"]?(.+?)['\"]?\n", text)
            desc = m.group(1).strip() if m else sd.parent.name
            skills[sd.parent.name] = desc
            if len(skills) >= max_skills:
                break
        except Exception:
            pass
    return skills


def _keyword_score(query: str, text: str) -> float:
    wa = set(re.findall(r"[a-z]{3,}", query.lower()))
    wb = set(re.findall(r"[a-z]{3,}", text.lower()))
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / len(wa | wb)


def _recency_score(skill_name: str) -> float:
    """Proxy recency from SKILL.md mtime (more recent = higher recency)."""
    p = SKILLS_DIR.rglob(f"{skill_name}/SKILL.md")
    try:
        mtime = next(p).stat().st_mtime
        return mtime
    except StopIteration:
        return 0.0


def _build_priority_orderings(
    tasks: list[str],
    skills: dict[str, str],
) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    """
    Build two priority orderings for each task:
      P1: content-similarity ranking (jaccard overlap)
      P2: recency-weighted ranking (more recently used skills first)
    
    Returns (P1_per_task, P2_per_task): task → [skill, ...] ranked best-first.
    """
    skill_names = list(skills.keys())
    recency = {s: _recency_score(s) for s in skill_names}
    max_rec = max(recency.values()) or 1.0

    P1: dict[str, list[str]] = {}
    P2: dict[str, list[str]] = {}

    for task in tasks:
        # P1: similarity
        sim_scores = {s: _keyword_score(task, skills[s]) for s in skill_names}
        P1[task] = sorted(skill_names, key=lambda s: -sim_scores[s])

        # P2: recency + similarity blend (30% recency, 70% similarity)
        blend = {s: 0.7 * sim_scores[s] + 0.3 * (recency[s] / max_rec) for s in skill_names}
        P2[task] = sorted(skill_names, key=lambda s: -blend[s])

    return P1, P2


def _intersection_rank(skill: str, ordering1: list[str], ordering2: list[str]) -> float:
    """Average rank under both orderings (lower = better in both)."""
    r1 = ordering1.index(skill) if skill in ordering1 else len(ordering1)
    r2 = ordering2.index(skill) if skill in ordering2 else len(ordering2)
    return (r1 + r2) / 2.0


def _intersection_match(
    tasks: list[str],
    skills: dict[str, str],
    P1: dict[str, list[str]],
    P2: dict[str, list[str]],
) -> list[dict]:
    """
    Greedy stable matching under priority intersection:
    For each task, pick the highest-ranked skill under the intersection
    (average rank), without replacement (each skill matched once).
    """
    skill_names = list(skills.keys())
    available   = set(skill_names)
    matches: list[dict] = []

    for task in tasks:
        if not available:
            break
        # Score each available skill by its intersection rank
        ranked = sorted(
            available,
            key=lambda s: _intersection_rank(s, P1[task], P2[task]),
        )
        best = ranked[0]
        available.discard(best)
        r1 = P1[task].index(best) + 1
        r2 = P2[task].index(best) + 1
        matches.append({
            "task": task,
            "matched_skill": best,
            "rank_P1": r1,
            "rank_P2": r2,
            "intersection_rank": round(_intersection_rank(best, P1[task], P2[task]), 2),
            "stable": r1 <= 5 and r2 <= 5,  # weak stability: top-5 in both
        })

    return matches


def run(query: str | None, dry_run: bool, list_skills: bool) -> None:
    now    = datetime.now(timezone.utc).isoformat()
    skills = _load_skills()
    print(f"[priority-matcher] Loaded {len(skills)} skills")

    if list_skills:
        for name, desc in list(skills.items())[:20]:
            print(f"  {name}: {desc[:60]}")
        return

    # Split query into tasks (same as task-assignment-optimizer)
    if query:
        tasks = [t.strip() for t in re.split(r"\band\b|\bthen\b|,|;", query, flags=re.IGNORECASE)
                 if len(t.strip()) > 5]
    else:
        tasks = [
            "research arxiv papers",
            "implement code changes",
            "review and test",
        ]

    if not tasks:
        tasks = [query or "general task"]

    P1, P2 = _build_priority_orderings(tasks, skills)
    matches = _intersection_match(tasks, skills, P1, P2)

    print(f"\n=== Priority Intersection Matcher — {now[:10]} ===")
    print(f"Tasks: {len(tasks)},  Skills available: {len(skills)}")
    print(f"\n  {'Task':<30} → {'Skill':<35} P1  P2  ∩-rank  stable")
    print("  " + "-" * 82)
    for m in matches:
        s = "✓" if m["stable"] else "✗"
        print(f"  {m['task'][:29]:<30} → {m['matched_skill'][:34]:<35} "
              f"{m['rank_P1']:<4}{m['rank_P2']:<4}{m['intersection_rank']:<8.1f}{s}")

    unstable = [m for m in matches if not m["stable"]]
    if unstable:
        print(f"\n  Warning: {len(unstable)} task(s) matched outside top-5 in at least one ordering")

    if not dry_run:
        _tmp_out_file = OUT_FILE.with_suffix('.tmp')
        _tmp_out_file.write_text(json.dumps({
            "ts": now, "query": query, "matches": matches,
        }, indent=2))
        _tmp_out_file.replace(OUT_FILE)
        print(f"\nWritten: {OUT_FILE}")
    else:
        print("(dry-run)")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("query", nargs="?", default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--list-skills", action="store_true")
    args = parser.parse_args()
    run(query=args.query, dry_run=args.dry_run, list_skills=args.list_skills)


if __name__ == "__main__":
    main()
