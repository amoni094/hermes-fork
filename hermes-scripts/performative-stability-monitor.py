#!/usr/bin/python3
"""
performative-stability-monitor.py

Detects when Hermes' tool-selection policies create feedback loops that
shift task distributions in ways that invalidate prior routing decisions
(performative prediction instability).

Math basis: Performative stability (fixed-point of prediction-induced distribution)
  A predictor h is performatively stable if:
    h = argmin_h E_{D(h)}[loss(h, z)]
  where D(h) is the distribution INDUCED by deploying h.
  
  Instability: h changes the task distribution D, which changes what h
  should predict, which changes h again → oscillating routing policies.
  
  Detected by tracking whether the tool distribution in recent sessions
  is drifting systematically (Jensen-Shannon divergence between consecutive
  windows > DRIFT_THRESHOLD).

Runs as a monitor in the suite.
"""
from __future__ import annotations

import json
import math
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

HOME         = Path.home()
SESSIONS_DIR = HOME / ".hermes/sessions"
CACHE_DIR    = HOME / ".hermes/cache/monitors"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE     = CACHE_DIR / "performative-stability.json"

DRIFT_THRESHOLD = 0.30   # JSD between windows; above = unstable
MIN_TOOLS_PER_WINDOW = 10
HALF_WINDOW = 3          # sessions per comparison window


def _tool_counts(sessions: list[Path]) -> Counter:
    counts: Counter = Counter()
    for sess in sessions:
        try:
            data = json.loads(sess.read_text())
            msgs = data if isinstance(data, list) else data.get("messages", [])
            for m in msgs:
                if not isinstance(m, dict) or m.get("role") != "assistant":
                    continue
                for b in (m.get("content", []) if isinstance(m.get("content"), list) else []):
                    if isinstance(b, dict) and b.get("type") == "tool_use":
                        counts[b.get("name", "unknown")] += 1
        except Exception:
            pass
    return counts


def _jsd(p: dict, q: dict) -> float:
    """Jensen-Shannon divergence between two tool-count dicts."""
    vocab = set(p) | set(q)
    if not vocab:
        return 0.0
    tp = sum(p.values()) or 1
    tq = sum(q.values()) or 1
    pv = {k: p.get(k, 0) / tp for k in vocab}
    qv = {k: q.get(k, 0) / tq for k in vocab}
    mv = {k: 0.5 * (pv[k] + qv[k]) for k in vocab}

    def _kl(a, b):
        return sum(av * math.log2(av / bv) for k in vocab
                   if (av := a.get(k, 0)) > 0 and (bv := b.get(k, 0)) > 0)

    return 0.5 * _kl(pv, mv) + 0.5 * _kl(qv, mv)


def run() -> int:
    now = datetime.now(timezone.utc).isoformat()
    print(f"\n=== Performative Stability Monitor — {now[:10]} ===\n")

    if not SESSIONS_DIR.exists():
        print("ALARM: no — no sessions directory")
        return 0

    sessions = sorted(SESSIONS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime)
    if len(sessions) < HALF_WINDOW * 2:
        print(f"Need {HALF_WINDOW * 2} sessions, have {len(sessions)}")
        print("ALARM: no — insufficient data")
        return 0

    # Split into two consecutive windows
    mid    = len(sessions) // 2
    early  = sessions[max(0, mid - HALF_WINDOW):mid]
    recent = sessions[mid:mid + HALF_WINDOW]

    counts_e = _tool_counts(early)
    counts_r = _tool_counts(recent)

    te = sum(counts_e.values())
    tr = sum(counts_r.values())

    if te < MIN_TOOLS_PER_WINDOW or tr < MIN_TOOLS_PER_WINDOW:
        print(f"Tool calls: early={te}, recent={tr} (need {MIN_TOOLS_PER_WINDOW} each)")
        print("ALARM: no — insufficient tool call data")
        return 0

    jsd   = _jsd(counts_e, counts_r)
    alarm = jsd > DRIFT_THRESHOLD

    print(f"Early window:  {te} calls across {len(early)} sessions")
    print(f"Recent window: {tr} calls across {len(recent)} sessions")
    print(f"JSD drift:     {jsd:.4f}  (threshold={DRIFT_THRESHOLD})")

    # Top-5 shifted tools
    all_tools = set(counts_e) | set(counts_r)
    shifts = sorted(
        all_tools,
        key=lambda t: abs(counts_r.get(t, 0) / max(tr, 1) - counts_e.get(t, 0) / max(te, 1)),
        reverse=True,
    )
    print("\nTop shifted tools:")
    for t in shifts[:5]:
        se = counts_e.get(t, 0) / te
        sr = counts_r.get(t, 0) / tr
        print(f"  {t:<35} early={se:.3f} recent={sr:.3f} Δ={sr-se:+.3f}")

    if alarm:
        print(f"\nALARM: yes — performative drift JSD={jsd:.4f} > {DRIFT_THRESHOLD}")
        print("  Routing policy may be creating unstable feedback loops")
    else:
        print(f"\nALARM: no — tool distribution stable (JSD={jsd:.4f})")

    OUT_FILE.write_text(json.dumps({
        "ts": now, "jsd": round(jsd, 6),
        "early_calls": te, "recent_calls": tr,
        "threshold": DRIFT_THRESHOLD,
    }, indent=2))
    return 1 if alarm else 0


if __name__ == "__main__":
    sys.exit(run())
