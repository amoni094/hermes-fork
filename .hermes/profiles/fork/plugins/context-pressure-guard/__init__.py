"""context-pressure-guard — pre_llm_call plugin for Hermes fork.

Reads the pressure log written by context-pressure-reader.py and injects
a [CONTEXT PRESSURE HIGH] hint into the system context when consecutive HIGH
pressure turns >= 2, nudging the model toward concise replies before the
compressor fires.

Architecture note (ARCHITECTURE.md TIER 2 gap #6):
  pressure_flag is logged but never acted on → this plugin closes the loop.

Stdlib-only; shadow-wrapped (never raises into the host).

ASSUME: pressure JSONL exists or is absent; compressor.lambda_ is a float in
        [0, 1] when present; pre_llm_call/pre_compress are synchronous.
GUARANTEE: fail-open (never raises); may return {context: hint}; lambda is set
           by a memoryless Lyapunov map, not an integral ratchet.
# inner_objective == outer_objective: True
# inner_objective: keep consecutive HIGH pressure at or below threshold
# outer_objective: preserve session usefulness under bounded context
"""
from __future__ import annotations
import os

import json
import logging
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger("context-pressure-guard")

# ISS small-gain (Sontag): perturbation amplification on shared hooks. Product of
# co-located plugin gains must be < 1.
ISS_GAIN = 0.45
EPS_DP = 0.0  # does not read vault.db / memories/

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
_LAMBDA_EQ = 0.5
_LYAPUNOV_K = 0.05  # plant small-gain: αK < 1 (α≈8 in the property-test plant)
_LAMBDA_MAX = 0.95


def lyapunov_V(pressure: float, threshold: float = _CONSECUTIVE_THRESHOLD) -> float:
    """V = (pressure - threshold)^2. Discrete Lyapunov candidate (Khalil)."""
    return (float(pressure) - float(threshold)) ** 2


def lyapunov_lambda(pressure: float) -> float:
    """Memoryless proportional map λ = clip(λeq + K·max(0, p-θ), λeq, λmax).

    Replaces the old integral ratchet (λ ← λ + 0.05 per turn) which saturates
    at 0.95 and cannot decrease V once control authority is gone.
    """
    error = max(0.0, float(pressure) - float(_CONSECUTIVE_THRESHOLD))
    return min(_LAMBDA_EQ + _LYAPUNOV_K * error, _LAMBDA_MAX)


def _build_pressure_hint(n: int) -> str:
    return (
        f"[CONTEXT PRESSURE HIGH: consecutive_high={n}"
        " — prefer concise responses and avoid large tool outputs this turn]"
    )


def _profile_root() -> Path:
    base = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
    profile = os.environ.get("HERMES_PROFILE", "")
    if profile and "profiles" not in str(base):
        return base / "profiles" / profile
    return base


def _advisory_paths() -> list[Path]:
    root = _profile_root()
    home = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
    return [
        root / "cache" / "rd-compaction-advisory.json",
        home / "cache" / "rd-compaction-advisory.json",
        Path.home() / ".hermes" / "profiles" / "fork" / "cache" / "rd-compaction-advisory.json",
    ]


def _read_rd_lambda_target() -> float | None:
    """Read rd-lambda-target.json written by rd-compaction-advisor. WIRE-050 fix.

    Returns the lambda value if present and valid, else None.
    This file is the direct lambda recommendation from the advisor (not aggressiveness proxy).
    """
    root = _profile_root()
    home = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
    candidates = [
        root / "cache" / "rd-lambda-target.json",
        home / "cache" / "rd-lambda-target.json",
    ]
    for path in candidates:
        try:
            if not path.exists():
                continue
            data = json.loads(path.read_text(encoding="utf-8"))
            val = float(data.get("lambda", -1) or -1)
            if 0.0 <= val <= 1.0:
                return val
        except (json.JSONDecodeError, OSError, ValueError):
            continue
    return None


def _read_rd_aggressiveness() -> float | None:
    """Read persisted rd-compaction-advisor aggressiveness. Fail-open."""
    for path in _advisory_paths():
        try:
            if not path.exists():
                continue
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and "aggressiveness" in data:
                return float(data["aggressiveness"])
        except Exception:
            continue
    return None


