#!/usr/bin/python3
"""
regime-transition-monitor.py

Detects when the agent's operational regime has shifted — from research to
coding to debugging to review — using a hidden Markov model over tool-call
sequences. Regime transitions that are abrupt or unplanned indicate context
fragmentation.

Math basis (dynamical_systems / stochastic_causal): the qualitative theory
of dynamical systems identifies regime transitions as bifurcation events where
a system crosses a separatrix. Concretely: estimate the steady-state tool-call
distribution per session (the "regime"), compare adjacent windows via KL
divergence, and flag abrupt rises (KL > threshold) as regime transitions.

For Hermes:
  - State = distribution over tool names in a rolling window of N tool calls
  - Transition metric = KL(P_current || P_reference) across windows
  - A high KL transition within a single session signals context fragmentation
    (agent switching tasks without completing current one)
  - A high KL transition between sessions signals the user has shifted domains
    (useful for warm-start routing: load different skills)
"""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

HOME      = Path.home()
SESSIONS  = HOME / ".hermes/sessions"
FORK_SESSIONS = HOME / ".hermes/profiles/fork/sessions"  # fork-profile sessions

CACHE_DIR = HOME / ".hermes/cache/monitors"
ALARM_FILE = CACHE_DIR / "regime-transition-alarm.json"
OUT_FILE   = CACHE_DIR / "regime-transitions.json"

CACHE_DIR.mkdir(parents=True, exist_ok=True)

WINDOW_SIZE = 20       # tool calls per window
KL_THRESHOLD = 0.8    # nats; above = regime transition
SMOOTHING = 0.01      # Laplace smoothing


def _extract_tools(text: str) -> list[str]:
    """Extract ordered list of tool names from a session JSONL."""
    tools: list[str] = []
    for line in text.split("\n"):
        try:
            obj = json.loads(line)
            if obj.get("role") == "assistant":
                for tc in obj.get("tool_calls", []):
                    if isinstance(tc, dict):
                        name = tc.get("function", {}).get("name", "")
                        if name:
                            tools.append(name)
        except Exception:
            pass
    return tools


def _window_dist(tools: list[str]) -> Counter:
    return Counter(tools)


def _kl_div(p: Counter, q: Counter, vocab: set[str]) -> float:
    """KL(P || Q) with Laplace smoothing."""
    total_p = sum(p.values()) + SMOOTHING * len(vocab)
    total_q = sum(q.values()) + SMOOTHING * len(vocab)
    kl = 0.0
    for t in vocab:
        pp = (p.get(t, 0) + SMOOTHING) / total_p
        qq = (q.get(t, 0) + SMOOTHING) / total_q
        kl += pp * math.log(pp / qq)
    return kl


def analyse_session(path: Path) -> dict | None:
    try:
        text = path.read_text()
    except Exception:
        return None
    tools = _extract_tools(text)
    if len(tools) < WINDOW_SIZE * 2:
        return None

    # Slide windows
    transitions: list[dict] = []
    vocab: set[str] = set(tools)
    prev_win = _window_dist(tools[:WINDOW_SIZE])

    for start in range(WINDOW_SIZE, len(tools) - WINDOW_SIZE, WINDOW_SIZE // 2):
        curr_win = _window_dist(tools[start:start + WINDOW_SIZE])
        kl = _kl_div(curr_win, prev_win, vocab)
        if kl > KL_THRESHOLD:
            transitions.append({
                "position": start,
                "kl": round(kl, 4),
                "from_top": prev_win.most_common(3),
                "to_top":   curr_win.most_common(3),
            })
        prev_win = curr_win

    return {
        "session": path.stem[:20],
        "total_tools": len(tools),
        "transitions": transitions,
        "fragmented": len(transitions) > 2,
    }


def run(dry_run: bool = False) -> None:
    now = datetime.now(timezone.utc).isoformat()
    session_files = sorted([f for d in [SESSIONS, FORK_SESSIONS] if d.exists() for f in d.glob("*.jsonl")])

    results: list[dict] = []
    fragmented: list[str] = []

    for sf in session_files:
        r = analyse_session(sf)
        if r is None:
            continue
        results.append(r)
        if r["fragmented"]:
            fragmented.append(r["session"])

    print(f"\n=== Regime Transition Monitor — {now[:10]} ===")
    print(f"Sessions analysed: {len(results)}")
    print(f"Fragmented sessions (>2 regime shifts): {len(fragmented)}")

    if results:
        all_trans = sum(len(r["transitions"]) for r in results)
        print(f"Total regime transitions detected: {all_trans}")
        # Show top fragmented
        top = sorted(results, key=lambda r: -len(r["transitions"]))[:5]
        if top[0]["transitions"]:
            print("\nMost fragmented sessions:")
            for r in top:
                if not r["transitions"]:
                    break
                print(f"  {r['session']}  {len(r['transitions'])} transitions  "
                      f"({r['total_tools']} tools total)")
                for t in r["transitions"][:2]:
                    from_tools = [x[0] for x in t["from_top"]]
                    to_tools   = [x[0] for x in t["to_top"]]
                    print(f"    @pos {t['position']:4d}  KL={t['kl']:.3f}  "
                          f"{from_tools} → {to_tools}")

    if not dry_run and results:
        out = {
            "ts": now,
            "sessions_analysed": len(results),
            "fragmented_count": len(fragmented),
            "fragmented_sessions": fragmented,
            "detail": results,
        }
        OUT_FILE.write_text(json.dumps(out, indent=2))
        print(f"\nWritten: {OUT_FILE}")
        if fragmented:
            ALARM_FILE.write_text(json.dumps({"ts": now, "fragmented": fragmented}, indent=2))
            print(f"ALARM: yes — {len(fragmented)} fragmented session(s)")
        else:
            print("ALARM: no — no fragmented sessions detected")
    elif dry_run:
        print("(dry-run)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Regime transition monitor")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
