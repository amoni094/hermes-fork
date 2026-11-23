#!/usr/bin/env python3
"""
retention_consistency_check.py

Checks the last N retained assistant messages for semantic contradictions,
grounded in Harrison's resolution completeness theorem (Ch. 3):
  "If a set of clauses S is unsatisfiable, resolution derives the empty clause."

Hermes application: a contradictory retained set is always wrong — at least
one of the contradicting messages should be demoted.

Usage:
  python3 retention_consistency_check.py [--path PATH] [--n 10] [--demo]

Output: JSON report with all pairs checked and any contradictions detected.
"""

import argparse
import json
import sys
from itertools import combinations
from typing import Optional


# ---------------------------------------------------------------------------
# Stub: logprob_classify
# In production this would call an LLM with logprobs to detect contradictions.
# Signature is fixed; the stub returns a deterministic demo value.
# ---------------------------------------------------------------------------
def logprob_classify(
    text_a: str,
    text_b: str,
    hypothesis: str = "These two statements contradict each other.",
    model: str = "claude-3-haiku-20240307",
) -> dict:
    """
    Classify whether text_a and text_b contradict each other.

    Production implementation would:
      1. Construct a prompt: "Given A: {text_a}\\nGiven B: {text_b}\\n{hypothesis}"
      2. Sample with logprobs; compute P(yes) vs P(no).
      3. Return {"contradiction": bool, "confidence": float, "logprob_yes": float}

    Stub returns a fixed safe value (no contradiction) for demo mode.
    """
    # Demo stub — always returns no contradiction with low confidence
    return {
        "contradiction": False,
        "confidence": 0.05,
        "logprob_yes": -3.0,
        "logprob_no": -0.05,
        "model": model,
        "stub": True,
    }


# ---------------------------------------------------------------------------
# Demo data
# ---------------------------------------------------------------------------
DEMO_MESSAGES = [
    {"role": "assistant", "content": "The jev-compaction plugin retains user messages unconditionally."},
    {"role": "assistant", "content": "User messages are always preserved; they are never demoted."},
    {"role": "assistant", "content": "The EMA score for tool calls is capped at 1.0."},
    {"role": "assistant", "content": "EMA values can exceed 1.0 under heavy load."},  # ← contradiction with above
    {"role": "assistant", "content": "Resolution is refutation complete: if S is unsatisfiable, the empty clause is derivable."},
    {"role": "assistant", "content": "Herbrand's theorem reduces first-order satisfiability to propositional satisfiability."},
]

# Inject a known contradiction for demo validation
DEMO_CONTRADICTIONS = [(2, 3)]  # indices 2 and 3 above are seeded contradictions


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------
def load_messages_from_jsonl(path: str, n: int) -> list[dict]:
    """Load the last `n` assistant messages from a JSONL file."""
    messages = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            # Support both {"role": ..., "content": ...} and {"message": {...}}
            if isinstance(obj, dict):
                if obj.get("role") == "assistant":
                    messages.append(obj)
                elif "message" in obj and obj["message"].get("role") == "assistant":
                    messages.append(obj["message"])
    return messages[-n:]


def check_consistency(messages: list[dict], contradiction_threshold: float = 0.7) -> dict:
    """
    Check all pairs of messages for semantic contradictions.

    Returns a report dict with:
      - total_messages: int
      - pairs_checked: int
      - contradictions: list of dicts
      - pairs: list of dicts (full detail)
    """
    report = {
        "total_messages": len(messages),
        "pairs_checked": 0,
        "contradictions": [],
        "pairs": [],
    }

    pairs = list(combinations(range(len(messages)), 2))
    report["pairs_checked"] = len(pairs)

    for i, j in pairs:
        text_a = messages[i].get("content", "")
        text_b = messages[j].get("content", "")

        result = logprob_classify(text_a, text_b)
        is_contradiction = (
            result.get("contradiction", False)
            or result.get("confidence", 0.0) >= contradiction_threshold
        )

        pair_record = {
            "idx_a": i,
            "idx_b": j,
            "snippet_a": text_a[:120],
            "snippet_b": text_b[:120],
            "logprob_yes": result.get("logprob_yes"),
            "logprob_no": result.get("logprob_no"),
            "confidence": result.get("confidence"),
            "contradiction": is_contradiction,
            "stub": result.get("stub", False),
        }
        report["pairs"].append(pair_record)

        if is_contradiction:
            report["contradictions"].append(pair_record)

    return report


