#!/usr/bin/env python3
"""Per-skill latency collector and aggregator.

Hook helpers record elapsed_ms to skill-latency.jsonl and tool_review_log.
--run aggregates mean/p95/p99 into skill-latency-stats.json.
"""
from __future__ import annotations

import os
from pathlib import Path


def _hermes_home() -> Path:
    """True ~/.hermes: strip a trailing profiles/<name> suffix."""
    env = os.environ.get('HERMES_HOME', '').strip()
    p = Path(env) if env else Path.home() / '.hermes'
    if p.name != '.hermes' and p.parent.name == 'profiles':
        return p.parent.parent
    return p


def _profile_name() -> str:
    profile = os.environ.get('HERMES_PROFILE', 'fork').strip()
    if profile:
        return profile
    raw = os.environ.get('HERMES_HOME', '').strip()
    if raw:
        p = Path(raw)
        if p.parent.name == 'profiles':
            return p.name
    if (_hermes_home() / 'profiles' / 'fork').exists():
        return 'fork'
    return ''


def _hermes_root() -> Path:
    base = _hermes_home()
    profile = _profile_name()
    return (base / 'profiles' / profile) if profile else base


def _paths() -> dict:
    base = _hermes_home()
    root = _hermes_root()
    cache = root / 'cache'
    return {
        'base': base,
        'root': root,
        'jsonl': cache / 'skill-latency.jsonl',
        'stats': cache / 'skill-latency-stats.json',
        'db': base / 'memory-facts' / 'lifecycle.db',
    }


_hermes_base = _hermes_home()
_hermes_profile = _profile_name()
_hermes_root_path = _hermes_root()

import argparse
import fcntl
import json
import sqlite3
import statistics
import sys
import tempfile
import time
import uuid
from collections import defaultdict
from datetime import datetime, timezone, UTC

_P0 = _paths()
CACHE = _P0['root'] / 'cache'
JSONL_PATH = _P0['jsonl']
STATS_PATH = _P0['stats']
LIFECYCLE_DB = _P0['db']

_STARTS: dict = {}


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _atomic_write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix('.lock')
    tmp = path.with_name(path.name + '.tmp')
    with open(str(lock_path), 'a', encoding='utf-8') as lf:
        fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
        try:
            tmp.write_text(json.dumps(obj, indent=2) + '\n', encoding='utf-8')
            os.replace(str(tmp), str(path))
        finally:
            fcntl.flock(lf.fileno(), fcntl.LOCK_UN)


