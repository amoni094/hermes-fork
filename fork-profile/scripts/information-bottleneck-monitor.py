#!/usr/bin/python3
"""
information-bottleneck-monitor.py

Prevents silent information loss in memory compaction by providing an
automated audit of information retention across Hermes context compression
events.

Math basis: information bottleneck principle (Tishby et al.)
  The bottleneck objective: min I(X;T) - β·I(T;Y)
  where X = full context, T = compressed representation, Y = task-relevant signal
  Operationally: estimate mutual information via proxy metrics:
    - retention_rate: fraction of unique concepts surviving compression
    - relevance_score: overlap between retained content and current task keywords
    - compression_ratio: |T| / |X|  (lower = more aggressive compression)
  Alarm when retention_rate < RETENTION_THRESHOLD or
            relevance_score  < RELEVANCE_THRESHOLD

Usage:
  python3 information-bottleneck-monitor.py          # scan recent sessions
  python3 information-bottleneck-monitor.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from collections import Counter

HOME         = Path.home()
SESSIONS_DIR = HOME / ".hermes/profiles/fork/sessions"
CACHE_DIR    = HOME / ".hermes/cache/monitors"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE     = CACHE_DIR / "information-bottleneck-report.json"

RETENTION_THRESHOLD  = 0.40   # alarm if <40% of concepts survive
RELEVANCE_THRESHOLD  = 0.20   # alarm if <20% relevance to task
COMPRESSION_WARN     = 0.10   # warn if compressed to <10% of original

# Task-relevant concept keywords (broad set; improves with session data)
TASK_CONCEPTS = {
    "implement", "search", "find", "write", "read", "edit", "test",
    "verify", "deploy", "research", "analyse", "debug", "fix", "create",
    "skill", "tool", "agent", "memory", "session", "task", "plan",
}


def _extract_concepts(text: str) -> set[str]:
    return set(re.findall(r"[a-z]{4,}", text.lower()))


def _extract_messages(session_path: Path) -> list[dict]:
    messages = []
    for line in session_path.read_text().splitlines():
        try:
            ev      = json.loads(line)
            content = ev.get("api_content", ev.get("content", ""))
            role    = ev.get("role", "")
            if isinstance(content, str) and content.strip():
                messages.append({"role": role, "text": content, "len": len(content)})
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        txt = block.get("text", "")
                        if txt.strip():
                            messages.append({"role": role, "text": txt, "len": len(txt)})
        except Exception:
            pass
    return messages


def analyse_session(session_path: Path) -> dict:
    messages = _extract_messages(session_path)
    if len(messages) < 4:
        return {"session": session_path.stem, "note": "insufficient messages", "alarm": False}

    # Compare first 25% of messages vs last 25% (equal-width windows, not all-vs-one)
    window = max(1, len(messages) // 4)
    early_msgs = messages[:window]
    late_msgs  = messages[-window:]

    early_text = " ".join(m["text"] for m in early_msgs)
    last_text  = " ".join(m["text"] for m in late_msgs)

    early_concepts = _extract_concepts(early_text)
    last_concepts  = _extract_concepts(last_text)

    if not early_concepts:
        return {"session": session_path.stem, "note": "no concepts in context", "alarm": False}

    retained       = early_concepts & last_concepts
    retention_rate = len(retained) / len(early_concepts)
    relevance      = len(last_concepts & TASK_CONCEPTS) / max(len(TASK_CONCEPTS), 1)
    comp_ratio     = len(last_text) / max(len(early_text), 1)

    alarm = retention_rate < RETENTION_THRESHOLD or relevance < RELEVANCE_THRESHOLD

    return {
        "session":        session_path.stem,
        "early_concepts": len(early_concepts),
        "retained":       len(retained),
        "retention_rate": round(retention_rate, 4),
        "relevance":      round(relevance, 4),
        "comp_ratio":     round(comp_ratio, 4),
        "alarm":          alarm,
    }


def run(dry_run: bool) -> int:
    now   = datetime.now(timezone.utc).isoformat()
    paths = sorted(SESSIONS_DIR.glob("*.jsonl"))[-10:]

    if not paths:
        print("[ib-monitor] No sessions found")
        return 0

    results      = [analyse_session(p) for p in paths]
    alarm_cases  = [r for r in results if r.get("alarm")]

    print(f"\n=== Information Bottleneck Monitor — {now[:10]} ===")
    print(f"Sessions checked: {len(results)}")

    for r in results:
        if "note" in r:
            print(f"  · {r['session'][:30]}  {r['note']}")
        else:
            icon = "✗" if r["alarm"] else "✓"
            print(f"  {icon} {r['session'][:30]}  "
                  f"retention={r['retention_rate']:.3f}  "
                  f"relevance={r['relevance']:.3f}  "
                  f"comp={r['comp_ratio']:.3f}")

    if alarm_cases:
        print(f"\nALARM: yes — {len(alarm_cases)} session(s) show information bottleneck loss")
        alarm_exit = 1
    else:
        print("\nALARM: no — information retention within bounds")
        alarm_exit = 0

    if not dry_run:
        OUT_FILE.write_text(json.dumps({
            "ts": now, "results": results,
            "alarm_count": len(alarm_cases),
        }, indent=2))

    return alarm_exit


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    sys.exit(run(args.dry_run))


if __name__ == "__main__":
    main()
