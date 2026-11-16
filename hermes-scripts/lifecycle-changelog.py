#!/usr/bin/env python3
"""lifecycle-changelog.py — cell changelog / audit log for lifecycle.db facts.

Dolt-inspired commit + cell-level changelog without Dolt itself.
Adds two tables (IF NOT EXISTS) and never alters existing tables:

  fact_commits(commit_id TEXT PK, parent_id TEXT, author TEXT, ts TEXT, message TEXT)
  fact_changelog(id INTEGER PK, commit_id TEXT, table_name TEXT,
                 op TEXT CHECK(op IN ('I','U','D')), row_pk TEXT, field TEXT,
                 from_val TEXT, to_val TEXT)

Time-travel replays I/U/D ops up to as_of_commit. Blame returns the last
commit that changed a field. Connections use WAL + busy_timeout.

Usage:
  python3 lifecycle-changelog.py init --db PATH
  python3 lifecycle-changelog.py history --db PATH --table TABLE --pk VAL
  python3 lifecycle-changelog.py blame --db PATH --table TABLE --pk VAL --field FIELD
  python3 lifecycle-changelog.py commit --db PATH --author A --message M
  python3 lifecycle-changelog.py --self-test
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import tempfile
import uuid
from datetime import datetime, timezone, UTC
from pathlib import Path

COMMITS_DDL = """
CREATE TABLE IF NOT EXISTS fact_commits (
    commit_id TEXT PRIMARY KEY,
    parent_id TEXT,
    author TEXT,
    ts TEXT,
    message TEXT
)
"""

CHANGELOG_DDL = """
CREATE TABLE IF NOT EXISTS fact_changelog (
    id INTEGER PRIMARY KEY,
    commit_id TEXT,
    table_name TEXT,
    op TEXT CHECK(op IN ('I','U','D')),
    row_pk TEXT,
    field TEXT,
    from_val TEXT,
    to_val TEXT
)
"""


def _profile_root() -> Path:
    base = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
    profile = os.environ.get("HERMES_PROFILE", "")
    if profile and "profiles" not in str(base):
        return base / "profiles" / profile
    return base


def _hermes_base() -> Path:
    """Return ~/.hermes (the base, not the profile root)."""
    h = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
    # If HERMES_HOME was set to profiles/fork, unwrap to the base
    if h.parent.name == "profiles":
        h = h.parent.parent
    return h


def default_db_path() -> Path:
    """Canonical shared lifecycle.db — always under the base, not the profile."""
    return _hermes_base() / "memory-facts" / "lifecycle.db"


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _val_text(v):
    if v is None:
        return None
    if isinstance(v, str):
        return v
    return json.dumps(v, default=str)


def _val_load(s):
    if s is None:
        return None
    if not isinstance(s, str):
        return s
    t = s.strip()
    if not t:
        return s
    if t[0] in "{[\"0123456789-" or t in ("true", "false", "null"):
        try:
            return json.loads(t)
        except json.JSONDecodeError:
            return s
    return s


def connect(db, readonly: bool = False) -> sqlite3.Connection:
    if isinstance(db, sqlite3.Connection):
        if not readonly:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA busy_timeout=5000")
        return db
    path = Path(db)
    path.parent.mkdir(parents=True, exist_ok=True)
    if readonly:
        uri = path.as_uri() + "?mode=ro"
        conn = sqlite3.connect(uri, uri=True, timeout=30)
    else:
        conn = sqlite3.connect(str(path), timeout=30)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
    conn.row_factory = sqlite3.Row
    return conn


def _owns_conn(db) -> bool:
    return not isinstance(db, sqlite3.Connection)


def existing_tables(conn: sqlite3.Connection) -> list:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    return [r[0] for r in rows]


def init_schema(db) -> dict:
    """Create fact_commits / fact_changelog if missing. Does not alter other tables."""
    owns = _owns_conn(db)
    conn = connect(db)
    try:
        before = existing_tables(conn)
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(COMMITS_DDL)
        conn.execute(CHANGELOG_DDL)
        conn.commit()
        after = existing_tables(conn)
        added = [t for t in after if t not in before]
        return {
            "existing_tables": before,
            "tables_now": after,
            "added": added,
            "ok": True,
        }
    except Exception:
        try:
            conn.rollback()
        except sqlite3.Error:
            pass
        raise
    finally:
        if owns:
            conn.close()


def new_commit(db, author, message, parent_id=None) -> str:
    """Insert a commit row; return commit_id (uuid4)."""
    owns = _owns_conn(db)
    conn = connect(db)
    try:
        commit_id = str(uuid.uuid4())
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            "INSERT INTO fact_commits(commit_id, parent_id, author, ts, message) "
            "VALUES (?, ?, ?, ?, ?)",
            (commit_id, parent_id, author, _now(), message),
        )
        conn.commit()
        return commit_id
    except Exception:
        try:
            conn.rollback()
        except sqlite3.Error:
            pass
        raise
    finally:
        if owns:
            conn.close()


def log_change(db, commit_id, table_name, op, row_pk, field=None, from_val=None, to_val=None) -> int:
    """Insert a changelog row. Returns row id."""
    if op not in ("I", "U", "D"):
        raise ValueError("op must be I, U, or D")
    owns = _owns_conn(db)
    conn = connect(db)
    try:
        conn.execute("BEGIN IMMEDIATE")
        cur = conn.execute(
            "INSERT INTO fact_changelog("
            "commit_id, table_name, op, row_pk, field, from_val, to_val) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                commit_id,
                table_name,
                op,
                str(row_pk) if row_pk is not None else None,
                field,
                _val_text(from_val),
                _val_text(to_val),
            ),
        )
        conn.commit()
        rid = cur.lastrowid
        return int(rid) if rid is not None else 0
    except Exception:
        try:
            conn.rollback()
        except sqlite3.Error:
            pass
        raise
    finally:
        if owns:
            conn.close()


def _row_to_dict(row) -> dict:
    return {k: row[k] for k in row.keys()}


def get_history(db, table_name, row_pk) -> list:
    """Changes for (table, pk) ordered by commit ts then changelog id."""
    owns = _owns_conn(db)
    conn = connect(db, readonly=True)
    try:
        rows = conn.execute(
            "SELECT ch.id, ch.commit_id, ch.table_name, ch.op, ch.row_pk, "
            "ch.field, ch.from_val, ch.to_val, "
            "c.parent_id, c.author, c.ts, c.message "
            "FROM fact_changelog ch "
            "JOIN fact_commits c ON c.commit_id = ch.commit_id "
            "WHERE ch.table_name = ? AND ch.row_pk = ? "
            "ORDER BY c.ts ASC, ch.id ASC",
            (table_name, str(row_pk)),
        ).fetchall()
        out = []
        for r in rows:
            rec = _row_to_dict(r)
            rec["from_val"] = _val_load(rec.get("from_val"))
            rec["to_val"] = _val_load(rec.get("to_val"))
            out.append(rec)
        return out
    finally:
        if owns:
            conn.close()


def _visible_commit_ids(conn: sqlite3.Connection, as_of_commit: str) -> set:
    row = conn.execute(
        "SELECT commit_id, parent_id, ts FROM fact_commits WHERE commit_id = ?",
        (as_of_commit,),
    ).fetchone()
    if not row:
        return set()
    chain = []
    seen = set()
    cur = as_of_commit
    while cur and cur not in seen:
        seen.add(cur)
        chain.append(cur)
        prow = conn.execute(
            "SELECT parent_id FROM fact_commits WHERE commit_id = ?", (cur,)
        ).fetchone()
        if not prow or not prow[0]:
            break
        cur = prow[0]
    if len(chain) > 1:
        return set(chain)
    ts = row["ts"] if isinstance(row, sqlite3.Row) else row[2]
    return {
        r[0]
        for r in conn.execute(
            "SELECT commit_id FROM fact_commits WHERE ts <= ?", (ts,)
        )
    }


def time_travel(db, table_name, row_pk, as_of_commit):
    """Replay changelog for (table, pk) through as_of_commit. None if deleted."""
    owns = _owns_conn(db)
    conn = connect(db, readonly=True)
    try:
        visible = _visible_commit_ids(conn, as_of_commit)
        if not visible:
            return None
        rows = conn.execute(
            "SELECT ch.id, ch.commit_id, ch.op, ch.field, ch.from_val, ch.to_val, c.ts "
            "FROM fact_changelog ch "
            "JOIN fact_commits c ON c.commit_id = ch.commit_id "
            "WHERE ch.table_name = ? AND ch.row_pk = ? "
            "ORDER BY c.ts ASC, ch.id ASC",
            (table_name, str(row_pk)),
        ).fetchall()
        state = None
        saw = False
        for r in rows:
            cid = r["commit_id"] if isinstance(r, sqlite3.Row) else r[1]
            if cid not in visible:
                continue
            saw = True
            op = r["op"]
            field = r["field"]
            to_val = _val_load(r["to_val"])
            if op == "D" and not field:
                state = None
                continue
            if state is None:
                state = {}
            if op == "I" and not field:
                if isinstance(to_val, dict):
                    state = dict(to_val)
                else:
                    state["_row"] = to_val
                continue
            if op == "D" and field:
                state.pop(field, None)
                continue
            if field:
                state[field] = to_val
            else:
                if isinstance(to_val, dict):
                    state.update(to_val)
                else:
                    state["_row"] = to_val
        if not saw:
            return {}
        return state
    finally:
        if owns:
            conn.close()


def blame(db, table_name, row_pk, field):
    """Last commit that changed `field` on this row. None if never changed."""
    owns = _owns_conn(db)
    conn = connect(db, readonly=True)
    try:
        row = conn.execute(
            "SELECT ch.id, ch.commit_id, ch.op, ch.field, ch.from_val, ch.to_val, "
            "c.parent_id, c.author, c.ts, c.message "
            "FROM fact_changelog ch "
            "JOIN fact_commits c ON c.commit_id = ch.commit_id "
            "WHERE ch.table_name = ? AND ch.row_pk = ? AND ch.field = ? "
            "ORDER BY c.ts DESC, ch.id DESC LIMIT 1",
            (table_name, str(row_pk), field),
        ).fetchone()
        if not row:
            return None
        rec = _row_to_dict(row)
        rec["from_val"] = _val_load(rec.get("from_val"))
        rec["to_val"] = _val_load(rec.get("to_val"))
        return rec
    finally:
        if owns:
            conn.close()


def cmd_init(args) -> int:
    rec = init_schema(args.db)
    rec["db"] = str(args.db)
    print(json.dumps(rec, indent=2, default=str))
    return 0


def cmd_history(args) -> int:
    rec = get_history(args.db, args.table, args.pk)
    print(json.dumps(rec, indent=2, default=str))
    return 0


def cmd_blame(args) -> int:
    rec = blame(args.db, args.table, args.pk, args.field)
    print(json.dumps(rec, indent=2, default=str))
    return 0


def cmd_commit(args) -> int:
    cid = new_commit(args.db, args.author, args.message, parent_id=args.parent_id)
    print(cid)
    return 0


def self_test() -> int:
    td = tempfile.TemporaryDirectory(prefix="lc-changelog-")
    db = Path(td.name) / f"lc_{uuid.uuid4().hex}.db"
    try:
        rec = init_schema(db)
        assert rec["ok"] is True
        rec2 = init_schema(db)
        assert rec2["ok"] is True
        assert "fact_commits" in rec2["tables_now"]
        assert "fact_changelog" in rec2["tables_now"]

        cid1 = new_commit(db, "tester", "insert fact")
        assert cid1
        log_change(db, cid1, "fact_lifecycle", "I", "m1", field="fact_text", to_val="hello")
        log_change(db, cid1, "fact_lifecycle", "I", "m1", field="memory_status", to_val="active")

        cid2 = new_commit(db, "tester", "update fact", parent_id=cid1)
        log_change(
            db, cid2, "fact_lifecycle", "U", "m1",
            field="fact_text", from_val="hello", to_val="world",
        )

        hist = get_history(db, "fact_lifecycle", "m1")
        assert len(hist) == 3
        assert hist[0]["op"] == "I" and hist[0]["to_val"] == "hello"
        assert hist[-1]["op"] == "U" and hist[-1]["to_val"] == "world"
        assert hist[0]["ts"] <= hist[-1]["ts"]

        state1 = time_travel(db, "fact_lifecycle", "m1", cid1)
        assert isinstance(state1, dict)
        assert state1["fact_text"] == "hello"
        assert state1["memory_status"] == "active"

        state2 = time_travel(db, "fact_lifecycle", "m1", cid2)
        assert isinstance(state2, dict)
        assert state2["fact_text"] == "world"
        assert state2["memory_status"] == "active"

        b = blame(db, "fact_lifecycle", "m1", "fact_text")
        assert b is not None
        assert b["commit_id"] == cid2
        assert b["to_val"] == "world"

        b_status = blame(db, "fact_lifecycle", "m1", "memory_status")
        assert b_status is not None
        assert b_status["commit_id"] == cid1

        cid3 = new_commit(db, "tester", "delete fact", parent_id=cid2)
        log_change(db, cid3, "fact_lifecycle", "D", "m1")
        state3 = time_travel(db, "fact_lifecycle", "m1", cid3)
        assert state3 is None

        assert get_history(db, "fact_lifecycle", "missing") == []
        assert blame(db, "fact_lifecycle", "m1", "no_such_field") is None
        assert time_travel(db, "fact_lifecycle", "nope", cid1) == {}

        # empty-string / malformed-op guards
        try:
            log_change(db, cid1, "fact_lifecycle", "X", "m1")
            raise AssertionError("bad op should raise")
        except ValueError:
            pass

        # WAL pragmas
        conn = connect(db)
        try:
            mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
            assert str(mode).lower() == "wal"
        finally:
            conn.close()

        print("PASS lifecycle-changelog self-test")
        return 0
    finally:
        td.cleanup()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--self-test", action="store_true")
    sub = ap.add_subparsers(dest="cmd")

    p_init = sub.add_parser("init", help="create fact_commits + fact_changelog")
    p_init.add_argument("--db", required=True)

    p_hist = sub.add_parser("history", help="list cell changes for a row")
    p_hist.add_argument("--db", required=True)
    p_hist.add_argument("--table", required=True)
    p_hist.add_argument("--pk", required=True)

    p_blame = sub.add_parser("blame", help="last commit that changed a field")
    p_blame.add_argument("--db", required=True)
    p_blame.add_argument("--table", required=True)
    p_blame.add_argument("--pk", required=True)
    p_blame.add_argument("--field", required=True)

    p_commit = sub.add_parser("commit", help="create an empty commit, print id")
    p_commit.add_argument("--db", required=True)
    p_commit.add_argument("--author", required=True)
    p_commit.add_argument("--message", required=True)
    p_commit.add_argument("--parent-id", default=None)

    args = ap.parse_args()
    if args.self_test:
        return self_test()
    if args.cmd == "init":
        return cmd_init(args)
    if args.cmd == "history":
        return cmd_history(args)
    if args.cmd == "blame":
        return cmd_blame(args)
    if args.cmd == "commit":
        return cmd_commit(args)
    ap.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
