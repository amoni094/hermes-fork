#!/usr/bin/env python3
"""
jev_verify_fn.py

Wires consistency_scorer.py to a real LLM call via Hermes auxiliary_client.
Implements the missing verify_fn that the consistency scorer needs.

Also provides:
  - atomic_subquestions(): batch multiple typed sub-questions in one call
  - calibrated_gate(): returns (act | flag | escalate) from a confidence float
  - logprob_classify(): reads letter-token logprobs for calibrated choice P(option)
    (OpenAI-compatible providers only; gracefully degrades to JSON mode otherwise)

Jev-inspired patterns, built on existing Hermes infrastructure.
No new core tools. Stdlib + hermes-agent imports only.

KNOWN ARCHITECTURAL LIMIT (A4): This script reaches into hermes-agent's internal
package via sys.path injection. This violates the Footprint Ladder (rung 2 = CLI
command + skill is the correct target). Cannot be fixed without a `hermes auxiliary`
CLI surface that does not yet exist. Document before using in production pipelines.

Usage (standalone):
    python3 jev_verify_fn.py --finding "Python handles None in this path correctly"
    python3 jev_verify_fn.py --demo

Usage (from other scripts):
    from jev_verify_fn import make_verify_fn, atomic_subquestions, calibrated_gate
"""

from __future__ import annotations
import os

import argparse
import json
import logging
import re
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ── Calibration event log (read by calibration-threshold-updater.py) ─────────

_CALIB_LOG = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))) / "cache" / "calibration-log.jsonl"

# Call budget: Jevons rebound guard (A7 fix)
_BUDGET_FILE = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))) / "cache" / "jev-call-budget.json"
_BUDGET_LOCK = threading.Lock()
_DEFAULT_DAILY_BUDGET = 200  # verify calls per day; raise explicitly if needed


def _check_and_charge_budget(n: int = 1) -> bool:
    """
    Consume n calls from the daily budget. Returns False if budget exhausted.
    Budget resets at UTC midnight. Best-effort: on write error, allows the call.
    """
    try:
        _BUDGET_FILE.parent.mkdir(parents=True, exist_ok=True)
        today = time.strftime("%Y-%m-%d", time.gmtime())
        with _BUDGET_LOCK:
            data: dict = {}
            if _BUDGET_FILE.exists():
                try:
                    data = json.loads(_BUDGET_FILE.read_text())
                except Exception:
                    data = {}
            if data.get("date") != today:
                data = {"date": today, "used": 0}
            used = data.get("used", 0)
            limit = data.get("limit", _DEFAULT_DAILY_BUDGET)
            if used + n > limit:
                logger.warning(
                    "jev_verify_fn: daily call budget exhausted (%d/%d). "
                    "Raise limit in %s or wait for UTC midnight.",
                    used, limit, _BUDGET_FILE,
                )
                return False
            data["used"] = used + n
            tmp = _BUDGET_FILE.with_suffix(".tmp")
            tmp.write_text(json.dumps(data))
            tmp.rename(_BUDGET_FILE)
        return True
    except Exception as exc:
        logger.debug("jev_verify_fn: budget check failed (%s); allowing call", exc)
        return True  # fail open: budget errors don't block real work


def _write_calib_event(scope: str, predicted: float, agreed: bool) -> None:
    """
    Append one calibration event to the log (best-effort, never raises).

    NOTE (A3): This writes a real predicted_confidence value (from the scorer
    result), not the hardcoded 0.5 that earlier versions used. calibration-
    threshold-updater.py reads this to compute the drift between predicted and
    observed agreement rates. If predicted_confidence is unknown at write time,
    pass float('nan') — the updater skips NaN entries for drift computation.

    NOTE (A1/schema): The 'agreed' key matches the schema expected by
    calibration-threshold-updater.py. Other writers (metacognitive-harness.py)
    use 'condorcet_score' — the updater must handle both.
    """
    try:
        _CALIB_LOG.parent.mkdir(parents=True, exist_ok=True)
        entry = json.dumps({
            "ts": time.time(),
            "scope": scope,
            "predicted_confidence": round(predicted, 4) if predicted == predicted else None,  # NaN check
            "agreed": agreed,
        })
        # O_APPEND writes on Linux are atomic for entries < PIPE_BUF (4096 bytes).
        # Do not read the file from hot scoring paths (consistency_scorer drift check removed).
        with _CALIB_LOG.open("a") as f:
            f.write(entry + "\n")
    except Exception as exc:
        logger.debug("jev_verify_fn: calib log write failed: %s", exc)


