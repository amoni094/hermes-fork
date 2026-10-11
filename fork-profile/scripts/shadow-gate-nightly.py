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

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent
# Main scripts is always 3 levels up from fork/scripts (not HERMES_HOME which is the profile)
_MAIN_SCRIPTS = Path(__file__).resolve().parent.parent.parent.parent / "scripts"
# Add both fork/scripts and main scripts to path (shadow_telemetry lives in main scripts)
for _d in [str(SCRIPTS_DIR), str(_MAIN_SCRIPTS)]:
    if _d not in sys.path:
        sys.path.insert(0, _d)

from shadow_telemetry import evaluate_flag  # noqa: E402

_HERMES_HOME = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_PROFILE = os.environ.get("HERMES_PROFILE", "fork")
# ADV2-012: profile cache, never the base Hermes cache.
TELEMETRY_DIR = _HERMES_HOME / "profiles" / _PROFILE / "cache" / "shadow-telemetry"
CACHE_DIR = _HERMES_HOME / "profiles" / _PROFILE / "cache"
EFFECTIVE_PATH = CACHE_DIR / "effective-shadow-decisions.json"
SUMMARY_PATH = CACHE_DIR / "nightly-gate-summary.json"

# Recommendation thresholds (task spec)
PROMOTE_PASS_RATE   = 0.9
PROMOTE_MIN_N       = 20
DISABLE_PASS_RATE   = 0.4
DISABLE_MIN_N       = 10

# Power gate: refuse to recommend PROMOTE unless N >= N_MIN_POWER.
# Statistical basis: for a one-sample binomial proportion test with pass_rate~0.9
# and MDE of 10 pp, 80% power at alpha=0.05 requires n≈96 (z²*p*(1-p)/d²).
# N=50 is underpowered for a 10pp MDE; use N=50 only as a minimum floor to
# ensure SPRT has had enough observations, not as a power guarantee.
# AUDIT-16: do not claim N=50 gives 80% power for 10pp MDE — it does not.
# Set N_min from actual MDE: n = (z_alpha+z_beta)^2 * p*(1-p) / d^2.
# For p=0.9, d=0.10, alpha=0.05, power=0.80: n≈71; use 75 as a round number.
# For p=0.8, d=0.10: n≈125. Floor at 50 preserves existing behavior as a
# minimum guard but operators should compute from actual pass_rate+MDE.
N_MIN_POWER = 50  # FLOOR ONLY — see comment above; actual power requires n≈75-125 for 10pp MDE

# Zero-tolerance event types: any occurrence in a flag's telemetry = hard REJECT.
# These are safety floors, not statistical tests.
ZERO_TOLERANCE_EVENT_TYPES = frozenset({
    'unauthorized_tool_call',
    'policy_violation',
    'tamper_detected',
})


def _pass_rate_from_result(result: dict) -> float | None:
    """Derive a 0-1 pass rate from evaluate_flag() output."""
    verdict = result.get("verdict", "")
    n = result.get("n_events", 0)
    metrics = result.get("metrics", {})

    if verdict == "needs_more_data" or n == 0:
        return None

    fp_rate = metrics.get("fp_rate", 0.0)
    return max(0.0, 1.0 - fp_rate)


