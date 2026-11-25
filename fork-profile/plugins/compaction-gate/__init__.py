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
    2. context_tokens >= TOKEN_THRESHOLD (default 100 000) — the host
       post_tool overflow path where _session_messages is empty and
       turn_count=0 (token count is the reliable signal there)
    3. Head-hit-rate SPRT (Wald 1945) on after_tokens/before_tokens
       from compaction_telemetry — replaces the fixed-K consecutive
       streak. H1 (needs compress) when LLR >= A; H0 (healthy) when
       LLR <= B; soft gate when 0 < LLR < A.

Hysteresis: once fired for session S, won't fire again until either:
- turn_count - last_turn_count >= HYSTERESIS_TURNS (turn-based path), or
- time.time() - last_fire_ts >= HYSTERESIS_TURNS*2 seconds (token path, turn_count=0).
Prevents redundant extraction on tightly-spaced compression events.

Short-to-medium bridge: SPRT LLR in (0, A) -> soft gate (log only,
no fact extraction) while evidence trends toward H1.

On pre_compress gate fire:
  1. Extract up to MAX_FACTS MDL-scored sentences from conversation history.
  2. Dedup by SHA-256 of normalised text.
  3. Write surviving facts to compaction_gate_facts (SQLite + FTS5 cgf_fts).
  4. Build a [HINDSIGHT CONTEXT ...] block and return it as
     ``{"hindsight_context": block}`` so the host can inject it.

Information-theoretic extensions
================================
1. Role-weighted sentence scoring (information bottleneck). User text is
   high-relevance Y; tool_result is low-relevance noise. Facts carry a
   role weight that tightens/loosens the MDL min-saving threshold.
2. Fill-rate adaptive gate (rate-distortion). When context_tokens /
   context_limit >= _FILL_RATE_AGGRESSIVE, TOKEN_THRESHOLD is reduced so
   the gate fires earlier at high fill (higher distortion tolerance).
3. Query-relevant fact retrieval (Wyner-Ziv). ``_auto_draw`` ranks
   persisted facts by TF-IDF-like overlap with recent user terms (decoder
   side information) instead of recency alone.

``pre_compress`` is the public hook name; ``on_pre_compress`` is a legacy alias.
"""
from __future__ import annotations

import hashlib
import json
import logging
import math
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
TOKEN_THRESHOLD = 100_000     # gate fires when context_tokens >= this (host post_tool path)
HYSTERESIS_TURNS = 200        # min turns between fires for same session
HHR_THRESHOLD = 0.35          # after_tokens/before_tokens ratio below → poor HHR (< 35% retained)
HHR_K = 3                     # kept for test/backward compat; gate uses SPRT not fixed-K
_SPRT_ALPHA = 0.05            # max false-compress rate
_SPRT_BETA = 0.10             # max miss rate
_SPRT_H0_LOW = HHR_THRESHOLD  # alias — H0: HHR above this = healthy
_SPRT_EPS = 0.01              # density floor to avoid log(0)
_SPRT_MAX_ROWS = 20           # look back at most 20 telemetry rows
SPRT_P0, SPRT_P1 = 0.40, 0.30
SPRT_ALPHA, SPRT_BETA = 0.05, 0.10
SPRT_N_MAX = 30  # truncated SPRT: fail-closed reject, never promote
COSINE_DUP = 0.95
DISTORTION_REFUSE = 0.5
_TFIDF_STOP = frozenset({
    "the", "a", "an", "of", "to", "and", "or", "in", "on", "for", "is", "it",
})
_DEFAULT_DEPTH = 1100         # legacy config key alias
_DEFAULT_MDL = 0.1
_MAX_FACTS = 40
_MIN_FACT_CHARS = 24
_MAX_MSG_CHARS = 4000
_JACCARD_DUP = 0.85
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+|\n+")
_WORD_RE = re.compile(r"[a-z0-9]{2,}")
_ROLE_WEIGHTS = {
    "user": 1.0,
    "assistant": 0.7,
    "tool_result": 0.3,
    "tool": 0.3,
    "system": 0.5,
}
_FILL_RATE_AGGRESSIVE = 0.80
_DEFAULT_CONTEXT_LIMIT = 200_000

# ── module-level state (reset by tests via _schema_ready / _last_fire) ────
_CTX: Any = None
_schema_ready: bool = False
_schema_lock = threading.Lock()
# session_id -> (last_turn_count, last_fire_timestamp) hysteresis guard
_last_fire: dict[str, tuple[int, float]] = {}


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
        conn.execute("""
            CREATE TABLE IF NOT EXISTS compaction_sprt_state (
                session_id TEXT PRIMARY KEY,
                parent_session_id TEXT,
                llr REAL NOT NULL DEFAULT 0,
                n_obs INTEGER NOT NULL DEFAULT 0,
                n_hits INTEGER NOT NULL DEFAULT 0,
                last_x INTEGER,
                last_decision TEXT NOT NULL DEFAULT 'continue',
                updated_at REAL
            )
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


