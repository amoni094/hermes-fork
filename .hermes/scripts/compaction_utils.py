"""Shared utilities for Hermes jev-compaction pipeline.

P7B-05 fix: _extract_content_text had 4 independent copies in:
  - segment_level_compactor.py
  - crystal_fidelity_tiers.py
  - cot_phase_scorer.py
  - jev-compaction/__init__.py (inlined)

Divergence already caused P7B-03 (crystal_lossy_compress not getting the P6B-02 fix
that segment_level_compactor received).  This module is the single source of truth;
all four files import from here.
"""
from __future__ import annotations

import logging as _logging
from typing import Any

_log = _logging.getLogger(__name__)


def extract_content_text(msg: dict[str, Any]) -> str:
    """Extract plain text from a message regardless of content shape.

    Handles:
      - str content       → returned as-is
      - list[str]         → joined with newline
      - list[dict]        → extracts 'text' or 'content' key from each dict
      - None / missing    → returns ''

    P10B-01 fix: previously returned '' silently for unknown dict shapes (e.g.
    {"type": "image_url", "url": "..."}). Callers receiving '' treat the message
    as zero-length and retain it as a ghost. Now emits a debug warning so that
    unexpected content shapes are visible in logs without breaking callers.

    P11B-01 fix: import logging and getLogger moved to module level.

    Does NOT modify the message.
    """
    c = msg.get("content")
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        parts: list[str] = []
        for item in c:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                t = item.get("text") or item.get("content") or ""
                if isinstance(t, str):
                    parts.append(t)
                elif t:
                    # P10B-01 fix: non-string value in text/content key — warn, skip
                    _log.debug(
                        "extract_content_text: non-string value in text/content key "
                        "(type=%s); skipping item", type(t).__name__
                    )
            else:
                # P10B-01 fix: unexpected item type in content list — warn, skip
                _log.debug(
                    "extract_content_text: unexpected item type %s in content list; skipping",
                    type(item).__name__,
                )
        return "\n".join(parts)
    if c is not None:
        # P10B-01 fix: unknown content shape (not str, not list, not None) — warn
        _log.debug(
            "extract_content_text: unknown content shape %s; returning ''",
            type(c).__name__,
        )
    return ""


def extract_content_length(msg: dict[str, Any]) -> int:
    """Return the character length of extractable text content in a message."""
    return len(extract_content_text(msg))
