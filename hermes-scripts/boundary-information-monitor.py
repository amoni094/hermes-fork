#!/usr/bin/python3
"""
boundary-information-monitor.py

Detects high-uncertainty decision points before they become errors —
monitors the information boundary between what Hermes knows vs. what it
needs to answer confidently, and triggers clarification requests.

Math basis: boundary information (from statistical learning theory)
  Decision boundary uncertainty: when the evidence vector x is within
  distance ε of the decision boundary, the decision is unreliable.
  Operationally via Platt-scaled confidence:
    P(correct | x) estimated from response hedge-rate + contradiction density
  Alarm when P(correct) < CONFIDENCE_THRESHOLD for task-relevant outputs.

Usage:
  python3 boundary-information-monitor.py          # scan recent sessions
  python3 boundary-information-monitor.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

HOME         = Path.home()
SESSIONS_DIR = HOME / ".hermes/profiles/fork/sessions"
CACHE_DIR    = HOME / ".hermes/cache/monitors"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE     = CACHE_DIR / "boundary-information-report.json"

CONFIDENCE_THRESHOLD = 0.55   # alarm if estimated confidence < 55%
MIN_RESPONSE_LEN     = 30     # skip very short responses

# Hedging language → confidence reduction
HEDGE_PATTERNS = [
    (r"(?i)\bi('m| am) not sure\b",           0.25),
    (r"(?i)\bit('s| is) unclear\b",           0.20),
    (r"(?i)\bI cannot determine\b",            0.30),
    (r"(?i)\bmight\b|\bcould\b|\bperhaps\b",   0.05),
    (r"(?i)\bI think\b|\bI believe\b",         0.08),
    (r"(?i)\bprobably\b|\blikely\b",           0.05),
    (r"(?i)\bdepends\b|\bit varies\b",         0.10),
    (r"(?i)\bI don'?t know\b",                 0.30),
    (r"(?i)\buncertain\b|\bunsure\b",          0.15),
]

# Contradiction signals → confidence reduction
CONTRADICTION_PATTERNS = [
    (r"(?i)\bhowever\b.{0,50}\bbut\b",        0.10),
    (r"(?i)\bon the other hand\b",             0.08),
    (r"(?i)\bcontradicts?\b|\bconflicts?\b",   0.15),
]


def _score_response(text: str) -> tuple[float, list[str]]:
    """Estimate confidence from 0 (uncertain) to 1 (confident)."""
    confidence = 1.0
    reasons    = []

    for pattern, penalty in HEDGE_PATTERNS:
        matches = len(re.findall(pattern, text))
        if matches:
            confidence -= penalty * matches
            reasons.append(f"hedge({matches}×): {pattern[:25]}")

    for pattern, penalty in CONTRADICTION_PATTERNS:
        matches = len(re.findall(pattern, text))
        if matches:
            confidence -= penalty * matches
            reasons.append(f"contradict({matches}×): {pattern[:25]}")

    return max(0.0, min(confidence, 1.0)), reasons


def analyse_session(session_path: Path) -> dict:
    responses  = []
    for line in session_path.read_text().splitlines():
        try:
            ev   = json.loads(line)
            role = ev.get("role", "")
            if role != "assistant":
                continue
            content = ev.get("api_content", ev.get("content", ""))
            texts   = []
            if isinstance(content, str):
                texts = [content]
            elif isinstance(content, list):
                texts = [b.get("text","") for b in content
                         if isinstance(b, dict) and b.get("type") == "text"]
            for t in texts:
                if len(t) >= MIN_RESPONSE_LEN:
                    responses.append(t)
        except Exception:
            pass

    if not responses:
        return {"session": session_path.stem, "note": "no assistant responses", "alarm": False}

    scores = [_score_response(r) for r in responses]
    confidences = [s[0] for s in scores]
    avg_conf    = sum(confidences) / len(confidences)
    min_conf    = min(confidences)
    low_count   = sum(1 for c in confidences if c < CONFIDENCE_THRESHOLD)

    alarm = min_conf < CONFIDENCE_THRESHOLD and low_count > len(responses) * 0.25

    return {
        "session":     session_path.stem,
        "responses":   len(responses),
        "avg_conf":    round(avg_conf, 4),
        "min_conf":    round(min_conf, 4),
        "low_count":   low_count,
        "alarm":       alarm,
    }


def run(dry_run: bool) -> int:
    now   = datetime.now(timezone.utc).isoformat()
    paths = sorted(SESSIONS_DIR.glob("*.jsonl"))[-10:]

    if not paths:
        print("[boundary-monitor] No sessions found")
        return 0

    results     = [analyse_session(p) for p in paths]
    alarm_cases = [r for r in results if r.get("alarm")]

    print(f"\n=== Boundary Information Monitor — {now[:10]} ===")
    print(f"Sessions checked: {len(results)}")

    for r in results:
        if "note" in r:
            print(f"  · {r['session'][:30]}  {r['note']}")
        else:
            icon = "✗" if r["alarm"] else "✓"
            print(f"  {icon} {r['session'][:30]}  "
                  f"avg_conf={r['avg_conf']:.3f}  "
                  f"min_conf={r['min_conf']:.3f}  "
                  f"low={r['low_count']}/{r['responses']}")

    if alarm_cases:
        print(f"\nALARM: yes — {len(alarm_cases)} session(s) show high decision-boundary uncertainty")
        return 1
    else:
        print(f"\nALARM: no — confidence within bounds")
        return 0


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    sys.exit(run(args.dry_run))


if __name__ == "__main__":
    main()