# ── SPRT lambda accumulator ───────────────────────────────────────────────

def sprt_bounds() -> tuple[float, float]:
    """Return (A, B) Wald log-thresholds.

    A = log((1-β)/α) = log(18) at α=0.05, β=0.10.
    B = log(β/(1-α)).
    log((1-α)/α)=log(19) is the α=β approximation and is wrong here.
    """
    a = math.log((1.0 - SPRT_BETA) / SPRT_ALPHA)
    b = math.log(SPRT_BETA / (1.0 - SPRT_ALPHA))
    return a, b


def sprt_llr_increment(x: int) -> float:
    """Bernoulli LLR step. x=1 (hit) is negative; x=0 (miss) is positive."""
    if int(x):
        return math.log(SPRT_P1 / SPRT_P0)
    return math.log((1.0 - SPRT_P1) / (1.0 - SPRT_P0))


def observe_hhr_ratio(after: int, before: int) -> int:
    """1 iff before>0 and after/before >= SPRT_P0; else 0."""
    try:
        if before and before > 0 and (after / before) >= SPRT_P0:
            return 1
        return 0
    except Exception:
        return 0


def update_sprt(
    conn: sqlite3.Connection,
    session_id: str,
    x: int,
    parent_session_id: str | None = None,
) -> dict:
    """Load row or inherit parent llr/n; add delta; persist; return state dict."""
    a_bound, b_bound = sprt_bounds()
    xbit = 1 if int(x) else 0
    delta = sprt_llr_increment(xbit)
    row = conn.execute(
        "SELECT llr, n_obs, n_hits FROM compaction_sprt_state WHERE session_id=?",
        (session_id,),
    ).fetchone()
    if row is None and parent_session_id:
        row = conn.execute(
            "SELECT llr, n_obs, n_hits FROM compaction_sprt_state WHERE session_id=?",
            (parent_session_id,),
        ).fetchone()
    if row is None:
        llr, n_obs, n_hits = 0.0, 0, 0
    else:
        llr, n_obs, n_hits = float(row[0] or 0.0), int(row[1] or 0), int(row[2] or 0)
    llr = llr + delta
    n_obs = n_obs + 1
    n_hits = n_hits + xbit
    if llr >= a_bound:
        decision = "accept_h1"
    elif llr <= b_bound:
        decision = "accept_h0"
    elif n_obs >= SPRT_N_MAX:
        # Truncated SPRT is fail-closed: never promote H0.
        decision = "truncated_reject"
    else:
        decision = "continue"
    conn.execute(
        """
        INSERT INTO compaction_sprt_state
            (session_id, parent_session_id, llr, n_obs, n_hits, last_x, last_decision, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(session_id) DO UPDATE SET
            parent_session_id=excluded.parent_session_id,
            llr=excluded.llr,
            n_obs=excluded.n_obs,
            n_hits=excluded.n_hits,
            last_x=excluded.last_x,
            last_decision=excluded.last_decision,
            updated_at=excluded.updated_at
        """,
        (
            session_id,
            parent_session_id,
            llr,
            n_obs,
            n_hits,
            xbit,
            decision,
            time.time(),
        ),
    )
    conn.commit()
    return {
        "llr": llr,
        "n_obs": n_obs,
        "n_hits": n_hits,
        "decision": decision,
        "a": a_bound,
        "b": b_bound,
    }


# ── TF-IDF cosine near-dup ────────────────────────────────────────────────

def _is_prospective(text: str) -> bool:
    t = text or ""
    return "[PROSPECTIVE]" in t or "[TODO]" in t or "[ACTION]" in t


def _tfidf_tokens(text: str) -> list[str]:
    return [t for t in (text or "").lower().split() if t and t not in _TFIDF_STOP]


