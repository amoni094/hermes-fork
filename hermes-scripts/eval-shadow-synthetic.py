#!/usr/bin/env python3
"""eval-shadow-synthetic.py — Write synthetic shadow telemetry JSONL.

Emits 200 events mixing high-pass, borderline, and zero-tolerance rows so
shadow-gate-nightly.py / msprt-shadow-gate.py have something to evaluate.

Event shape (compat with shadow_telemetry.evaluate_flag AND fork nightly ZT):
  {session_id, flag, flag_name, pass_rate, n_events, ts, event_type,
   analysis: {score, false_positive}, score}

Usage:
  HERMES_HOME=~/.hermes HERMES_PROFILE=fork python3 eval-shadow-synthetic.py
  python3 eval-shadow-synthetic.py --self-test
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import sys
import time
from pathlib import Path

_hermes_base = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_hermes_profile = os.environ.get("HERMES_PROFILE", "")
_hermes_root = (
    (_hermes_base / "profiles" / _hermes_profile)
    if _hermes_profile and "profiles" not in str(_hermes_base)
    else _hermes_base
)

DEFAULT_OUT = _hermes_root / "cache" / "shadow-telemetry" / "synthetic-eval-session.jsonl"
N_TOTAL = 200
N_PASS = 158
N_BORDER = 40
N_ZT = 2
RHO = 0.6  # AR(1) within-day autocorrelation (loop-eval empirical alpha inflation)


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def _ar1_series(n: int, mu: float, sigma: float, rho: float, rng: random.Random) -> list[float]:
    xs = []
    x = mu
    for _ in range(n):
        x = rho * x + (1.0 - rho) * mu + rng.gauss(0.0, sigma)
        xs.append(x)
    return xs


def generate_events(now: float | None = None, seed: int = 46) -> list[dict]:
    rng = random.Random(seed)
    now = float(now if now is not None else time.time())
    events: list[dict] = []

    def emit(i: int, flag: str, pass_rate: float, event_type: str, session: str) -> dict:
        pr = max(0.0, min(1.0, float(pass_rate)))
        fp = bool(pr < 0.75) and rng.random() < (0.75 - pr)
        # Map pass_rate in [0,1] onto SPRT score scale ~ N(3..5)
        score = 3.0 + 2.0 * pr
        return {
            "schema_version": 1,
            "session_id": session,
            "flag": flag,
            "flag_name": flag,
            "pass_rate": round(pr, 4),
            "n_events": 1,
            "ts": now - (N_TOTAL - i) * 42.0,
            "event_type": event_type,
            "score": round(score, 4),
            "mean_score": round(score, 4),
            "analysis": {
                "score": round(pr, 4),
                "false_positive": fp,
            },
        }

    # 100 high-pass on consistency_scoring (n>=N_MIN_POWER=50, pass_rate>0.8)
    high = [max(0.81, min(0.99, x)) for x in _ar1_series(100, mu=0.92, sigma=0.03, rho=RHO, rng=rng)]
    for i, x in enumerate(high):
        events.append(emit(i, "consistency_scoring", x, "shadow_eval", "sess-high-%02d" % (i // 10)))

    # 58 high-pass + 40 borderline on aimd_controller
    mid_high = [max(0.81, min(0.99, x)) for x in _ar1_series(58, mu=0.88, sigma=0.04, rho=RHO, rng=rng)]
    border = [max(0.52, min(0.68, x)) for x in _ar1_series(40, mu=0.60, sigma=0.04, rho=RHO, rng=rng)]
    base = 100
    for j, x in enumerate(mid_high):
        events.append(emit(base + j, "aimd_controller", x, "shadow_eval", "sess-aimd-%02d" % (j // 10)))
    for j, x in enumerate(border):
        events.append(
            emit(base + 58 + j, "aimd_controller", x, "shadow_eval", "sess-aimd-b-%02d" % (j // 10))
        )

    # 2 zero-tolerance events on loop_detection
    events.append(
        emit(198, "loop_detection", 0.0, "unauthorized_tool_call", "sess-zt-00")
    )
    events.append(
        emit(199, "loop_detection", 0.0, "unauthorized_tool_call", "sess-zt-01")
    )
    events[198]["analysis"]["false_positive"] = True
    events[198]["analysis"]["violation_type"] = "unauthorized_tool_call"
    events[199]["analysis"]["false_positive"] = True
    events[199]["analysis"]["violation_type"] = "unauthorized_tool_call"

    if len(events) != N_TOTAL:
        raise AssertionError("expected %d events, got %d" % (N_TOTAL, len(events)))
    return events


def write_events(path: Path, events: list[dict]) -> Path:
    lines = "".join(json.dumps(e, separators=(",", ":")) + "\n" for e in events)
    _atomic_write_text(path, lines)
    return path


def summarize(events: list[dict]) -> dict:
    n_pass = sum(1 for e in events if e.get("pass_rate", 0) > 0.8)
    n_border = sum(1 for e in events if 0.5 <= e.get("pass_rate", 0) <= 0.75)
    n_zt = sum(1 for e in events if e.get("event_type") == "unauthorized_tool_call")
    flags = sorted({e["flag"] for e in events})
    return {
        "n": len(events),
        "n_pass_gt_0_8": n_pass,
        "n_borderline": n_border,
        "n_zero_tolerance": n_zt,
        "flags": flags,
    }


def self_test() -> int:
    failures = []
    events = generate_events(now=1_700_000_000.0, seed=46)
    if len(events) != 200:
        failures.append("n=%d" % len(events))
    n_zt = sum(1 for e in events if e["event_type"] == "unauthorized_tool_call")
    if n_zt != 2:
        failures.append("zt=%d" % n_zt)
    n_pass = sum(1 for e in events if e["pass_rate"] > 0.8)
    if n_pass < 150:
        failures.append("pass=%d" % n_pass)
    for e in events:
        for k in ("session_id", "flag_name", "pass_rate", "n_events", "ts", "event_type", "flag"):
            if k not in e:
                failures.append(f"missing {k}")
                break
        else:
            if e.get("flag") != e.get("flag_name"):
                failures.append("flag mismatch")
                break
    # empty / malformed resilience: generate_events is pure
    try:
        generate_events(now=0.0, seed=0)
    except Exception as exc:
        failures.append(f"seed0 raised {exc}")
    if failures:
        print(json.dumps({"self_test": "FAIL", "failures": failures}))
        return 1
    print(json.dumps({"self_test": "PASS", **summarize(events)}))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--self-test", action="store_true")
    p.add_argument("--out", default="", help="JSONL output path")
    args = p.parse_args(argv)
    if args.self_test:
        return self_test()
    out = Path(args.out) if args.out else DEFAULT_OUT
    events = generate_events()
    write_events(out, events)
    summary = summarize(events)
    summary["out"] = str(out)
    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    sys.exit(main())
