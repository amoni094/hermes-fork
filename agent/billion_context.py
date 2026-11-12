"""Billion-context techniques for hermes-fork (fail-open, no external proxy).

Thresholds are derived at runtime from the model context window, not from
billion-context's 200K production constants:

    raw_zone_tokens = min(50_000, int(context_limit * 0.25))
    growth_floor    = max(10_000, int(context_limit * 0.22))
    ccr_min_tokens  = max(500,    int(context_limit * 0.02))
    nudge_threshold = 0.45          # fraction of context_limit
    tier2_enabled   = context_limit >= 128_000
    tier3_enabled   = context_limit >= 500_000

Unknown/unavailable context_limit defaults to 128_000 (conservative medium).
"""
from __future__ import annotations

import json
import logging
import re
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

DEFAULT_CONTEXT_LIMIT = 128_000
NUDGE_THRESHOLD_FRACTION = 0.45
HARD_WINDOW_FRACTION = 0.90
TIER2_MIN_CONTEXT = 128_000
TIER3_MIN_CONTEXT = 500_000
TIER1_SURVIVAL_ROUNDS = 3
CRUSH_MIN_REDUCTION = 0.10
_ERROR_LINE_RE = re.compile(
    r"\b(ERROR|FAIL(?:ED|URE)?|FATAL|CRITICAL|Exception|Traceback|PANIC)\b",
    re.IGNORECASE,
)
_WARN_LINE_RE = re.compile(r"\b(WARN(?:ING)?)\b", re.IGNORECASE)
_PLACEHOLDER_MARK = "[stored tool output ·"
_CCR_LOCK = threading.Lock()
# session_id -> {store_id: text}. Disk is source of truth; this is a hot cache
# plus a session-end cleanup index.
_ccr_store: dict[str, dict[str, str]] = {}


def resolve_context_limit(source: Any = None) -> int:
    """Best-effort context window. Never raises. Defaults to 128K."""
    try:
        if isinstance(source, (int, float)) and source > 0:
            return int(source)
        if source is not None:
            for attr in ("context_length", "context_limit", "model_context_length"):
                val = getattr(source, attr, None)
                if isinstance(val, (int, float)) and val > 0:
                    return int(val)
            nested = getattr(source, "context_compressor", None)
            if nested is not None:
                return resolve_context_limit(nested)
            if isinstance(source, dict):
                for key in ("context_length", "context_limit"):
                    val = source.get(key)
                    if isinstance(val, (int, float)) and val > 0:
                        return int(val)
    except Exception:
        logger.debug("billion_context: context_limit probe failed", exc_info=True)
    return DEFAULT_CONTEXT_LIMIT


def scaled_thresholds(context_limit: Any = None) -> dict[str, Any]:
    """All BC knobs for this window. Safe to call every turn."""
    ctx = resolve_context_limit(context_limit)
    return {
        "context_limit": ctx,
        "raw_zone_tokens": min(50_000, int(ctx * 0.25)),
        "growth_floor": max(10_000, int(ctx * 0.22)),
        "ccr_min_tokens": max(500, int(ctx * 0.02)),
        "nudge_threshold": NUDGE_THRESHOLD_FRACTION,
        "nudge_tokens": int(ctx * NUDGE_THRESHOLD_FRACTION),
        "hard_window_tokens": int(ctx * HARD_WINDOW_FRACTION),
        "tier2_enabled": ctx >= TIER2_MIN_CONTEXT,
        "tier3_enabled": ctx >= TIER3_MIN_CONTEXT,
    }


