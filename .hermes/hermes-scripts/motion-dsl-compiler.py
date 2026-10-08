#!/usr/bin/python3
"""
motion-dsl-compiler.py

Enables skill-chaining agents to plan complex multi-step sequences
by compiling a high-level task description into a typed, executable
Domain-Specific Language (DSL) plan — similar to how LAMP (Language-
Assisted Motion Planning) compiles language to robot trajectories.

CS SPIKE basis (LAMP: Language-Assisted Motion Planning for Controllable
Video Generation): applies motion planning DSL concepts to Hermes skill
chains. The "motion" is information flow; the "trajectory" is a sequence
of tool calls with typed inputs/outputs and constraint annotations.

Math basis: typed compositional DSL with constraint propagation
  Each DSL step has: tool, input_type, output_type, constraints
  Composition rule: step_i.output_type = step_{i+1}.input_type
  Type checking ensures the chain is well-typed before execution.

  Constraint types:
    MUST_PRECEDE(a, b)  — a must complete before b starts
    PRODUCES(a, key)    — a produces a value bound to 'key'
    CONSUMES(b, key)    — b requires 'key' in its context
    TIMEOUT(step, secs) — step must finish within secs
    RETRY(step, n)      — retry step up to n times on failure

  Output: executable JSON plan + human-readable DSL text

Usage:
  python3 motion-dsl-compiler.py "research papers then implement and test"
  python3 motion-dsl-compiler.py --task-file plan.txt
  python3 motion-dsl-compiler.py "..." --emit-json
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

HOME      = Path.home()
CACHE_DIR = HOME / ".hermes/cache/monitors"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE  = CACHE_DIR / "motion-dsl-plan.json"

# DSL vocabulary: verb phrases → (tool, input_type, output_type, constraints)
DSL_VERB_MAP: dict[str, dict] = {
    # Research verbs
    "research":     {"tool": "web_search",   "in": "query:str",   "out": "results:list", "retry": 2},
    "search":       {"tool": "web_search",   "in": "query:str",   "out": "results:list", "retry": 2},
    "fetch":        {"tool": "web_extract",  "in": "url:str",     "out": "content:str",  "retry": 1},
    "read":         {"tool": "read_file",    "in": "path:str",    "out": "text:str",     "retry": 0},
    "find":         {"tool": "search_files", "in": "pattern:str", "out": "matches:list", "retry": 0},
    # Implementation verbs
    "implement":    {"tool": "write_file",   "in": "content:str", "out": "path:str",     "retry": 0},
    "write":        {"tool": "write_file",   "in": "content:str", "out": "path:str",     "retry": 0},
    "create":       {"tool": "write_file",   "in": "content:str", "out": "path:str",     "retry": 0},
    "edit":         {"tool": "patch",        "in": "diff:str",    "out": "path:str",     "retry": 0},
    "fix":          {"tool": "patch",        "in": "diff:str",    "out": "path:str",     "retry": 1},
    "update":       {"tool": "patch",        "in": "diff:str",    "out": "path:str",     "retry": 0},
    # Execution verbs
    "run":          {"tool": "terminal",     "in": "cmd:str",     "out": "output:str",   "retry": 1, "timeout": 120},
    "test":         {"tool": "terminal",     "in": "cmd:str",     "out": "output:str",   "retry": 2, "timeout": 180},
    "execute":      {"tool": "execute_code", "in": "code:str",    "out": "result:any",   "retry": 1},
    "debug":        {"tool": "terminal",     "in": "cmd:str",     "out": "output:str",   "retry": 3, "timeout": 60},
    "verify":       {"tool": "execute_code", "in": "code:str",    "out": "bool",         "retry": 1},
    "compile":      {"tool": "terminal",     "in": "cmd:str",     "out": "output:str",   "retry": 1},
    # Memory/skill verbs
    "remember":     {"tool": "memory",       "in": "fact:str",    "out": "handle:str",   "retry": 0},
    "load skill":   {"tool": "skill_view",   "in": "name:str",    "out": "skill:str",    "retry": 0},
    "save skill":   {"tool": "skill_manage", "in": "skill:dict",  "out": "name:str",     "retry": 0},
    # Delegation verbs
    "delegate":     {"tool": "delegate_task","in": "task:str",    "out": "result:any",   "retry": 0, "timeout": 1800},
    "spawn":        {"tool": "delegate_task","in": "task:str",    "out": "result:any",   "retry": 0, "timeout": 1800},
    # Review verbs
    "review":       {"tool": "read_file",    "in": "path:str",    "out": "text:str",     "retry": 0},
    "summarise":    {"tool": "execute_code", "in": "text:str",    "out": "summary:str",  "retry": 1},
    "analyse":      {"tool": "execute_code", "in": "data:any",    "out": "analysis:str", "retry": 1},
}

# Type compatibility matrix (which output types feed which input types)
TYPE_COMPAT: dict[str, set[str]] = {
    "results:list": {"query:str", "content:str", "url:str"},
    "content:str":  {"path:str", "cmd:str", "code:str", "diff:str", "text:str"},
    "text:str":     {"path:str", "cmd:str", "code:str", "diff:str", "content:str"},
    "path:str":     {"path:str", "cmd:str", "code:str"},
    "output:str":   {"content:str", "text:str", "code:str"},
    "result:any":   {"content:str", "text:str", "data:any"},
    "matches:list": {"pattern:str", "content:str"},
    "bool":         set(),
    "handle:str":   set(),
    "skill:str":    {"cmd:str"},
    "name:str":     set(),
    "analysis:str": {"content:str", "text:str"},
    "summary:str":  {"content:str", "text:str"},
}


def _parse_clauses(task: str) -> list[str]:
    return [c.strip() for c in
            re.split(r"\bthen\b|\band\b|\bafter\b|\bfinally\b|,|;", task, flags=re.IGNORECASE)
            if len(c.strip()) > 3]


def _match_verb(clause: str) -> tuple[str | None, dict | None]:
    """Find the best matching DSL verb for a clause."""
    clause_l = clause.lower()
    # Try multi-word verbs first (longest match)
    for verb in sorted(DSL_VERB_MAP, key=len, reverse=True):
        if verb in clause_l:
            return verb, DSL_VERB_MAP[verb]
    # Fallback: first content word
    words = re.findall(r"[a-z]{3,}", clause_l)
    for w in words:
        if w in DSL_VERB_MAP:
            return w, DSL_VERB_MAP[w]
    return None, None


def _type_check(steps: list[dict]) -> list[str]:
    """Check type compatibility of adjacent steps. Returns list of type errors."""
    errors = []
    for i in range(1, len(steps)):
        prev_out = steps[i - 1]["out_type"]
        curr_in  = steps[i]["in_type"]
        compat   = TYPE_COMPAT.get(prev_out, set())
        if curr_in not in compat and prev_out != curr_in:
            errors.append(
                f"Type mismatch step {i}→{i+1}: "
                f"{steps[i-1]['verb']} produces {prev_out} but "
                f"{steps[i]['verb']} expects {curr_in}"
            )
    return errors


def compile_plan(task: str) -> dict:
    now     = datetime.now(timezone.utc).isoformat()
    clauses = _parse_clauses(task)
    steps   = []

    for idx, clause in enumerate(clauses):
        verb, spec = _match_verb(clause)
        if verb is None or spec is None:
            steps.append({
                "step": idx + 1, "clause": clause, "verb": "UNKNOWN",
                "tool": "execute_code", "in_type": "any", "out_type": "any",
                "retry": 0, "timeout": 180, "constraints": [],
            })
            continue

        constraints = []
        if idx > 0:
            constraints.append(f"MUST_PRECEDE(step_{idx}, step_{idx+1})")
        if idx > 0:
            constraints.append(f"CONSUMES(step_{idx+1}, output_of_step_{idx})")
        constraints.append(f"PRODUCES(step_{idx+1}, result_{idx+1})")

        steps.append({
            "step":        idx + 1,
            "clause":      clause,
            "verb":        verb,
            "tool":        spec["tool"],
            "in_type":     spec["in"],
            "out_type":    spec["out"],
            "retry":       spec.get("retry", 0),
            "timeout":     spec.get("timeout", 180),
            "constraints": constraints,
        })

    type_errors = _type_check(steps)

    return {
        "ts":          now,
        "task":        task,
        "steps":       steps,
        "n_steps":     len(steps),
        "type_errors": type_errors,
        "well_typed":  len(type_errors) == 0,
    }


def _emit_dsl_text(plan: dict) -> str:
    lines = [f"PLAN: {plan['task']}", f"STEPS: {plan['n_steps']}", ""]
    for s in plan["steps"]:
        lines.append(f"  step {s['step']}: {s['verb'].upper()}")
        lines.append(f"    tool:    {s['tool']}")
        lines.append(f"    in:      {s['in_type']}")
        lines.append(f"    out:     {s['out_type']}")
        if s["retry"]:
            lines.append(f"    retry:   {s['retry']}")
        if s["timeout"] != 180:
            lines.append(f"    timeout: {s['timeout']}s")
        for c in s["constraints"]:
            lines.append(f"    @ {c}")
        lines.append("")
    if plan["type_errors"]:
        lines.append("TYPE ERRORS:")
        for e in plan["type_errors"]:
            lines.append(f"  ! {e}")
    else:
        lines.append("TYPE CHECK: OK")
    return "\n".join(lines)


def run(task: str, emit_json: bool, dry_run: bool) -> None:
    plan = compile_plan(task)
    dsl  = _emit_dsl_text(plan)

    print(f"\n=== Motion DSL Compiler — {plan['ts'][:10]} ===")
    print(dsl)

    if not dry_run:
        out_data = plan if emit_json else {**plan, "dsl_text": dsl}
        _tmp_out_file = OUT_FILE.with_suffix('.tmp')
        _tmp_out_file.write_text(json.dumps(out_data, indent=2))
        _tmp_out_file.replace(OUT_FILE)
        print(f"\nWritten: {OUT_FILE}")
    else:
        print("(dry-run)")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("task", nargs="?",
                        default="research arxiv papers then implement findings and test")
    parser.add_argument("--emit-json", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run(task=args.task, emit_json=args.emit_json, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
