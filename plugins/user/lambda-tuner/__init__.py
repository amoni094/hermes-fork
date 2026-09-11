"""lambda-tuner — classify session type, tune compression live.

# See FORK_README.md § lambda-tuner
"""
from __future__ import annotations

import json
import logging
import math
import os
import re
import time
import tempfile
from collections import Counter, OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .complexity import DEFAULT_SCORER, TaskComplexityScorer

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Hint file — JSON schema, atomic write, HERMES_HOME-aware path
# ---------------------------------------------------------------------------
def _hint_path() -> Path:
    """Resolve hint file path respecting HERMES_HOME, consistent with wrapper."""
    base = os.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))
    return Path(base) / "cache" / "last-session-type.json"


_HINT_TTL_SECONDS = 6 * 3600  # 6h — stale hints fall back to mixed in wrapper

# Matches hermes-session wrapper table (rr_scorer_lambda). Hint schema includes
# lambda for the wrapper; live compressor uses COMPRESSION_PROFILES instead.
_TYPE_TO_LAMBDA = {
    "research": "0.55",  # why: 0.55 not 0.7 — Phase-1 exec-state already holds web_extract
    "code": "0.2",
    "mixed": "0.4",
    "entropy-adaptive": "0.4",
}

_last_hint_key: tuple[str, str] | None = None  # (type, lambda_str) dirty-check
_pending_intent: str | None = None
_intent_applied: OrderedDict[str, bool] = OrderedDict()


def _read_hint() -> dict[str, Any] | None:
    """Load the hint JSON. Fail-open: missing/malformed → None."""
    try:
        hint_path = _hint_path()
        if not hint_path.is_file():
            return None
        with open(hint_path, encoding="utf-8") as f:
            hint = json.load(f)
        if not isinstance(hint, dict):
            return None
        return hint
    except Exception:
        return None


def _apply_intent_from_hint(agent: Any, hint: dict[str, Any] | None) -> None:
    """Apply hint['type'] as compression profile and hint['intent'] to compressor (fail-open)."""
    if not hint or agent is None:
        return
    compressor = getattr(agent, "context_compressor", None)
    # Apply session-type profile from hint (covers entropy-adaptive + all other types).
    try:
        hint_type = hint.get("type")
        if isinstance(hint_type, str) and hint_type.strip() and compressor is not None:
            if hasattr(compressor, "set_compression_profile"):
                compressor.set_compression_profile(hint_type.strip(), _source="lambda-tuner-hint")
    except Exception as exc:
        logger.debug("lambda-tuner: applying profile from hint failed (fail-open): %s", exc)
    # Apply intent.
    try:
        intent = hint.get("intent")
        if not isinstance(intent, str) or not intent.strip():
            return
        if compressor is None:
            return
        compressor.current_intent = intent.strip()[:500]  # why: cap matches PluginContext.set_intent bound
        global _pending_intent
        _pending_intent = intent.strip()[:500]
    except Exception as exc:
        logger.debug("lambda-tuner: applying intent from hint failed (fail-open): %s", exc)


