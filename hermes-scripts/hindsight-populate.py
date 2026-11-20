#!/usr/bin/env python3
"""hindsight-populate.py — incremental turn-behavior.jsonl → hindsight_events.

Reads the profile-aware turn-behavior JSONL and inserts tool_call events
into ~/.hermes/hindsight.db. Incremental via byte+line offset in
cache/hindsight-populate-state.json. WAL, 500-row batches, fail-open.

Usage:
  HERMES_HOME=~/.hermes HERMES_PROFILE=fork python3 hindsight-populate.py
  python3 hindsight-populate.py --self-test
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import sqlite3
import sys
import tempfile
import time
import traceback
from datetime import UTC, datetime
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', 'fork')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base

BATCH_SIZE = 500
BUSY_TIMEOUT_MS = 8000
SCHEMA = """
CREATE TABLE IF NOT EXISTS hindsight_events (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id   TEXT,
    turn_idx     INTEGER,
    event_type   TEXT NOT NULL,
    payload      TEXT DEFAULT '{}',
    quality      REAL DEFAULT NULL,
    created_at   REAL DEFAULT (unixepoch('now', 'subsec'))
)
"""
META_DDL = """
CREATE TABLE IF NOT EXISTS hindsight_populate_meta (
    key TEXT PRIMARY KEY,
    value TEXT
)
"""


def _true_base(p: Path) -> Path:
    if p.name != '.hermes' and p.parent.name == 'profiles':
        return p.parent.parent
    return p


def cache_dir() -> Path:
    d = _hermes_root / 'cache'
    d.mkdir(parents=True, exist_ok=True)
    return d


def jsonl_path() -> Path:
    return cache_dir() / 'turn-behavior.jsonl'


def state_path() -> Path:
    return cache_dir() / 'hindsight-populate-state.json'


def report_path() -> Path:
    return cache_dir() / 'hindsight-populate-report.json'


def hindsight_db_path() -> Path:
    base = _true_base(_hermes_base)
    for cand in (
        _hermes_root / 'hindsight.db',
        base / 'hindsight.db',
        Path.home() / '.hermes' / 'hindsight.db',
    ):
        if cand.is_file():
            return cand
    dest = base / 'hindsight.db'
    dest.parent.mkdir(parents=True, exist_ok=True)
    return dest


def _atomic_write_json(dest: Path, data: dict) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + '.tmp')
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    os.replace(tmp, dest)


def _log(msg: str) -> None:
    print(f'[hindsight-populate] {msg}', file=sys.stderr)


def load_state() -> dict:
    p = state_path()
    default = {'byte_offset': 0, 'line_offset': 0, 'last_ts': None}
    if not p.is_file():
        return default
    try:
        raw = json.loads(p.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as exc:
        _log(f'state unreadable, starting at 0: {exc}')
        return default
    if not isinstance(raw, dict):
        return default
    try:
        byte_offset = int(raw.get('byte_offset', 0) or 0)
        line_offset = int(raw.get('line_offset', 0) or 0)
    except (TypeError, ValueError):
        byte_offset, line_offset = 0, 0
    byte_offset = max(byte_offset, 0)
    line_offset = max(line_offset, 0)
    return {
        'byte_offset': byte_offset,
        'line_offset': line_offset,
        'last_ts': raw.get('last_ts'),
    }


def save_state(state: dict) -> None:
    try:
        _atomic_write_json(state_path(), state)
    except OSError as exc:
        _log(f'failed to persist state (fail-open): {exc}')


def parse_ts(ts) -> float:
    if ts is None:
        return time.time()
    if isinstance(ts, (int, float)):
        return float(ts)
    s = str(ts).strip()
    if not s:
        return time.time()
    if s.endswith('Z'):
        s = s[:-1] + '+00:00'
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        try:
            return float(s)
        except ValueError:
            return time.time()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.timestamp()


def turn_idx_from_id(turn_id, sequential: int) -> int:
    s = str(turn_id or '')
    suffix = s[-8:] if len(s) >= 8 else s
    if len(suffix) == 8:
        try:
            int(suffix, 16)
        except ValueError:
            return sequential % 10000
        if all(c in '0123456789abcdefABCDEF' for c in suffix):
            return int(suffix, 16) % 10000
    return sequential % 10000


def payload_json(row: dict) -> str:
    blob = {
        'tool_name': row.get('tool_name'),
        'success': bool(row.get('success')),
        'token_estimate': row.get('token_estimate'),
        'skill_entropy': row.get('skill_entropy'),
    }
    try:
        return json.dumps(blob, ensure_ascii=False, default=str)
    except (TypeError, ValueError, UnicodeError):
        try:
            return json.dumps(blob, ensure_ascii=True, default=str)
        except Exception:
            return '{}'


def row_to_tuple(row: dict, sequential: int) -> tuple:
    success = bool(row.get('success'))
    return (
        str(row.get('session_id') or ''),
        int(turn_idx_from_id(row.get('turn_id'), sequential)),
        'tool_call',
        payload_json(row),
        1.0 if success else 0.0,
        float(parse_ts(row.get('ts'))),
    )


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(db_path), timeout=BUSY_TIMEOUT_MS / 1000.0)
    con.execute('PRAGMA journal_mode=WAL')
    con.execute(f'PRAGMA busy_timeout={BUSY_TIMEOUT_MS}')
    con.execute('PRAGMA synchronous=NORMAL')
    try:
        con.execute(SCHEMA)
        con.execute(META_DDL)
        con.commit()
    except sqlite3.Error as exc:
        _log(f'schema ensure failed (fail-open): {exc}')
    return con


def _write_cursor(con: sqlite3.Connection, cursor: dict | None) -> None:
    if not cursor:
        return
    con.execute(META_DDL)
    con.execute(
        'INSERT INTO hindsight_populate_meta(key, value) VALUES (?, ?) '
        'ON CONFLICT(key) DO UPDATE SET value=excluded.value',
        ('cursor', json.dumps(cursor, default=str)),
    )


def read_db_cursor(con: sqlite3.Connection) -> dict | None:
    try:
        con.execute(META_DDL)
        row = con.execute(
            "SELECT value FROM hindsight_populate_meta WHERE key='cursor'"
        ).fetchone()
    except sqlite3.Error as exc:
        _log(f'db cursor read skipped: {exc}')
        return None
    if not row or not row[0]:
        return None
    try:
        raw = json.loads(row[0])
    except json.JSONDecodeError:
        return None
    if not isinstance(raw, dict):
        return None
    return raw


def insert_batch(con: sqlite3.Connection, batch: list[tuple], cursor: dict | None = None) -> int:
    """Insert batch atomically. On failure, try row-by-row and skip errors."""
    if not batch:
        return 0
    sql = (
        'INSERT INTO hindsight_events '
        '(session_id, turn_idx, event_type, payload, quality, created_at) '
        'VALUES (?, ?, ?, ?, ?, ?)'
    )
    try:
        con.execute('BEGIN IMMEDIATE')
        con.executemany(sql, batch)
        _write_cursor(con, cursor)
        con.commit()
        return len(batch)
    except sqlite3.Error as exc:
        _log(f'batch insert failed, falling back to per-row: {exc}')
        try:
            con.rollback()
        except sqlite3.Error:
            pass
        inserted = 0
        for rec in batch:
            try:
                con.execute('BEGIN IMMEDIATE')
                con.execute(sql, rec)
                _write_cursor(con, cursor)
                con.commit()
                inserted += 1
            except sqlite3.Error as row_exc:
                _log(f'row skipped (fail-open): {row_exc}')
                try:
                    con.rollback()
                except sqlite3.Error:
                    pass
        return inserted


def iter_new_lines(path: Path, byte_offset: int):
    """Yield (line_text, next_byte_offset) for complete lines after offset.

    next_byte_offset is the file position AFTER the consumed line (start of
    the following byte). Incomplete trailing line is not yielded, so the
    next run retries it — no skip, no double-count.
    """
    size = path.stat().st_size
    if byte_offset > size:
        # truncated/rotated log — restart from 0
        byte_offset = 0
    byte_offset = max(byte_offset, 0)
    with path.open('rb') as fh:
        fh.seek(byte_offset)
        while True:
            start = fh.tell()
            raw = fh.readline()
            if not raw:
                break
            if not raw.endswith(b'\n'):
                # partial line at EOF — leave offset at `start`
                break
            text = raw.decode('utf-8', errors='replace')
            yield text, fh.tell(), start


def populate(db_path: Path | None = None) -> dict:
    t0 = time.monotonic()
    src = jsonl_path()
    dbp = db_path or hindsight_db_path()
    state = load_state()
    n_inserted = 0
    n_seen = 0
    n_skipped = 0
    last_ts = state.get('last_ts')
    byte_offset = int(state.get('byte_offset') or 0)
    line_offset = int(state.get('line_offset') or 0)

    if not src.is_file():
        report = {
            'n_inserted': 0,
            'n_total': 0,
            'last_ts': last_ts,
            'duration': round(time.monotonic() - t0, 4),
            'note': f'missing source {src}',
        }
        try:
            _atomic_write_json(report_path(), report)
        except OSError:
            pass
        return report

    try:
        size = src.stat().st_size
    except OSError as exc:
        _log(f'stat failed (fail-open): {exc}')
        report = {
            'n_inserted': 0,
            'n_total': 0,
            'last_ts': last_ts,
            'duration': round(time.monotonic() - t0, 4),
            'error': str(exc),
        }
        try:
            _atomic_write_json(report_path(), report)
        except OSError:
            pass
        return report

    if byte_offset > size:
        _log(f'source shrank ({size} < {byte_offset}); resetting offset')
        byte_offset = 0
        line_offset = 0

    con = None
    lock_fd = None
    try:
        con = connect(dbp)
    except sqlite3.Error as exc:
        _log(f'db connect failed (fail-open): {exc}')
        report = {
            'n_inserted': 0,
            'n_total': 0,
            'last_ts': last_ts,
            'duration': round(time.monotonic() - t0, 4),
            'error': str(exc),
        }
        try:
            _atomic_write_json(report_path(), report)
        except OSError:
            pass
        return report

    db_cur = read_db_cursor(con)
    if db_cur is not None:
        try:
            db_off = int(db_cur.get('byte_offset') or 0)
        except (TypeError, ValueError):
            db_off = 0
        if db_off > byte_offset:
            # DB committed further than the JSON state file (crash window).
            byte_offset = db_off
            try:
                line_offset = int(db_cur.get('line_offset') or line_offset)
            except (TypeError, ValueError):
                pass
            if db_cur.get('last_ts') is not None:
                last_ts = db_cur.get('last_ts')

    try:
        lock_path = cache_dir() / 'hindsight-populate.lock'
        lock_fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o644)
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        if lock_fd is not None:
            try:
                os.close(lock_fd)
            except OSError:
                pass
            lock_fd = None
        _log('another populate holds the lock; skipping (fail-open)')
        try:
            con.close()
        except sqlite3.Error:
            pass
        return {
            'n_inserted': 0,
            'n_total': 0,
            'last_ts': last_ts,
            'duration': round(time.monotonic() - t0, 4),
            'note': 'lock_busy',
        }

    batch: list[tuple] = []
    batch_end_offset = byte_offset
    batch_end_line = line_offset
    sequential = line_offset

    def flush() -> None:
        nonlocal n_inserted, byte_offset, line_offset, batch, batch_end_offset, batch_end_line
        if not batch:
            return
        cursor = {
            'byte_offset': batch_end_offset,
            'line_offset': batch_end_line,
            'last_ts': last_ts,
        }
        inserted = insert_batch(con, batch, cursor)
        n_inserted += inserted
        # Advance cursor past the batch even if some rows were skipped,
        # otherwise a poison row would stall the pipeline forever.
        byte_offset = batch_end_offset
        line_offset = batch_end_line
        save_state(cursor)
        batch = []

    try:
        for text, next_off, _start in iter_new_lines(src, byte_offset):
            sequential += 1
            stripped = text.strip()
            if not stripped:
                batch_end_offset = next_off
                batch_end_line = sequential
                n_seen += 1
                continue
            try:
                row = json.loads(stripped)
            except json.JSONDecodeError:
                n_skipped += 1
                n_seen += 1
                batch_end_offset = next_off
                batch_end_line = sequential
                continue
            if not isinstance(row, dict):
                n_skipped += 1
                n_seen += 1
                batch_end_offset = next_off
                batch_end_line = sequential
                continue
            try:
                rec = row_to_tuple(row, sequential)
            except Exception as exc:
                n_skipped += 1
                n_seen += 1
                batch_end_offset = next_off
                batch_end_line = sequential
                _log(f'row convert skipped: {exc}')
                continue
            batch.append(rec)
            n_seen += 1
            batch_end_offset = next_off
            batch_end_line = sequential
            if rec[5] is not None:
                last_ts = rec[5]
            if len(batch) >= BATCH_SIZE:
                flush()
        flush()
        if batch_end_offset > byte_offset:
            byte_offset = batch_end_offset
            line_offset = batch_end_line
            save_state({
                'byte_offset': byte_offset,
                'line_offset': line_offset,
                'last_ts': last_ts,
            })
    except Exception as exc:
        _log(f'populate loop error (fail-open): {exc}')
        traceback.print_exc(file=sys.stderr)
        try:
            flush()
        except Exception:
            pass
    finally:
        if con is not None:
            try:
                con.close()
            except sqlite3.Error:
                pass
        if lock_fd is not None:
            try:
                os.close(lock_fd)
            except OSError:
                pass

    duration = round(time.monotonic() - t0, 4)
    n_total = 0
    try:
        con2 = sqlite3.connect(f'file:{dbp}?mode=ro', uri=True, timeout=2)
        try:
            n_total = int(con2.execute('SELECT COUNT(*) FROM hindsight_events').fetchone()[0])
        finally:
            con2.close()
    except sqlite3.Error as exc:
        _log(f'count query failed (fail-open): {exc}')

    report = {
        'n_inserted': n_inserted,
        'n_total': n_total,
        'n_seen': n_seen,
        'n_skipped': n_skipped,
        'last_ts': last_ts,
        'byte_offset': byte_offset,
        'line_offset': line_offset,
        'duration': duration,
        'source': str(src),
        'db': str(dbp),
    }
    try:
        _atomic_write_json(report_path(), report)
    except OSError as exc:
        _log(f'report write failed (fail-open): {exc}')
    return report


def self_test() -> int:
    td = Path(tempfile.mkdtemp(prefix='hindsight-populate-'))
    dbp = td / 'hindsight.db'
    con = connect(dbp)
    rows = [
        ('sess-a', 1, 'tool_call', '{"tool_name":"t1","success":true}', 1.0, 1.0),
        ('sess-b', 2, 'tool_call', '{"tool_name":"t2","success":false}', 0.0, 2.0),
        ('sess-c', 3, 'tool_call', '{"tool_name":"t3","success":true}', 1.0, 3.0),
    ]
    n = insert_batch(con, rows)
    count = con.execute('SELECT COUNT(*) FROM hindsight_events').fetchone()[0]
    con.close()
    ok = n == 3 and count == 3
    # incremental offset: two complete lines + partial
    src = td / 'turn-behavior.jsonl'
    line1 = json.dumps({
        'ts': '2026-01-01T00:00:00+00:00',
        'session_id': 's1',
        'turn_id': 'abc:deadbeef',
        'tool_name': 'web_search',
        'skill_entropy': 0.2,
        'success': True,
        'token_estimate': 10,
    }) + '\n'
    line2 = json.dumps({
        'ts': '2026-01-01T00:00:01+00:00',
        'session_id': 's1',
        'turn_id': 'abc:cafebabe',
        'tool_name': 'read_file',
        'skill_entropy': 0.1,
        'success': False,
        'token_estimate': 5,
    }) + '\n'
    partial = '{"ts": "2026-01-01T00:00:02+00:00", "session_id": "s1"'
    src.write_bytes((line1 + line2 + partial).encode('utf-8'))
    # monkeypatch paths via env-local cache
    global _hermes_root, _hermes_base
    old_root, old_base = _hermes_root, _hermes_base
    try:
        _hermes_root = td
        _hermes_base = td
        (td / 'cache').mkdir(exist_ok=True)
        # jsonl_path uses cache_dir under _hermes_root
        src_dest = td / 'cache' / 'turn-behavior.jsonl'
        src_dest.write_bytes(src.read_bytes())
        r1 = populate(db_path=dbp)
        # first pass should insert 2 (partial withheld)
        if r1.get('n_inserted') != 2:
            print(f'SELF-TEST FAIL incremental first pass n_inserted={r1}', file=sys.stderr)
            ok = False
        # complete the partial line and re-run — must insert exactly 1 more
        with src_dest.open('ab') as fh:
            fh.write(b', "turn_id": "abc:0badf00d", "tool_name": "x", '
                     b'"skill_entropy": 0, "success": true, "token_estimate": 1}\n')
        r2 = populate(db_path=dbp)
        if r2.get('n_inserted') != 1:
            print(f'SELF-TEST FAIL incremental second pass n_inserted={r2}', file=sys.stderr)
            ok = False
        # third pass: no new complete lines
        r3 = populate(db_path=dbp)
        if r3.get('n_inserted') != 0:
            print(f'SELF-TEST FAIL third pass reprocess n_inserted={r3}', file=sys.stderr)
            ok = False
    finally:
        _hermes_root, _hermes_base = old_root, old_base
    if ok:
        print('SELF-TEST PASS count=3 incremental=ok')
        return 0
    print('SELF-TEST FAIL', file=sys.stderr)
    return 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description='Populate hindsight_events from turn-behavior.jsonl')
    ap.add_argument('--self-test', action='store_true')
    args = ap.parse_args(argv)
    if args.self_test:
        return self_test()
    try:
        report = populate()
        print(json.dumps(report, ensure_ascii=False, default=str))
        return 0
    except Exception as exc:
        _log(f'fatal caught (fail-open): {exc}')
        traceback.print_exc(file=sys.stderr)
        return 0


if __name__ == '__main__':
    sys.exit(main())
