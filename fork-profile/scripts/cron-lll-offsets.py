#!/usr/bin/env python3
"""LLL + Moser–Tardos offset packing for hard cron conflicts (Motwani Ch 5).

On-demand tool — not registered as a cron job.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import sys
from pathlib import Path

_hermes_base = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_hermes_profile = os.environ.get("HERMES_PROFILE", "")
_hermes_root = (
    (_hermes_base / "profiles" / _hermes_profile)
    if _hermes_profile and "profiles" not in str(_hermes_base)
    else _hermes_base
)
JOBS_PATH = _hermes_root / "cron" / "jobs.json"


def _f(x, default=0.0) -> float:
    try:
        v = float(x or 0.0)
    except (TypeError, ValueError):
        v = default
    return v


def symmetric_lll_ok(p, D) -> bool:
    try:
        p = float(p or 0.0)
        D = float(D or 0.0)
    except (TypeError, ValueError):
        return False
    return math.e * p * (D + 1) <= 1.0


def moser_tardos_offsets(jobs, slots, conflicts, rng=None, max_steps=10_000):
    """jobs[i] -> offset in [0, slots). conflicts: list of (i,j) pairs."""
    rng = rng or random.Random()
    try:
        slots = int(slots or 0)
    except (TypeError, ValueError):
        slots = 0
    n = len(jobs)
    if slots <= 0 or n == 0:
        return [0] * n, 0
    off = [rng.randrange(slots) for _ in jobs]

    def violations():
        return [(i, j) for i, j in conflicts if off[i] == off[j]]

    for step in range(max_steps):
        bad = violations()
        if not bad:
            return off, step
        i, j = rng.choice(bad)
        off[rng.choice((i, j))] = rng.randrange(slots)
    return off, max_steps


def _cadence_s(job: dict) -> float:
    sched = job.get("schedule") or {}
    expr = str(sched.get("expr") or "")
    parts = expr.split()
    if len(parts) != 5:
        return 86400.0
    minute, hour, dom, _m, dow = parts
    try:
        if minute.startswith("*/"):
            return max(60.0, float(int(minute[2:])) * 60.0)
        if hour.startswith("*/"):
            return float(int(hour[2:])) * 3600.0
        if dow not in ("*", "?") and dom in ("*", "?"):
            return 7 * 86400.0
        if dom not in ("*", "?"):
            return 30 * 86400.0
        if hour not in ("*", "?"):
            return 86400.0
        if minute not in ("*", "?"):
            return 3600.0
    except (TypeError, ValueError):
        return 86400.0
    return 3600.0


def detect_conflicts(jobs: list[dict]) -> list[tuple[int, int]]:
    """Edge if timeout_i + timeout_j > 0.5 * min(cadence_i, cadence_j)."""
    n = len(jobs)
    timeouts = []
    cads = []
    for j in jobs:
        t = _f(j.get("timeout", j.get("timeout_seconds", 120)), 120.0)
        timeouts.append(t)
        cads.append(_cadence_s(j))
    edges = []
    for i in range(n):
        for k in range(i + 1, n):
            if timeouts[i] + timeouts[k] > 0.5 * min(cads[i], cads[k]):
                edges.append((i, k))
    return edges


def pack_jobs(jobs_path: Path, slots: int = 60, rng=None) -> dict:
    path = Path(jobs_path)
    obj = json.loads(path.read_bytes().decode("utf-8", errors="replace"))
    jobs = obj.get("jobs") if isinstance(obj, dict) else obj
    if not isinstance(jobs, list):
        return {"ok": False, "error": "jobs not a list"}
    cron_jobs = [j for j in jobs if isinstance(j, dict) and (j.get("schedule") or {}).get("kind") == "cron"]
    conflicts = detect_conflicts(cron_jobs)
    deg = [0] * len(cron_jobs)
    for i, j in conflicts:
        deg[i] += 1
        deg[j] += 1
    D = max(deg) if deg else 0
    p = 1.0 / max(slots, 1)
    ok = symmetric_lll_ok(p, D)
    off, steps = moser_tardos_offsets(cron_jobs, slots, conflicts, rng=rng)
    return {
        "ok": True,
        "lll_ok": ok,
        "D": D,
        "p": p,
        "n": len(cron_jobs),
        "n_conflicts": len(conflicts),
        "steps": steps,
        "offsets": off[:20],
    }


def _self_test() -> int:
    assert symmetric_lll_ok(0.01, 2) is True
    assert symmetric_lll_ok(0.9, 10) is False
    rng = random.Random(1)
    jobs = ["a", "b", "c", "d"]
    conflicts = [(0, 1), (2, 3)]
    off, steps = moser_tardos_offsets(jobs, 8, conflicts, rng=rng)
    assert off[0] != off[1]
    assert off[2] != off[3]
    dummy = [
        {"timeout": 2000, "schedule": {"kind": "cron", "expr": "0 * * * *"}},
        {"timeout": 2000, "schedule": {"kind": "cron", "expr": "0 * * * *"}},
        {"timeout": 1, "schedule": {"kind": "cron", "expr": "0 * * * *"}},
    ]
    conf = detect_conflicts(dummy)
    assert (0, 1) in conf
    print(json.dumps({"ok": True, "steps": steps, "off": off, "conflicts": conf}))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="LLL cron offset packing")
    p.add_argument("--self-test", action="store_true")
    p.add_argument("--jobs", default=str(JOBS_PATH))
    p.add_argument("--slots", type=int, default=60)
    args = p.parse_args(argv)
    if args.self_test:
        return _self_test()
    print(json.dumps(pack_jobs(Path(args.jobs), slots=args.slots)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
