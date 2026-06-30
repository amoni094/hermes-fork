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


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        sys.stdout.write("{}\n")
        return

    tool_name = payload.get("tool_name", "")
    tool_input = payload.get("tool_input") or {}
    session_id = payload.get("session_id", "")

    if tool_name in SKIP_TOOLS:
        sys.stdout.write("{}\n")
        return

    rules = load_rules()
    result = evaluate(tool_name, tool_input, rules)
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
