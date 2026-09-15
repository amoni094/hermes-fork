#!/usr/bin/env python3
"""
track-budget.py — post_tool_call hook for session budget enforcement
~/.hermes/agent-hooks/track-budget.py

Fires after every tool call. Accumulates:
  - tool_calls: total number of tool invocations
  - destructive_calls: rm, delete, DROP, write to sensitive paths
  - delegation_depth: max subagent nesting seen this session

Reads policy from ~/.hermes/budget-policy.yaml (created on first run if absent).
Writes state to ~/.hermes/state/budget-<session_id>.json.

Returns a context injection when any limit is within 10% of threshold,
or a BLOCK signal (non-zero exit, context with "BUDGET EXCEEDED") when
a hard limit is breached.

Policy example (budget-policy.yaml):
  hard_limits:
    tool_calls: 500
    destructive_calls: 20
    delegation_depth: 3
  soft_warn_pct: 0.85   # warn at 85% of hard limit

──────────────────────────────────────────────────────────────────────────────
AUDIT NOTE (security finding 2026-06-30 — destructive_calls enforcement gap):

This hook runs as a POST_tool_call hook. It COUNTS destructive_calls *after*
the tool has already executed; it does NOT prevent a destructive call from
running. Consequences:
  - The call that crosses the destructive_calls hard limit has ALREADY run by
    the time this hook fires; the BLOCK signal only stops the *next* action.
  - There is no pre-tool gate tied to destructive_calls. Genuine pre-execution
    blocking of destructive commands is provided separately by
    veto-pre-tool.py (pattern hard-blocks), not by this budget counter.
To make destructive_calls a true pre-execution cap, the counter check would
need to be mirrored into a pre_tool_call hook that blocks when the projected
count (current + 1) would meet/exceed the limit. Logged to
~/.hermes/logs/audit-security-findings.md.
──────────────────────────────────────────────────────────────────────────────
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime, timezone

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

HOME = Path("/var/home/rainbow/.hermes")
STATE_DIR = HOME / "state"
STATE_DIR.mkdir(parents=True, exist_ok=True)
POLICY_FILE = HOME / "budget-policy.yaml"

# ── Default policy (written if absent) ───────────────────────────────────────
DEFAULT_POLICY = {
    "hard_limits": {
        "tool_calls": 500,
        "destructive_calls": 30,
        "delegation_depth": 4,
    },
    "soft_warn_pct": 0.85,
}

DESTRUCTIVE_TOOLS = {"terminal", "write_file", "patch", "mcp__terminal", "mcp__write_file", "mcp__patch"}
DESTRUCTIVE_PATTERNS = ["rm ", "rm\t", "rmdir", "shred", "DROP TABLE", "DROP DATABASE", "DELETE FROM", "truncate"]

def load_policy():
    if POLICY_FILE.exists() and HAS_YAML:
        try:
            import yaml
            with POLICY_FILE.open() as f:
                p = yaml.safe_load(f)
            if p:
                return p
        except Exception:
            pass
    # Write default if missing
    if not POLICY_FILE.exists():
        if HAS_YAML:
            import yaml
            with POLICY_FILE.open("w") as f:
                yaml.dump(DEFAULT_POLICY, f, default_flow_style=False)
        else:
            import json as _j
            with POLICY_FILE.open("w") as f:
                _j.dump(DEFAULT_POLICY, f, indent=2)
    return DEFAULT_POLICY

def is_destructive(tool_name: str, tool_input: dict) -> bool:
    if tool_name in DESTRUCTIVE_TOOLS:
        # Check arguments for destructive patterns
        args_str = json.dumps(tool_input).lower()
        if any(p.lower() in args_str for p in DESTRUCTIVE_PATTERNS):
            return True
    return False

def main():
    payload = json.load(sys.stdin)
    extra = payload.get("extra") or {}
    session_id = payload.get("session_id", "unknown")
    tool_name = extra.get("tool_name", "")
    tool_input = extra.get("tool_input") or {}
    current_depth = extra.get("delegation_depth", 0) or 0

    state_file = STATE_DIR / f"budget-{session_id}.json"

    # Load or init state
    if state_file.exists():
        try:
            state = json.loads(state_file.read_text())
        except Exception:
            state = {}
    else:
        state = {}

    state.setdefault("tool_calls", 0)
    state.setdefault("destructive_calls", 0)
    state.setdefault("max_delegation_depth", 0)
    state.setdefault("session_start", datetime.now(timezone.utc).isoformat())

    # Update counters
    state["tool_calls"] += 1
    if is_destructive(tool_name, tool_input):
        state["destructive_calls"] += 1
    if current_depth > state["max_delegation_depth"]:
        state["max_delegation_depth"] = current_depth

    state["last_updated"] = datetime.now(timezone.utc).isoformat()
    state["last_tool"] = tool_name

    state_file.write_text(json.dumps(state, indent=2))

    # Check limits
    policy = load_policy()
    limits = policy.get("hard_limits", DEFAULT_POLICY["hard_limits"])
    warn_pct = policy.get("soft_warn_pct", 0.85)

    warnings = []
    exceeded = []

    checks = [
        ("tool_calls", state["tool_calls"], limits.get("tool_calls", 500)),
        ("destructive_calls", state["destructive_calls"], limits.get("destructive_calls", 30)),
        ("delegation_depth", state["max_delegation_depth"], limits.get("delegation_depth", 4)),
    ]

    for metric, current, limit in checks:
        if current >= limit:
            exceeded.append(f"{metric}={current} (limit={limit})")
        elif current >= limit * warn_pct:
            pct = int(100 * current / limit)
            warnings.append(f"{metric} at {pct}% of limit ({current}/{limit})")

    if exceeded:
        context = (
            f"[BUDGET EXCEEDED] Session has breached hard limits: {', '.join(exceeded)}. "
            f"Stop and report to user before taking more tool actions."
        )
        out = {"context": context, "budget_exceeded": True}
        sys.stdout.write(json.dumps(out) + "\n")
        sys.exit(2)  # non-zero signals enforcement breach
    elif warnings:
        context = f"[budget-warn] Approaching session limits: {'; '.join(warnings)}."
        sys.stdout.write(json.dumps({"context": context}) + "\n")
    else:
        sys.stdout.write("{}\n")

if __name__ == "__main__":
    main()
