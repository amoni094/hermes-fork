"""tool-result-audit plugin — post_tool_call injection-risk auditor.

Shadow-mode only: never modifies results, never raises, never blocks.
Wires tool-auth-shim.py into the live Hermes fork agent via post_tool_call hook.
Implements Shoham inspection-game probabilistic auditing (tier='EXTERNAL').
"""
from __future__ import annotations
import os

import importlib.util
import logging
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────

INJECTION_RISK_TOOLS: frozenset[str] = frozenset({
    "web_search",
    "web_extract",
    "browser_exec",
    "js",
    "web_extract_url",
})

_SHIM_PATH = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))) / "scripts" / "tool-auth-shim.py"
_TIER = "EXTERNAL"  # inspection-game tier for all external-content tools

# ── Dynamic import of tool-auth-shim ────────────────────────────────────────

_tool_auth_shim: Any = None


def _load_shim() -> Any:
    """Dynamically import tool-auth-shim.py using importlib.util.
    Returns the module or None on failure (shadow: never raises).
    """
    global _tool_auth_shim
    if _tool_auth_shim is not None:
        return _tool_auth_shim
    try:
        spec = importlib.util.spec_from_file_location(
            "tool_auth_shim", str(_shim_PATH := _SHIM_PATH)
        )
        if spec is None or spec.loader is None:
            logger.debug("tool-result-audit: spec_from_file_location returned None for %s", _shim_PATH)
            return None
        mod = importlib.util.module_from_spec(spec)
        sys.modules.setdefault("tool_auth_shim", mod)
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
        _tool_auth_shim = mod
        logger.debug("tool-result-audit: loaded tool-auth-shim from %s", _shim_PATH)
        return mod
    except Exception as exc:
        logger.debug("tool-result-audit: failed to load tool-auth-shim (fail-open): %s", exc)
        return None


# ── Result text extraction ───────────────────────────────────────────────────

def _extract_text(result: Any) -> str:
    """Extract a string from a tool result regardless of its shape.

    Handles:
    - str → returned directly
    - dict → checks keys: 'output', 'content', 'text', 'data', 'result' in order
    - list → joins stringified elements (up to first 20 items)
    - anything else → str() coercion
    """
    try:
        if isinstance(result, str):
            return result
        if isinstance(result, dict):
            for key in ("output", "content", "text", "data", "result"):
                val = result.get(key)
                if isinstance(val, str) and val:
                    return val
                if isinstance(val, (dict, list)):
                    # recurse one level
                    return _extract_text(val)
            # fallback: stringify the whole dict
            import json as _json
            try:
                return _json.dumps(result)
            except Exception:
                return str(result)
        if isinstance(result, list):
            parts: list[str] = []
            for item in result[:20]:
                parts.append(_extract_text(item))
            return " ".join(parts)
        return str(result) if result is not None else ""
    except Exception:
        return ""


# ── Hook ─────────────────────────────────────────────────────────────────────

def on_post_tool_call(
    *,
    tool_name: str = "",
    args: dict | None = None,
    result: Any = None,
    status: str = "ok",
    session_id: str = "",
    tool_call_id: str = "",
    turn_id: str = "",
    duration_ms: float = 0.0,
    middleware_trace: Any = None,
    **_kwargs: Any,
) -> None:
    """post_tool_call hook — shadow audit for injection-risk tools.

    Observer only: return value is None and is ignored by the plugin API.
    Never modifies the result, never raises.
    """
    try:
        # Only audit external-content tools
        if tool_name not in INJECTION_RISK_TOOLS:
            return None

        # Only audit successful calls
        if status != "ok":
            return None

        # Extract text from the result
        text = _extract_text(result)
        if not text:
            return None

        # Load shim (cached after first successful load)
        shim = _load_shim()
        if shim is None:
            return None

        # Probabilistic inspection-game audit (shadow: never raises, never blocks)
        try:
            shim.audit_tool_result(tool_name, _TIER, text)
        except Exception as exc:
            logger.debug(
                "tool-result-audit: audit_tool_result failed for %s (fail-open): %s",
                tool_name, exc,
            )
    except Exception as exc:
        logger.debug("tool-result-audit: on_post_tool_call top-level fail-open: %s", exc)

    return None


# ── Plugin registration ───────────────────────────────────────────────────────

def register(ctx: Any) -> None:
    """Register post_tool_call hook with the Hermes plugin context."""
    try:
        ctx.register_hook("post_tool_call", on_post_tool_call)
        logger.info(
            "tool-result-audit: registered post_tool_call hook "
            "(auditing tools: %s, tier=%s)",
            sorted(INJECTION_RISK_TOOLS),
            _TIER,
        )
    except Exception as exc:
        # Shadow: log and silently fail — never crash the agent
        logger.debug("tool-result-audit: register failed (fail-open): %s", exc)
