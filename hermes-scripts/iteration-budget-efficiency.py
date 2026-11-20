#!/usr/bin/env python3
"""Iteration-budget efficiency monitor (turns spinning vs 500/50 caps).

Reads token-usage.jsonl (base + profile). Groups by session_id, takes max(turn_id).
Writes cache/iteration-budget-efficiency.json (+ optional alarm).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone, UTC
from pathlib import Path

WINDOW_S = 24 * 3600
PARENT_CAP = 500
SUBAGENT_CAP = 50
TURN_WARN = 80
TURN_HIGH = 200
SPIN_COMPLETION = 250
SPIN_TURNS = 30


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


def _parse_ts(val: object) -> float | None:
    if not val:
        return None
    s = str(val).strip()
    if not s:
        return None
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s).timestamp()
    except ValueError:
        return None


def scan_usage(paths: list[Path], cutoff: float) -> dict[str, dict]:
    sess: dict[str, dict] = {}
    seen_files: set[Path] = set()
    for path in paths:
        if not path.is_file():
            continue
        rp = path.resolve()
        if rp in seen_files:
            continue
        seen_files.add(rp)
        try:
            fh = path.open()
        except OSError:
            continue
        with fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(rec, dict):
                    continue
                if rec.get("scope") == "ue_blackbox":
                    continue
                sid = rec.get("session_id") or ""
                if not sid:
                    continue
                ts = _parse_ts(rec.get("ts"))
                if ts is not None and ts < cutoff:
                    continue
                try:
                    turn = int(rec.get("turn_id") or 0)
                except (TypeError, ValueError):
                    turn = 0
                try:
                    comp = int(rec.get("completion_tokens") or 0)
                except (TypeError, ValueError):
                    comp = 0
                try:
                    prompt = int(rec.get("prompt_tokens") or 0)
                except (TypeError, ValueError):
                    prompt = 0
                try:
                    tools = int(rec.get("tool_calls_count") or 0)
                except (TypeError, ValueError):
                    tools = 0
                slot = sess.setdefault(
                    sid,
                    {
                        "max_turn": 0,
                        "n_rows": 0,
                        "sum_completion": 0,
                        "sum_prompt": 0,
                        "max_prompt": 0,
                        "max_tools": 0,
                        "spin_turns": 0,
                        "last_model": rec.get("model"),
                        "pressure": rec.get("pressure_flag"),
                    },
                )
                slot["n_rows"] += 1
                slot["max_turn"] = max(slot["max_turn"], turn)
                slot["sum_completion"] += comp
                slot["sum_prompt"] += prompt
                slot["max_prompt"] = max(slot["max_prompt"], prompt)
                slot["max_tools"] = max(slot["max_tools"], tools)
                if turn > 0 and comp < SPIN_COMPLETION:
                    slot["spin_turns"] += 1
                if rec.get("model"):
                    slot["last_model"] = rec.get("model")
                if rec.get("pressure_flag"):
                    slot["pressure"] = rec.get("pressure_flag")
    return sess


def build_report(sess: dict[str, dict]) -> dict:
    n = len(sess)
    turns = [v["max_turn"] for v in sess.values()]
    mean_turn = (sum(turns) / n) if n else 0.0
    hot = sorted(sess.items(), key=lambda kv: kv[1]["max_turn"], reverse=True)[:8]
    alarms: list[dict] = []
    n_warn = sum(1 for t in turns if t >= TURN_WARN)
    n_high = sum(1 for t in turns if t >= TURN_HIGH)
    n_spin = sum(1 for v in sess.values() if v["max_turn"] >= SPIN_TURNS and v["spin_turns"] >= SPIN_TURNS)
    if n_high:
        alarms.append({"severity": "HIGH", "why": "session(s) used >= 200 iterations", "n": n_high})
    elif n_warn:
        alarms.append({"severity": "MEDIUM", "why": "session(s) used >= 80 iterations", "n": n_warn})
    if n_spin:
        alarms.append(
            {
                "severity": "MEDIUM",
                "why": "spinning sessions (many short completions)",
                "n": n_spin,
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
        "n_sessions": n,
        "mean_max_turn": round(mean_turn, 2),
        "max_turn": max(turns) if turns else 0,
        "n_over_80": n_warn,
        "n_over_200": n_high,
        "n_spin": n_spin,
        "parent_cap": PARENT_CAP,
        "subagent_cap": SUBAGENT_CAP,
        "hottest": [
            {
                "session_id": sid,
                "max_turn": v["max_turn"],
                "n_rows": v["n_rows"],
                "max_prompt": v["max_prompt"],
                "spin_turns": v["spin_turns"],
                "model": v.get("last_model"),
                "pressure": v.get("pressure"),
            }
            for sid, v in hot
        ],
        "alarms": alarms,
        "theory": "iteration_budget.resolve_max_iterations parent=500 subagent=50",
    }


def _self_test() -> int:
    home = _hermes_home()
    os.environ["HERMES_HOME"] = str(home / "profiles" / "fork")
    assert _hermes_home() == home
    os.environ["HERMES_HOME"] = str(home)
    sess = {
        "a": {"max_turn": 90, "n_rows": 90, "sum_completion": 1000, "sum_prompt": 1, "max_prompt": 1, "max_tools": 1, "spin_turns": 80, "last_model": "x", "pressure": None},
        "b": {"max_turn": 5, "n_rows": 5, "sum_completion": 2000, "sum_prompt": 1, "max_prompt": 1, "max_tools": 1, "spin_turns": 0, "last_model": "x", "pressure": None},
    }
    r = build_report(sess)
    assert r["n_over_80"] == 1
    assert r["status"] == "warn"
    print(json.dumps({"status": "ok", "self_test": True}))
    return 0


def _run() -> int:
    home = _hermes_home()
    root = _hermes_root()
    cutoff = datetime.now(UTC).timestamp() - WINDOW_S
    sess = scan_usage(
        [home / "logs" / "token-usage.jsonl", root / "logs" / "token-usage.jsonl"],
        cutoff,
    )
    report = build_report(sess)
    out = root / "cache" / "iteration-budget-efficiency.json"
    _atomic_write(out, report)
    alarm_path = root / "cache" / "iteration-budget-efficiency-alarm.json"
    if report["status"] in {"warn", "alarm"} and report["alarms"]:
        sev = "HIGH" if report["status"] == "alarm" else "MEDIUM"
        _atomic_write(
            alarm_path,
            {
                "ts": report["ts"],
                "name": "iteration-budget-efficiency",
                "severity": sev,
                "status": report["status"],
                "summary": f"max_turn={report['max_turn']} over80={report['n_over_80']}",
                "alarms": report["alarms"],
            },
        )
    elif alarm_path.exists():
        try:
            alarm_path.unlink()
        except OSError:
            pass
    print(json.dumps({"status": report["status"], "out": str(out), "max_turn": report["max_turn"]}))
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
