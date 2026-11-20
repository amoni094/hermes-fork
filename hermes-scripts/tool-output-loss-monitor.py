#!/usr/bin/env python3
"""Tool-output loss monitor (truncation hiding useful data).

Scans profile/base state.db messages for the gateway truncation_notice marker
``TRUNCATED - N bytes/chars omitted out of M total``. Writes
cache/tool-output-loss.json (+ optional alarm).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
import time
from datetime import datetime, timezone, UTC
from pathlib import Path

NOTICE_RE = re.compile(
    r"TRUNCATED -\s*([0-9,]+)\s+(bytes|chars)\s+omitted out of\s+([0-9,]+)\s+total",
    re.IGNORECASE,
)
WINDOW_S = 7 * 24 * 3600
LOSS_RATIO_HIGH = 0.70
N_EVENTS_WARN = 5
N_EVENTS_HIGH = 20


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


def parse_notice(text: str) -> dict | None:
    m = NOTICE_RE.search(text or "")
    if not m:
        return None
    omitted = int(m.group(1).replace(",", ""))
    unit = m.group(2).lower()
    total = int(m.group(3).replace(",", ""))
    if total <= 0:
        return None
    return {
        "omitted": omitted,
        "unit": unit,
        "total": total,
        "kept": max(0, total - omitted),
        "loss_ratio": omitted / total,
    }


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


def scan_db(db: Path, cutoff: float) -> list[dict]:
    if not db.is_file():
        return []
    try:
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=2)
    except sqlite3.Error:
        return []
    events: list[dict] = []
    try:
        try:
            con.execute("PRAGMA busy_timeout=5000")
            con.execute("PRAGMA journal_mode=WAL")
        except sqlite3.Error:
            pass
        cur = con.execute(
            "SELECT session_id, tool_name, timestamp, content FROM messages "
            "WHERE content LIKE '%TRUNCATED -%'"
        )
        for sid, tool, ts, content in cur:
            parsed = parse_notice(content or "")
            if parsed is None:
                continue
            epoch = _as_epoch(ts)
            if epoch is not None and epoch < cutoff:
                continue
            events.append(
                {
                    "session_id": sid or "",
                    "tool_name": tool or "",
                    "ts": epoch,
                    **parsed,
                }
            )
    except sqlite3.Error:
        return events
    finally:
        try:
            con.close()
        except sqlite3.Error:
            pass
    return events


def merge_events(batches: list[list[dict]]) -> list[dict]:
    seen: set[tuple] = set()
    out: list[dict] = []
    for batch in batches:
        for ev in batch:
            key = (
                ev.get("session_id"),
                ev.get("ts"),
                ev.get("omitted"),
                ev.get("total"),
                ev.get("tool_name"),
            )
            if key in seen:
                continue
            seen.add(key)
            out.append(ev)
    return out


def build_report(events: list[dict]) -> dict:
    n = len(events)
    high_loss = [e for e in events if float(e.get("loss_ratio") or 0) >= LOSS_RATIO_HIGH]
    by_tool: dict[str, int] = {}
    omitted_sum = 0
    total_sum = 0
    for e in events:
        t = e.get("tool_name") or "unknown"
        by_tool[t] = by_tool.get(t, 0) + 1
        omitted_sum += int(e.get("omitted") or 0)
        total_sum += int(e.get("total") or 0)
    alarms: list[dict] = []
    if n >= N_EVENTS_HIGH:
        alarms.append({"severity": "HIGH", "why": "many truncation events", "n": n})
    elif n >= N_EVENTS_WARN:
        alarms.append({"severity": "MEDIUM", "why": "truncation events in window", "n": n})
    if high_loss:
        worst = max(high_loss, key=lambda e: float(e.get("loss_ratio") or 0))
        alarms.append(
            {
                "severity": "HIGH" if float(worst["loss_ratio"]) >= 0.85 else "MEDIUM",
                "why": "single tool result dropped most of its payload",
                "loss_ratio": round(float(worst["loss_ratio"]), 4),
                "omitted": worst.get("omitted"),
                "total": worst.get("total"),
                "tool_name": worst.get("tool_name") or None,
            }
        )
    status = "ok"
    if any(a["severity"] == "HIGH" for a in alarms):
        status = "alarm"
    elif alarms:
        status = "warn"
    top_events = sorted(events, key=lambda e: float(e.get("loss_ratio") or 0), reverse=True)[:8]
    slim = [
        {
            "session_id": e.get("session_id"),
            "tool_name": e.get("tool_name"),
            "omitted": e.get("omitted"),
            "total": e.get("total"),
            "loss_ratio": round(float(e.get("loss_ratio") or 0), 4),
            "unit": e.get("unit"),
        }
        for e in top_events
    ]
    return {
        "ts": _now().isoformat(),
        "window_s": WINDOW_S,
        "status": status,
        "n_events": n,
        "n_high_loss": len(high_loss),
        "omitted_sum": omitted_sum,
        "total_sum": total_sum,
        "mean_loss_ratio": round(omitted_sum / total_sum, 4) if total_sum else None,
        "by_tool": by_tool,
        "worst": slim,
        "alarms": alarms,
        "theory": "tools.tool_output_truncate.truncation_notice",
    }


def _self_test() -> int:
    home = _hermes_home()
    os.environ["HERMES_HOME"] = str(home / "profiles" / "fork")
    assert _hermes_home() == home
    os.environ["HERMES_HOME"] = str(home)
    p = parse_notice("[... TRUNCATED - 118,523 bytes omitted out of 168,523 total]")
    assert p is not None
    assert p["omitted"] == 118523
    assert p["total"] == 168523
    assert parse_notice("hello") is None
    events = [
        {"session_id": "s", "tool_name": "terminal", "omitted": 90, "total": 100, "loss_ratio": 0.9, "unit": "bytes"},
        {"session_id": "s2", "tool_name": "read_file", "omitted": 10, "total": 100, "loss_ratio": 0.1, "unit": "chars"},
    ]
    report = build_report(events)
    assert report["n_events"] == 2
    assert report["status"] in {"warn", "alarm"}
    print(json.dumps({"status": "ok", "self_test": True}))
    return 0


def _run() -> int:
    home = _hermes_home()
    root = _hermes_root()
    cutoff = time.time() - WINDOW_S
    events = merge_events(
        [
            scan_db(root / "state.db", cutoff),
            scan_db(home / "state.db", cutoff),
        ]
    )
    # live plugin jsonl if present
    plugin_log = root / "cache" / "tool-output-loss.jsonl"
    if plugin_log.is_file():
        try:
            extra: list[dict] = []
            with plugin_log.open() as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if rec.get("scope") == "ue_blackbox":
                        continue
                    if "omitted" in rec and "total" in rec:
                        extra.append(rec)
            events = merge_events([events, extra])
        except OSError:
            pass
    report = build_report(events)
    out = root / "cache" / "tool-output-loss.json"
    _atomic_write(out, report)
    alarm_path = root / "cache" / "tool-output-loss-alarm.json"
    if report["status"] in {"warn", "alarm"} and report["alarms"]:
        sev = "HIGH" if report["status"] == "alarm" else "MEDIUM"
        _atomic_write(
            alarm_path,
            {
                "ts": report["ts"],
                "name": "tool-output-loss-monitor",
                "severity": sev,
                "status": report["status"],
                "summary": f"tool truncation n={report['n_events']} mean_loss={report['mean_loss_ratio']}",
                "alarms": report["alarms"],
            },
        )
    elif alarm_path.exists():
        try:
            alarm_path.unlink()
        except OSError:
            pass
    print(json.dumps({"status": report["status"], "out": str(out), "n": report["n_events"]}))
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
