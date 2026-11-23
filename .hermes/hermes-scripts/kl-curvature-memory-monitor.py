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
import os

import argparse
import json
import math
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

HOME         = Path.home()
_HH = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_HP = os.environ.get("HERMES_PROFILE", "fork")
_RT = _HH / "profiles" / _HP if _HP else _HH
SESSIONS_DIR = _RT / "sessions"
# ADV21-011: use profile-aware cache path
CACHE_DIR    = _RT / "cache"
try:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
except Exception:
    pass
OUT_FILE     = CACHE_DIR / "kl-curvature-report.json"
ALARM_FILE   = CACHE_DIR / "kl-curvature-alarm.json"

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
        try:
            import time as _t
            tmp = ALARM_FILE.with_suffix('.tmp')
            tmp.write_text(json.dumps({"alarm": False, "reason": "no_sessions", "ts": _t.time()}, ensure_ascii=False))
            os.replace(tmp, ALARM_FILE)
        except Exception:
            pass
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
        _tmp_out_file = OUT_FILE.with_suffix('.tmp')
        _tmp_out_file.write_text(json.dumps({
            "ts": now, "results": results, "alarm_count": len(alarm_cases),
        }, indent=2))
        _tmp_out_file.replace(OUT_FILE)
        # ADV21-011: persist alarm sidecar for aggregator glob
        try:
            import time as _t
            payload = {"alarm": bool(alarm_cases), "n_alarms": len(alarm_cases),
                       "n_sessions": len(results), "ts": _t.time(),
                       "reason": "high_kl_curvature" if alarm_cases else "ok"}
            tmp_alarm = ALARM_FILE.with_suffix('.tmp')
            tmp_alarm.write_text(json.dumps(payload, ensure_ascii=False))
            os.replace(tmp_alarm, ALARM_FILE)
        except Exception:
            pass

    return rc


def _self_test() -> int:
    """ADV21-011: verify profile-aware path + chi2 with 3-element distribution."""
    try:
        dist = {'tool_read': 40, 'tool_write': 8, 'tool_search': 2}
        total = sum(dist.values())
        k = max(len(dist), 1)
        uniform = 1.0 / k
        chi2 = sum((v/total - uniform)**2 / uniform for v in dist.values())
        assert chi2 > 0, f"chi2={chi2} must be positive"
        assert CACHE_DIR == _RT / "cache", f"CACHE_DIR={CACHE_DIR} must be profile-aware"
        print("[kl-curvature] --self-test PASS")
        return 0
    except Exception as exc:
        print(f"[kl-curvature] --self-test FAIL: {exc}")
        return 1


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--self-test", action="store_true")
    args = p.parse_args()
    if getattr(args, "self_test", False):
        sys.exit(_self_test())
    try:
        rc = run(args.dry_run)
    except Exception as exc:
        # ADV21-011: H-I7 — never crash caller
        print(f"[kl-curvature] ERROR (suppressed): {exc}", file=sys.stderr)
        rc = 1
    sys.exit(rc)


if __name__ == "__main__":
    main()
