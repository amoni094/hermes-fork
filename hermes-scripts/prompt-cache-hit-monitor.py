#!/usr/bin/env python3
"""Prompt-cache hit-rate monitor (single-user cost/latency).

Reads agent.log ``cache=R/P (Q%) write=W`` lines and session_model_usage
(cache_read_tokens / cache_write_tokens). Writes cache/prompt-cache-hit.json
and optional *-alarm.json for alarm-aggregator.

stdlib only. Fail-open. --self-test / --run.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone, UTC
from pathlib import Path

API_RE = re.compile(
    r"API call #(\d+): model=(\S+) provider=(\S+) in=(\d+) out=(\d+) "
    r"total=(\d+) latency=([\d.]+)s"
    r"(?: cache=(\d+)/(\d+) \((\d+)%\))?"
    r"(?: write=(\d+))?"
)
TS_RE = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})")
WINDOW_S = 24 * 3600
MIN_CALLS_ALARM = 20
HIT_WARN = 0.50
HIT_HIGH = 0.25
CACHE_MODELS = ("claude", "anthropic", "sonnet", "haiku", "opus", "gpt-", "o1", "o3", "o4")


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


def _parse_log_ts(line: str) -> float | None:
    m = TS_RE.match(line)
    if not m:
        return None
    try:
        dt = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")
        return dt.replace(tzinfo=datetime.now().astimezone().tzinfo).timestamp()
    except ValueError:
        return None


def _log_paths(home: Path, root: Path) -> list[Path]:
    out: list[Path] = []
    seen: set[Path] = set()
    for d in (home / "logs", root / "logs"):
        if not d.is_dir():
            continue
        for name in ("agent.log", "agent.log.1", "agent.log.2"):
            p = d / name
            rp = p.resolve() if p.exists() else p
            if p.is_file() and rp not in seen:
                seen.add(rp)
                out.append(p)
    return out


def _supports_cache(model: str) -> bool:
    m = (model or "").lower()
    return any(tok in m for tok in CACHE_MODELS)


def parse_api_line(line: str) -> dict | None:
    idx = line.find("API call #")
    if idx < 0:
        return None
    m = API_RE.search(line[idx:])
    if not m:
        return None
    cache_read = int(m.group(8) or 0)
    prompt = int(m.group(9) or m.group(4) or 0)
    pct = int(m.group(10) or 0)
    write = int(m.group(11) or 0)
    if m.group(8) is None:
        prompt = int(m.group(4) or 0)
        pct = 0
    return {
        "n": int(m.group(1)),
        "model": m.group(2),
        "provider": m.group(3),
        "prompt_tokens": int(m.group(4)),
        "completion_tokens": int(m.group(5)),
        "total_tokens": int(m.group(6)),
        "latency_s": float(m.group(7)),
        "cache_read": cache_read,
        "cache_prompt": prompt,
        "cache_pct": pct,
        "cache_write": write,
    }


def scan_logs(paths: list[Path], cutoff: float) -> list[dict]:
    rows: list[dict] = []
    for path in paths:
        try:
            with path.open(errors="replace") as fh:
                for line in fh:
                    if "API call #" not in line:
                        continue
                    ts = _parse_log_ts(line)
                    if ts is not None and ts < cutoff:
                        continue
                    rec = parse_api_line(line)
                    if rec is None:
                        continue
                    rec["ts"] = ts
                    rec["src"] = path.name
                    rows.append(rec)
        except OSError:
            continue
    return rows


def scan_usage_db(dbs: list[Path]) -> dict:
    totals = {
        "api_call_count": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_read_tokens": 0,
        "cache_write_tokens": 0,
        "reasoning_tokens": 0,
        "sessions": 0,
        "by_model": {},
    }
    seen: set[Path] = set()
    for db in dbs:
        if not db.is_file():
            continue
        rp = db.resolve()
        if rp in seen:
            continue
        seen.add(rp)
        try:
            con = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=2)
        except sqlite3.Error:
            continue
        try:
            try:
                con.execute("PRAGMA busy_timeout=5000")
                con.execute("PRAGMA journal_mode=WAL")
            except sqlite3.Error:
                pass
            cur = con.execute(
                "SELECT model, SUM(api_call_count), SUM(input_tokens), SUM(output_tokens), "
                "SUM(cache_read_tokens), SUM(cache_write_tokens), SUM(reasoning_tokens), "
                "COUNT(*) FROM session_model_usage GROUP BY model"
            )
            for model, calls, inn, out, cr, cw, rt, n in cur:
                model = model or "unknown"
                rec = totals["by_model"].setdefault(
                    model,
                    {
                        "api_call_count": 0,
                        "input_tokens": 0,
                        "output_tokens": 0,
                        "cache_read_tokens": 0,
                        "cache_write_tokens": 0,
                        "reasoning_tokens": 0,
                        "rows": 0,
                    },
                )
                rec["api_call_count"] += int(calls or 0)
                rec["input_tokens"] += int(inn or 0)
                rec["output_tokens"] += int(out or 0)
                rec["cache_read_tokens"] += int(cr or 0)
                rec["cache_write_tokens"] += int(cw or 0)
                rec["reasoning_tokens"] += int(rt or 0)
                rec["rows"] += int(n or 0)
                totals["api_call_count"] += int(calls or 0)
                totals["input_tokens"] += int(inn or 0)
                totals["output_tokens"] += int(out or 0)
                totals["cache_read_tokens"] += int(cr or 0)
                totals["cache_write_tokens"] += int(cw or 0)
                totals["reasoning_tokens"] += int(rt or 0)
                totals["sessions"] += int(n or 0)
        except sqlite3.Error:
            continue
        finally:
            try:
                con.close()
            except sqlite3.Error:
                pass
    return totals


def _hit_rate(read: int, prompt: int) -> float | None:
    denom = read + prompt
    if denom <= 0:
        return None
    return read / denom


def build_report(log_rows: list[dict], db_tot: dict) -> dict:
    by_model: dict[str, dict] = defaultdict(
        lambda: {
            "n": 0,
            "cache_read": 0,
            "prompt": 0,
            "cache_write": 0,
            "pct_sum": 0,
            "cold_writes": 0,
        }
    )
    n_with_cache_field = 0
    for r in log_rows:
        b = by_model[r["model"]]
        b["n"] += 1
        b["cache_read"] += r["cache_read"]
        # P in cache=R/P is the prompt denominator; do not add cache_read+prompt.
        denom = int(r.get("cache_prompt") or r.get("prompt_tokens") or 0)
        b["prompt"] += denom
        b["cache_write"] += r["cache_write"]
        b["pct_sum"] += r["cache_pct"]
        if r["cache_write"] > 0 and r["cache_pct"] < 50:
            b["cold_writes"] += 1
        if r["cache_read"] or r["cache_pct"]:
            n_with_cache_field += 1

    log_models = {}
    for model, b in by_model.items():
        n = b["n"] or 1
        log_hit = (b["cache_read"] / b["prompt"]) if b["prompt"] else None
        log_models[model] = {
            "n": b["n"],
            "cache_read": b["cache_read"],
            "prompt_tokens": b["prompt"],
            "cache_write": b["cache_write"],
            "mean_cache_pct": round(b["pct_sum"] / n, 2),
            "cold_writes": b["cold_writes"],
            "hit_rate": log_hit,
        }

    cr = int(db_tot.get("cache_read_tokens") or 0)
    inn = int(db_tot.get("input_tokens") or 0)
    db_hit = _hit_rate(cr, inn)

    alarms: list[dict] = []
    cache_n = 0
    cache_hit_weighted = 0.0
    for model, rec in log_models.items():
        if not _supports_cache(model):
            continue
        cache_n += rec["n"]
        if rec["hit_rate"] is not None:
            cache_hit_weighted += rec["hit_rate"] * rec["n"]
        if rec["n"] >= MIN_CALLS_ALARM and rec["hit_rate"] is not None:
            if rec["hit_rate"] < HIT_HIGH:
                alarms.append(
                    {
                        "severity": "HIGH",
                        "model": model,
                        "hit_rate": round(rec["hit_rate"], 4),
                        "n": rec["n"],
                        "why": "prompt-cache hit rate below 25% on a cache-capable model",
                    }
                )
            elif rec["hit_rate"] < HIT_WARN:
                alarms.append(
                    {
                        "severity": "MEDIUM",
                        "model": model,
                        "hit_rate": round(rec["hit_rate"], 4),
                        "n": rec["n"],
                        "why": "prompt-cache hit rate below 50% on a cache-capable model",
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
        "log_calls": len(log_rows),
        "log_calls_with_cache_field": n_with_cache_field,
        "log_by_model": log_models,
        "db_usage": {
            "api_call_count": db_tot.get("api_call_count", 0),
            "input_tokens": inn,
            "output_tokens": db_tot.get("output_tokens", 0),
            "cache_read_tokens": cr,
            "cache_write_tokens": db_tot.get("cache_write_tokens", 0),
            "reasoning_tokens": db_tot.get("reasoning_tokens", 0),
            "hit_rate": db_hit,
            "by_model": db_tot.get("by_model", {}),
        },
        "weighted_log_hit_rate": (
            round(cache_hit_weighted / cache_n, 4) if cache_n else None
        ),
        "alarms": alarms,
        "theory": "Anthropic/OpenAI prompt-cache hit rate; prefix instability via cold writes",
    }


def _self_test() -> int:
    home = _hermes_home()
    os.environ["HERMES_HOME"] = str(home / "profiles" / "fork")
    stripped = _hermes_home()
    assert stripped == home, (stripped, home)
    os.environ["HERMES_HOME"] = str(home)

    line = (
        "2026-11-06 11:00:55,474 - agent.turn_usage - INFO - "
        "API call #1: model=claude-sonnet-4-6 provider=anthropic "
        "in=269 out=88 total=357 latency=2.3s cache=91541/91700 (99%) write=400"
    )
    rec = parse_api_line(line)
    assert rec is not None
    assert rec["cache_read"] == 91541
    assert rec["cache_pct"] == 99
    assert rec["cache_write"] == 400
    assert rec["cache_prompt"] == 91700
    miss = parse_api_line(
        "API call #2: model=grok-4.6 provider=xai in=100 out=10 total=110 latency=1.0s"
    )
    assert miss is not None and miss["cache_read"] == 0 and miss["cache_pct"] == 0
    assert parse_api_line("nope") is None
    assert _hit_rate(0, 0) is None
    assert abs((_hit_rate(90, 10) or 0) - 0.9) < 1e-9
    report = build_report([rec, miss], {"cache_read_tokens": 90, "input_tokens": 10})
    assert "status" in report
    claude_hit = report["log_by_model"]["claude-sonnet-4-6"]["hit_rate"]
    assert claude_hit is not None and claude_hit > 0.9
    tmp = Path(os.environ.get("TMPDIR") or "/tmp") / "prompt-cache-hit-selftest.json"
    _atomic_write(tmp, {"ok": True})
    assert tmp.is_file()
    tmp.unlink(missing_ok=True)
    print(json.dumps({"status": "ok", "self_test": True}))
    return 0


def _run() -> int:
    home = _hermes_home()
    root = _hermes_root()
    cutoff = time.time() - WINDOW_S
    rows = scan_logs(_log_paths(home, root), cutoff)
    dbs = [home / "state.db", root / "state.db"]
    db_tot = scan_usage_db(dbs)
    report = build_report(rows, db_tot)
    out = root / "cache" / "prompt-cache-hit.json"
    _atomic_write(out, report)
    alarm_path = root / "cache" / "prompt-cache-hit-alarm.json"
    if report["status"] in {"warn", "alarm"} and report["alarms"]:
        sev = "HIGH" if report["status"] == "alarm" else "MEDIUM"
        _atomic_write(
            alarm_path,
            {
                "ts": report["ts"],
                "name": "prompt-cache-hit-monitor",
                "severity": sev,
                "status": report["status"],
                "summary": f"prompt-cache {report['status']}: {len(report['alarms'])} model(s)",
                "alarms": report["alarms"],
            },
        )
    elif alarm_path.exists():
        try:
            alarm_path.unlink()
        except OSError:
            pass
    print(json.dumps({"status": report["status"], "out": str(out), "log_calls": report["log_calls"]}))
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