def _atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _effective_promote_flags() -> tuple[set[str] | None, str]:
    """None means effective file missing/unreadable — never emit **promote**."""
    if not EFFECTIVE_PATH.exists():
        return None, "effective_missing"
    try:
        data = json.loads(EFFECTIVE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, "effective_unreadable"
    if not isinstance(data, dict):
        return None, "effective_unreadable"
    flags: set[str] = set()
    for d in data.get("decisions") or []:
        if isinstance(d, dict) and d.get("decision") == "PROMOTE" and d.get("flag"):
            flags.add(str(d["flag"]))
    return flags, "effective-shadow-decisions.json"


def _recommendation(pass_rate: float | None, n: int, flag: str = "",
                    promote_flags: set[str] | None = None) -> str:
    if pass_rate is None:
        return "keep-shadow (insufficient data)"
    if n < N_MIN_POWER:
        return f"hold (underpowered: n={n} < N_min={N_MIN_POWER})"
    if pass_rate > PROMOTE_PASS_RATE and n > PROMOTE_MIN_N:
        if promote_flags is not None and flag in promote_flags:
            return "**promote**"
        return "hold (effective-shadow not PROMOTE)"
    if pass_rate < DISABLE_PASS_RATE and n > DISABLE_MIN_N:
        return "**disable**"
    return "keep-shadow"


def _check_zero_tolerance_raw(flag: str, jsonl_path: Path) -> list[str]:
    """Scan raw JSONL events for zero-tolerance event_type violations.

    evaluate_flag() only surfaces aggregate fp_rate; it does not expose
    event_type breakdowns. We scan the raw JSONL for the flag to find
    any zero-tolerance events (unauthorized_tool_call, policy_violation,
    tamper_detected) which must hard-REJECT regardless of aggregate metrics.
    """
    violations = []
    try:
        with jsonl_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    evt = json.loads(line)
                    if evt.get("flag") != flag:
                        continue
                    # Check direct event_type field
                    et = evt.get("event_type", "")
                    if et in ZERO_TOLERANCE_EVENT_TYPES:
                        violations.append(f"event_type:{et}")
                    # Also check analysis sub-dict for tagged violation types
                    analysis = evt.get("analysis", {})
                    at = analysis.get("violation_type", "")
                    if at in ZERO_TOLERANCE_EVENT_TYPES:
                        violations.append(f"analysis.violation_type:{at}")
                    # Check metadata dict
                    meta = evt.get("metadata", {})
                    for key in ZERO_TOLERANCE_EVENT_TYPES:
                        if meta.get(key, 0) > 0 or meta.get(key) is True:
                            violations.append(f"metadata:{key}")
                except json.JSONDecodeError:
                    pass
    except OSError:
        pass
    return list(dict.fromkeys(violations))  # deduplicate preserving order


def _check_zero_tolerance(result: dict) -> list[str]:
    """Return list of zero-tolerance violations found in flag telemetry metadata.

    NOTE: evaluate_flag() does not expose event_type breakdowns in its metrics
    dict. This function checks only what evaluate_flag surfaces (fp flags).
    For raw event scanning use _check_zero_tolerance_raw().
    """
    violations = []
    metrics = result.get('metrics', {})
    # Check metrics dict for known zero-tolerance keys (may be present in custom evaluate_flag extensions)
    for key in ZERO_TOLERANCE_EVENT_TYPES:
        if metrics.get(key, 0) > 0:
            violations.append(f"{key}={metrics[key]}")
    return violations


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
    promote_flags, rec_source = _effective_promote_flags()
    n_promote_vetoed = 0
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
        # Check metrics-based violations (custom evaluate_flag extensions)
        zero_tol_violations = _check_zero_tolerance(best_result or {})
        # Also scan raw JSONL events for event_type-level violations
        # (evaluate_flag only surfaces aggregate fp_rate, not event_type breakdown)
        for fpath in flag_to_files.get(flag, []):
            zero_tol_violations.extend(_check_zero_tolerance_raw(flag, fpath))
        zero_tol_violations = list(dict.fromkeys(zero_tol_violations))  # dedup
        # Zero-tolerance: safety floor; overrides all statistical logic.
        if zero_tol_violations:
            rec = f"**REJECT** (zero-tolerance violation: {'; '.join(zero_tol_violations)})"
        else:
            rec = _recommendation(pass_rate, n, flag, promote_flags)
            would_promote = (
                pass_rate is not None
                and n >= N_MIN_POWER
                and pass_rate > PROMOTE_PASS_RATE
                and n > PROMOTE_MIN_N
            )
            if would_promote and rec != "**promote**":
                n_promote_vetoed += 1

        rows.append({
            "flag": flag,
            "n": n,
            "pass_rate": pass_rate,
            "verdict": best_result.get("verdict", "?"),
            "recommendation": rec,
            "zero_tolerance_violations": zero_tol_violations,
        })

    # Print markdown summary
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
    hold = [r for r in rows if "hold (underpowered" in r["recommendation"]]
    reject = [r for r in rows if "REJECT" in r["recommendation"]]
    if reject:
        print(f"**REJECT (zero-tolerance):** {', '.join('`' + r['flag'] + '`' for r in reject)}")
    if promote:
        print(f"**Promote candidates:** {', '.join('`' + r['flag'] + '`' for r in promote)}")
    if disable:
        print(f"**Disable candidates:** {', '.join('`' + r['flag'] + '`' for r in disable)}")
    if hold:
        print(f"**Underpowered (hold):** {', '.join('`' + r['flag'] + '`' for r in hold)} — need n>={N_MIN_POWER}")
    if not promote and not disable and not reject:
        print("_No flags ready for promotion, disable, or reject._")

    rates = [r["pass_rate"] for r in rows if r.get("pass_rate") is not None]
    summary = {
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "n_tested": len(rows),
        "pass_rate": (sum(rates) / len(rates)) if rates else None,
        "n_promote_vetoed": n_promote_vetoed,
        "recommendation_source": rec_source,
    }
    try:
        _atomic_write(SUMMARY_PATH, summary)
    except OSError:
        pass


def self_test() -> int:
    failures = []
    expected = (
        Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
        / "profiles" / os.environ.get("HERMES_PROFILE", "fork")
        / "cache" / "shadow-telemetry"
    )
    if TELEMETRY_DIR != expected:
        failures.append(f"TELEMETRY_DIR={TELEMETRY_DIR} expected={expected}")
    rec_none = _recommendation(0.99, 100, "f", None)
    if rec_none == "**promote**":
        failures.append("ADV2-012 promote without effective")
    rec_empty = _recommendation(0.99, 100, "f", set())
    if rec_empty == "**promote**":
        failures.append("ADV2-012 promote when flag not in effective")
    rec_ok = _recommendation(0.99, 100, "f", {"f"})
    if rec_ok != "**promote**":
        failures.append(f"ADV2-012 expected **promote** got {rec_ok}")
    if failures:
        print(json.dumps({"self_test": "FAIL", "failures": failures}))
        return 1
    print(json.dumps({"self_test": "PASS"}))
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--self-test", action="store_true")
    args = p.parse_args()
    if args.self_test:
        sys.exit(self_test())
    main()