def _tfidf_vector(text: str, df: dict[str, int], n_docs: int) -> dict[str, float]:
    tokens = _tfidf_tokens(text)
    if not tokens:
        return {}
    counts: dict[str, int] = {}
    for t in tokens:
        counts[t] = counts.get(t, 0) + 1
    length = float(len(tokens))
    vec: dict[str, float] = {}
    for t, cnt in counts.items():
        tf = cnt / length
        idf = math.log((n_docs + 1) / (df.get(t, 0) + 1)) + 1.0
        vec[t] = tf * idf
    norm = math.sqrt(sum(v * v for v in vec.values()))
    if norm <= 0.0:
        return {}
    return {k: v / norm for k, v in vec.items()}


def _cosine_sparse(a: dict, b: dict) -> float:
    if not a or not b:
        return 0.0
    dot = sum(a[k] * b[k] for k in a.keys() & b.keys())
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    if na <= 0.0 or nb <= 0.0:
        return 0.0
    return dot / (na * nb)


def _corpus_df(conn: sqlite3.Connection) -> tuple[dict[str, int], int]:
    rows = conn.execute(
        "SELECT fact_text FROM compaction_gate_facts ORDER BY created_at DESC LIMIT 500"
    ).fetchall()
    df: dict[str, int] = {}
    n_docs = 0
    for (text,) in rows:
        n_docs += 1
        for t in set(_tfidf_tokens(text or "")):
            df[t] = df.get(t, 0) + 1
    return df, n_docs


def _max_cosine_against_corpus(text: str, conn: sqlite3.Connection) -> float:
    df, n_docs = _corpus_df(conn)
    if n_docs <= 0:
        return 0.0
    query = _tfidf_vector(text, df, n_docs)
    if not query:
        return 0.0
    best = 0.0
    rows = conn.execute(
        "SELECT fact_text FROM compaction_gate_facts ORDER BY created_at DESC LIMIT 500"
    ).fetchall()
    for (fact_text,) in rows:
        other = _tfidf_vector(fact_text or "", df, n_docs)
        c = _cosine_sparse(query, other)
        best = max(best, c)
    return best


# ── token-Jaccard distortion gate ─────────────────────────────────────────

def tokenize_ws(text: str) -> set[str]:
    return set((text or "").split())


def token_jaccard_distortion(pre: str, post: str) -> float:
    p, q = tokenize_ws(pre), tokenize_ws(post)
    if not p and not q:
        return 0.0
    union = p | q
    if not union:
        return 0.0
    return 1.0 - (len(p & q) / len(union))


def distortion_gate(
    pre: str, post: str, threshold: float = DISTORTION_REFUSE
) -> dict:
    """Alarm on rewrite/fabrication, not on extractive compression.

    DPI: I(decision; compressed) ≤ I(decision; raw). Pure deletions
    (post tokens ⊆ pre tokens, post nonempty) cannot invent decision
    info, so they must not refuse even when Jaccard distortion > 0.5.
    Empty post vs nonempty pre still refuses (total wipe).
    """
    d = token_jaccard_distortion(pre, post)
    j = 1.0 - d
    pre_tok, post_tok = tokenize_ws(pre), tokenize_ws(post)
    extractive = bool(post_tok) and post_tok <= pre_tok
    refuse = (d > threshold) and not extractive
    return {
        "distortion": d,
        "jaccard": j,
        "alarm": refuse,
        "refuse": refuse,
        "extractive": extractive,
        "n_pre": len(pre_tok),
        "n_post": len(post_tok),
    }


def _distortion_log_path() -> Path:
    return _profile_root() / "cache" / "compaction-distortion-log.jsonl"


def _append_distortion_log(record: dict[str, Any]) -> None:
    path = _distortion_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    line = (json.dumps(record, ensure_ascii=False, default=str) + "\n").encode("utf-8")
    flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
    fd = os.open(str(path), flags, 0o644)
    try:
        os.write(fd, line)
    finally:
        os.close(fd)


# ── gate logic ────────────────────────────────────────────────────────────

