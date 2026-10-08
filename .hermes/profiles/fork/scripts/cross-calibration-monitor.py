#!/usr/bin/env python3
"""Cross-calibration monitor: detect drift across the three independent calibration silos.

Silos monitored:
  1. reasoning-calibration.jsonl  – reasoning-complexity-classifier.py
     metric: was_correct (bool → 0/1 float)
  2. calibration-log.jsonl        – calibration-threshold-updater.py
     metric: observed_rate (float from agreed/total per-entry, i.e. agreed=True→1.0 else 0.0)
  3. routing-calibration.jsonl    – memory-query-router.py
     metric: result_count (int, normalised to 0-1 by clipping at 10)

Flags:
  DRIFT_ALARM        – any two silo means differ by >0.15
  TREND_DIVERGENCE   – trend directions conflict (one ↑, one ↓, both |slope|>0.01)

Exit 1 if any alarm, 0 otherwise.
"""

import json
import math
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Profile-aware path resolution (same pattern as the other scripts)
# ---------------------------------------------------------------------------
_hermes_base = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_hermes_profile = os.environ.get("HERMES_PROFILE", "")
_hermes_root = (
    (_hermes_base / "profiles" / _hermes_profile)
    if _hermes_profile and "profiles" not in str(_hermes_base)
    else _hermes_base
)
CACHE_DIR = _hermes_root / "cache"

# Silo definitions: (name, path, metric_extractor_fn)
REASONING_CALIB = CACHE_DIR / "reasoning-calibration.jsonl"
CONDORCET_CALIB = CACHE_DIR / "calibration-log.jsonl"
ROUTING_CALIB   = CACHE_DIR / "routing-calibration.jsonl"

ALARM_PATH = CACHE_DIR / "cross-calibration-alarm.json"

LAST_N       = 50   # lines to read from each log
TREND_N      = 10   # entries for least-squares trend
DRIFT_THRESH = 0.15 # mean-difference threshold
SLOPE_THRESH = 0.01 # slope threshold for trend-direction conflict


# ---------------------------------------------------------------------------
# Metric extractors
# ---------------------------------------------------------------------------

def _extract_reasoning(row: dict) -> float | None:
    """was_correct bool → 1.0/0.0; falls back to predicted_level==actual_level."""
    if "was_correct" in row:
        return 1.0 if row["was_correct"] else 0.0
    pl = row.get("predicted_level", row.get("level"))
    al = row.get("actual_level",    row.get("actual"))
    if pl is not None and al is not None:
        return 1.0 if pl == al else 0.0
    return None


def _extract_condorcet(row: dict) -> float | None:
    """agreed bool → 1.0/0.0 (mirrors calibration-threshold-updater.py's observed_rate)."""
    if "agreed" in row:
        return 1.0 if row["agreed"] else 0.0
    # Fallback: use observed_rate directly if stored
    if "observed_rate" in row:
        try:
            return float(row["observed_rate"])
        except (TypeError, ValueError):
            return None
    return None


def _extract_routing(row: dict) -> float | None:
    """result_count clipped to [0, 10] then normalised to [0, 1]."""
    rc = row.get("result_count", -1)
    try:
        rc = float(rc)
    except (TypeError, ValueError):
        return None
    if rc < 0:
        return None
    return min(rc, 10.0) / 10.0


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def _read_last_n(path: Path, n: int) -> list[dict]:
    """Return up to n parsed JSON objects from the tail of a JSONL file."""
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    tail = lines[-n:] if len(lines) > n else lines
    rows = []
    for line in tail:
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


# ---------------------------------------------------------------------------
# Statistics (stdlib-only)
# ---------------------------------------------------------------------------

def _mean(values: list[float]) -> float:
    return sum(values) / len(values)