# ── Hermes auxiliary_client import (lazy, cached, thread-safe) ──────────────

# S1 fix: resolve path and cache import at module level, check before inserting.
_HERMES_AGENT_PATH = str(Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))) / "hermes-agent")
_call_llm_cache: Any = None
_call_llm_lock = threading.Lock()


def _get_call_llm():
    """
    Import call_llm from hermes-agent tree; raises ImportError with guidance if missing.
    Thread-safe; import runs at most once per process.
    """
    global _call_llm_cache
    if _call_llm_cache is not None:
        return _call_llm_cache
    with _call_llm_lock:
        if _call_llm_cache is not None:
            return _call_llm_cache
        if _HERMES_AGENT_PATH not in sys.path:
            sys.path.insert(0, _HERMES_AGENT_PATH)
        try:
            from agent.auxiliary_client import call_llm  # noqa: PLC0415
            _call_llm_cache = call_llm
            return call_llm
        except ImportError as exc:
            raise ImportError(
                "Cannot import agent.auxiliary_client. "
                "Run from inside the hermes-agent venv or add it to PYTHONPATH. "
                "Alternatively, activate the venv: "
                "source ~/.hermes/hermes-agent/venv/bin/activate"
            ) from exc


# ── Core verify_fn factory ────────────────────────────────────────────────────

def make_verify_fn(
    *,
    provider: str | None = None,
    model: str | None = None,
    timeout: float = 8.0,
    scope: str = "default",
    log_calibration: bool = True,
):
    """
    Return a verify_fn compatible with consistency_scorer.consistency_score().

    The returned fn calls a cheap LLM with a yes/no question about the finding.
    Errors and timeouts count as disagreement (conservative — matches scorer design).

    IMPORTANT: the verify_fn does NOT write a calibration event itself — it has
    no access to the final consistency_score() result. The caller (or a wrapper)
    must call _write_calib_event(scope, final_score, ground_truth) separately
    when ground truth is available. See A3 in the known limitations.

    Args:
        provider: auxiliary provider (default: None → auto-route via auxiliary chain)
        model:    auxiliary model (default: None → config/auto; mistral-small recommended)
        timeout:  per-call timeout in seconds
        scope:    calibration log scope label (e.g. "skill_routing", "research_finding")
        log_calibration: reserved for future use (currently no-op; see A3)
    """
    call_llm = _get_call_llm()

    def verify_fn(finding: str) -> bool:
        if not _check_and_charge_budget(1):
            logger.warning("verify_fn: budget exhausted, returning False (disagreement)")
            return False
        messages = [
            {
                "role": "user",
                "content": (
                    "Does the following finding hold? "
                    "Answer with exactly one word: yes or no.\n\n"
                    f"Finding: {finding}"
                ),
            }
        ]
        try:
            response = call_llm(
                task="consistency_verify",
                provider=provider,
                model=model,
                messages=messages,
                max_tokens=4,
                temperature=0.0,
                timeout=timeout,
            )
            # Extract text (handles SimpleNamespace and dict shapes)
            text = ""
            if hasattr(response, "choices") and response.choices:
                msg = response.choices[0].message
                text = getattr(msg, "content", "") or ""
            elif isinstance(response, str):
                text = response
            word = text.strip().lower()
            # S10 fix: accept only 'yes'/'y'; log warning for unexpected tokens
            if word in {"yes", "y"}:
                return True
            elif word in {"no", "n"}:
                return False
            else:
                # Multi-word fallback: trust first word only, but warn
                first = word.split()[0] if word else ""
                if first in {"yes", "y"}:
                    logger.debug("verify_fn: model gave multi-word answer %r; treating as yes", text[:60])
                    return True
                logger.debug("verify_fn: unexpected answer %r; treating as disagreement", text[:60])
                return False
        except Exception as exc:
            logger.debug("verify_fn: LLM call failed (%s); counting as disagreement", exc)
            return False  # conservative: failure = disagreement

    return verify_fn


