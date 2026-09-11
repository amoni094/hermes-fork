"""Predicates over lambda-tuner session classification.

Boolean helpers other plugins can import to gate behavior without
re-implementing the classifier. Fail-open: unknown or missing sessions
return False / None.

Reads ``_fired`` from the parent package. After classify/lock it stores:

    {session_id: {"type": str, "confidence": float, "ts": float}}
"""
from __future__ import annotations

from typing import Any, Optional


def _records() -> Any:
    try:
        from . import _fired
        return _fired
    except Exception:
        return {}


def _record(session_id: str) -> Optional[dict[str, Any]]:
    try:
        rec = _records().get(session_id)
    except Exception:
        return None
    if rec is None:
        return None
    if isinstance(rec, str):
        return {"type": rec, "confidence": 0.0, "ts": 0.0}
    if isinstance(rec, dict):
        return rec
    return None


def session_type(session_id: str) -> Optional[str]:
    """Return ``'research'|'code'|'mixed'`` for a locked session, else None."""
    rec = _record(session_id)
    if not rec:
        return None
    t = rec.get("type")
    if t in ("research", "code", "mixed"):
        return t
    return None


def is_research_session(session_id: str) -> bool:
    """True if ``_fired`` has this session locked as type ``research``."""
    return session_type(session_id) == "research"


def is_code_session(session_id: str) -> bool:
    """True if ``_fired`` has this session locked as type ``code``."""
    return session_type(session_id) == "code"


def is_high_confidence(session_id: str, threshold: float = 0.8) -> bool:
    """True if the locked session's confidence is >= *threshold*."""
    rec = _record(session_id)
    if not rec:
        return False
    try:
        return float(rec.get("confidence", 0.0) or 0.0) >= float(threshold)
    except (TypeError, ValueError):
        return False
