#!/usr/bin/env python3
"""staleness-monitor.py — Monitor freshness of critical Hermes log files.

D2 liveness fix (Lynch, Distributed Algorithms §8): liveness property
AF(log_written) — critical logs must be written within expected intervals.
If a log is absent or stale beyond threshold, emit an alarm entry.

Monitored files (with their correct cache locations):
  - routing-calibration.jsonl: base cache, 48h  (routing-weight-updater input)
  - calibration-log.jsonl:     base cache, 48h  (gate-audit threshold input)
  - skill-beta-state.json:     profile cache, 24h (bandit posteriors)
  - routing-regret-log.jsonl:  profile cache, 48h (FTRL vs uniform)
  - skill-router-index.json:   profile cache, 72h (skill routing index)
"""
from __future__ import annotations
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

BASE_CACHE    = _hermes_base / "cache"
PROFILE_CACHE = _hermes_root / "cache"
ALARM_PATH    = PROFILE_CACHE / "staleness-alarms.jsonl"

# (filename, cache_dir, max_age_seconds)
MONITORED = [
    ("routing-calibration.jsonl",  BASE_CACHE,    48 * 3600),
    ("calibration-log.jsonl",      BASE_CACHE,    48 * 3600),
    ("skill-beta-state.json",      PROFILE_CACHE, 24 * 3600),
    ("routing-regret-log.jsonl",   PROFILE_CACHE, 48 * 3600),
    ("skill-router-index.json",    PROFILE_CACHE, 72 * 3600),
]

def main():
    now = time.time()
    alarms = []
    ok = []
    for fname, cache_dir, max_age_s in MONITORED:
        fpath = cache_dir / fname
        if not fpath.exists():
            alarms.append({"file": fname, "issue": "missing", "path": str(fpath),
                           "max_age_h": max_age_s / 3600})
        else:
            age_s = now - fpath.stat().st_mtime
            age_h = age_s / 3600
            if age_s > max_age_s:
                alarms.append({"file": fname, "issue": "stale", "age_h": round(age_h, 1),
                               "max_age_h": max_age_s / 3600, "path": str(fpath)})
            else:
                ok.append(f"{fname} ({age_h:.1f}h old)")

    for entry in ok:
        print(f"[OK] {entry}")

    if alarms:
        ALARM_PATH.parent.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        for a in alarms:
            a["ts"] = ts
            with open(ALARM_PATH, "a") as f:
                f.write(json.dumps(a) + "\n")
            print(f"[ALARM] {a['file']}: {a['issue']} (max {a['max_age_h']:.0f}h)", file=sys.stderr)
    else:
        print(f"[staleness-monitor] All {len(ok)} monitored files are fresh.")
    # exit 0 always: cron-safe (Clarke et al. AG(monitor→safe))
    sys.exit(0)

if __name__ == "__main__":
    main()
