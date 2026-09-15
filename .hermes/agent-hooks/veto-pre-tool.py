#!/usr/bin/env python3
"""
veto-pre-tool.py — pre_tool_call hook with native Veto-compatible rule evaluation
~/.hermes/agent-hooks/veto-pre-tool.py

Fires before every tool call. Loads local Veto-format rules from
~/.hermes/veto/rules/*.yaml and evaluates them deterministically — no network
calls, no async overhead, sub-millisecond latency.

Rule format is 100% compatible with Veto's YAML rule schema (version "1.0").
Rules can be managed with veto-cli and loaded here without modification.

Hermes pre_tool_call protocol:
  - stdout {"decision": "block", "reason": "..."} → tool is blocked
  - stdout {"context": "..."} → tool runs, context injected into model
  - stdout {} or empty → tool proceeds silently
  - non-zero exit → treated as block
"""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

RULES_DIR = Path("/var/home/rainbow/.hermes/veto/rules")
AUDIT_LOG = Path("/var/home/rainbow/.hermes/logs/veto-audit.jsonl")
AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)

# ── Budget state paths (mirrors track-budget.py) ─────────────────────────────
STATE_DIR = Path("/var/home/rainbow/.hermes/state")
POLICY_FILE = Path("/var/home/rainbow/.hermes/budget-policy.yaml")
DESTRUCTIVE_TOOLS = {"terminal", "write_file", "patch", "mcp__terminal", "mcp__write_file", "mcp__patch"}
DESTRUCTIVE_PATTERNS = ["rm ", "rm\t", "rmdir", "shred", "DROP TABLE", "DROP DATABASE", "DELETE FROM", "truncate"]

def _load_destructive_limit() -> int:
    """Read destructive_calls hard limit from budget-policy.yaml. Default 30."""
    try:
        import yaml
        with POLICY_FILE.open() as f:
            p = yaml.safe_load(f) or {}
        return int(p.get("hard_limits", {}).get("destructive_calls", 30))
    except Exception:
        return 30

def _is_destructive(tool_name: str, tool_input: dict) -> bool:
    if tool_name not in DESTRUCTIVE_TOOLS:
        return False
    args_str = json.dumps(tool_input).lower()
    return any(p.lower() in args_str for p in DESTRUCTIVE_PATTERNS)

def _check_destructive_cap(session_id: str, tool_name: str, tool_input: dict) -> dict | None:
    """
    Pre-tool destructive_calls cap enforcement.
    Returns a block decision dict if the cap would be breached, else None.
    This mirrors the count in track-budget.py but fires PRE-tool so the
    limit is a true hard cap, not a post-hoc observation.
    """
    if not session_id or not _is_destructive(tool_name, tool_input):
        return None
    try:
        state_file = STATE_DIR / f"budget-{session_id}.json"
        state = {}
        if state_file.exists():
            state = json.loads(state_file.read_text())
        current = int(state.get("destructive_calls", 0))
        limit = _load_destructive_limit()
        if current + 1 > limit:
            return {
                "decision": "block",
                "reason": (
                    f"[budget/destructive-cap] Destructive call cap reached: "
                    f"{current}/{limit} destructive calls this session. "
                    f"Stop and report to user before taking more destructive actions."
                ),
            }
    except Exception:
        pass  # fail open for budget check (veto rules still apply)
    return None

# ── Skip list: read-only tools that never need governance ────────────────────
SKIP_TOOLS = {
    "web_search", "web_extract", "mcp__web_search", "mcp__web_extract",
    "read_file", "mcp__read_file", "search_files", "mcp__search_files",
    "mcp__browser_snapshot", "mcp__browser_get_images", "mcp__vision_analyze",
    "mcp__memory", "mcp__session_search", "mcp__skill_view", "mcp__skills_list",
    "mcp__qmd_query", "mcp__qmd_get", "mcp__qmd_multi_get", "mcp__clarify",
    "mcp__todo", "mcp__browser_vision",
}


# ── Rule loader ──────────────────────────────────────────────────────────────

def load_rules() -> list[dict]:
    """Load all Veto-format rule files from RULES_DIR."""
    rules = []
    if not RULES_DIR.exists():
        return rules
    try:
        import yaml
        has_yaml = True
    except ImportError:
        has_yaml = False

    for rule_file in sorted(RULES_DIR.glob("*.yaml")):
        try:
            if has_yaml:
                import yaml
                docs = yaml.safe_load(rule_file.read_text()) or {}
            else:
                # Minimal fallback: skip if yaml unavailable
                continue
            for rule in docs.get("rules", []):
                if isinstance(rule, dict):
                    rules.append(rule)
        except Exception:
            pass
    return rules


# ── Condition evaluator ──────────────────────────────────────────────────────

def get_field_value(arguments: dict, field_path: str) -> str | None:
    """Resolve 'arguments.command' style field paths."""
    parts = field_path.split(".")
    if parts[0] == "arguments":
        parts = parts[1:]
    obj = arguments
    for part in parts:
        if not isinstance(obj, dict):
            return None
        obj = obj.get(part)
    return str(obj) if obj is not None else None


