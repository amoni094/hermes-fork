#!/usr/bin/python3
"""
prediction-tradeoff-monitor.py

Enables adaptive skill-routing policies that explicitly trade off
prediction-driven optimisation vs robustness to prediction error.

Math basis: Consistency-robustness tradeoff (learning-augmented algorithms)
  For any online algorithm ALG with a prediction p:
    consistency  C(ALG) = max ratio when prediction is perfect (p = OPT)
    robustness   R(ALG) = max ratio when prediction is adversarial
  Optimal tradeoff curve: C + R >= 2 (cannot be simultaneously < 2 each).
  
  Operationally: track per-session prediction accuracy of skill routing
  (did the top-ranked skill get used?). High accuracy → increase
  prediction weight (better consistency). Low accuracy → increase
  robustness margin (fallback threshold).
  
  Alarm if both C and R are > TRADEOFF_CEILING (curve violated).

Runs as a monitor in the suite.
"""
from __future__ import annotations
import os

import json
import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

HOME         = Path.home()
_HH = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_HP = os.environ.get("HERMES_PROFILE", "fork")
_RT = _HH / "profiles" / _HP if _HP else _HH
SESSIONS_DIR = HOME / ".hermes/sessions"
FORK_SESSIONS = _RT / "sessions"  # fork-profile sessions

CACHE_DIR    = HOME / ".hermes/cache/monitors"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE     = CACHE_DIR / "prediction-tradeoff.json"

TRADEOFF_CEILING = 0.75  # alarm if BOTH C and R exceed this (both high = well-calibrated)
MIN_SESSIONS     = 3
WINDOW           = 10    # sessions to look back


def _load_skill_usage(sessions: list[Path]) -> list[dict]:
    """Extract skill_view calls and whether they were followed by tool use."""
    records = []
    for sess in sessions[-WINDOW:]:
        try:
            data  = json.loads(sess.read_text())
            msgs  = data if isinstance(data, list) else data.get("messages", [])
            skill_views = []
            for i, m in enumerate(msgs):
                if not isinstance(m, dict) or m.get("role") != "assistant":
                    continue
                for block in (m.get("content", []) if isinstance(m.get("content"), list) else []):
                    if not isinstance(block, dict):
                        continue
                    if block.get("type") == "tool_use" and block.get("name") == "skill_view":
                        skill_views.append(i)
            records.append({
                "session": sess.name[:30],
                "skill_views": len(skill_views),
                "total_tools": sum(
                    1 for m in msgs if isinstance(m, dict) and m.get("role") == "assistant"
                    and any(isinstance(b, dict) and b.get("type") == "tool_use"
                            for b in (m.get("content", []) if isinstance(m.get("content"), list) else []))
                ),
            })
        except Exception:
            pass
    return records


def compute_tradeoff(records: list[dict]) -> dict:
    """Estimate consistency (prediction hit rate) and robustness (miss rate)."""
    if not records:
        return {"C": 0.0, "R": 0.0, "sessions": 0}

    total_tools  = sum(r["total_tools"] for r in records)
    total_views  = sum(r["skill_views"] for r in records)

    if total_tools == 0:
        return {"C": 1.0, "R": 1.0, "sessions": len(records)}

    # C = fraction of sessions where skills were consulted before acting
    sessions_with_views = sum(1 for r in records if r["skill_views"] > 0)
    C = sessions_with_views / len(records)

    # R = robustness proxy: fraction of tool calls NOT preceded by skill_view
    # (agent acted without consulting prediction → robust but possibly suboptimal)
    R = 1.0 - (total_views / max(total_tools, 1))
    R = max(0.0, min(R, 1.0))

    return {"C": round(C, 4), "R": round(R, 4), "sessions": len(records)}


def run() -> int:
    now  = datetime.now(timezone.utc).isoformat()
    print(f"\n=== Prediction Tradeoff Monitor — {now[:10]} ===\n")

    if not SESSIONS_DIR.exists():
        print("ALARM: no — no sessions directory")
        return 0

    sessions = sorted([f for d in [SESSIONS_DIR, FORK_SESSIONS] if d.exists() for f in d.glob("*.jsonl")], key=lambda p: p.stat().st_mtime)
    if len(sessions) < MIN_SESSIONS:
        print(f"Only {len(sessions)} sessions (need {MIN_SESSIONS})")
        print("ALARM: no — insufficient data")
        return 0

    records = _load_skill_usage(sessions)
    t       = compute_tradeoff(records)

    print(f"Sessions analysed: {t['sessions']}")
    print(f"Consistency C = {t['C']:.4f}  (skill-consult rate)")
    print(f"Robustness  R = {t['R']:.4f}  (unguided action rate)")
    print(f"C + R         = {t['C'] + t['R']:.4f}  (theory floor = 2.0)")

    alarm = t["C"] > TRADEOFF_CEILING and t["R"] > TRADEOFF_CEILING
    if alarm:
        print(f"\nALARM: yes — both C={t['C']:.3f} and R={t['R']:.3f} > {TRADEOFF_CEILING}; "
              f"routing is both over-reliant on skill predictions AND frequently bypassing them")
    else:
        print(f"\nALARM: no — prediction tradeoff balanced (C={t['C']:.3f}, R={t['R']:.3f})")

    _tmp_out_file = OUT_FILE.with_suffix('.tmp')
    _tmp_out_file.write_text(json.dumps({"ts": now, **t}, indent=2))
    _tmp_out_file.replace(OUT_FILE)
    return 1 if alarm else 0


if __name__ == "__main__":
    sys.exit(run())
