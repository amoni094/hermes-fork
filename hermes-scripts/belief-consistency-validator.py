#!/usr/bin/python3
"""
belief-consistency-validator.py

Provides empirical grounds for deciding whether to reify internal agent
belief states — validates that observed LLM behavior is consistent with
a stable underlying belief model rather than random or incoherent.

CS SPIKE basis (Beliefs and Behavior in Language Models, arXiv:2609.11018):
Applies latent belief variable inference to Hermes tool-call sequences.
A Hermes session is consistent if the tool selections, query patterns,
and skill choices can be explained by a single coherent "intent vector"
that remains stable across the session.

Math basis: belief consistency as fixed-point of intent inference
  Define intent_t = f(tool_calls_{0..t}) — the running belief estimate.
  Consistency condition: ||intent_t - intent_{t-1}|| < ε for all t > warm-up
  
  If intent drifts monotonically → task scope creep
  If intent oscillates → incoherent session / context confusion
  If intent is stable → well-formed session with consistent goal

Features:
  - Extracts intent signatures from tool name sequences (no LLM)
  - Detects monotonic drift, oscillation, and stability
  - Flags sessions where belief consistency < threshold
  - Outputs per-session consistency score and drift classification

Usage:
  python3 belief-consistency-validator.py [--dry-run]
  python3 belief-consistency-validator.py --session 20260915_...
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

HOME         = Path.home()
SESSIONS_DIR = HOME / ".hermes/profiles/fork/sessions"
CACHE_DIR    = HOME / ".hermes/cache/monitors"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE     = CACHE_DIR / "belief-consistency-report.json"

CONSISTENCY_THRESHOLD = 0.70   # sessions below this are flagged
WARMUP_STEPS          = 2      # ignore first N steps in drift analysis
OSCILLATION_RATIO     = 0.4    # if sign changes > 40% of steps → oscillation


# Tool intent categories (dimensionality of the belief space)
INTENT_DIMS = {
    "research":      ["web_search", "web_extract", "arxiv"],
    "implementation":["write_file", "patch", "execute_code"],
    "verification":  ["terminal", "read_file", "search_files"],
    "delegation":    ["delegate_task", "browser_exec"],
    "memory_mgmt":   ["memory", "skill_view", "skill_manage"],
    "interaction":   ["clarify", "text_to_speech", "vision_analyze"],
}
DIM_NAMES = list(INTENT_DIMS.keys())
N_DIMS    = len(DIM_NAMES)


def _tool_to_intent_vec(tool: str) -> np.ndarray:
    v = np.zeros(N_DIMS)
    for i, (dim, tools) in enumerate(INTENT_DIMS.items()):
        if any(t in tool for t in tools):
            v[i] = 1.0
    return v


def _extract_tool_sequence(session_path: Path) -> list[str]:
    tools = []
    for line in session_path.read_text().splitlines():
        try:
            ev = json.loads(line)
            if ev.get("role") != "assistant":
                continue
            content = ev.get("content", ev.get("api_content", ""))
            if isinstance(content, str):
                for m in re.finditer(r'"name"\s*:\s*"([^"]+)"', content):
                    tools.append(m.group(1))
            elif isinstance(content, list):
                for b in content:
                    if isinstance(b, dict) and b.get("type") == "tool_use":
                        tools.append(b.get("name", "unknown"))
        except Exception:
            pass
    return tools


def _running_intent(tools: list[str]) -> list[np.ndarray]:
    """Compute running cumulative intent vector (normalised)."""
    cum = np.zeros(N_DIMS)
    intents = []
    for t in tools:
        cum = cum + _tool_to_intent_vec(t)
        norm = np.linalg.norm(cum)
        intents.append(cum / norm if norm > 0 else cum.copy())
    return intents


def _consistency_score(intents: list[np.ndarray]) -> tuple[float, str]:
    """
    Compute consistency score ∈ [0,1] and classify drift pattern.
    Higher = more consistent.
    """
    if len(intents) <= WARMUP_STEPS:
        return 1.0, "insufficient_data"

    post_warmup = intents[WARMUP_STEPS:]
    if len(post_warmup) < 2:
        return 1.0, "insufficient_data"

    # Compute step-wise drift: ||intent_t - intent_{t-1}||
    drifts = [np.linalg.norm(post_warmup[i] - post_warmup[i-1])
               for i in range(1, len(post_warmup))]

    mean_drift = float(np.mean(drifts))
    # Score: 1 - normalised mean drift (drift ∈ [0, √2])
    score = max(0.0, 1.0 - mean_drift / 1.414)

    # Classify: check sign changes in primary dimension
    primary = np.argmax(post_warmup[-1])
    primary_series = [v[primary] for v in post_warmup]
    diffs = np.diff(primary_series)
    sign_changes = int(np.sum(np.diff(np.sign(diffs)) != 0)) if len(diffs) > 1 else 0
    sign_ratio = sign_changes / max(len(diffs) - 1, 1)

    # Check monotonic drift
    is_monotone = all(d >= 0 for d in diffs) or all(d <= 0 for d in diffs)

    if score > CONSISTENCY_THRESHOLD:
        pattern = "stable"
    elif sign_ratio > OSCILLATION_RATIO:
        pattern = "oscillating"
    elif is_monotone:
        pattern = "scope_drift"
    else:
        pattern = "incoherent"

    return round(score, 4), pattern


def run_monitor(session_filter: str | None, dry_run: bool) -> int:
    now    = datetime.now(timezone.utc).isoformat()
    alarms: list[str] = []
    results: list[dict] = []

    if session_filter:
        paths = list(SESSIONS_DIR.glob(f"*{session_filter}*.jsonl"))
    else:
        paths = sorted(SESSIONS_DIR.glob("*.jsonl"))[-15:]

    print(f"[belief-consistency] Analysing {len(paths)} session(s)")

    for p in paths:
        tools = _extract_tool_sequence(p)
        if len(tools) < 3:
            continue

        intents = _running_intent(tools)
        score, pattern = _consistency_score(intents)
        final_intent = DIM_NAMES[int(np.argmax(intents[-1]))] if intents else "unknown"

        alarm = score < CONSISTENCY_THRESHOLD
        if alarm:
            alarms.append(
                f"INCONSISTENT: session {p.stem[:16]} score={score:.3f} pattern={pattern} "
                f"dominant_intent={final_intent} ({len(tools)} tool calls)"
            )

        results.append({
            "session":        p.stem,
            "n_tools":        len(tools),
            "consistency":    score,
            "pattern":        pattern,
            "dominant_intent": final_intent,
            "alarm":          alarm,
        })

    print(f"\n=== Belief Consistency Validator — {now[:10]} ===")
    if not results:
        print("  No sessions with sufficient tool calls (need ≥3)")
        print("\nALARM: no — insufficient data")
        return 0

    for r in results:
        flag = "  ALARM" if r["alarm"] else "OK"
        print(f"  [{flag}] {r['session'][:20]}: tools={r['n_tools']} "
              f"consistency={r['consistency']:.3f} pattern={r['pattern']} "
              f"intent={r['dominant_intent']}")

    if alarms:
        print(f"\nALARM: yes — {len(alarms)} inconsistent session(s):")
        for a in alarms:
            print(f"  {a}")
        alarm_exit = 1
    else:
        print("\nALARM: no — all sessions show consistent belief states")
        alarm_exit = 0

    if not dry_run:
        OUT_FILE.write_text(json.dumps({
            "ts": now, "sessions": results, "alarms": alarms,
        }, indent=2))
        print(f"\nWritten: {OUT_FILE}")

    return alarm_exit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--session", default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    import sys
    sys.exit(run_monitor(session_filter=args.session, dry_run=args.dry_run))


if __name__ == "__main__":
    main()
