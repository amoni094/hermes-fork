#!/usr/bin/env python3
"""MeshHeal: Two-Timescale Self-Healing for Gray Failures in Decentralized LLM Agent Networks.

Slow-loop CUSUM skill exclusion. Hard core invariant: a skill in the excluded
set must NOT appear in routing-exclusion.json active_skills until recovery
criteria are met.

Usage:
  python3 skill-monitor.py --self-test
  python3 skill-monitor.py --run
"""
from __future__ import annotations

import os
from pathlib import Path


def _hermes_home() -> Path:
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


_hermes_base = _hermes_home()
_hermes_profile = _profile_name()
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile else _hermes_base

import argparse
import fcntl
import json
import random
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timezone, UTC

LIFECYCLE_DB = _hermes_base / 'memory-facts' / 'lifecycle.db'
OUT_PATH = _hermes_root / 'cache' / 'routing-exclusion.json'

MU0 = 0.75
SLACK = 0.1
H_THRESH = 5.0
RECOVERY_WINDOW = 20
RECOVERY_MEAN = 0.70

DDL = (
    'CREATE TABLE IF NOT EXISTS tool_review_log ('
    'skill_name TEXT, turn_id TEXT, task_id TEXT, '
    'output_score REAL, reviewer_id TEXT, verdict_pass INTEGER)'
)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _connect(db_path: Path):
    conn = sqlite3.connect(str(db_path), timeout=30)
    conn.execute('PRAGMA journal_mode=WAL')
    return conn


def ensure_table(conn) -> None:
    conn.execute(DDL)
    conn.commit()


def _atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix('.lock')
    tmp = path.with_suffix(path.suffix + '.tmp')
    payload = json.dumps(data, indent=2) + '\n'
    with open(lock_path, 'w', encoding='utf-8') as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        tmp.write_text(payload, encoding='utf-8')
        os.replace(str(tmp), str(path))


def _clip01(x) -> float | None:
    try:
        xv = float(x)
    except (TypeError, ValueError):
        return None
    if xv != xv:
        return None
    xv = max(xv, 0.0)
    xv = min(xv, 1.0)
    return xv


def cusum_detect(scores, mu0: float = MU0, slack: float = SLACK, h: float = H_THRESH):
    """S_t = max(0, S_prev + (mu0 - slack - x_t)); degraded if any S_t > h."""
    S = 0.0
    max_S = 0.0
    first = None
    n = 0
    for x in scores:
        xv = _clip01(x)
        if xv is None:
            continue
        n += 1
        S = max(0.0, S + (mu0 - slack - xv))
        max_S = max(max_S, S)
        if first is None and S > h:
            first = n - 1
    return {'S': S, 'max_S': max_S, 'degraded': first is not None, 'first_index': first, 'n': n}


def recovery_ok(scores, mu0: float = MU0, slack: float = SLACK,
                window: int = RECOVERY_WINDOW, mean_min: float = RECOVERY_MEAN):
    vals = []
    for x in scores:
        xv = _clip01(x)
        if xv is not None:
            vals.append(xv)
    if len(vals) < window:
        return False, 0.0, 0.0
    last = vals[-window:]
    mean = sum(last) / float(len(last))
    S = 0.0
    for xv in last:
        S = max(0.0, S + (mu0 - slack - xv))
    return (mean >= mean_min and S <= 1e-12), mean, S


def load_rows(conn):
    tabs = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if 'tool_review_log' not in tabs:
        return []
    cols = {r[1] for r in conn.execute('PRAGMA table_info(tool_review_log)')}
    out = []
    if 'skill_name' in cols and 'output_score' in cols:
        raw = conn.execute(
            'SELECT skill_name, output_score FROM tool_review_log ORDER BY rowid'
        ).fetchall()
        for name, score in raw:
            if not name:
                continue
            xv = _clip01(score)
            if xv is None:
                xv = 0.0
            out.append((str(name), xv))
        return out
    if 'tool_name' in cols and 'score' in cols:
        raw = conn.execute(
            'SELECT tool_name, score FROM tool_review_log ORDER BY rowid'
        ).fetchall()
        for name, score in raw:
            if not name:
                continue
            xv = _clip01(score)
            if xv is None:
                xv = 0.0
            out.append((str(name), xv))
        return out
    return out


