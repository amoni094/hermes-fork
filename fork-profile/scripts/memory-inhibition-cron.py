#!/usr/bin/env python3
"""Retrieval-induced forgetting TTL adjuster (Anderson, Bjork & Bjork 1994).

Strongly practised facts in a domain inhibit weakly practised competitors:
extend TTL on strong traces, shrink TTL on neglected competitors.

No domain column in fact_lifecycle — group by fact_type (else 'default').
No ttl column — remaining life is encoded in valid_to.

Hard core: within-domain relative access (strong > 2*mean, weak < 0.5*mean
and idle > 45d). Belt: +/- 30d / 15d caps at 365d / 7d remaining.
TTL writes are idempotent: only move valid_to if the new target is strictly
later (strong) or strictly earlier (weak).
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone, UTC
from pathlib import Path

_hermes_base = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_hermes_profile = os.environ.get("HERMES_PROFILE", "")
_hermes_root = (
    (_hermes_base / "profiles" / _hermes_profile)
    if _hermes_profile and "profiles" not in str(_hermes_base)
    else _hermes_base
)

STRONG_TTL_DAYS = 30
WEAK_TTL_DAYS = 15
TTL_MAX_DAYS = 365
TTL_MIN_DAYS = 7
WEAK_IDLE_DAYS = 45


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _parse_dt(raw, now: datetime) -> datetime | None:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _lifecycle_db() -> Path:
    override = os.environ.get("LIFECYCLE_DB", "").strip()
    if override:
        return Path(override)
    # Prefer the profile DB the task named; fall back to shared base DB.
    profile_db = _hermes_root / "memory-facts" / "lifecycle.db"
    base_db = _hermes_base / "memory-facts" / "lifecycle.db"
    if profile_db.exists():
        return profile_db
    return base_db


def _connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path), timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    rows = conn.execute("PRAGMA table_info(" + table + ")").fetchall()
    return {str(r[1]) for r in rows}


def _pick_table(conn: sqlite3.Connection) -> str | None:
    names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if "fact_lifecycle" in names:
        return "fact_lifecycle"
    for name in sorted(names):
        if name.startswith("sqlite_"):
            continue
        cols = _table_columns(conn, name)
        if "access_count" in cols:
            return name
    return None


def run(now: datetime | None = None, dry_run: bool = False) -> dict:
    now = now or _utcnow()
    db_path = _lifecycle_db()
    summary = {
        "db": str(db_path),
        "table": None,
        "n_facts": 0,
        "domains": 0,
        "extended": 0,
        "reduced": 0,
        "skipped": 0,
        "dry_run": dry_run,
        "status": "ok",
    }
    if not db_path.exists():
        summary["status"] = "insufficient_data"
        summary["reason"] = "missing_db"
        return summary
    conn = _connect(db_path)
    try:
        table = _pick_table(conn)
        if not table:
            summary["status"] = "insufficient_data"
            summary["reason"] = "no_fact_table"
            return summary
        summary["table"] = table
        cols = _table_columns(conn, table)
        domain_col = "domain" if "domain" in cols else ("fact_type" if "fact_type" in cols else None)
        ttl_col = "valid_to" if "valid_to" in cols else ("decay_at" if "decay_at" in cols else None)
        if "access_count" not in cols or "memory_id" not in cols:
            summary["status"] = "insufficient_data"
            summary["reason"] = "missing_columns"
            return summary
        rows = conn.execute("SELECT * FROM " + table).fetchall()
        summary["n_facts"] = len(rows)
        if not rows:
            summary["status"] = "insufficient_data"
            summary["reason"] = "empty_table"
            return summary
        has_iw = "inhibition_weight" in cols
        groups: dict[str, list] = defaultdict(list)
        for row in rows:
            rec = dict(row)
            domain = "default"
            if domain_col:
                raw = rec.get(domain_col)
                domain = str(raw).strip() if raw not in (None, "") else "default"
            groups[domain].append(rec)
        summary["domains"] = len(groups)
        updates: list[tuple[str, str]] = []
        iw_updates: list[tuple[float, str]] = []
        summary["inhibited"] = 0
        summary["cleared_inhibition"] = 0
        for _domain, facts in groups.items():
            accesses = []
            for rec in facts:
                try:
                    accesses.append(int(rec.get("access_count") or 0))
                except (TypeError, ValueError):
                    accesses.append(0)
            mean_access = sum(accesses) / max(1, len(accesses))
            for rec, access in zip(facts, accesses):
                last = _parse_dt(rec.get("last_accessed"), now)
                idle_days = (now - last).days if last is not None else WEAK_IDLE_DAYS + 1
                current_vt = _parse_dt(rec.get(ttl_col), now) if ttl_col else None
                memory_id = rec.get("memory_id")
                if not memory_id:
                    summary["skipped"] += 1
                    continue
                target = None
                kind = None
                iw = None
                if access > 2.0 * mean_access:
                    base = current_vt if current_vt is not None else now
                    candidate = base + timedelta(days=STRONG_TTL_DAYS)
                    cap = now + timedelta(days=TTL_MAX_DAYS)
                    target = min(candidate, cap)
                    kind = "extend"
                    iw = 0.0  # strong traces are not inhibited
                    if current_vt is not None and target <= current_vt:
                        target = None  # TTL already at/beyond cap; still write iw
                elif access < 0.5 * mean_access and idle_days > WEAK_IDLE_DAYS:
                    floor = now + timedelta(days=TTL_MIN_DAYS)
                    if current_vt is None:
                        target = floor
                    else:
                        target = max(current_vt - timedelta(days=WEAK_TTL_DAYS), floor)
                    kind = "reduce"
                    # 0-1 scale expected by unified-recall: score / (1 + iw)
                    denom = max(mean_access, 1e-9)
                    iw = min(1.0, max(0.0, 1.0 - (access / denom)))
                    if current_vt is not None and target >= current_vt:
                        target = None
                else:
                    summary["skipped"] += 1
                    continue
                if has_iw and iw is not None:
                    iw_updates.append((float(iw), str(memory_id)))
                    if iw > 0.0:
                        summary["inhibited"] += 1
                    else:
                        summary["cleared_inhibition"] += 1
                if target is None:
                    if kind == "extend" or kind == "reduce":
                        # TTL no-op; inhibition write still counts
                        pass
                    continue
                iso = target.isoformat()
                if kind == "extend":
                    summary["extended"] += 1
                else:
                    summary["reduced"] += 1
                updates.append((iso, str(memory_id)))
        if updates and ttl_col and not dry_run:
            conn.executemany(
                "UPDATE " + table + " SET " + ttl_col + " = ?, updated_at = datetime('now') WHERE memory_id = ?",
                updates,
            )
            conn.commit()
        elif updates and not ttl_col:
            summary["status"] = "ok"
            summary["reason"] = "no_ttl_column"
        if iw_updates and has_iw and not dry_run:
            conn.executemany(
                "UPDATE " + table + " SET inhibition_weight = ?, updated_at = datetime('now') WHERE memory_id = ?",
                iw_updates,
            )
            conn.commit()
        return summary
    finally:
        conn.close()


def _self_test() -> int:
    import tempfile
    import uuid as _uuid

    tmp = Path(tempfile.mkdtemp(prefix="mem-inhib-")) / ("lc_" + _uuid.uuid4().hex + ".db")
    conn = sqlite3.connect(str(tmp), timeout=30)
    conn.execute('PRAGMA journal_mode=WAL')
    try:
        conn.execute(
            "CREATE TABLE fact_lifecycle ("
            "memory_id TEXT PRIMARY KEY, fact_type TEXT, access_count INTEGER, "
            "last_accessed TEXT, valid_to TEXT, updated_at TEXT, inhibition_weight REAL DEFAULT 0.0)"
        )
        now = datetime(2026, 10, 29, tzinfo=UTC)
        old = (now - timedelta(days=60)).isoformat()
        vt = (now + timedelta(days=40)).isoformat()
        conn.executemany(
            "INSERT INTO fact_lifecycle VALUES (?,?,?,?,?,?,?)",
            [
                ("hot", "alpha", 10, now.isoformat(), vt, now.isoformat(), 0.0),
                ("cold", "alpha", 0, old, vt, now.isoformat(), 0.0),
                ("mid", "alpha", 4, now.isoformat(), vt, now.isoformat(), 0.0),
            ],
        )
        conn.commit()
    finally:
        conn.close()
    os.environ["LIFECYCLE_DB"] = str(tmp)
    try:
        summary = run(now=now, dry_run=False)
        assert summary["extended"] == 1, summary
        assert summary["reduced"] == 1, summary
        conn = sqlite3.connect(str(tmp), timeout=30)
        conn.execute('PRAGMA journal_mode=WAL')
        try:
            rows = {r[0]: r[1] for r in conn.execute("SELECT memory_id, valid_to FROM fact_lifecycle")}
            iws = {r[0]: r[1] for r in conn.execute("SELECT memory_id, inhibition_weight FROM fact_lifecycle")}
        finally:
            conn.close()
        hot_vt = datetime.fromisoformat(rows["hot"])
        cold_vt = datetime.fromisoformat(rows["cold"])
        assert hot_vt > datetime.fromisoformat(vt)
        assert cold_vt < datetime.fromisoformat(vt)
        assert iws["hot"] == 0.0, iws
        assert iws["cold"] > 0.0, iws
        assert 0.0 <= iws["cold"] <= 1.0, iws
        print(json.dumps({"ok": True, "summary": summary}))
        return 0
    finally:
        try:
            tmp.unlink()
        except OSError:
            pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="RIF memory-inhibition TTL adjuster")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        return _self_test()
    summary = run(dry_run=args.dry_run)
    print("memory-inhibition SUMMARY " + json.dumps(summary, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
