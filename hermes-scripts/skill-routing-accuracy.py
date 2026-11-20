#!/usr/bin/env python3
"""Skill-routing spray / miss-cascade monitor.

Counts skill_view tool_calls per session in state.db (no message body dump).
Spray = too many unique skills loaded in one session (router miss cascade).
Writes cache/skill-routing-accuracy.json (+ optional alarm).
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone, UTC
from pathlib import Path

WINDOW_S = 7 * 24 * 3600
SPRAY_UNIQUE = 10
SPRAY_CALLS = 20
UNIQUE_HIGH = 16


def _hermes_home() -> Path:
    env = os.environ.get("HERMES_HOME", "").strip()
    path = Path(env).expanduser().resolve() if env else (Path.home() / ".hermes")
    if path.name == ".hermes":
        return path
    if path.parent.name == "profiles":
        return path.parent.parent
    return path


def _profile_name() -> str:
    return os.environ.get("HERMES_PROFILE") or "fork"


def _hermes_root() -> Path:
    home = _hermes_home()
    env = os.environ.get("HERMES_HOME", "").strip()
    if env:
        p = Path(env).expanduser().resolve()
        if p.parent.name == "profiles":
            return p
    cand = home / "profiles" / _profile_name()
    return cand if cand.is_dir() else home


def _atomic_write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    data = json.dumps(payload, indent=2, default=str) + "\n"
    fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
    try:
        os.write(fd, data.encode())
        os.fsync(fd)
    finally:
        os.close(fd)
    os.replace(tmp, path)


def _now() -> datetime:
    return datetime.now(UTC)


def _as_epoch(val: object) -> float | None:
    if val is None:
        return None
    if isinstance(val, (int, float)):
        v = float(val)
        if v > 1e12:
            v /= 1000.0
        return v
    s = str(val).strip()
    if not s:
        return None
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s).timestamp()
    except ValueError:
        try:
            return float(s)
        except ValueError:
            return None


def extract_skill_name(tool_calls: object) -> list[str]:
    names: list[str] = []
    obj = tool_calls
    if isinstance(obj, str):
        try:
            obj = json.loads(obj)
        except json.JSONDecodeError:
            return names
    if not isinstance(obj, list):
        return names
    for item in obj:
        if not isinstance(item, dict):
            continue
        fn = item.get("function") if isinstance(item.get("function"), dict) else item
        name = (fn or {}).get("name") or item.get("name")
        if name != "skill_view":
            continue
        args = (fn or {}).get("arguments") or item.get("arguments") or {}
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError:
                args = {}
        if not isinstance(args, dict):
            continue
        skill = args.get("name") or args.get("skill") or ""
        skill = str(skill).strip()
        if skill:
            names.append(skill)
    return names


def scan_db(db: Path, cutoff: float) -> dict[str, list[str]]:
    per: dict[str, list[str]] = defaultdict(list)
    if not db.is_file():
        return per
    try:
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=2)
    except sqlite3.Error:
        return per
    try:
        try:
            con.execute("PRAGMA busy_timeout=5000")
            con.execute("PRAGMA journal_mode=WAL")
        except sqlite3.Error:
            pass
        cur = con.execute(
            "SELECT session_id, timestamp, tool_calls FROM messages "
            "WHERE tool_calls LIKE '%skill_view%'"
        )
        for sid, ts, raw in cur:
            epoch = _as_epoch(ts)
            if epoch is not None and epoch < cutoff:
                continue
            sid_s = sid or ""
            if not sid_s:
                continue
            for name in extract_skill_name(raw):
                per[sid_s].append(name)
    except sqlite3.Error:
        return per
    finally:
        try:
            con.close()
        except sqlite3.Error:
            pass
    return per


def merge_per(a: dict[str, list[str]], b: dict[str, list[str]]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = defaultdict(list)
    for src in (a, b):
        for sid, names in src.items():
            out[sid].extend(names)
    return out


def build_report(per: dict[str, list[str]]) -> dict:
    spray = []
    all_counts: Counter[str] = Counter()
    for sid, names in per.items():
        uniq = sorted(set(names))
        all_counts.update(uniq)
        if len(uniq) >= SPRAY_UNIQUE or len(names) >= SPRAY_CALLS:
            spray.append(
                {
                    "session_id": sid,
                    "n_calls": len(names),
                    "n_unique": len(uniq),
                    "skills": uniq[:24],
                }
            )
    spray.sort(key=lambda x: x["n_unique"], reverse=True)
    alarms: list[dict] = []
    n_high = sum(1 for s in spray if s["n_unique"] >= UNIQUE_HIGH)
    if n_high:
        alarms.append(
            {
                "severity": "HIGH",
                "why": "session loaded >= 16 unique skills (router miss cascade)",
                "n": n_high,
            }
        )
    elif spray:
        alarms.append(
            {
                "severity": "MEDIUM",
                "why": "session skill spray (unique>=10 or calls>=20)",
                "n": len(spray),
            }
        )
    status = "ok"
    if any(a["severity"] == "HIGH" for a in alarms):
        status = "alarm"
    elif alarms:
        status = "warn"
    return {
        "ts": _now().isoformat(),
        "window_s": WINDOW_S,
        "status": status,
        "n_sessions_with_skill_view": len(per),
        "n_spray_sessions": len(spray),
        "top_skills": all_counts.most_common(12),
        "spray": spray[:10],
        "alarms": alarms,
        "theory": "skill_view fan-out as proxy for router miss; unique>=10 is spray",
    }


def _self_test() -> int:
    home = _hermes_home()
    os.environ["HERMES_HOME"] = str(home / "profiles" / "fork")
    assert _hermes_home() == home
    os.environ["HERMES_HOME"] = str(home)
    raw = json.dumps(
        [
            {
                "type": "function",
                "function": {
                    "name": "skill_view",
                    "arguments": json.dumps({"name": "computer-use"}),
                },
            }
        ]
    )
    assert extract_skill_name(raw) == ["computer-use"]
    assert extract_skill_name("not json") == []
    names = [f"s{i}" for i in range(12)]
    report = build_report({"sess": names})
    assert report["n_spray_sessions"] == 1
    print(json.dumps({"status": "ok", "self_test": True}))
    return 0


def _run() -> int:
    home = _hermes_home()
    root = _hermes_root()
    cutoff = datetime.now(UTC).timestamp() - WINDOW_S
    per = merge_per(
        scan_db(root / "state.db", cutoff),
        scan_db(home / "state.db", cutoff),
    )
    report = build_report(per)
    out = root / "cache" / "skill-routing-accuracy.json"
    _atomic_write(out, report)
    alarm_path = root / "cache" / "skill-routing-accuracy-alarm.json"
    if report["status"] in {"warn", "alarm"} and report["alarms"]:
        sev = "HIGH" if report["status"] == "alarm" else "MEDIUM"
        _atomic_write(
            alarm_path,
            {
                "ts": report["ts"],
                "name": "skill-routing-accuracy",
                "severity": sev,
                "status": report["status"],
                "summary": f"spray_sessions={report['n_spray_sessions']}",
                "alarms": report["alarms"],
            },
        )
    elif alarm_path.exists():
        try:
            alarm_path.unlink()
        except OSError:
            pass
    print(
        json.dumps(
            {
                "status": report["status"],
                "out": str(out),
                "spray": report["n_spray_sessions"],
            }
        )
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-test", action="store_true")
    p.add_argument("--run", action="store_true")
    args = p.parse_args(argv)
    if args.self_test:
        return _self_test()
    # Scheduler does not pass job.args; cron argv is empty → default --run.
    try:
        return _run()
    except Exception as exc:
        print(f"fail-open: {exc}", file=sys.stderr)
        return 0


if __name__ == "__main__":
    sys.exit(main())