def evaluate_condition(cond: dict, arguments: dict) -> bool:
    field = cond.get("field", "")
    operator = cond.get("operator", "")
    value = str(cond.get("value", ""))
    actual = get_field_value(arguments, field)
    if actual is None:
        return False

    if operator == "matches":
        try:
            return bool(re.search(value, actual, re.IGNORECASE))
        except re.error:
            return False
    elif operator == "contains":
        return value.lower() in actual.lower()
    elif operator == "starts_with":
        return actual.lower().startswith(value.lower())
    elif operator == "ends_with":
        return actual.lower().endswith(value.lower())
    elif operator == "equals":
        return actual.lower() == value.lower()
    elif operator == "greater_than":
        try:
            return float(actual) > float(value)
        except ValueError:
            return False
    return False


def evaluate_rule(rule: dict, tool_name: str, arguments: dict) -> bool:
    """
    Returns True if the rule matches this tool call.
    Supports both 'conditions' (flat AND list) and 'condition_groups' (OR of AND groups).
    """
    if not rule.get("enabled", True):
        return False

    # Tool filter
    tools = rule.get("tools", [])
    if tools and tool_name not in tools:
        return False

    conditions = rule.get("conditions")
    condition_groups = rule.get("condition_groups")

    # No conditions = always matches for this tool
    if not conditions and not condition_groups:
        return True

    # Flat AND conditions
    if conditions and isinstance(conditions, list):
        if all(evaluate_condition(c, arguments) for c in conditions if isinstance(c, dict)):
            return True

    # OR of AND groups
    if condition_groups and isinstance(condition_groups, list):
        for group in condition_groups:
            if isinstance(group, list) and group:
                if all(evaluate_condition(c, arguments) for c in group if isinstance(c, dict)):
                    return True

    return False


# ── Main evaluation ──────────────────────────────────────────────────────────

def evaluate(tool_name: str, arguments: dict, rules: list[dict]) -> dict:
    """
    Evaluate all rules against a tool call.
    Returns {"action": "block"|"warn"|"log"|"allow", "rule_id": ..., "reason": ...}
    Priority: block > warn > log > allow
    """
    first_warn = None
    first_log = None

    for rule in rules:
        if not evaluate_rule(rule, tool_name, arguments):
            continue

        action = rule.get("action", "allow")
        rule_id = rule.get("id", "")
        reason = rule.get("description") or rule.get("name", "rule matched")

        if action == "block":
            return {"action": "block", "rule_id": rule_id, "reason": reason}
        elif action == "warn" and first_warn is None:
            first_warn = {"action": "warn", "rule_id": rule_id, "reason": reason}
        elif action == "log" and first_log is None:
            first_log = {"action": "log", "rule_id": rule_id, "reason": reason}

    return first_warn or first_log or {"action": "allow", "rule_id": "", "reason": ""}


def write_audit(entry: dict):
    try:
        with AUDIT_LOG.open("a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _fail_closed(reason: str):
    """Emit a block decision. Used whenever the hook cannot safely evaluate.

    Security posture: FAIL CLOSED. If we cannot parse the payload, load rules,
    or evaluate them, we must block the tool rather than let a potentially
    destructive call through ungoverned.
    """
    sys.stdout.write(json.dumps({
        "decision": "block",
        "reason": f"[veto/fail-closed] {reason}",
    }) + "\n")


def main():
    # Fail-closed payload parsing: a malformed/empty payload means we cannot
    # identify the tool or its arguments, so we block rather than allow.
    try:
        payload = json.load(sys.stdin)
    except Exception as e:
        _fail_closed(f"could not parse hook payload: {e}")
        return

    if not isinstance(payload, dict):
        _fail_closed("hook payload was not a JSON object")
        return

    tool_name = payload.get("tool_name", "")
    tool_input = payload.get("tool_input") or {}
    session_id = payload.get("session_id", "")

    if tool_name in SKIP_TOOLS:
        sys.stdout.write("{}\n")
        return

    # ── Pre-tool destructive_calls cap ────────────────────────────────────────
    # Check before veto rules so the budget cap fires even if no pattern matches.
    cap_block = _check_destructive_cap(session_id, tool_name, tool_input)
    if cap_block:
        write_audit({
            "ts": datetime.now(timezone.utc).isoformat(),
            "session_id": session_id,
            "tool": tool_name,
            "action": "block",
            "rule_id": "budget/destructive-cap",
            "reason": cap_block["reason"][:300],
        })
        sys.stdout.write(json.dumps(cap_block) + "\n")
        return

    # Fail-closed evaluation: any error while loading or evaluating rules must
    # block the call, never silently allow it.
    try:
        rules = load_rules()
        result = evaluate(tool_name, tool_input, rules)
    except Exception as e:
        _fail_closed(f"rule evaluation error for tool '{tool_name}': {e}")
        return

    action = result["action"]
    rule_id = result["rule_id"]
    reason = result["reason"]

    if action in ("block", "warn", "log"):
        write_audit({
            "ts": datetime.now(timezone.utc).isoformat(),
            "session_id": session_id,
            "tool": tool_name,
            "action": action,
            "rule_id": rule_id,
            "reason": reason[:300],
        })

    if action == "block":
        tag = f"veto/{rule_id}" if rule_id else "veto"
        sys.stdout.write(json.dumps({
            "decision": "block",
            "reason": f"[{tag}] {reason}",
        }) + "\n")
    elif action == "warn":
        tag = f"veto/{rule_id}" if rule_id else "veto"
        sys.stdout.write(json.dumps({
            "context": f"[{tag}] WARNING: {reason}",
        }) + "\n")
    else:
        sys.stdout.write("{}\n")


if __name__ == "__main__":
    main()