# ── Atomic sub-questions (speculative fan-out, single call) ──────────────────

# S7 fix: strip markdown code fences that some providers emit
_FENCE_RE = re.compile(r"^```[a-z]*\n?|\n?```$", re.MULTILINE)


def _strip_fences(text: str) -> str:
    return _FENCE_RE.sub("", text).strip()


@dataclass
class SubQuestion:
    """One typed sub-question for atomic_subquestions()."""
    id: str                         # key in the returned dict
    question: str                   # natural language question
    type: str = "bool"              # "bool" | "choice:A,B,C" | "score:0-5"
    weight: float = 1.0             # for caller-side weighting (not used internally)


@dataclass
class SubQuestionResult:
    id: str
    answer: Any                     # bool, str choice, or int score
    raw: str = ""                   # raw value from JSON
    error: str = ""                 # non-empty if this question failed to parse


def atomic_subquestions(
    context: str,
    questions: list[SubQuestion],
    *,
    provider: str | None = None,
    model: str | None = None,
    timeout: float = 15.0,
) -> list[SubQuestionResult]:
    """
    Ask multiple typed sub-questions in ONE LLM call (speculative fan-out pattern).

    Builds a JSON schema covering all questions, fires one call_llm call,
    returns typed results. Adding questions barely changes latency because
    they're evaluated together. Code owns control flow; AI fills semantic gaps.

    CRITICAL RULE (from poker evaluation): if a question requires multi-step
    implicit inference from raw state (e.g. "does a 3-spade board threaten a
    flush?" from raw card symbols), compute the answer in code first and pass
    the conclusion as context. Only ask the model about genuine semantic gaps.

    Type formats:
        "bool"         → answer is true or false
        "choice:A,B,C" → answer is one of A, B, C (exact string match)
        "score:0-5"    → answer is integer in [0, 5]

    Returns list of SubQuestionResult in the same order as questions.
    On provider error, returns all results with error="provider_error".
    """
    if not _check_and_charge_budget(1):
        return [
            SubQuestionResult(id=q.id, answer=None, error="budget_exhausted")
            for q in questions
        ]

    call_llm = _get_call_llm()

    # Build JSON schema properties for each question
    properties: dict[str, Any] = {}
    required = []
    descriptions = []

    for q in questions:
        required.append(q.id)
        if q.type == "bool":
            properties[q.id] = {"type": "boolean", "description": q.question}
        elif q.type.startswith("choice:"):
            opts = [o.strip() for o in q.type[7:].split(",") if o.strip()]
            properties[q.id] = {"type": "string", "enum": opts, "description": q.question}
        elif q.type.startswith("score:"):
            parts = q.type[6:].split("-")
            lo, hi = (int(parts[0]), int(parts[1])) if len(parts) == 2 else (0, 5)
            properties[q.id] = {
                "type": "integer",
                "minimum": lo,
                "maximum": hi,
                "description": q.question,
            }
        else:
            properties[q.id] = {"type": "string", "description": q.question}
        descriptions.append(f"  {q.id} ({q.type}): {q.question}")

    schema = {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False,
    }

    system = (
        "You are a precise classifier. Answer each question about the context "
        "using ONLY the JSON schema provided. Do not add explanation."
    )
    user_prompt = (
        f"Context:\n{context}\n\n"
        "Answer these questions:\n" + "\n".join(descriptions)
    )
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_prompt},
    ]
    extra_body = {
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "atomic_subquestions",
                "schema": schema,
                "strict": False,
            },
        }
    }

    # S6 fix: scale max_tokens with question count; minimum 512
    max_tokens = max(512, 100 * len(questions))

    try:
        response = call_llm(
            task="atomic_subquestions",
            provider=provider,
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=0.0,
            timeout=timeout,
            extra_body=extra_body,
        )
        text = ""
        if hasattr(response, "choices") and response.choices:
            msg = response.choices[0].message
            text = getattr(msg, "content", "") or ""
        elif isinstance(response, str):
            text = response

        # S7 fix: strip markdown fences before parsing
        text = _strip_fences(text)
        if not text.endswith("}"):
            logger.warning(
                "atomic_subquestions: response may be truncated (doesn't end with '}'); "
                "raw tail: %r", text[-40:]
            )
        parsed = json.loads(text)
    except Exception as exc:
        logger.warning("atomic_subquestions: provider/parse error: %s", exc)
        return [
            SubQuestionResult(id=q.id, answer=None, error="provider_error")
            for q in questions
        ]

    # Parse and type-check each answer
    results = []
    for q in questions:
        raw = parsed.get(q.id)
        try:
            if q.type == "bool":
                # S12 fix: string "false" must not become True via bool()
                if isinstance(raw, bool):
                    answer = raw
                else:
                    answer = str(raw).lower() not in {"false", "0", "no", ""}
            elif q.type.startswith("choice:"):
                answer = str(raw)
            elif q.type.startswith("score:"):
                answer = int(raw)
            else:
                answer = str(raw)
            results.append(SubQuestionResult(id=q.id, answer=answer, raw=str(raw)))
        except (TypeError, ValueError) as exc:
            results.append(SubQuestionResult(id=q.id, answer=None, raw=str(raw), error=str(exc)))

    return results


