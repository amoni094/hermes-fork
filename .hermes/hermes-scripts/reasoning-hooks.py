#!/usr/bin/env python3
"""Runtime consumer for loop_harness.reasoning_hooks + feature_list.json.

Hermes core does not auto-inject these gates before tool calls. Skills and
scripts MUST query this helper (or import hook_enabled) and skip/run accordingly.

Usage:
  python3 ~/.hermes/scripts/reasoning-hooks.py status
  python3 ~/.hermes/scripts/reasoning-hooks.py enabled --hook pre_tool_call_kapro_check
  python3 ~/.hermes/scripts/reasoning-hooks.py inventory
  python3 ~/.hermes/scripts/reasoning-hooks.py log-kapro --recommendation USE_CACHED --task "..."

Exit: enabled → 0 if hook true, 1 if false/unknown; others 0=ok, 2=error.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HERMES_HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
CONFIG_PATH = HERMES_HOME / "config.yaml"
INVENTORY_PATH = HERMES_HOME / "cache" / "loop-harness" / "feature_list.json"
KAPRO_LOG = HERMES_HOME / "cache" / "kapro-check.jsonl"

HOOK_TO_COMMAND = {
    "pre_task_select_frameworks": "reasoning-complexity-classifier.py select-frameworks",
    "pre_action_lookahead": "working-memory.py lookahead",
    "pre_subtask_subplan_verify": "working-memory.py subplan-verify",
    "on_attribution_causal_check": "metacognitive-harness.py causal-check",
    "pre_completion_boundary_check": "metacognitive-harness.py boundary-check",
    "on_failure_hypothesize": "critique-bank.py hypothesize",
    "on_framework_conflict_resolve": "metacognitive-harness.py conflict-resolve",
    "mid_task_switch_framework": "working-memory.py switch-framework",
    "pre_tool_call_kapro_check": "metacognitive-harness.py kapro-check",
}

DEFAULT_LEVEL_RULES = {
    "L0": "no_frameworks",
    "L1": "no_frameworks",
    "L2": "primary_only",
    "L3": "primary_and_secondary_cascade",
}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        return {}
    try:
        import yaml  # type: ignore
    except ImportError:
        return _parse_yaml_lite(CONFIG_PATH.read_text())
    try:
        return yaml.safe_load(CONFIG_PATH.read_text()) or {}
    except Exception:
        return {}


def _parse_yaml_lite(text: str) -> dict[str, Any]:
    """Minimal fallback if PyYAML is missing — only used for hook booleans."""
    return {}


def reasoning_hooks() -> dict[str, bool]:
    cfg = load_config()
    hooks = ((cfg.get("loop_harness") or {}).get("reasoning_hooks") or {})
    out: dict[str, bool] = {}
    for k, v in hooks.items():
        if str(k).startswith("_"):
            continue
        out[str(k)] = bool(v)
    return out


def hook_enabled(name: str, default: bool = True) -> bool:
    hooks = reasoning_hooks()
    if name not in hooks:
        return default
    return bool(hooks[name])


def level_rules() -> dict[str, str]:
    cfg = load_config()
    nested = (
        ((cfg.get("reasoning_research") or {}).get("reasoning_frameworks") or {})
        .get("reasoning_selection") or {}
    ).get("level_rules") or {}
    top = (cfg.get("reasoning_selection") or {}).get("level_rules") or {}
    merged = dict(DEFAULT_LEVEL_RULES)
    if isinstance(nested, dict):
        merged.update({str(k): str(v) for k, v in nested.items()})
    if isinstance(top, dict):
        merged.update({str(k): str(v) for k, v in top.items()})
    return merged


def cascade_order() -> list[str]:
    default = [
        "abstain-check", "causal-check", "lookahead", "subplan-verify",
        "hypothesize", "boundary-check", "kapro-check",
    ]
    cfg = load_config()
    top = ((cfg.get("reasoning_selection") or {}).get("conflict_resolution") or {}).get(
        "cascade_order"
    )
    nested = (
        (((cfg.get("reasoning_research") or {}).get("reasoning_frameworks") or {})
         .get("reasoning_selection") or {}).get("conflict_resolution") or {}
    ).get("cascade_order")
    order = top or nested or default
    if not isinstance(order, list) or not order:
        return default
    return [str(x) for x in order]


def load_inventory() -> list[dict[str, Any]]:
    if not INVENTORY_PATH.exists():
        return []
    try:
        data = json.loads(INVENTORY_PATH.read_text())
    except json.JSONDecodeError:
        return []
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict) and isinstance(data.get("features"), list):
        return [x for x in data["features"] if isinstance(x, dict)]
    return []


def log_kapro(recommendation: str, payload: dict[str, Any]) -> Path:
    KAPRO_LOG.parent.mkdir(parents=True, exist_ok=True)
    rec = (recommendation or "").strip().upper()
    entry = {
        "ts": _now(),
        "recommendation": rec,
        "reduces_tool_call": rec in ("USE_CACHED", "SKIP", "SKIP_ACTION"),
        **payload,
    }
    with KAPRO_LOG.open("a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return KAPRO_LOG


def parse_level(raw: str | None) -> tuple[str | None, str | None]:
    """Return (level, error). level is L0-L3 or None if omitted."""
    if raw is None or str(raw).strip() == "":
        return None, None
    s = str(raw).strip().upper()
    if s in ("0", "1", "2", "3"):
        s = f"L{s}"
    if s in ("L0", "L1", "L2", "L3"):
        return s, None
    return None, f"Invalid --level {raw!r}: expected L0-L3 (or 0-3)."


def parse_verdict_arg(raw: str) -> tuple[str | None, float | None, str | None]:
    """Parse a verdict string or JSON object. Returns (verdict, confidence, error)."""
    text = (raw or "").strip()
    if not text:
        return "", None, None
    if text[0] in "{[":
        try:
            val = json.loads(text)
        except json.JSONDecodeError as e:
            return None, None, f"malformed --verdict JSON: {e}"
        if isinstance(val, dict):
            verdict = (
                val.get("verdict")
                or val.get("resolved_verdict")
                or val.get("boundary_verdict")
                or val.get("lookahead_verdict")
                or val.get("recommendation")
                or val.get("k_verdict")
            )
            if verdict is None:
                return None, None, "JSON verdict object missing verdict/resolved_verdict field"
            conf = val.get("confidence")
            try:
                conf_f = float(conf) if conf is not None else None
            except (TypeError, ValueError):
                conf_f = None
            return str(verdict), conf_f, None
        if isinstance(val, list):
            return None, None, "JSON verdict must be an object, not a list"
    return text, None, None


def cmd_status(_args: argparse.Namespace) -> int:
    hooks = reasoning_hooks()
    print(json.dumps({
        "hermes_home": str(HERMES_HOME),
        "config_path": str(CONFIG_PATH),
        "hooks": hooks,
        "hook_to_command": HOOK_TO_COMMAND,
        "inventory_path": str(INVENTORY_PATH),
        "inventory_count": len(load_inventory()),
        "note": (
            "Hooks are skill/script gates, not Hermes-core pre-tool interceptors. "
            "Call `enabled --hook KEY` before the matching subcommand."
        ),
    }, indent=2))
    return 0


def cmd_enabled(args: argparse.Namespace) -> int:
    name = (args.hook or "").strip()
    if not name:
        print(json.dumps({"error": "--hook is required", "enabled": False}))
        return 2
    on = hook_enabled(name, default=False if name not in reasoning_hooks() else True)
    known = name in reasoning_hooks()
    print(json.dumps({
        "hook": name,
        "enabled": on,
        "known": known,
        "command": HOOK_TO_COMMAND.get(name),
    }))
    return 0 if on else 1


def cmd_inventory(_args: argparse.Namespace) -> int:
    items = load_inventory()
    print(json.dumps({"path": str(INVENTORY_PATH), "count": len(items), "features": items}, indent=2))
    return 0


def cmd_log_kapro(args: argparse.Namespace) -> int:
    rec = (args.recommendation or "").strip()
    if not rec:
        print(json.dumps({"error": "--recommendation is required"}))
        return 2
    path = log_kapro(rec, {"task": args.task or "", "source": "reasoning-hooks.py"})
    print(json.dumps({"logged": True, "path": str(path), "recommendation": rec}))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("status", help="Dump hook map and inventory stats")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("enabled", help="Exit 0 if hook is enabled, 1 if disabled")
    p.add_argument("--hook", required=True)
    p.set_defaults(func=cmd_enabled)

    p = sub.add_parser("inventory", help="Read feature_list.json capability inventory")
    p.set_defaults(func=cmd_inventory)

    p = sub.add_parser("log-kapro", help="Append a KAPRO skip/cache observability event")
    p.add_argument("--recommendation", required=True)
    p.add_argument("--task", default="")
    p.set_defaults(func=cmd_log_kapro)

    args = ap.parse_args()
    return int(args.func(args) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
