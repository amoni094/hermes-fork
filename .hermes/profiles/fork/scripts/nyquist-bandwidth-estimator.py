#!/usr/bin/env python3
"""nyquist-bandwidth-estimator.py — sampling theorem check for cron periods.

Vetterli: a process of bandwidth B Hz must be sampled at fs >= 2B (Nyquist).
Cron jobs whose period T > 1/(2B) alias the underlying context-pressure signal.

Method:
  1. Read context-pressure / turn-usage series (numeric fill or token ratio).
  2. Autocorrelation r[k]; PSD via rFFT (Wiener–Khinchin).
  3. -3 dB bandwidth = first frequency at which PSD <= peak/2 after the peak.
  4. Flag jobs with T > 1/(2B). Hard core: aliasing detection.

Stdlib + numpy. Usage:
  /usr/bin/python3 nyquist-bandwidth-estimator.py --self-test
  /usr/bin/python3 nyquist-bandwidth-estimator.py
"""
from __future__ import annotations

# numpy-reexec-guard: re-exec under /usr/bin/python3 if numpy unavailable (ADV-006 fix)
import sys as _sys
try:
    import numpy as _np_test  # noqa: F401
    del _np_test
except ImportError:
    import os as _os
    _os.execv('/usr/bin/python3', ['/usr/bin/python3'] + _sys.argv)







import argparse
import json
import math
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

_base = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_profile = os.environ.get("HERMES_PROFILE", "")
_root = (_base / "profiles" / _profile) if _profile and "profiles" not in str(_base) else _base
CACHE = _root / "cache"
JOBS_PATH = _root / "cron" / "jobs.json"
OUT_PATH = CACHE / "nyquist-bandwidth.json"


def _atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def autocorr(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=np.float64)
    x = x - x.mean()
    if x.size < 4:
        return np.array([1.0])
    r = np.correlate(x, x, mode="full")
    mid = x.size - 1
    r = r[mid:]
    if r[0] == 0:
        return r
    return r / r[0]


def bandwidth_hz(x: np.ndarray, dt: float) -> float:
    """-3 dB bandwidth from autocorr PSD. dt in seconds."""
    if dt <= 0 or x.size < 8:
        return 0.0
    r = autocorr(x)
    psd = np.abs(np.fft.rfft(r))
    freqs = np.fft.rfftfreq(r.size, d=dt)
    if psd.size <= 1:
        return 0.0
    peak_i = int(np.argmax(psd[1:]) + 1)
    half = psd[peak_i] / 2.0  # -3 dB
    for i in range(peak_i, psd.size):
        if psd[i] <= half:
            return float(freqs[i])
    return float(freqs[-1])


def aliases(period_s: float, B: float) -> bool:
    """True if sampling is below Nyquist: 1/T < 2B  <=>  T > 1/(2B)."""
    if B <= 0 or period_s <= 0:
        return False
    return period_s > 1.0 / (2.0 * B)


def _job_period_seconds(job: dict) -> float | None:
    sched = job.get("schedule") or {}
    kind = sched.get("kind")
    if kind == "interval":
        minutes = sched.get("minutes")
        if minutes:
            return float(minutes) * 60.0
    expr = sched.get("expr") or ""
    # crude cron: */N * * * * → N minutes
    parts = expr.split()
    if len(parts) >= 1 and parts[0].startswith("*/"):
        try:
            n = int(parts[0][2:])
            return n * 60.0
        except ValueError:
            return None
    if expr == "0 * * * *":
        return 3600.0
    if expr.endswith("* * *") and parts[0] == "0" and parts[1].startswith("*/"):
        try:
            return int(parts[1][2:]) * 3600.0
        except ValueError:
            return None
    if kind == "cron" and expr == "0 7 * * *":
        return 86400.0
    if kind == "cron":
        # daily-ish fallback
        if len(parts) == 5 and parts[2] == "*" and parts[3] == "*" and parts[4] == "*":
            if parts[1].isdigit() and parts[0].isdigit():
                return 86400.0
    return None


