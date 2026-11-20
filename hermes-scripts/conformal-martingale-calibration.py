#!/usr/bin/env python3
"""Per-tool conformal power-martingale calibration drift detector.

Vovk conformal martingale (power betting, epsilon=0.2) on predicted_confidence
sequences from calibration-log.jsonl.

HARD RULE: rows with scope=='ue_blackbox' are skipped entirely. Do not fall
back to tool_name for those rows.

One mixed 168k-row stream is not exchangeable; we run one martingale per
tool_name (or per non-blackbox scope when tool_name is missing). Window=400.

stdlib only. Fail-open. --self-test and --run.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import math
import os
import random
import sys
from datetime import datetime, timezone, UTC
from pathlib import Path

ALPHA = 0.05
EPSILON = 0.2  # power martingale betting parameter
WINDOW = 400
MIN_N = 30
MAX_KEYS = 40


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


def p_value_rank(x: float, history: list[float]) -> float | None:
    n = len(history)
    if n == 0:
        return None
    le = sum(1 for h in history if h <= x)
    return (1.0 + le) / (n + 1.0)


def power_martingale(scores: list[float], alpha: float = ALPHA, epsilon: float = EPSILON):
    xs = []
    for s in scores:
        try:
            v = float(s)
        except (TypeError, ValueError):
            continue
        if v != v:  # NaN
            continue
        xs.append(v)
    n = len(xs)
    if n < 2:
        return {
            "detected": False,
            "index": None,
            "martingale": 1.0,
            "n": n,
            "status": "insufficient_data",
        }
    log_s = 0.0
    capital = 1.0
    idx = None
    thresh = 1.0 / max(alpha, 1e-12)
    eps = min(max(epsilon, 1e-6), 0.99)
    for t in range(1, n):
        pv = p_value_rank(xs[t], xs[:t])
        if pv is None:
            continue
        pv = min(max(pv, 1e-12), 1.0)
        # Power betting increment with CUSUM floor (jumper/Page restart).
        # Without the floor, S decays to 0 on typical p~0.5 and cannot recover.
        log_s = max(0.0, log_s + math.log(eps) + (eps - 1.0) * math.log(pv))
        log_s = min(log_s, 40.0)
        capital = math.exp(log_s)
        if capital >= thresh and idx is None:
            idx = t
    return {
        "detected": capital >= thresh,
        "index": idx,
        "martingale": capital,
        "n": n,
        "status": "ok",
        "alpha": alpha,
        "epsilon": eps,
    }


def series_key(rec: dict) -> str | None:
    """Skip ue_blackbox entirely. Never fall back to tool_name for those rows."""
    scope = rec.get("scope")
    if scope == "ue_blackbox":
        return None
    tool = rec.get("tool_name")
    if tool:
        return "tool:" + str(tool)
    if scope:
        return "scope:" + str(scope)
    return "ungrouped"


def load_series(calib_path: Path, window: int = WINDOW) -> tuple[dict[str, list[float]], int, int]:
    series: dict[str, list[float]] = {}
    skipped_ue = 0
    skipped_other = 0
    if not calib_path.exists():
        return series, skipped_ue, skipped_other
    try:
        fh = calib_path.open(encoding="utf-8", errors="replace")
    except OSError:
        return series, skipped_ue, skipped_other
    with fh:
        for line in fh:
            raw = line.strip()
            if not raw:
                continue
            try:
                rec = json.loads(raw)
            except json.JSONDecodeError:
                skipped_other += 1
                continue
            if not isinstance(rec, dict):
                skipped_other += 1
                continue
            if rec.get("scope") == "ue_blackbox":
                skipped_ue += 1
                continue
            key = series_key(rec)
            if key is None:
                skipped_ue += 1
                continue
            raw_score = rec.get("predicted_confidence")
            if raw_score is None:
                skipped_other += 1
                continue
            try:
                score = float(raw_score)
            except (TypeError, ValueError):
                skipped_other += 1
                continue
            if score != score:
                skipped_other += 1
                continue
            bucket = series.setdefault(key, [])
            bucket.append(score)
    # keep last WINDOW per key
    for k, xs in list(series.items()):
        if len(xs) > window:
            series[k] = xs[-window:]
    return series, skipped_ue, skipped_other


def detect_all(series: dict[str, list[float]], skipped_ue: int, skipped_other: int) -> dict:
    results = []
    any_hit = False
    # prefer largest series
    items = sorted(series.items(), key=lambda kv: -len(kv[1]))[:MAX_KEYS]
    for key, xs in items:
        if len(xs) < MIN_N:
            continue
        r = power_martingale(xs)
        r["key"] = key
        results.append(r)
        if r.get("detected"):
            any_hit = True
    status = "ok" if results else "insufficient_data"
    return {
        "ts": _now(),
        "status": status,
        "detected": any_hit,
        "alpha": ALPHA,
        "epsilon": EPSILON,
        "window": WINDOW,
        "skipped_ue_blackbox": skipped_ue,
        "skipped_other": skipped_other,
        "n_series": len(results),
        "series": results,
        "theory": "Vovk power conformal martingale eps=0.2 per tool",
    }


def run(root: Path | None = None) -> dict:
    root = root or _hermes_root()
    series, skipped_ue, skipped_other = load_series(root / "cache" / "calibration-log.jsonl")
    report = detect_all(series, skipped_ue, skipped_other)
    out = root / "cache" / "conformal-martingale-calibration.json"
    _atomic_write(out, report)
    return report


def _self_test() -> int:
    os.environ["HERMES_HOME"] = str(Path.home() / ".hermes" / "profiles" / "fork")
    assert _hermes_home() == Path.home() / ".hermes"

    empty = power_martingale([])
    assert empty["status"] == "insufficient_data"
    rng = random.Random(2)
    stable = [rng.gauss(0.6, 0.02) for _ in range(80)]
    r0 = power_martingale(stable)
    assert r0["status"] == "ok"
    shifted = stable + [rng.gauss(0.1, 0.02) for _ in range(40)]
    r1 = power_martingale(shifted)
    assert r1["n"] == 120
    # 1/p mixing would trip immediately; power martingale should still see the shift
    assert r1["detected"] is True, r1

    recs = [
        {"scope": "ue_blackbox", "tool_name": "evil", "predicted_confidence": 0.01},
        {"tool_name": "terminal", "predicted_confidence": 0.5},
        {"scope": "ue_blackbox", "predicted_confidence": 0.99, "tool_name": "terminal"},
        {"tool_name": "terminal", "predicted_confidence": 0.55},
        {"predicted_confidence": 0.4},
    ]
    assert series_key(recs[0]) is None
    assert series_key(recs[1]) == "tool:terminal"
    assert series_key(recs[2]) is None  # never fall back to tool_name
    assert series_key(recs[3]) == "tool:terminal"
    assert series_key(recs[4]) == "ungrouped"

    print("[conformal-martingale-calibration] --self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Per-tool conformal martingale on calibration-log")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--run", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        try:
            return _self_test()
        except Exception as exc:
            print(f"[conformal-martingale-calibration] --self-test FAIL: {exc}")
            return 1
    try:
        report = run()
        hits = [s for s in (report.get("series") or []) if s.get("detected")]
        print(json.dumps({
            "status": report.get("status"),
            "detected": report.get("detected"),
            "n_series": report.get("n_series"),
            "skipped_ue_blackbox": report.get("skipped_ue_blackbox"),
            "hits": [{"key": h.get("key"), "martingale": h.get("martingale"), "index": h.get("index")} for h in hits[:8]],
        }, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "error", "reason": str(exc)}))
        return 0


if __name__ == "__main__":
    sys.exit(main())
