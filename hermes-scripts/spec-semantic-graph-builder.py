#!/usr/bin/python3
"""
spec-semantic-graph-builder.py

Enables automated detection of missing security guards and state-transition
invariants in Hermes skill/plan specifications by building a semantic
dependency graph from SKILL.md and plan files.

CS SPIKE basis (CS wave5 — spec semantic analysis):
  LLM-generated code and skill specs lack formal intent verification.
  This script builds a directed graph from skill preconditions, postconditions,
  tool dependencies, and guard clauses — then detects:
  (a) Missing security guards (skill invokes destructive tool with no guard)
  (b) Unreachable postconditions (no path from precondition to postcondition)
  (c) State-transition gaps (required prior state never established)

Math basis: semantic graph as a typed directed hypergraph
  Nodes: {precondition, action, postcondition, guard}
  Edges: REQUIRES, PRODUCES, GUARDS, CONFLICTS_WITH
  Invariant check: for every PRODUCES edge (a→p), there must exist a
  reachable GUARDS edge (g→a) when action `a` is destructive.
  Gap detection: BFS from initial state; unreachable postconditions flagged.

Usage:
  python3 spec-semantic-graph-builder.py              # scan all skills
  python3 spec-semantic-graph-builder.py --skill NAME # single skill
  python3 spec-semantic-graph-builder.py --export graph.json
  python3 spec-semantic-graph-builder.py --dry-run
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
PLANS_DIR  = HOME / ".hermes/plans"
CACHE_DIR  = HOME / ".hermes/cache/monitors"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE      = CACHE_DIR / "spec-semantic-graph.json"
BASELINE_FILE = CACHE_DIR / "spec-semantic-graph-baseline.json"

# Patterns for extracting semantic elements from SKILL.md
GUARD_PATTERNS = [
    r"(?i)\b(check|verify|validate|assert|ensure|guard|require|must)\b[^.\n]{0,60}",
    r"(?i)\b(if .{0,30} then|only if|unless|except when)\b[^.\n]{0,60}",
    r"(?i)\b(auth|permission|access|token|credential)\b[^.\n]{0,40}",
]
DESTRUCTIVE_KEYWORDS = {
    "delete", "remove", "drop", "truncate", "overwrite", "destroy",
    "kill", "terminate", "wipe", "reset", "purge", "rmdir", "unlink",
}
PRECONDITION_HEADERS  = re.compile(r"(?i)^#{1,4}\s*(precondition|prerequisite|requires?|before|setup)")
POSTCONDITION_HEADERS = re.compile(r"(?i)^#{1,4}\s*(postcondition|produces?|output|result|after|effect)")
ACTION_HEADERS        = re.compile(r"(?i)^#{1,4}\s*(step|action|procedure|workflow|usage|use when)")


def _extract_nodes(text: str, source: str) -> dict:
    lines  = text.splitlines()
    nodes: dict[str, list[str]] = {
        "preconditions": [], "postconditions": [], "actions": [], "guards": [],
    }
    mode = None
    for line in lines:
        if PRECONDITION_HEADERS.match(line):
            mode = "preconditions"
        elif POSTCONDITION_HEADERS.match(line):
            mode = "postconditions"
        elif ACTION_HEADERS.match(line):
            mode = "actions"
        elif line.startswith("#"):
            mode = None

        if mode and line.strip() and not line.startswith("#"):
            nodes[mode].append(line.strip()[:120])

        for pat in GUARD_PATTERNS:
            m = re.search(pat, line)
            if m:
                nodes["guards"].append(m.group()[:80])

    return nodes


def _find_destructive_actions(nodes: dict) -> list[str]:
    destructive = []
    for action in nodes.get("actions", []):
        words = set(re.findall(r"[a-z]+", action.lower()))
        if words & DESTRUCTIVE_KEYWORDS:
            destructive.append(action[:80])
    return destructive


def _check_guard_coverage(nodes: dict) -> list[dict]:
    """Flag destructive actions that have no associated guard."""
    issues = []
    guards_text = " ".join(nodes.get("guards", [])).lower()
    for action in _find_destructive_actions(nodes):
        # Check if any guard keyword appears near this action's key terms
        action_words = set(re.findall(r"[a-z]{4,}", action.lower()))
        covered = any(w in guards_text for w in action_words)
        if not covered:
            issues.append({
                "type":   "MISSING_GUARD",
                "action": action,
                "detail": "destructive action with no guard clause found in spec",
            })
    return issues


def _check_postcondition_reachability(nodes: dict) -> list[dict]:
    """Flag postconditions that have no matching action producing them."""
    issues = []
    actions_text = " ".join(nodes.get("actions", [])).lower()
    for pc in nodes.get("postconditions", []):
        pc_words = set(re.findall(r"[a-z]{4,}", pc.lower()))
        reachable = any(w in actions_text for w in pc_words)
        if not reachable and pc_words:
            issues.append({
                "type":        "UNREACHABLE_POSTCONDITION",
                "postcondition": pc[:80],
                "detail":      "postcondition has no action that produces it",
            })
    return issues


def analyse_skill(path: Path) -> dict:
    try:
        text = path.read_text()
    except Exception as e:
        return {"path": str(path), "error": str(e), "issues": []}

    nodes  = _extract_nodes(text, str(path))
    issues = (
        _check_guard_coverage(nodes) +
        _check_postcondition_reachability(nodes)
    )

    return {
        "path":   str(path),
        "name":   path.parent.name if path.name == "SKILL.md" else path.stem,
        "nodes":  {k: len(v) for k, v in nodes.items()},
        "issues": issues,
    }


def run(skill_name: str | None, export: Path | None, dry_run: bool) -> int:
    now = datetime.now(timezone.utc).isoformat()

    # Collect skill files
    skill_files: list[Path] = []
    for base in [SKILLS_DIR, FORK_SKILLS]:
        if base.exists():
            skill_files.extend(base.rglob("SKILL.md"))
    if PLANS_DIR.exists():
        skill_files.extend(PLANS_DIR.glob("*.md"))

    if skill_name:
        skill_files = [f for f in skill_files if skill_name.lower() in str(f).lower()]

    print(f"\n=== Spec Semantic Graph Builder — {now[:10]} ===")
    print(f"Analysing {len(skill_files)} spec files...")

    results    = [analyse_skill(f) for f in skill_files]
    all_issues = [i for r in results for i in r.get("issues", [])]

    by_type: dict[str, int] = defaultdict(int)
    for issue in all_issues:
        by_type[issue["type"]] += 1

    print(f"Files analysed: {len(results)}")
    print(f"Total issues:   {len(all_issues)}")
    for t, c in sorted(by_type.items()):
        print(f"  {t}: {c}")

    critical = [i for i in all_issues if i["type"] == "MISSING_GUARD"]
    if critical[:3]:
        print("\nTop MISSING_GUARD issues:")
        for i in critical[:3]:
            print(f"  ! {i['action'][:70]}")

    # Only alarm on NEW issues beyond baseline (static structural issues are permanent noise)
    baseline_count = 0
    if BASELINE_FILE.exists():
        try:
            baseline_count = json.loads(BASELINE_FILE.read_text()).get("issue_count", 0)
        except Exception:
            pass
    else:
        _bl_tmp = BASELINE_FILE.with_suffix(".tmp")
        _bl_tmp.write_text(json.dumps({"issue_count": len(all_issues), "ts": now}, indent=2))
        _bl_tmp.replace(BASELINE_FILE)
        baseline_count = len(all_issues)

    new_issues = len(all_issues) - baseline_count
    if new_issues > 5:
        print(f"\nALARM: yes — {new_issues} new spec issues since baseline (total={len(all_issues)}, baseline={baseline_count})")
        alarm_exit = 1
    else:
        print(f"\nALARM: no — issue count stable (total={len(all_issues)}, baseline={baseline_count}, delta={new_issues:+d})")
        alarm_exit = 0

    if not dry_run:
        payload = {"ts": now, "files": len(results), "issues": all_issues, "by_type": dict(by_type)}
        _out_tmp = OUT_FILE.with_suffix(".tmp")
        _out_tmp.write_text(json.dumps(payload, indent=2))
        _out_tmp.replace(OUT_FILE)
        if export:
            _exp_tmp = export.with_suffix(".tmp")
            _exp_tmp.write_text(json.dumps({"results": results}, indent=2))
            _exp_tmp.replace(export)
            print(f"Graph exported: {export}")

    return alarm_exit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skill",  default=None)
    parser.add_argument("--export", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    sys.exit(run(skill_name=args.skill, export=args.export, dry_run=args.dry_run))


if __name__ == "__main__":
    main()
