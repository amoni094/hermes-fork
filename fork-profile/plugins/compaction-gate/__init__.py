"""compaction-gate — depth gate + MDL fact scoring on pre_compress.

Fail-open: any exception is swallowed so compression always proceeds.
Does not mutate messages, the compressor, or conversation history.

Architecture
============
Two hooks are registered:

post_compaction
  Fires after every committed compression pass. Writes one row to
  compaction_telemetry(session_id, after_tokens, before_tokens, kind,
  created_at) in state.db. This activates the HHR branch of the gate —
  without it the HHR path is permanently inactive.

pre_compress
  Fires before ContextCompressor.compress() runs. Gate triggers
  (either condition fires):
    1. turn_count >= TURN_THRESHOLD (default 1100)
    2. Head-hit-rate (after_tokens/before_tokens) < HHR_THRESHOLD for
       HHR_K consecutive rows in compaction_telemetry

Hysteresis: once fired for session S at turn T, won't fire again until
T + HYSTERESIS_TURNS (default 200). Prevents redundant extraction on
tightly-spaced compression events.

Short-to-medium bridge: 1 <= low_rows < HHR_K -> soft gate (log only,
no fact extraction) to track the transition window.

On pre_compress gate fire:
  1. Extract up to MAX_FACTS MDL-scored sentences from conversation history.
  2. Dedup by SHA-256 of normalised text.
  3. Write surviving facts to compaction_gate_facts (SQLite + FTS5 cgf_fts).
  4. Build a [HINDSIGHT CONTEXT ...] block (future hook return path).

``pre_compress`` is the public hook name; ``on_pre_compress`` is a legacy alias.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import sqlite3
import time
import threading
import zlib
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

logger = logging.getLogger("compaction-gate")

# ── tunables ──────────────────────────────────────────────────────────────
ISS_GAIN = 0.35
TURN_THRESHOLD = 1100         # gate fires when turn_count >= this
HYSTERESIS_TURNS = 200        # min turns between fires for same session
HHR_THRESHOLD = 0.35          # after_tokens/before_tokens ratio below → poor HHR (< 35% retained)
HHR_K = 3                     # consecutive low-HHR rows needed for hard gate
_DEFAULT_DEPTH = 1100         # legacy config key alias
_DEFAULT_MDL = 0.1
_MAX_FACTS = 40
_MIN_FACT_CHARS = 24
_MAX_MSG_CHARS = 4000
_JACCARD_DUP = 0.85
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+|\n+")
_WORD_RE = re.compile(r"[a-z0-9]{2,}")

# ── module-level state (reset by tests via _schema_ready / _last_fire) ────
_CTX: Any = None
_schema_ready: bool = False
_schema_lock = threading.Lock()
# session_id -> last turn_count at which the gate fired (hysteresis guard)
_last_fire: dict[str, int] = {}


# ── path helpers ──────────────────────────────────────────────────────────

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


def _db_path() -> Path:
    return _profile_root() / "state.db"


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


# ── SQLite schema ─────────────────────────────────────────────────────────

def _ensure_schema(conn: sqlite3.Connection) -> None:
    """Create compaction_gate_facts + FTS5 shadow cgf_fts. Idempotent."""
    global _schema_ready
    if _schema_ready:
        return
    with _schema_lock:
        if _schema_ready:
            return  # double-checked locking
        conn.execute("""
            CREATE TABLE IF NOT EXISTS compaction_gate_facts (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id  TEXT    NOT NULL,
                topic       TEXT    NOT NULL DEFAULT '',
                fact_text   TEXT    NOT NULL,
                confidence  REAL    NOT NULL DEFAULT 1.0,
                created_at  REAL    NOT NULL,
                dedup_hash  TEXT    NOT NULL UNIQUE
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS cgf_session_idx
            ON compaction_gate_facts(session_id)
        """)
        # FTS5 content table backed by compaction_gate_facts
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS cgf_fts
            USING fts5(fact_text, content='compaction_gate_facts', content_rowid='id')
        """)
        conn.commit()
        _schema_ready = True