def _check_hhr(session_id: str, conn: sqlite3.Connection) -> tuple[bool, bool]:
    """
    Wald SPRT on head-hit-rate from compaction_telemetry.

    H0: healthy (HHR >= _SPRT_H0_LOW). H1: needs compress (HHR < _SPRT_H0_LOW).
    Returns (hard_gate, soft_gate):
      hard_gate: LLR >= A (H1 accepted)
      soft_gate: 0 < LLR < A (trending toward H1; log-only)
    Fail-open: any exception returns (False, False).
    Prefers compaction_sprt_state.llr when a row exists; falls back to
    telemetry SPRT / K=3 streak if the table is empty.
    """
    try:
        try:
            state = conn.execute(
                "SELECT llr, last_decision, n_obs FROM compaction_sprt_state WHERE session_id=?",
                (session_id,),
            ).fetchone()
        except Exception:
            try:
                state = conn.execute(
                    "SELECT llr FROM compaction_sprt_state WHERE session_id=?",
                    (session_id,),
                ).fetchone()
                if state is not None:
                    state = (state[0], None, None)
            except Exception:
                state = None
        if state is not None:
            llr = float(state[0] or 0.0)
            decision = (state[1] or "") if len(state) > 1 else ""
            n_obs = int(state[2] or 0) if len(state) > 2 and state[2] is not None else 0
            a_bound, _b_bound = sprt_bounds()
            if decision == "accept_h0":
                return False, False
            if decision in ("accept_h1", "truncated_reject") or n_obs >= SPRT_N_MAX:
                return True, False
            if llr >= a_bound:
                return True, False
            if 0 < llr < a_bound:
                return False, True
            return False, False
        a_bound = math.log((1.0 - _SPRT_BETA) / _SPRT_ALPHA)
        b_bound = math.log(_SPRT_BETA / (1.0 - _SPRT_ALPHA))
        rows = conn.execute(
            "SELECT after_tokens, before_tokens FROM compaction_telemetry "
            "WHERE session_id=? ORDER BY id DESC LIMIT ?",
            (session_id, _SPRT_MAX_ROWS),
        ).fetchall()
        if not rows:
            return False, False

        # Piecewise-uniform densities on [0, θ] vs (θ, 1]. The off-support
        # floor must be high enough that ONE poor HHR stays in (0, A) (soft
        # gate) while HHR_K consecutive poor rows still accept H1.
        f1_low = 1.0 / _SPRT_H0_LOW
        f0_high = 1.0 / (1.0 - _SPRT_H0_LOW)
        one_obs_cap = f1_low / math.exp(a_bound)  # LLR == A at this eps
        eps = max(_SPRT_EPS, one_obs_cap * 1.25)

        llr = 0.0
        for r in rows:
            if not (
                isinstance(r[0], (int, float))
                and isinstance(r[1], (int, float))
                and r[1] > 0
            ):
                continue
            hhr = r[0] / r[1]
            f1 = f1_low if hhr < _SPRT_H0_LOW else eps
            f0 = eps if hhr < _SPRT_H0_LOW else f0_high
            llr += math.log(f1 / f0)

        if llr >= a_bound:
            return True, False
        if llr <= b_bound:
            return False, False
        if llr > 0:
            return False, True
        return False, False
    except Exception:
        logger.debug(
            "compaction-gate: compaction_telemetry absent or unreadable; HHR gate inactive"
        )
        return False, False


_FUSED_P_THRESHOLD = 0.65
_FUSED_MAX_AGE_S = 3600.0


def _check_fused_signal() -> bool:
    """Read cache/compaction-fused-signal.json; fire_full if fresh FUSE_COMPACT."""
    try:
        path = _profile_root() / "cache" / "compaction-fused-signal.json"
        if not path.is_file():
            return False
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return False
        if str(data.get("recommend") or "") != "FUSE_COMPACT":
            return False
        try:
            p_compact = float(data.get("p_compact") or 0.0)
        except (TypeError, ValueError):
            return False
        if p_compact < _FUSED_P_THRESHOLD:
            return False
        ts_raw = data.get("ts")
        if not isinstance(ts_raw, str) or not ts_raw.strip():
            return False
        ts = datetime.fromisoformat(ts_raw)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        age = datetime.now(UTC) - ts.astimezone(UTC)
        if age.total_seconds() > _FUSED_MAX_AGE_S or age.total_seconds() < 0:
            return False
        return True
    except Exception:
        return False


