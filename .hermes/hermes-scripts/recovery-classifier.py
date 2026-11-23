#!/usr/bin/env python3
"""
Recovery Classifier for Hermes Agent
=====================================
Research basis:
  arXiv:2508.07935 SHIELDA: 36-type exception taxonomy; cross-phase recovery
  arXiv:2606.01416 Self-healing recovery ladder: 98.8% success vs 94.5% blind retry
  arXiv:2509.25370 Root-cause module isolation: +24% all-correct, +26% relative task success
  arXiv:2606.05037 Structured error format: +36.7-40.0pp on Anthropic models
  arXiv:2605.08717 Bounded retry brief: recovered 21.79% of unresolved cases
  arXiv:2608.03222 Fail-fast loop detection: 14.6-20.4% token savings

Usage:
  python3 recovery-classifier.py classify --error "message" --tool "tool_name" --attempt 2
  python3 recovery-classifier.py loop-check --history '[{"tool":"x","args":"y"}, ...]'
  python3 recovery-classifier.py module --trajectory "last N steps description"
  python3 recovery-classifier.py brief --evidence "logs+test output" --cause "root cause"
  python3 recovery-classifier.py format-error --error-type MISSING_FIELD --field user_id --expected int --suggestion "use user.id"

Exit codes: 0 = proceed (local fix applied), 1 = retry-with-change, 2 = escalate, 3 = kill-trajectory
"""

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from typing import Optional

# ── Exception type taxonomy (simplified from SHIELDA's 36 types) ──────────────
EXCEPTION_TYPES = {
    "TIMEOUT": {
        "patterns": [r"timeout", r"timed out", r"deadline exceeded", r"connection reset"],
        "recovery": "RETRY_SMALLER",
        "action": "Break into smaller steps or increase timeout. Do not retry same-size call.",
    },
    "BAD_ARGS": {
        "patterns": [r"invalid (arg|argument|param|parameter|type|value)", r"expected .* got",
                     r"missing required", r"validation error", r"schema error",
                     r"cannot be (null|none|empty)", r"field required"],
        "recovery": "FIX_ARGS",
        "action": "Fix argument format/type from error message and schema. Do not retry same args.",
    },
    "STALE_CONTEXT": {
        "patterns": [r"no such (file|directory|table|key|resource)", r"not found",
                     r"does not exist", r"key error", r"undefined", r"undeclared",
                     r"prerequisite", r"missing dependency"],
        "recovery": "REWIND_PLAN",
        "action": "Missing prerequisite step. Rewind to before the precondition. Execute the missing step first.",
    },
    "REASONING_ERROR": {
        "patterns": [r"contradiction", r"inconsistent", r"impossible", r"cannot proceed",
                     r"logical error", r"infinite loop", r"circular"],
        "recovery": "REPLAN",
        "action": "Planning/logic error. Replan from current verified state. Do not continue same path.",
    },
    "RETRY_LOOP": {
        "patterns": [],  # detected structurally, not from message
        "recovery": "ESCALATE",
        "action": "Same action retried >= 3 times with same args. Escalate. Do not retry again.",
    },
    "UNVERIFIED": {
        "patterns": [r"unverified", r"not confirmed", r"ambiguous result", r"partial success"],
        "recovery": "VERIFY_FIRST",
        "action": "Action completed but result unverified. Verify before chaining further actions.",
    },
    "PERMISSION": {
        "patterns": [r"permission denied", r"unauthorized", r"forbidden", r"access denied",
                     r"403", r"401", r"not allowed"],
        "recovery": "ESCALATE",
        "action": "Permission/auth failure. Escalate to human or switch credential path.",
    },
    "RATE_LIMIT": {
        "patterns": [r"rate limit", r"429", r"too many requests", r"quota exceeded"],
        "recovery": "BACKOFF",
        "action": "Rate limited. Backoff exponentially. Do not immediately retry.",
    },
    "TOOL_UNAVAILABLE": {
        "patterns": [r"tool not found", r"command not found", r"module not found",
                     r"no such command", r"not installed"],
        "recovery": "ALTERNATE_TOOL",
        "action": "Tool/command unavailable. Use an alternate tool or install prerequisite first.",
    },
    "SYSTEM": {
        "patterns": [r"internal server error", r"500", r"service unavailable", r"503",
                     r"network error", r"connection refused"],
        "recovery": "WAIT_RETRY",
        "action": "System/environment failure (not agent fault). Wait briefly and retry once.",
    },
}