def _open_db() -> sqlite3.Connection | None:
    """Open the profile state.db; return None on any error (fail-open)."""
    try:
        path = _db_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(path), check_same_thread=False, timeout=5.0)
        conn.execute("PRAGMA journal_mode=WAL")
        _ensure_schema(conn)
        return conn
    except Exception as exc:
        logger.debug("compaction-gate: db open failed: %s", exc)
        return None


# ── gate logic ────────────────────────────────────────────────────────────

def _check_hhr(session_id: str, conn: sqlite3.Connection) -> tuple[bool, bool]:
    """
    Check head-hit-rate from compaction_telemetry.
    Returns (hard_gate, soft_gate):
      hard_gate: K consecutive low-HHR rows exist
      soft_gate: 1 ≤ low-HHR rows < K (short→medium transition)
    """
    try:
        rows = conn.execute(
            "SELECT after_tokens, before_tokens FROM compaction_telemetry "
            "WHERE session_id=? ORDER BY id DESC LIMIT ?",
            (session_id, HHR_K)
        ).fetchall()
    except Exception:
        logger.debug("compaction-gate: compaction_telemetry absent or unreadable; HHR gate inactive")
        return False, False

    if not rows:
        return False, False

    low_rows = [
        r for r in rows
        if isinstance(r[0], (int, float)) and isinstance(r[1], (int, float))
        and r[1] > 0 and (r[0] / r[1]) < HHR_THRESHOLD
    ]
    if len(low_rows) >= HHR_K:
        return True, False
    if 0 < len(low_rows) < HHR_K:
        return False, True
    return False, False


def _check_gate(session_id: str, turn_count: int, conn: sqlite3.Connection) -> tuple[bool, bool]:
    """
    Decide whether the gate fires for this session.
    Returns (fire_full, fire_soft):
      fire_full: extract and persist facts
      fire_soft: log-only transition signal (no facts written)
    Applies hysteresis: once fired at turn T, won't fire_full again until T+HYSTERESIS_TURNS.
    Records the fire turn in _last_fire.
    depth_threshold is read from config at call-time so operators can tune without restart.
    """
    # Read tunable threshold from config (falls back to module constant)
    depth_threshold = _cfg_int("depth_threshold", TURN_THRESHOLD)

    # Hysteresis check
    last = _last_fire.get(session_id, 0)
    if last and (turn_count - last) < HYSTERESIS_TURNS:
        return False, False

    # Hard gate: turn threshold
    if turn_count >= depth_threshold:
        _last_fire[session_id] = turn_count
        return True, False

    # HHR-based gate
    hard, soft = _check_hhr(session_id, conn)
    if hard:
        _last_fire[session_id] = turn_count
        return True, False
    if soft:
        return False, True

    return False, False


# ── fact extraction + scoring ─────────────────────────────────────────────

def _dedup_hash(fact: str) -> str:
    """SHA-256 of lowercased, whitespace-normalised fact text (hex, 64 chars)."""
    normalised = " ".join(fact.lower().split())
    return hashlib.sha256(normalised.encode("utf-8")).hexdigest()


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
    if len(facts) == 1:
        item = {
            "text": facts[0][:400],
            "mdl_saving": 1.0,
            "bytes": len(facts[0].encode("utf-8")),
            "redundant": False,
            "reason": "",
        }
        return [item], []
    joined = "\n".join(facts)
    l_all = _zlib_len(joined)
    kept_words: list[set[str]] = []
    for i, fact in enumerate(facts):
        others = [f for j, f in enumerate(facts) if j != i]
        l_wo = _zlib_len("\n".join(others)) if others else 0
        l_self = max(_zlib_len(fact), 1)
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


# ── persistence ───────────────────────────────────────────────────────────

