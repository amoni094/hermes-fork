#!/usr/bin/python3
"""
quantization-state-divergence-monitor.py

Detects when Hermes's internal state representations have drifted due to
context compression / quantization events, by measuring the KL divergence
between the current tool-call distribution and the pre-compression baseline.

Math basis (generalization_theory / information_geometry): quantization of
a continuous distribution to a discrete one incurs a distortion D >= R^{-1}(I)
where R is the rate-distortion function. For Hermes context compression
(lambda-tuner), each compression event introduces a quantization step.
The cumulative KL divergence between the original and reconstructed state
is a lower bound on the information lost.

Concretely:
  - Baseline: tool-call distribution from the first N turns of a session
  - Current:  tool-call distribution from the most recent N turns
  - Metric:   KL(current || baseline) — measures state drift post-compression
  - Alarm:    KL > threshold (state has diverged beyond recoverable distortion)

This complements session-stability-monitor.py (which uses Lyapunov V_t) with
a direct information-theoretic measure of compression distortion.
"""

from __future__ import annotations

import argparse
import json
import math
import sqlite3
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

HOME      = Path.home()
SESSIONS  = HOME / ".hermes/sessions"
FORK_SESSIONS = HOME / ".hermes/profiles/fork/sessions"  # fork-profile sessions

CACHE_DIR = HOME / ".hermes/cache/monitors"
STATE_DB  = HOME / ".hermes/memory-facts/stability.db"
ALARM_FILE = CACHE_DIR / "quantization-divergence-alarm.json"
OUT_FILE   = CACHE_DIR / "quantization-divergence.json"

CACHE_DIR.mkdir(parents=True, exist_ok=True)

BASELINE_WINDOW = 10   # first N tool calls = baseline
CURRENT_WINDOW  = 10   # last N tool calls = current
KL_THRESHOLD    = 1.0  # nats; above = significant state drift
SMOOTHING       = 0.01


def _extract_tools(text: str) -> list[str]:
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


def _kl_div(p: Counter, q: Counter) -> float:
    """KL(P || Q) with Laplace smoothing."""
    vocab = set(p) | set(q)
    n_p = sum(p.values()) + SMOOTHING * len(vocab)
    n_q = sum(q.values()) + SMOOTHING * len(vocab)
    kl = 0.0
    for t in vocab:
        pp = (p.get(t, 0) + SMOOTHING) / n_p
        qq = (q.get(t, 0) + SMOOTHING) / n_q
        kl += pp * math.log(pp / qq)
    return kl


def analyse_session(path: Path) -> dict | None:
    try:
        text = path.read_text()
    except Exception:
        return None
    tools = _extract_tools(text)
    if len(tools) < BASELINE_WINDOW + CURRENT_WINDOW:
        return None

    baseline = Counter(tools[:BASELINE_WINDOW])
    current  = Counter(tools[-CURRENT_WINDOW:])
    kl = _kl_div(current, baseline)

    return {
        "session":  path.stem[:20],
        "n_tools":  len(tools),
        "baseline_top": baseline.most_common(3),
        "current_top":  current.most_common(3),
        "kl_divergence": round(kl, 4),
        "alarm": kl > KL_THRESHOLD,
    }


def run(dry_run: bool = False) -> None:
    now = datetime.now(timezone.utc).isoformat()
    session_files = sorted([f for d in [SESSIONS, FORK_SESSIONS] if d.exists() for f in d.glob("*.jsonl")])

    results: list[dict] = []
    alarms:  list[dict] = []

    for sf in session_files:
        r = analyse_session(sf)
        if r is None:
            continue
        results.append(r)
        if r["alarm"]:
            alarms.append(r)

    print(f"\n=== Quantization State Divergence Monitor — {now[:10]} ===")
    print(f"Sessions analysed:  {len(results)}")
    print(f"Diverged sessions:  {len(alarms)}")

    if results:
        mean_kl = sum(r["kl_divergence"] for r in results) / len(results)
        print(f"Mean KL divergence: {mean_kl:.4f} nats  (threshold={KL_THRESHOLD})")
        for r in sorted(results, key=lambda x: -x["kl_divergence"])[:5]:
            tag = " <-- ALARM" if r["alarm"] else ""
            print(f"  {r['session']}  KL={r['kl_divergence']:.4f}  "
                  f"n={r['n_tools']}{tag}")
            if r["alarm"]:
                base = [t for t, _ in r["baseline_top"]]
                curr = [t for t, _ in r["current_top"]]
                print(f"    baseline: {base}  →  current: {curr}")
    else:
        print("No sessions long enough to analyse (need ≥20 tool calls).")

    if not dry_run:
        out = {
            "ts": now,
            "sessions_analysed": len(results),
            "alarms": len(alarms),
            "detail": results,
        }
        OUT_FILE.write_text(json.dumps(out, indent=2))
        if alarms:
            ALARM_FILE.write_text(json.dumps(alarms, indent=2))
            print(f"ALARM: yes — {len(alarms)} session(s) KL divergence above threshold")
        else:
            print("ALARM: no — all sessions within KL threshold")
        print(f"Written: {OUT_FILE}")
    else:
        print("(dry-run)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Quantization state divergence monitor")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
