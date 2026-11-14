"""compaction-gate — depth gate + MDL fact scoring on pre_compress.

Fail-open: any exception is swallowed so compression always proceeds.
Does not mutate messages, the compressor, or conversation history.
"""
from __future__ import annotations

import json
import logging
import os
import re
import time
import zlib
from datetime import datetime, timezone, UTC
from pathlib import Path
from typing import Any

logger = logging.getLogger("compaction-gate")

ISS_GAIN = 0.35
_DEFAULT_DEPTH = 50
_DEFAULT_MDL = 0.1
_MAX_FACTS = 40
_MIN_FACT_CHARS = 24
_MAX_MSG_CHARS = 4000
_JACCARD_DUP = 0.85
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+|\n+")
_WORD_RE = re.compile(r"[a-z0-9]{2,}")

_CTX: Any = None
_LOG_PATH = (
    Path.home()
    / ".hermes"
    / "profiles"
    / "fork"
    / "cache"
    / "compaction-gate-log.jsonl"
)


def _profile_root() -> Path:
    hh = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
    hp = os.environ.get("HERMES_PROFILE", "")
    if hp and hh.name == hp and hh.parent.name == "profiles":
        return hh
    if hp:
        cand = hh / "profiles" / hp
        if cand.is_dir():
            return cand
    fork = Path.home() / ".hermes" / "profiles" / "fork"
    return fork if fork.is_dir() else hh


def _log_path() -> Path:
    return _profile_root() / "cache" / "compaction-gate-log.jsonl"


def _now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _append_log(record: dict[str, Any]) -> None:
    """Single O_APPEND write of one JSON line (atomic vs other appenders)."""
    path = _log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    line = (json.dumps(record, ensure_ascii=False, default=str) + "\n").encode("utf-8")
    flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
    fd = os.open(str(path), flags, 0o644)
    try:
        os.write(fd, line)
    finally:
        os.close(fd)


def _cfg_int(key: str, default: int) -> int:
    ctx = _CTX
    if ctx is None:
        return default
    try:
        raw = ctx.get_config(key, default)
        return int(raw if raw is not None else default)
    except Exception:
        return default


def _cfg_float(key: str, default: float) -> float:
    ctx = _CTX
    if ctx is None:
        return default
    try:
        raw = ctx.get_config(key, default)
        return float(raw if raw is not None else default)
    except Exception:
        return default


def _text_of(msg: Any) -> str:
    if not isinstance(msg, dict):
        return ""
    content = msg.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict):
                t = part.get("text") or part.get("content") or ""
                if isinstance(t, str):
                    parts.append(t)
        return "\n".join(parts)
    return ""


def _extract_facts(messages: list[Any]) -> list[str]:
    facts: list[str] = []
    seen: set[str] = set()
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        role = str(msg.get("role") or "").lower()
        if role in {"tool", "system", "tool_result"}:
            continue
        text = _text_of(msg).strip()
        if not text:
            continue
        if len(text) > _MAX_MSG_CHARS:
            text = text[:_MAX_MSG_CHARS]
        for chunk in _SENTENCE_RE.split(text):
            fact = " ".join(chunk.split())
            if len(fact) < _MIN_FACT_CHARS:
                continue
            key = fact.lower()
            if key in seen:
                continue
            seen.add(key)
            facts.append(fact)
            if len(facts) >= _MAX_FACTS:
                return facts
    return facts


def _zlib_len(s: str) -> int:
    if not s:
        return 0
    return len(zlib.compress(s.encode("utf-8"), 6))


def _score_facts(
    facts: list[str], min_saving: float
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """MDL: joint zlib length vs leave-one-out. Low saving => redundant."""
    scored: list[dict[str, Any]] = []
    flagged: list[dict[str, Any]] = []
    if not facts:
        return scored, flagged
    joined = "\n".join(facts)
    l_all = _zlib_len(joined)
    kept_words: list[set[str]] = []
    for i, fact in enumerate(facts):
        others = [f for j, f in enumerate(facts) if j != i]
        l_wo = _zlib_len("\n".join(others)) if others else 0
        l_self = max(_zlib_len(fact), 1)
        # Unique information: joint encoding shorter than independent parts.
        # saving ~ 0 when the fact is already implied by the rest.
        saving = (l_wo + l_self - l_all) / float(l_self)
        words = set(_WORD_RE.findall(fact.lower()))
        reason = ""
        redundant = False
        for prev in kept_words:
            union = len(words | prev) or 1
            if (len(words & prev) / union) >= _JACCARD_DUP:
                redundant = True
                reason = "jaccard"
                break
        if not redundant and saving < min_saving:
            redundant = True
            reason = "mdl"
        item = {
            "text": fact[:400],
            "mdl_saving": round(saving, 4),
            "bytes": len(fact.encode("utf-8")),
            "redundant": redundant,
            "reason": reason,
        }
        scored.append(item)
        if redundant:
            flagged.append(item)
        else:
            kept_words.append(words)
    return scored, flagged


def _history(agent: Any) -> list[Any]:
    if agent is None:
        return []
    hist = getattr(agent, "conversation_history", None)
    if isinstance(hist, list):
        return hist
    return []


def on_pre_compress(
    session_id: str = "",
    turn_count: int = 0,
    context_tokens: int = 0,
    trigger_reason: str = "auto",
    agent: Any = None,
    **_kwargs: Any,
) -> None:
    """VALID_HOOKS name is pre_compress (not on_pre_compress). Fail-open."""
    t0 = time.monotonic()
    try:
        depth = _cfg_int("depth_threshold", _DEFAULT_DEPTH)
        min_saving = _cfg_float("mdl_min_saving", _DEFAULT_MDL)
        turns = int(turn_count or 0)
        hist = _history(agent)
        if turns <= 0:
            turns = len(hist)
        record: dict[str, Any] = {
            "ts": _now_iso(),
            "session_id": session_id or getattr(agent, "session_id", "") or "",
            "turn_count": turns,
            "context_tokens": int(context_tokens or 0),
            "trigger_reason": trigger_reason or "auto",
            "depth_threshold": depth,
            "mdl_min_saving": min_saving,
            "gated": False,
            "n_facts": 0,
            "n_redundant": 0,
            "iss_gain": ISS_GAIN,
        }
        if turns <= depth:
            record["gated"] = True
            record["skip"] = "depth"
            record["elapsed_ms"] = round((time.monotonic() - t0) * 1000, 2)
            _append_log(record)
            return
        facts = _extract_facts(hist)
        scored, flagged = _score_facts(facts, min_saving)
        record["n_facts"] = len(scored)
        record["n_redundant"] = len(flagged)
        record["redundant"] = [
            {"text": x["text"][:160], "reason": x["reason"], "mdl_saving": x["mdl_saving"]}
            for x in flagged[:12]
        ]
        record["elapsed_ms"] = round((time.monotonic() - t0) * 1000, 2)
        _append_log(record)
        return
    except Exception as exc:
        logger.debug("compaction-gate: fail-open: %s", exc)
        try:
            _append_log(
                {
                    "ts": _now_iso(),
                    "session_id": session_id or "",
                    "error": type(exc).__name__,
                    "fail_open": True,
                }
            )
        except Exception:
            pass
        return


def register(ctx: Any) -> None:
    global _CTX
    try:
        _CTX = ctx
        if not bool(ctx.get_config("enabled", True)):
            logger.debug("compaction-gate: disabled via settings.enabled")
            return
        ctx.register_hook("pre_compress", on_pre_compress)
        logger.debug("compaction-gate: registered pre_compress")
    except Exception as exc:
        logger.warning("compaction-gate: register failed (fail-open): %s", exc)
