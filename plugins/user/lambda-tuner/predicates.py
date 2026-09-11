"""Predicates over lambda-tuner session classification.

Boolean helpers other plugins can import to gate behavior without
re-implementing the classifier. Fail-open: unknown or missing sessions
return False / None.

Reads ``_fired`` from the parent package. After classify/lock it stores:

    {session_id: {"type": str, "confidence": float, "ts": float}}
"""
from __future__ import annotations

import re
from typing import Any, Optional

# Whole-message greeter/ack — effort bypass (narrower than the classifier greeting filter).
_GREETER_RE = re.compile(
    r"^[\s!.,?]*("
    r"hey|hi|ok(?:ay)?|sure|thanks|thank\s+you|continue|go\s+ahead"
    r")[\s!.,?]*$",
    re.IGNORECASE,
)


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


def turns_since_classification(session_id: str, compressor=None) -> int:
    """Turns since classification lock. -1 if unknown.

    When *compressor* is provided, reads the ChronoMem ``classification_locked``
    checkpoint directly. *session_id* is accepted for API symmetry.
    """
    del session_id  # checkpoint lives on the compressor, not in _fired
    if compressor is None:
        return -1
    try:
        est = getattr(compressor, "_entropy_estimator", None)
        if est is None or not hasattr(est, "since_checkpoint"):
            return -1
        clock = getattr(compressor, "turn_clock", None)
        if clock is None:
            return -1
        return int(est.since_checkpoint("classification_locked", clock))
    except Exception:
        return -1


def session_complexity(sid: str) -> Optional[float]:
    """Locked complexity score from ``_fired``, or None if unknown."""
    rec = _record(sid)
    if not rec:
        return None
    try:
        value = rec.get("complexity")
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def is_greeter_turn(message: str) -> bool:
    """True for whole-message greetings/acks that should force effort=low."""
    if not isinstance(message, str):
        return False
    return bool(_GREETER_RE.match(message.strip()))


def turn_complexity_score(ctx) -> float:
    """Last raw turn complexity stored on *ctx*, or 0.0."""
    try:
        return float(getattr(ctx, "_turn_complexity_score", 0.0) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def recommended_effort(ctx) -> str:
    """Effort level set on the last scored turn, or empty string."""
    try:
        return str(getattr(ctx, "_recommended_effort", "") or "")
    except Exception:
        return ""
