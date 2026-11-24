"""CCR retrieve/status tools for the billion-context plugin."""
from __future__ import annotations

import json
from typing import Any


def _acp_retrieve(args: Any = None, session_id: str = "", **_kwargs: Any) -> str:
    from agent.billion_context import ccr_retrieve
    # Registry calls handler(args_dict, **context_kwargs); unpack the dict.
    if isinstance(args, dict):
        store_id = str(args.get("id") or "")
        session_id = str(args.get("session_id") or session_id or "")
    else:
        store_id = str(args or "")
    return ccr_retrieve(store_id, session_id=session_id)


def _acp_status(args: Any = None, **_kwargs: Any) -> str:
    from agent.billion_context import scaled_thresholds
    import os
    from pathlib import Path
    # args is a dict (possibly empty) passed by the registry dispatch convention.
    session_id = str((args.get("session_id") if isinstance(args, dict) else None) or "")
    knobs = scaled_thresholds()
    base = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
    profile = os.environ.get("HERMES_PROFILE", "")
    if profile and "profiles" not in str(base):
        base = base / "profiles" / profile
    ccr_dir = base / "cache" / "billion-context" / "ccr"
    stored = 0
    try:
        stored = sum(1 for _ in ccr_dir.glob("*/*.json")) if ccr_dir.exists() else 0
    except Exception:
        stored = 0
    return json.dumps({
        "ok": True,
        "thresholds": knobs,
        "stored_results": stored,
        "session_id": session_id or "",
    })


ACP_RETRIEVE_SCHEMA = {
    "name": "acp_retrieve",
    "description": (
        "Retrieve a tool result previously replaced by a billion-context CCR "
        "placeholder. Pass the id from the placeholder (e.g. m00423)."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "id": {"type": "string", "description": "Stored id from the placeholder (mXXXXXXXX)."},
        },
        "required": ["id"],
        "additionalProperties": False,
    },
}

ACP_STATUS_SCHEMA = {
    "name": "acp_status",
    "description": "Billion-context CCR/compression status: scaled thresholds and stored result count.",
    "parameters": {
        "type": "object",
        "properties": {},
        "additionalProperties": False,
    },
}


def register_tools(ctx: Any) -> None:
    ctx.register_tool(
        name="acp_retrieve",
        toolset="billion-context",
        schema=ACP_RETRIEVE_SCHEMA,
        handler=_acp_retrieve,
        description=ACP_RETRIEVE_SCHEMA["description"],
        emoji="📦",
    )
    ctx.register_tool(
        name="acp_status",
        toolset="billion-context",
        schema=ACP_STATUS_SCHEMA,
        handler=_acp_status,
        description=ACP_STATUS_SCHEMA["description"],
        emoji="📦",
    )