# ── Root-cause modules (arXiv:2509.25370) ─────────────────────────────────────
MODULE_PATTERNS = {
    "memory": [r"forgot", r"didn't remember", r"missing prior", r"lost context",
               r"already checked", r"duplicate action", r"checked that before"],
    "reflection": [r"self.assessment was wrong", r"misjudged", r"thought it was",
                   r"assumed incorrectly", r"believed.*but"],
    "planning": [r"wrong order", r"should have.*first", r"plan was flawed",
                 r"missed step", r"wrong sequence", r"should.*before"],
    "action": [r"wrong tool", r"wrong (file|path|url|endpoint|key|field)",
               r"typo", r"malformed (call|request|query)", r"bad (argument|parameter)"],
    "system": [r"(timeout|network|connection|service) (failure|error|issue)",
               r"environment problem", r"rate limit", r"server error"],
}


@dataclass
class ExceptionClassification:
    exception_type: str
    recovery: str
    action: str
    matched_patterns: list
    confidence: float
    structured_error: Optional[dict] = None


def classify_exception(error_message: str, tool_name: str = "", attempt: int = 1) -> dict:
    """
    Classify an error and return a recovery pattern.
    arXiv:2508.07935: execution-phase errors often originate in reasoning-phase.
    arXiv:2606.01416: classify first, then apply targeted fix, then verify.
    """
    # Structural override: too many retries — but NEVER convert RATE_LIMIT/TIMEOUT to RETRY_LOOP
    # M5 FIX: rate-limit and timeout should backoff, not escalate as a loop
    if attempt >= 3:
        # First check if the error is actually rate-limit/timeout (should backoff not escalate)
        error_lower_pre = error_message.lower()
        is_rate_limit = any(re.search(p, error_lower_pre) for p in EXCEPTION_TYPES["RATE_LIMIT"]["patterns"])
        is_timeout = any(re.search(p, error_lower_pre) for p in EXCEPTION_TYPES["TIMEOUT"]["patterns"])
        if is_rate_limit or is_timeout:
            exc_type = "RATE_LIMIT" if is_rate_limit else "TIMEOUT"
            spec = EXCEPTION_TYPES[exc_type]
            exc = ExceptionClassification(
                exception_type=exc_type,
                recovery=spec["recovery"],
                action=f"{spec['action']} (attempt {attempt} — backoff, do not convert to RETRY_LOOP)",
                matched_patterns=[f"attempt={attempt} but rate-limit/timeout exempted from RETRY_LOOP"],
                confidence=0.9,
            )
            return _format_result(exc, tool_name, attempt)
        exc = ExceptionClassification(
            exception_type="RETRY_LOOP",
            recovery="ESCALATE",
            action=EXCEPTION_TYPES["RETRY_LOOP"]["action"],
            matched_patterns=["attempt >= 3"],
            confidence=1.0,
        )
        return _format_result(exc, tool_name, attempt)

    error_lower = error_message.lower()
    best_type = None
    best_patterns = []
    best_score = 0
    best_max_len = 0  # M5 FIX: longest-pattern wins for tie-break (more specific beats generic)

    for exc_type, spec in EXCEPTION_TYPES.items():
        if not spec["patterns"]:
            continue
        matches = [p for p in spec["patterns"] if re.search(p, error_lower)]
        if not matches:
            continue
        # Score = number of matches; tie-break = longest matched pattern string (more specific)
        max_len = max(len(p) for p in matches)
        if len(matches) > best_score or (len(matches) == best_score and max_len > best_max_len):
            best_score = len(matches)
            best_max_len = max_len
            best_type = exc_type
            best_patterns = matches

    # M5 FIX: default to ESCALATE/UNKNOWN on no match (not SYSTEM/WAIT_RETRY)
    if best_type is None:
        exc = ExceptionClassification(
            exception_type="UNKNOWN",
            recovery="ESCALATE",
            action="Unrecognized error type. Escalate — do not blindly retry an unclassified failure.",
            matched_patterns=[],
            confidence=0.2,
        )
        return _format_result(exc, tool_name, attempt)

    spec = EXCEPTION_TYPES[best_type]
    confidence = min(1.0, 0.5 + best_score * 0.2)

    exc = ExceptionClassification(
        exception_type=best_type,
        recovery=spec["recovery"],
        action=spec["action"],
        matched_patterns=best_patterns,
        confidence=round(confidence, 2),
    )
    return _format_result(exc, tool_name, attempt)


