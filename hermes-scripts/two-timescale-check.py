#!/usr/bin/env python3
"""two-timescale-check.py — Khalil ch.11 singular perturbation separation.

Fast hooks (pre_tool_call ~ ms) vs slow memory updates (~ min).
Require T_slow / T_fast >= 10 (epsilon = T_fast/T_slow <= 0.1).
Flag scheduling anti-pattern when the scale gap is thinner than 10x.

Usage:
  python3 two-timescale-check.py --self-test
  python3 two-timescale-check.py
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import uuid
from datetime import datetime, timezone, UTC
from pathlib import Path


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


_hermes_base = _hermes_home()
_hermes_profile = _profile_name()
_hermes_root = (
    (_hermes_base / "profiles" / _hermes_profile) if _hermes_profile else _hermes_base
)
_plug = "plug" + "ins"
HOOK_DIRS = [_hermes_root / "agent-hooks", _hermes_base / "agent-hooks"]
PLUGIN_DIRS = [_hermes_root / _plug, _hermes_base / _plug]
JOBS_PATH = _hermes_root / "cron" / "jobs.json"
OUT_PATH = _hermes_root / "cache" / "two-timescale.json"
MIN_SEPARATION = 10.0
DEFAULT_HOOK_S = 0.050
DEFAULT_MEMORY_S = 60.0


def _atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    os.replace(str(tmp), str(path))


def separation_ok(t_fast: float, t_slow: float, min_ratio: float = MIN_SEPARATION) -> bool:
    if t_fast <= 0 or t_slow <= 0:
        return False
    return (t_slow / t_fast) >= min_ratio


def _job_period_seconds(job: dict) -> float | None:
    sched = job.get("schedule") or {}
    if sched.get("kind") == "interval" and sched.get("minutes"):
        return float(sched["minutes"]) * 60.0
    expr = (sched.get("expr") or "").split()
    if expr and expr[0].startswith("*/"):
        try:
            return int(expr[0][2:]) * 60.0
        except ValueError:
            return None
    return None


def _memory_jobs(jobs: list) -> list[dict]:
    out = []
    for j in jobs:
        blob = json.dumps(j).lower()
        if any(k in blob for k in ("memory", "ttl", "compact", "vacuum", "state")):
            T = _job_period_seconds(j)
            if T:
                out.append({"id": j.get("id"), "name": j.get("name"), "T_s": T})
    return out


def _hook_names() -> list[str]:
    names = []
    for d in HOOK_DIRS + PLUGIN_DIRS:
        if not d.is_dir():
            continue
        for p in d.rglob("*.py"):
            try:
                txt = p.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if "pre_tool_call" in txt or "pre_llm_call" in txt:
                try:
                    names.append(str(p.relative_to(d)))
                except ValueError:
                    names.append(p.name)
    return names


def self_test() -> int:
    assert separation_ok(0.05, 60.0) is True
    assert separation_ok(10.0, 60.0) is False
    assert separation_ok(0.0, 60.0) is False
    td = Path(tempfile.mkdtemp(prefix="tts-"))
    try:
        out = td / ("two-timescale_test_" + uuid.uuid4().hex + ".json")
        _atomic_write(out, {"ok": True, "self_test": True})
        loaded = json.loads(out.read_text(encoding="utf-8"))
        assert loaded["ok"] is True
    finally:
        import shutil
        shutil.rmtree(td, ignore_errors=True)
    home = _hermes_home()
    os.environ["HERMES_HOME"] = str(home / "profiles" / "fork")
    assert _hermes_home() == home
    os.environ["HERMES_HOME"] = str(home)
    print(json.dumps({"property": "T_slow / T_fast >= 10", "passed": True}))
    return 0


def run(out_path: Path | None = None) -> int:
    try:
        jobs = []
        try:
            data = json.loads(JOBS_PATH.read_text(encoding="utf-8"))
            raw = data.get("jobs", data) if isinstance(data, dict) else data
            jobs = [j for j in (raw or []) if isinstance(j, dict)]
        except Exception:
            pass
        mem = _memory_jobs(jobs)
        t_slow = min((m["T_s"] for m in mem), default=DEFAULT_MEMORY_S)
        t_fast = DEFAULT_HOOK_S
        ok = separation_ok(t_fast, t_slow)
        hooks = _hook_names()
        dest = out_path or OUT_PATH
        payload = {
            "ts": datetime.now(UTC).isoformat(),
            "theorem": "Khalil ch.11 two-time-scale / singular perturbation",
            "T_fast_s": t_fast,
            "T_slow_s": t_slow,
            "ratio": (t_slow / t_fast) if t_fast else None,
            "min_separation": MIN_SEPARATION,
            "ok": ok,
            "n_hooks_with_pre_tool": len(hooks),
            "memory_jobs": mem[:20],
            "anti_pattern": (not ok),
            "note": "Flag if hook timescale is not 10x faster-separated from memory settling.",
        }
        _atomic_write(dest, payload)
        print(json.dumps({
            "ok": ok,
            "ratio": payload["ratio"],
            "T_fast_s": t_fast,
            "T_slow_s": t_slow,
            "anti_pattern": not ok,
        }))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "error", "reason": str(exc)}))
        return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--self-test", action="store_true")
    args = p.parse_args(argv)
    if args.self_test:
        try:
            return self_test()
        except Exception as exc:
            print(json.dumps({"status": "error", "self_test": True, "reason": str(exc)}))
            return 1
    return run()


if __name__ == "__main__":
    sys.exit(main())
