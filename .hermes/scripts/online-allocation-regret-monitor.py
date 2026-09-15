#!/usr/bin/python3
"""
online-allocation-regret-monitor.py

Enables Hermes to dynamically trade off immediate responsiveness against
allocation regret — monitors the switching regret accumulated by the
current routing policy across tool/skill invocations.

Math basis: multi-armed bandit switching regret (arXiv spike)
  For a routing policy π over K arms (tools/skills), switching regret is:
    R_switch(T) = Σ_{t=1}^T [r*(t) - r_π(t)] + λ · Σ_{t=2}^T 1[π(t)≠π(t-1)]
  where r*(t) = best-arm reward at time t, λ = switching cost.
  
  Alarm when R_switch / T > REGRET_RATE_THRESHOLD (policy switching too
  much relative to reward gain).

Usage:
  python3 online-allocation-regret-monitor.py          # scan recent sessions
  python3 online-allocation-regret-monitor.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

HOME         = Path.home()
SESSIONS_DIR = HOME / ".hermes/profiles/fork/sessions"
CACHE_DIR    = HOME / ".hermes/cache/monitors"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE     = CACHE_DIR / "regret-monitor-report.json"

REGRET_RATE_THRESHOLD = 0.40   # alarm if switching regret rate > 40%
SWITCHING_COST        = 0.10   # λ: cost per tool switch
MIN_CALLS             = 6


def _extract_tools(session_path: Path) -> list[str]:
    tools = []
    for line in session_path.read_text().splitlines():
        try:
            ev      = json.loads(line)
            content = ev.get("api_content", ev.get("content", ""))
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        tools.append(block.get("name", "unknown"))
        except Exception:
            pass
    return tools


def _tool_reward(tool: str, freq_map: dict[str, float]) -> float:
    """Proxy reward: normalised frequency (popular tools = higher baseline reward)."""
    return freq_map.get(tool, 0.1)


def analyse_session(session_path: Path) -> dict:
    tools = _extract_tools(session_path)
    if len(tools) < MIN_CALLS:
        return {
            "session": session_path.stem,
            "note":    f"only {len(tools)} tool calls (min {MIN_CALLS})",
            "alarm":   False,
        }

    total      = len(tools)
    counts     = Counter(tools)
    # Frequency-based reward proxy: most-used tool = reward 1.0
    max_count  = max(counts.values())
    freq_map   = {t: c / max_count for t, c in counts.items()}

    # Best arm at each step (hindsight): the globally most frequent tool
    best_arm   = counts.most_common(1)[0][0]
    best_reward = 1.0   # normalised

    # Compute switching regret
    regret     = 0.0
    switches   = 0
    for i, tool in enumerate(tools):
        reward  = freq_map.get(tool, 0.1)
        regret += best_reward - reward
        if i > 0 and tools[i] != tools[i-1]:
            regret  += SWITCHING_COST
            switches += 1

    regret_rate = regret / total
    alarm       = regret_rate > REGRET_RATE_THRESHOLD

    return {
        "session":      session_path.stem,
        "tool_calls":   total,
        "switches":     switches,
        "switch_rate":  round(switches / max(total - 1, 1), 4),
        "regret":       round(regret, 4),
        "regret_rate":  round(regret_rate, 4),
        "best_arm":     best_arm,
        "alarm":        alarm,
    }


def run(dry_run: bool) -> int:
    now   = datetime.now(timezone.utc).isoformat()
    paths = sorted(SESSIONS_DIR.glob("*.jsonl"))[-10:]

    if not paths:
        print("[regret-monitor] No sessions found")
        return 0

    results     = [analyse_session(p) for p in paths]
    alarm_cases = [r for r in results if r.get("alarm")]

    print(f"\n=== Online Allocation Regret Monitor — {now[:10]} ===")
    print(f"Sessions checked: {len(results)}")

    for r in results:
        if "note" in r:
            print(f"  · {r['session'][:30]}  {r['note']}")
        else:
            icon = "✗" if r["alarm"] else "✓"
            print(f"  {icon} {r['session'][:30]}  "
                  f"regret_rate={r['regret_rate']:.3f}  "
                  f"switches={r['switches']}/{r['tool_calls']}  "
                  f"best={r['best_arm']}")

    if alarm_cases:
        print(f"\nALARM: yes — {len(alarm_cases)} session(s) exceed switching regret threshold")
        rc = 1
    else:
        print(f"\nALARM: no — routing regret within bounds")
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
