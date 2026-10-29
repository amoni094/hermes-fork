#!/usr/bin/env python3
"""Power-of-two-choices offset rebalancer for cron fire times (Motwani Ch 3).

Only apply at insert/rebase — never jitter already-claimed due jobs.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from collections import Counter
from datetime import datetime, timezone, UTC
from pathlib import Path

_hermes_base = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_hermes_profile = os.environ.get("HERMES_PROFILE", "")
_hermes_root = (
    (_hermes_base / "profiles" / _hermes_profile)
    if _hermes_profile and "profiles" not in str(_hermes_base)
    else _hermes_base
)
JOBS_PATH = _hermes_root / "cron" / "jobs.json"


def minute_bin(ts: int) -> int:
    return (int(ts) // 60) % (24 * 60)


def load_histogram(next_runs: list[int]) -> Counter:
    return Counter(minute_bin(t) for t in next_runs)


def two_choice_offset(existing_next_runs: list[int], period_s: int, rng=None) -> int:
    """Pick an offset in [0, period) by probing two candidate first-fire times."""
    rng = rng or random.Random()
    try:
        period_s = int(period_s or 0)
    except (TypeError, ValueError):
        period_s = 0
    if period_s <= 0:
        return 0
    hist = load_histogram([int(t) for t in existing_next_runs if t is not None])
    a = rng.randrange(period_s)
    b = rng.randrange(period_s)
    now = int(time.time())
    la = hist[minute_bin(now + a)]
    lb = hist[minute_bin(now + b)]
    return a if la <= lb else b


def _parse_next_run(job: dict) -> int | None:
    raw = job.get("next_run_at")
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return int(raw)
    try:
        dt = datetime.fromisoformat(str(raw))
        return int(dt.timestamp())
    except (TypeError, ValueError):
        return None


def _load_jobs_obj(path: Path):
    raw = path.read_bytes().decode("utf-8", errors="replace")
    return json.loads(raw)


def rebalance_offsets(jobs_path, rng=None, dry_run: bool = True) -> dict:
    """Rebase unclaimed recurring jobs onto lighter minute bins.

    Does not touch jobs with a live fire_claim (at-most-once).
    """
    rng = rng or random.Random()
    path = Path(jobs_path)
    obj = _load_jobs_obj(path)
    jobs = obj.get("jobs") if isinstance(obj, dict) else obj
    if not isinstance(jobs, list):
        return {"ok": False, "error": "jobs not a list"}
    existing = []
    for j in jobs:
        ts = _parse_next_run(j) if isinstance(j, dict) else None
        if ts is not None:
            existing.append(ts)
    moved = 0
    for j in jobs:
        if not isinstance(j, dict):
            continue
        if j.get("fire_claim"):
            continue
        sched = j.get("schedule") or {}
        if str(sched.get("kind") or "") != "cron":
            continue
        period = 3600
        expr = str(sched.get("expr") or "")
        parts = expr.split()
        if len(parts) == 5 and parts[1] not in ("*", "?"):
            period = 86400
        elif len(parts) == 5 and parts[0].startswith("*/"):
            try:
                period = int(parts[0][2:]) * 60
            except (TypeError, ValueError):
                period = 3600
        off = two_choice_offset(existing, period, rng)
        now = int(time.time())
        new_ts = now + off
        old = _parse_next_run(j)
        if old is None or minute_bin(old) != minute_bin(new_ts):
            moved += 1
        existing.append(new_ts)
        if not dry_run:
            j["next_run_at"] = datetime.fromtimestamp(new_ts, tz=UTC).isoformat()
    if not dry_run and isinstance(obj, dict):
        obj["updated_at"] = datetime.now(UTC).isoformat()
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(obj, indent=2), encoding="utf-8")
        os.replace(str(tmp), str(path))
    hist = load_histogram(existing)
    max_load = max(hist.values()) if hist else 0
    return {"ok": True, "moved": moved, "max_bin": max_load, "dry_run": dry_run, "n": len(jobs)}


def _self_test() -> int:
    rng = random.Random(0)
    off = two_choice_offset([0] * 20, 3600, rng)
    assert 0 <= off < 3600
    hist = load_histogram([0, 60, 60, 120])
    assert hist[1] == 2
    assert minute_bin(0) == 0
    print(json.dumps({"ok": True, "offset": off, "hist": dict(hist)}))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Two-choice cron offset rebalancer")
    p.add_argument("--self-test", action="store_true")
    p.add_argument("--apply", action="store_true", help="write jobs.json (default dry-run)")
    p.add_argument("--jobs", default=str(JOBS_PATH))
    args = p.parse_args(argv)
    if args.self_test:
        return _self_test()
    report = rebalance_offsets(args.jobs, dry_run=not args.apply)
    print(json.dumps(report))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
