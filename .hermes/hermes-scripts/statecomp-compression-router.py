#!/usr/bin/env python3
"""
statecomp-compression-router.py — StateComp-inspired compression timing router.

Based on: StateComp (arXiv:2609.27298) — State Conditioned Compression.
Wave 16 implementation: predicts whether past interactions are safe to compress
based on current agent state. Uses span+token gates to avoid compressing too early.

Key insight: separate readiness prediction from execution decision.
A positive router decision does NOT immediately trigger summarization;
it accumulates span candidates until gate thresholds are met.

Usage:
  python3 statecomp-compression-router.py --check SESSION_ID   # predict ready spans
  python3 statecomp-compression-router.py --stats               # compression stats
  python3 statecomp-compression-router.py --daemon              # cron mode
"""

from __future__ import annotations

import argparse
import json
import math
import os
import pathlib
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# -- Profile-aware paths ------------------------------------------------------
_HH = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_HP = os.environ.get("HERMES_PROFILE", "")
_RT = (_HH / "profiles" / _HP) if _HP else _HH
_CACHE = _RT / "cache"
_SESSIONS = _RT / "sessions"
_SCRIPTS = Path(__file__).parent

ROUTER_STATE = _CACHE / "statecomp-router-state.json"
STATS_FILE = _CACHE / "statecomp-stats.json"

# Gate thresholds (from StateComp paper)
SCORE_THRESHOLD = 0.62       # router readiness score to mark candidate
MIN_SPAN_LENGTH = 3          # min consecutive ready interactions to form a span
MIN_SOURCE_TOKENS = 800      # min tokens in span to justify summarization cost
MIN_READY_RATIO = 0.55       # fraction of span interactions that must be ready

# State features for readiness scoring (heuristic — no model available)
# Based on: reasoning externalized to file/tool/env feedback = ready to compress
EXTERNALIZATION_PATTERNS = [
    r'\bwrote to\b', r'\bsaved to\b', r'\bcommitted\b', r'\bfile written\b',
    r'\btest passed\b', r'\bexit code 0\b', r'\bsuccess\b', r'\bcompleted\b',
    r'\bpatched\b', r'\bdeployed\b', r'\binstalled\b', r'\bverified\b',
]
_EXT_RE = re.compile('|'.join(EXTERNALIZATION_PATTERNS), re.IGNORECASE)

LOW_ENTROPY_SIGNALS = [
    r'\byes\b', r'\bokay\b', r'\bdone\b', r'\bcorrect\b', r'\bunderstood\b',
    r'\backnowledged\b', r'\bconfirmed\b', r'\bno action needed\b',
]
_LOW_ENT_RE = re.compile('|'.join(LOW_ENTROPY_SIGNALS), re.IGNORECASE)


