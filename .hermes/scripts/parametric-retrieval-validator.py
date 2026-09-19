#!/usr/bin/python3
"""
parametric-retrieval-validator.py

Detects when parametric-only reasoning begins to fail and automatically
signals escalation to tool-augmented retrieval.

Math basis: parametric memory as a bounded linear operator
  Let R: Query → Answer be the parametric retrieval operator.
  Capacity bound: ||R(q)|| ≤ M · ||q||  for all queries q
  When ||R(q)|| approaches the capacity limit M, retrieval fidelity degrades.
  
  Operationally:
    - confidence_proxy: length / coherence ratio of assistant response
    - hedge_rate: fraction of output lines containing hedging language
    - repetition_rate: n-gram repetition (proxy for degenerate generation)
    - escalation_signal: hedge_rate > HEDGE_THRESHOLD or repetition > REP_THRESHOLD

  When escalation_signal fires: recommend specific tools to augment retrieval.

Usage:
  python3 parametric-retrieval-validator.py             # scan recent sessions
  python3 parametric-retrieval-validator.py --text "some response to validate"
  python3 parametric-retrieval-validator.py --dry-run
"""
from __future__ import annotations
import os

import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

HOME         = Path.home()
_HH = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_HP = os.environ.get("HERMES_PROFILE", "fork")
_RT = _HH / "profiles" / _HP if _HP else _HH
SESSIONS_DIR = _RT / "sessions"
CACHE_DIR    = HOME / ".hermes/cache/monitors"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE     = CACHE_DIR / "parametric-retrieval-validation.json"

HEDGE_THRESHOLD = 0.20   # >20% hedging lines → signal
REP_THRESHOLD   = 0.15   # >15% repeated trigrams → signal

HEDGE_PATTERNS = re.compile(
    r"(?i)\b(i('m| am) not (sure|certain)|"
    r"i (don't|do not) (know|have|recall)|"
    r"as (of|far as) (my|i know)|"
    r"i (believe|think|assume)|"
    r"may (not be|be incorrect)|"
    r"approximate|estimate|uncertain|unclear|"
    r"you (may|might|should) (want to |need to )?verify|"
    r"check (the )?(docs|documentation|source)|"
    r"i (cannot|can't) (access|retrieve|search))\b"
)

ESCALATION_TOOLS = {
    "web_search":   "external facts, current events, live data",
    "web_extract":  "specific URLs, documentation pages",
    "skill_view":   "Hermes-specific procedures and skills",
    "read_file":    "local files, configs, scripts",
    "execute_code": "computational verification, precise calculations",
}


def _ngrams(text: str, n: int = 3) -> list[tuple]:
    words = re.findall(r"[a-z]{3,}", text.lower())
    return list(zip(*[words[i:] for i in range(n)]))


def _repetition_rate(text: str) -> float:
    grams  = _ngrams(text)
    if not grams:
        return 0.0
    counts = Counter(grams)
    repeated = sum(c - 1 for c in counts.values() if c > 1)
    return repeated / len(grams)


def validate_response(text: str) -> dict:
    lines       = [l for l in text.splitlines() if l.strip()]
    total_lines = max(len(lines), 1)

    hedge_count = sum(1 for l in lines if HEDGE_PATTERNS.search(l))
    hedge_rate  = hedge_count / total_lines
    rep_rate    = _repetition_rate(text)

    # Confidence proxy: longer, coherent responses = higher confidence
    word_count  = len(text.split())
    conf_proxy  = min(word_count / 200.0, 1.0) * (1.0 - hedge_rate)

    escalate    = hedge_rate > HEDGE_THRESHOLD or rep_rate > REP_THRESHOLD

    # Recommend tools based on hedge content
    recommended_tools = []
    if re.search(r"(?i)(docs|documentation|official|source)", text):
        recommended_tools.append("web_extract")
    if re.search(r"(?i)(current|latest|recent|today|now)", text):
        recommended_tools.append("web_search")
    if re.search(r"(?i)(skill|procedure|workflow|hermes)", text):
        recommended_tools.append("skill_view")
    if re.search(r"(?i)(file|config|script|code)", text):
        recommended_tools.append("read_file")
    if not recommended_tools and escalate:
        recommended_tools = ["web_search", "read_file"]

    return {
        "text_len":         len(text),
        "word_count":       word_count,
        "hedge_rate":       round(hedge_rate, 4),
        "repetition_rate":  round(rep_rate, 4),
        "confidence_proxy": round(conf_proxy, 4),
        "escalate":         escalate,
        "recommended_tools": recommended_tools,
        "reason":           (
            f"hedge_rate={hedge_rate:.2f}>{HEDGE_THRESHOLD}" if hedge_rate > HEDGE_THRESHOLD
            else f"repetition={rep_rate:.2f}>{REP_THRESHOLD}" if rep_rate > REP_THRESHOLD
            else "within parametric capacity"
        ),
    }


