#!/usr/bin/python3
"""
hierarchy-radius-monitor.py

Predicts and prevents context-budget overflow before it occurs by
maintaining a hierarchical packing-radius ordering over active context
blocks — detects when the hierarchy is violated (overflow risk).

Math basis: hierarchical packing radius ordering
  A sequence of nested constraint sets C_1 ⊆ C_2 ⊆ ... ⊆ C_k induces a
  hierarchy of packing radii r_1 ≥ r_2 ≥ ... ≥ r_k (larger set = smaller
  packing radius). Violation: r_{i} < r_{i+1} for some i → hierarchy
  inverted → context blocks mis-ordered by priority.
  
  Proxy via token budget tiers:
    tier 1 (critical): system prompt + task spec
    tier 2 (active):   current tool results
    tier 3 (history):  prior conversation turns
    tier 4 (cache):    skill descriptions, memory injections
  Alarm when any lower-priority tier consumes more tokens than a higher tier
  AND total > BUDGET_WARNING_THRESHOLD.

Usage:
  python3 hierarchy-radius-monitor.py          # scan recent sessions
  python3 hierarchy-radius-monitor.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HOME         = Path.home()
SESSIONS_DIR = HOME / ".hermes/profiles/fork/sessions"
CACHE_DIR    = HOME / ".hermes/cache/monitors"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE     = CACHE_DIR / "hierarchy-radius-report.json"

# Token budget tiers (priority order: tier 1 = highest)
TIERS = {
    "system":   1,   # system prompt
    "user":     2,   # user messages
    "tool":     3,   # tool results
    "assistant":4,   # assistant turns
}
BUDGET_WARNING_THRESHOLD = 8000   # tokens; below this, hierarchy violations are low-risk
CHARS_PER_TOKEN          = 4      # rough approximation


def _count_tokens(text: str) -> int:
    return max(len(text) // CHARS_PER_TOKEN, 1)


def analyse_session(session_path: Path) -> dict:
    tier_tokens: dict[str, int] = {t: 0 for t in TIERS}
    total = 0

    for line in session_path.read_text().splitlines():
        try:
            ev      = json.loads(line)
            role    = ev.get("role", "")
            content = ev.get("api_content", ev.get("content", ""))
            text    = ""
            if isinstance(content, str):
                text = content
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict):
                        text += block.get("text", "") + block.get("content", "")
            if role in tier_tokens:
                t = _count_tokens(text)
                tier_tokens[role] += t
                total += t
        except Exception:
            pass

    if total < BUDGET_WARNING_THRESHOLD // 4:
        return {
            "session": session_path.stem,
            "note":    f"only ~{total} tokens (too small)",
            "alarm":   False,
        }

    # Check hierarchy: tier N should have ≤ tokens of tier N-1
    violations = []
    tier_list  = sorted(TIERS.items(), key=lambda x: x[1])
    for i in range(len(tier_list) - 1):
        name_hi, pri_hi = tier_list[i]
        name_lo, pri_lo = tier_list[i + 1]
        t_hi = tier_tokens[name_hi]
        t_lo = tier_tokens[name_lo]
        # Lower-priority tier should not dominate higher-priority by >3×
        if t_lo > t_hi * 3 and t_hi > 0:
            violations.append(
                f"{name_lo}({t_lo}) >> {name_hi}({t_hi})"
            )

    alarm = len(violations) > 0 and total > BUDGET_WARNING_THRESHOLD

    return {
        "session":    session_path.stem,
        "total_tok":  total,
        "tiers":      {k: v for k, v in tier_tokens.items()},
        "violations": violations,
        "alarm":      alarm,
    }


def run(dry_run: bool) -> int:
    now   = datetime.now(timezone.utc).isoformat()
    paths = sorted(SESSIONS_DIR.glob("*.jsonl"))[-10:]

    if not paths:
        print("[hierarchy-radius] No sessions found")
        return 0

    results     = [analyse_session(p) for p in paths]
    alarm_cases = [r for r in results if r.get("alarm")]

    print(f"\n=== Hierarchy Radius Monitor — {now[:10]} ===")
    print(f"Sessions checked: {len(results)}")

    for r in results:
        if "note" in r:
            print(f"  · {r['session'][:30]}  {r['note']}")
        else:
            icon  = "✗" if r["alarm"] else "✓"
            tiers = r.get("tiers", {})
            print(f"  {icon} {r['session'][:30]}  "
                  f"total={r['total_tok']}tok  "
                  f"sys={tiers.get('system',0)} "
                  f"usr={tiers.get('user',0)} "
                  f"tool={tiers.get('tool',0)} "
                  f"asst={tiers.get('assistant',0)}")
            for v in r.get("violations", []):
                print(f"      VIOLATION: {v}")

    if alarm_cases:
        print(f"\nALARM: yes — {len(alarm_cases)} session(s) show context hierarchy violations")
        rc = 1
    else:
        print(f"\nALARM: no — context budget hierarchy intact")
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
