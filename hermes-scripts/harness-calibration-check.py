#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path


def _hermes_home() -> Path:
    env = os.environ.get("HERMES_HOME", "").strip()
    p = Path(env) if env else Path.home() / ".hermes"
    if p.name != ".hermes" and p.parent.name == "profiles":
        return p.parent.parent
    cur = p
    for _ in range(4):
        if (cur / "hermes-scripts").is_dir():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    return p


_hermes_base = _hermes_home()
_hermes_profile = os.environ.get("HERMES_PROFILE", "")
_hermes_root = (
    (_hermes_base / "profiles" / _hermes_profile)
    if _hermes_profile and "profiles" not in str(_hermes_base)
    else _hermes_base
)

"""One-off harness calibration check over recent AB eval meta.jsonl files."""

import json
import os
from collections import defaultdict
from pathlib import Path


def _abeval_root() -> Path:
    env = os.environ.get("ABEVAL_ROOT", "").strip()
    if env:
        return Path(env)
    scratch = _hermes_root / "cache" / "scratch"
    preferred = scratch / "benchmark-elite3b"
    if preferred.exists():
        return preferred
    return scratch


def _load_records(root: Path) -> list[tuple[float, dict]]:
    recs = []
    if not root.exists():
        return recs
    for p in root.rglob("meta.jsonl"):
        try:
            mtime = p.stat().st_mtime
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(rec, dict):
                continue
            recs.append((mtime, rec))
    return recs


def _suite_runs(recs: list[tuple[float, dict]], n: int = 10) -> list[dict[str, float]]:
    """Group records into suite runs by parent-of-model directory mtime buckets.

    Each unique meta.jsonl mtime (rounded to 60s) across the tree is too fine.
    Prefer grouping by the `results/` parent directory of each file's records:
    one suite dir = one run if it contains multiple models.
    Fallback: last 10 unique integer-minute mtimes.
    """
    by_dir: dict[str, list[tuple[float, dict]]] = defaultdict(list)
    for mtime, rec in recs:
        # Group by nearest ancestor named 'results' parent, else file mtime minute
        by_dir[str(int(mtime // 3600))].append((mtime, rec))
    # If few hour-buckets, use the unique suite roots instead
    hour_keys = sorted(by_dir, key=lambda k: int(k))
    if len(hour_keys) < 2:
        # treat whole recs as one run
        runs = [_pass_rates([r for _, r in recs])]
        return runs[-n:]
    runs = []
    for k in hour_keys[-n:]:
        runs.append(_pass_rates([r for _, r in by_dir[k]]))
    return runs


def _pass_rates(records: list[dict]) -> dict[str, float]:
    by_task: dict[str, list[int]] = defaultdict(list)
    for rec in records:
        task = str(rec.get("task") or rec.get("name") or "").strip()
        if not task:
            continue
        if "exit" in rec:
            ok = 1 if int(rec.get("exit") or 1) == 0 else 0
        elif "pass" in rec:
            ok = 1 if rec.get("pass") else 0
        elif "ok" in rec:
            ok = 1 if rec.get("ok") else 0
        else:
            continue
        by_task[task].append(ok)
    return {t: (sum(v) / len(v) if v else 0.0) for t, v in by_task.items()}


def _consecutive(values: list[float], pred) -> bool:
    if len(values) < 3:
        return False
    streak = 0
    for v in values:
        if pred(v):
            streak += 1
            if streak >= 3:
                return True
        else:
            streak = 0
    return False


def main() -> int:
    root = _abeval_root()
    recs = _load_records(root)
    runs = _suite_runs(recs, 10)
    tasks = sorted({t for run in runs for t in run})
    ceiling = []
    floor = []
    discriminating = []
    latest = runs[-1] if runs else {}
    for task in tasks:
        series = [run[task] for run in runs if task in run]
        if _consecutive(series, lambda x: x >= 0.95):
            ceiling.append(task)
            print(f"CEILING TASK: {task} - consider replacing with harder variant")
        if _consecutive(series, lambda x: x <= 0.05):
            floor.append(task)
            print(f"FLOOR TASK: {task} - checker may be broken or task too hard")
        rate = latest.get(task)
        if rate is None and series:
            rate = series[-1]
        if rate is not None and 0.30 <= rate <= 0.70:
            discriminating.append(task)
    if not discriminating:
        print("WARNING: no discriminating tasks in suite")
    print(
        f"HARNESS_HEALTH n_ceiling={len(ceiling)} n_floor={len(floor)} "
        f"n_discriminating={len(discriminating)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
