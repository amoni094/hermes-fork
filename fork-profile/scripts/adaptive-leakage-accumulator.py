#!/usr/bin/python3
"""
adaptive-leakage-accumulator.py

Detects and bounds information leakage across adaptive multi-turn
interactions — tracks how much sensitive context bleeds into subsequent
responses as interaction history grows.

Math basis: adaptive information leakage bound
  In a T-round adaptive protocol, total leakage L_T satisfies:
    L_T ≤ Σ_{t=1}^{T} ε_t   where ε_t = per-round leakage
  Operationally:
    ε_t = size of sensitive tokens appearing in turn t's response
          that were introduced in previous turns (not in current query)
  Alarm when L_T / T_total > LEAKAGE_RATE_THRESHOLD (leakage rate too high).

Usage:
  python3 adaptive-leakage-accumulator.py          # scan recent sessions
  python3 adaptive-leakage-accumulator.py --dry-run
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
OUT_FILE     = CACHE_DIR / "leakage-accumulator-report.json"

LEAKAGE_RATE_THRESHOLD = 0.30   # alarm if >30% of response tokens are leaked context
MIN_TURNS              = 3

# Sensitive token patterns (proxy for PII / credential / internal data)
SENSITIVE_PATTERNS = [
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.\w+\b",  # email
    r"\b\d{3}-\d{2}-\d{4}\b",                        # SSN-like
    r"(?i)\bpassword\b|\bapi[_\s]?key\b|\btoken\b",  # credential keywords
    r"(?i)\bsecret\b|\bcredential\b",
    r"\b(?:sk|pk|rk)-[A-Za-z0-9]{20,}\b",            # API key format
]


def _sensitive_tokens(text: str) -> set[str]:
    found = set()
    for pat in SENSITIVE_PATTERNS:
        for m in re.finditer(pat, text):
            found.add(m.group().lower()[:30])
    return found


def analyse_session(session_path: Path) -> dict:
    turns: list[dict] = []
    for line in session_path.read_text().splitlines():
        try:
            ev      = json.loads(line)
            role    = ev.get("role", "")
            content = ev.get("api_content", ev.get("content", ""))
            text    = ""
            if isinstance(content, str):
                text = content
            elif isinstance(content, list):
                text = " ".join(
                    b.get("text", "") for b in content
                    if isinstance(b, dict) and b.get("type") == "text"
                )
            if text.strip() and role in ("user", "assistant"):
                turns.append({"role": role, "text": text})
        except Exception:
            pass

    if len(turns) < MIN_TURNS:
        return {
            "session": session_path.stem,
            "note":    f"only {len(turns)} turns (min {MIN_TURNS})",
            "alarm":   False,
        }

    # Accumulate introduced sensitive tokens per turn; track leakage into responses
    introduced: set[str] = set()
    total_response_tokens = 0
    leaked_tokens         = 0

    for turn in turns:
        sens = _sensitive_tokens(turn["text"])
        word_count = max(len(turn["text"].split()), 1)

        if turn["role"] == "user":
            introduced |= sens
        else:
            # Response: count sensitive tokens from prior context appearing here
            leaked = sens & introduced
            leaked_tokens         += len(leaked)
            total_response_tokens += word_count

    leakage_rate = leaked_tokens / max(total_response_tokens / 50, 1)
    # Normalise: leaked_tokens per 50-word response chunk
    alarm = leakage_rate > LEAKAGE_RATE_THRESHOLD and leaked_tokens > 0

    return {
        "session":             session_path.stem,
        "turns":               len(turns),
        "introduced_sensitive": len(introduced),
        "leaked_tokens":       leaked_tokens,
        "leakage_rate":        round(leakage_rate, 4),
        "alarm":               alarm,
    }


def run(dry_run: bool) -> int:
    now   = datetime.now(timezone.utc).isoformat()
    paths = sorted(SESSIONS_DIR.glob("*.jsonl"))[-10:]

    if not paths:
        print("[leakage-accumulator] No sessions found")
        return 0

    results     = [analyse_session(p) for p in paths]
    alarm_cases = [r for r in results if r.get("alarm")]

    print(f"\n=== Adaptive Leakage Accumulator — {now[:10]} ===")
    print(f"Sessions checked: {len(results)}")

    for r in results:
        if "note" in r:
            print(f"  · {r['session'][:30]}  {r['note']}")
        else:
            icon = "✗" if r["alarm"] else "✓"
            print(f"  {icon} {r['session'][:30]}  "
                  f"leakage_rate={r['leakage_rate']:.3f}  "
                  f"leaked={r['leaked_tokens']}  "
                  f"turns={r['turns']}")

    if alarm_cases:
        print(f"\nALARM: yes — {len(alarm_cases)} session(s) exceed leakage rate threshold")
        rc = 1
    else:
        print(f"\nALARM: no — information leakage within bounds")
        rc = 0

    if not dry_run:
        OUT_FILE.write_text(json.dumps({
            "ts": now, "results": results, "alarm_count": len(alarm_cases),
        }, indent=2))

    return rc


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    sys.exit(run(args.dry_run))


if __name__ == "__main__":
    main()
