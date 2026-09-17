#!/usr/bin/python3
"""
privacy-constrained-skill-router.py

Enforces fine-grained data governance when routing tasks to skills —
prevents PII, secrets, or sensitive data from flowing to skills that
lack appropriate data-handling declarations.

Math basis: lattice-based information flow control (Bell-LaPadula variant)
  Sensitivity levels form a lattice L = {PUBLIC < INTERNAL < CONFIDENTIAL < SECRET}
  A task with sensitivity level s can only be routed to a skill with
  declared clearance c where c ≥ s in the lattice ordering.
  
  Additionally: track taint propagation — if any input token matches a
  PII pattern, the task sensitivity is raised to at least CONFIDENTIAL.

Usage:
  python3 privacy-constrained-skill-router.py --task TASK --skill SKILL
  python3 privacy-constrained-skill-router.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

HOME      = Path.home()
CACHE_DIR = HOME / ".hermes/cache/monitors"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE  = CACHE_DIR / "privacy-routing-decisions.json"

# Sensitivity lattice (ordered low→high)
LEVELS = ["PUBLIC", "INTERNAL", "CONFIDENTIAL", "SECRET"]

# PII / sensitive data patterns → minimum sensitivity level
PII_PATTERNS: list[tuple[str, str]] = [
    (r"\b\d{3}-\d{2}-\d{4}\b",                    "SECRET"),       # SSN
    (r"\b4[0-9]{12}(?:[0-9]{3})?\b",              "SECRET"),       # Visa card
    (r"(?i)\bpassword\b",                           "CONFIDENTIAL"), # password mention
    (r"(?i)\bapi[_\s]?key\b",                       "CONFIDENTIAL"), # API key
    (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.\w+\b","CONFIDENTIAL"), # email
    (r"(?i)\bpii\b|\bpersonal.?data\b",             "CONFIDENTIAL"), # explicit PII ref
    (r"(?i)\bsecret\b|\btoken\b|\bcredential\b",    "CONFIDENTIAL"), # secret/token
    (r"(?i)\binternal\b|\bconfidential\b",           "INTERNAL"),    # internal data
]

# Skill clearance declarations (extend by reading skill frontmatter)
SKILL_CLEARANCES: dict[str, str] = {
    "web_search":        "PUBLIC",
    "web_extract":       "PUBLIC",
    "terminal":          "INTERNAL",
    "write_file":        "INTERNAL",
    "read_file":         "INTERNAL",
    "execute_code":      "INTERNAL",
    "browser_exec":      "CONFIDENTIAL",
    "browser_vault_fill":"SECRET",
    "memory":            "CONFIDENTIAL",
    "skill_manage":      "INTERNAL",
    "delegate_task":     "CONFIDENTIAL",
}


def _level_idx(level: str) -> int:
    return LEVELS.index(level) if level in LEVELS else 0


def _detect_sensitivity(task: str) -> tuple[str, list[str]]:
    """Return (max_sensitivity_level, list_of_matched_reasons)."""
    level  = "PUBLIC"
    reasons: list[str] = []
    for pattern, min_level in PII_PATTERNS:
        if re.search(pattern, task):
            reasons.append(f"{pattern[:30]} → {min_level}")
            if _level_idx(min_level) > _level_idx(level):
                level = min_level
    return level, reasons


def route(task: str, skill: str) -> dict:
    task_level, reasons = _detect_sensitivity(task)
    skill_level = SKILL_CLEARANCES.get(skill, "PUBLIC")

    task_idx  = _level_idx(task_level)
    skill_idx = _level_idx(skill_level)

    allowed = skill_idx >= task_idx

    return {
        "task_preview":   task[:80],
        "skill":          skill,
        "task_sensitivity": task_level,
        "skill_clearance":  skill_level,
        "allowed":          allowed,
        "taint_reasons":    reasons,
        "verdict": "ALLOW" if allowed else (
            f"BLOCK — {skill} has clearance {skill_level} "
            f"but task requires {task_level}"
        ),
    }


def run(task: str | None, skill: str | None, dry_run: bool) -> int:
    now = datetime.now(timezone.utc).isoformat()

    demo_cases = [
        ("Search for recent AI papers",                 "web_search"),
        ("Send my email john@example.com to the agent", "web_search"),
        ("Store my password=s3cr3t in memory",          "memory"),
        ("Store my password=s3cr3t in memory",          "browser_vault_fill"),
        ("Read internal config file",                   "read_file"),
        ("Process PII data from user records",          "delegate_task"),
    ]

    if task and skill:
        cases = [(task, skill)]
    else:
        cases = demo_cases
        print(f"[privacy-router] Running {len(cases)} demo cases\n")

    results  = []
    blocked  = 0
    print(f"=== Privacy-Constrained Skill Router — {now[:10]} ===")
    print(f"  {'Task':<45} {'Skill':<20} Verdict")
    print("  " + "-" * 90)

    for t, s in cases:
        r = route(t, s)
        icon = "✓" if r["allowed"] else "✗"
        print(f"  {icon} {r['task_preview'][:44]:<45} {r['skill']:<20} {r['verdict'][:40]}")
        if r["taint_reasons"]:
            print(f"      Taint: {'; '.join(r['taint_reasons'][:2])}")
        results.append(r)
        if not r["allowed"]:
            blocked += 1

    print(f"\nBlocked: {blocked}/{len(results)}")
    if blocked:
        print("ALARM: yes — privacy routing violations detected")
    else:
        print("ALARM: no — all routes within clearance bounds")

    if not dry_run:
        OUT_FILE.write_text(json.dumps({"ts": now, "results": results}, indent=2))

    return 1 if blocked else 0


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--task",    default=None)
    p.add_argument("--skill",   default=None)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    sys.exit(run(args.task, args.skill, args.dry_run))


if __name__ == "__main__":
    main()