def group_scores(rows):
    grouped = defaultdict(list)
    for name, score in rows:
        grouped[str(name)].append(score)
    return grouped


def load_prev(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        if isinstance(data, dict):
            return data
    except (OSError, json.JSONDecodeError):
        pass
    return {}


def _recovery_cursor(recovery_log, skill: str) -> int:
    n = 0
    for ev in recovery_log:
        if not isinstance(ev, dict):
            continue
        if ev.get('skill') == skill:
            try:
                n = max(n, int(ev.get('n_rows') or 0))
            except (TypeError, ValueError):
                continue
    return n


def enforce_hard_core(active, excluded):
    """Hard core: excluded skills must not appear in active_skills."""
    ex = set(excluded)
    return [s for s in active if s not in ex]


def meshheal(rows, prev=None, ts=None) -> dict:
    prev = prev if isinstance(prev, dict) else {}
    ts = ts or _now()
    grouped = group_scores(rows)
    known = sorted(grouped.keys())
    excluded_prev = prev.get('excluded') if isinstance(prev.get('excluded'), dict) else {}
    recovery_log = list(prev.get('recovery_log') or [])

    excluded = {}
    for skill, meta in excluded_prev.items():
        if isinstance(meta, dict) and skill:
            excluded[str(skill)] = dict(meta)

    for skill, scores in grouped.items():
        if skill in excluded:
            continue
        cursor = _recovery_cursor(recovery_log, skill)
        series = scores[cursor:] if cursor else scores
        det = cusum_detect(series)
        if det['degraded']:
            excluded[skill] = {
                'ts_excluded': ts,
                'reason': 'cusum_changepoint',
                'cusum_value': float(det['max_S']),
            }

    still = {}
    for skill, meta in excluded.items():
        scores = grouped.get(skill, [])
        ok, _mean, _s = recovery_ok(scores)
        if ok:
            recovery_log.append({
                'ts': ts,
                'skill': skill,
                'reason': 'mean_and_cusum_reset',
                'n_rows': len(scores),
            })
        else:
            det = cusum_detect(scores)
            meta = dict(meta)
            meta['cusum_value'] = float(det['max_S'])
            if 'reason' not in meta:
                meta['reason'] = 'cusum_changepoint'
            if 'ts_excluded' not in meta:
                meta['ts_excluded'] = ts
            still[skill] = meta
    excluded = still

    active = enforce_hard_core([s for s in known if s not in excluded], excluded)
    payload = {
        'ts': ts,
        'active_skills': active,
        'excluded': excluded,
        'recovery_log': recovery_log,
    }
    for s in excluded:
        if s in payload['active_skills']:
            raise AssertionError(f'hard-core invariant violated: {s} in active_skills')
    return payload


def cmd_run(db_path: Path | None = None, out_path: Path | None = None) -> int:
    # H-I7: shadow monitor must not fail the live path
    try:
        db_path = db_path or LIFECYCLE_DB
        out_path = out_path or OUT_PATH
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = None
        try:
            conn = _connect(db_path)
            ensure_table(conn)
            rows = load_rows(conn)
        finally:
            if conn is not None:
                conn.close()
        if not rows:
            print(json.dumps({
                'status': 'insufficient_data',
                'n': 0,
                'out': str(out_path),
            }))
            prev = load_prev(out_path)
            payload = {
                'ts': _now(),
                'active_skills': list(prev.get('active_skills') or []),
                'excluded': dict(prev.get('excluded') or {}) if isinstance(prev.get('excluded'), dict) else {},
                'recovery_log': list(prev.get('recovery_log') or []),
            }
            payload['active_skills'] = enforce_hard_core(payload['active_skills'], payload['excluded'])
            _atomic_write(out_path, payload)
            return 0
        prev = load_prev(out_path)
        payload = meshheal(rows, prev=prev)
        _atomic_write(out_path, payload)
        print(json.dumps({
            'status': 'ok',
            'n': len(rows),
            'n_active': len(payload['active_skills']),
            'n_excluded': len(payload['excluded']),
            'out': str(out_path),
        }))
        return 0
    except Exception as exc:
        print(json.dumps({'status': 'error', 'reason': str(exc)}))
        return 0


def _bernoulli(rng: random.Random, p: float) -> float:
    return 1.0 if rng.random() < p else 0.0


def cmd_self_test() -> int:
    rng = random.Random(0)
    rows = []
    for turn in range(1, 301):
        for sk in range(5):
            p = 0.40 if (sk == 2 and turn >= 150) else 0.85
            rows.append(('skill_%d' % sk, _bernoulli(rng, p)))

    rows_180 = []
    for turn in range(1, 181):
        base = (turn - 1) * 5
        rows_180.extend(rows[base:base + 5])
    snap180 = meshheal(rows_180, prev={})
    assert 'skill_2' in snap180['excluded'], snap180['excluded']
    assert snap180['excluded']['skill_2'].get('reason') == 'cusum_changepoint'
    assert 'skill_2' not in snap180['active_skills'], snap180['active_skills']
    for sk in ('skill_0', 'skill_1', 'skill_3', 'skill_4'):
        assert sk not in snap180['excluded'], (sk, snap180['excluded'])
        assert sk in snap180['active_skills'], snap180['active_skills']

    full = meshheal(rows, prev={})
    assert 'skill_2' in full['excluded'], full['excluded']
    assert 'skill_2' not in full['active_skills'], full['active_skills']
    for s in full['excluded']:
        assert s not in full['active_skills']

    rec_rows = list(rows)
    for _ in range(25):
        rec_rows.append(('skill_2', _bernoulli(rng, 0.85)))
    recovered = meshheal(rec_rows, prev=full)
    assert 'skill_2' not in recovered['excluded'], recovered['excluded']
    assert 'skill_2' in recovered['active_skills'], recovered['active_skills']
    assert any(ev.get('skill') == 'skill_2' for ev in recovered['recovery_log'])
    for s in recovered['excluded']:
        assert s not in recovered['active_skills']

    # Isolated write: never touch production OUT_PATH
    import tempfile, uuid
    td = Path(tempfile.mkdtemp(prefix='meshheal-'))
    out = td / ('routing-exclusion_test_' + uuid.uuid4().hex + '.json')
    _atomic_write(out, recovered)
    loaded = json.loads(out.read_text(encoding='utf-8'))
    assert 'skill_2' in loaded['active_skills']
    assert 'skill_2' not in loaded.get('excluded', {})
    try:
        out.unlink()
        out.with_suffix('.lock').unlink(missing_ok=True)
        td.rmdir()
    except OSError:
        pass

    print('PASS')
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description='MeshHeal two-timescale skill CUSUM monitor')
    p.add_argument('--self-test', action='store_true')
    p.add_argument('--run', action='store_true')
    p.add_argument('--db', type=str, default='')
    p.add_argument('--out', type=str, default='')
    args = p.parse_args(argv)
    if args.self_test:
        try:
            return cmd_self_test()
        except AssertionError as exc:
            print(f'FAIL: {exc}', file=sys.stderr)
            return 1
    # Cron scheduler invokes wrappers with empty argv; default to run.
    db = Path(args.db) if args.db else None
    out = Path(args.out) if args.out else None
    return cmd_run(db_path=db, out_path=out)


if __name__ == '__main__':
    sys.exit(main())
