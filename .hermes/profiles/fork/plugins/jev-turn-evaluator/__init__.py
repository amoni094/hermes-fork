"""jev-turn-evaluator — JEV-inspired per-turn quality telemetry plugin.

Shadow-only observer. Registers a post_llm_call hook that scores each assistant
turn across four quality dimensions and appends the result to a JSONL telemetry
file. Does NOT inject messages, mutate conversation history, or affect control
flow in any way.

ASSUME: post_llm_call is observer-only (host ignores return); auxiliary LLM optional.
GUARANTEE: returns None; never appends to conversation_history; swallows exceptions.
# inner_objective == outer_objective: True
# inner_objective: record per-turn quality telemetry
# outer_objective: observe session quality without affecting control flow

Design principles derived from adversarial audit deleg_123bd8ee (2026-10-07):

  1. post_llm_call is observer-only — return values are ignored by the host.
     This plugin returns None unconditionally.

  2. No recursion. The evaluator includes an origin-tag guard: if the last user
     message contains the evaluator's sentinel tag, evaluation is skipped to
     prevent any reentrance (even if a future host seam were to allow injection).

  3. Separate named budget (jev_eval_budget.json, 100/day by default) so the
     evaluator never starves jev-compaction's shared jev-call-budget.json.

  4. All exceptions are swallowed (H-I7). A telemetry failure must never
     contaminate the live session.

  5. Enabled only when `shadow_jev_evaluator: true` appears in the plugin
     config. Default: off. Promotion path: shadow_telemetry.py → shadow-gate-
     nightly.py → config flip after N sessions with no regressions.

  6. Uses atomic O_APPEND writes (<PIPE_BUF). No read-modify-write on the JSONL
     file; no in-process EMA that would require cross-process locks.

  7. Uses atomic_subquestions() from jev_verify_fn (provider-agnostic; works on
     Anthropic). Does NOT call logprob_classify (returns NaN on Anthropic).

  8. Sampling: evaluates 1 in SAMPLE_RATE turns (default=3) to bound latency
     and budget in tool-heavy sessions.

JSONL schema (one entry per evaluated turn):
  {
    "ts": float,                    # epoch seconds
    "session_id": str,
    "turn_idx": int,                # monotone counter per session
    "sampled": bool,                # false = skipped this turn
    "skip_reason": str | null,
    "scores": {
      "factual_coherence": int | null,   # 0-5
      "task_progress":     int | null,   # 0-5
      "tool_alignment":    bool | null,  # did tool calls match stated intent
      "efficiency":        int | null    # 0-5 (token/action economy)
    },
    "errors": [str]                 # per-question parse errors
  }
"""
from __future__ import annotations

import json
import logging
import os
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

ISS_GAIN = 0.12
EPS_DP = 0.0

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_HH = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_HP = os.environ.get("HERMES_PROFILE", "")
_PROFILE_ROOT = (_HH / "profiles" / _HP) if _HP else _HH

# Telemetry output (append-only)
_SCORES_LOG = _PROFILE_ROOT / "cache" / "jev-turn-scores.jsonl"

# Separate eval budget — never touches jev-call-budget.json (compaction's counter)
_EVAL_BUDGET_FILE = _PROFILE_ROOT / "cache" / "jev_eval_budget.json"
_EVAL_BUDGET_LOCK = threading.Lock()
_DEFAULT_EVAL_BUDGET = 100   # verify calls per day

# Evaluate 1 in N turns (configurable via plugin config)
_DEFAULT_SAMPLE_RATE = 3

# Sentinel to detect reentrant calls (future-proofing against message injection)
_EVALUATOR_SENTINEL = "[jev-eval-origin]"

# Turn counter — per-process, per-session (resets on session change)
_turn_state: Dict[str, Any] = {"session_id": None, "turn_idx": 0}
_TURN_LOCK = threading.Lock()

# ---------------------------------------------------------------------------
# Budget management (independent from jev_verify_fn budget)
# ---------------------------------------------------------------------------

def _check_eval_budget() -> bool:
    """Consume 1 eval credit. Returns False if exhausted. Fail-open on I/O error."""
    try:
        _EVAL_BUDGET_FILE.parent.mkdir(parents=True, exist_ok=True)
        today = time.strftime("%Y-%m-%d", time.gmtime())
        with _EVAL_BUDGET_LOCK:
            data: dict = {}
            if _EVAL_BUDGET_FILE.exists():
                try:
                    data = json.loads(_EVAL_BUDGET_FILE.read_text())
                except Exception:
                    data = {}
            if data.get("date") != today:
                data = {"date": today, "used": 0}
            used = data.get("used", 0)
            limit = data.get("limit", _DEFAULT_EVAL_BUDGET)
            if used + 1 > limit:
                logger.debug("jev-turn-evaluator: eval budget exhausted (%d/%d)", used, limit)
                return False
            data["used"] = used + 1
            tmp = _EVAL_BUDGET_FILE.with_suffix(".tmp")
            tmp.write_text(json.dumps(data))
            tmp.rename(_EVAL_BUDGET_FILE)
        return True
    except Exception as exc:
        logger.debug("jev-turn-evaluator: budget check failed (%s); allowing", exc)
        return True  # fail-open

