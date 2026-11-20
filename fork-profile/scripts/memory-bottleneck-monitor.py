#!/usr/bin/env python3
"""
Memory Bottleneck Monitor — I(episodic; semantic) tracking (stdlib Kraskov k-NN).

Source:    arXiv:2609.24647 — information-theoretic bounds on memory compression
Invariant: I(episodic; semantic) > threshold_min implies retrieval quality is
           maintained; drop below triggers compression_alert.
Kill test: Inject synthetic embeddings with known MI≈0 (independent noise);
           assert monitor does not invent data when lifecycle.db is missing.

Pure stdlib only (no numpy/scipy). Fail-open.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import sqlite3
import sys
import tempfile
import uuid
from datetime import datetime, timezone, UTC
from pathlib import Path

K_NN = 5
WINDOW = 20
ALERT_RATIO = 0.3
EULER_GAMMA = 0.5772156649015328606


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


def _cache() -> Path:
    return _hermes_root() / "cache"


def _lifecycle_db() -> Path:
    return _hermes_home() / "memory-facts" / "lifecycle.db"


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _atomic_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
            fh.write("\n")
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _chebyshev(a: list[float], b: list[float]) -> float:
    n = min(len(a), len(b))
    if n == 0:
        return 0.0
    m = 0.0
    for i in range(n):
        d = abs(a[i] - b[i])
        m = max(m, d)
    return m


def _digamma_int(n: int) -> float:
    """ψ(n) for integer n >= 1: -γ + H_{n-1}."""
    if n <= 0:
        return 0.0
    s = 0.0
    for k in range(1, n):
        s += 1.0 / k
    return -EULER_GAMMA + s


def estimate_mi(X: list[list[float]], Y: list[list[float]], k: int = K_NN) -> float | None:
    """Kraskov k-NN I(X;Y) with Chebyshev metric. None if insufficient data."""
    n = min(len(X), len(Y))
    if n < k + 2:
        return None
    z = [list(X[i]) + list(Y[i]) for i in range(n)]
    xa = [list(X[i]) for i in range(n)]
    ya = [list(Y[i]) for i in range(n)]

    eps_k = []
    for i in range(n):
        dists = [_chebyshev(z[i], z[j]) for j in range(n) if j != i]
        dists.sort()
        eps_k.append(dists[k - 1] if len(dists) >= k else (dists[-1] if dists else 0.0))

    nx = []
    ny = []
    for i in range(n):
        e = eps_k[i]
        # count neighbors strictly inside the open ball of radius e (Kraskov I)
        cx = sum(1 for j in range(n) if j != i and _chebyshev(xa[i], xa[j]) < e)
        cy = sum(1 for j in range(n) if j != i and _chebyshev(ya[i], ya[j]) < e)
        nx.append(cx)
        ny.append(cy)

    acc = 0.0
    for i in range(n):
        acc += _digamma_int(nx[i] + 1) + _digamma_int(ny[i] + 1)
    mi = _digamma_int(k) - (acc / n) + _digamma_int(n)
    return max(0.0, mi)


def _parse_vec(raw) -> list[float] | None:
    if raw is None:
        return None
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8", errors="replace")
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return None
    if not isinstance(raw, (list, tuple)) or not raw:
        return None
    try:
        return [float(x) for x in raw]
    except (TypeError, ValueError):
        return None


def _load_embeddings(db_path: Path, limit: int = 200) -> tuple[list[list[float]], list[list[float]], str]:
    """Load episodic/semantic vectors. Never invents synthetic production data."""
    if not db_path.exists():
        return [], [], "missing_db"
    episodic: list[list[float]] = []
    semantic: list[list[float]] = []
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=30)
        try:
            try:
                conn.execute("PRAGMA busy_timeout=30000")
                conn.execute("PRAGMA journal_mode=WAL")
            except sqlite3.Error:
                pass
            cur = conn.cursor()
            for tbl in ("episodic_embeddings", "memory_embeddings", "graphiti_nodes"):
                try:
                    cur.execute(f"SELECT embedding FROM {tbl} LIMIT ?", (limit,))
                    rows = cur.fetchall()
                except sqlite3.OperationalError:
                    continue
                vecs = []
                for r in rows:
                    v = _parse_vec(r[0] if r else None)
                    if v:
                        vecs.append(v)
                if not vecs:
                    continue
                if not episodic:
                    episodic = vecs
                elif not semantic:
                    semantic = vecs
                    break
        finally:
            conn.close()
    except sqlite3.Error:
        return [], [], "db_error"
    if not episodic or not semantic:
        return episodic, semantic, "insufficient_tables"
    n = min(len(episodic), len(semantic), limit)
    return episodic[:n], semantic[:n], "ok"


def run_monitor(db_path: Path | None = None, out_dir: Path | None = None) -> dict:
    cache = out_dir or _cache()
    db = db_path or _lifecycle_db()
    state_path = cache / "memory-bottleneck-state.json"
    alert_path = cache / "memory-bottleneck-alert.json"
    out_path = cache / "memory-bottleneck.json"

    epi, sem, reason = _load_embeddings(db)
    if reason != "ok":
        result = {
            "ts": _now(),
            "status": "insufficient_data",
            "reason": reason,
            "mi_episodic_semantic": None,
            "baseline_mi": None,
            "alert": False,
            "n_samples": min(len(epi), len(sem)),
        }
        _atomic_json(out_path, result)
        return result

    mi = estimate_mi(epi, sem)
    if mi is None:
        result = {
            "ts": _now(),
            "status": "insufficient_data",
            "reason": "n_lt_knn",
            "mi_episodic_semantic": None,
            "baseline_mi": None,
            "alert": False,
            "n_samples": min(len(epi), len(sem)),
        }
        _atomic_json(out_path, result)
        return result

    state = {"baseline_mi": None, "history": []}
    if state_path.exists():
        try:
            loaded = json.loads(state_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                state = loaded
        except (OSError, json.JSONDecodeError):
            pass

    history = list(state.get("history") or [])[-WINDOW:]
    history.append({"ts": _now(), "mi": round(mi, 4)})

    baseline = state.get("baseline_mi")
    if baseline is None and len(history) >= 5:
        baseline = sum(float(h.get("mi") or 0.0) for h in history[:5]) / 5.0

    alert = False
    if baseline and mi < ALERT_RATIO * float(baseline):
        alert = True

    new_state = {"baseline_mi": baseline, "history": history}
    _atomic_json(state_path, new_state)

    result = {
        "ts": _now(),
        "status": "alarm" if alert else "ok",
        "mi_episodic_semantic": round(mi, 4),
        "baseline_mi": round(float(baseline), 4) if baseline else None,
        "alert": alert,
        "n_samples": len(epi),
    }
    _atomic_json(out_path, result)
    if alert:
        _atomic_json(alert_path, result)
    elif alert_path.exists():
        try:
            alert_path.unlink()
        except OSError:
            pass
    return result


def _self_test() -> int:
    home = _hermes_home()
    old_home = os.environ.get("HERMES_HOME")
    old_prof = os.environ.get("HERMES_PROFILE")
    try:
        os.environ["HERMES_HOME"] = str(home / "profiles" / "fork")
        os.environ["HERMES_PROFILE"] = "fork"
        assert _hermes_home() == home, _hermes_home()
        os.environ["HERMES_HOME"] = str(home)
        assert _hermes_home() == home
        assert str(_cache()).endswith("/profiles/fork/cache"), _cache()
    finally:
        if old_home is None:
            os.environ.pop("HERMES_HOME", None)
        else:
            os.environ["HERMES_HOME"] = old_home
        if old_prof is None:
            os.environ.pop("HERMES_PROFILE", None)
        else:
            os.environ["HERMES_PROFILE"] = old_prof

    rng = random.Random(0)
    d = 8
    n = 40
    base = [[rng.gauss(0, 1) for _ in range(d)] for _ in range(n)]
    correlated_a = [[v + rng.gauss(0, 0.2) for v in row] for row in base]
    correlated_b = [[v + rng.gauss(0, 0.2) for v in row] for row in base]
    noise_a = [[rng.gauss(0, 1) for _ in range(d)] for _ in range(n)]
    noise_b = [[rng.gauss(0, 1) for _ in range(d)] for _ in range(n)]
    mi_corr = estimate_mi(correlated_a, correlated_b)
    mi_noise = estimate_mi(noise_a, noise_b)
    assert mi_corr is not None and mi_corr >= 0.0, mi_corr
    assert mi_noise is not None and mi_noise >= 0.0, mi_noise
    assert mi_corr >= mi_noise, (mi_corr, mi_noise)
    assert estimate_mi([[0.0]], [[1.0]]) is None

    td = Path(tempfile.mkdtemp(prefix="mbm-"))
    try:
        missing = run_monitor(db_path=td / "nope.db", out_dir=td)
        assert missing["status"] == "insufficient_data", missing
        out = td / "memory-bottleneck.json"
        assert out.is_file()
        payload = json.loads(out.read_text(encoding="utf-8"))
        assert payload["mi_episodic_semantic"] is None
        tmp_probe = td / ("memory-bottleneck_test_" + uuid.uuid4().hex + ".json")
        _atomic_json(tmp_probe, {"ok": True})
        assert json.loads(tmp_probe.read_text(encoding="utf-8"))["ok"] is True
    finally:
        import shutil

        shutil.rmtree(td, ignore_errors=True)

    print(json.dumps({
        "status": "ok",
        "self_test": True,
        "mi_corr": mi_corr,
        "mi_noise": mi_noise,
    }))
    return 0


def main(argv: list[str] | None = None) -> int:
    pa = argparse.ArgumentParser()
    pa.add_argument("--self-test", action="store_true")
    pa.add_argument("--run", action="store_true")
    pa.add_argument("--layer1", action="store_true", help="alias for --self-test")
    args = pa.parse_args(argv)
    if args.self_test or args.layer1:
        try:
            return _self_test()
        except Exception as exc:
            print(f"[memory-bottleneck-monitor] --self-test FAIL: {exc}")
            return 1
    try:
        result = run_monitor()
        print(json.dumps(result, default=str))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "error", "reason": str(exc)}))
        return 0


if __name__ == "__main__":
    sys.exit(main())
