#!/usr/bin/env python3
"""Session hygiene dashboard — combines sibling monitors.

Recursive pass: interactions between compression loss, truncation, cache
misses, and iteration spin. Writes cache/session-hygiene-dashboard.json.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone, UTC
from pathlib import Path

CHILDREN = (
    "prompt-cache-hit.json",
    "compression-quality.json",
    "cron-missed-runs.json",
    "tool-output-loss.json",
    "iteration-budget-efficiency.json",
    "skill-routing-accuracy.json",
    "reasoning-effort-calibration.json",
)


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


def _load(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return obj if isinstance(obj, dict) else None


def _stat_size(path: Path) -> int | None:
    try:
        return int(path.stat().st_size)
    except OSError:
        return None


def build_report(children: dict[str, dict | None], mem_bytes: int | None) -> dict:
    statuses = {}
    alarms: list[dict] = []
    for name, obj in children.items():
        if obj is None:
            statuses[name] = "missing"
            continue
        st = str(obj.get("status") or "unknown")
        statuses[name] = st
        for a in obj.get("alarms") or []:
            if isinstance(a, dict):
                alarms.append({"source": name, **a})
    cache = children.get("prompt-cache-hit.json") or {}
    trunc = children.get("tool-output-loss.json") or {}
    comp = children.get("compression-quality.json") or {}
    it = children.get("iteration-budget-efficiency.json") or {}
    interactions: list[dict] = []
    scan = (comp.get("scan") or {}) if isinstance(comp.get("scan"), dict) else {}
    compression_pressure = (
        int(scan.get("n_ineffective") or 0) > 0
        or int(comp.get("live_prompt_tokens") or 0) >= 100000
        or str(comp.get("status")) == "alarm"
        and any(
            "ineffective" in str(a.get("why") or "") or "abort" in str(a.get("why") or "")
            for a in (comp.get("alarms") or [])
            if isinstance(a, dict)
        )
    )
    if str(trunc.get("status")) in {"warn", "alarm"} and compression_pressure:
        interactions.append(
            {
                "severity": "HIGH",
                "why": "tool truncation AND live compression pressure — remaining tail is at risk",
            }
        )
    hit = cache.get("weighted_log_hit_rate")
    max_turn = it.get("max_turn") or 0
    if isinstance(hit, (int, float)) and hit < 0.4 and int(max_turn) >= 80:
        interactions.append(
            {
                "severity": "HIGH",
                "why": "long iteration session with poor prompt-cache hit rate",
                "hit_rate": hit,
                "max_turn": max_turn,
            }
        )
    mem_alarm = None
    if mem_bytes is not None and mem_bytes > 8000:
        mem_alarm = {
            "severity": "MEDIUM",
            "why": "MEMORY.md larger than 8KiB (injection bloat risk)",
            "bytes": mem_bytes,
        }
        alarms.append({"source": "memory.md", **mem_alarm})
    if interactions:
        alarms.extend({"source": "interaction", **x} for x in interactions)
    status = "ok"
    if statuses and all(s == "missing" for s in statuses.values()) and not alarms:
        status = "insufficient_data"
    elif any(a.get("severity") == "HIGH" for a in alarms) or any(
        s == "alarm" for s in statuses.values()
    ):
        status = "alarm"
    elif alarms or any(s == "warn" for s in statuses.values()):
        status = "warn"
    return {
        "ts": _now().isoformat(),
        "status": status,
        "children": statuses,
        "memory_md_bytes": mem_bytes,
        "interactions": interactions,
        "alarms": alarms[:24],
        "n_alarms": len(alarms),
        "theory": "compose sibling monitors; truncation×compaction and cache×iterations",
    }


def _self_test() -> int:
    home = _hermes_home()
    old_home = os.environ.get("HERMES_HOME")
    os.environ["HERMES_HOME"] = str(home / "profiles" / "fork")
    assert _hermes_home() == home
    os.environ["HERMES_HOME"] = str(home)
    empty = build_report({name: None for name in CHILDREN}, None)
    assert empty["status"] == "insufficient_data"
    r = build_report(
        {
            "prompt-cache-hit.json": {"status": "ok", "weighted_log_hit_rate": 0.2, "alarms": []},
            "compression-quality.json": {
                "status": "warn",
                "live_prompt_tokens": 120000,
                "scan": {"n_ineffective": 2},
                "alarms": [{"severity": "MEDIUM", "why": "x"}],
            },
            "tool-output-loss.json": {"status": "alarm", "alarms": [{"severity": "HIGH", "why": "y"}]},
            "iteration-budget-efficiency.json": {"status": "warn", "max_turn": 90, "alarms": []},
        },
        9000,
    )
    assert r["status"] == "alarm"
    assert r["interactions"]
    if old_home is None:
        os.environ.pop("HERMES_HOME", None)
    else:
        os.environ["HERMES_HOME"] = old_home
    print(json.dumps({"status": "ok", "self_test": True}))
    return 0


def _run() -> int:
    root = _hermes_root()
    cache = root / "cache"
    children = {name: _load(cache / name) for name in CHILDREN}
    mem = None
    for cand in (
        root / "memories" / "MEMORY.md",
        _hermes_home() / "memories" / "MEMORY.md",
    ):
        sz = _stat_size(cand)
        if sz is not None:
            mem = sz
            break
    report = build_report(children, mem)
    out = cache / "session-hygiene-dashboard.json"
    _atomic_write(out, report)
    alarm_path = cache / "session-hygiene-dashboard-alarm.json"
    if report["status"] in {"warn", "alarm"} and report["alarms"]:
        sev = "HIGH" if report["status"] == "alarm" else "MEDIUM"
        _atomic_write(
            alarm_path,
            {
                "ts": report["ts"],
                "name": "session-hygiene-dashboard",
                "severity": sev,
                "status": report["status"],
                "summary": f"hygiene {report['status']} n_alarms={report['n_alarms']}",
                "alarms": report["alarms"][:12],
            },
        )
    elif alarm_path.exists():
        try:
            alarm_path.unlink()
        except OSError:
            pass
    print(json.dumps({"status": report["status"], "out": str(out), "n_alarms": report["n_alarms"]}))
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
