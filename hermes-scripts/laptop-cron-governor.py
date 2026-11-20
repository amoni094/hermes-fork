#!/usr/bin/env python3
"""Laptop cron governor: battery + loadavg + measured WCET skip gate.

Single-user Fedora laptop. Fail-open everywhere.
  --run     write cache/laptop-cron-policy.json
  --check SCRIPT   exit 0 = run, 75 = skip this fire (wrapper treats as ok)
  --self-test

Policy (Liu-Layland C_i = p95 from cron-measured-utilisation.json):
  AC + load1 <= nproc:        no skip
  AC + load1 > nproc:         skip jobs with p95 > 60s
  AC + load1 > 2*nproc:       skip jobs with p95 > 20s
  battery capacity >= 50:     skip p95 > 60s
  battery 20-50:              skip p95 > 20s
  battery 10-20:              skip p95 > 8s
  battery < 10:               skip all except never_skip
Unknown C_i => run (fail-open). Missing sysfs => run.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import sys
from datetime import datetime, timezone, UTC
from pathlib import Path

SKIP_EXIT = 75
NEVER_SKIP = frozenset({
    "laptop-cron-governor.py",
    "cron-measured-wcet.py",
    "cron-admission-control.py",
    "hermes-platform-watchdog.py",
    "cron-sandbox-wrapper.sh",
    "cron-sandbox-runner.py",
})


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


def _read_sysfs(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return None


def read_power(sys_root: Path | None = None) -> dict:
    root = sys_root or Path("/sys/class/power_supply")
    bat_status = None
    capacity = None
    ac_online = None
    if not root.exists():
        return {
            "on_battery": None,
            "capacity": None,
            "ac_online": None,
            "bat_status": None,
            "reason": "no_sysfs",
        }
    for child in sorted(root.iterdir()):
        typ = (_read_sysfs(child / "type") or "").lower()
        if typ == "battery":
            bat_status = _read_sysfs(child / "status")
            cap_raw = _read_sysfs(child / "capacity")
            try:
                capacity = int(cap_raw) if cap_raw is not None else None
            except ValueError:
                capacity = None
        elif typ in ("mains", "line"):
            online = _read_sysfs(child / "online")
            if online is not None:
                ac_online = online == "1"
    on_battery = None
    if ac_online is True:
        on_battery = False
    elif ac_online is False:
        on_battery = True
    elif bat_status:
        on_battery = bat_status.lower() not in ("charging", "full", "not charging")
        if bat_status.lower() == "discharging":
            on_battery = True
    return {
        "on_battery": on_battery,
        "capacity": capacity,
        "ac_online": ac_online,
        "bat_status": bat_status,
        "reason": None,
    }


def read_load(proc_loadavg: Path | None = None, cpuinfo: Path | None = None) -> dict:
    nproc = 1
    try:
        text = (cpuinfo or Path("/proc/cpuinfo")).read_text(encoding="utf-8")
        n = text.count("processor")
        if n > 0:
            nproc = n
    except OSError:
        nproc = os.cpu_count() or 1
    load1 = None
    try:
        parts = (proc_loadavg or Path("/proc/loadavg")).read_text(encoding="utf-8").split()
        load1 = float(parts[0])
    except (OSError, ValueError, IndexError):
        load1 = None
    return {"load1": load1, "nproc": nproc}


def max_job_seconds(power: dict, load: dict) -> float | None:
    """None means no skip. 0 means skip all except never_skip."""
    cap = power.get("capacity")
    on_bat = power.get("on_battery")
    load1 = load.get("load1")
    nproc = max(int(load.get("nproc") or 1), 1)

    limit = None  # no skip
    if on_bat is True:
        if cap is None:
            limit = 60.0
        elif cap < 10:
            limit = 0.0
        elif cap < 20:
            limit = 8.0
        elif cap < 50:
            limit = 20.0
        else:
            limit = 60.0
    if load1 is not None:
        if load1 > 2 * nproc:
            cand = 20.0
            limit = cand if limit is None else min(limit, cand)
        elif load1 > nproc:
            cand = 60.0
            limit = cand if limit is None else min(limit, cand)
    return limit


def load_wcet(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    by_base = data.get("by_basename") if isinstance(data, dict) else None
    if isinstance(by_base, dict):
        out = {}
        for k, v in by_base.items():
            try:
                out[str(k)] = float(v)
            except (TypeError, ValueError):
                continue
        return out
    return {}


def decide_skip(script: str, limit: float | None, wcet: dict) -> tuple[bool, str]:
    base = Path(script).name
    if not base:
        return False, "empty_script"
    if base in NEVER_SKIP:
        return False, "never_skip"
    if limit is None:
        return False, "no_limit"
    p95 = wcet.get(base)
    if limit == 0.0:
        return True, "battery_critical"
    if p95 is None:
        return False, "unknown_C_fail_open"
    if p95 > limit:
        return True, "p95_gt_limit"
    return False, "under_limit"


# Scheduler never calls --check. Gate only these deferrable monitors via jobs.json.
DEFERABLE = frozenset({
    "prompt-cache-hit-monitor.py",
    "compression-quality-monitor.py",
    "cron-missed-runs-monitor.py",
    "tool-output-loss-monitor.py",
    "iteration-budget-efficiency.py",
    "session-hygiene-dashboard.py",
    "skill-routing-accuracy.py",
    "reasoning-effort-calibration.py",
    "circadian-skill-prewarm.py",
    "conformal-martingale-calibration.py",
    "skill-latency-collector.py",
    "turn-behavior-collector.py",
    "skill-info-cost.py",
    "skill-compliance-covariance.py",
    "llm-autoscaler.py",
    "memory-bottleneck-monitor.py",
})
PAUSED_REASON = "laptop-cron-governor"


def apply_job_gates(root: Path, limit: float | None, wcet: dict) -> dict:
    """Pause/unpause DEFERABLE jobs. Fail-open. Does not touch unrelated jobs."""
    summary: dict = {"paused": [], "unpaused": [], "error": None}
    jobs_path = root / "cron" / "jobs.json"
    if not jobs_path.is_file():
        summary["error"] = "jobs.json missing"
        return summary
    try:
        lock = jobs_path.with_name("jobs.json.lock")
        with open(str(lock), "a", encoding="utf-8") as lf:
            fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
            try:
                data = json.loads(jobs_path.read_text(encoding="utf-8"))
                jobs = data.get("jobs") if isinstance(data, dict) else None
                if not isinstance(jobs, list):
                    summary["error"] = "jobs not list"
                    return summary
                changed = False
                for job in jobs:
                    if not isinstance(job, dict):
                        continue
                    script = str(job.get("script") or "")
                    base = Path(script).name
                    if base not in DEFERABLE:
                        continue
                    skip, _reason = decide_skip(script, limit, wcet)
                    jid = str(job.get("id") or base)
                    if skip:
                        if job.get("enabled") is False and job.get("paused_reason") != PAUSED_REASON:
                            continue
                        if job.get("enabled") is False and job.get("paused_reason") == PAUSED_REASON:
                            continue
                        job["enabled"] = False
                        job["state"] = "paused"
                        job["paused_reason"] = PAUSED_REASON
                        summary["paused"].append(jid)
                        changed = True
                    elif job.get("paused_reason") == PAUSED_REASON:
                        job["enabled"] = True
                        job["state"] = "scheduled"
                        job.pop("paused_reason", None)
                        summary["unpaused"].append(jid)
                        changed = True
                if changed:
                    tmp = jobs_path.with_name("jobs.json.tmp")
                    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
                    os.replace(str(tmp), str(jobs_path))
            finally:
                fcntl.flock(lf.fileno(), fcntl.LOCK_UN)
        return summary
    except Exception as exc:
        summary["error"] = str(exc)
        return summary


def build_policy(power: dict, load: dict, wcet: dict) -> dict:
    limit = max_job_seconds(power, load)
    skip = limit == 0.0
    if limit is None:
        reason = "no_limit"
    elif skip:
        reason = "battery_critical"
    else:
        reason = "limited"
    return {
        "ts": _now(),
        "status": "ok",
        "skip": skip,
        "reason": reason,
        "on_battery": power.get("on_battery"),
        "capacity": power.get("capacity"),
        "ac_online": power.get("ac_online"),
        "bat_status": power.get("bat_status"),
        "load1": load.get("load1"),
        "nproc": load.get("nproc"),
        "max_job_seconds": limit,
        "n_wcet": len(wcet),
        "never_skip": sorted(NEVER_SKIP),
        "theory": "Liu-Layland C_i + laptop energy/load governor",
    }


def run(root: Path | None = None) -> dict:
    root = root or _hermes_root()
    power = read_power()
    load = read_load()
    wcet = load_wcet(root / "cache" / "cron-measured-utilisation.json")
    policy = build_policy(power, load, wcet)
    policy["gates"] = apply_job_gates(root, policy.get("max_job_seconds"), wcet)
    _atomic_write(root / "cache" / "laptop-cron-policy.json", policy)
    return policy


def check_script(script: str, root: Path | None = None) -> int:
    """0 = run, 75 = skip. Never raises to caller."""
    try:
        root = root or _hermes_root()
        power = read_power()
        load = read_load()
        wcet = load_wcet(root / "cache" / "cron-measured-utilisation.json")
        limit = max_job_seconds(power, load)
        skip, reason = decide_skip(script, limit, wcet)
        rec = {
            "ts": _now(),
            "script": script,
            "basename": Path(script).name,
            "skip": skip,
            "reason": reason,
            "max_job_seconds": limit,
            "p95_s": wcet.get(Path(script).name),
            "on_battery": power.get("on_battery"),
            "capacity": power.get("capacity"),
            "load1": load.get("load1"),
        }
        if skip:
            logp = root / "cache" / "laptop-cron-skips.jsonl"
            try:
                logp.parent.mkdir(parents=True, exist_ok=True)
                with open(str(logp), "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(rec) + "\n")
            except OSError:
                pass
            print(json.dumps(rec))
            return SKIP_EXIT
        return 0
    except Exception:
        return 0


def _self_test() -> int:
    os.environ["HERMES_HOME"] = str(Path.home() / ".hermes" / "profiles" / "fork")
    os.environ.pop("HERMES_PROFILE", None)
    assert _hermes_home() == Path.home() / ".hermes", _hermes_home()

    skip, reason = decide_skip("/x/laptop-cron-governor.py", 0.0, {})
    assert skip is False and reason == "never_skip"
    skip, reason = decide_skip("/x/heavy.py", None, {"heavy.py": 999})
    assert skip is False and reason == "no_limit"
    skip, reason = decide_skip("/x/heavy.py", 20.0, {})
    assert skip is False and reason == "unknown_C_fail_open"
    skip, reason = decide_skip("/x/heavy.py", 20.0, {"heavy.py": 40.0})
    assert skip is True and reason == "p95_gt_limit"
    skip, reason = decide_skip("/x/light.py", 20.0, {"light.py": 4.0})
    assert skip is False and reason == "under_limit"
    skip, reason = decide_skip("/x/any.py", 0.0, {"any.py": 1.0})
    assert skip is True and reason == "battery_critical"

    lim = max_job_seconds(
        {"on_battery": False, "capacity": 90},
        {"load1": 0.2, "nproc": 8},
    )
    assert lim is None, lim
    lim = max_job_seconds(
        {"on_battery": True, "capacity": 15},
        {"load1": 0.2, "nproc": 8},
    )
    assert lim == 8.0, lim
    lim = max_job_seconds(
        {"on_battery": False, "capacity": 90},
        {"load1": 20.0, "nproc": 8},
    )
    assert lim == 20.0, lim

    import shutil
    import tempfile

    td = Path(tempfile.mkdtemp(prefix="lcg-"))
    try:
        (td / "cron").mkdir()
        payload = {
            "jobs": [
                {
                    "id": "a",
                    "script": "/x/prompt-cache-hit-monitor.py",
                    "enabled": True,
                    "state": "scheduled",
                },
                {
                    "id": "b",
                    "script": "/x/laptop-cron-governor.py",
                    "enabled": True,
                    "state": "scheduled",
                },
                {
                    "id": "c",
                    "script": "/x/other.py",
                    "enabled": True,
                    "state": "scheduled",
                },
            ]
        }
        (td / "cron" / "jobs.json").write_text(json.dumps(payload), encoding="utf-8")
        g = apply_job_gates(td, 0.0, {})
        assert g.get("error") is None, g
        data = json.loads((td / "cron" / "jobs.json").read_text(encoding="utf-8"))
        by = {j["id"]: j for j in data["jobs"]}
        assert by["a"]["enabled"] is False
        assert by["a"]["paused_reason"] == PAUSED_REASON
        assert by["b"]["enabled"] is True
        assert by["c"]["enabled"] is True
        g2 = apply_job_gates(td, None, {})
        assert g2.get("error") is None, g2
        data = json.loads((td / "cron" / "jobs.json").read_text(encoding="utf-8"))
        by = {j["id"]: j for j in data["jobs"]}
        assert by["a"]["enabled"] is True
        assert "paused_reason" not in by["a"]
    finally:
        shutil.rmtree(td, ignore_errors=True)

    print(json.dumps({"status": "ok", "self_test": True}))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Laptop battery/load cron governor")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--check", metavar="SCRIPT", default="")
    args = ap.parse_args()
    if args.self_test:
        try:
            return _self_test()
        except Exception as exc:
            print(f"[laptop-cron-governor] --self-test FAIL: {exc}")
            return 1
    if args.check:
        return check_script(args.check)
    try:
        policy = run()
        print(json.dumps({
            k: policy.get(k)
            for k in (
                "status", "on_battery", "capacity", "ac_online",
                "load1", "nproc", "max_job_seconds", "n_wcet",
            )
        }, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "error", "reason": str(exc)}))
        return 0


if __name__ == "__main__":
    sys.exit(main())
