#!/usr/bin/env python3
"""
shadow-gate-nightly.py — Nightly shadow telemetry gate report.

Reads ~/.hermes/cache/shadow-telemetry/*.jsonl, evaluates each flag found,
and prints a markdown summary with promotion/disable recommendations.

Output contract (no_agent=True):
  - Non-empty -> delivered as message
  - Empty     -> no telemetry yet (exits 0)
"""
from __future__ import annotations

import json
import sys
import pathlib
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))

from shadow_telemetry import evaluate_flag  # noqa: E402

import os as _os_sgn
_hermes_base_sgn = pathlib.Path(_os_sgn.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_hermes_profile_sgn = _os_sgn.environ.get("HERMES_PROFILE", "")
_hermes_root_sgn = (_hermes_base_sgn / "profiles" / _hermes_profile_sgn) if _hermes_profile_sgn else _hermes_base_sgn
TELEMETRY_DIR = _hermes_root_sgn / "cache" / "shadow-telemetry"

# Recommendation thresholds (task spec)
PROMOTE_PASS_RATE   = 0.9
PROMOTE_MIN_N       = 20
DISABLE_PASS_RATE   = 0.4
DISABLE_MIN_N       = 10


def _pass_rate_from_result(result: dict) -> float | None:
    """Derive a 0-1 pass rate from evaluate_flag() output."""
    verdict = result.get("verdict", "")
    n = result.get("n_events", 0)
    metrics = result.get("metrics", {})

    if verdict == "needs_more_data" or n == 0:
        return None

    fp_rate = metrics.get("fp_rate", 0.0)
    return max(0.0, 1.0 - fp_rate)


def _recommendation(pass_rate: float | None, n: int) -> str:
    if pass_rate is None:
        return "keep-shadow (insufficient data)"
    if pass_rate > PROMOTE_PASS_RATE and n > PROMOTE_MIN_N:
        return "**promote**"
    if pass_rate < DISABLE_PASS_RATE and n > DISABLE_MIN_N:
        return "**disable**"
    return "keep-shadow"


def main() -> None:
    TELEMETRY_DIR.mkdir(parents=True, exist_ok=True)

    jsonl_files = sorted(TELEMETRY_DIR.glob("*.jsonl"))
    if not jsonl_files:
        print("No shadow telemetry data yet.")
        sys.exit(0)

    # Collect all flag names across all files
    flag_to_files: dict[str, list[Path]] = {}
    for path in jsonl_files:
        seen_flags: set[str] = set()
        try:
            with path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        evt = json.loads(line)
                        flag = evt.get("flag", "").strip()
                        if flag:
                            seen_flags.add(flag)
                    except json.JSONDecodeError:
                        pass
        except OSError:
            pass
        for flag in seen_flags:
            flag_to_files.setdefault(flag, []).append(path)

    if not flag_to_files:
        print("No shadow telemetry data yet.")
        sys.exit(0)

    rows: list[dict] = []
    for flag in sorted(flag_to_files):
        # evaluate_flag reads from default sink; pass each file in turn and
        # merge: pick the file with the most events for that flag.
        best_result: dict | None = None
        for fpath in flag_to_files[flag]:
            result = evaluate_flag(flag, fpath)
            if best_result is None or result.get("n_events", 0) > best_result.get("n_events", 0):
                best_result = result

        n = best_result.get("n_events", 0)
        pass_rate = _pass_rate_from_result(best_result)
        rec = _recommendation(pass_rate, n)

        rows.append({
            "flag": flag,
            "n": n,
            "pass_rate": pass_rate,
            "verdict": best_result.get("verdict", "?"),
            "recommendation": rec,
        })

    # Print markdown summary
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    print(f"## Shadow Gate Nightly Report — {now}")
    print()
    print("| Flag | Samples (n) | Pass rate | Recommendation |")
    print("|------|------------|-----------|----------------|")
    for row in rows:
        pr_str = f"{row['pass_rate']:.1%}" if row['pass_rate'] is not None else "—"
        print(f"| `{row['flag']}` | {row['n']} | {pr_str} | {row['recommendation']} |")

    print()
    promote = [r for r in rows if "promote" in r["recommendation"]]
    disable = [r for r in rows if "disable" in r["recommendation"]]
    if promote:
        print(f"**Promote candidates:** {', '.join('`' + r['flag'] + '`' for r in promote)}")
    if disable:
        print(f"**Disable candidates:** {', '.join('`' + r['flag'] + '`' for r in disable)}")
    if not promote and not disable:
        print("_No flags ready for promotion or disable._")


if __name__ == "__main__":
    main()
