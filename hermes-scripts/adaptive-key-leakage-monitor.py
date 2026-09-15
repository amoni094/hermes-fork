#!/usr/bin/python3
"""
adaptive-key-leakage-monitor.py

Detects when skill-routing or memory-retrieval patterns indicate that
session-specific context (effectively a "key") is leaking across turns
in ways that could corrupt future routing decisions.

Math basis: Key leakage in adaptive channel coding
  A channel code leaks its key if the encoder's output distribution
  shifts in response to the key faster than the decoder can adapt.
  Operationally: if the distribution of tool-calls in the first half
  of a session is systematically predictable from the last turn's
  tool calls, the session has a strong "memory" that may be biasing
  future routing (leaking past context into new decisions).

  Measured as: mutual information proxy between last-turn tool and
  next-turn tool, via empirical joint frequency table.
  High MI (> LEAKAGE_THRESHOLD) = routing is over-anchored to recent tool history.

Runs as a monitor in the suite.
"""
from __future__ import annotations

import json
import math
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

HOME          = Path.home()
SESSIONS_DIR  = HOME / ".hermes/sessions"
FORK_SESSIONS = HOME / ".hermes/profiles/fork/sessions"
CACHE_DIR     = HOME / ".hermes/cache/monitors"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE      = CACHE_DIR / "adaptive-key-leakage.json"

LEAKAGE_THRESHOLD = 1.5   # nats; above = routing over-anchored to recent tool history
MIN_BIGRAMS       = 15    # need enough tool-call pairs to estimate MI
WINDOW            = 8     # sessions to analyse


def _load_tool_sequence(path: Path) -> list[str]:
    try:
        lines = path.read_text().strip().splitlines()
        if lines and lines[0].startswith("{") and len(lines) > 1:
            messages = [json.loads(l) for l in lines if l.strip()]
        else:
            data = json.loads(path.read_text())
            messages = data if isinstance(data, list) else data.get("messages", [])
    except Exception:
        return []
    seq = []
    for msg in messages:
        if not isinstance(msg, dict) or msg.get("role") != "assistant":
            continue
        for b in (msg.get("content", []) if isinstance(msg.get("content"), list) else []):
            if isinstance(b, dict) and b.get("type") == "tool_use":
                seq.append(b.get("name", "unknown"))
    return seq


def _mutual_information(seq: list[str]) -> float:
    """Empirical MI between consecutive tool calls I(T_t ; T_{t+1})."""
    if len(seq) < 2:
        return 0.0
    bigrams  = list(zip(seq[:-1], seq[1:]))
    n        = len(bigrams)
    joint    = Counter(bigrams)
    p_a      = Counter(a for a, _ in bigrams)
    p_b      = Counter(b for _, b in bigrams)

    mi = 0.0
    for (a, b), cnt in joint.items():
        p_ab = cnt / n
        p_a_ = p_a[a] / n
        p_b_ = p_b[b] / n
        if p_ab > 0 and p_a_ > 0 and p_b_ > 0:
            mi += p_ab * math.log(p_ab / (p_a_ * p_b_))
    return mi


def run() -> int:
    now = datetime.now(timezone.utc).isoformat()
    print(f"\n=== Adaptive Key Leakage Monitor — {now[:10]} ===\n")

    session_files = sorted(
        [f for d in [SESSIONS_DIR, FORK_SESSIONS] if d.exists()
         for f in d.glob("*.jsonl")],
        key=lambda p: p.stat().st_mtime
    )[-WINDOW:]

    if not session_files:
        print("ALARM: no — no session files found")
        return 0

    results = []
    for sf in session_files:
        seq = _load_tool_sequence(sf)
        if len(seq) < 4:
            continue
        bigrams = len(seq) - 1
        mi = _mutual_information(seq)
        results.append({
            "session": sf.stem[:40],
            "tool_calls": len(seq),
            "bigrams": bigrams,
            "mi_nats": round(mi, 4),
            "leaking": mi > LEAKAGE_THRESHOLD,
        })

    total_bigrams = sum(r["bigrams"] for r in results)
    if total_bigrams < MIN_BIGRAMS:
        print(f"Total tool-call pairs: {total_bigrams} (need {MIN_BIGRAMS})")
        print("ALARM: no — insufficient data")
        return 0

    print(f"{'Session':<42} {'Tools':>6} {'MI (nats)':>10}  Status")
    print("  " + "-" * 65)
    leaking = []
    for r in results:
        icon = "✗" if r["leaking"] else "✓"
        print(f"  {icon} {r['session']:<42} {r['tool_calls']:>6} {r['mi_nats']:>10.4f}  "
              f"{'LEAKING' if r['leaking'] else 'OK'}")
        if r["leaking"]:
            leaking.append(r)

    avg_mi = sum(r["mi_nats"] for r in results) / max(len(results), 1)
    print(f"\nSessions analysed: {len(results)}, Leaking: {len(leaking)}")
    print(f"Average MI: {avg_mi:.4f} nats  (threshold={LEAKAGE_THRESHOLD})")

    alarm = len(leaking) > 0
    if alarm:
        print(f"\nALARM: yes — {len(leaking)} session(s) show routing MI > {LEAKAGE_THRESHOLD} nats "
              f"(tool-selection over-anchored to recent history)")
    else:
        print(f"\nALARM: no — routing MI within bounds (avg={avg_mi:.4f} nats)")

    OUT_FILE.write_text(json.dumps({
        "ts": now, "sessions": len(results),
        "avg_mi": round(avg_mi, 6), "leaking_count": len(leaking),
        "threshold": LEAKAGE_THRESHOLD, "detail": results,
    }, indent=2))
    return 1 if alarm else 0


if __name__ == "__main__":
    sys.exit(run())