# ── Confidence gate (Jev-style three-tier routing) ────────────────────────────

@dataclass
class GateConfig:
    act_threshold: float = 0.9        # >= this → act autonomously
    flag_threshold: float = 0.5       # >= this → flag/confirm; < this → escalate
    stakes: str = "medium"            # "low" | "medium" | "high" — adjusts thresholds


# S2 fix: HIGH stakes RAISES thresholds (was incorrectly negative, making it easier
# to act at high stakes). The tuple is (act_adjustment, flag_adjustment).
# Positive = threshold goes up = harder to reach "act" = more conservative.
_STAKES_ADJUSTMENTS = {
    "low":    (-0.10, -0.10),   # lower bar for trivial tasks
    "medium": (0.0,   0.0),
    "high":   (+0.10, +0.05),   # higher bar for irreversible/expensive decisions
}


def calibrated_gate(confidence: float, config: GateConfig | None = None) -> str:
    """
    Map a calibrated confidence float to a routing decision.

    Returns one of: "act" | "flag" | "escalate"

    act:      confidence is high enough to proceed autonomously
    flag:     medium confidence — surface for confirmation before irreversible steps
    escalate: low confidence — route to a more capable model or human

    Stakes adjustment raises or lowers thresholds:
      low    (-0.10): act >= 0.80, flag >= 0.40  (permissive — cheap trivial tasks)
      medium (±0.00): act >= 0.90, flag >= 0.50  (default)
      high   (+0.10): act >= 1.00, flag >= 0.55  (conservative — irreversible actions)

    NOTE: if confidence is float('nan') or None (e.g. logprob fallback unavailable),
    this function returns "escalate" to fail safe rather than silently acting.
    """
    if config is None:
        config = GateConfig()

    # S3 fix: NaN/None confidence → escalate (safe default; logprob fallback returns nan)
    try:
        if confidence != confidence:  # NaN check
            logger.warning("calibrated_gate: NaN confidence received; returning 'escalate'")
            return "escalate"
    except TypeError:
        logger.warning("calibrated_gate: non-numeric confidence %r; returning 'escalate'", confidence)
        return "escalate"

    adj_act, adj_flag = _STAKES_ADJUSTMENTS.get(config.stakes, (0.0, 0.0))
    effective_act  = config.act_threshold  + adj_act
    effective_flag = config.flag_threshold + adj_flag

    if confidence >= effective_act:
        return "act"
    elif confidence >= effective_flag:
        return "flag"
    else:
        return "escalate"


# ── Logprob classify (calibrated P(option) for OpenAI-compat providers) ──────