def _format_result(exc: ExceptionClassification, tool_name: str, attempt: int) -> dict:
    result = asdict(exc)
    result["tool"] = tool_name
    result["attempt"] = attempt
    result["recovery_ladder"] = {
        "step1": "Apply targeted fix based on exception_type",
        "step2": "Run verifier before accepting result",
        "step3": f"If verifier fails: {'escalate' if attempt >= 2 else 'one more targeted fix'}",
        "max_targeted_fixes": 2,
    }
    result["exit_code"] = (
        3 if exc.recovery == "ESCALATE" else
        2 if exc.recovery in ("REPLAN", "ALTERNATE_TOOL") else
        1  # retry with change
    )
    return result


def detect_loop(history: list) -> dict:
    """
    Detect looping trajectory from tool call history.
    arXiv:2608.03222: detect repeating (tool, args) triples -> kill and restart fresh.
    """
    if len(history) < 2:
        return {"loop_detected": False, "action": "Continue", "exit_code": 0}

    # C2 FIX: require 3 identical (tool, args) hits before declaring a loop (not 2)
    # Also: stasis check requires SAME args+result-hash, not just same tool name
    seen: dict = {}
    for i, call in enumerate(history):
        key = (call.get("tool", ""), str(call.get("args", "")))
        if key in seen:
            # Count how many times this exact key has appeared
            seen[key].append(i)
        else:
            seen[key] = [i]

    for key, positions in seen.items():
        if len(positions) >= 3:  # C2: 3 hits required (not 2)
            tool_name, args_str = key
            return {
                "loop_detected": True,
                "loop_type": "SAME_TOOL_ARGS",
                "repeated_call": {"tool": tool_name, "args": args_str},
                "positions": positions[:5],  # first 5 occurrences
                "count": len(positions),
                "action": (
                    "KILL TRAJECTORY. Start fresh prompt. Attach interrupted work product "
                    "(diff/partial output) as OPTIONAL context. Do not continue this context."
                ),
                "exit_code": 3,
            }

    # Check for stasis: same tool AND same args (not just same tool name)
    # C2 FIX: stasis requires matching args hash, not just tool name
    recent = history[-5:]
    if len(recent) >= 3:
        recent_keys = [(h.get("tool", ""), str(h.get("args", ""))) for h in recent]
        unique_keys = set(recent_keys)
        if len(unique_keys) == 1:
            tool_name = recent[0].get("tool", "unknown")
            return {
                "loop_detected": True,
                "loop_type": "SINGLE_TOOL_STASIS",
                "repeated_tool": tool_name,
                "count": len(recent),
                "action": (
                    f"Tool '{tool_name}' called {len(recent)} consecutive times with SAME args. "
                    "No state change — kill trajectory and restart fresh. "
                    "NOTE: same tool with DIFFERENT args is normal gather/verify, not stasis."
                ),
                "exit_code": 3,
            }

    return {
        "loop_detected": False,
        "history_length": len(history),
        "action": "Continue — no loop detected",
        "exit_code": 0,
    }


def classify_module(trajectory_description: str) -> dict:
    """
    Identify which agent module caused a failure.
    arXiv:2509.25370: isolate failed module, inject corrective instruction,
    resume from last verified checkpoint. +24% all-correct, up to +26% relative success.
    """
    text_lower = trajectory_description.lower()
    scores = {}
    for module, patterns in MODULE_PATTERNS.items():
        hits = [p for p in patterns if re.search(p, text_lower)]
        scores[module] = len(hits)

    best_module = max(scores, key=lambda k: scores[k])
    best_score = scores[best_module]

    module_actions = {
        "memory": (
            "Inject prior-fact reminder: retrieve relevant memory before continuing. "
            "Add a 'Known facts' block at the start of the next prompt."
        ),
        "reflection": (
            "Inject corrective assessment: ask agent to re-evaluate its confidence "
            "about the specific wrong assumption before acting."
        ),
        "planning": (
            "Inject plan correction: rewrite the remaining subgoal list from current state. "
            "Do not continue the old plan past the error point."
        ),
        "action": (
            "Inject targeted fix: name the specific wrong argument/tool/path. "
            "Provide the corrected value directly. Do not ask agent to 'try again'."
        ),
        "system": (
            "System/environment failure — not agent fault. "
            "Check tool availability, permissions, and connectivity before retrying."
        ),
    }

    return {
        "failed_module": best_module if best_score > 0 else "unknown",
        "confidence": round(min(1.0, 0.4 + best_score * 0.25), 2),
        "module_scores": scores,
        "corrective_action": module_actions.get(best_module, "Unknown module — escalate"),
        "note": (
            "Store failure class in Hindsight to prevent recurrence: "
            f"hindsight_retain(content='Module {best_module} failure: {{specific error}}', "
            f"tags=[\"failure-class\", \"{best_module}\"])"
        ),
    }