# ---------------------------------------------------------------------------
# Telemetry writer (atomic O_APPEND)
# ---------------------------------------------------------------------------

def _append_score_entry(entry: dict) -> None:
    """Append one JSON entry to the scores log. O_APPEND is atomic for entries < PIPE_BUF."""
    try:
        _SCORES_LOG.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(entry, separators=(",", ":")) + "\n"
        with _SCORES_LOG.open("a", encoding="utf-8") as f:
            f.write(line)
    except Exception as exc:
        logger.debug("jev-turn-evaluator: log write failed: %s", exc)

# ---------------------------------------------------------------------------
# Evaluation core
# ---------------------------------------------------------------------------

def _evaluate_turn(
    assistant_response: str,
    conversation_history: list,
    session_id: str,
    turn_idx: int,
    provider: Optional[str],
    model: Optional[str],
) -> dict:
    """
    Run atomic_subquestions() over the turn. Returns a scores dict.
    Errors per-question are stored in the entry's errors list, not raised.
    """
    # Build state: last user message + assistant response (truncated to control cost)
    last_user = ""
    for msg in reversed(conversation_history or []):
        if isinstance(msg, dict) and msg.get("role") == "user":
            content = msg.get("content", "")
            if isinstance(content, list):
                # structured message list — extract text parts
                parts = [p.get("text", "") for p in content if isinstance(p, dict) and p.get("type") == "text"]
                content = " ".join(parts)
            last_user = str(content)[:500]
            break

    response_snippet = str(assistant_response or "")[:800]

    state = (
        f"Last user message: {last_user}\n\n"
        f"Assistant response (truncated): {response_snippet}"
    )

    # Import atomic_subquestions lazily (avoids A4 sys.path cost at module load)
    try:
        _ha = str(_HH / "hermes-agent")
        if _ha not in sys.path:
            sys.path.insert(0, _ha)
        from agent.auxiliary_client import call_llm  # noqa: PLC0415
    except ImportError:
        return {
            "factual_coherence": None, "task_progress": None,
            "tool_alignment": None, "efficiency": None,
        }, ["auxiliary_client unavailable"]

    # Build JSON-schema batch (4 questions in one call)
    schema = {
        "type": "object",
        "properties": {
            "factual_coherence": {
                "type": "integer", "minimum": 0, "maximum": 5,
                "description": "How factually coherent and internally consistent is the response? (0=contradictory/nonsense, 5=fully consistent)"
            },
            "task_progress": {
                "type": "integer", "minimum": 0, "maximum": 5,
                "description": "How well does the response advance the user's stated goal? (0=no progress/wrong direction, 5=decisive progress)"
            },
            "tool_alignment": {
                "type": "boolean",
                "description": "Did tool calls (if any) align with the stated intent in the response? True if aligned or no tools used."
            },
            "efficiency": {
                "type": "integer", "minimum": 0, "maximum": 5,
                "description": "How efficiently was the task addressed? (0=wasteful/repetitive, 5=concise and direct)"
            },
        },
        "required": ["factual_coherence", "task_progress", "tool_alignment", "efficiency"],
        "additionalProperties": False,
    }

    messages = [
        {
            "role": "system",
            "content": (
                "You are a precise quality evaluator for AI agent turns. "
                "Score the assistant response shown using ONLY the JSON schema provided. "
                "Do not add explanation or commentary."
            ),
        },
        {"role": "user", "content": f"Evaluate this agent turn:\n\n{state}"},
    ]

    errors: List[str] = []
    scores = {"factual_coherence": None, "task_progress": None, "tool_alignment": None, "efficiency": None}

    try:
        response = call_llm(
            task="jev_turn_eval",
            provider=provider,
            model=model,
            messages=messages,
            max_tokens=128,
            temperature=0.0,
            timeout=12.0,
            extra_body={
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "turn_eval",
                        "schema": schema,
                        "strict": False,
                    },
                }
            },
        )
        text = ""
        if hasattr(response, "choices") and response.choices:
            msg = response.choices[0].message
            text = getattr(msg, "content", "") or ""
        elif isinstance(response, str):
            text = response

        # Strip markdown fences
        import re
        text = re.sub(r"^```[a-z]*\n?|\n?```$", "", text, flags=re.MULTILINE).strip()

        parsed = json.loads(text)
        # Type-coerce
        for k in ("factual_coherence", "task_progress", "efficiency"):
            v = parsed.get(k)
            if v is not None:
                try:
                    scores[k] = int(v)
                except (TypeError, ValueError) as e:
                    errors.append(f"{k}: {e}")
        ta = parsed.get("tool_alignment")
        if ta is not None:
            if isinstance(ta, bool):
                scores["tool_alignment"] = ta
            else:
                scores["tool_alignment"] = str(ta).lower() not in {"false", "0", "no", ""}
    except Exception as exc:
        errors.append(f"provider/parse: {exc}")

    return scores, errors