def estimate_tokens(text: Any) -> int:
    """Rough token estimate (~4 chars/token). Fail-open to 0."""
    try:
        if text is None:
            return 0
        if not isinstance(text, str):
            text = str(text)
        return max(0, (len(text) + 3) // 4)
    except Exception:
        return 0


def message_text(msg: Any) -> str:
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
            elif isinstance(part, dict) and isinstance(part.get("text"), str):
                parts.append(part["text"])
        return "\n".join(parts)
    return ""


def first_user_index(messages: Optional[list] = None) -> int:
    """Index of the first real user message, or -1."""
    try:
        for i, msg in enumerate(messages or []):
            if not isinstance(msg, dict) or msg.get("role") != "user":
                continue
            if msg.get("_synthetic") or msg.get("_compression") or msg.get("_thinking_prefill"):
                continue
            if msg.get("_hermes_internal"):
                continue
            return i
    except Exception:
        logger.debug("billion_context: first_user_index failed", exc_info=True)
    return -1


def should_skip_for_growth(
    *,
    tokens: int,
    last_compression_token_count: int,
    threshold_tokens: int,
    context_limit: Any = None,
) -> bool:
    """True when auto-compress should wait for more growth (BC growth gate).

    Inactive until a compression has landed *under* the threshold. Never skips
    when the prompt is already in the hard window (90% of context_limit).
    """
    try:
        if last_compression_token_count <= 0:
            return False
        if last_compression_token_count >= threshold_tokens:
            return False
        if tokens < threshold_tokens:
            return False
        knobs = scaled_thresholds(context_limit)
        if tokens >= knobs["hard_window_tokens"]:
            return False
        growth = tokens - last_compression_token_count
        return growth < knobs["growth_floor"]
    except Exception:
        logger.debug("billion_context: growth gate failed", exc_info=True)
        return False


# --- Crush (deterministic first tier) ---------------------------------------

def _fold_records(rows: list) -> Any:
    if not rows or not all(isinstance(r, dict) for r in rows):
        return rows
    keys = [set(r.keys()) for r in rows]
    common = set.intersection(*keys) if keys else set()
    if not common:
        return rows
    constants: dict[str, Any] = {}
    for key in sorted(common):
        values = [r[key] for r in rows]
        if all(v == values[0] for v in values):
            constants[key] = values[0]
    collapsed: list[dict[str, Any]] = []
    for row in rows:
        slim = {k: v for k, v in row.items() if k not in constants}
        if collapsed and slim == {k: v for k, v in collapsed[-1].items() if k != "_run"}:
            collapsed[-1]["_run"] = int(collapsed[-1].get("_run", 1)) + 1
        else:
            collapsed.append(dict(slim))
    if not constants and collapsed == rows:
        return rows
    return {"_constants": constants, "_rows": collapsed, "_n": len(rows)}


def json_fold(text: str) -> Optional[str]:
    """Lossless JSON constant-hoist + identical-run collapse. None if not worth it."""
    try:
        data = json.loads(text)
    except Exception:
        return None
    try:
        if isinstance(data, list):
            folded: Any = _fold_records(data)
        elif isinstance(data, dict):
            folded = {
                k: (_fold_records(v) if isinstance(v, list) else v) for k, v in data.items()
            }
        else:
            return None
        out = json.dumps(folded, ensure_ascii=False, separators=(",", ":"))
        if len(out) >= int(len(text) * (1.0 - CRUSH_MIN_REDUCTION)):
            return None
        return out
    except Exception:
        return None


def log_select(text: str) -> Optional[str]:
    """Keep every ERROR/FAIL line; dedupe warnings; keep head+tail of the rest."""
    try:
        if text.count("\n") < 8:
            return None
        lines = text.splitlines()
        if len(lines) < 12:
            return None
        errors: list[str] = []
        warns: list[str] = []
        warn_seen: set[str] = set()
        other: list[str] = []
        for line in lines:
            if _ERROR_LINE_RE.search(line):
                errors.append(line)
            elif _WARN_LINE_RE.search(line):
                key = line.strip()
                if key not in warn_seen:
                    warn_seen.add(key)
                    warns.append(line)
            else:
                other.append(line)
        kept_other = other[:5] + (["…"] if len(other) > 25 else []) + other[-20:]
        parts: list[str] = []
        if errors:
            parts.append("## errors (verbatim)")
            parts.extend(errors)
        if warns:
            parts.append("## warnings (deduped)")
            parts.extend(warns)
        parts.append("## other (head+tail)")
        parts.extend(kept_other)
        out = "\n".join(parts)
        if len(out) >= int(len(text) * (1.0 - CRUSH_MIN_REDUCTION)):
            return None
        return out
    except Exception:
        return None


def _already_crushed(text: str) -> bool:
    """True for CCR placeholders and outputs already json-folded or log-selected."""
    if not isinstance(text, str) or not text:
        return False
    if _PLACEHOLDER_MARK in text[:80]:
        return True
    head = text.lstrip()[:40]
    if head.startswith("## errors (verbatim)") or head.startswith("## warnings (deduped)"):
        return True
    snippet = text[:400]
    return '"_constants"' in snippet[:120] and '"_rows"' in snippet


def crush_text(text: str) -> str:
    """Apply json-fold then log-select. Fail-open: return original on any miss."""
    if not isinstance(text, str) or len(text) < 200 or _already_crushed(text):
        return text
    folded = json_fold(text)
    if folded is not None:
        return folded
    selected = log_select(text)
    if selected is not None:
        return selected
    return text


def _set_message_text(msg: dict[str, Any], new_text: str) -> None:
    content = msg.get("content")
    if isinstance(content, str):
        msg["content"] = new_text
        return
    if isinstance(content, list) and content:
        first = content[0]
        if isinstance(first, dict) and "text" in first:
            new_part = dict(first)
            new_part["text"] = new_text
            msg["content"] = [new_part] + list(content[1:])
            return
        if isinstance(first, str):
            msg["content"] = [new_text] + list(content[1:])
            return
    msg["content"] = new_text


def crush_message_list(
    messages: list[dict[str, Any]],
    *,
    protect_head: int = 0,
    raw_zone_tokens: int = 0,
    crush_end: Optional[int] = None,
) -> list[dict[str, Any]]:
    """Crush tool outputs outside the protected head and raw working zone.

    Copies the list (and any mutated message dicts). Original objects are left
    unchanged so a compression abort can return the canonical transcript.
    ``crush_end`` (exclusive), when set, is the start of the already-planned
    compressor tail so crush does not spare a band the summariser will drop.
    """
    try:
        n = len(messages)
        if n == 0:
            return messages
        tail_start = n
        if crush_end is not None:
            tail_start = max(protect_head, min(n, int(crush_end)))
        elif raw_zone_tokens > 0:
            acc = 0
            tail_start = n
            for i in range(n - 1, protect_head - 1, -1):
                acc += estimate_tokens(message_text(messages[i]))
                tail_start = i
                if acc >= raw_zone_tokens:
                    break
        pin = first_user_index(messages)
        out = list(messages)
        for i, msg in enumerate(messages):
            if i < protect_head or i >= tail_start or i == pin:
                continue
            if not isinstance(msg, dict):
                continue
            if msg.get("_bc_crushed"):
                continue
            role = msg.get("role")
            if role not in ("tool", "function"):
                continue
            original = message_text(msg)
            crushed = crush_text(original)
            if crushed is original or crushed == original:
                continue
            clone = dict(msg)
            _set_message_text(clone, crushed)
            clone["_bc_crushed"] = True
            out[i] = clone
        return out
    except Exception:
        logger.debug("billion_context: crush_message_list failed", exc_info=True)
        return messages


# --- Covered-range note (compress() → post_compaction; in-process only) ------

_last_covered: dict[str, tuple[int, int]] = {}


def note_compress_covered(session_id: str, start: int, end: int) -> None:
    """Remember the last planned middle-window indices for block bookkeeping."""
    try:
        key = session_id or "nosession"
        _last_covered[key] = (int(start), int(end))
    except Exception:
        logger.debug("billion_context: note_compress_covered failed", exc_info=True)


def take_last_covered(session_id: str) -> tuple[int, int]:
    """Return last noted (start, end), default (0, 0). Does not clear."""
    try:
        return _last_covered.get(session_id or "nosession", (0, 0))
    except Exception:
        return (0, 0)


# --- CCR --------------------------------------------------------------------

def is_ccr_placeholder(text: str) -> bool:
    return isinstance(text, str) and _PLACEHOLDER_MARK in text[:80]


def ccr_placeholder(
    store_id: str,
    tokens: int,
    tool_name: str,
    relevance: Optional[float] = None,
) -> str:
    name = (tool_name or "tool").replace("`", "").replace("\n", " ").strip()[:64] or "tool"
    rel = ""
    if isinstance(relevance, (int, float)):
        rel = f" · relevance:{max(0.0, min(1.0, float(relevance))):.2f}"
    return f"[stored tool output · {tokens} tok{rel} · {name} · id={store_id}] → retrieve with acp_retrieve"


def maybe_ccr_store(
    result: str,
    *,
    tool_name: str,
    session_id: str,
    context_limit: Any = None,
    store_dir: Optional[Path] = None,
    query: str = "",
    relevance: Optional[float] = None,
) -> str:
    """Replace oversized tool results with a retrieve placeholder. Fail-open."""
    try:
        if not isinstance(result, str) or is_ccr_placeholder(result):
            return result
        if tool_name in ("acp_retrieve", "acp_status"):
            return result
        knobs = scaled_thresholds(context_limit)
        tokens = estimate_tokens(result)
        if tokens < knobs["ccr_min_tokens"]:
            return result
        if _ERROR_LINE_RE.search(result[:4000]) and tokens < knobs["ccr_min_tokens"] * 4:
            return result
        rel = relevance
        if rel is None and query:
            try:
                from agent.adaptive_retrieval import keyword_overlap_score
                rel = keyword_overlap_score(query, result)
            except Exception:
                rel = None
        store_id = _write_ccr(
            result,
            session_id=session_id,
            tool_name=tool_name,
            store_dir=store_dir,
            relevance=rel,
        )
        if not store_id:
            return result
        return ccr_placeholder(store_id, tokens, tool_name, relevance=rel)
    except Exception:
        logger.debug("billion_context: CCR store failed", exc_info=True)
        return result


def _ccr_root(store_dir: Optional[Path] = None) -> Path:
    if store_dir is not None:
        return store_dir
    import os
    base = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
    profile = os.environ.get("HERMES_PROFILE", "")
    if profile and "profiles" not in str(base):
        base = base / "profiles" / profile
    return base / "cache" / "billion-context" / "ccr"


def _write_ccr(
    text: str,
    *,
    session_id: str,
    tool_name: str,
    store_dir: Optional[Path] = None,
    relevance: Optional[float] = None,
) -> str:
    sid = (session_id or "nosession").replace("/", "_")[:80]
    store_id = "m" + uuid.uuid4().hex[:8]
    root = _ccr_root(store_dir) / sid
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{store_id}.json"
    payload = {
        "id": store_id,
        "tool": tool_name,
        "text": text,
        "ts": time.time(),
        "relevance": relevance,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    with _CCR_LOCK:
        _ccr_store.setdefault(sid, {})[store_id] = text
    return store_id


def ccr_retrieve(store_id: str, *, session_id: str = "", store_dir: Optional[Path] = None) -> str:
    """Return stored tool output or an error string. Never raises."""
    try:
        clean = (store_id or "").strip().lstrip("#")
        if not re.fullmatch(r"m?[0-9a-fA-F]{6,16}", clean):
            return json.dumps({"error": "invalid id"})
        if not clean.startswith("m"):
            clean = "m" + clean
        sid = (session_id or "").replace("/", "_")[:80]
        with _CCR_LOCK:
            cached = (_ccr_store.get(sid) or {}).get(clean)
            if not cached and sid:
                for bucket in _ccr_store.values():
                    if clean in bucket:
                        cached = bucket[clean]
                        break
        if isinstance(cached, str) and cached:
            return cached
        root = _ccr_root(store_dir)
        candidates: list[Path] = []
        if sid:
            candidates.append(root / sid / f"{clean}.json")
        if root.exists():
            candidates.extend(root.glob(f"*/{clean}.json"))
        for path in candidates:
            if path.is_file():
                data = json.loads(path.read_text(encoding="utf-8"))
                return data.get("text") or json.dumps(data)
        return json.dumps({"error": "not found", "id": clean})
    except Exception as exc:
        return json.dumps({"error": str(exc)})


def clear_ccr_session(session_id: str = "", store_dir: Optional[Path] = None) -> None:
    """Drop in-memory CCR cache and on-disk files for *session_id*. Fail-open."""
    try:
        sid = (session_id or "nosession").replace("/", "_")[:80]
        with _CCR_LOCK:
            _ccr_store.pop(sid, None)
        root = _ccr_root(store_dir) / sid
        if root.is_dir():
            for path in root.glob("*.json"):
                try:
                    path.unlink()
                except Exception:
                    pass
            try:
                root.rmdir()
            except Exception:
                pass
    except Exception:
        logger.debug("billion_context: CCR session cleanup failed", exc_info=True)


# --- Turn classification / output steering ----------------------------------

VERBOSITY = {
    "new_user_ask": ("L2", "Answer at normal detail. Do not recap prior turns."),
    "mechanical_continuation": ("L1", "Continue the tool loop concisely. No preamble."),
    "error_continuation": ("L3", "Focus on the error: cause, evidence, next fix. No tour."),
    "unknown": ("L2", "Stay on the current step."),
}


def classify_turn(messages: Optional[list] = None) -> str:
    """new_user_ask | mechanical_continuation | error_continuation | unknown."""
    try:
        msgs = [m for m in (messages or []) if isinstance(m, dict)]
        if not msgs:
            return "unknown"
        last = msgs[-1]
        role = last.get("role")
        if role in ("tool", "function"):
            body = message_text(last)
            if _ERROR_LINE_RE.search(body[:2000]):
                return "error_continuation"
            return "mechanical_continuation"
        if role == "assistant" and last.get("tool_calls"):
            return "mechanical_continuation"
        if role == "user":
            return "new_user_ask"
        # Walk back past assistant text to the trigger.
        for msg in reversed(msgs[-8:]):
            r = msg.get("role")
            if r == "user":
                return "new_user_ask"
            if r in ("tool", "function"):
                if _ERROR_LINE_RE.search(message_text(msg)[:2000]):
                    return "error_continuation"
                return "mechanical_continuation"
        return "unknown"
    except Exception:
        return "unknown"


def verbosity_directive(kind: str) -> str:
    level, text = VERBOSITY.get(kind, VERBOSITY["unknown"])
    # Byte-stable: fixed wording so prefix cache still hits when the class is unchanged.
    return f"[output-steering {level} · {kind}] {text}"


# --- Blocks / nudge ---------------------------------------------------------

def new_block(
    *,
    summary: str,
    covered_start: int,
    covered_end: int,
    tier: int = 1,
    tokens_in: int = 0,
    tokens_out: int = 0,
) -> dict[str, Any]:
    return {
        "blockId": "b" + uuid.uuid4().hex[:10],
        "tier": int(tier),
        "summary": summary[:4000],
        "covered": [int(covered_start), int(covered_end)],
        "createdAt": time.time(),
        "survivedCount": 0,
        "generation": "young",
        "tokensIn": tokens_in,
        "tokensOut": tokens_out,
    }


def promote_blocks(blocks: list[dict[str, Any]], *, context_limit: Any = None) -> list[dict[str, Any]]:
    """Age young tier-1 blocks; batch-merge old ones into tier-2 when enabled."""
    try:
        knobs = scaled_thresholds(context_limit)
        out: list[dict[str, Any]] = []
        old_t1: list[dict[str, Any]] = []
        for block in blocks:
            b = dict(block)
            if b.get("tier") == 1:
                b["survivedCount"] = int(b.get("survivedCount") or 0) + 1
                if b["survivedCount"] >= TIER1_SURVIVAL_ROUNDS:
                    b["generation"] = "old"
            if b.get("tier") == 1 and b.get("generation") == "old" and knobs["tier2_enabled"]:
                old_t1.append(b)
            else:
                out.append(b)
        if old_t1 and knobs["tier2_enabled"]:
            covered = []
            for b in old_t1:
                c = b.get("covered") or [0, 0]
                covered.extend(c[:2])
            merged = new_block(
                summary=" | ".join(str(b.get("summary") or "")[:240] for b in old_t1)[:2000],
                covered_start=min(covered) if covered else 0,
                covered_end=max(covered) if covered else 0,
                tier=2,
                tokens_in=sum(int(b.get("tokensOut") or 0) for b in old_t1),
            )
            if knobs["tier3_enabled"]:
                # Keep as tier-2; a later pass with many tier-2 blocks can fold to tier-3.
                t2 = [b for b in out if b.get("tier") == 2]
                if len(t2) >= TIER1_SURVIVAL_ROUNDS:
                    summaries = [str(b.get("summary") or "")[:200] for b in t2]
                    t3 = new_block(
                        summary=" || ".join(summaries)[:2000],
                        covered_start=0,
                        covered_end=0,
                        tier=3,
                    )
                    out = [b for b in out if b.get("tier") != 2] + [t3]
            out.append(merged)
        return out
    except Exception:
        logger.debug("billion_context: promote_blocks failed", exc_info=True)
        return blocks


def compressible_ranges(messages: Optional[list] = None, *, context_limit: Any = None) -> list[dict[str, Any]]:
    """Recommendation list for the compression nudge (tool results outside raw zone)."""
    knobs = scaled_thresholds(context_limit)
    msgs = messages or []
    n = len(msgs)
    pin = first_user_index(msgs)
    acc = 0
    tail_start = n
    for i in range(n - 1, -1, -1):
        acc += estimate_tokens(message_text(msgs[i]))
        tail_start = i
        if acc >= knobs["raw_zone_tokens"]:
            break
    ranges: list[dict[str, Any]] = []
    for i, msg in enumerate(msgs):
        if i == pin or i >= tail_start:
            continue
        if not isinstance(msg, dict) or msg.get("role") not in ("tool", "function"):
            continue
        tok = estimate_tokens(message_text(msg))
        if tok < 80:
            continue
        ranges.append({
            "index": i,
            "tokens": tok,
            "tool": str(msg.get("name") or msg.get("tool_name") or "tool")[:40],
        })
    ranges.sort(key=lambda r: -r["tokens"])
    return ranges[:12]


def nudge_text(ranges: list[dict[str, Any]], *, tokens: int, context_limit: Any = None) -> str:
    knobs = scaled_thresholds(context_limit)
    if not ranges:
        return ""
    lines = [
        f"[bc-nudge] growth approaching · {tokens}/{knobs['context_limit']} tok · "
        f"floor={knobs['growth_floor']} raw_zone={knobs['raw_zone_tokens']}",
        "Compressible tool results (oldest working area; raw zone kept):",
    ]
    for item in ranges:
        lines.append(f"  - msg[{item['index']}] {item['tokens']} tok · {item['tool']}")
    lines.append("Compress only content no longer needed by the current step.")
    return "\n".join(lines)