def _persist_facts(
    conn: sqlite3.Connection, session_id: str, scored: list[dict[str, Any]]
) -> int:
    """Write non-redundant facts to compaction_gate_facts + cgf_fts. Returns count inserted."""
    inserted = 0
    ts = time.time()
    for item in scored:
        if item.get("redundant"):
            continue
        text = item["text"]
        dh = _dedup_hash(text)
        existing = conn.execute(
            "SELECT id FROM compaction_gate_facts WHERE dedup_hash=?", (dh,)
        ).fetchone()
        if existing:
            continue
        conn.execute(
            "INSERT INTO compaction_gate_facts"
            "(session_id, topic, fact_text, confidence, created_at, dedup_hash)"
            "VALUES (?, ?, ?, ?, ?, ?)",
            (session_id, "auto", text, round(item.get("mdl_saving", 1.0), 4), ts, dh),
        )
        rowid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.execute("INSERT INTO cgf_fts(rowid, fact_text) VALUES (?, ?)", (rowid, text))
        inserted += 1
    conn.commit()
    return inserted


# ── retrieval / auto-draw ─────────────────────────────────────────────────

def _auto_draw(conn: sqlite3.Connection, session_id: str, limit: int = 20) -> str:
    """
    Retrieve the most recent persisted facts for session_id.
    Returns a [HINDSIGHT CONTEXT ...] block string, or "" if none.
    """
    try:
        rows = conn.execute(
            "SELECT fact_text FROM compaction_gate_facts "
            "WHERE session_id=? ORDER BY created_at DESC LIMIT ?",
            (session_id, limit),
        ).fetchall()
    except Exception:
        return ""
    if not rows:
        return ""
    lines = [r[0] for r in rows]
    block = "[HINDSIGHT CONTEXT — pre-compression fact archive]\n" + "\n".join(
        f"- {line}" for line in lines
    )
    return block


# ── config helpers ────────────────────────────────────────────────────────

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


def _history(agent: Any) -> list[Any]:
    """Try every known attribute name AIAgent uses for its message store."""
    if agent is None:
        return []
    for attr in ("_session_messages", "conversation_history", "_messages"):
        hist = getattr(agent, attr, None)
        if isinstance(hist, list) and hist:
            return hist
    return []


# ── public hook entry-point ───────────────────────────────────────────────

def pre_compress(
    session_id: str = "",
    turn_count: int = 0,
    context_tokens: int = 0,
    trigger_reason: str = "auto",
    agent: Any = None,
    messages: list | None = None,
    **_kwargs: Any,
) -> dict[str, Any]:
    """
    Main hook. Returns {} always (fail-open).
    On gate fire: extracts MDL facts, persists to SQLite, logs outcome.
    ``messages`` is an optional snapshot from the host (future-compat);
    falls back to agent._session_messages / conversation_history.
    """
    t0 = time.monotonic()
    try:
        min_saving = _cfg_float("mdl_min_saving", _DEFAULT_MDL)
        # Prefer explicitly supplied snapshot; fall back to agent store
        hist = list(messages) if isinstance(messages, list) and messages else _history(agent)
        turns = int(turn_count or 0)
        if turns <= 0:
            turns = len(hist)

        sid = session_id or getattr(agent, "session_id", "") or ""

        conn = _open_db()
        if conn is None:
            _append_log({
                "ts": _now_iso(), "session_id": sid,
                "error": "db_unavailable", "fail_open": True,
            })
            return {}

        try:
            fire_full, fire_soft = _check_gate(sid, turns, conn)

            record: dict[str, Any] = {
                "ts": _now_iso(),
                "session_id": sid,
                "turn_count": turns,
                "context_tokens": int(context_tokens or 0),
                "trigger_reason": trigger_reason or "auto",
                "depth_threshold": TURN_THRESHOLD,
                "mdl_min_saving": min_saving,
                "gated": not (fire_full or fire_soft),  # True = gate blocked, compression proceeds unmodified
                "fire_full": fire_full,
                "fire_soft": fire_soft,
                "n_facts": 0,
                "n_redundant": 0,
                "n_inserted": 0,
                "iss_gain": ISS_GAIN,
            }

            if fire_soft:
                record["note"] = "short_to_medium_transition"
                record["elapsed_ms"] = round((time.monotonic() - t0) * 1000, 2)
                _append_log(record)
                return {}

            if not fire_full:
                record["skip"] = "depth"
                record["elapsed_ms"] = round((time.monotonic() - t0) * 1000, 2)
                _append_log(record)
                return {}

            # Gate fired — extract, score, persist
            facts = _extract_facts(hist)
            scored, flagged = _score_facts(facts, min_saving)
            record["n_facts"] = len(scored)
            record["n_redundant"] = len(flagged)

            n_inserted = _persist_facts(conn, sid, scored)
            record["n_inserted"] = n_inserted

            context_block = _auto_draw(conn, sid)
            if context_block:
                record["hindsight_chars"] = len(context_block)

            record["elapsed_ms"] = round((time.monotonic() - t0) * 1000, 2)
            _append_log(record)
        finally:
            conn.close()

    except Exception as exc:
        logger.debug("compaction-gate: fail-open: %s", exc)
        try:
            _append_log({
                "ts": _now_iso(),
                "session_id": session_id or "",
                "error": type(exc).__name__,
                "fail_open": True,
            })
        except Exception:
            pass

    return {}


