#!/usr/bin/env python3
"""Reasoning-effort calibration monitor.

Uses session_model_usage.reasoning_tokens vs output_tokens. High reasoning
share on grok/xai with tiny output, or zero reasoning on long coding sessions,
is a calibration smell. Writes cache/reasoning-effort-calibration.json.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone, UTC
from pathlib import Path

REASON_SHARE_HIGH = 0.80
REASON_SHARE_MIN_OUT = 2000
ZERO_REASON_MIN_CALLS = 20
ZERO_REASON_MIN_OUT = 8000


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


def scan_db(db: Path) -> list[dict]:
    if not db.is_file():
        return []
    try:
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=2)
    except sqlite3.Error:
        return []
    rows: list[dict] = []
    try:
        try:
            con.execute("PRAGMA busy_timeout=5000")
            con.execute("PRAGMA journal_mode=WAL")
        except sqlite3.Error:
            pass
        cur = con.execute(
            "SELECT session_id, model, api_call_count, input_tokens, output_tokens, "
            "reasoning_tokens, last_seen FROM session_model_usage"
        )
        for sid, model, calls, inn, out, rt, last in cur:
            rows.append(
                {
                    "session_id": sid or "",
                    "model": model or "",
                    "api_call_count": int(calls or 0),
                    "input_tokens": int(inn or 0),
                    "output_tokens": int(out or 0),
                    "reasoning_tokens": int(rt or 0),
                    "last_seen": last,
                }
            )
    except sqlite3.Error:
        return rows
    finally:
        try:
            con.close()
        except sqlite3.Error:
            pass
    return rows


def merge_rows(batches: list[list[dict]]) -> list[dict]:
    seen: set[tuple] = set()
    out: list[dict] = []
    for batch in batches:
        for r in batch:
            key = (
                r.get("session_id"),
                r.get("model"),
                r.get("api_call_count"),
                r.get("reasoning_tokens"),
                r.get("output_tokens"),
            )
            if key in seen:
                continue
            seen.add(key)
            out.append(r)
    return out


def build_report(rows: list[dict]) -> dict:
    by_model: dict[str, dict] = {}
    high_share = []
    zero_reason = []
    for r in rows:
        model = r.get("model") or "unknown"
        slot = by_model.setdefault(
            model,
            {
                "rows": 0,
                "calls": 0,
                "output": 0,
                "reasoning": 0,
            },
        )
        slot["rows"] += 1
        slot["calls"] += r["api_call_count"]
        slot["output"] += r["output_tokens"]
        slot["reasoning"] += r["reasoning_tokens"]
        out = r["output_tokens"]
        rt = r["reasoning_tokens"]
        denom = out + rt
        share = (rt / denom) if denom else None
        if share is not None and share >= REASON_SHARE_HIGH and denom >= REASON_SHARE_MIN_OUT:
            high_share.append(
                {
                    "session_id": r["session_id"],
                    "model": model,
                    "share": round(share, 4),
                    "reasoning_tokens": rt,
                    "output_tokens": out,
                }
            )
        if (
            rt == 0
            and r["api_call_count"] >= ZERO_REASON_MIN_CALLS
            and out >= ZERO_REASON_MIN_OUT
            and "grok" in model.lower()
        ):
            zero_reason.append(
                {
                    "session_id": r["session_id"],
                    "model": model,
                    "api_call_count": r["api_call_count"],
                    "output_tokens": out,
                }
            )
    for slot in by_model.values():
        denom = slot["output"] + slot["reasoning"]
        slot["reason_share"] = round(slot["reasoning"] / denom, 4) if denom else None
    alarms: list[dict] = []
    if len(high_share) >= 3:
        alarms.append(
            {
                "severity": "MEDIUM",
                "why": "sessions with reasoning share >= 80% of (reason+output)",
                "n": len(high_share),
            }
        )
    if len(zero_reason) >= 3:
        alarms.append(
            {
                "severity": "MEDIUM",
                "why": "long grok sessions with zero reasoning_tokens",
                "n": len(zero_reason),
            }
        )
    status = "ok"
    if alarms:
        status = "warn"
    return {
        "ts": _now().isoformat(),
        "status": status,
        "n_rows": len(rows),
        "by_model": by_model,
        "high_reason_share": high_share[:8],
        "zero_reason_long": zero_reason[:8],
        "alarms": alarms,
        "theory": "session_model_usage.reasoning_tokens vs output; effort knob smell",
    }


def _self_test() -> int:
    home = _hermes_home()
    os.environ["HERMES_HOME"] = str(home / "profiles" / "fork")
    assert _hermes_home() == home
    os.environ["HERMES_HOME"] = str(home)
    rows = [
        {
            "session_id": "a",
            "model": "grok-4.6",
            "api_call_count": 30,
            "input_tokens": 1,
            "output_tokens": 100,
            "reasoning_tokens": 9000,
            "last_seen": 0,
        },
        {
            "session_id": "b",
            "model": "grok-4.6",
            "api_call_count": 25,
            "input_tokens": 1,
            "output_tokens": 9000,
            "reasoning_tokens": 0,
            "last_seen": 0,
        },
    ]
    r = build_report(rows)
    assert r["n_rows"] == 2
    print(json.dumps({"status": "ok", "self_test": True}))
    return 0


def _run() -> int:
    home = _hermes_home()
    root = _hermes_root()
    rows = merge_rows([scan_db(root / "state.db"), scan_db(home / "state.db")])
    report = build_report(rows)
    out = root / "cache" / "reasoning-effort-calibration.json"
    _atomic_write(out, report)
    alarm_path = root / "cache" / "reasoning-effort-calibration-alarm.json"
    if report["status"] in {"warn", "alarm"} and report["alarms"]:
        _atomic_write(
            alarm_path,
            {
                "ts": report["ts"],
                "name": "reasoning-effort-calibration",
                "severity": "MEDIUM",
                "status": report["status"],
                "summary": f"reasoning calibration {report['status']}",
                "alarms": report["alarms"],
            },
        )
    elif alarm_path.exists():
        try:
            alarm_path.unlink()
        except OSError:
            pass
    print(json.dumps({"status": report["status"], "out": str(out), "n": report["n_rows"]}))
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
