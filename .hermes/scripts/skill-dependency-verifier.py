#!/usr/bin/python3
"""
skill-dependency-verifier.py

Allows Hermes to pre-verify complex multi-agent task plans against safety
invariants before execution: detects skill-delegation cycles, impossible
task plans, missing prerequisites, and circular dependencies.

Research basis (arXiv core agent sweep — skill dependency invariant checking):
  Before dispatching a multi-agent plan, verify that the dependency graph
  is a DAG (directed acyclic graph) with all prerequisites satisfiable.

Math basis: topological sort + reachability on dependency graph
  Given a plan P = {(task_i, skill_i, deps_i)}, verify:
  1. DAG property: no cycles (Kahn's algorithm)
  2. Satisfiability: all deps_i are produced by some earlier task
  3. Capacity: no skill appears more than max_parallel times concurrently
  4. Completeness: all output types required by later steps are produced

  Outputs: VALID / CYCLE / UNSATISFIABLE / CAPACITY_EXCEEDED with detail.

Usage:
  python3 skill-dependency-verifier.py plan.json
  python3 skill-dependency-verifier.py --example   # run built-in example
  python3 skill-dependency-verifier.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path

HOME      = Path.home()
CACHE_DIR = HOME / ".hermes/cache/monitors"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE  = CACHE_DIR / "skill-dependency-report.json"

MAX_PARALLEL = 3   # max concurrent instances of the same skill


def _kahn_topo(nodes: list[str], edges: list[tuple[str, str]]) -> tuple[list[str], list[tuple[str, str]]]:
    """
    Kahn's topological sort.
    Returns (order, cycle_edges). If cycle_edges is non-empty, graph has a cycle.
    """
    in_degree: dict[str, int] = {n: 0 for n in nodes}
    adj: dict[str, list[str]] = defaultdict(list)
    for src, dst in edges:
        adj[src].append(dst)
        in_degree[dst] = in_degree.get(dst, 0) + 1

    queue = deque(n for n in nodes if in_degree.get(n, 0) == 0)
    order: list[str] = []
    while queue:
        n = queue.popleft()
        order.append(n)
        for succ in adj[n]:
            in_degree[succ] -= 1
            if in_degree[succ] == 0:
                queue.append(succ)

    # Any node not in order is part of a cycle
    unvisited = set(nodes) - set(order)
    cycle_edges = [(s, d) for s, d in edges if s in unvisited or d in unvisited]
    return order, cycle_edges


def _build_level_sets(nodes: list[str], edges: list[tuple[str, str]],
                      topo_order: list[str]) -> list[list[str]]:
    """Assign each node to a level (parallel execution wave)."""
    level: dict[str, int] = {n: 0 for n in nodes}
    adj: dict[str, list[str]] = defaultdict(list)
    for src, dst in edges:
        adj[src].append(dst)
    for n in topo_order:
        for succ in adj[n]:
            level[succ] = max(level[succ], level[n] + 1)
    max_lv = max(level.values(), default=0)
    return [[n for n, lv in level.items() if lv == i] for i in range(max_lv + 1)]


def verify_plan(plan: dict) -> dict:
    """
    Verify a task plan dict with structure:
      {
        "tasks": [
          {"id": "t1", "skill": "web_search", "deps": [], "produces": ["results"],
           "requires": []},
          {"id": "t2", "skill": "write_file", "deps": ["t1"], "requires": ["results"],
           "produces": ["file_path"]},
          ...
        ]
      }
    Returns verification report dict.
    """
    now    = datetime.now(timezone.utc).isoformat()
    tasks  = plan.get("tasks", [])
    errors: list[str] = []
    warnings: list[str] = []

    if not tasks:
        return {"status": "EMPTY", "ts": now, "errors": ["No tasks in plan"], "warnings": []}

    node_ids  = [t["id"] for t in tasks]
    task_map  = {t["id"]: t for t in tasks}

    # Build dependency edges
    dep_edges: list[tuple[str, str]] = []
    for t in tasks:
        for dep in t.get("deps", []):
            if dep not in task_map:
                errors.append(f"MISSING_DEP: task '{t['id']}' depends on unknown task '{dep}'")
            else:
                dep_edges.append((dep, t["id"]))  # dep must complete before t

    # 1. Cycle check
    topo_order, cycle_edges = _kahn_topo(node_ids, dep_edges)
    if cycle_edges:
        errors.append(f"CYCLE: circular dependency detected — {cycle_edges[:3]}")

    # 2. Satisfiability: check that all 'requires' tokens are produced by dependencies
    produced: dict[str, str] = {}  # token → producing task_id
    for task_id in topo_order:
        t = task_map[task_id]
        for req in t.get("requires", []):
            if req not in produced:
                errors.append(
                    f"UNSATISFIED: task '{task_id}' requires '{req}' but no preceding "
                    f"task produces it"
                )
        for prod in t.get("produces", []):
            if prod in produced:
                warnings.append(
                    f"OVERWRITE: task '{task_id}' produces '{prod}' which was already "
                    f"produced by task '{produced[prod]}'"
                )
            produced[prod] = task_id

    # 3. Capacity check: count concurrent skill instances per wave
    level_sets = _build_level_sets(node_ids, dep_edges, topo_order)
    for lv_idx, wave in enumerate(level_sets):
        skill_counts: dict[str, int] = defaultdict(int)
        for tid in wave:
            skill = task_map[tid].get("skill", "unknown")
            skill_counts[skill] += 1
        for skill, cnt in skill_counts.items():
            if cnt > MAX_PARALLEL:
                warnings.append(
                    f"CAPACITY: wave {lv_idx} has {cnt} concurrent '{skill}' instances "
                    f"(max {MAX_PARALLEL})"
                )

    # 4. Check for tasks that produce nothing (dead-end sinks without terminal intent)
    all_deps = {dep for t in tasks for dep in t.get("deps", [])}
    dead_sinks = [t["id"] for t in tasks if t["id"] not in all_deps
                  and not t.get("produces") and len(tasks) > 1]
    if dead_sinks:
        warnings.append(f"DEAD_SINK: tasks {dead_sinks} produce nothing and have no dependents")

    status = "VALID" if not errors else (
        "CYCLE" if any("CYCLE" in e for e in errors) else
        "UNSATISFIABLE" if any("UNSATISFIED" in e for e in errors) else
        "INVALID"
    )

    return {
        "ts": now,
        "status": status,
        "n_tasks": len(tasks),
        "topo_order": topo_order,
        "level_sets": level_sets,
        "errors": errors,
        "warnings": warnings,
        "produced_tokens": list(produced.keys()),
    }


EXAMPLE_PLAN = {
    "tasks": [
        {"id": "search",    "skill": "web_search",   "deps": [],
         "requires": [],                    "produces": ["results"]},
        {"id": "extract",   "skill": "web_extract",  "deps": ["search"],
         "requires": ["results"],           "produces": ["content"]},
        {"id": "implement", "skill": "write_file",   "deps": ["extract"],
         "requires": ["content"],           "produces": ["file_path"]},
        {"id": "test",      "skill": "terminal",     "deps": ["implement"],
         "requires": ["file_path"],         "produces": ["test_output"]},
        {"id": "save",      "skill": "skill_manage", "deps": ["test"],
         "requires": ["test_output", "file_path"], "produces": ["skill_name"]},
    ]
}

CYCLE_PLAN = {
    "tasks": [
        {"id": "a", "skill": "web_search", "deps": ["c"], "requires": [], "produces": ["x"]},
        {"id": "b", "skill": "write_file", "deps": ["a"], "requires": ["x"], "produces": ["y"]},
        {"id": "c", "skill": "terminal",   "deps": ["b"], "requires": ["y"], "produces": ["z"]},
    ]
}


def _print_report(report: dict) -> None:
    status = report["status"]
    flag = "PASS" if status == "VALID" else "FAIL"
    print(f"\n  Status: [{flag}] {status}")
    print(f"  Tasks: {report['n_tasks']}  |  Topo order: {report['topo_order']}")
    if report.get("level_sets"):
        print(f"  Execution waves:")
        for i, wave in enumerate(report["level_sets"]):
            print(f"    Wave {i}: {wave}")
    if report["errors"]:
        print(f"  Errors ({len(report['errors'])}):")
        for e in report["errors"]:
            print(f"    ! {e}")
    if report["warnings"]:
        print(f"  Warnings ({len(report['warnings'])}):")
        for w in report["warnings"]:
            print(f"    ~ {w}")
    if not report["errors"] and not report["warnings"]:
        print(f"  Produced tokens: {report['produced_tokens']}")
        print("  No errors or warnings.")


def run(plan_path: Path | None, example: bool, dry_run: bool) -> int:
    now = datetime.now(timezone.utc).isoformat()
    print(f"\n=== Skill Dependency Verifier — {now[:10]} ===")

    plans = []
    if example:
        plans = [("example_valid", EXAMPLE_PLAN), ("example_cycle", CYCLE_PLAN)]
    elif plan_path and plan_path.exists():
        plans = [(plan_path.stem, json.loads(plan_path.read_text()))]
    else:
        print("No plan provided. Run with --example or pass a plan.json path.")
        return 0

    all_reports = []
    any_fail = False
    for name, plan in plans:
        print(f"\nPlan: {name}")
        report = verify_plan(plan)
        _print_report(report)
        all_reports.append({"name": name, **report})
        if report["status"] != "VALID":
            any_fail = True

    if not dry_run:
        _tmp_out_file = OUT_FILE.with_suffix('.tmp')
        _tmp_out_file.write_text(json.dumps({"ts": now, "reports": all_reports}, indent=2))
        _tmp_out_file.replace(OUT_FILE)
        print(f"\nWritten: {OUT_FILE}")
    else:
        print("\n(dry-run)")

    return 1 if any_fail else 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("plan_path", nargs="?", type=Path, default=None)
    parser.add_argument("--example", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    sys.exit(run(plan_path=args.plan_path, example=args.example, dry_run=args.dry_run))


if __name__ == "__main__":
    main()
