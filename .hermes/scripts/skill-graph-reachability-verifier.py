#!/usr/bin/python3
"""
skill-graph-reachability-verifier.py

Enables offline verification that multi-skill orchestration plans will
actually reach their intended goal state — catches dead-end skill chains
before execution wastes budget.

Math basis: reachability in a typed directed skill graph
  Nodes: skills (identified by name)
  Edges: skill A → skill B if A's postconditions satisfy B's preconditions
  Goal: given a start skill and target skill, is target reachable via BFS?
  Additional check: no-exit nodes (skills with no outgoing edges and
  non-terminal postconditions) signal dead-ends in the plan.

Usage:
  python3 skill-graph-reachability-verifier.py --from SKILL --to SKILL
  python3 skill-graph-reachability-verifier.py --plan plan.json
  python3 skill-graph-reachability-verifier.py --audit-all
  python3 skill-graph-reachability-verifier.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path

HOME       = Path.home()
SKILLS_DIR = HOME / ".hermes/skills"
FORK_SKILLS = HOME / ".hermes/profiles/fork/skills"
CACHE_DIR  = HOME / ".hermes/cache/monitors"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE      = CACHE_DIR / "skill-graph-reachability-report.json"
BASELINE_FILE = CACHE_DIR / "skill-graph-reachability-baseline.json"

# Keyword sets for postcondition/precondition matching
POSTCOND_HEADERS = re.compile(r"(?i)^#{1,4}\s*(after|output|result|produces?|postcondition)")
PRECOND_HEADERS  = re.compile(r"(?i)^#{1,4}\s*(before|requires?|precondition|setup|input)")
TERMINAL_WORDS   = {"done", "complete", "finished", "deployed", "saved", "written", "verified"}


def _extract_skill_meta(path: Path) -> dict:
    """Extract name, precondition keywords, postcondition keywords."""
    try:
        text  = path.read_text()
        lines = text.splitlines()
    except Exception:
        return {}

    name = path.parent.name if path.name == "SKILL.md" else path.stem
    pre_kw: set[str] = set()
    post_kw: set[str] = set()
    mode = None

    for line in lines:
        if PRECOND_HEADERS.match(line):
            mode = "pre"
        elif POSTCOND_HEADERS.match(line):
            mode = "post"
        elif line.startswith("#"):
            mode = None

        if mode and not line.startswith("#"):
            words = set(re.findall(r"[a-z]{4,}", line.lower()))
            if mode == "pre":
                pre_kw |= words
            else:
                post_kw |= words

    # Fallback: extract from description line (first non-header line)
    if not pre_kw and not post_kw:
        for line in lines[:20]:
            if line.strip() and not line.startswith("#"):
                pre_kw = set(re.findall(r"[a-z]{4,}", line.lower()))
                break

    return {"name": name, "pre": pre_kw, "post": post_kw, "path": str(path)}


def _build_graph(skills: list[dict]) -> dict[str, list[str]]:
    """Build adjacency list: skill → list of skills it enables."""
    graph: dict[str, list[str]] = defaultdict(list)

    for i, a in enumerate(skills):
        for j, b in enumerate(skills):
            if i == j:
                continue
            # Edge A→B if A's postconditions overlap B's preconditions
            overlap = a["post"] & b["pre"]
            if len(overlap) >= 2:   # require ≥2 keyword overlap
                graph[a["name"]].append(b["name"])

    return dict(graph)


def _bfs_reachable(graph: dict[str, list[str]], start: str) -> set[str]:
    visited = {start}
    queue   = deque([start])
    while queue:
        node = queue.popleft()
        for nb in graph.get(node, []):
            if nb not in visited:
                visited.add(nb)
                queue.append(nb)
    return visited


def _find_dead_ends(skills: list[dict], graph: dict[str, list[str]]) -> list[str]:
    dead_ends = []
    for skill in skills:
        name = skill["name"]
        if name not in graph or not graph[name]:
            # No outgoing edges — check if postconditions look terminal
            post_text = " ".join(skill["post"])
            if not any(w in post_text for w in TERMINAL_WORDS):
                dead_ends.append(name)
    return dead_ends


def run(from_skill: str | None, to_skill: str | None,
        plan_file: Path | None, audit_all: bool, dry_run: bool) -> int:
    now = datetime.now(timezone.utc).isoformat()

    # Load skills
    skill_files: list[Path] = []
    for base in [SKILLS_DIR, FORK_SKILLS]:
        if base.exists():
            skill_files.extend(base.rglob("SKILL.md"))

    skills = [_extract_skill_meta(f) for f in skill_files]
    skills = [s for s in skills if s.get("name")]

    print(f"\n=== Skill Graph Reachability Verifier — {now[:10]} ===")
    print(f"Skills loaded: {len(skills)}")

    graph     = _build_graph(skills)
    edge_count = sum(len(v) for v in graph.values())
    print(f"Graph: {len(graph)} nodes with edges, {edge_count} total edges")

    results: list[dict] = []

    if from_skill and to_skill:
        # Point-to-point reachability
        reachable = _bfs_reachable(graph, from_skill)
        ok        = to_skill in reachable
        print(f"\n  {from_skill} → {to_skill}: {'REACHABLE' if ok else 'UNREACHABLE'}")
        print(f"  ({len(reachable)} skills reachable from {from_skill})")
        results.append({"from": from_skill, "to": to_skill, "reachable": ok})
        alarm_exit = 0 if ok else 1

    elif plan_file and plan_file.exists():
        plan   = json.loads(plan_file.read_text())
        chain  = plan.get("skills", plan.get("steps", []))
        broken = []
        for i in range(len(chain) - 1):
            a, b   = chain[i], chain[i+1]
            reach  = _bfs_reachable(graph, a)
            if b not in reach:
                broken.append((a, b))
        if broken:
            print(f"\nBroken links in plan:")
            for a, b in broken:
                print(f"  {a} ↛ {b}")
            alarm_exit = 1
        else:
            print(f"\nPlan is fully reachable ({len(chain)} skills)")
            alarm_exit = 0
        results.append({"plan": str(plan_file), "broken": broken})

    else:
        # Audit: find all dead-end skills and connectivity stats
        dead_ends     = _find_dead_ends(skills, graph)
        isolated      = [s["name"] for s in skills if s["name"] not in graph]
        largest_comp  = max((len(_bfs_reachable(graph, s["name"])) for s in skills[:20]), default=0)

        print(f"Dead-end skills (no outgoing edges, non-terminal): {len(dead_ends)}")
        print(f"Isolated skills (no edges at all): {len(isolated)}")
        print(f"Largest reachable component (sample): {largest_comp} skills")

        if dead_ends[:5]:
            print(f"Sample dead-ends: {dead_ends[:5]}")

        results.append({
            "dead_ends": len(dead_ends),
            "isolated":  len(isolated),
            "largest_component": largest_comp,
        })
        alarm_exit = 0
        # Only alarm if dead-end count has INCREASED from baseline (not just the permanent baseline state)
        baseline_dead = 0
        if BASELINE_FILE.exists():
            try:
                bl = json.loads(BASELINE_FILE.read_text())
                baseline_dead = bl.get("dead_ends", 0)
            except Exception:
                pass
        else:
            # First run: write baseline, don't alarm
            BASELINE_FILE.write_text(json.dumps({"dead_ends": len(dead_ends), "ts": now}, indent=2))
            baseline_dead = len(dead_ends)

        new_dead = len(dead_ends) - baseline_dead
        if new_dead > 5:   # alarm only when 5+ new dead-ends appear beyond baseline
            alarm_exit = 1
            print(f"\nALARM: yes — {new_dead} new dead-end skills since baseline (total={len(dead_ends)}, baseline={baseline_dead})")
        else:
            print(f"\nALARM: no — dead-end count stable (total={len(dead_ends)}, baseline={baseline_dead}, delta={new_dead:+d})")

    if not dry_run:
        OUT_FILE.write_text(json.dumps({"ts": now, "results": results}, indent=2))

    return alarm_exit


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--from",      dest="from_skill", default=None)
    p.add_argument("--to",        dest="to_skill",   default=None)
    p.add_argument("--plan",      type=Path,         default=None)
    p.add_argument("--audit-all", action="store_true")
    p.add_argument("--dry-run",   action="store_true")
    args = p.parse_args()
    sys.exit(run(args.from_skill, args.to_skill, args.plan, args.audit_all, args.dry_run))


if __name__ == "__main__":
    main()
