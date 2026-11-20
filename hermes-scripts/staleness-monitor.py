#!/usr/bin/env python3
"""staleness-monitor.py — Monitor freshness of critical Hermes log files.

D2 liveness fix (Lynch, Distributed Algorithms §8): liveness property
AF(log_written) — critical logs must be written within expected intervals.
If a log is absent or stale beyond threshold, emit an alarm entry.

Monitored files and their max-stale thresholds:
  - routing-calibration.jsonl: 48h (routing-weight-updater depends on it)
  - calibration-log.jsonl: 48h (gate-audit / threshold-updater reads it)
  - skill-beta-state.json: 24h (bandit posteriors must be updated regularly)
  - routing-regret-log.jsonl: 48h (FTRL vs uniform comparison)
  - msprt-shadow-gate.json: 26h (mSPRT gate calibration)
  - block-bootstrap-sprt.json: 48h (SPRT A_boot calibration)
  - cusum-h-calibration.json: 168h (CUSUM h* weekly recalibration)
"""
from __future__ import annotations
import os
import json, os, sys, time
from pathlib import Path

_hermes_base = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_hermes_profile = os.environ.get("HERMES_PROFILE", "")
_hermes_root = (
    (_hermes_base / "profiles" / _hermes_profile)
    if _hermes_profile and "profiles" not in str(_hermes_base)
    else _hermes_base
)

if not _hermes_base.is_dir():
    print(f"ERROR: HERMES_HOME={_hermes_base} does not exist", file=sys.stderr)
    sys.exit(2)

ALARM_PATH = _hermes_root / "cache" / "staleness-alarms.jsonl"
CACHE_DIR = _hermes_root / "cache"

# (filename, max_age_hours, label)
MONITORED = [
    ("routing-calibration.jsonl", 48, "routing calibration"),
    ("calibration-log.jsonl",     48, "gate-audit / threshold-updater"),
    ("skill-beta-state.json",     24, "bandit posteriors"),
    ("routing-regret-log.jsonl",  48, "FTRL vs uniform"),
    ("msprt-shadow-gate.json",    26, "msprt gate calibration"),
    ("block-bootstrap-sprt.json", 48, "SPRT A_boot calibration"),
    ("cusum-h-calibration.json", 168, "CUSUM h* calibration (weekly recalibration)"),
]
CHECKS = MONITORED

def main():
    now = time.time()
    alarms = []
    ok = []
    for fname, max_age_h, label in MONITORED:
        max_age_s = max_age_h * 3600
        fpath = CACHE_DIR / fname
        if not fpath.exists():
            alarms.append({
                "file": fname, "issue": "missing",
                "max_age_h": max_age_h, "label": label,
            })
        else:
            age_s = now - fpath.stat().st_mtime
            age_h = age_s / 3600
            if age_s > max_age_s:
                alarms.append({
                    "file": fname, "issue": "stale",
                    "age_h": round(age_h, 1), "max_age_h": max_age_h,
                    "label": label,
                })
            else:
                ok.append(f"{fname} ({age_h:.1f}h old, {label})")

    for entry in ok:
        print(f"[OK] {entry}")

    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if alarms:
        for a in alarms:
            a["ts"] = ts
            with open(ALARM_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(a) + "\n")
            print(f"[ALARM] {a['file']}: {a['issue']} (max {a['max_age_h']}h)", file=sys.stderr)
    else:
        print(f"[staleness-monitor] All {len(ok)} monitored files are fresh.")

    # Aggregator glob is *-alarm.json (ADV2-011). jsonl stays as the detailed record.
    sidecar = {
        "alarm": bool(alarms),
        "alarms": alarms,
        "written_at": ts,
    }
    sidecar_path = CACHE_DIR / "staleness-alarm.json"
    tmp = sidecar_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(sidecar, indent=2) + "\n")
    os.replace(tmp, sidecar_path)
    # exit 0: alarms written; cron-safe (Clarke et al. AG(monitor→safe))
    return 0


def self_test() -> int:
    failures = []
    names = [c[0] for c in CHECKS]
    if "cusum-h-calibration.json" not in names:
        failures.append("CHECKS missing cusum-h-calibration.json")
    row = next((c for c in CHECKS if c[0] == "cusum-h-calibration.json"), None)
    if row is None or row[1] != 168:
        failures.append(f"cusum max_age != 168: {row}")
    if failures:
        print(json.dumps({"self_test": "FAIL", "failures": failures}))
        return 1
    print(json.dumps({"self_test": "PASS", "n_checks": len(CHECKS)}))
    return 0


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(self_test())
    sys.exit(main() or 0)
