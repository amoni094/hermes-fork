#!/usr/bin/env python3
"""
mcp-auth-drift-check.py — MCP authorization drift detection
arXiv:2609.23498 — Runtime Authorization Consistency Checking for MCP Workflows

"Authorization drift": locally-valid MCP tool calls that exceed session-level bounds
because authorization state is tracked per-call, not per-session.

Reads ~/.hermes/profiles/fork/logs/mcp-calls.jsonl.
For each MCP tool call checks:
  (a) Timestamp within session window bounds
  (b) Tool name in declared allowlist (from config.yaml mcp_servers keys)
  (c) No tool called >3x within 60 seconds (burst)

Flags violations to ~/.hermes/profiles/fork/logs/mcp-auth-drift.jsonl.
Exits 0 always (non-fatal diagnostic).
"""
import sys
import json
import os
import datetime
from pathlib import Path

_HERMES_HOME = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_hh = str(_HERMES_HOME)
_FORK_ROOT = _HERMES_HOME if ("profiles" in _hh and _hh.endswith("fork")) else _HERMES_HOME / "profiles/fork"
MCP_LOG = _FORK_ROOT / "logs/mcp-calls.jsonl"
DRIFT_LOG = _FORK_ROOT / "logs/mcp-auth-drift.jsonl"
CONFIG_PATH = _FORK_ROOT / "config.yaml"
DRIFT_LOG.parent.mkdir(parents=True, exist_ok=True)

SESSION_WINDOW_HOURS = 8  # max session window for auth validity
BURST_WINDOW_SECONDS = 60
# BURST_LIMIT must match BURST_WARN_THRESHOLD in mcp-auth-drift-hook.py (F25 alignment)
BURST_LIMIT = 3


def _now_iso() -> str:
    return datetime.datetime.utcnow().isoformat() + "Z"


def _load_allowlist() -> set[str]:
    """Extract MCP server names from config.yaml as the tool allowlist."""
    if not CONFIG_PATH.exists():
        return set()
    try:
        # Minimal YAML parsing for mcp_servers keys (no yaml dep)
        text = CONFIG_PATH.read_text()
        in_mcp = False
        keys: set[str] = set()
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("mcp_servers:"):
                in_mcp = True
                continue
            if in_mcp:
                if stripped.startswith("-") or (stripped and not stripped[0].isspace() and ":" not in stripped):
                    in_mcp = False
                    continue
                if ":" in stripped and not stripped.startswith("#"):
                    key = stripped.split(":")[0].strip()
                    if key:
                        # Normalize: mcp__graphiti__* -> graphiti
                        keys.add(key)
                        keys.add(f"mcp__{key}__")  # prefix match
        return keys
    except Exception:
        return set()


def _is_tool_allowed(tool_name: str, allowlist: set[str]) -> bool:
    """Check if tool_name is in allowlist (exact or prefix match)."""
    if not allowlist:
        return True  # no allowlist = allow all
    if tool_name in allowlist:
        return True
    for prefix in allowlist:
        if prefix.endswith("__") and tool_name.startswith(prefix):
            return True
    return False


def _parse_ts(ts_str: str) -> datetime.datetime | None:
    try:
        ts_str = ts_str.rstrip("Z")
        return datetime.datetime.fromisoformat(ts_str)
    except Exception:
        return None


def main() -> int:
    if not MCP_LOG.exists():
        return 0

    allowlist = _load_allowlist()
    violations = []

    # Load all MCP call records
    records = []
    try:
        with MCP_LOG.open() as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    records.append(rec)
                except json.JSONDecodeError:
                    pass
    except OSError:
        # Log file unreadable — nothing to audit, exit cleanly
        return 0

    now = datetime.datetime.utcnow()
    session_cutoff = now - datetime.timedelta(hours=SESSION_WINDOW_HOURS)

    # Index by tool_name for burst check
    calls_by_tool: dict[str, list[datetime.datetime]] = {}

    for rec in records:
        tool_name = rec.get("tool_name", "")
        ts_raw = rec.get("ts", rec.get("timestamp", ""))
        ts = _parse_ts(ts_raw)

        if not tool_name or not ts:
            continue

        # (a) Session window check
        if ts < session_cutoff:
            violations.append({
                "ts": _now_iso(),
                "tool_name": tool_name,
                "call_ts": ts_raw,
                "issue": "call outside session window",
                "severity": "medium",
            })

        # (b) Allowlist check
        if not _is_tool_allowed(tool_name, allowlist):
            violations.append({
                "ts": _now_iso(),
                "tool_name": tool_name,
                "call_ts": ts_raw,
                "issue": f"tool not in MCP allowlist (allowlist={sorted(allowlist)[:10]})",
                "severity": "high",
            })

        # Collect for burst check
        calls_by_tool.setdefault(tool_name, []).append(ts)

    # (c) Burst check — >BURST_LIMIT calls of same tool within BURST_WINDOW_SECONDS
    burst_cutoff = now - datetime.timedelta(seconds=BURST_WINDOW_SECONDS)
    for tool_name, timestamps in calls_by_tool.items():
        recent = [t for t in timestamps if t >= burst_cutoff]
        if len(recent) > BURST_LIMIT:
            violations.append({
                "ts": _now_iso(),
                "tool_name": tool_name,
                "call_ts": recent[-1].isoformat() + "Z",
                "issue": f"burst: {len(recent)} calls within {BURST_WINDOW_SECONDS}s (limit={BURST_LIMIT})",
                "severity": "high",
            })

    if violations:
        with DRIFT_LOG.open("a") as f:
            for v in violations:
                f.write(json.dumps(v) + "\n")

    return len(violations)


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
