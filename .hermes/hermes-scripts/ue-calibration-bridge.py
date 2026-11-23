#!/usr/bin/env python3
"""Bridge UE scores into calibration-log.jsonl for calibration-threshold-updater.

Hard core (DPI): predicted_confidence = 1 - composite_ue, then
predicted_confidence = min(predicted_confidence, logprob_confidence)
when logprobs are present. Never claim higher confidence than evidence.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from pathlib import Path
from typing import Any, Optional

_hermes_base = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_hermes_profile = os.environ.get("HERMES_PROFILE", "")
_hermes_root = (
    (_hermes_base / "profiles" / _hermes_profile)
    if _hermes_profile and "profiles" not in str(_hermes_base)
    else _hermes_base
)

SCOPE = "ue_blackbox"


def _clip01(x: Any, default: float = 0.0) -> float:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(v):
        return default
    if v < 0.0:
        return 0.0
    if v > 1.0:
        return 1.0
    return v


def _cache_dir() -> Path:
    override = os.environ.get("UE_CACHE_DIR", "").strip()
    p = Path(override) if override else (_hermes_root / "cache")
    try:
        p.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return p


def _ue_path() -> Path:
    return _cache_dir() / "ue-blackbox-scores.jsonl"


def _calib_path() -> Path:
    return _cache_dir() / "calibration-log.jsonl"


def _state_path() -> Path:
    return _cache_dir() / "ue-calibration-bridge-state.json"


def _atomic_write_json(path: Path, obj: Any) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(str(tmp), str(path))
    except Exception:
        try:
            tmp = path.with_name(path.name + ".tmp")
            if tmp.exists():
                tmp.unlink()
        except Exception:
            pass


def _read_json(path: Path, default: Any) -> Any:
    try:
        if not path.exists():
            return default
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        return data
    except Exception:
        return default


def _iter_jsonl(path: Path):
    try:
        if not path.exists():
            return
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                s = line.strip()
                if not s or not s.startswith("{"):
                    continue
                try:
                    obj = json.loads(s)
                except Exception:
                    continue
                if isinstance(obj, dict):
                    yield obj
    except Exception:
        return


def _append_jsonl(path: Path, obj: Any) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(obj, ensure_ascii=False) + "\n")
            fh.flush()
    except Exception:
        pass


def _entry_id(row: dict) -> str:
    ts = row.get("ts")
    qh = row.get("query_hash") or ""
    return "%s:%s" % (qh, ts)


def predicted_confidence(row: dict) -> Optional[float]:
    if "composite_ue" not in row:
        return None
    try:
        ue = float(row.get("composite_ue"))
    except (TypeError, ValueError):
        return None
    if not math.isfinite(ue):
        return None
    # Negative or >1 UE is not evidence of certainty: fail closed (UE=1, conf=0).
    if ue < 0.0 or ue > 1.0:
        ue = 1.0 if ue < 0.0 else 1.0
    ue = _clip01(ue, default=1.0)
    conf = _clip01(1.0 - ue, default=0.0)
    lp = row.get("logprob_confidence")
    if lp is not None and str(lp).strip() != "":
        lp_c = _clip01(lp, default=conf)
        if conf > lp_c:
            conf = lp_c
    # empty-input rows are not evidence of high confidence
    if row.get("empty_input") is True:
        conf = min(conf, 0.0)
    return _clip01(conf, default=0.0)


def _iso_ts(row: dict) -> str:
    iso = row.get("ts_iso")
    if isinstance(iso, str) and iso:
        return iso
    ts = row.get("ts")
    try:
        tsf = float(ts)
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(tsf))
    except (TypeError, ValueError):
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def sync(since_hours: float = 24.0) -> dict:
    state = _read_json(_state_path(), default={})
    if not isinstance(state, dict):
        state = {}
    seen = state.get("synced_ids")
    if not isinstance(seen, list):
        seen = []
    seen_set = set(str(x) for x in seen[-5000:])  # cap memory
    cutoff = time.time() - max(float(since_hours), 0.0) * 3600.0
    appended = 0
    skipped = 0
    dpi_clamped = 0
    malformed = 0
    for row in _iter_jsonl(_ue_path()) or []:
        try:
            ts = float(row.get("ts", 0.0))
        except (TypeError, ValueError):
            ts = 0.0
            malformed += 1
        if ts and ts < cutoff:
            skipped += 1
            continue
        eid = _entry_id(row)
        if eid in seen_set:
            skipped += 1
            continue
        conf = predicted_confidence(row)
        if conf is None:
            skipped += 1
            continue
        lp = row.get("logprob_confidence")
        raw = _clip01(1.0 - _clip01(row.get("composite_ue"), default=1.0), default=0.0)
        if lp is not None and str(lp).strip() != "" and raw > _clip01(lp, default=raw) + 1e-12:
            dpi_clamped += 1
        out = {
            "ts": _iso_ts(row),
            "query_hash": row.get("query_hash") or "",
            "predicted_confidence": round(conf, 4),
            "scope": SCOPE,
        }
        _append_jsonl(_calib_path(), out)
        seen_set.add(eid)
        seen.append(eid)
        appended += 1
    state_out = {
        "synced_ids": seen[-5000:],
        "last_sync_ts": time.time(),
        "last_appended": appended,
    }
    _atomic_write_json(_state_path(), state_out)
    return {
        "appended": appended,
        "skipped": skipped,
        "dpi_clamped": dpi_clamped,
        "malformed": malformed,
        "ue_path": str(_ue_path()),
        "calib_path": str(_calib_path()),
        "since_hours": since_hours,
    }


def status() -> dict:
    ue_n = sum(1 for _ in (_iter_jsonl(_ue_path()) or []))
    cal_n = 0
    ue_scope = 0
    for row in _iter_jsonl(_calib_path()) or []:
        cal_n += 1
        if row.get("scope") == SCOPE:
            ue_scope += 1
    state = _read_json(_state_path(), default={})
    return {
        "ue_scores": ue_n,
        "calibration_log_rows": cal_n,
        "ue_blackbox_rows": ue_scope,
        "state": state if isinstance(state, dict) else {},
        "ue_path": str(_ue_path()),
        "calib_path": str(_calib_path()),
    }


def self_test() -> int:
    failures: list[str] = []

    def check(cond: bool, msg: str) -> None:
        if not cond:
            failures.append(msg)

    isolated = _hermes_root / "cache" / "scratch" / "ue-self-test-bridge"
    try:
        isolated.mkdir(parents=True, exist_ok=True)
        for leftover in isolated.glob("*"):
            try:
                leftover.unlink()
            except Exception:
                pass
    except Exception:
        pass
    os.environ["UE_CACHE_DIR"] = str(isolated)

    # missing files: sync/status do not raise
    st0 = status()
    check(st0["ue_scores"] == 0, "status missing files")
    syn0 = sync(since_hours=24)
    check(syn0["appended"] == 0, "sync missing files appended")

    now = time.time()
    rows = [
        {"ts": now, "ts_iso": "2026-01-01T00:00:00Z", "query_hash": "aaa", "composite_ue": 0.2, "logprob_confidence": 0.5},
        {"ts": now, "query_hash": "bbb", "composite_ue": 0.9},
        {"ts": now, "query_hash": "ccc", "composite_ue": 0.0, "logprob_confidence": 0.3},  # DPI clamp 1.0 -> 0.3
        {"ts": now, "query_hash": "ddd", "empty_input": True, "composite_ue": 1.0},
        {"ts": now, "query_hash": "eee", "composite_ue": "nope"},
        "not a dict",
    ]
    p = _ue_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write("NOT JSON\n")
        for row in rows:
            if isinstance(row, dict):
                fh.write(json.dumps(row) + "\n")
            else:
                fh.write(str(row) + "\n")
        fh.write("{]\n")

    # DPI unit checks
    c1 = predicted_confidence(rows[0])
    check(c1 is not None and abs(c1 - 0.5) < 1e-9, "DPI min(0.8, 0.5) => 0.5 got %s" % c1)
    c2 = predicted_confidence(rows[1])
    check(c2 is not None and abs(c2 - 0.1) < 1e-9, "no logprob 1-0.9=0.1 got %s" % c2)
    c3 = predicted_confidence(rows[2])
    check(c3 is not None and abs(c3 - 0.3) < 1e-9, "DPI clamp 1.0 to 0.3 got %s" % c3)
    check(c3 <= 0.3, "DPI upper bound")
    c4 = predicted_confidence(rows[3])
    check(c4 == 0.0, "empty_input conf")
    c5 = predicted_confidence({"composite_ue": 2.5})
    check(c5 == 0.0, "ue>1 clips then 1-1=0 got %s" % c5)
    c6 = predicted_confidence({"composite_ue": -1})
    check(c6 == 0.0, "negative ue must fail-closed conf=0 got %s" % c6)

    syn = sync(since_hours=24)
    check(syn["appended"] >= 3, "appended %s" % syn)
    # idempotent
    syn2 = sync(since_hours=24)
    check(syn2["appended"] == 0, "not idempotent: %s" % syn2)

    # calibration rows valid and DPI-respecting
    cal_rows = list(_iter_jsonl(_calib_path()) or [])
    for cr in cal_rows:
        pc = _clip01(cr.get("predicted_confidence"), default=99)
        check(0.0 <= pc <= 1.0, "calib conf range %s" % cr)
        check(cr.get("scope") == SCOPE, "scope")
        check("query_hash" in cr and "ts" in cr, "schema")

    # the aaa row must not exceed logprob 0.5
    aaa = [c for c in cal_rows if c.get("query_hash") == "aaa"]
    check(aaa and aaa[0]["predicted_confidence"] <= 0.5 + 1e-9, "aaa DPI")
    ccc = [c for c in cal_rows if c.get("query_hash") == "ccc"]
    check(ccc and ccc[0]["predicted_confidence"] <= 0.3 + 1e-9, "ccc DPI")

    if failures:
        print(json.dumps({"self_test": "FAIL", "failures": failures}))
        return 1
    print(json.dumps({"self_test": "PASS", "n_checks": 12}))
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    try:
        ap = argparse.ArgumentParser(description="UE to calibration-log bridge")
        ap.add_argument("--self-test", action="store_true")
        sub = ap.add_subparsers(dest="cmd")
        p_sync = sub.add_parser("sync")
        p_sync.add_argument("--since-hours", type=float, default=24.0)
        sub.add_parser("status")
        sub.add_parser("self-test")
        args = ap.parse_args(argv)
        if args.self_test or args.cmd in ("self-test", "self_test"):
            return self_test()
        if args.cmd == "status":
            print(json.dumps(status(), ensure_ascii=False))
            return 0
        hours = 24.0
        if args.cmd == "sync":
            try:
                hours = float(args.since_hours)
            except (TypeError, ValueError, AttributeError):
                hours = 24.0
            if not math.isfinite(hours) or hours < 0:
                hours = 24.0
        rec = sync(since_hours=hours)
        print(json.dumps(rec, ensure_ascii=False))
        return 0
    except Exception:
        try:
            print(json.dumps({"error": "unhandled", "appended": 0}))
        except Exception:
            pass
        return 1


if __name__ == "__main__":
    sys.exit(main())