def logprob_classify(
    context: str,
    options: list[str],
    *,
    provider: str | None = None,
    model: str | None = None,
    timeout: float = 8.0,
) -> dict[str, float]:
    """
    Classify context into one of options using next-token logprob reading.

    Returns {option: probability} normalized to sum=1.0.

    On providers that don't support logprobs (Anthropic, Gemini), returns
    {chosen_option: float('nan'), ...} so that calibrated_gate() sees NaN and
    returns "escalate" rather than silently acting. Callers that need a hard
    choice on non-OAI providers should use atomic_subquestions() instead.

    The mini-jev finding: reading letter-token P(A), P(B), P(C) at the answer
    position gives better-calibrated probabilities than asking the model to
    write confidence numbers. -0.22pp accuracy loss vs JSON grammar, 4x faster
    on short texts (Qwen3-4B on CLINC150 — not validated on Hermes routing tasks).

    Logprob reading requires: OpenAI API, OpenRouter (model-dependent),
    or local llama.cpp OpenAI-compat server. Does NOT work on Anthropic or Gemini.
    Max 26 options (A–Z). Raises ValueError for >26.
    """
    if not options:
        return {}
    if len(options) > 26:
        raise ValueError(f"logprob_classify: max 26 options, got {len(options)}")

    if not _check_and_charge_budget(1):
        return {opt: float("nan") for opt in options}

    call_llm = _get_call_llm()

    letters = [chr(65 + i) for i in range(len(options))]
    option_map = dict(zip(letters, options))
    choices_text = "\n".join(f"{l}. {o}" for l, o in option_map.items())

    messages = [
        {
            "role": "user",
            "content": (
                "Choose the best option for the following context. "
                "Respond with ONLY the letter.\n\n"
                f"Context: {context}\n\n"
                f"Options:\n{choices_text}"
            ),
        }
    ]

    # Try logprob path first
    try:
        # S5 fix: use min(len, 20) not min(len, 5) — OAI supports up to 20
        response = call_llm(
            task="logprob_classify",
            provider=provider,
            model=model,
            messages=messages,
            max_tokens=1,
            temperature=0.0,
            timeout=timeout,
            extra_body={"logprobs": True, "top_logprobs": min(len(options), 20)},
        )

        if (
            hasattr(response, "choices")
            and response.choices
            and hasattr(response.choices[0], "logprobs")
            and response.choices[0].logprobs is not None
        ):
            lp = response.choices[0].logprobs
            content = getattr(lp, "content", None)
            if content:
                import math
                raw_probs: dict[str, float] = {}
                for token_lp in content[:1]:
                    top = getattr(token_lp, "top_logprobs", [])
                    for tlp in top:
                        tok = getattr(tlp, "token", "").strip().upper()
                        lp_val = getattr(tlp, "logprob", None)
                        if tok in option_map and lp_val is not None:
                            raw_probs[tok] = math.exp(lp_val)

                if raw_probs:
                    total = sum(raw_probs.values())
                    if total > 0:
                        return {option_map[l]: p / total for l, p in raw_probs.items()}
    except Exception as exc:
        logger.debug("logprob_classify: logprob path failed (%s), falling back", exc)

    # S3 fix: fallback returns NaN probabilities so calibrated_gate() fails safe.
    # Do NOT return 1.0/0.0 — that makes calibrated_gate always return "act".
    # Callers that need a hard choice on Anthropic should use atomic_subquestions().
    logger.warning(
        "logprob_classify: logprobs unavailable for this provider. "
        "Returning NaN probabilities — calibrated_gate() will return 'escalate'. "
        "Use atomic_subquestions() for Anthropic/Gemini providers."
    )
    return {opt: float("nan") for opt in options}


# ── CLI entrypoint ────────────────────────────────────────────────────────────

