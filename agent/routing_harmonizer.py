"""LLM routing hints aligned with the session-type classifier.

Canonical implementation lives in :mod:`agent.session_classifier`. This module
re-exports ``get_routing_hint`` so callers can depend on a stable routing name
even while the classifier file is being landed in parallel.
"""
from __future__ import annotations

from agent.session_classifier import (  # noqa: F401
    CONFIDENCE_FLOOR,
    SESSION_TYPES,
    WINDOW_SIZE,
    classify,
    get_routing_hint,
)

__all__ = [
    "CONFIDENCE_FLOOR",
    "SESSION_TYPES",
    "WINDOW_SIZE",
    "classify",
    "get_routing_hint",
]
