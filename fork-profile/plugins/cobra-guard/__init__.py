"""cobra-guard — CoBRA heuristic skip warnings + outcome logging.

arXiv:2609.00967 (CoBRA: Learning Tool-Use Boundaries via Counterfactual Margins)

Wired into Hermes via pre_tool_call / post_tool_call plugin hooks.

Contract:
- WARN on stderr when a skip rule matches; NEVER block (heuristics false-positive).
- Log (tool, query, outcome) after each call for later probe training.
- Fail open. HERMES_COBRA_GUARD=0 disables.
"""
from __future__ import annotations

import importlib.util
import logging
import os
import sys
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_TRUTHY_OFF = {"0", "false", "off", "no", "disable", "disabled"}

_state_lock = threading.Lock()
_state: Dict[str, Any] = {"tools": [], "chars": 0}

_guard_mod = None
_logger_mod = None


def _enabled() -> bool:
    raw = os.environ.get("HERMES_COBRA_GUARD", "1").strip().lower()
    return raw not in _TRUTHY_OFF


def _scripts_dir() -> Path:
    env = os.environ.get("HERMES_HOME", "").strip()
    candidates = []
    if env:
        candidates.append(Path(env) / "scripts")
    candidates.append(Path.home() / ".hermes" / "scripts")
    for c in candidates:
        if (c / "cobra-skip-guard.py").is_file():
            return c
    return candidates[0]


def _load_script(filename: str):
    path = _scripts_dir() / filename
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location(f"cobra_{path.stem}", path)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _mods():
    global _guard_mod, _logger_mod
    if _guard_mod is None:
        _guard_mod = _load_script("cobra-skip-guard.py")
    if _logger_mod is None:
        _logger_mod = _load_script("cobra-outcome-logger.py")
    return _guard_mod, _logger_mod


def _query_from_args(tool_name: str, args: Any) -> str:
    if not isinstance(args, dict):
        return ""
    for key in ("query", "q", "goal", "command", "path", "pattern", "prompt"):
        val = args.get(key)
        if isinstance(val, str) and val.strip():
            return val
    urls = args.get("urls")
    if isinstance(urls, list):
        return " ".join(str(u) for u in urls if u)
    url = args.get("url")
    if isinstance(url, str) and url.strip():
        return url
    return ""


def _result_len(result: Any) -> int:
    if result is None:
        return 0
    if isinstance(result, (bytes, bytearray)):
        return len(result)
    return len(str(result))


def reset_session_state() -> None:
    with _state_lock:
        _state["tools"] = []
        _state["chars"] = 0


def evaluate_skip(tool_name: str, args: Any) -> tuple[bool, str]:
    """Return (should_skip, reason). Fail-open: (False, ...) on any error."""
    guard, _ = _mods()
    if guard is None or not hasattr(guard, "rules"):
        return False, "cobra-skip-guard unavailable"
    query = _query_from_args(tool_name, args)
    with _state_lock:
        ctx_tools = list(_state["tools"])
        ctx_chars = int(_state["chars"])
    try:
        return guard.rules(tool_name, query, ctx_tools, ctx_chars)
    except Exception as exc:
        logger.debug("cobra-guard rules failed: %s", exc)
        return False, f"rules error: {exc}"


def pre_tool_call(tool_name: str = "", args: Any = None, **_kwargs) -> Optional[Dict[str, Any]]:
    """Warn-only pre-flight. Always returns None so dispatch is never blocked."""
    if not _enabled() or not tool_name:
        return None
    try:
        should_skip, reason = evaluate_skip(tool_name, args)
        if should_skip:
            msg = f"[cobra-guard] WARN (not blocking): {reason}\n"
            sys.stderr.write(msg)
            sys.stderr.flush()
            logger.warning("cobra-guard skip recommended: %s", reason)
    except Exception:
        logger.debug("cobra-guard pre_tool_call failed", exc_info=True)
    return None


def post_tool_call(
    tool_name: str = "",
    args: Any = None,
    result: Any = None,
    session_id: str = "",
    turn_id: str = "",
    **_kwargs,
) -> None:
    if not _enabled() or not tool_name:
        return
    try:
        query = _query_from_args(tool_name, args)
        rlen = _result_len(result)
        with _state_lock:
            prior = list(_state["tools"])
            ctx_chars = int(_state["chars"])
            _state["tools"].append(tool_name)
            _state["chars"] = ctx_chars + rlen
        _, logger_mod = _mods()
        if logger_mod is not None and hasattr(logger_mod, "_append"):
            record = {
                "ts": __import__("datetime").datetime.now(
                    __import__("datetime").timezone.utc
                ).isoformat(),
                "tool_name": tool_name,
                "query_tokens": len(query.split()) if query else 0,
                "context_chars": ctx_chars,
                "context_tools_prior": prior,
                "result_len": rlen,
                "result_used": None,
                "session_id": session_id or "",
                "turn_id": turn_id or "",
            }
            logger_mod._append(record)
    except Exception:
        logger.debug("cobra-guard post_tool_call failed", exc_info=True)


def on_session_start(**_kwargs) -> None:
    reset_session_state()


def on_session_reset(**_kwargs) -> None:
    reset_session_state()


def register(ctx: Any) -> None:
    try:
        if ctx.get_config("enabled", True) is False:
            logger.debug("cobra-guard: disabled via plugin config")
            return
    except Exception:
        pass
    ctx.register_hook("pre_tool_call", pre_tool_call)
    ctx.register_hook("post_tool_call", post_tool_call)
    ctx.register_hook("on_session_start", on_session_start)
    ctx.register_hook("on_session_reset", on_session_reset)
    logger.debug("cobra-guard: registered pre_tool_call (warn-only) and post_tool_call logger")
