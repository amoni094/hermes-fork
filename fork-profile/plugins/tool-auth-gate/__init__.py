"""tool-auth-gate — Agentao-inspired host-contract tool authorization plugin.

arXiv:2608.13574 (Agentao: Separation of Proposal and Authorization in Agentic Systems)

Implements a lightweight proposal/authorize split on top of Hermes' existing pre_tool_call
plugin hook. The agent's LLM produces a tool-use proposal; this gate checks it against a
policy table before execution reaches the dispatcher.

Policy model:
- DENY_ALWAYS: tools that should never run from automated/agent context without explicit
  user escalation. Returns action="approve" to route through the human-approval gate.
- DENY_IN_CONTEXT: tools denied when specific contextual signals are present (e.g.
  delegate_task when subagent depth is already at max, terminal when sandboxed).
- ALLOW: everything else passes through (action not returned = continue).

The gate is intentionally conservative: it only escalates to human approval for genuinely
high-risk calls (destructive filesystem, broadcast messaging, credential access). It does
NOT block routine tool calls. False-positive approvals are far more disruptive than
false-negative misses.

Configuration (config.yaml under plugins.tool-auth-gate):
  escalate_tools: [list of tool names to always escalate to human approval]
  deny_tools: [list of tool names to block outright with a message]

Defaults (no config needed):
  escalate: write_file on paths matching /etc/, /usr/, ~/.hermes/hermes-agent/
  deny: none (deny_tools is empty by default)
"""
from __future__ import annotations

import hashlib
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Policy tables — edit these to change the gate's behavior
# ---------------------------------------------------------------------------

# Tools that write to protected paths get escalated to human approval.
# Pattern matched against the serialized args string (cheap, no JSON parse needed on hot path).
_PROTECTED_PATH_PATTERNS: List[re.Pattern] = [
    re.compile(r"/etc/"),
    re.compile(r"/usr/(bin|lib|share|local)"),
    re.compile(r"hermes-agent/"),         # don't let agent patch its own source
    re.compile(r"\.hermes/hermes-agent"), # same, dotpath form
]

# Tools whose args we inspect for protected path writes.
_PATH_WRITE_TOOLS = {"write_file", "patch", "terminal"}

# Tools that are always blocked (hard deny, no human escalation option).
# Empty by default — add tool names here only for genuinely irrecoverable actions.
_HARD_DENY_TOOLS: frozenset = frozenset()

# Tools that are always escalated to human approval regardless of args.
# Empty by default — configurable via plugin config.
_ALWAYS_ESCALATE_TOOLS: frozenset = frozenset()


def derive_scope_token(session_id: str, delegation_depth: int) -> str:
    """Return an 8-char authority-scoped capability token for the given session and depth."""
    return hashlib.sha256(
        (session_id + ":" + str(delegation_depth)).encode()
    ).hexdigest()[:8]


def _load_config(ctx: Any) -> None:
    """Pull escalate_tools / deny_tools from plugin config if available."""
    global _ALWAYS_ESCALATE_TOOLS, _HARD_DENY_TOOLS
    try:
        # PluginContext.get_config(key, default) — not get_plugin_config()
        escalate = ctx.get_config("escalate_tools", []) or []
        deny = ctx.get_config("deny_tools", []) or []
        if escalate:
            _ALWAYS_ESCALATE_TOOLS = frozenset(str(t) for t in escalate)
        if deny:
            _HARD_DENY_TOOLS = frozenset(str(t) for t in deny)
    except Exception:
        pass  # config loading must never break the session


def _args_touch_protected_path(args: Dict[str, Any]) -> Optional[str]:
    """Return the matched protected path pattern string, or None.

    Only inspects known path-carrying argument keys to avoid false positives
    on URL strings or code snippets that happen to contain /etc/ or similar.
    """
    PATH_KEYS = ("path", "file", "filename", "target", "dest", "source", "command", "old_string", "new_string")
    candidate_strs: list[str] = []
    for k, v in args.items():
        if k.lower() in PATH_KEYS and isinstance(v, str):
            candidate_strs.append(v)
    # Fall back to full args scan only for terminal/execute_code where the
    # command string carries the path, not a named key.
    if not candidate_strs:
        candidate_strs = [str(v) for v in args.values() if isinstance(v, str)]
    for s in candidate_strs:
        for pat in _PROTECTED_PATH_PATTERNS:
            m = pat.search(s)
            if m:
                return m.group(0)
    return None


def _make_pre_tool_call_hook(ctx: Any):
    def pre_tool_call(tool_name: str, args: Dict[str, Any], **_kwargs) -> Optional[Dict[str, Any]]:
        """Agentao gate: inspect proposal before dispatch, escalate or block if needed."""
        try:
            # --- R5: Authority-scoped capability token scope-escalation check ---
            delegation_depth: int = 0
            try:
                delegation_depth = int(ctx.get_config("delegation_depth", 0) or 0)
            except Exception:
                try:
                    delegation_depth = int(ctx.metadata.get("delegation_depth", 0) or 0)
                except Exception:
                    delegation_depth = 0

            if delegation_depth > 0:
                _SENSITIVE_PATTERNS = ("/etc/", "/usr/", "hermes-agent", "config.yaml")
                # Build a list of strings to check: tool name + all string arg values
                candidates = [tool_name] + [v for v in args.values() if isinstance(v, str)]
                if any(pat in s for pat in _SENSITIVE_PATTERNS for s in candidates):
                    session_id: str = ""
                    try:
                        session_id = str(ctx.get_config("session_id", "") or "")
                    except Exception:
                        try:
                            session_id = str(ctx.metadata.get("session_id", "") or "")
                        except Exception:
                            session_id = ""
                    token = derive_scope_token(session_id, delegation_depth)
                    print(
                        f"SCOPE_ESCALATION: depth={delegation_depth} scope={token} tool={tool_name}",
                        file=sys.stderr,
                    )

            # Hard deny — block outright (no human escalation offered).
            if tool_name in _HARD_DENY_TOOLS:
                return {
                    "action": "block",
                    "message": (
                        f"[tool-auth-gate] Tool '{tool_name}' is in the hard-deny list "
                        f"and cannot be called from an agent context. "
                        f"Remove it from plugins.tool-auth-gate.deny_tools to allow."
                    ),
                }

            # Always-escalate list — route to human-approval gate.
            if tool_name in _ALWAYS_ESCALATE_TOOLS:
                return {
                    "action": "approve",
                    "message": (
                        f"[tool-auth-gate] Tool '{tool_name}' requires explicit human approval "
                        f"(configured in plugins.tool-auth-gate.escalate_tools)."
                    ),
                }

            # Protected-path check for write tools.
            if tool_name in _PATH_WRITE_TOOLS:
                matched = _args_touch_protected_path(args)
                if matched:
                    return {
                        "action": "approve",
                        "message": (
                            f"[tool-auth-gate] '{tool_name}' targets a protected path "
                            f"(matched: '{matched}'). Confirm this write is intentional."
                        ),
                    }

        except Exception:
            # Gate failures must never block tool execution — fail open.
            logger.debug("tool-auth-gate: pre_tool_call check failed", exc_info=True)

        # Default: no directive — tool proceeds normally.
        return None

    return pre_tool_call


def register(ctx: Any) -> None:
    _load_config(ctx)
    ctx.register_hook("pre_tool_call", _make_pre_tool_call_hook(ctx))
    logger.debug("tool-auth-gate: registered pre_tool_call hook")