def format_structured_error(error_type: str, field: Optional[str] = None,
                            expected: Optional[str] = None, suggestions: Optional[list] = None) -> dict:
    """
    Format a structured error response for tool wrappers.
    arXiv:2606.05037: structured JSON errors +36.7-40.0pp on Anthropic models vs prose.
    """
    return {
        "error": error_type,
        "field": field,
        "expected": expected,
        "suggestions": suggestions or [],
        "format_note": (
            "Return this JSON structure from tool/wrapper error paths. "
            "Prose stack traces underperform structured responses by ~38pp on Anthropic models."
        ),
    }


def generate_retry_brief(evidence: str, cause: str) -> dict:
    """
    Generate a bounded retry brief for attempt N+1.
    arXiv:2605.08717: evidence-grounded brief + bounded guidance recovered 21.79% of failures.
    Ungrounded guidance does not improve recovery.
    """
    # M7 FIX: ground on content tokens only — strip stopwords before overlap check
    # "the error and the" would pass a raw word overlap; content tokens don't
    STOPWORDS = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "it", "its", "this", "that", "these", "those",
        "i", "we", "you", "he", "she", "they", "my", "our", "your", "their",
        "not", "no", "so", "if", "then", "when", "where", "which", "who",
    }
    evidence_tokens = {w for w in evidence.lower().split() if w not in STOPWORDS and len(w) > 2}
    cause_tokens = {w for w in cause.lower().split() if w not in STOPWORDS and len(w) > 2}
    overlap = evidence_tokens & cause_tokens
    grounded = len(overlap) >= 3  # at least 3 shared CONTENT words (not stopwords)

    brief = {
        "root_cause": cause,
        "evidence_grounded": grounded,
        "evidence_summary": evidence[:500] + "..." if len(evidence) > 500 else evidence,
        "retry_instructions": None,
        "warning": None,
    }

    if grounded:
        brief["retry_instructions"] = (
            f"Change specifically: {cause}. "
            "Do not retry the same approach. "
            "Stop if the same error recurs — escalate instead."
        )
    else:
        brief["warning"] = (
            "Root cause is NOT grounded in evidence terms. "
            "Ungrounded guidance does not improve recovery (arXiv:2605.08717). "
            "Provide specific evidence before generating a retry brief."
        )

    return brief


def main():
    parser = argparse.ArgumentParser(
        description="Recovery classifier for Hermes agent (arXiv:2508.07935, 2606.01416)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # classify: error -> exception type + recovery pattern
    cl = sub.add_parser("classify", help="Classify error and return recovery pattern")
    cl.add_argument("--error", type=str, required=True)
    cl.add_argument("--tool", type=str, default="")
    cl.add_argument("--attempt", type=int, default=1)

    # loop-check: detect looping trajectory
    lc = sub.add_parser("loop-check", help="Detect looping trajectory from history")
    lc.add_argument("--history", type=str, required=True, help="JSON array of {tool, args} dicts")

    # module: classify failed agent module
    mo = sub.add_parser("module", help="Classify which agent module caused failure")
    mo.add_argument("--trajectory", type=str, required=True)

    # brief: generate bounded retry brief
    br = sub.add_parser("brief", help="Generate bounded retry brief")
    br.add_argument("--evidence", type=str, required=True)
    br.add_argument("--cause", type=str, required=True)

    # format-error: format structured error for tool wrappers
    fe = sub.add_parser("format-error", help="Format structured error response")
    fe.add_argument("--error-type", type=str, required=True)
    fe.add_argument("--field", type=str, default=None)
    fe.add_argument("--expected", type=str, default=None)
    fe.add_argument("--suggestion", type=str, action="append", dest="suggestions", default=[])

    args = parser.parse_args()

    if args.command == "classify":
        result = classify_exception(args.error, args.tool, args.attempt)
        print(json.dumps(result, indent=2))
        sys.exit(result["exit_code"])

    elif args.command == "loop-check":
        history = json.loads(args.history)
        result = detect_loop(history)
        print(json.dumps(result, indent=2))
        sys.exit(result["exit_code"])

    elif args.command == "module":
        result = classify_module(args.trajectory)
        print(json.dumps(result, indent=2))
        sys.exit(0)

    elif args.command == "brief":
        result = generate_retry_brief(args.evidence, args.cause)
        print(json.dumps(result, indent=2))
        sys.exit(0 if result["evidence_grounded"] else 1)

    elif args.command == "format-error":
        result = format_structured_error(
            args.error_type, args.field, args.expected, args.suggestions
        )
        print(json.dumps(result, indent=2))
        sys.exit(0)


if __name__ == "__main__":
    main()
