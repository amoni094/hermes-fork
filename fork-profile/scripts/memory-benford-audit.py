#!/usr/bin/env python3
"""memory-benford-audit.py — Benford leading-digit chi-square audit.

P(d) = log10(1+1/d) for d in 1..9. Chi-square df=8, critical p=0.05 is 15.507.
Only unbounded-magnitude fields (durations ms, token counts, costs), not [0,1].
"""
from __future__ import annotations

import json
import math
import os
import random
import sqlite3
import sys
from collections import Counter
from typing import Any, Dict, Iterable, List, Optional, Sequence

home = os.environ.get("HERMES_HOME", "")
home = home.removesuffix("/profiles/fork")
if not home:
    home = os.path.expanduser("~/.hermes")
profile_dir = home + "/profiles/fork"
CACHE = os.path.join(profile_dir, "cache")
COST_PATH = os.path.join(CACHE, "cost-attribution.json")
LIFECYCLE_DB = os.path.join(profile_dir, "memory-facts", "lifecycle.db")
OUT_PATH = os.path.join(CACHE, "benford-audit-result.json")

CRITICAL = 15.507
MIN_N = 30
JSONL_FIELDS = (
    "tokens", "total_tokens", "budget_tokens", "token_estimate",
    "duration_ms", "elapsed_ms", "latency_ms", "elapsed",
    "cost", "context_tokens", "n_pre_tokens", "n_post_tokens",
    "content_len", "query_len", "response_len", "joint_size",
)
MAX_JSONL_FILES = 200
MAX_LINES_PER_FILE = 5000


def _atomic_write(path: str, obj: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)
        f.write("\n")
    os.replace(tmp, path)


def leading_digit(x: Any) -> Optional[int]:
    if isinstance(x, bool) or x is None:
        return None
    try:
        v = abs(float(x))
    except (TypeError, ValueError):
        return None
    if v < 1.0 or v != v or v in (float("inf"),):
        return None
    s = f"{v:.15e}"
    for ch in s:
        if ch in "123456789":
            return int(ch)
    return None


def benford_expected(n: int) -> list[float]:
    return [n * math.log10(1.0 + 1.0 / d) for d in range(1, 10)]


def chi_square(digits: Sequence[int]) -> float:
    n = len(digits)
    if n == 0:
        return 0.0
    counts = Counter(digits)
    exp = benford_expected(n)
    chi = 0.0
    for d in range(1, 10):
        e = exp[d - 1]
        if e <= 0:
            continue
        o = counts.get(d, 0)
        chi += (o - e) ** 2 / e
    return chi


def report_source(source_name: str, values: Iterable[Any]) -> dict[str, Any]:
    digits: list[int] = []
    for v in values:
        d = leading_digit(v)
        if d is not None:
            digits.append(d)
    n = len(digits)
    if n < MIN_N:
        return {
            "source_name": source_name,
            "N": n,
            "chi2": None,
            "alarm": False,
            "skipped": True,
            "reason": "too_few",
        }
    chi2 = chi_square(digits)
    return {
        "source_name": source_name,
        "N": n,
        "chi2": chi2,
        "alarm": chi2 > CRITICAL,
        "skipped": False,
    }


def numeric_leaves_gt1(obj: Any, out: list[float]) -> None:
    if isinstance(obj, bool) or obj is None:
        return
    if isinstance(obj, (int, float)):
        if obj > 1:
            out.append(float(obj))
        return
    if isinstance(obj, dict):
        for v in obj.values():
            numeric_leaves_gt1(v, out)
        return
    if isinstance(obj, list):
        for v in obj:
            numeric_leaves_gt1(v, out)


def load_cost_values(path: str = COST_PATH) -> list[float]:
    try:
        with open(path, encoding="utf-8") as f:
            raw = json.loads(f.read())
    except FileNotFoundError:
        return []
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return []
    out: list[float] = []
    numeric_leaves_gt1(raw, out)
    return out


