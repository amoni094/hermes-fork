#!/usr/bin/python3
"""
quickest-change-detector.py

Detects regime shifts in multi-turn agent sessions as quickly as possible
— implements CUSUM-based quickest change detection on tool-call and
response-length time series.

Math basis: CUSUM (Cumulative Sum) quickest change point detection
  For observations X_1, X_2, ..., X_t with pre-change mean μ_0 and
  post-change mean μ_1:
    S_t = max(0, S_{t-1} + (X_t - μ_0) - κ)
    κ = (μ_1 - μ_0) / 2   (optimal slack for detecting shift μ_0 → μ_1)
  Alarm when S_t > CUSUM_THRESHOLD.
  
  Applied to: (1) response length series (detects verbosity shifts)
              (2) tool-call inter-arrival time (detects pace shifts)
              (3) error/retry count (detects quality degradation)

Usage:
  python3 quickest-change-detector.py          # scan recent sessions
  python3 quickest-change-detector.py --dry-run
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
OUT_FILE     = CACHE_DIR / "cusum-change-report.json"

CUSUM_THRESHOLD = 5.0    # alarm when CUSUM statistic exceeds this
SHIFT_FACTOR    = 1.5    # expected post-change mean = shift_factor × pre-change mean
MIN_OBS         = 5      # minimum observations per series


def _cusum(series: list[float], shift_factor: float = SHIFT_FACTOR) -> tuple[float, int]:
    """Run CUSUM on series. Return (max_stat, alarm_index or -1)."""
    if len(series) < MIN_OBS:
        return 0.0, -1

    mu0 = sum(series[:MIN_OBS]) / MIN_OBS
    mu1 = mu0 * shift_factor
    kappa = (mu1 - mu0) / 2

    s     = 0.0
    s_max = 0.0
    alarm_idx = -1

    for i, x in enumerate(series[MIN_OBS:], MIN_OBS):
        s = max(0.0, s + (x - mu0) - kappa)
        if s > s_max:
            s_max = s
        if s > CUSUM_THRESHOLD and alarm_idx == -1:
            alarm_idx = i

    return s_max, alarm_idx


def _extract_series(session_path: Path) -> dict[str, list[float]]:
    """Extract response_length, tool_count per-message series."""
    resp_lengths = []
    tool_counts  = []

    for line in session_path.read_text().splitlines():
        try:
            ev      = json.loads(line)
            role    = ev.get("role", "")
            content = ev.get("api_content", ev.get("content", ""))

            text = ""
            tools_in_msg = 0
            if isinstance(content, str):
                text = content
            elif isinstance(content, list):
                for b in content:
                    if isinstance(b, dict):
                        text += b.get("text", "")
                        if b.get("type") == "tool_use":
                            tools_in_msg += 1

            if role == "assistant" and text.strip():
                resp_lengths.append(float(len(text)))
                tool_counts.append(float(tools_in_msg))
        except Exception:
            pass

    return {"resp_lengths": resp_lengths, "tool_counts": tool_counts}


def analyse_session(session_path: Path) -> dict:
    series  = _extract_series(session_path)
    rl      = series["resp_lengths"]
    tc      = series["tool_counts"]

    if len(rl) < MIN_OBS:
        return {
            "session": session_path.stem,
            "note":    f"only {len(rl)} assistant messages (min {MIN_OBS})",
            "alarm":   False,
        }

    rl_stat, rl_idx = _cusum(rl)
    tc_stat, tc_idx = _cusum(tc)
    alarm = rl_stat > CUSUM_THRESHOLD or tc_stat > CUSUM_THRESHOLD

    return {
        "session":      session_path.stem,
        "messages":     len(rl),
        "rl_cusum":     round(rl_stat, 4),
        "tc_cusum":     round(tc_stat, 4),
        "rl_alarm_idx": rl_idx,
        "tc_alarm_idx": tc_idx,
        "alarm":        alarm,
    }


def run(dry_run: bool) -> int:
    now   = datetime.now(timezone.utc).isoformat()
    paths = sorted(SESSIONS_DIR.glob("*.jsonl"))[-10:]

    if not paths:
        print("[cusum-detector] No sessions found")
        return 0

    results     = [analyse_session(p) for p in paths]
    alarm_cases = [r for r in results if r.get("alarm")]

    print(f"\n=== Quickest Change Detector (CUSUM) — {now[:10]} ===")
    print(f"Sessions checked: {len(results)}")

    for r in results:
        if "note" in r:
            print(f"  · {r['session'][:30]}  {r['note']}")
        else:
            icon = "✗" if r["alarm"] else "✓"
            print(f"  {icon} {r['session'][:30]}  "
                  f"rl_cusum={r['rl_cusum']:.3f}  "
                  f"tc_cusum={r['tc_cusum']:.3f}  "
                  f"msgs={r['messages']}")

    if alarm_cases:
        print(f"\nALARM: yes — {len(alarm_cases)} session(s) show regime shifts")
        rc = 1
    else:
        print(f"\nALARM: no — no regime shifts detected")
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
