#!/usr/bin/env python3
"""jev-scores-staleness-check.py — Sentinel for missing jev-turn-scores producer.

WIRE-021: jev-turn-scores.jsonl has no dedicated script producer. The JEV plugin
may write it as a side-effect of live turns; nothing regenerates it on a schedule.
This sentinel fail-closes (alarm=true) when the file is missing or older than 24h.

Usage:
  python3 jev-scores-staleness-check.py --self-test
  python3 jev-scores-staleness-check.py
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from datetime import datetime, timezone, UTC
from pathlib import Path

_hermes_base = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_hermes_profile = os.environ.get("HERMES_PROFILE", "")
_hermes_root = (
    (_hermes_base / "profiles" / _hermes_profile)
    if _hermes_profile and "profiles" not in str(_hermes_base)
    else _hermes_base
)
CACHE = _hermes_root / "cache"
OUT = CACHE / "jev-scores-missing-alarm.json"
MAX_AGE_H = 24.0

CANDIDATES = (
    CACHE / "shadow-telemetry" / "jev-turn-scores.jsonl",
    CACHE / "jev-turn-scores.jsonl",
    _hermes_root / "logs" / "jev-turn-scores.jsonl",
)


def _atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _newest_scores(candidates=CANDIDATES) -> tuple[Path | None, float | None]:
    best: Path | None = None
    best_mt: float | None = None
    for p in candidates:
        try:
            mt = p.stat().st_mtime
        except OSError:
            continue
        if best_mt is None or mt > best_mt:
            best, best_mt = p, mt
    return best, best_mt


def check(now: float | None = None, candidates=CANDIDATES) -> dict:
    ts = datetime.now(UTC).isoformat()
    path, mt = _newest_scores(candidates)
    tnow = now if now is not None else time.time()
    if path is None or mt is None:
        return {
            "alarm": True,
            "reason": "no_jev_scores",
            "age_h": None,
            "path": None,
            "ts": ts,
            "note": "WIRE-021: no producer script; plugin write is opportunistic",
        }
    age_h = (tnow - mt) / 3600.0
    if age_h > MAX_AGE_H:
        return {
            "alarm": True,
            "reason": "no_jev_scores",
            "age_h": round(age_h, 3),
            "path": str(path),
            "ts": ts,
            "note": "WIRE-021: no producer script; scores older than 24h",
        }
    return {
        "alarm": False,
        "reason": None,
        "age_h": round(age_h, 3),
        "path": str(path),
        "ts": ts,
    }


def run() -> dict:
    report = check()
    try:
        _atomic_write(OUT, report)
        report["output"] = str(OUT)
    except OSError as exc:
        report["write_error"] = str(exc)
    return report


def self_test() -> int:
    failures = []
    td = Path(tempfile.mkdtemp())
    missing = check(candidates=(td / "nope.jsonl",))
    if missing.get("alarm") is not True or missing.get("reason") != "no_jev_scores":
        failures.append(f"missing: {missing}")
    fresh = td / "jev-turn-scores.jsonl"
    fresh.write_text("{}\n", encoding="utf-8")
    ok = check(candidates=(fresh,))
    if ok.get("alarm") is not False:
        failures.append(f"fresh: {ok}")
    old = td / "old.jsonl"
    old.write_text("{}\n", encoding="utf-8")
    old_t = time.time() - 25 * 3600
    os.utime(old, (old_t, old_t))
    stale = check(candidates=(old,))
    if stale.get("alarm") is not True or stale.get("reason") != "no_jev_scores":
        failures.append(f"stale: {stale}")
    if stale.get("age_h") is None or stale["age_h"] < 24:
        failures.append(f"age_h: {stale.get('age_h')}")
    if failures:
        print(json.dumps({"self_test": "FAIL", "failures": failures}))
        return 1
    print(json.dumps({"self_test": "PASS"}))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--self-test", action="store_true")
    args = p.parse_args(argv)
    if args.self_test:
        return self_test()
    out = run()
    print(json.dumps({k: out.get(k) for k in ("alarm", "reason", "age_h", "output")}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