# ---------------------------------------------------------------------------
# Demo mode: inject seeded contradictions to show the report structure
# ---------------------------------------------------------------------------
def run_demo() -> dict:
    """
    Run on synthetic data with a seeded contradiction.
    Returns a report; always exits 0.
    """
    messages = DEMO_MESSAGES

    # Manually override the stub for the seeded contradiction pair
    report = {
        "total_messages": len(messages),
        "pairs_checked": 0,
        "contradictions": [],
        "pairs": [],
        "demo_mode": True,
        "note": (
            "Demo mode: logprob_classify stub is active. "
            "Pair (2,3) is seeded as a contradiction to illustrate report structure."
        ),
    }

    pairs = list(combinations(range(len(messages)), 2))
    report["pairs_checked"] = len(pairs)

    for i, j in pairs:
        text_a = messages[i].get("content", "")
        text_b = messages[j].get("content", "")

        # Seed contradiction for the known pair
        is_seeded = (i, j) in DEMO_CONTRADICTIONS
        if is_seeded:
            result = {
                "contradiction": True,
                "confidence": 0.92,
                "logprob_yes": -0.08,
                "logprob_no": -2.5,
                "stub": True,
                "seeded": True,
            }
        else:
            result = logprob_classify(text_a, text_b)

        is_contradiction = result.get("contradiction", False)

        pair_record = {
            "idx_a": i,
            "idx_b": j,
            "snippet_a": text_a[:120],
            "snippet_b": text_b[:120],
            "logprob_yes": result.get("logprob_yes"),
            "logprob_no": result.get("logprob_no"),
            "confidence": result.get("confidence"),
            "contradiction": is_contradiction,
            "stub": result.get("stub", False),
            "seeded": result.get("seeded", False),
        }
        report["pairs"].append(pair_record)

        if is_contradiction:
            report["contradictions"].append(pair_record)

    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Check retained assistant messages for semantic contradictions.\n"
            "Grounded in Resolution Completeness (Harrison Ch. 3, Robinson 1965):\n"
            "  if a set of clauses is unsatisfiable, resolution derives the empty clause.\n"
            "A contradictory retained set is always wrong — one side must be demoted."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--path",
        type=str,
        default=None,
        help="Path to a JSONL file containing retained messages. "
             "Each line: {\"role\": \"assistant\", \"content\": \"...\"}",
    )
    parser.add_argument(
        "--n",
        type=int,
        default=10,
        help="Number of most-recent assistant messages to check (default: 10).",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run on synthetic demo data with a seeded contradiction and exit 0.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.7,
        help="Contradiction confidence threshold (0-1, default: 0.7).",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        default=True,
        help="Pretty-print JSON output (default: True).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.demo:
        report = run_demo()
        indent = 2 if args.pretty else None
        print(json.dumps(report, indent=indent))
        n_contradictions = len(report.get("contradictions", []))
        print(
            f"\n# Demo complete: {report['pairs_checked']} pairs checked, "
            f"{n_contradictions} contradiction(s) found.",
            file=sys.stderr,
        )
        sys.exit(0)

    if args.path is None:
        # Default: demo mode when no path given
        print(
            "No --path provided. Running in demo mode. Use --path to supply a JSONL file.",
            file=sys.stderr,
        )
        report = run_demo()
    else:
        try:
            messages = load_messages_from_jsonl(args.path, args.n)
        except FileNotFoundError:
            print(f"ERROR: File not found: {args.path}", file=sys.stderr)
            sys.exit(1)

        if not messages:
            print("WARNING: No assistant messages found in file.", file=sys.stderr)
            report = {"total_messages": 0, "pairs_checked": 0, "contradictions": [], "pairs": []}
        else:
            report = check_consistency(messages, contradiction_threshold=args.threshold)

    indent = 2 if args.pretty else None
    print(json.dumps(report, indent=indent))

    n_contradictions = len(report.get("contradictions", []))
    print(
        f"# {report.get('total_messages', 0)} messages, "
        f"{report.get('pairs_checked', 0)} pairs checked, "
        f"{n_contradictions} contradiction(s) detected.",
        file=sys.stderr,
    )

    # Non-zero exit if contradictions found (useful for CI / cron alerting)
    sys.exit(1 if n_contradictions > 0 else 0)


if __name__ == "__main__":
    main()