def _estimate_tokens(text: str) -> int:
    """Rough token estimate: chars / 4."""
    return max(1, len(text) // 4)


def _readiness_score(interaction: dict) -> float:
    """
    Heuristic readiness score for a single interaction.
    High score = reasoning has been externalized, safe to compress.
    Range: [0.0, 1.0]
    """
    content = str(interaction.get("content", "")) + str(interaction.get("result", ""))
    role = interaction.get("role", "")
    score = 0.3  # base

    # Tool results with success signals = high readiness
    if role in ("tool", "system"):
        score += 0.2

    # Externalization patterns found
    ext_hits = len(_EXT_RE.findall(content))
    score += min(0.3, ext_hits * 0.1)

    # Low-entropy content (short acks)
    if len(content.split()) < 30 and _LOW_ENT_RE.search(content):
        score += 0.2

    # Recency penalty (recent interactions less safe to compress)
    age_turns = interaction.get("age_turns", 0)
    if age_turns < 5:
        score -= 0.2

    return max(0.0, min(1.0, score))


def _load_session_interactions(session_id: str) -> list[dict]:
    """Load interactions from a session file."""
    candidates = list(_SESSIONS.glob(f"*{session_id}*")) if session_id != "latest" else []
    if not candidates:
        # Try latest session
        all_sessions = sorted(_SESSIONS.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not all_sessions:
            return []
        session_file = all_sessions[0]
    else:
        session_file = candidates[0]

    interactions = []
    try:
        lines = session_file.read_text(errors="ignore").splitlines()
        for i, line in enumerate(lines):
            try:
                obj = json.loads(line)
                obj["age_turns"] = len(lines) - i
                interactions.append(obj)
            except json.JSONDecodeError:
                continue
    except (OSError, PermissionError):
        pass
    return interactions


def _find_ready_spans(interactions: list[dict]) -> list[dict]:
    """
    Find consecutive spans of interactions ready for compression.
    Applies span-length gate and token-count gate before marking executable.
    """
    if not interactions:
        return []

    # Score each interaction
    scores = [(_readiness_score(ia), ia) for ia in interactions]

    # Find consecutive ready interactions (score >= threshold)
    ready_flags = [s >= SCORE_THRESHOLD for s, _ in scores]

    # Build spans of consecutive ready interactions
    spans = []
    i = 0
    while i < len(ready_flags):
        if ready_flags[i]:
            j = i
            while j < len(ready_flags) and ready_flags[j]:
                j += 1
            span_interactions = interactions[i:j]
            span_scores = [s for s, _ in scores[i:j]]
            spans.append({
                "start": i,
                "end": j,
                "length": j - i,
                "interactions": span_interactions,
                "avg_score": sum(span_scores) / len(span_scores),
                "ready_ratio": sum(1 for s in span_scores if s >= SCORE_THRESHOLD) / len(span_scores),
                "token_estimate": sum(_estimate_tokens(str(ia)) for ia in span_interactions),
            })
            i = j
        else:
            i += 1

    # Apply gates
    executable_spans = []
    for span in spans:
        passes_length = span["length"] >= MIN_SPAN_LENGTH
        passes_tokens = span["token_estimate"] >= MIN_SOURCE_TOKENS
        passes_ratio = span["ready_ratio"] >= MIN_READY_RATIO

        span["executable"] = passes_length and passes_tokens and passes_ratio
        span["gate_failures"] = []
        if not passes_length:
            span["gate_failures"].append(f"span_length={span['length']}<{MIN_SPAN_LENGTH}")
        if not passes_tokens:
            span["gate_failures"].append(f"tokens={span['token_estimate']}<{MIN_SOURCE_TOKENS}")
        if not passes_ratio:
            span["gate_failures"].append(f"ready_ratio={span['ready_ratio']:.2f}<{MIN_READY_RATIO}")

        executable_spans.append(span)

    return executable_spans


def cmd_check(session_id: str) -> int:
    """Check a session and report compression-ready spans."""
    interactions = _load_session_interactions(session_id)
    if not interactions:
        print(f"[statecomp] No interactions found for session: {session_id}")
        return 0

    spans = _find_ready_spans(interactions)
    executable = [s for s in spans if s["executable"]]

    print(f"[statecomp] Session: {session_id}")
    print(f"[statecomp] Total interactions: {len(interactions)}")
    print(f"[statecomp] Candidate spans: {len(spans)}, executable: {len(executable)}")

    for i, span in enumerate(executable):
        print(f"  Span {i}: turns {span['start']}-{span['end']} "
              f"({span['length']} turns, ~{span['token_estimate']} tokens, "
              f"score={span['avg_score']:.2f})")

    # Save state
    _CACHE.mkdir(parents=True, exist_ok=True)
    state = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "session_id": session_id,
        "total_interactions": len(interactions),
        "candidate_spans": len(spans),
        "executable_spans": len(executable),
        "spans": [{k: v for k, v in s.items() if k != "interactions"}
                  for s in executable],
    }
    tmp = ROUTER_STATE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2))
    tmp.replace(ROUTER_STATE)

    return 0


def cmd_stats() -> int:
    """Show compression router stats."""
    if not ROUTER_STATE.exists():
        print("[statecomp] No router state found. Run --check first.")
        return 0
    state = json.loads(ROUTER_STATE.read_text())
    print(f"[statecomp] Last run: {state.get('ts', 'unknown')}")
    print(f"[statecomp] Session: {state.get('session_id', '?')}")
    print(f"[statecomp] Executable spans: {state.get('executable_spans', 0)}")
    spans = state.get("spans", [])
    total_tokens = sum(s.get("token_estimate", 0) for s in spans)
    print(f"[statecomp] Compressible tokens: ~{total_tokens}")
    return 0


def cmd_daemon() -> int:
    """Cron mode: check latest session and report."""
    return cmd_check("latest")


def main() -> int:
    ap = argparse.ArgumentParser(description="StateComp compression timing router")
    ap.add_argument("--check", metavar="SESSION_ID", help="Check a session for ready spans")
    ap.add_argument("--stats", action="store_true", help="Show compression stats")
    ap.add_argument("--daemon", action="store_true", help="Cron daemon mode")
    args = ap.parse_args()

    if args.check:
        return cmd_check(args.check)
    if args.stats:
        return cmd_stats()
    if args.daemon:
        return cmd_daemon()
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
