"""lambda-tuner — classify session type from first message, tune compression live.

Classifies each session as research / code / mixed from accumulated user messages,
then applies the appropriate ContextCompressor profile via the fork's new
``set_compression_profile()`` API (takes effect on the next compression event,
no N+1 lag). Also writes a hint file for the ``hermes-session`` launch wrapper so
the next-session warm-up path still works.

Design:
- Uses ``ctx.compressor.set_compression_profile(profile)`` when the compressor is
  reachable (hermes-fork only). Falls back to hint-file-only on vanilla Hermes.
- Accumulates all user turns; greeting/ack turns are filtered before scoring.
- Locks classification once a confident non-mixed result is found.
- Fail-open: any error is silently logged, never raised into hook dispatch.
"""
from __future__ import annotations

import json
import logging
import os
import re
import time
import tempfile
from collections import OrderedDict
from pathlib import Path
from typing import Any

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
_TYPE_TO_LAMBDA = {"research": "0.55", "code": "0.2", "mixed": "0.4"}

_last_hint_key: tuple[str, str] | None = None  # (type, lambda_str) dirty-check


def _write_hint(session_type: str, confidence: float, scores: dict[str, float]) -> None:
    """Atomically write the JSON hint file. Skip if type+lambda unchanged."""
    global _last_hint_key
    lam_str = _TYPE_TO_LAMBDA.get(session_type, _TYPE_TO_LAMBDA["mixed"])
    key = (session_type, lam_str)
    if _last_hint_key == key:
        return
    hint_path = _hint_path()
    hint_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "type": session_type,
        "profile": session_type,  # maps directly to COMPRESSION_PROFILES key
        "lambda": lam_str,
        "confidence": round(confidence, 3),
        "scores": {k: round(v, 3) for k, v in scores.items()},
        "ts": time.time(),
        "expires_at": time.time() + _HINT_TTL_SECONDS,
        "source": "lambda-tuner-plugin",
    }
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
    r"|citation|bibliography|abstract"
    r"|sweep(?:\s+papers?|\s+arxiv)?"
    r"|web\s+search|web\s+scrape|web\s+extract"
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
_MIN_SIGNAL   = 1


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
# Plugin state — bounded LRU so a long-running gateway cannot grow forever
# ---------------------------------------------------------------------------

_MAX_SESSIONS = 64
_MAX_MESSAGES_PER_SESSION = 32
_fired: OrderedDict[str, str] = OrderedDict()  # session_id -> locked type
_session_messages: OrderedDict[str, list[str]] = OrderedDict()


def _touch_session(session_id: str) -> None:
    """LRU-touch and evict oldest sessions (and their _fired entries) over cap."""
    if session_id in _session_messages:
        _session_messages.move_to_end(session_id)
    if session_id in _fired:
        _fired.move_to_end(session_id)
    while len(_session_messages) > _MAX_SESSIONS:
        evicted, _ = _session_messages.popitem(last=False)
        _fired.pop(evicted, None)
    while len(_fired) > _MAX_SESSIONS:
        _fired.popitem(last=False)


def _apply_profile(ctx: Any, agent: Any, session_type: str, session_id: str, confidence: float, n_turns: int) -> None:
    compressor = None
    try:
        compressor = ctx.compressor
    except AttributeError:
        pass
    if compressor is None and agent is not None:
        compressor = getattr(agent, "context_compressor", None)
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

def register(ctx: Any) -> None:
    def on_pre_llm_call(
        *,
        session_id: str = "",
        user_message: Any = None,
        is_first_turn: bool = False,
        agent: Any = None,
        **_kwargs: Any,
    ) -> None:
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
            if session_id in _fired:
                # Re-apply locked profile in case the compressor was rebuilt
                # (model switch / engine swap) after we first committed.
                _apply_profile(ctx, agent, _fired[session_id], session_id, 1.0, len(bucket))
                return

            session_type, confidence, scores = _classify(bucket)
            commit = session_type != "mixed" or len(bucket) >= 3

            _apply_profile(ctx, agent, session_type, session_id, confidence, len(bucket))
            _write_hint(session_type, confidence, scores)

            if commit:
                _fired[session_id] = session_type
                _fired.move_to_end(session_id)
                logger.debug(
                    "lambda-tuner: committed sid=%s type=%s conf=%.2f scores=%s turn=%d",
                    session_id, session_type, confidence, scores, len(bucket),
                )

        except Exception as exc:
            logger.debug("lambda-tuner: classify failed (fail-open): %s", exc)

    ctx.register_hook("pre_llm_call", on_pre_llm_call)
    # Run before other pre_llm_call hooks that might read compression state.
    try:
        hooks = ctx._manager._hooks.get("pre_llm_call")
        if hooks and hooks[-1] is on_pre_llm_call:
            hooks.insert(0, hooks.pop())
    except Exception:
        pass  # fail-open: registration order stays as-is

