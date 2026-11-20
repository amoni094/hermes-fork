#!/usr/bin/env python3
"""Circadian skill/tool prewarm schedule from calibration-log.jsonl.

Hour-of-day histograms (Australia/Sydney) of tool_name and non-blackbox scope.
Writes cache/circadian-prewarm.json with the next hour's likely tools.

HARD RULE: skip scope=='ue_blackbox' entirely (no tool_name fallback).

stdlib only. Fail-open. --self-test and --run.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone, UTC
from pathlib import Path
from zoneinfo import ZoneInfo

TZ_NAME = "Australia/Sydney"
TOP_K = 12
MIN_ROWS = 50


def _hermes_home() -> Path:
    env = os.environ.get("HERMES_HOME", "").strip()
    p = Path(env) if env else Path.home() / ".hermes"
    if p.name != ".hermes" and p.parent.name == "profiles":
        return p.parent.parent
    return p


def _profile_name() -> str:
    profile = os.environ.get("HERMES_PROFILE", "").strip()
    if profile:
        return profile
    raw = os.environ.get("HERMES_HOME", "").strip()
    if raw:
        p = Path(raw)
        if p.parent.name == "profiles":
            return p.name
    if (_hermes_home() / "profiles" / "fork").exists():
        return "fork"
    return ""


def _hermes_root() -> Path:
    base = _hermes_home()
    profile = _profile_name()
    return (base / "profiles" / profile) if profile else base


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _atomic_write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_suffix(path.suffix + ".lock")
    tmp = path.with_name(path.name + ".tmp")
    payload = json.dumps(obj, indent=2) + "\n"
    with open(str(lock), "a", encoding="utf-8") as lf:
        fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
        try:
            tmp.write_text(payload, encoding="utf-8")
            os.replace(str(tmp), str(path))
        finally:
            fcntl.flock(lf.fileno(), fcntl.LOCK_UN)


def _tz() -> timezone | ZoneInfo:
    try:
        return ZoneInfo(TZ_NAME)
    except Exception:
        return timezone(timedelta(hours=11), name="AEDT")


def parse_ts(value) -> datetime | None:
    if not value:
        return None
    text = str(value).strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt


def ingest(calib_path: Path) -> tuple[dict[int, Counter], dict[int, Counter], int, int]:
    tools: dict[int, Counter] = defaultdict(Counter)
    skills: dict[int, Counter] = defaultdict(Counter)
    skipped_ue = 0
    kept = 0
    tz = _tz()
    if not calib_path.exists():
        return tools, skills, skipped_ue, kept
    try:
        fh = calib_path.open(encoding="utf-8", errors="replace")
    except OSError:
        return tools, skills, skipped_ue, kept
    with fh:
        for line in fh:
            raw = line.strip()
            if not raw:
                continue
            try:
                rec = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if not isinstance(rec, dict):
                continue
            if rec.get("scope") == "ue_blackbox":
                skipped_ue += 1
                continue
            dt = parse_ts(rec.get("ts"))
            if dt is None:
                continue
            hour = dt.astimezone(tz).hour
            tool = rec.get("tool_name")
            if tool:
                tools[hour][str(tool)] += 1
                kept += 1
            scope = rec.get("scope")
            if scope and scope != "ue_blackbox":
                skills[hour][str(scope)] += 1
    return tools, skills, skipped_ue, kept


def top_for_hour(counter: Counter, k: int = TOP_K) -> list[dict]:
    total = sum(counter.values()) or 1
    return [
        {"name": name, "n": n, "p": n / total}
        for name, n in counter.most_common(k)
    ]


def build_report(tools, skills, skipped_ue: int, kept: int, now: datetime | None = None) -> dict:
    tz = _tz()
    now = now or datetime.now(tz)
    hour = now.astimezone(tz).hour
    nxt = (hour + 1) % 24
    if kept < MIN_ROWS:
        status = "insufficient_data"
    else:
        status = "ok"
    return {
        "ts": _now(),
        "status": status,
        "tz": TZ_NAME,
        "hour": hour,
        "next_hour": nxt,
        "kept_rows": kept,
        "skipped_ue_blackbox": skipped_ue,
        "next_hour_tools": top_for_hour(tools.get(nxt, Counter())),
        "next_hour_skills": top_for_hour(skills.get(nxt, Counter())),
        "this_hour_tools": top_for_hour(tools.get(hour, Counter())),
        "theory": "circadian demand histogram for single-user laptop prewarm",
    }


def run(root: Path | None = None) -> dict:
    root = root or _hermes_root()
    tools, skills, skipped_ue, kept = ingest(root / "cache" / "calibration-log.jsonl")
    report = build_report(tools, skills, skipped_ue, kept)
    _atomic_write(root / "cache" / "circadian-prewarm.json", report)
    return report


def _self_test() -> int:
    os.environ["HERMES_HOME"] = str(Path.home() / ".hermes" / "profiles" / "fork")
    assert _hermes_home() == Path.home() / ".hermes"
    dt = parse_ts("2026-11-06T03:00:00Z")
    assert dt is not None
    tools: dict[int, Counter] = defaultdict(Counter)
    tools[14]["terminal"] = 10
    tools[14]["read_file"] = 5
    report = build_report(tools, {}, 3, 200, now=datetime(2026, 11, 6, 13, 0, tzinfo=_tz()))
    assert report["status"] == "ok"
    assert report["next_hour"] == 14
    assert report["next_hour_tools"][0]["name"] == "terminal"
    assert report["skipped_ue_blackbox"] == 3
    empty = build_report({}, {}, 0, 0)
    assert empty["status"] == "insufficient_data"
    print("[circadian-skill-prewarm] --self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Circadian skill/tool prewarm histogram")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--run", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        try:
            return _self_test()
        except Exception as exc:
            print(f"[circadian-skill-prewarm] --self-test FAIL: {exc}")
            return 1
    try:
        report = run()
        print(json.dumps({
            "status": report.get("status"),
            "hour": report.get("hour"),
            "next_hour": report.get("next_hour"),
            "kept_rows": report.get("kept_rows"),
            "skipped_ue_blackbox": report.get("skipped_ue_blackbox"),
            "next_hour_tools": report.get("next_hour_tools"),
            "next_hour_skills": report.get("next_hour_skills"),
        }, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "error", "reason": str(exc)}))
        return 0


if __name__ == "__main__":
    sys.exit(main())