def _load_pressure_series() -> tuple[np.ndarray, float]:
    candidates = []
    for d in (CACHE, _base / "cache", _root / "logs"):
        if not d.exists():
            continue
        candidates.extend(d.glob("*pressure*.jsonl"))
        candidates.extend(d.glob("turn_usage*.jsonl"))
        candidates.extend(d.glob("*turn*usage*.jsonl"))
    if not candidates:
        return np.array([]), 60.0
    path = sorted(candidates, key=lambda p: p.stat().st_mtime)[-1]
    xs, ts = [], []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        val = row.get("fill") or row.get("ratio") or row.get("pressure") or row.get("tokens")
        if isinstance(val, str):
            if val.upper() == "HIGH":
                val = 1.0
            elif val.upper() == "LOW":
                val = 0.0
            else:
                try:
                    val = float(val)
                except ValueError:
                    continue
        if isinstance(val, (int, float)):
            xs.append(float(val))
            t = row.get("ts") or row.get("t")
            if isinstance(t, (int, float)):
                ts.append(float(t))
    x = np.asarray(xs, dtype=np.float64)
    dt = 60.0
    if len(ts) >= 2:
        dts = np.diff(sorted(ts))
        dts = dts[dts > 0]
        if dts.size:
            dt = float(np.median(dts))
    return x, dt


def self_test() -> int:
    rng = np.random.default_rng(1)
    dt = 1.0
    t = np.arange(0, 512) * dt
    # 0.05 Hz sine (period 20s). Nyquist at 0.1 Hz → T>10s aliases.
    x = np.sin(2 * np.pi * 0.05 * t) + 0.01 * rng.normal(size=t.size)
    B = bandwidth_hz(x, dt)
    # Must detect that T=30s aliases and T=1s does not, given B around 0.05
    if B <= 0:
        print(json.dumps({"passed": False, "reason": "B<=0", "B": B}))
        return 1
    if not aliases(30.0, B):
        print(json.dumps({"passed": False, "reason": "missed aliasing", "B": B}))
        return 1
    if aliases(1.0, B):
        print(json.dumps({"passed": False, "reason": "false alias on fast sample", "B": B}))
        return 1
    print(json.dumps({
        "property": "aliasing iff T > 1/(2B)",
        "passed": True,
        "B_hz": B,
        "nyquist_period_s": 1.0 / (2.0 * B),
    }))
    return 0


def run() -> int:
    x, dt = _load_pressure_series()
    B = bandwidth_hz(x, dt) if x.size >= 8 else 0.0
    jobs = []
    try:
        data = json.loads(JOBS_PATH.read_text(encoding="utf-8"))
        raw = data.get("jobs", data) if isinstance(data, dict) else data
        jobs = [j for j in (raw or []) if isinstance(j, dict)]
    except Exception:
        jobs = []
    flagged = []
    for job in jobs:
        if job.get("enabled") is False:
            continue
        T = _job_period_seconds(job)
        if T is None or B <= 0:
            continue
        if aliases(T, B):
            flagged.append({
                "id": job.get("id"),
                "name": job.get("name"),
                "period_s": T,
                "nyquist_period_s": 1.0 / (2.0 * B),
                "aliasing": True,
            })
    out = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "n_samples": int(x.size),
        "dt_s": dt,
        "bandwidth_hz": B,
        "nyquist_fs": (2.0 * B) if B > 0 else None,
        "n_jobs": len(jobs),
        "n_aliased": len(flagged),
        "aliased_jobs": flagged[:50],
        "theorem": "Vetterli sampling / Nyquist fs >= 2B",
    }
    _atomic_write(OUT_PATH, out)
    print(json.dumps({k: out[k] for k in ("bandwidth_hz", "n_samples", "n_aliased", "n_jobs")}))
    for f in flagged[:10]:
        print(f"ALIASING: job {f['id']} T={f['period_s']}s > 1/(2B)={f['nyquist_period_s']:.3f}s")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--self-test", action="store_true")
    args = p.parse_args(argv)
    if args.self_test:
        return self_test()
    return run()


if __name__ == "__main__":
    sys.exit(main())
