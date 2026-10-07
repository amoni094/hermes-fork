"""memory-ransac-gate — post_tool_call RANSAC outlier gate.

Calls memory-ransac-commit.py is_inlier(text, corpus) to reject tool results
that are geometric outliers relative to current memory distribution.

Hard core: INLIER_K=2.5, ABS_FLOOR=0.15 (from memory-ransac-commit.py).
Fail-open: any exception returns None (H-I7).
Shadow: never raises, never injects synthetic messages.

Assume: tool_result is a string or dict; corpus loaded from working-memory SQLite.
Guarantee: if result is an outlier, flags with _ransac_outlier key. Never blocks.

Inner objective: reject outlier tool results before memory commit.
Outer objective: maintain memory quality via RANSAC inlier gating.
inner == outer when corpus is representative of current memory state.
"""
from __future__ import annotations

import importlib.util
import logging
import os
import sqlite3
from pathlib import Path
from typing import Any, Optional

log = logging.getLogger("memory-ransac-gate")

_INNER_OBJECTIVE = "reject outlier tool results before memory commit"
_OUTER_OBJECTIVE = "maintain memory quality"

_MOD = None
_CORPUS: list[str] = []
_CORPUS_TS: float = 0.0
_CORPUS_TTL = 300.0  # refresh corpus every 5 minutes


def _hermes_base() -> Path:
    hh = os.environ.get("HERMES_HOME", "").strip()
    base = Path(hh) if hh else Path.home() / ".hermes"
    if base.name == "fork" and "profiles" in str(base):
        base = base.parent.parent
    return base


def _load_ransac():
    base = _hermes_base()
    for candidate in [
        base / "hermes-scripts" / "memory-ransac-commit.py",
        base / "scripts" / "memory-ransac-commit.py",
    ]:
        if candidate.exists():
            spec = importlib.util.spec_from_file_location("memory_ransac_commit", candidate)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)  # type: ignore[union-attr]
            return mod
    return None


def _load_corpus() -> list[str]:
    """Load recent memory entries as corpus for RANSAC baseline."""
    import time
    global _CORPUS, _CORPUS_TS
    now = time.time()
    if now - _CORPUS_TS < _CORPUS_TTL and _CORPUS:
        return _CORPUS
    try:
        base = _hermes_base()
        db_path = base / "memory.db"
        if not db_path.exists():
            db_path = base / "profiles" / "fork" / "memory.db"
        if not db_path.exists():
            return []
        with sqlite3.connect(str(db_path), timeout=2) as con:
            rows = con.execute(
                "SELECT value FROM memories ORDER BY rowid DESC LIMIT 200"
            ).fetchall()
        _CORPUS = [str(r[0]) for r in rows if r[0]]
        _CORPUS_TS = now
    except Exception:
        pass
    return _CORPUS


def post_tool_call(tool_name: str, args: dict, result: Any) -> Optional[Any]:
    """Gate: flag tool results that are RANSAC outliers. Fail-open (H-I7)."""
    global _MOD
    try:
        if _MOD is None:
            _MOD = _load_ransac()
        if _MOD is None:
            return None
        corpus = _load_corpus()
        if len(corpus) < 10:
            return None  # insufficient baseline — pass through
        candidate = str(result)[:4096]
        verdict = _MOD.is_inlier(candidate, corpus)
        if isinstance(verdict, dict) and not verdict.get("inlier", True):
            log.warning(
                "memory-ransac-gate: outlier detected tool=%s score=%.3f threshold=%.3f",
                tool_name,
                verdict.get("score", float("nan")),
                verdict.get("threshold", float("nan")),
            )
            if isinstance(result, dict):
                result = dict(result)
                result["_ransac_outlier"] = True
                result["_ransac_score"] = verdict.get("score")
        return None
    except Exception:  # H-I7: never raise
        return None


def register(ctx: Any) -> None:
    """Register post_tool_call hook with Hermes plugin system."""
    ctx.register_hook("post_tool_call", post_tool_call)