def _monotone_lambda(current: float, proposed: float, floor: float, cap: float = _LAMBDA_MAX) -> float:
    """Hard core: lambda only increases; never decreases spontaneously."""
    return min(cap, max(float(current or 0.0), float(proposed or 0.0), float(floor or 0.0)))


def _floor_path() -> Path:
    return _profile_root() / "cache" / "rd-lambda-floor.json"


def _read_session_floor(session_id: str) -> float:
    path = _floor_path()
    try:
        if not path.exists():
            return 0.0
        data = json.loads(path.read_text(encoding="utf-8")) or {}
        if data.get("session_id") and session_id and data.get("session_id") != session_id:
            return 0.0  # new session: floor resets (not spontaneous)
        return float(data.get("lambda", 0.0) or 0.0)
    except Exception:
        return 0.0


def _atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload), encoding="utf-8")
    os.replace(tmp, path)


def _write_session_floor(session_id: str, value: float) -> None:
    _atomic_json(_floor_path(), {
        "session_id": session_id,
        "lambda": round(float(value), 4),
        "ts": __import__("time").time(),
    })


def _write_lambda_tuner_target(new_lambda: float, session_id: str) -> None:
    """File interface for lambda-tuner (no hook parameter exposed)."""
    root = _profile_root()
    _atomic_json(root / "cache" / "rd-lambda-target.json", {
        "lambda": round(float(new_lambda), 4),
        "session_id": session_id,
        "monotone": True,
        "source": "context-pressure-guard/rd-compaction-advisor",
        "ts": __import__("time").time(),
    })
    home = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
    for hp in (root / "cache" / "last-session-type.json", home / "cache" / "last-session-type.json"):
        try:
            if not hp.exists():
                continue
            data = json.loads(hp.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                continue
            old = float(data.get("lambda", 0) or 0)
            if new_lambda > old:
                data["lambda"] = str(round(new_lambda, 3))
                data["rd_wired"] = True
                _atomic_json(hp, data)
        except Exception:
            continue


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
    """Wire rd-compaction-advisor aggressiveness into compressor lambda.

    Always reads cache/rd-compaction-advisory.json. Lyapunov pressure map
    still raises lambda when consecutive HIGH exceeds threshold. Hard core:
    lambda is monotone-increasing within a session (never decreases
    spontaneously). Writes cache/rd-lambda-target.json for lambda-tuner.
    Fail-open (H-I7). Proposal: proposals/wave18-rd-compaction-wiring.json.
    """
    try:
        status = _get_pressure_status()
        n = int(status.get("consecutive_high", 0) or 0)
        rd_agg = _read_rd_aggressiveness()
        proposed = float(rd_agg) if rd_agg is not None else 0.0
        if n > _CONSECUTIVE_THRESHOLD:
            proposed = max(proposed, float(lyapunov_lambda(n)))
        # WIRE-050 fix: also consume rd-lambda-target.json (direct lambda from advisor)
        _rd_lambda = _read_rd_lambda_target()
        if _rd_lambda is not None:
            proposed = max(proposed, _rd_lambda)
        compressor = None
        if agent is not None:
            compressor = getattr(agent, "context_compressor", None)
        current_lambda = _LAMBDA_EQ
        if compressor is not None:
            current_lambda = float(getattr(compressor, "lambda_", _LAMBDA_EQ) or _LAMBDA_EQ)
        floor = _read_session_floor(session_id)
        new_lambda = _monotone_lambda(current_lambda, proposed, floor)
        if compressor is not None and new_lambda > current_lambda:
            compressor.lambda_ = new_lambda
            logger.info(
                "context-pressure-guard: rd-wired lambda %.2f → %.2f "
                "(rd_agg=%s consecutive_high=%d V=%.2f)",
                current_lambda,
                new_lambda,
                rd_agg,
                n,
                lyapunov_V(n),
            )
        if new_lambda > floor:
            _write_session_floor(session_id, new_lambda)
        _write_lambda_tuner_target(new_lambda, session_id)
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