def _check_gate(session_id: str, turn_count: int, conn: sqlite3.Connection,
                context_tokens: int = 0) -> tuple[bool, bool]:
    """
    Decide whether the gate fires for this session.
    Returns (fire_full, fire_soft):
      fire_full: extract and persist facts
      fire_soft: log-only transition signal (no facts written)
    Applies hysteresis: once fired at turn T, won't fire_full again until T+HYSTERESIS_TURNS.
    Records the fire turn in _last_fire.
    depth_threshold is read from config at call-time so operators can tune without restart.
    Token gate: fires when context_tokens >= token_threshold (host post_tool overflow path where
    _session_messages is empty and turn_count is 0).
    """
    # Read tunable threshold from config (falls back to module constant)
    depth_threshold = _cfg_int("depth_threshold", TURN_THRESHOLD)
    token_threshold = _cfg_int("token_threshold", TOKEN_THRESHOLD)
    # Rate-distortion: at high fill, tolerate more distortion — fire earlier.
    try:
        context_limit = _cfg_int("context_limit", _DEFAULT_CONTEXT_LIMIT)
        if context_tokens > 0 and context_limit > 0:
            fill_rate = context_tokens / context_limit
            if fill_rate >= _FILL_RATE_AGGRESSIVE:
                token_threshold = int(token_threshold * 0.75)
    except Exception:
        pass
    # Hysteresis: keyed on turn count when available, timestamp otherwise.
    # _last_fire stores (last_turns, last_ts) per session.
    last_entry = _last_fire.get(session_id)
    if last_entry is not None:
        last_turns, last_ts = last_entry if isinstance(last_entry, tuple) else (last_entry, 0.0)
        elapsed = time.time() - last_ts if last_ts else float("inf")
        if turn_count > 0 and last_turns > 0:
            # Turn-based hysteresis: both sides have real turn counts
            if (turn_count - last_turns) < HYSTERESIS_TURNS:
                return False, False
        else:
            # Time-based hysteresis: covers token path (turn_count=0) and
            # token→turn transition (last_turns=0 but fired recently)
            if elapsed < (HYSTERESIS_TURNS * 2):
                return False, False

    # Hard gate: turn threshold OR token overflow (post_tool path)
    if turn_count >= depth_threshold or (context_tokens >= token_threshold > 0):
        _last_fire[session_id] = (turn_count, time.time())
        return True, False

    # HHR-based gate
    hard, soft = _check_hhr(session_id, conn)
    if hard:
        _last_fire[session_id] = (turn_count, time.time())
        return True, False

    # Fused multi-trigger posterior (naive-Bayes log-odds). Fresh FUSE_COMPACT
    # with p_compact >= 0.65 is an additional hard-gate source.
    try:
        if _check_fused_signal():  # sibling may define this; fail-open if absent
            _last_fire[session_id] = (turn_count, time.time())
            return True, False
    except Exception:
        pass

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


def _role_weight(role: str) -> float:
    try:
        return max(0.1, min(1.0, float(_ROLE_WEIGHTS.get(role, 0.5))))
    except Exception:
        return 0.5


def _extract_facts(messages: list[Any]) -> list[tuple[str, float]]:
    """Extract (text, role_weight) pairs. Fail-open to unweighted user facts."""
    try:
        facts: list[tuple[str, float]] = []
        seen: set[str] = set()
        for msg in messages:
            if not isinstance(msg, dict):
                continue
            role = str(msg.get("role") or "user").lower() or "user"
            weight = _role_weight(role)
            text = _text_of(msg).strip()
            if not text:
                continue
            if len(text) > _MAX_MSG_CHARS:
                text = text[:_MAX_MSG_CHARS]
            min_chars = _MIN_FACT_CHARS * 2 if role in {"tool_result", "tool"} else _MIN_FACT_CHARS
            for chunk in _SENTENCE_RE.split(text):
                fact = " ".join(chunk.split())
                if len(fact) < min_chars:
                    continue
                key = fact.lower()
                if key in seen:
                    continue
                seen.add(key)
                facts.append((fact, weight))
                if len(facts) >= _MAX_FACTS:
                    return facts
        return facts
    except Exception as exc:
        logger.debug("compaction-gate: _extract_facts fail-open: %s", exc)
        return []


def _zlib_len(s: str) -> int:
    if not s:
        return 0
    return len(zlib.compress(s.encode("utf-8"), 6))


