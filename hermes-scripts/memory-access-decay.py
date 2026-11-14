#!/usr/bin/env python3
"""memory-access-decay.py — access-weighted retention decay.

Entries not accessed decay in weight over time; frequently accessed
entries get a boosted TTL. Matches the ai-memory M8 retention mix:

  weight = salience * exp(-lambda * age_days)
         + sigma * log1p(access_count) * exp(-mu * idle_days)

Default: compute + write cache JSON (no DB mutation).
  --apply   write retention_score (and valid_to boosts) back to lifecycle.db
  --self-test

Stdlib only. Fail-open (exit 0) on missing DB / malformed JSON.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sqlite3
import sys
from datetime import datetime, timedelta, timezone, UTC
from pathlib import Path

_raw_home = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
if _raw_home.parent.name == 'profiles':
    _hermes_base = _raw_home.parent.parent
    _hermes_root = _raw_home
    if not _hermes_profile:
        _hermes_profile = _raw_home.name
else:
    _hermes_base = _raw_home
    _hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile else _hermes_base

LAMBDA_AGE = 0.02
MU_IDLE = 0.08
SIGMA_ACCESS = 0.35
COLD_WEIGHT = 0.20
HOT_ACCESS = 3
TTL_BOOST_CAP_DAYS = 28.0
TTL_BOOST_UNIT_DAYS = 7.0


def _cache_dir() -> Path:
    override = os.environ.get("UE_CACHE_DIR", "").strip()
    p = Path(override) if override else (_hermes_root / "cache")
    try:
        p.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return p


def _atomic_write(path: Path, obj) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")
        os.replace(tmp, path)
    except Exception:
        pass


def _apply_state_path() -> Path:
    return _cache_dir() / "memory-access-decay-apply-state.json"


def _load_apply_state() -> dict:
    p = _apply_state_path()
    try:
        if not p.exists():
            return {}
        obj = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(obj, dict):
            return {}
        out = {}
        for k, v in obj.items():
            if k is None or v is None:
                continue
            out[str(k)] = str(v)
        return out
    except Exception:
        return {}


def _ttl_from_last_access(entry: dict, now: datetime):
    """Pin valid_to to last_accessed + boost, capped at last_accessed + CAP.

    Returns (new_valid_to, accessed_key) or (None, None) when there is nothing
    to write. Daily cron must not roll valid_to forward from *now*.
    """
    la = _parse_dt(entry.get("last_accessed") or entry.get("accessed_at"), now)
    if la is None:
        return None, None
    try:
        idle = (now - la).total_seconds() / 86400.0
    except Exception:
        return None, None
    if not math.isfinite(idle) or idle < 0.0 or idle > TTL_BOOST_CAP_DAYS:
        return None, None
    try:
        boost = float(entry.get("ttl_boost_days") or 0.0)
    except (TypeError, ValueError):
        boost = 0.0
    if not math.isfinite(boost) or boost <= 0.0:
        return None, None
    boost = max(0.0, min(TTL_BOOST_CAP_DAYS, boost))
    target = la + timedelta(days=boost)
    cap = la + timedelta(days=TTL_BOOST_CAP_DAYS)
    new_vt = min(target, cap)
    return new_vt, la.isoformat()


def _clip01(x) -> float:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(v):
        return 0.0
    return max(0.0, min(1.0, v))


def _parse_dt(raw, now: datetime):
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    s = s.replace("Z", "+00:00")
    dt = None
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(s, fmt)
                break
            except ValueError:
                dt = None
        if dt is None:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt


def _days_between(then, now: datetime, default: float) -> float:
    dt = _parse_dt(then, now)
    if dt is None:
        return float(default)
    try:
        delta = (now - dt).total_seconds() / 86400.0
    except Exception:
        return float(default)
    if not math.isfinite(delta):
        return float(default)
    return max(0.0, delta)


def access_weight(entry: dict, now=None) -> dict:
    """Return a scored copy of *entry*. Never raises."""
    now = now or datetime.now(UTC)
    out = dict(entry)
    try:
        access = int(entry.get("access_count") or 0)
    except (TypeError, ValueError):
        access = 0
    access = max(0, access)
    salience = _clip01(entry.get("salience", entry.get("retention_score", 0.5)))
    if salience == 0.0 and entry.get("retention_score") in (None, ""):
        salience = 0.5
    age_days = _days_between(entry.get("valid_from") or entry.get("inserted_at"), now, 30.0)
    idle_days = _days_between(entry.get("last_accessed"), now, 365.0 if access == 0 else 30.0)
    try:
        age_term = salience * math.exp(-LAMBDA_AGE * age_days)
        access_term = SIGMA_ACCESS * math.log1p(access) * math.exp(-MU_IDLE * idle_days)
        weight = _clip01(age_term + access_term)
        boost = TTL_BOOST_UNIT_DAYS * math.log1p(access) * math.exp(-MU_IDLE * idle_days)
        boost = max(0.0, min(TTL_BOOST_CAP_DAYS, boost))
    except Exception:
        weight, boost, age_term, access_term = 0.0, 0.0, 0.0, 0.0
    cold = weight < COLD_WEIGHT and access < HOT_ACCESS
    hot = access >= HOT_ACCESS and idle_days < 7.0
    out.update({
        "access_count": access,
        "age_days": round(age_days, 4),
        "idle_days": round(idle_days, 4),
        "salience": round(salience, 6),
        "age_term": round(age_term, 6),
        "access_term": round(access_term, 6),
        "weight": round(weight, 6),
        "ttl_boost_days": round(boost, 4),
        "cold": bool(cold),
        "hot": bool(hot),
    })
    return out


def _lifecycle_db() -> Path:
    override = os.environ.get("LIFECYCLE_DB", "").strip()
    if override:
        return Path(override)
    # Shared DB lives on the unwrapped base, never profiles/<name>/memory-facts.
    return _hermes_base / "memory-facts" / "lifecycle.db"


_WANTED_COLS = (
    "memory_id", "fact_text", "fact_type", "volatility_class",
    "valid_from", "valid_to", "access_count", "last_accessed",
    "retention_score", "memory_status", "inserted_at",
)


def _table_columns(con: sqlite3.Connection, table: str) -> set:
    try:
        rows = con.execute(f"PRAGMA table_info({table})").fetchall()
        # PRAGMA table_info: cid, name, type, notnull, dflt_value, pk
        return {r[1] for r in rows if r and r[1]}
    except Exception:
        return set()


def load_entries() -> list:
    entries = []
    db = _lifecycle_db()
    try:
        if db.exists() and db.stat().st_size > 0:
            uri = "file:" + str(db) + "?mode=ro"
            con = sqlite3.connect(uri, uri=True, timeout=2.0)
            try:
                con.row_factory = sqlite3.Row
                cols = _table_columns(con, "fact_lifecycle")
                if "memory_id" not in cols:
                    cols = set()
                select_cols = [c for c in _WANTED_COLS if c in cols]
                if select_cols:
                    rows = con.execute(
                        "SELECT " + ", ".join(select_cols) + " FROM fact_lifecycle"
                    ).fetchall()
                    for r in rows:
                        d = {k: r[k] for k in r.keys()}
                        d["entry_id"] = d.get("memory_id")
                        d["salience"] = d.get("retention_score")
                        d["source"] = "lifecycle"
                        entries.append(d)
            finally:
                con.close()
    except Exception:
        pass
    cache = _cache_dir()
    for name in ("ue-memory-gate-log.jsonl", "ue-blackbox-scores.jsonl"):
        p = cache / name
        try:
            if not p.exists():
                continue
            with open(p, "r", encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    s = line.strip()
                    if not s.startswith("{"):
                        continue
                    try:
                        obj = json.loads(s)
                    except json.JSONDecodeError:
                        continue
                    if not isinstance(obj, dict):
                        continue
                    eid = obj.get("entry_id") or obj.get("memory_id") or obj.get("id")
                    if not eid:
                        continue
                    # Cache JSONL ids are not lifecycle memory_ids — never apply them.
                    entries.append({
                        "entry_id": eid,
                        "access_count": obj.get("access_count", 0),
                        "last_accessed": obj.get("last_accessed") or obj.get("ts"),
                        "inserted_at": obj.get("inserted_at") or obj.get("ts"),
                        "retention_score": obj.get("retention_score") or obj.get("importance"),
                        "salience": obj.get("salience") or obj.get("importance"),
                        "source": "cache",
                    })
        except Exception:
            continue
    return entries


def compute(now=None) -> dict:
    now = now or datetime.now(UTC)
    try:
        raw = load_entries()
        scored = [access_weight(e, now=now) for e in raw]
        n = len(scored)
        cold = sum(1 for e in scored if e.get("cold"))
        hot = sum(1 for e in scored if e.get("hot"))
        mean_w = (sum(float(e["weight"]) for e in scored) / n) if n else 0.0
        rec = {
            "ok": True,
            "n": n,
            "n_cold": cold,
            "n_hot": hot,
            "mean_weight": round(mean_w, 6),
            "lambda_age": LAMBDA_AGE,
            "mu_idle": MU_IDLE,
            "sigma_access": SIGMA_ACCESS,
            "ts": now.isoformat(),
            "entries": scored,
        }
        _atomic_write(_cache_dir() / "memory-access-decay.json", rec)
        return rec
    except Exception as exc:
        return {"ok": False, "skipped": True, "reason": str(exc), "n": 0, "entries": []}


def apply_db(rec: dict, now=None) -> dict:
    now = now or datetime.now(UTC)
    db = _lifecycle_db()
    applied = 0
    skipped = 0
    try:
        if not db.exists():
            return {"applied": 0, "reason": "missing_db"}
        con = sqlite3.connect(str(db), timeout=5.0, isolation_level="IMMEDIATE")
        con.execute('PRAGMA journal_mode=WAL')
        try:
            cols = _table_columns(con, "fact_lifecycle")
            if "memory_id" not in cols:
                return {"applied": 0, "reason": "no_memory_id_column"}
            set_score = "retention_score" in cols
            set_updated = "updated_at" in cols
            can_valid_to = "valid_to" in cols
            if not set_score and not set_updated and not can_valid_to:
                return {"applied": 0, "reason": "no_writable_columns"}
            known = {
                r[0]
                for r in con.execute("SELECT memory_id FROM fact_lifecycle").fetchall()
                if r and r[0]
            }
            apply_state = _load_apply_state()
            state_dirty = False
            for e in rec.get("entries") or []:
                if e.get("source") != "lifecycle":
                    skipped += 1
                    continue
                mid = e.get("memory_id")
                if not mid or mid not in known:
                    skipped += 1
                    continue
                parts = []
                params = []
                if set_score:
                    parts.append("retention_score = ?")
                    params.append(_clip01(e.get("weight")))
                if can_valid_to:
                    new_vt, acc_key = _ttl_from_last_access(e, now)
                    if new_vt is not None and acc_key:
                        prev_key = apply_state.get(str(mid))
                        # accessed_at is the idempotency key: same access must
                        # not re-pin valid_to on the next daily cron.
                        if prev_key != acc_key:
                            current = _parse_dt(e.get("valid_to"), now)
                            if current is None or new_vt > current:
                                parts.append("valid_to = ?")
                                params.append(new_vt.isoformat())
                                apply_state[str(mid)] = acc_key
                                state_dirty = True
                if set_updated:
                    parts.append("updated_at = datetime('now')")
                if not parts:
                    skipped += 1
                    continue
                params.append(mid)
                cur = con.execute(
                    "UPDATE fact_lifecycle SET " + ", ".join(parts) + " WHERE memory_id = ?",
                    tuple(params),
                )
                if cur.rowcount and cur.rowcount > 0:
                    applied += 1
                else:
                    skipped += 1
            con.commit()
            if state_dirty:
                _atomic_write(_apply_state_path(), apply_state)
        finally:
            con.close()
    except Exception as ext:
        return {"applied": applied, "skipped": skipped, "fail_open": str(ext)}
    return {"applied": applied, "skipped": skipped}


def self_test() -> int:
    import tempfile
    now = datetime(2026, 10, 26, tzinfo=UTC)
    hot = access_weight({
        "entry_id": "hot",
        "access_count": 12,
        "last_accessed": "2026-10-25T00:00:00+00:00",
        "valid_from": "2026-09-01T00:00:00+00:00",
        "retention_score": 0.6,
    }, now=now)
    cold = access_weight({
        "entry_id": "cold",
        "access_count": 0,
        "last_accessed": None,
        "valid_from": "2025-01-01T00:00:00+00:00",
        "retention_score": 0.6,
    }, now=now)
    empty = access_weight({}, now=now)
    assert hot["weight"] > cold["weight"]
    assert hot["ttl_boost_days"] > cold["ttl_boost_days"]
    assert hot["hot"] is True
    assert cold["cold"] is True
    assert 0.0 <= empty["weight"] <= 1.0
    garbage = access_weight({
        "entry_id": "bad-ts",
        "access_count": 1,
        "last_accessed": "not-a-date",
        "valid_from": "???",
        "valid_to": None,
        "retention_score": 0.4,
    }, now=now)
    assert 0.0 <= garbage["weight"] <= 1.0
    td = Path(tempfile.mkdtemp(prefix="mad-"))
    old_db = os.environ.get("LIFECYCLE_DB")
    old_cache = os.environ.get("UE_CACHE_DIR")
    try:
        os.environ["UE_CACHE_DIR"] = str(td / "cache")
        os.environ["LIFECYCLE_DB"] = str(td / "missing.db")
        skip_apply = apply_db({"entries": [
            {"memory_id": "does-not-exist", "weight": 0.9, "source": "lifecycle"},
            {"entry_id": "cache-only", "weight": 0.9, "source": "cache"},
        ]}, now=now)
        assert skip_apply.get("applied", 0) == 0
        rec = compute(now=now)
        assert rec["n"] >= 0
        assert rec.get("ok") is True
        db = td / "lc.db"
        con = sqlite3.connect(str(db))
        con.execute('PRAGMA journal_mode=WAL')
        con.execute(
            "CREATE TABLE fact_lifecycle "
            "(memory_id TEXT PRIMARY KEY, retention_score REAL, valid_to TEXT, updated_at TEXT)"
        )
        con.execute(
            "INSERT INTO fact_lifecycle VALUES ('hot1', 0.1, '2026-10-01T00:00:00+00:00', NULL)"
        )
        con.commit()
        con.close()
        os.environ["LIFECYCLE_DB"] = str(db)
        first = apply_db({"entries": [{
            "memory_id": "hot1", "weight": 0.9, "ttl_boost_days": 7,
            "valid_to": "2026-10-01T00:00:00+00:00", "source": "lifecycle",
        }]}, now=now)
        assert first.get("applied") == 1
        con = sqlite3.connect(str(db))
        con.execute('PRAGMA journal_mode=WAL')
        vt1 = con.execute("SELECT valid_to FROM fact_lifecycle WHERE memory_id='hot1'").fetchone()[0]
        con.close()
        second = apply_db({"entries": [{
            "memory_id": "hot1", "weight": 0.9, "ttl_boost_days": 7,
            "valid_to": vt1, "source": "lifecycle",
        }]}, now=now)
        assert second.get("applied") == 1
        con = sqlite3.connect(str(db))
        con.execute('PRAGMA journal_mode=WAL')
        vt2 = con.execute("SELECT valid_to FROM fact_lifecycle WHERE memory_id='hot1'").fetchone()[0]
        con.close()
        assert vt1 == vt2
        # Pin from last_accessed, not from now. A later now must not roll valid_to.
        later = now + timedelta(days=1)
        pin = apply_db({"entries": [{
            "memory_id": "hot1", "weight": 0.9, "ttl_boost_days": 7,
            "last_accessed": "2026-10-25T00:00:00+00:00",
            "valid_to": "2026-10-01T00:00:00+00:00", "source": "lifecycle",
        }]}, now=now)
        assert pin.get("applied") == 1
        con = sqlite3.connect(str(db))
        con.execute('PRAGMA journal_mode=WAL')
        vt_pin = con.execute("SELECT valid_to FROM fact_lifecycle WHERE memory_id='hot1'").fetchone()[0]
        con.close()
        expected = datetime(2026, 11, 1, tzinfo=UTC)
        assert _parse_dt(vt_pin, now) == expected
        rerun = apply_db({"entries": [{
            "memory_id": "hot1", "weight": 0.9, "ttl_boost_days": 7,
            "last_accessed": "2026-10-25T00:00:00+00:00",
            "valid_to": vt_pin, "source": "lifecycle",
        }]}, now=later)
        assert rerun.get("applied") == 1
        con = sqlite3.connect(str(db))
        con.execute('PRAGMA journal_mode=WAL')
        vt_rerun = con.execute("SELECT valid_to FROM fact_lifecycle WHERE memory_id='hot1'").fetchone()[0]
        con.close()
        assert vt_pin == vt_rerun
        # New access may raise valid_to once; still not a rolling now+28d floor.
        bumped = apply_db({"entries": [{
            "memory_id": "hot1", "weight": 0.9, "ttl_boost_days": 7,
            "last_accessed": "2026-10-26T00:00:00+00:00",
            "valid_to": vt_rerun, "source": "lifecycle",
        }]}, now=later)
        assert bumped.get("applied") == 1
        con = sqlite3.connect(str(db))
        con.execute('PRAGMA journal_mode=WAL')
        vt_bump = con.execute("SELECT valid_to FROM fact_lifecycle WHERE memory_id='hot1'").fetchone()[0]
        con.close()
        parsed_bump = _parse_dt(vt_bump, now)
        assert parsed_bump == datetime(2026, 11, 2, tzinfo=UTC)
        floor = later + timedelta(days=TTL_BOOST_CAP_DAYS)
        assert parsed_bump is not None and parsed_bump < floor
    finally:
        if old_db is None:
            os.environ.pop("LIFECYCLE_DB", None)
        else:
            os.environ["LIFECYCLE_DB"] = old_db
        if old_cache is None:
            os.environ.pop("UE_CACHE_DIR", None)
        else:
            os.environ["UE_CACHE_DIR"] = old_cache
    print("PASS memory-access-decay self-test")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--apply", action="store_true", help="write scores back to lifecycle.db")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    try:
        rec = compute()
        if args.apply:
            rec["apply"] = apply_db(rec)
        slim = {k: rec[k] for k in rec if k != "entries"}
        slim["n_entries"] = len(rec.get("entries") or [])
        print(json.dumps(slim, indent=2, default=str))
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "skipped": True, "reason": str(exc)}))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