def _append_jsonl(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix('.lock')
    with open(str(lock_path), 'a', encoding='utf-8') as lf:
        fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
        try:
            with open(str(path), 'a', encoding='utf-8') as f:
                f.write(json.dumps(record, default=str) + '\n')
        finally:
            fcntl.flock(lf.fileno(), fcntl.LOCK_UN)


def _connect(db_path: Path):
    conn = sqlite3.connect(str(db_path), timeout=30)
    conn.execute('PRAGMA journal_mode=WAL')
    return conn


def on_pre_tool_call(tool_name: str = '', session_id: str = '', **kwargs):
    try:
        key = (str(session_id or ''), str(tool_name or ''))
        _STARTS[key] = time.monotonic()
    except Exception:
        return
    return


def on_post_tool_call(tool_name: str = '', args=None, result=None, session_id: str = '',
                      jsonl_path: Path | None = None, db_path: Path | None = None, **kwargs):
    try:
        key = (str(session_id or ''), str(tool_name or ''))
        start = _STARTS.pop(key, None)
        now_m = time.monotonic()
        if start is not None:
            elapsed_ms = float((now_m - start) * 1000.0)
        else:
            dm = kwargs.get('duration_ms')
            try:
                elapsed_ms = float(dm) if dm is not None else 0.0
            except (TypeError, ValueError):
                elapsed_ms = 0.0
        if elapsed_ms < 0:
            elapsed_ms = 0.0
        rec = {
            'ts': _now(),
            'tool_name': str(tool_name or ''),
            'session_id': str(session_id or ''),
            'elapsed_ms': elapsed_ms,
            'result_size': len(str(result)) if result is not None else 0,
        }
        live = _paths()
        _append_jsonl(Path(jsonl_path) if jsonl_path is not None else live['jsonl'], rec)
        dbp = Path(db_path) if db_path is not None else live['db']
        if dbp.exists():
            conn = None
            try:
                conn = _connect(dbp)
                tabs = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                if 'tool_review_log' in tabs:
                    outcome = 'ok' if result is not None else 'fail'
                    score = 1.0 if result is not None else 0.0
                    conn.execute(
                        'INSERT INTO tool_review_log (ts, session_id, tool_name, latency_ms, outcome, score, notes) '
                        'VALUES (?,?,?,?,?,?,?)',
                        (rec['ts'], rec['session_id'], rec['tool_name'], elapsed_ms, outcome, score, ''),
                    )
                    conn.commit()
            except sqlite3.Error:
                pass
            finally:
                if conn is not None:
                    conn.close()
        return rec
    except Exception:
        return None


def _percentile(sorted_vals, p: float) -> float:
    if not sorted_vals:
        return 0.0
    if len(sorted_vals) == 1:
        return float(sorted_vals[0])
    k = (len(sorted_vals) - 1) * p
    f = int(k)
    c = min(f + 1, len(sorted_vals) - 1)
    if f == c:
        return float(sorted_vals[f])
    return float(sorted_vals[f] * (c - k) + sorted_vals[c] * (k - f))


def aggregate(jsonl_path: Path, stats_path: Path) -> dict:
    if not jsonl_path.exists():
        return {'status': 'insufficient_data', 'reason': 'missing_jsonl'}
    by_skill = defaultdict(list)
    try:
        with open(str(jsonl_path), encoding='utf-8', errors='replace') as fh:
            for line in fh:
                raw = line.strip()
                if not raw:
                    continue
                try:
                    rec = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if not isinstance(rec, dict):
                    continue
                name = rec.get('tool_name') or rec.get('skill_name')
                ms = rec.get('elapsed_ms')
                if not name or ms is None:
                    continue
                try:
                    ms_f = float(ms)
                except (TypeError, ValueError):
                    continue
                if ms_f != ms_f or ms_f < 0:
                    continue
                by_skill[str(name)].append(ms_f)
    except OSError as exc:
        return {'status': 'error', 'reason': str(exc)}
    if not by_skill:
        return {'status': 'insufficient_data', 'reason': 'no_rows'}
    stats = {}
    for name, vals in by_skill.items():
        vals_sorted = sorted(vals)
        stats[name] = {
            'n': len(vals_sorted),
            'mean_ms': float(statistics.mean(vals_sorted)),
            'p95_ms': _percentile(vals_sorted, 0.95),
            'p99_ms': _percentile(vals_sorted, 0.99),
        }
    payload = {'ts': _now(), 'skills': stats, 'n_skills': len(stats)}
    _atomic_write(stats_path, payload)
    return {'status': 'ok', 'n_skills': len(stats), 'written': str(stats_path)}


def _self_test() -> int:
    # PATH STRIPPING RULE
    old_home = os.environ.get('HERMES_HOME')
    old_prof = os.environ.get('HERMES_PROFILE')
    try:
        os.environ['HERMES_HOME'] = str(Path.home() / '.hermes' / 'profiles' / 'fork')
        os.environ.pop('HERMES_PROFILE', None)
        assert _hermes_home() == Path.home() / '.hermes', _hermes_home()
        assert _profile_name() == 'fork', _profile_name()
        assert 'profiles' in str(_hermes_root())
        os.environ['HERMES_HOME'] = str(Path.home() / '.hermes')
        os.environ['HERMES_PROFILE'] = 'fork'
        assert _hermes_home() == Path.home() / '.hermes'
        assert _profile_name() == 'fork'
    finally:
        if old_home is None:
            os.environ.pop('HERMES_HOME', None)
        else:
            os.environ['HERMES_HOME'] = old_home
        if old_prof is None:
            os.environ.pop('HERMES_PROFILE', None)
        else:
            os.environ['HERMES_PROFILE'] = old_prof

    td = Path(tempfile.mkdtemp(prefix='slc-'))
    try:
        db = td / 'lc.db'
        conn = sqlite3.connect(str(db), timeout=30)
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute(
            'CREATE TABLE tool_review_log (id INTEGER PRIMARY KEY, ts TEXT, session_id TEXT, '
            'tool_name TEXT, latency_ms REAL, outcome TEXT, score REAL, notes TEXT)'
        )
        conn.commit()
        conn.close()
        out = td / ('skill-latency_test_' + uuid.uuid4().hex + '.jsonl')
        on_pre_tool_call(tool_name='terminal', session_id='s1')
        time.sleep(0.01)
        rec = on_post_tool_call(
            tool_name='terminal', result={'ok': True}, session_id='s1',
            jsonl_path=out, db_path=db,
        )
        assert rec is not None, rec
        assert rec['elapsed_ms'] >= 0.0
        assert out.exists()
        lines = out.read_text(encoding='utf-8').splitlines()
        assert len(lines) == 1, lines
        conn = sqlite3.connect(str(db), timeout=30)
        conn.execute('PRAGMA journal_mode=WAL')
        n = conn.execute('SELECT COUNT(*) FROM tool_review_log').fetchone()[0]
        conn.close()
        assert n == 1, n
        stats = td / 'stats.json'
        r = aggregate(out, stats)
        assert r.get('status') == 'ok', r
        payload = json.loads(stats.read_text(encoding='utf-8'))
        assert 'terminal' in payload['skills']
        missing = aggregate(td / 'nope.jsonl', stats)
        assert missing.get('status') == 'insufficient_data'
        rec2 = on_post_tool_call(
            tool_name='read_file', result={'x': 1}, session_id='s2',
            jsonl_path=out, db_path=db, duration_ms=12.5,
        )
        assert rec2 is not None and abs(rec2['elapsed_ms'] - 12.5) < 1e-9, rec2
    finally:
        import shutil
        shutil.rmtree(td, ignore_errors=True)
    print('[skill-latency-collector] --self-test PASS')
    return 0


def main() -> None:
    live = _paths()
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--run', action='store_true')
    ap.add_argument('--jsonl', default=str(live['jsonl']))
    ap.add_argument('--stats', default=str(live['stats']))
    args = ap.parse_args()
    if args.self_test:
        try:
            sys.exit(_self_test())
        except Exception as exc:
            print(f'[skill-latency-collector] --self-test FAIL: {exc}')
            sys.exit(1)
    try:
        result = aggregate(Path(args.jsonl), Path(args.stats))
        print(json.dumps(result, indent=2, default=str))
        sys.exit(0)
    except Exception as exc:
        print(json.dumps({'status': 'error', 'reason': str(exc)}))
        sys.exit(0)


if __name__ == '__main__':
    main()
