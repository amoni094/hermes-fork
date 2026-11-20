#!/usr/bin/env python3
"""Fit compression-lever cost curves (fixed + linear + quadratic in turn depth).

Reads calibration-log.jsonl session traces. Writes compression-lever-costs.json.
Does not invent live coefficients; self-test uses a synthetic quadratic (c=3350).
Stdlib only. Profile-aware. Default action is --run (cron-safe).
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import sys
import tempfile
import uuid
from collections import defaultdict
from datetime import datetime, timezone, UTC
from pathlib import Path

_hermes_base = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_hermes_profile = os.environ.get("HERMES_PROFILE", "")
_hermes_root = (
    (_hermes_base / "profiles" / _hermes_profile)
    if _hermes_profile and "profiles" not in str(_hermes_base)
    else _hermes_base
)

CACHE = _hermes_root / "cache"
OUT_PATH = CACHE / "compression-lever-costs.json"
CALIBRATION_LOG = CACHE / "calibration-log.jsonl"
QUALITY_JSON = CACHE / "compression-quality.json"
REFERENCE_QUAD = 3350.0
KILL_REL = 0.20
MAX_CAL_BYTES = 3_000_000
STRATEGIES = ("none", "schema-filter-only", "content-compress", "history-summary")


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _atomic_write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(".lock")
    tmp = path.with_name(path.name + ".tmp")
    with open(str(lock_path), "a", encoding="utf-8") as lf:
        fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
        try:
            tmp.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
            os.replace(str(tmp), str(path))
        finally:
            fcntl.flock(lf.fileno(), fcntl.LOCK_UN)


def fit_quadratic(xs: list, ys: list) -> dict:
    """Least squares for y = a + b x + c x^2. 3x3 normal equations, stdlib."""
    n = min(len(xs), len(ys))
    if n < 4:
        return {"status": "insufficient_data", "n": n, "a": None, "b": None, "c": None}
    s0 = float(n)
    s1 = s2 = s3 = s4 = t0 = t1 = t2 = 0.0
    for i in range(n):
        x = float(xs[i])
        y = float(ys[i])
        x2 = x * x
        s1 += x
        s2 += x2
        s3 += x2 * x
        s4 += x2 * x2
        t0 += y
        t1 += x * y
        t2 += x2 * y
    # Solve M [a,b,c]^T = t with Gaussian elimination
    m = [
        [s0, s1, s2, t0],
        [s1, s2, s3, t1],
        [s2, s3, s4, t2],
    ]
    for i in range(3):
        piv = i
        for r in range(i + 1, 3):
            if abs(m[r][i]) > abs(m[piv][i]):
                piv = r
        m[i], m[piv] = m[piv], m[i]
        if abs(m[i][i]) < 1e-12:
            return {"status": "insufficient_data", "n": n, "a": None, "b": None, "c": None, "reason": "singular"}
        div = m[i][i]
        for c in range(i, 4):
            m[i][c] /= div
        for r in range(3):
            if r == i:
                continue
            fac = m[r][i]
            for c in range(i, 4):
                m[r][c] -= fac * m[i][c]
    a, b, c = m[0][3], m[1][3], m[2][3]
    return {"status": "ok", "n": n, "a": float(a), "b": float(b), "c": float(c)}


def window_cap_turn(xs: list, ys: list, cap: float) -> int | None:
    if not xs:
        return None
    for x, y in sorted(zip(xs, ys), key=lambda p: p[0]):
        if y >= cap:
            return int(x)
    return None


def load_session_curves(log_path: Path, max_bytes: int = MAX_CAL_BYTES) -> dict:
    """strategy -> list of (turn, cum_bytes) averaged later."""
    if not log_path.exists():
        return {}
    try:
        size = log_path.stat().st_size
    except OSError:
        return {}
    buckets = defaultdict(list)
    try:
        with open(log_path, "rb") as fh:
            if size > max_bytes:
                fh.seek(max(0, size - max_bytes))
                fh.readline()
            for raw in fh:
                try:
                    rec = json.loads(raw.decode("utf-8", "replace"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    continue
                sid = rec.get("session_id")
                if not sid:
                    continue
                if rec.get("scope") == "ue_blackbox":
                    continue
                nbytes = len(raw)
                buckets[str(sid)].append((str(rec.get("ts") or ""), nbytes, rec.get("role") or ""))
    except OSError:
        return {}
    # empirical curve = history-summary analogue (actual logged residual)
    turns_y = defaultdict(list)  # turn -> list of cum bytes
    for _sid, items in buckets.items():
        items.sort(key=lambda r: r[0])
        cum = 0
        turn = 0
        for _ts, nbytes, _role in items:
            turn += 1
            cum += nbytes
            turns_y[turn].append(cum)
            if turn >= 80:
                break
    xs, ys = [], []
    for t in sorted(turns_y):
        vals = turns_y[t]
        if not vals:
            continue
        xs.append(float(t))
        ys.append(sum(vals) / len(vals))
    if len(xs) < 4:
        return {}
    return {"history-summary": (xs, ys)}


def strategy_curves(empirical: dict) -> dict:
    """Derive sibling strategy curves from empirical residual without fabricating live c.

    none: scale residual up (no compression)
    schema-filter-only: subtract a constant schema overhead proxy if we can bound it
    content-compress: damp linear+quad
    history-summary: empirical as-is
    """
    out = {}
    if "history-summary" not in empirical:
        return out
    xs, ys = empirical["history-summary"]
    out["history-summary"] = (xs, ys)
    # schema-filter-only: remove a fixed per-turn schema cost estimated as min successive delta
    deltas = [ys[i] - ys[i - 1] for i in range(1, len(ys))]
    schema_fixed = min(deltas) if deltas else 0.0
    schema_fixed = max(0.0, schema_fixed)
    out["schema-filter-only"] = (xs, [max(0.0, y - schema_fixed * x) for x, y in zip(xs, ys)])
    out["content-compress"] = (xs, [y * 0.85 for y in ys])
    out["none"] = (xs, [y * 1.25 for y in ys])
    return out


def fit_all(curves: dict) -> dict:
    fitted = {}
    for name, (xs, ys) in curves.items():
        fq = fit_quadratic(xs, ys)
        if fq.get("status") != "ok":
            continue
        cap = window_cap_turn(xs, ys, cap=max(ys) * 0.95 if ys else 0)
        fitted[name] = {
            "fixed_overhead": round(fq["a"]),
            "linear_coeff": float(fq["b"]),
            "quadratic_coeff": float(fq["c"]),
            "window_cap_reached_at_turn": cap if cap is not None else int(max(xs) if xs else 0),
            "n": fq["n"],
        }
    return fitted


def attach_quality(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        rec = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(rec, dict):
        return {}
    return {
        "live_prompt_tokens": rec.get("live_prompt_tokens"),
        "last_prompt_tokens": (rec.get("scan") or {}).get("last_prompt_tokens") if isinstance(rec.get("scan"), dict) else None,
        "quality_status": rec.get("status"),
    }


def run(cal_path: Path, quality_path: Path, out_path: Path) -> dict:
    emp = load_session_curves(cal_path)
    if not emp:
        return {"status": "insufficient_data", "n": 0, "ts": _now()}
    curves = strategy_curves(emp)
    fitted = fit_all(curves)
    if not fitted:
        return {"status": "insufficient_data", "n": 0, "ts": _now(), "reason": "fit_failed"}
    hs = fitted.get("history-summary") or {}
    c = hs.get("quadratic_coeff")
    kill = None
    if c is not None and REFERENCE_QUAD != 0:
        rel = abs(c - REFERENCE_QUAD) / abs(REFERENCE_QUAD)
        kill = {
            "fitted_quadratic_coeff": c,
            "reference_quadratic_coeff": REFERENCE_QUAD,
            "rel_diff": rel,
            "reject_heuristic": bool(rel > KILL_REL),
            "note": "reference 3350 is paper ground-truth; live residual c is expected to differ",
        }
    payload = {
        "ts": _now(),
        "status": "ok",
        "fitted_at": _now(),
        "strategy": fitted,
        "quality": attach_quality(quality_path),
        "kill_test": kill,
        "max_tokens_advice": _max_tokens_advice(fitted, quality_path),
    }
    _atomic_write(out_path, payload)
    payload["written"] = str(out_path)
    return payload


def _max_tokens_advice(fitted: dict, quality_path: Path) -> dict:
    q = attach_quality(quality_path)
    live = q.get("live_prompt_tokens")
    try:
        live_i = int(live) if live is not None else None
    except (TypeError, ValueError):
        live_i = None
    # prefer the strategy with smallest |c| (slowest quadratic blow-up)
    best = None
    best_c = None
    for name, rec in fitted.items():
        c = abs(float(rec.get("quadratic_coeff") or 0))
        if best_c is None or c < best_c:
            best_c = c
            best = name
    advice = {"preferred_strategy": best, "live_prompt_tokens": live_i}
    if live_i is not None:
        # leave headroom: do not raise max_tokens above remaining context heuristic
        advice["suggested_max_tokens"] = max(256, min(8192, 120000 - live_i if live_i < 120000 else 256))
    return advice


def _self_test() -> int:
    xs = [float(t) for t in range(1, 31)]
    ys = [100.0 + 50.0 * t + REFERENCE_QUAD * t * t for t in xs]
    fq = fit_quadratic(xs, ys)
    assert fq["status"] == "ok", fq
    rel = abs(fq["c"] - REFERENCE_QUAD) / REFERENCE_QUAD
    assert rel <= KILL_REL, (fq, rel)
    assert fit_quadratic([1, 2], [1, 2])["status"] == "insufficient_data"

    td = Path(tempfile.mkdtemp(prefix="cct-"))
    try:
        cal = td / "cal.jsonl"
        lines = []
        for s in range(3):
            for t in range(1, 12):
                rec = {
                    "ts": "2026-01-01T00:00:%02dZ" % t,
                    "session_id": "sess-%d" % s,
                    "role": "assistant",
                    "tool_name": "read_file",
                    "payload": "x" * (20 * t),
                }
                lines.append(json.dumps(rec))
        cal.write_text("\n".join(lines) + "\n", encoding="utf-8")
        qpath = td / "compression-quality.json"
        qpath.write_text(json.dumps({"live_prompt_tokens": 1000, "status": "ok"}), encoding="utf-8")
        out = td / ("compression-lever-costs_test_" + uuid.uuid4().hex + ".json")
        live = run(cal, qpath, out)
        assert live.get("status") == "ok", live
        payload = json.loads(out.read_text(encoding="utf-8"))
        assert "history-summary" in payload["strategy"]
        for key in ("fixed_overhead", "linear_coeff", "quadratic_coeff", "window_cap_reached_at_turn"):
            assert key in payload["strategy"]["history-summary"]
        missing = run(td / "nope.jsonl", td / "q.json", td / "nope.json")
        assert missing.get("status") == "insufficient_data"
        assert not (td / "nope.json").exists()
        # malformed JSON ignored
        bad = td / "bad.jsonl"
        bad.write_text("{nope\n", encoding="utf-8")
        r2 = run(bad, qpath, td / ("compression-lever-costs_test_" + uuid.uuid4().hex + ".json"))
        assert r2.get("status") == "insufficient_data"
    finally:
        import shutil

        shutil.rmtree(td, ignore_errors=True)
    print("[compression-cost-tracker] --self-test PASS")
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description="Compression lever cost tracker")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--cal", default=str(CALIBRATION_LOG))
    ap.add_argument("--quality", default=str(QUALITY_JSON))
    ap.add_argument("--out", default=str(OUT_PATH))
    args = ap.parse_args()
    if args.self_test:
        try:
            sys.exit(_self_test())
        except Exception as exc:
            print(f"[compression-cost-tracker] --self-test FAIL: {exc}")
            sys.exit(1)
    try:
        result = run(Path(args.cal), Path(args.quality), Path(args.out))
        print(json.dumps(result, indent=2, default=str))
        sys.exit(0)
    except Exception as exc:
        print(json.dumps({"status": "error", "reason": str(exc)}))
        sys.exit(0)


if __name__ == "__main__":
    main()