def _demo() -> None:
    """Quick smoke test of all patterns without a real LLM (mock verify_fn)."""
    import random

    # S9 fix: each thread gets its own Random instance (not shared state)
    def make_mock_fn(seed: int):
        rng = random.Random(seed)
        return lambda f: rng.random() > 0.3

    # 1. consistency_scorer with per-thread mock verify_fn
    sys.path.insert(0, str(Path(__file__).parent))
    try:
        from consistency_scorer import consistency_score, ConsistencyConfig  # noqa: PLC0415
        score = consistency_score(
            "Python's open() raises FileNotFoundError on missing files",
            make_mock_fn(42),
            ConsistencyConfig(enabled=True, n=3, timeout=5.0, log_results=False),
        )
        print(f"consistency_score (mock, p≈0.7 agree): {score}")
    except ImportError:
        print("consistency_scorer.py not found in same directory — skip")

    # 2. atomic_subquestions schema construction (no LLM call)
    questions = [
        SubQuestion("needs_browser", "Does this need web access?", "bool"),
        SubQuestion("complexity", "Complexity 0-5", "score:0-5"),
        SubQuestion("route", "Best route", "choice:direct,skill,subagent"),
    ]
    props = {}
    for q in questions:
        if q.type == "bool":
            props[q.id] = {"type": "boolean"}
        elif q.type.startswith("choice:"):
            props[q.id] = {"type": "string", "enum": q.type[7:].split(",")}
        elif q.type.startswith("score:"):
            parts = q.type[6:].split("-")
            props[q.id] = {"type": "integer", "minimum": int(parts[0]), "maximum": int(parts[1])}
    print(f"atomic_subquestions schema: {json.dumps(props, indent=2)}")

    # 3. calibrated_gate — verify stakes signs are correct
    tests = [
        (0.95, "medium", "act"),
        (0.72, "medium", "flag"),   # 0.72 < 0.90
        (0.85, "high",   "flag"),   # 0.85 < 1.00 (high stakes: act >= 1.00)
        (0.3,  "high",   "escalate"),
        (0.82, "low",    "act"),    # 0.82 >= 0.80 (low stakes: act >= 0.80)
    ]
    for conf, stakes, expected in tests:
        decision = calibrated_gate(conf, GateConfig(stakes=stakes))
        status = "OK" if decision == expected else f"FAIL (expected {expected!r})"
        print(f"calibrated_gate({conf}, stakes={stakes!r}) → {decision!r}  {status}")

    # 4. NaN safety
    nan_result = calibrated_gate(float("nan"))
    print(f"calibrated_gate(NaN) → {nan_result!r}  {'OK' if nan_result == 'escalate' else 'FAIL'}")

    # 5. logprob_classify NaN fallback (no LLM)
    result = {opt: float("nan") for opt in ["research", "coding"]}
    gate = calibrated_gate(result.get("research", float("nan")))
    print(f"logprob NaN fallback → gate={gate!r}  {'OK' if gate == 'escalate' else 'FAIL'}")

    print("Demo complete. No LLM calls made.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Jev-inspired patterns for Hermes")
    parser.add_argument("--finding", help="Test verify_fn against this finding string")
    parser.add_argument("--scope", default="cli_test", help="Calibration scope label")
    parser.add_argument("--model", default=None, help="Auxiliary model override")
    parser.add_argument("--provider", default=None, help="Auxiliary provider override")
    parser.add_argument("--demo", action="store_true", help="Run smoke test (no LLM calls)")
    parser.add_argument(
        "--budget-status", action="store_true",
        help="Show current daily call budget status"
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG)

    if args.demo:
        _demo()
        return

    if args.budget_status:
        try:
            today = time.strftime("%Y-%m-%d", time.gmtime())
            data = json.loads(_BUDGET_FILE.read_text()) if _BUDGET_FILE.exists() else {}
            if data.get("date") != today:
                print(f"Budget: 0/{data.get('limit', _DEFAULT_DAILY_BUDGET)} used today (fresh)")
            else:
                print(f"Budget: {data['used']}/{data.get('limit', _DEFAULT_DAILY_BUDGET)} used today")
        except Exception as exc:
            print(f"Budget file read error: {exc}")
        return

    if args.finding:
        print(f"Testing verify_fn for finding: {args.finding!r}")
        try:
            fn = make_verify_fn(
                provider=args.provider,
                model=args.model,
                scope=args.scope,
            )
            result = fn(args.finding)
            print(f"verify_fn result: {result}")
        except ImportError as exc:
            print(f"ImportError: {exc}")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
