#!/usr/bin/python3
"""
kl-curvature-memory-monitor.py

Detects when Hermes' tool/skill chains have accumulated too much
memory-dependent state — uses KL-divergence curvature (= Fisher
information) as a proxy for how "rigid" the current routing state is.

Math basis: KL curvature = Fisher information
  The local curvature of KL(p_θ || p_θ₀) at θ=θ₀ equals the Fisher
  information matrix I(θ₀). High Fisher information → routing distribution
  is sharply concentrated → overfit to recent history.
  
  Operationally: estimate curvature from tool-call frequency distribution
    p_t[k] = count(tool_k in last W calls) / W
    p_0[k] = uniform baseline (1/K)
    KL(p_t || p_0) = Σ_k p_t[k] · log(p_t[k] / p_0[k])
    Curvature proxy: Σ_k (p_t[k] - p_0[k])² / p_0[k]   (χ² divergence ≈ Fisher)
  
  Alarm when curvature > CURVATURE_THRESHOLD (routing is over-rigid).

Usage:
  python3 kl-curvature-memory-monitor.py          # scan recent sessions
  python3 kl-curvature-memory-monitor.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

HOME         = Path.home()
SESSIONS_DIR = HOME / ".hermes/profiles/fork/sessions"
CACHE_DIR    = HOME / ".hermes/cache/monitors"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE     = CACHE_DIR / "kl-curvature-report.json"

CURVATURE_THRESHOLD = 3.0   # χ² proxy; >3.0 = over-rigid routing
WINDOW              = 50    # last N tool calls to analyse
MIN_CALLS           = 5     # skip sessions with fewer tool calls


def _extract_tool_calls(session_path: Path) -> list[str]:
    tools = []
    for line in session_path.read_text().splitlines():
        try:
            ev = json.loads(line)
            # Tool calls appear as role=assistant with tool_use blocks
            content = ev.get("api_content", ev.get("content", ""))
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        tools.append(block.get("name", "unknown"))
        except Exception:
            pass
    return tools[-WINDOW:]


def _chi2_curvature(counts: Counter, total: int, k: int) -> float:
    """χ² divergence from uniform: Σ (p_t - 1/K)² / (1/K)."""
    uniform = 1.0 / k
    curvature = 0.0
    for tool, cnt in counts.items():
        p_t = cnt / total
        curvature += (p_t - uniform) ** 2 / uniform
    return curvature


def analyse_session(session_path: Path) -> dict:
    tools = _extract_tool_calls(session_path)
    if len(tools) < MIN_CALLS:
        return {
            "session": session_path.stem,
            "note": f"only {len(tools)} tool calls (min {MIN_CALLS})",
            "alarm": False,
        }

    counts    = Counter(tools)
    k         = max(len(counts), 1)
    curvature = _chi2_curvature(counts, len(tools), k)

    # KL from uniform (for reporting)
    kl = sum(
        (cnt / len(tools)) * math.log((cnt / len(tools)) / (1.0 / k))
        for cnt in counts.values()
    )

    top_tool = counts.most_common(1)[0]
    alarm    = curvature > CURVATURE_THRESHOLD

    return {
        "session":    session_path.stem,
        "tool_calls": len(tools),
        "unique":     k,
        "curvature":  round(curvature, 4),
        "kl_uniform": round(kl, 4),
        "top_tool":   f"{top_tool[0]} ({top_tool[1]}×)",
        "alarm":      alarm,
    }


def run(dry_run: bool) -> int:
    now   = datetime.now(timezone.utc).isoformat()
    paths = sorted(SESSIONS_DIR.glob("*.jsonl"))[-10:]

    if not paths:
        print("[kl-curvature] No sessions found")
        return 0

    results     = [analyse_session(p) for p in paths]
    alarm_cases = [r for r in results if r.get("alarm")]

    print(f"\n=== KL-Curvature Memory Monitor — {now[:10]} ===")
    print(f"Sessions checked: {len(results)}")

    for r in results:
        if "note" in r:
            print(f"  · {r['session'][:30]}  {r['note']}")
        else:
            icon = "✗" if r["alarm"] else "✓"
            print(f"  {icon} {r['session'][:30]}  "
                  f"curvature={r['curvature']:.3f}  "
                  f"KL={r['kl_uniform']:.3f}  "
                  f"top={r['top_tool']}")

    if alarm_cases:
        print(f"\nALARM: yes — {len(alarm_cases)} session(s) show over-rigid routing "
              f"(curvature > {CURVATURE_THRESHOLD})")
        rc = 1
    else:
        print(f"\nALARM: no — routing diversity within bounds")
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