def _extract_named_fields(obj: Any, out: list[float]) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in JSONL_FIELDS:
                if isinstance(v, bool) or v is None:
                    pass
                else:
                    try:
                        fv = float(v)
                        if fv > 1:
                            out.append(fv)
                    except (TypeError, ValueError):
                        pass
            else:
                _extract_named_fields(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _extract_named_fields(v, out)


def load_jsonl_values(cache_dir: str = CACHE) -> list[float]:
    out: list[float] = []
    try:
        names = sorted(os.listdir(cache_dir))
    except OSError:
        return out
    nfiles = 0
    for name in names:
        if not name.endswith(".jsonl"):
            continue
        nfiles += 1
        if nfiles > MAX_JSONL_FILES:
            break
        path = os.path.join(cache_dir, name)
        try:
            with open(path, encoding="utf-8") as f:
                for i, line in enumerate(f):
                    if i >= MAX_LINES_PER_FILE:
                        break
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except (json.JSONDecodeError, TypeError, ValueError):
                        continue
                    _extract_named_fields(obj, out)
        except OSError:
            continue
    return out


def load_wcet_values(db_path: str = LIFECYCLE_DB) -> list[float]:
    if not os.path.exists(db_path):
        return []
    try:
        conn = sqlite3.connect(db_path, timeout=5)
        try:
            tables = {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()}
            if "cron_wcet" not in tables:
                return []
            cols = {r[1] for r in conn.execute("PRAGMA table_info(cron_wcet)").fetchall()}
            if "wcet_ms" not in cols:
                return []
            rows = conn.execute(
                "SELECT wcet_ms FROM cron_wcet WHERE wcet_ms IS NOT NULL"
            ).fetchall()
        finally:
            conn.close()
    except sqlite3.Error:
        return []
    out: list[float] = []
    for (v,) in rows:
        try:
            fv = float(v)
        except (TypeError, ValueError):
            continue
        if fv > 1:
            out.append(fv)
    return out


def load_skill_latency_values(cache_dir: str = CACHE) -> list[float]:
    """Direct read of skill-latency.jsonl elapsed_ms (known-good magnitude field)."""
    out: list[float] = []
    path = os.path.join(cache_dir, "skill-latency.jsonl")
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    v = obj.get("elapsed_ms")
                    if v is not None and not isinstance(v, bool):
                        fv = float(v)
                        if fv > 1:
                            out.append(fv)
                except Exception:
                    continue
    except OSError:
        pass
    return out


def run() -> dict[str, Any]:
    sources = [
        report_source("skill-latency.elapsed_ms", load_skill_latency_values()),
        report_source("cost-attribution.json", load_cost_values()),
        report_source("cache-jsonl", load_jsonl_values()),
        report_source("lifecycle.cron_wcet", load_wcet_values()),
    ]
    return {
        "sources": sources,
        "any_alarm": any(s.get("alarm") for s in sources),
        "critical": CRITICAL,
        "min_n": MIN_N,
    }


def self_test() -> None:
    rng = random.Random(0)
    benford_vals = [int(10 ** rng.uniform(0, 4)) for _ in range(1000)]
    r_b = report_source("selftest-benford", benford_vals)
    assert not r_b["skipped"], r_b
    assert r_b["chi2"] < CRITICAL, r_b

    rng2 = random.Random(0)
    uniform_vals = [rng2.randint(1, 9) * 100 for _ in range(1000)]
    r_u = report_source("selftest-uniform", uniform_vals)
    assert not r_u["skipped"], r_u
    assert r_u["chi2"] > CRITICAL, r_u

    # N < 30 skip
    r_s = report_source("tiny", [10, 20, 30])
    assert r_s["skipped"] and r_s["alarm"] is False

    # leading digit of <1 skipped
    assert leading_digit(0.5) is None
    assert leading_digit(0) is None
    assert leading_digit(1234) == 1
    assert leading_digit(9.9) == 9

    print("self-test: PASS")


def main() -> int:
    if "--self-test" in sys.argv:
        self_test()
        return 0
    result = run()
    try:
        _atomic_write(OUT_PATH, result)
    except OSError:
        pass
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
