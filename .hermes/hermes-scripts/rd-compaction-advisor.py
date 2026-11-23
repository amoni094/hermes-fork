#!/usr/bin/env python3
"""Rate-distortion-*shaped* compaction aggressiveness advisor.

For Gaussian sources R(D) = (1/2) log(σ²/D). LLM tokens are not Gaussian
samples; we do not compute R(D). We borrow the *shape*: tighter remaining
budget → accept more distortion (more aggressive summaries).

Usage:
    python3 rd-compaction-advisor.py --current-tokens 85000
    python3 rd-compaction-advisor.py --current-tokens 85000 --threshold 120000

Output: JSON with aggressiveness in [0,1], recommended focus_topic_prefix, rationale.

Integration (not wired): print JSON and, if a caller wants, prepend
focus_topic_prefix to a compress() / /compress focus_topic. There is no
run_compress_context() symbol in Hermes. Log scraping is best-effort only
and disabled unless --from-log is set.

Curve (k=3, conservative):
    remaining = 1 - min(current/threshold, 1)
    aggressiveness = exp(-k * remaining)
    remaining=1 (empty) → ~0.05 minimal
    remaining=0 (at/over threshold) → 1.0 aggressive
    aggressive (>=0.75) only when remaining ≲ 0.10
"""
from __future__ import annotations
import argparse
import json
import math
import os
import re
import sys
from pathlib import Path

HERMES_HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))


def _read_config_compression() -> dict:
    """Read compression.threshold_tokens from ~/.hermes/config.yaml."""
    config_path = HERMES_HOME / "config.yaml"
    if not config_path.exists():
        return {}
    try:
        text = config_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return {}
    try:
        import yaml  # type: ignore
        data = yaml.safe_load(text) or {}
        sec = data.get("compression") if isinstance(data, dict) else None
        if isinstance(sec, dict) and "threshold_tokens" in sec:
            return {"threshold_tokens": int(sec["threshold_tokens"])}
    except Exception:
        pass
    # Anchored so we do not match micro_compact_defrag_threshold_tokens.
    m = re.search(r"(?m)^[ \t]*threshold_tokens:[ \t]*(\d+)\s*$", text)
    if m:
        return {"threshold_tokens": int(m.group(1))}
    return {}


def compute_aggressiveness(
    current_tokens: int, threshold_tokens: int, k: float = 3.0
) -> dict:
    """Map budget usage to a conservative aggressiveness in [0, 1]."""
    current_tokens = max(int(current_tokens), 0)
    threshold_tokens = max(int(threshold_tokens), 1)
    if k <= 0:
        k = 3.0

    budget_fraction = min(current_tokens / threshold_tokens, 1.0)
    remaining_fraction = max(1.0 - budget_fraction, 0.0)

    # Conservative: stay gentle until the window is nearly full.
    # exp(-k * remaining): remaining=1 → e^{-k}≈0.05; remaining=0 → 1.
    aggressiveness = math.exp(-k * remaining_fraction)

    if aggressiveness < 0.25:
        level = "minimal"
        focus_prefix = "Preserve as much verbatim detail as possible."
    elif aggressiveness < 0.50:
        level = "light"
        focus_prefix = "Summarise older tool results but keep key decisions and outputs."
    elif aggressiveness < 0.75:
        level = "moderate"
        focus_prefix = "Aggressively summarise tool outputs; preserve user decisions and errors."
    else:
        level = "aggressive"
        focus_prefix = "Maximally compress: keep only task state, decisions, and error resolutions."

    return {
        "current_tokens": current_tokens,
        "threshold_tokens": threshold_tokens,
        "budget_fraction": round(budget_fraction, 3),
        "remaining_fraction": round(remaining_fraction, 3),
        "aggressiveness": round(aggressiveness, 3),
        "level": level,
        "focus_topic_prefix": focus_prefix,
        "rationale": (
            f"Context at {100 * budget_fraction:.0f}% of threshold "
            f"({current_tokens:,}/{threshold_tokens:,} tokens). "
            f"R(D)-shaped curve aggressiveness=exp(-{k}*remaining) → "
            f"{aggressiveness:.2f} ({level}). "
            f"Remaining headroom: {100 * remaining_fraction:.0f}%. "
            f"Not a Gaussian R(D) evaluation."
        ),
    }


def _current_from_log() -> int | None:
    """Best-effort: only explicit current/prompt/context token fields, not bare 'N tokens'."""
    log_path = HERMES_HOME / "logs" / "agent.log"
    if not log_path.exists():
        return None
    try:
        size = os.path.getsize(log_path)
        with open(log_path, "rb") as f:
            f.seek(max(0, size - 50000))
            tail = f.read().decode("utf-8", errors="replace")
    except OSError:
        return None
    matches = re.findall(
        r"(?:prompt_tokens|context_tokens|current_tokens|approx_tokens)[=:\s]+(\d{3,8})",
        tail,
        flags=re.I,
    )
    if not matches:
        return None
    try:
        return int(matches[-1])
    except ValueError:
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Rate-distortion-shaped compaction advisor")
    parser.add_argument(
        "--current-tokens", type=int, default=None,
        help="Current token count (required unless --from-log)",
    )
    parser.add_argument(
        "--threshold", type=int, default=None,
        help="compression.threshold_tokens (reads config.yaml if omitted)",
    )
    parser.add_argument("--k", type=float, default=3.0, help="Curve shape (default 3.0)")
    parser.add_argument(
        "--from-log", action="store_true",
        help="Best-effort parse agent.log for prompt_tokens/context_tokens (unreliable)",
    )
    args = parser.parse_args()

    cfg = _read_config_compression()
    threshold = cfg.get("threshold_tokens", 120000) if args.threshold is None else args.threshold

    if args.current_tokens is not None:
        current = args.current_tokens
    elif args.from_log:
        found = _current_from_log()
        if found is None:
            print(json.dumps({
                "error": "Could not determine current token count from agent.log. Pass --current-tokens.",
            }))
            sys.exit(1)
        current = found
    else:
        print(json.dumps({
            "error": "Pass --current-tokens (or --from-log for a best-effort log parse).",
        }))
        sys.exit(1)

    result = compute_aggressiveness(current, threshold, k=args.k)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