def _stddev(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    m = _mean(values)
    variance = sum((v - m) ** 2 for v in values) / (len(values) - 1)
    return math.sqrt(variance)


def _slope(values: list[float]) -> float:
    """Ordinary least-squares slope of values vs index (0, 1, … n-1)."""
    n = len(values)
    if n < 2:
        return 0.0
    xs = [float(i) for i in range(n)]
    xm = _mean(xs)
    ym = _mean(values)
    num = sum((xs[i] - xm) * (values[i] - ym) for i in range(n))
    den = sum((xs[i] - xm) ** 2 for i in range(n))
    return num / den if den != 0 else 0.0


# ---------------------------------------------------------------------------
# Core analysis
# ---------------------------------------------------------------------------

def _analyse_silo(name: str, path: Path, extractor) -> dict:
    rows = _read_last_n(path, LAST_N)
    values = []
    for row in rows:
        v = extractor(row)
        if v is not None:
            values.append(v)

    if not values:
        return {"name": name, "values": [], "mean": None, "stddev": None, "trend": None, "n": 0}

    trend_vals = values[-TREND_N:] if len(values) >= TREND_N else values
    return {
        "name":   name,
        "values": values,
        "mean":   _mean(values),
        "stddev": _stddev(values),
        "trend":  _slope(trend_vals),
        "n":      len(values),
    }


def _check_drift(silos: list[dict]) -> tuple[bool, str]:
    active = [s for s in silos if s["mean"] is not None]
    if len(active) < 2:
        return False, ""
    pairs = []
    for i in range(len(active)):
        for j in range(i + 1, len(active)):
            diff = abs(active[i]["mean"] - active[j]["mean"])
            if diff > DRIFT_THRESH:
                pairs.append(
                    f"{active[i]['name']} vs {active[j]['name']}: "
                    f"|{active[i]['mean']:.3f} − {active[j]['mean']:.3f}| = {diff:.3f}"
                )
    if pairs:
        return True, "DRIFT_ALARM: " + "; ".join(pairs)
    return False, ""


def _check_trend(silos: list[dict]) -> tuple[bool, str]:
    active = [s for s in silos if s["trend"] is not None and abs(s["trend"]) > SLOPE_THRESH]
    if len(active) < 2:
        return False, ""
    positives = [s for s in active if s["trend"] > 0]
    negatives = [s for s in active if s["trend"] < 0]
    if positives and negatives:
        pos_names = [s["name"] for s in positives]
        neg_names = [s["name"] for s in negatives]
        msg = (
            f"TREND_DIVERGENCE: ↑ {pos_names} vs ↓ {neg_names}"
        )
        return True, msg
    return False, ""


# ---------------------------------------------------------------------------
# Output / alarm
# ---------------------------------------------------------------------------

def _severity(drift: bool, trend: bool) -> str:
    if drift and trend:
        return "critical"
    if drift:
        return "high"
    if trend:
        return "medium"
    return "ok"


def _write_alarm(alarm_path: Path, alarm: bool, severity: str, msg: str) -> None:
    payload = {
        "alarm":    alarm,
        "severity": severity,
        "msg":      msg,
        "ts":       datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    alarm_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_fd, tmp_path = tempfile.mkstemp(
        dir=alarm_path.parent, prefix=".cross-calibration-alarm-", suffix=".tmp"
    )
    try:
        with os.fdopen(tmp_fd, "w") as fh:
            json.dump(payload, fh, indent=2)
        os.replace(tmp_path, alarm_path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _print_table(silos: list[dict]) -> None:
    header = f"{'Name':<30} {'Mean':>8} {'Stddev':>8} {'Trend':>10} {'N':>5}"
    print(header)
    print("-" * len(header))
    for s in silos:
        mean_s  = f"{s['mean']:.4f}"   if s["mean"]  is not None else "N/A"
        std_s   = f"{s['stddev']:.4f}" if s["stddev"] is not None else "N/A"
        trend_s = f"{s['trend']:+.5f}" if s["trend"]  is not None else "N/A"
        print(f"{s['name']:<30} {mean_s:>8} {std_s:>8} {trend_s:>10} {s['n']:>5}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    silos_spec = [
        ("reasoning-calibration", REASONING_CALIB, _extract_reasoning),
        ("calibration-log",       CONDORCET_CALIB,  _extract_condorcet),
        ("routing-calibration",   ROUTING_CALIB,    _extract_routing),
    ]

    silos = [_analyse_silo(name, path, extractor) for name, path, extractor in silos_spec]

    drift_alarm, drift_msg  = _check_drift(silos)
    trend_alarm, trend_msg  = _check_trend(silos)
    alarm = drift_alarm or trend_alarm

    msgs = [m for m in [drift_msg, trend_msg] if m]
    combined_msg = "; ".join(msgs) if msgs else "no alarm"
    severity = _severity(drift_alarm, trend_alarm)

    print(f"ALARM: {'YES' if alarm else 'NO'}")
    if alarm:
        for m in msgs:
            print(f"  {m}")
    print()
    _print_table(silos)

    _write_alarm(ALARM_PATH, alarm, severity, combined_msg)
    print(f"\nAlarm written → {ALARM_PATH}")

    return 1 if alarm else 0


if __name__ == "__main__":
    sys.exit(main())