def _extract_assistant_responses(session_path: Path) -> list[str]:
    responses = []
    for line in session_path.read_text().splitlines():
        try:
            ev = json.loads(line)
            if ev.get("role") == "assistant":
                content = ev.get("content", "")
                if isinstance(content, str) and len(content) > 50:
                    responses.append(content)
                elif isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            txt = block.get("text", "")
                            if len(txt) > 50:
                                responses.append(txt)
        except Exception:
            pass
    return responses


def run(text: str | None, dry_run: bool) -> int:
    now = datetime.now(timezone.utc).isoformat()

    if text:
        result = validate_response(text)
        print(f"\n=== Parametric Retrieval Validator ===")
        print(f"hedge_rate={result['hedge_rate']:.3f}  "
              f"rep_rate={result['repetition_rate']:.3f}  "
              f"confidence={result['confidence_proxy']:.3f}")
        if result["escalate"]:
            print(f"ESCALATE: yes — {result['reason']}")
            print(f"Recommended tools: {result['recommended_tools']}")
        else:
            print(f"ESCALATE: no — {result['reason']}")
        return 1 if result["escalate"] else 0

    # Session scan
    paths = sorted(SESSIONS_DIR.glob("*.jsonl"))[-5:]
    if not paths:
        print("[param-validator] No sessions found")
        return 0

    all_results = []
    for p in paths:
        responses = _extract_assistant_responses(p)
        if not responses:
            continue
        session_results = [validate_response(r) for r in responses]
        escalate_count  = sum(1 for r in session_results if r["escalate"])
        avg_hedge       = sum(r["hedge_rate"] for r in session_results) / len(session_results)
        avg_conf        = sum(r["confidence_proxy"] for r in session_results) / len(session_results)
        all_results.append({
            "session":       p.stem,
            "responses":     len(session_results),
            "escalate_count": escalate_count,
            "avg_hedge_rate": round(avg_hedge, 4),
            "avg_confidence": round(avg_conf, 4),
        })

    print(f"\n=== Parametric Retrieval Validator — {now[:10]} ===")
    print(f"Sessions scanned: {len(all_results)}")

    alarm_sessions = [r for r in all_results if r["escalate_count"] > 0]
    for r in all_results:
        icon = "⚠" if r["escalate_count"] else "✓"
        print(f"  {icon} {r['session'][:30]}  responses={r['responses']}  "
              f"hedge={r['avg_hedge_rate']:.3f}  conf={r['avg_confidence']:.3f}  "
              f"escalate={r['escalate_count']}")

    if alarm_sessions:
        print(f"\nALARM: yes — {len(alarm_sessions)} session(s) showing parametric retrieval strain")
        alarm_exit = 1
    else:
        print("\nALARM: no — parametric retrieval within capacity bounds")
        alarm_exit = 0

    if not dry_run:
        _tmp_out_file = OUT_FILE.with_suffix('.tmp')
        _tmp_out_file.write_text(json.dumps({"ts": now, "results": all_results}, indent=2))
        _tmp_out_file.replace(OUT_FILE)

    return alarm_exit


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--text",    default=None, help="Validate a specific response string")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    sys.exit(run(args.text, args.dry_run))


if __name__ == "__main__":
    main()