def _write_hint(session_type: str, confidence: float, scores: dict[str, float]) -> None:
    """Atomically write the JSON hint file. Skip if type+lambda unchanged."""
    global _last_hint_key
    lam_str = _TYPE_TO_LAMBDA.get(session_type, _TYPE_TO_LAMBDA["mixed"])
    key = (session_type, lam_str)
    if _last_hint_key == key:
        return
    hint_path = _hint_path()
    hint_path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "type": session_type,
        "profile": session_type,  # maps directly to COMPRESSION_PROFILES key
        "lambda": lam_str,
        "confidence": round(confidence, 3),
        "scores": {k: round(v, 3) for k, v in scores.items()},
        "ts": time.time(),
        "expires_at": time.time() + _HINT_TTL_SECONDS,
        "source": "lambda-tuner-plugin",
    }
    # Preserve wrapper-provided intent across classifier rewrites.
    intent = _pending_intent
    if not (isinstance(intent, str) and intent.strip()):
        try:
            prev = (_read_hint() or {}).get("intent")
            if isinstance(prev, str) and prev.strip():
                intent = prev.strip()
        except Exception:
            intent = None
    if isinstance(intent, str) and intent.strip():
        payload["intent"] = intent.strip()
    fd, tmp = tempfile.mkstemp(dir=hint_path.parent, prefix=".hint-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(payload, f)
        os.replace(tmp, hint_path)
        _last_hint_key = key
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------------------
# Lexicons — phrase-anchored, collocate-aware
# ---------------------------------------------------------------------------

# Research signals: domain-specific, unlikely to collide with coding/chat.
_RESEARCH_RE = re.compile(
    r"\b("
    r"arxiv|pre-?print|pre\s*print"
    r"|papers?(?:\s+on|\s+about)?"
    r"|research(?:\s+paper|\s+on|\s+about)?"
    r"|literature\s+(?:review|survey|search)"
    r"|systematic\s+review"
    r"|citation|bibliography"
    r"|(?:paper|article)\s+abstract|read\s+(?:the\s+)?abstract"
    r"|sweep(?:\s+papers?|\s+arxiv)?"
    r"|web\s+scrape|web\s+extract"
    r"|find\s+papers?|search\s+papers?"
    r"|rss\s+feed|news\s+feed|news\s+monitor"
    r"|survey\s+(?:the\s+)?(?:literature|papers?|field|domain)"
    r"|summarize\s+(?:this\s+)?(?:paper|article|post|page)"
    r"|doi\s*:|semantic\s+scholar|pubmed|google\s+scholar"
    r")",
    re.IGNORECASE,
)

# Code signals: specific to software development.
_CODE_RE = re.compile(
    r"\b("
    r"fix\s+(?:the\s+)?(?:bug|error|test|failing|broken|crash)"
    r"|debug(?:ging)?"
    r"|traceback|stack\s*trace|segfault|assertion\s+error"
    r"|refactor(?:ing)?"
    r"|implement(?:ing|ation)?"
    r"|pull\s+request|open\s+a?\s*pr\b"
    r"|git\s+(?:commit|push|merge|branch|diff|log|rebase|stash)"
    r"|failing\s+test|broken\s+test|test\s+fail"
    r"|deploy(?:ment|ing)?"
    r"|write\s+(?:a?\s*)?\w+\.(?:py|ts|js|go|rs|sh|yaml|json)"
    r"|edit\s+\w+\.(?:py|ts|js|go|rs|sh|yaml|json)"
    r"|patch\s+(?:the\s+)?\w+"
    r"|compile|build\s+(?:error|fail|the\s+project)"
    r"|linter|mypy|pyright|eslint"
    r"|unit\s+test|integration\s+test|pytest|jest|cargo\s+test"
    r"|(?:add|create|write)\s+(?:an?\s+)?(?:function|class|method|module|plugin|skill|endpoint|route|handler)"
    r"|write\s+(?:an?\s+)?(?:new\s+)?(?:function|class|method|test|script|parser|helper)"
    r")",
    re.IGNORECASE,
)

# Greeting/ack patterns — do NOT classify on these; wait for more signal.
_GREETING_RE = re.compile(
    r"^[\s!.,?]*("
    r"hey|hi|hello|morning|good\s+morning|good\s+(?:afternoon|evening)"
    r"|what(?:'s|\s+is)\s+up|sup|yo|howdy|hola"
    r"|ok(ay)?|sure|sounds?\s+good|great|thanks|thank\s+you|cool"
    r"|continue|go\s+ahead|proceed|let['']\s*(?:go|start|do)"
    r")[\s!.,?]*$",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Classifier
# ---------------------------------------------------------------------------

_SCORE_MARGIN = 1.5
_MIN_SIGNAL   = 1  # why: 1 not 2 — _MIN_SIGNAL=2 is too strict for short messages


def _weighted_score(text: str) -> dict[str, float]:
    research_hits = float(len(_RESEARCH_RE.findall(text)))
    code_hits     = float(len(_CODE_RE.findall(text)))
    return {"research": research_hits, "code": code_hits}


def _classify(messages: list[str]) -> tuple[str, float, dict[str, float]]:
    """Classify accumulated user messages → (session_type, confidence, scores)."""
    real_messages = [m for m in messages if not _GREETING_RE.match(m.strip())]
    if not real_messages:
        return "mixed", 0.0, {"research": 0.0, "code": 0.0}

    combined = " ".join(real_messages)
    scores = _weighted_score(combined)
    r = scores["research"]
    c = scores["code"]
    total = r + c

    if total < _MIN_SIGNAL:
        return "mixed", 0.0, scores

    if r > c * _SCORE_MARGIN and r >= _MIN_SIGNAL:
        confidence = min(1.0, (r - c) / max(r, 1))
        return "research", confidence, scores
    if c > r * _SCORE_MARGIN and c >= _MIN_SIGNAL:
        confidence = min(1.0, (c - r) / max(c, 1))
        return "code", confidence, scores

    confidence = 0.5 - abs(r - c) / max(total, 1)
    return "mixed", max(0.0, confidence), scores


# ---------------------------------------------------------------------------
# Post-lock entropy divergence → one-shot reclassification
# ---------------------------------------------------------------------------
# why: lock-at-turn-3 can stick a long session in the wrong profile. After 15
# classified turns, if recent-5 Shannon entropy sits >0.4 outside the locked
# type's expected R(D) band, allow one high-confidence flip (conf > 0.85).
_RECLASSIFY_MIN_TURNS = 15
_RECLASSIFY_ENTROPY_DELTA = 0.4
_RECLASSIFY_MIN_CONFIDENCE = 0.85
_RECLASSIFY_MAX = 1
_RECENT_ENTROPY_WINDOW = 5

# Bands match ContextCompressor._entropy_adaptive_threshold_percent:
# H > 4.0 → research (0.45); H < 2.5 → code (0.55); else mixed.
_EXPECTED_ENTROPY_RANGE: dict[str, tuple[float | None, float | None]] = {
    "research": (4.0, None),
    "code": (0.0, 2.5),
    "mixed": (2.5, 4.0),
}


def _shannon_unigram(text: str) -> float:
    """Whitespace-token Shannon entropy in bits. Empty → 0.0. Fail-open."""
    try:
        tokens = str(text).split()
        n = len(tokens)
        if n <= 0:
            return 0.0
        counts = Counter(tokens)
        entropy = 0.0
        for count in counts.values():
            if count <= 0:
                continue
            p = count / n
            entropy -= p * math.log2(p)
        return float(entropy)
    except Exception:
        return 0.0


def _entropy_range_divergence(h: float, session_type: str) -> float:
    """Distance of *h* outside the expected entropy range for *session_type*."""
    bounds = _EXPECTED_ENTROPY_RANGE.get(session_type)
    if bounds is None:
        return 0.0
    lo, hi = bounds
    if lo is not None and h < lo:
        return float(lo - h)
    if hi is not None and h > hi:
        return float(h - hi)
    return 0.0


def _maybe_reclassify_on_entropy_decay(
    ctx: Any,
    agent: Any,
    session_id: str,
    bucket: list[str],
    rec: dict[str, Any],
    locked: str,
) -> None:
    """Track running entropy; maybe one high-confidence type flip. Fail-open."""
    if not isinstance(rec, dict):
        return
    try:
        recent = bucket[-_RECENT_ENTROPY_WINDOW:]
        h = _shannon_unigram(" ".join(recent))
        divergence = _entropy_range_divergence(h, locked)
        rec["_recent_entropy"] = h
        rec["_entropy_divergence"] = divergence

        try:
            reclass_count = int(rec.get("_reclassification_count", 0) or 0)
        except (TypeError, ValueError):
            reclass_count = 0
        if reclass_count >= _RECLASSIFY_MAX:
            return

        try:
            lock_turn = int(rec.get("lock_turn", 0) or 0)
        except (TypeError, ValueError):
            lock_turn = 0
        turns_classified = len(bucket) - lock_turn
        if turns_classified <= _RECLASSIFY_MIN_TURNS:
            return
        if divergence <= _RECLASSIFY_ENTROPY_DELTA:
            return

        session_type, confidence, scores = _classify(bucket)
        if session_type == locked:
            return
        if confidence <= _RECLASSIFY_MIN_CONFIDENCE:
            return

        rec["type"] = session_type
        rec["confidence"] = float(confidence)
        rec["ts"] = time.time()
        rec["scores"] = scores
        rec["_reclassification_count"] = reclass_count + 1
        rec["reclassified"] = True
        try:
            rec["complexity"] = float(DEFAULT_SCORER.score(" ".join(bucket)))
        except Exception:
            pass
        _fired[session_id] = rec
        _fired.move_to_end(session_id)
        _apply_profile(ctx, agent, session_type, session_id, confidence, len(bucket))
        try:
            _write_hint(session_type, confidence, scores)
        except Exception as exc:
            logger.debug("lambda-tuner: reclassify hint write failed (fail-open): %s", exc)
        logger.debug(
            "lambda-tuner: reclassified sid=%s %s -> %s conf=%.2f entropy=%.3f div=%.3f",
            session_id, locked, session_type, confidence, h, divergence,
        )
        try:
            ctx.emit_episode(
                f"Session {session_id} reclassified {locked} -> {session_type} "
                f"confidence={confidence} entropy={h:.3f}",
                tags=["classification", "lambda-tuner", "reclassify"],
            )
        except Exception:
            pass
    except Exception as exc:
        logger.debug("lambda-tuner: entropy-decay reclassify failed (fail-open): %s", exc)


def _write_warm_start_cache(session_id: str, rec: dict[str, Any], turn_count: int) -> None:
    """Atomic last-session-type.json for the next session. Fail-open.

    Includes wrapper-compat fields (type/lambda/expires_at) plus the warm-start
    schema (session_id, session_type, complexity_score, profile_applied,
    turn_count, timestamp ISO8601, reclassified).
    """
    try:
        session_type = rec.get("type") if isinstance(rec, dict) else None
        if not isinstance(session_type, str) or not session_type.strip():
            session_type = "mixed"
        try:
            complexity_score = float((rec or {}).get("complexity", 0.0) or 0.0)
        except (TypeError, ValueError):
            complexity_score = 0.0
        try:
            confidence = float((rec or {}).get("confidence", 0.0) or 0.0)
        except (TypeError, ValueError):
            confidence = 0.0
        try:
            reclassified = bool((rec or {}).get("reclassified")) or (
                int((rec or {}).get("_reclassification_count", 0) or 0) >= 1
            )
        except (TypeError, ValueError):
            reclassified = False
        scores = (rec or {}).get("scores") if isinstance(rec, dict) else None
        if not isinstance(scores, dict):
            scores = {"research": 0.0, "code": 0.0}
        lam_str = _TYPE_TO_LAMBDA.get(session_type, _TYPE_TO_LAMBDA["mixed"])
        now = time.time()
        payload: dict[str, Any] = {
            "type": session_type,
            "profile": session_type,
            "lambda": lam_str,
            "confidence": round(confidence, 3),
            "scores": {str(k): round(float(v), 3) for k, v in scores.items()},
            "ts": now,
            "expires_at": now + _HINT_TTL_SECONDS,
            "source": "lambda-tuner-plugin",
            "session_id": session_id,
            "session_type": session_type,
            "complexity_score": round(complexity_score, 4),
            "profile_applied": session_type,
            "turn_count": int(turn_count),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "reclassified": bool(reclassified),
        }
        intent = _pending_intent
        if not (isinstance(intent, str) and intent.strip()):
            try:
                prev = (_read_hint() or {}).get("intent")
                if isinstance(prev, str) and prev.strip():
                    intent = prev.strip()
            except Exception:
                intent = None
        if isinstance(intent, str) and intent.strip():
            payload["intent"] = intent.strip()
        hint_path = _hint_path()
        hint_path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=hint_path.parent, prefix=".hint-", suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(payload, f)
            os.replace(tmp, hint_path)
        except Exception:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise
    except Exception as exc:
        logger.warning("lambda-tuner: warm-start cache write failed (fail-open): %s", exc)


# ---------------------------------------------------------------------------
# Plugin state — bounded LRU so a long-running gateway cannot grow forever
# ---------------------------------------------------------------------------

_MAX_SESSIONS = 64
_MAX_MESSAGES_PER_SESSION = 32
# session_id -> {"type": str, "confidence": float, "ts": float}
_fired: OrderedDict[str, dict[str, Any]] = OrderedDict()
_session_messages: OrderedDict[str, list[str]] = OrderedDict()


def _fired_type(session_id: str) -> str | None:
    rec = _fired.get(session_id)
    if rec is None:
        return None
    if isinstance(rec, dict):
        t = rec.get("type")
        return t if isinstance(t, str) else None
    if isinstance(rec, str):
        return rec
    return None


def _touch_session(session_id: str) -> None:
    """LRU-touch and evict oldest sessions (and their _fired entries) over cap."""
    if session_id in _session_messages:
        _session_messages.move_to_end(session_id)
    if session_id in _fired:
        _fired.move_to_end(session_id)
    if session_id in _intent_applied:
        _intent_applied.move_to_end(session_id)
    while len(_session_messages) > _MAX_SESSIONS:
        evicted, _ = _session_messages.popitem(last=False)
        _fired.pop(evicted, None)
        _intent_applied.pop(evicted, None)
    while len(_fired) > _MAX_SESSIONS:
        evicted, _ = _fired.popitem(last=False)
        _intent_applied.pop(evicted, None)
    while len(_intent_applied) > _MAX_SESSIONS:
        _intent_applied.popitem(last=False)


def _apply_profile(ctx: Any, agent: Any, session_type: str, session_id: str, confidence: float, n_turns: int) -> None:
    # Prefer the per-call agent kwarg (correct session) over ctx.compressor which
    # goes through the process-global PluginManager._agent (last-writer-wins, can be
    # a different session in gateway/subagent scenarios). Fall back to ctx.compressor
    # only when the hook was not passed a live agent reference.
    compressor = None
    if agent is not None:
        compressor = getattr(agent, "context_compressor", None)
    if compressor is None:
        try:
            compressor = ctx.compressor
        except AttributeError:
            pass
    if compressor is not None and hasattr(compressor, "set_compression_profile"):
        try:
            # _source is accepted via **kwargs on set_compression_profile and only used for logs.
            compressor.set_compression_profile(session_type, _source="lambda-tuner")
            logger.debug(
                "lambda-tuner: live profile=%s sid=%s conf=%.2f turn=%d",
                session_type, session_id, confidence, n_turns,
            )
        except Exception as exc:
            logger.debug("lambda-tuner: set_compression_profile failed: %s", exc)


# ---------------------------------------------------------------------------
# Plugin registration
# ---------------------------------------------------------------------------

def _maybe_apply_hint_intent(session_id: str, agent: Any) -> None:
    """Read hint intent once per session and set compressor.current_intent.

    Skips (does not mark applied) when *agent* is None so on_session_start
    without an agent kwarg can retry from pre_llm_call.
    """
    if session_id in _intent_applied:
        return
    if agent is None:
        return
    try:
        hint = _read_hint()
        _apply_intent_from_hint(agent, hint)
    except Exception as exc:
        logger.debug("lambda-tuner: hint intent apply failed (fail-open): %s", exc)
    try:
        _intent_applied[session_id] = True
        _intent_applied.move_to_end(session_id)
        while len(_intent_applied) > _MAX_SESSIONS:
            _intent_applied.popitem(last=False)
    except Exception:
        pass


def register(ctx: Any) -> None:
    def on_session_start(
        *,
        session_id: str = "",
        agent: Any = None,
        **_kwargs: Any,
    ) -> None:
        try:
            # Populate ctx._session_id so compact_tool_result can read it.
            # why: PluginContext._session_id is None until set here; compact_tool_result
            #      needs it to call predicates.session_type(session_id).
            try:
                ctx._session_id = session_id
            except Exception:
                pass
            _maybe_apply_hint_intent(session_id, agent)
            if agent is None:
                # on_session_start may not receive agent; try ctx.compressor.
                try:
                    compressor = ctx.compressor
                except Exception:
                    compressor = None
                if compressor is not None:
                    hint = _read_hint()
                    try:
                        intent = (hint or {}).get("intent")
                        if isinstance(intent, str) and intent.strip():
                            compressor.current_intent = intent.strip()[:500]  # why: cap matches PluginContext.set_intent and wrapper
                            global _pending_intent
                            _pending_intent = intent.strip()
                    except Exception as exc:
                        logger.debug(
                            "lambda-tuner: ctx.compressor intent set failed (fail-open): %s",
                            exc,
                        )
        except Exception as exc:
            logger.debug("lambda-tuner: on_session_start failed (fail-open): %s", exc)

    def on_pre_llm_call(
        *,
        session_id: str = "",
        user_message: Any = None,
        is_first_turn: bool = False,
        agent: Any = None,
        **_kwargs: Any,
    ) -> None:
        try:
            _maybe_apply_hint_intent(session_id, agent)
        except Exception:
            pass

        if not isinstance(user_message, str):
            user_message = str(user_message or "")
        if not user_message.strip():
            return

        bucket = _session_messages.setdefault(session_id, [])
        bucket.append(user_message)
        if len(bucket) > _MAX_MESSAGES_PER_SESSION:
            del bucket[:-_MAX_MESSAGES_PER_SESSION]
        _touch_session(session_id)

        try:
            locked = _fired_type(session_id)
            if locked is not None:
                # Re-apply locked profile in case the compressor was rebuilt
                # (model switch / engine swap) after we first committed.
                rec = _fired.get(session_id) or {}
                conf = 1.0
                if isinstance(rec, dict):
                    try:
                        conf = float(rec.get("confidence", 1.0) or 1.0)
                    except (TypeError, ValueError):
                        conf = 1.0
                _apply_profile(ctx, agent, locked, session_id, conf, len(bucket))
                if isinstance(rec, dict):
                    _maybe_reclassify_on_entropy_decay(
                        ctx, agent, session_id, bucket, rec, locked,
                    )
                return

            session_type, confidence, scores = _classify(bucket)
            commit = session_type != "mixed" or len(bucket) >= 3

            _apply_profile(ctx, agent, session_type, session_id, confidence, len(bucket))
            _write_hint(session_type, confidence, scores)

            if commit:
                accumulated_text = " ".join(bucket)
                complexity = 0.0
                try:
                    complexity = float(DEFAULT_SCORER.score(accumulated_text))
                    DEFAULT_SCORER.update_recent(accumulated_text)
                except Exception as exc:
                    logger.debug("lambda-tuner: complexity score failed (fail-open): %s", exc)
                    complexity = 0.0

                try:
                    if session_id:
                        ctx._session_id = session_id
                    if complexity > 0.75:
                        ctx.set_reasoning_mode("deep")
                    elif complexity < 0.25:
                        ctx.set_reasoning_mode("fast")
                    else:
                        ctx.set_reasoning_mode("default")
                except Exception as exc:
                    logger.debug("lambda-tuner: set_reasoning_mode failed (fail-open): %s", exc)

                compressor = None
                if agent is not None:
                    compressor = getattr(agent, "context_compressor", None)
                if compressor is None:
                    try:
                        compressor = ctx.compressor
                    except Exception:
                        compressor = None

                try:
                    if compressor is not None and hasattr(compressor, "set_compression_profile"):
                        if complexity > 0.7:
                            protect = int(getattr(compressor, "protect_last_n", 20) or 20) + 5
                            compressor.set_compression_profile(
                                {"protect_last_n": min(protect, 40)},
                                _source="lambda-tuner-complexity",
                            )
                        elif complexity < 0.3:
                            prune = int(getattr(compressor, "proactive_prune_tokens", 16000) or 0) - 8000
                            compressor.set_compression_profile(
                                {"proactive_prune_tokens": max(prune, 8000)},
                                _source="lambda-tuner-complexity",
                            )
                except Exception as exc:
                    logger.debug("lambda-tuner: complexity profile adjust failed (fail-open): %s", exc)

                _fired[session_id] = {
                    "type": session_type,
                    "confidence": float(confidence),
                    "ts": time.time(),
                    "complexity": complexity,
                    "scores": scores,
                    "lock_turn": len(bucket),
                    "_reclassification_count": 0,
                    "reclassified": False,
                }
                _fired.move_to_end(session_id)
                logger.debug(
                    "lambda-tuner: committed sid=%s type=%s conf=%.2f scores=%s turn=%d complexity=%.3f",
                    session_id, session_type, confidence, scores, len(bucket), complexity,
                )
                try:
                    ctx.emit_episode(
                        f"Session {session_id} classified as {session_type} confidence={confidence}",
                        tags=["classification", "lambda-tuner"],
                    )
                except Exception as exc:
                    logger.debug("lambda-tuner: emit_episode failed (fail-open): %s", exc)
                try:
                    if compressor is not None:
                        est = getattr(compressor, "_entropy_estimator", None)
                        if est is not None and hasattr(est, "checkpoint"):
                            est.checkpoint("classification_locked", compressor.turn_clock)
                except Exception as exc:
                    logger.debug("lambda-tuner: classification checkpoint failed (fail-open): %s", exc)

        except Exception as exc:
            logger.debug("lambda-tuner: classify failed (fail-open): %s", exc)

    def on_session_end(*, session_id: str = "", **_kwargs: Any) -> None:  # registered as on_session_finalize
        # Clear ctx._session_id so compact_tool_result doesn't use a stale session_id.
        try:
            ctx._session_id = None
        except Exception:
            pass
        """Drop per-session classifier state so long-running gateways cannot leak it."""
        try:
            rec = _fired.get(session_id) or {}
            turn_count = len(_session_messages.get(session_id, []) or [])
            if isinstance(rec, dict):
                _write_warm_start_cache(session_id, rec, turn_count)
                try:
                    complexity = float(rec.get("complexity", 0.0) or 0.0)
                except (TypeError, ValueError):
                    complexity = 0.0
                if complexity > 0.8 and rec.get("type") == "code":
                    try:
                        ctx.suggest_skill_update(
                            "hermes-fork",
                            "High-complexity code session; consider raising code profile protect_last_n",
                            "medium",
                        )
                    except Exception:
                        pass
            try:
                suggestions = ctx.get_skill_suggestions()
                if suggestions:
                    logger.info("lambda-tuner skill suggestions: %s", suggestions)
            except Exception:
                pass
            _session_messages.pop(session_id, None)
            _fired.pop(session_id, None)
            _intent_applied.pop(session_id, None)
        except Exception as exc:
            logger.debug("lambda-tuner: on_session_end cleanup failed (fail-open): %s", exc)

    def on_pre_compress(
        *,
        session_id: str = "",
        context_tokens: int = 0,
        agent: Any = None,
        **_kwargs: Any,
    ) -> None:
        """pre_compress hook: reaffirm compression profile before each compress event.

        If the session type is already locked, reapply the profile (guards against
        update_model() resets). If no type is locked yet and context is large,
        apply entropy-adaptive to let the estimator guide the threshold.
        """
        try:
            fired_entry = _fired.get(session_id)
            if fired_entry is not None:
                # Reaffirm the locked session type profile (idempotent; guards against resets).
                session_type = fired_entry.get("type", "mixed")
                _apply_profile(ctx, agent, session_type, session_id, fired_entry.get("confidence", 0.0), 0)
                # IB prune is only beneficial for code sessions (evicts ack/boilerplate turns).
                # Research sessions must keep unique mid-conversation turns; tool stubs
                # already handled by _prune_old_tool_results.
                # why: importance_biased_prune evicts by lowest score (0.7 = user/assistant) —
                #      deleting unique analytical history is harmful in research but safe in code.
                if session_type == "code":
                    try:
                        compressor = getattr(agent, "context_compressor", None) if agent is not None else None
                        if compressor is not None:
                            compressor.importance_biased_prune_enabled = True
                    except Exception:
                        pass
                elif session_type == "research":
                    # Ensure IB prune is off for research (may have been set by an earlier /new leak).
                    try:
                        compressor = getattr(agent, "context_compressor", None) if agent is not None else None
                        if compressor is not None:
                            compressor.importance_biased_prune_enabled = False
                    except Exception:
                        pass
            elif context_tokens > 60_000:
                # VERIFIED: entropy-adaptive guard is correctly wired.
                # Session type is None (not in _fired) AND context_tokens > 60000
                # → apply entropy-adaptive so EntropyEstimator guides the
                # threshold until the classifier locks. Do not remove this branch.
                _apply_profile(ctx, agent, "entropy-adaptive", session_id, 0.5, 0)
        except Exception as exc:
            logger.debug("lambda-tuner: on_pre_compress failed (fail-open): %s", exc)

    ctx.register_hook("on_session_start", on_session_start)
    ctx.register_hook("pre_llm_call", on_pre_llm_call)
    ctx.register_hook("pre_compress", on_pre_compress)
    ctx.register_hook("on_session_finalize", on_session_end)
    # Run before other pre_llm_call hooks that might read compression state.
    try:
        hooks = ctx._manager._hooks.get("pre_llm_call")
        if hooks and hooks[-1] is on_pre_llm_call:
            hooks.insert(0, hooks.pop())
    except Exception:
        pass  # fail-open: registration order stays as-is


# Export predicates for other plugins (lazy-read `_fired` at call time).
from .predicates import (  # noqa: E402
    is_code_session,
    is_high_confidence,
    is_research_session,
    session_complexity,
    session_type,
    was_reclassified,
)

__all__ = [
    "register",
    "is_research_session",
    "is_code_session",
    "is_high_confidence",
    "session_type",
    "session_complexity",
    "was_reclassified",
    "TaskComplexityScorer",
]