# Legacy alias
on_pre_compress = pre_compress


# ── post_compaction hook — writes compaction_telemetry rows ───────────────

def _ensure_telemetry_schema(conn: sqlite3.Connection) -> None:
    """Create compaction_telemetry if absent. Idempotent."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS compaction_telemetry (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id   TEXT    NOT NULL,
            after_tokens INTEGER,
            before_tokens INTEGER,
            kind         TEXT    NOT NULL DEFAULT '',
            created_at   REAL    NOT NULL
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS ct_session_idx
        ON compaction_telemetry(session_id)
    """)
    conn.commit()


def on_post_compaction(
    session_id: str = "",
    before_tokens: int | None = None,
    after_tokens: int | None = None,
    kind: str | None = None,
    **_kwargs: Any,
) -> None:
    """Record one committed compaction pass in compaction_telemetry.

    Fail-open: any exception is swallowed. This is the sole production
    writer for compaction_telemetry; without it the HHR branch of
    _check_hhr() always returns (False, False).
    """
    try:
        conn = _open_db()
        if conn is None:
            return
        try:
            _ensure_telemetry_schema(conn)
            conn.execute(
                "INSERT INTO compaction_telemetry"
                "(session_id, after_tokens, before_tokens, kind, created_at)"
                "VALUES (?, ?, ?, ?, ?)",
                (
                    session_id or "",
                    int(after_tokens) if after_tokens is not None else None,
                    int(before_tokens) if before_tokens is not None else None,
                    kind or "",
                    time.time(),
                ),
            )
            conn.commit()
            logger.debug(
                "compaction-gate: telemetry row: session=%s before=%s after=%s kind=%s",
                session_id, before_tokens, after_tokens, kind,
            )
        finally:
            conn.close()
    except Exception as exc:
        logger.debug("compaction-gate: on_post_compaction fail-open: %s", exc)


# ── plugin registration ───────────────────────────────────────────────────

def register(ctx: Any) -> None:
    global _CTX
    try:
        _CTX = ctx
        if not bool(ctx.get_config("enabled", True)):
            logger.debug("compaction-gate: disabled via settings.enabled")
            return
        ctx.register_hook("pre_compress", pre_compress)
        ctx.register_hook("post_compaction", on_post_compaction)
        logger.debug("compaction-gate: registered pre_compress + post_compaction")
    except Exception as exc:
        logger.warning("compaction-gate: register failed (fail-open): %s", exc)