def _normalize_fact_weights(facts: list[Any]) -> list[tuple[str, float]]:
    """Accept list[str] or list[tuple[str, float]]; default weight 1.0."""
    out: list[tuple[str, float]] = []
    for f in facts:
        if isinstance(f, str):
            out.append((f, 1.0))
            continue
        if isinstance(f, (tuple, list)) and f:
            text = str(f[0])
            if len(f) >= 2:
                try:
                    w = max(0.1, min(1.0, float(f[1])))
                except Exception:
                    w = 1.0
            else:
                w = 1.0
            out.append((text, w))
            continue
        out.append((str(f), 1.0))
    return out


def _score_facts(
    facts: list[tuple[str, float]] | list[str], min_saving: float
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """MDL: joint zlib length vs leave-one-out. Low saving => redundant.

    Role weight adjusts the MDL threshold: effective_min = min_saving / weight.
    User facts (weight 1.0) keep the baseline; tool_result (0.3) must save more.
    Plain list[str] is treated as weight 1.0 for backward compatibility.
    """
    scored: list[dict[str, Any]] = []
    flagged: list[dict[str, Any]] = []
    try:
        weighted = _normalize_fact_weights(facts)
    except Exception:
        weighted = [(str(f), 1.0) for f in facts]
    if not weighted:
        return scored, flagged
    texts = [t for t, _ in weighted]
    if len(weighted) == 1:
        item = {
            "text": texts[0][:400],
            "mdl_saving": 1.0,
            "bytes": len(texts[0].encode("utf-8")),
            "redundant": False,
            "reason": "",
            "weight": weighted[0][1],
        }
        return [item], []
    joined = "\n".join(texts)
    l_all = _zlib_len(joined)
    kept_words: list[set[str]] = []
    for i, (fact, weight) in enumerate(weighted):
        others = [t for j, t in enumerate(texts) if j != i]
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
        try:
            effective_min = min_saving / weight if weight else min_saving
        except Exception:
            effective_min = min_saving
        if not redundant and saving < effective_min:
            redundant = True
            reason = "mdl"
        item = {
            "text": fact[:400],
            "mdl_saving": round(saving, 4),
            "bytes": len(fact.encode("utf-8")),
            "redundant": redundant,
            "reason": reason,
            "weight": weight,
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
        try:
            if not _is_prospective(text) and _max_cosine_against_corpus(text, conn) > COSINE_DUP:
                continue
        except Exception:
            pass
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

def _tfidf_score(fact_text: str, query_terms: set[str]) -> float:
    """Term-overlap score: query hits / sqrt(|fact words|). Fail-open to 0.0."""
    try:
        if not query_terms:
            return 0.0
        words = _WORD_RE.findall((fact_text or "").lower())
        if not words:
            return 0.0
        hits = sum(1 for w in words if w in query_terms)
        return hits / math.sqrt(len(words))
    except Exception:
        return 0.0


def _auto_draw(
    conn: sqlite3.Connection,
    session_id: str,
    limit: int = 20,
    query_terms: set[str] | None = None,
) -> str:
    """
    Retrieve persisted facts for session_id.
    With query_terms: rank up to limit*3 candidates by TF-IDF overlap,
    tie-break created_at DESC. Without: recency only.
    Returns a [HINDSIGHT CONTEXT ...] block string, or "" if none.
    """
    try:
        use_query = bool(query_terms)
        fetch_limit = (limit * 3) if use_query else limit
        if use_query:
            rows = conn.execute(
                "SELECT fact_text, created_at FROM compaction_gate_facts "
                "WHERE session_id=? ORDER BY created_at DESC LIMIT ?",
                (session_id, fetch_limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT fact_text FROM compaction_gate_facts "
                "WHERE session_id=? ORDER BY created_at DESC LIMIT ?",
                (session_id, fetch_limit),
            ).fetchall()
    except Exception:
        return ""
    if not rows:
        return ""
    lines: list[str]
    if use_query:
        try:
            scored: list[tuple[float, float, str]] = []
            for r in rows:
                text = r[0]
                created = float(r[1]) if len(r) > 1 and r[1] is not None else 0.0
                scored.append((_tfidf_score(text, query_terms or set()), created, text))
            scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
            lines = [t for _, _, t in scored[:limit]]
        except Exception:
            lines = [r[0] for r in rows[:limit]]
    else:
        lines = [r[0] for r in rows]
    if not lines:
        return ""
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
    Main hook. Fail-open: returns {} on skip/error.
    On full gate fire: extracts MDL facts, persists to SQLite, logs outcome,
    and returns ``{"hindsight_context": block}`` when the auto-draw is non-empty.
    ``messages`` is an optional snapshot from the host (future-compat);
    falls back to agent._session_messages / conversation_history.
    """
    t0 = time.monotonic()
    try:
        min_saving = _cfg_float("mdl_min_saving", _DEFAULT_MDL)
        depth_threshold = _cfg_int("depth_threshold", TURN_THRESHOLD)
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
            fire_full, fire_soft = _check_gate(sid, turns, conn, context_tokens=int(context_tokens or 0))

            record: dict[str, Any] = {
                "ts": _now_iso(),
                "session_id": sid,
                "turn_count": turns,
                "context_tokens": int(context_tokens or 0),
                "trigger_reason": trigger_reason or "auto",
                "depth_threshold": depth_threshold,
                "mdl_min_saving": min_saving,
                "gated": not (fire_full or fire_soft),  # True = gate blocked, compression proceeds unmodified
                "fire_full": fire_full,
                "fire_soft": fire_soft,
                "n_facts": 0,
                "n_redundant": 0,
                "n_inserted": 0,
                "iss_gain": ISS_GAIN,
            }
            try:
                ctx_tokens = int(context_tokens or 0)
                context_limit = _cfg_int("context_limit", _DEFAULT_CONTEXT_LIMIT)
                fill_rate = (ctx_tokens / context_limit) if ctx_tokens > 0 and context_limit > 0 else 0.0
                record["fill_rate"] = round(fill_rate, 4)
                record["context_limit"] = context_limit
            except Exception:
                record["fill_rate"] = 0.0

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

            context_block = ""
            try:
                query_terms: set[str] = set()
                for msg in hist[-6:]:
                    if isinstance(msg, dict) and msg.get("role") == "user":
                        query_terms |= set(_WORD_RE.findall(_text_of(msg).lower()))
                context_block = _auto_draw(conn, sid, query_terms=query_terms)
            except Exception as exc:
                logger.debug("compaction-gate: query draw fail-open: %s", exc)
                try:
                    context_block = _auto_draw(conn, sid)
                except Exception:
                    context_block = ""
            if context_block:
                record["hindsight_chars"] = len(context_block)

            record["elapsed_ms"] = round((time.monotonic() - t0) * 1000, 2)
            _append_log(record)
            return {"hindsight_context": context_block} if context_block else {}
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


def _kw_int(src: dict[str, Any], *names: str) -> int | None:
    """First convertible int among *names*; None if all missing/invalid."""
    for name in names:
        val = src.get(name)
        if val is None or isinstance(val, bool):
            continue
        try:
            return int(val)
        except (TypeError, ValueError):
            continue
    return None


def on_post_compaction(
    session_id: str = "",
    before_tokens: int | None = None,
    after_tokens: int | None = None,
    kind: str | None = None,
    **kwargs: Any,
) -> None:
    """Record one committed compaction pass in compaction_telemetry.

    Fail-open: any exception is swallowed. This is the sole production
    writer for compaction_telemetry; without it the HHR branch of
    _check_hhr() always returns (False, False).

    Token counts: host paths disagree on names. fire_post_compaction
    (compaction_events) passes before_tokens/after_tokens; the v1
    compaction payload and some callers use tokens_before/tokens_after.
    Probe all known aliases; missing values stay NULL.
    """
    try:
        merged = {
            "before_tokens": before_tokens,
            "after_tokens": after_tokens,
            "kind": kind,
            **kwargs,
        }
        after = _kw_int(
            merged,
            "after_tokens",
            "tokens_after",
            "context_tokens_after",
            "compressed_tokens",
        )
        before = _kw_int(
            merged,
            "before_tokens",
            "tokens_before",
            "context_tokens_before",
            "original_tokens",
        )
        kind_val = merged.get("kind") or merged.get("reason") or ""
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
                    after,
                    before,
                    kind_val if isinstance(kind_val, str) else str(kind_val),
                    time.time(),
                ),
            )
            conn.commit()
            try:
                if after is not None and before is not None:
                    x = observe_hhr_ratio(after, before)
                    parent_id = merged.get("parent_session_id") or merged.get("parent_id")
                    if parent_id is not None:
                        parent_id = str(parent_id)
                    update_sprt(conn, session_id or "", x, parent_id)
            except Exception:
                pass
            try:
                pre_text = merged.get("pre_text")
                if pre_text is None:
                    pre_text = merged.get("before_text")
                if pre_text is None:
                    pre_text = merged.get("original_text")
                post_text = merged.get("post_text")
                if post_text is None:
                    post_text = merged.get("after_text")
                if post_text is None:
                    post_text = merged.get("compressed_text")
                if pre_text is not None or post_text is not None:
                    dg = distortion_gate(str(pre_text or ""), str(post_text or ""))
                    rec = {
                        "ts": _now_iso(),
                        "session_id": session_id or "",
                        **dg,
                    }
                    if dg.get("refuse"):
                        rec["kind"] = "high_distortion_alarm"
                    _append_distortion_log(rec)
                    if dg.get("refuse"):
                        _append_log({
                            "ts": rec["ts"],
                            "session_id": session_id or "",
                            "kind": "high_distortion_alarm",
                            "distortion": dg.get("distortion"),
                            "refuse": True,
                        })
            except Exception:
                pass
            logger.debug(
                "compaction-gate: telemetry row: session=%s before=%s after=%s kind=%s",
                session_id, before, after, kind_val,
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


def _self_test() -> int:
    """Exercise the three information-theoretic extensions. Returns pass count."""
    passed = 0

    msgs = [
        {"role": "user", "content": "The user wants a compact representation of session facts now."},
        {"role": "tool_result", "content": "short noise"},
        {
            "role": "tool_result",
            "content": "tool payload " + ("x" * (_MIN_FACT_CHARS * 2)),
        },
        {
            "role": "assistant",
            "content": "The assistant reply discusses information bottleneck weighting clearly.",
        },
    ]
    extracted = _extract_facts(msgs)
    assert all(isinstance(x, tuple) and len(x) == 2 for x in extracted), extracted
    assert any(abs(w - 1.0) < 1e-9 for _, w in extracted)
    assert any(abs(w - 0.7) < 1e-9 for _, w in extracted)
    assert any(abs(w - 0.3) < 1e-9 for _, w in extracted)
    assert not any("short noise" in t for t, _ in extracted)
    scored_plain, _ = _score_facts(["A unique fact about compression theory and gates xx."], 0.1)
    assert scored_plain and scored_plain[0]["mdl_saving"] == 1.0
    passed += 1

    class _FakeCtx:
        def get_config(self, key: str, default: Any = None) -> Any:
            if key == "context_limit":
                return 100_000
            return default

    global _CTX, _last_fire
    prev_ctx, prev_fire = _CTX, dict(_last_fire)
    try:
        _CTX = _FakeCtx()
        _last_fire.clear()
        conn = sqlite3.connect(":memory:")
        ff, fs = _check_gate("fill-low", 0, conn, context_tokens=80_000)
        assert ff and not fs, (ff, fs)
        _last_fire.clear()
        _CTX = None
        ff2, _ = _check_gate("fill-base", 0, conn, context_tokens=80_000)
        assert not ff2
        conn.close()
    finally:
        _CTX = prev_ctx
        _last_fire.clear()
        _last_fire.update(prev_fire)
    passed += 1

    assert _tfidf_score("alpha beta gamma", set()) == 0.0
    assert _tfidf_score("alpha beta gamma", {"alpha"}) > 0.0
    conn = sqlite3.connect(":memory:")
    _schema_ready_prev = _schema_ready
    try:
        globals()["_schema_ready"] = False
        _ensure_schema(conn)
        ts = time.time()
        relevant = "Wyner Ziv side information ranks memory facts by query overlap"
        stale = "Unrelated cooking recipe uses unsalted butter and flour only"
        for fact, created in ((relevant, ts), (stale, ts + 1.0)):
            dh = _dedup_hash(fact)
            conn.execute(
                "INSERT INTO compaction_gate_facts"
                "(session_id, topic, fact_text, confidence, created_at, dedup_hash)"
                "VALUES (?, ?, ?, ?, ?, ?)",
                ("s-q", "auto", fact, 1.0, created, dh),
            )
        conn.commit()
        recency = _auto_draw(conn, "s-q", limit=1)
        assert stale in recency and relevant not in recency
        ranked = _auto_draw(conn, "s-q", limit=1, query_terms={"wyner", "ziv", "query"})
        assert relevant in ranked
    finally:
        conn.close()
        globals()["_schema_ready"] = _schema_ready_prev
    passed += 1
    return passed


if __name__ == "__main__":
    n = _self_test()
    print(f"self-test ok ({n} checks)")
