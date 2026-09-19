"""context-pressure-guard — pre_llm_call plugin for Hermes fork.

Reads the pressure log written by context-pressure-reader.py and injects
a [CONTEXT PRESSURE HIGH] hint into the system context when consecutive HIGH
pressure turns >= 2, nudging the model toward concise replies before the
compressor fires.

Architecture note (ARCHITECTURE.md TIER 2 gap #6):
  pressure_flag is logged but never acted on → this plugin closes the loop.

Stdlib-only; shadow-wrapped (never raises into the host).
"""
from __future__ import annotations
import os

import json
import logging
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger("context-pressure-guard")

# ── pressure reader ──────────────────────────────────────────────────────────

_SCRIPT_PATH = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))) / "scripts" / "context-pressure-reader.py"


def _get_pressure_status() -> dict:
    """Inline reimplementation of context-pressure-reader.get_pressure_status().

    We inline rather than import to avoid sys.path mutation and to stay
    fail-open regardless of script location.  The logic is identical to the
    55-line reference script.
    """
    try:
        cache_dir = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))) / "cache"
        candidates = (
            list(cache_dir.glob("*pressure*.jsonl"))
            + list(cache_dir.glob("turn_usage*.jsonl"))
            + list(cache_dir.glob("*turn*usage*.jsonl"))
        )
        if not candidates:
            return {"consecutive_high": 0, "should_reduce": False, "source": "no_log"}
        log_path = sorted(candidates, key=lambda p: p.stat().st_mtime)[-1]
        lines = log_path.read_text().splitlines()[-10:]
        consecutive = 0
        for line in reversed(lines):
            try:
                row = json.loads(line)
                pf = row.get("pressure_flag") or row.get("pressure") or ""
                if str(pf).upper() == "HIGH":
                    consecutive += 1
                else:
                    break
            except Exception:
                break
        return {
            "consecutive_high": consecutive,
            "should_reduce": consecutive >= 3,
            "source": str(log_path),
        }
    except Exception as exc:
        return {"consecutive_high": 0, "should_reduce": False, "error": str(exc)}


# ── hook implementations ─────────────────────────────────────────────────────

# Threshold: fire the hint when >= 2 consecutive HIGH turns are seen.
# (The reader's own should_reduce fires at >= 3; we act earlier.)
_CONSECUTIVE_THRESHOLD = 2


def _build_pressure_hint(n: int) -> str:
    return (
        f"[CONTEXT PRESSURE HIGH: consecutive_high={n}"
        " — prefer concise responses and avoid large tool outputs this turn]"
    )


def on_pre_llm_call(
    *,
    agent: Any = None,
    session_id: str = "",
    messages: Any = None,
    **_kwargs: Any,
) -> dict | None:
    """Inject a context pressure hint before the LLM call when pressure is high."""
    try:
        status = _get_pressure_status()
        n = status.get("consecutive_high", 0)
        if n >= _CONSECUTIVE_THRESHOLD:
            hint = _build_pressure_hint(n)
            logger.info(
                "context-pressure-guard: injecting hint (consecutive_high=%d, source=%s)",
                n,
                status.get("source", "unknown"),
            )
            return {"context": hint}
        # Normal path — no hint needed.
        logger.debug(
            "context-pressure-guard: pressure OK (consecutive_high=%d)", n
        )
    except Exception as exc:
        logger.debug("context-pressure-guard: on_pre_llm_call suppressed: %s", exc)
    return None


def on_pre_compress(
    *,
    session_id: str = "",
    context_tokens: int = 0,
    agent: Any = None,
    **_kwargs: Any,
) -> None:
    """Optional: tighten compressor aggressiveness when pressure is high.

    We nudge the compressor's lambda (aggressiveness) upward so it prunes
    more eagerly when the pressure log says we're sustained-HIGH.  Fail-open.
    """
    try:
        status = _get_pressure_status()
        n = status.get("consecutive_high", 0)
        if n < _CONSECUTIVE_THRESHOLD:
            return
        # Try to find the compressor via agent or ctx (whichever is available
        # in this closure's scope at call time — ctx is captured in register()).
        compressor = None
        if agent is not None:
            compressor = getattr(agent, "context_compressor", None)
        if compressor is None:
            return
        # Nudge lambda up by 0.05 per consecutive HIGH turn, capped at 0.95.
        current_lambda = float(getattr(compressor, "lambda_", 0.5) or 0.5)
        nudge = min(0.05 * n, 0.20)  # max +0.20 total nudge
        new_lambda = min(current_lambda + nudge, 0.95)
        if new_lambda != current_lambda:
            compressor.lambda_ = new_lambda
            logger.info(
                "context-pressure-guard: nudged compressor lambda %.2f → %.2f "
                "(consecutive_high=%d)",
                current_lambda,
                new_lambda,
                n,
            )
    except Exception as exc:
        logger.debug("context-pressure-guard: on_pre_compress suppressed: %s", exc)


# ── registration ─────────────────────────────────────────────────────────────


def register(ctx: Any) -> None:
    """Register hooks with the Hermes plugin context."""
    try:
        ctx.register_hook("pre_llm_call", on_pre_llm_call)
        logger.debug("context-pressure-guard: registered pre_llm_call hook")
    except Exception as exc:
        logger.warning("context-pressure-guard: failed to register pre_llm_call: %s", exc)

    try:
        ctx.register_hook("pre_compress", on_pre_compress)
        logger.debug("context-pressure-guard: registered pre_compress hook")
    except Exception as exc:
        # pre_compress is optional — log at debug so it doesn't alarm on older
        # Hermes versions that don't expose this hook.
        logger.debug("context-pressure-guard: pre_compress registration skipped: %s", exc)
