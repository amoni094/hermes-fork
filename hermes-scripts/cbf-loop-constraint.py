#!/usr/bin/env python3
"""Control barrier function gate between loop-PID output and irreversible actions."""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime, timezone, UTC
from pathlib import Path

_hermes_base = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_hermes_profile = os.environ.get("HERMES_PROFILE", "")
if os.environ.get("HERMES_ROOT"):
    _hermes_root = Path(os.environ["HERMES_ROOT"])
else:
    _hermes_root = (
        (_hermes_base / "profiles" / _hermes_profile)
        if _hermes_profile and "profiles" not in str(_hermes_base)
        else _hermes_base
    )
CACHE = _hermes_root / "cache"
OUT_PATH = CACHE / "cbf-safe-action.json"


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _atomic_write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_name(path.name + ".lock")
    fd = os.open(str(lock_path), os.O_RDWR | os.O_CREAT, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
        os.replace(str(tmp), str(path))
    finally:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        except OSError:
            pass
        os.close(fd)


def _lifecycle_db() -> Path:
    env = os.environ.get("LIFECYCLE_DB", "").strip()
    if env:
        return Path(env)
    return _hermes_base / "memory-facts" / "lifecycle.db"


def _load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return obj if isinstance(obj, dict) else None


def _read_input() -> dict:
    composite = _load_json(CACHE / "loop-stability-composite.json")
    if composite is not None:
        return composite
    pid = _load_json(CACHE / "loop-pid-output.json")
    if pid is not None:
        return pid
    return {"control_signal": 0.0, "lyapunov_ok": True, "iss_ok": True}


def constrain(inp: dict | None = None, out_path: Path | None = None) -> dict:
    inp = inp if inp is not None else _read_input()
    out_path = out_path or OUT_PATH
    max_signal = float(os.environ.get("CBF_MAX_SIGNAL", "1.0"))
    raw = inp.get("control_signal", 0.0)
    try:
        raw = float(raw)
    except (TypeError, ValueError):
        raw = 0.0
    h = raw
    lyap = bool(inp.get("lyapunov_ok", True))
    iss = bool(inp.get("iss_ok", True))
    emergency_stop = not (lyap and iss)
    if emergency_stop:
        safe = 0.0
        constrained = True
    elif abs(h) > max_signal:
        safe = max_signal * (1.0 if h >= 0 else -1.0)
        constrained = True
    else:
        safe = h
        constrained = False
    result = {
        "ts": _now(),
        "raw_signal": raw,
        "safe_signal": safe,
        "constrained": constrained,
        "emergency_stop": emergency_stop,
        "h_value": h,
        "MAX_SIGNAL": max_signal,
    }
    _atomic_write(out_path, result)
    _maybe_log(result)
    return result


def _maybe_log(report: dict) -> None:
    db = _lifecycle_db()
    if not db.exists():
        return
    try:
        conn = sqlite3.connect(str(db), timeout=30)
        conn.execute("PRAGMA journal_mode=WAL")
        try:
            tables = {
                r[0]
                for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            }
            if "cbf_log" not in tables:
                return
            conn.execute(
                "INSERT INTO cbf_log(ts, raw_signal, safe_signal, constrained, emergency_stop) VALUES (?,?,?,?,?)",
                (
                    report["ts"],
                    report["raw_signal"],
                    report["safe_signal"],
                    1 if report["constrained"] else 0,
                    1 if report["emergency_stop"] else 0,
                ),
            )
            conn.commit()
        finally:
            conn.close()
    except Exception:
        pass


def _self_test() -> int:
    td = Path(tempfile.mkdtemp(prefix="cbf-loop-"))
    cache = td / "cache"
    cache.mkdir(parents=True)
    (cache / "loop-stability-composite.json").write_text(
        json.dumps(
            {"lyapunov_ok": False, "control_signal": 0.5, "iss_ok": True},
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["HERMES_ROOT"] = str(td)
    env["LIFECYCLE_DB"] = str(td / (f"no-cbf-{uuid.uuid4().hex}.db"))
    proc = subprocess.run(
        [sys.executable, str(Path(__file__).resolve())],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if proc.returncode != 0:
        raise AssertionError(f"subprocess rc={proc.returncode} stderr={proc.stderr}")
    out = json.loads(proc.stdout)
    assert out["emergency_stop"] is True, out
    assert out["constrained"] is True, out
    assert out["safe_signal"] == 0.0, out
    written = json.loads((cache / "cbf-safe-action.json").read_text(encoding="utf-8"))
    assert written["emergency_stop"] is True, written
    assert written["constrained"] is True, written
    try:
        for p in cache.iterdir():
            p.unlink()
        cache.rmdir()
        td.rmdir()
    except OSError:
        pass
    print("[cbf-loop-constraint] --self-test PASS emergency_stop")
    return 0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        try:
            sys.exit(_self_test())
        except Exception as exc:
            print(f"[cbf-loop-constraint] --self-test FAIL: {exc}")
            sys.exit(1)
    try:
        r = constrain()
        print(json.dumps(r))
    except Exception as e:
        print(json.dumps({"status": "error", "reason": str(e)}))
        sys.exit(0)


if __name__ == "__main__":
    main()