# ---------------------------------------------------------------------------
# Hook factory
# ---------------------------------------------------------------------------

def _make_post_llm_call_hook(ctx: Any, sample_rate: int, provider: Optional[str], model: Optional[str]):
    def post_llm_call(
        assistant_response: Any = None,
        conversation_history: Any = None,
        **_kwargs,
    ) -> None:
        """Shadow observer: score the turn and append to JSONL. Never raises."""
        try:
            # Extract session_id from ctx (best-effort)
            session_id = ""
            try:
                session_id = str(ctx.get_config("session_id", "") or ctx.metadata.get("session_id", ""))
            except Exception:
                pass

            # Increment turn counter (per session)
            with _TURN_LOCK:
                if _turn_state["session_id"] != session_id:
                    _turn_state["session_id"] = session_id
                    _turn_state["turn_idx"] = 0
                _turn_state["turn_idx"] += 1
                turn_idx = _turn_state["turn_idx"]

            ts = time.time()
            entry_base = {"ts": ts, "session_id": session_id, "turn_idx": turn_idx}

            # Reentrance guard: skip if last user message has evaluator sentinel
            try:
                for msg in reversed(conversation_history or []):
                    if isinstance(msg, dict) and msg.get("role") == "user":
                        content = msg.get("content", "")
                        if isinstance(content, str) and _EVALUATOR_SENTINEL in content:
                            _append_score_entry({**entry_base, "sampled": False, "skip_reason": "reentrant_sentinel"})
                            return
                        break
            except Exception:
                pass

            # Sampling: skip unless this is a sample turn
            if sample_rate > 1 and (turn_idx % sample_rate) != 1:
                _append_score_entry({**entry_base, "sampled": False, "skip_reason": f"sampling_{turn_idx % sample_rate}"})
                return

            # Budget check
            if not _check_eval_budget():
                _append_score_entry({**entry_base, "sampled": False, "skip_reason": "budget_exhausted"})
                return

            # Extract response text
            resp_text = ""
            if isinstance(assistant_response, str):
                resp_text = assistant_response
            elif hasattr(assistant_response, "content"):
                content = assistant_response.content
                if isinstance(content, list):
                    resp_text = " ".join(
                        p.get("text", "") if isinstance(p, dict) else str(p)
                        for p in content
                    )
                else:
                    resp_text = str(content or "")

            # Run evaluation
            scores, errors = _evaluate_turn(
                assistant_response=resp_text,
                conversation_history=conversation_history or [],
                session_id=session_id,
                turn_idx=turn_idx,
                provider=provider,
                model=model,
            )

            _append_score_entry({
                **entry_base,
                "sampled": True,
                "skip_reason": None,
                "scores": scores,
                "errors": errors,
            })

        except Exception as exc:
            # H-I7: shadow paths never raise
            logger.debug("jev-turn-evaluator: post_llm_call shadow exception: %s", exc)

    return post_llm_call


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def register(ctx: Any) -> None:
    """Register the post_llm_call shadow hook if shadow_jev_evaluator is enabled."""
    try:
        enabled = ctx.get_config("shadow_jev_evaluator", False)
    except Exception:
        enabled = False

    if not enabled:
        logger.debug("jev-turn-evaluator: shadow_jev_evaluator=false — not registering hook")
        return

    try:
        sample_rate = int(ctx.get_config("sample_rate", _DEFAULT_SAMPLE_RATE))
    except Exception:
        sample_rate = _DEFAULT_SAMPLE_RATE

    try:
        provider = ctx.get_config("eval_provider", None)
        model = ctx.get_config("eval_model", None)
    except Exception:
        provider = None
        model = None

    ctx.register_hook("post_llm_call", _make_post_llm_call_hook(ctx, sample_rate, provider, model))
    logger.debug(
        "jev-turn-evaluator: shadow registered (sample_rate=%d, provider=%s, model=%s)",
        sample_rate, provider or "auto", model or "auto",
    )
