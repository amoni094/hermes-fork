#!/usr/bin/env python3
"""Epistemic Regret Minimization - Label-Free Causal Critique Beyond Outcome Reward.

Causal-critique score for a skill increases when confounds are flagged AND
interventional reasoning is validated. It does NOT increase on outcome
correctness alone without causal structure inspection.
"""
from __future__ import annotations

import os
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base

import argparse
import fcntl
import json
import math
import random
import sqlite3
import sys
import uuid
from collections import defaultdict
from datetime import datetime, timezone

CACHE = _hermes_root / 'cache'
RANKING_PATH = CACHE / 'causal-critique-ranking.json'
COHERENCE_PATH = CACHE / 'skill-causal-coherence.json'
EVENTS_JSONL = CACHE / 'causal-events.jsonl'
EVENTS_DB = CACHE / 'causal-events.db'

INTERV_KEYS = ('interventional_flag', 'intervention_validated', 'interventional_correct', 'intervention_flag')
CONFOUND_KEYS = ('confound_flag', 'confound_flagged', 'confound_rate', 'confounds')


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _coerce_float(v, default=0.0) -> float:
    try:
        x = float(v)
        if not math.isfinite(x):
            return default
        return x
    except (TypeError, ValueError):
        return default


def _coerce_bool(v) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return bool(v)
    s = str(v).strip().lower()
    return s in ('1', 'true', 'yes', 'y')


def _atomic_write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(path.suffix + '.lock') if path.suffix else path.with_name(path.name + '.lock')
    tmp = path.with_name(path.name + '.tmp')
    payload = json.dumps(obj, indent=2) + '\n'
    with open(str(lock_path), 'a', encoding='utf-8') as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        try:
            tmp.write_text(payload, encoding='utf-8')
            tmp.replace(path)
        finally:
            fcntl.flock(lf, fcntl.LOCK_UN)


def _append_jsonl(path: Path, rec: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_suffix('.lock')
    line = json.dumps(rec) + '\n'
    with open(str(lock), 'a', encoding='utf-8') as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        try:
            with open(str(path), 'a', encoding='utf-8') as fh:
                fh.write(line)
        finally:
            fcntl.flock(lf, fcntl.LOCK_UN)


def has_causal_structure(entry: dict) -> bool:
    """Hard core: BOTH interventional and confound flags must be present."""
    if not isinstance(entry, dict):
        return False
    keys = set(entry.keys())
    has_int = any(k in keys for k in INTERV_KEYS)
    has_conf = any(k in keys for k in CONFOUND_KEYS)
    return has_int and has_conf


def causal_coherence_score(interventional_correct, total, confound_rate) -> float:
    tot = max(1.0, _coerce_float(total, 1.0))
    ic = _coerce_float(interventional_correct)
    if ic > 1.0 or tot > 1.0:
        rate = ic / tot
    else:
        rate = ic
    rate = max(0.0, min(1.0, rate))
    cr = max(0.0, min(1.0, _coerce_float(confound_rate)))
    s = rate * (1.0 - cr)
    if not math.isfinite(s):
        return 0.0
    return max(0.0, min(1.0, s))


def _entry_counts(entry: dict) -> tuple:
    total = entry.get('total', entry.get('n', entry.get('n_tasks')))
    ic = entry.get('interventional_correct')
    if ic is None:
        ic = 1.0 if _coerce_bool(entry.get('intervention_validated')) else 0.0
        if total is None:
            total = 1.0
    total = _coerce_float(total, 1.0)
    ic = _coerce_float(ic)
    cr = entry.get('confound_rate')
    if cr is None:
        if 'confound_flag' in entry or 'confound_flagged' in entry:
            flagged = _coerce_bool(entry.get('confound_flagged', entry.get('confound_flag')))
            cr = 1.0 if flagged else 0.0
        else:
            cr = 0.0
    return ic, total, _coerce_float(cr)


def score_entry(entry: dict) -> float:
    ic, total, cr = _entry_counts(entry)
    return causal_coherence_score(ic, total, cr)


def load_ranking(path: Path) -> list:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError, UnicodeError):
        return []
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        for k in ('ranking', 'entries', 'skills', 'items', 'data'):
            v = data.get(k)
            if isinstance(v, list):
                return [x for x in v if isinstance(x, dict)]
    return []


def load_history(path: Path) -> dict:
    if not path.exists():
        return {'ts': None, 'skills': {}}
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError, UnicodeError):
        return {'ts': None, 'skills': {}}
    if not isinstance(data, dict):
        return {'ts': None, 'skills': {}}
    skills = data.get('skills')
    if not isinstance(skills, dict):
        skills = {}
    return {'ts': data.get('ts'), 'skills': skills}


def skill_id_of(entry: dict) -> str:
    for k in ('skill_id', 'skill', 'name', 'id'):
        v = entry.get(k)
        if v is not None and str(v).strip():
            return str(v).strip()
    return 'unknown'


def accumulate(entries: list, history: dict, events_out: list) -> dict:
    skills = dict(history.get('skills') or {})
    n_updated = 0
    n_skipped_no_structure = 0
    for i, entry in enumerate(entries):
        sid = skill_id_of(entry)
        if not has_causal_structure(entry):
            n_skipped_no_structure += 1
            continue
        new_score = score_entry(entry)
        prev = skills.get(sid) or {}
        prev_score = _coerce_float(prev.get('causal_coherence_score'), 0.0)
        delta = new_score - prev_score
        rec = {
            'causal_coherence_score': new_score,
            'n': int(_coerce_float(prev.get('n'), 0) + 1),
            'history': list(prev.get('history') or [])[-49:] + [{'ts': _now(), 'score': new_score}],
        }
        skills[sid] = rec
        events_out.append({
            'ts': _now(),
            'skill_id': sid,
            'episode_id': str(entry.get('episode_id') or entry.get('episode') or i),
            'confound_flagged': _coerce_bool(entry.get('confound_flagged', entry.get('confound_flag'))),
            'intervention_validated': _coerce_bool(entry.get('intervention_validated', entry.get('interventional_flag'))),
            'score_delta': round(delta, 6),
        })
        n_updated += 1
    return {
        'ts': _now(),
        'n_entries': len(entries),
        'n_updated': n_updated,
        'n_skipped_no_structure': n_skipped_no_structure,
        'skills': skills,
    }


def _events_db_insert(db_path: Path, events: list) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), timeout=30)
    try:
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute(
            'CREATE TABLE IF NOT EXISTS causal_events ('
            'id INTEGER PRIMARY KEY, ts TEXT, skill_id TEXT, episode_id TEXT, '
            'confound_flagged INTEGER, intervention_validated INTEGER, score_delta REAL)'
        )
        conn.executemany(
            'INSERT INTO causal_events(ts, skill_id, episode_id, confound_flagged, '
            'intervention_validated, score_delta) VALUES (?,?,?,?,?,?)',
            [(e['ts'], e['skill_id'], e['episode_id'], int(bool(e['confound_flagged'])),
              int(bool(e['intervention_validated'])), float(e['score_delta'])) for e in events],
        )
        conn.commit()
    finally:
        conn.close()


def persist_events(events: list, jsonl: Path, db: Path) -> None:
    for e in events:
        _append_jsonl(jsonl, e)
    if events:
        _events_db_insert(db, events)


def layer1_demo(rng=None) -> dict:
    """50 Pearl-ladder tasks: skill A 80% confound-free interventional, B 40%."""
    rng = rng or random.Random(11)
    tasks = []
    # 25 A + 25 B (50 tasks). Flags always present (structure inspected).
    # A: 20/25 interventional-correct, 2/25 confounded -> score = 0.80 * 0.92 = 0.736
    # Tighten A: 22/25 correct (0.88), 2/25 confound (0.08) -> 0.88*0.92=0.8096
    a_correct = [1] * 22 + [0] * 3
    a_conf = [0] * 23 + [1] * 2
    rng.shuffle(a_correct)
    rng.shuffle(a_conf)
    for i in range(25):
        tasks.append({
            'skill_id': 'A',
            'episode_id': 'pearl-A-%02d' % i,
            'rung': 'intervention',
            'interventional_flag': True,
            'confound_flag': True,
            'intervention_validated': bool(a_correct[i]),
            'interventional_correct': float(a_correct[i]),
            'confound_flagged': bool(a_conf[i]),
            'total': 1.0,
            'outcome_correct': True,
        })
    b_correct = [1] * 10 + [0] * 15
    b_conf = [1] * 15 + [0] * 10
    rng.shuffle(b_correct)
    rng.shuffle(b_conf)
    for i in range(25):
        tasks.append({
            'skill_id': 'B',
            'episode_id': 'pearl-B-%02d' % i,
            'rung': 'intervention',
            'interventional_flag': True,
            'confound_flag': True,
            'intervention_validated': bool(b_correct[i]),
            'interventional_correct': float(b_correct[i]),
            'confound_flagged': bool(b_conf[i]),
            'total': 1.0,
            'outcome_correct': True,
        })
    return tasks


def scores_from_tasks(tasks: list) -> dict:
    buckets = defaultdict(lambda: {'ic': 0.0, 'n': 0.0, 'conf': 0.0})
    for t in tasks:
        sid = skill_id_of(t)
        ic, total, cr = _entry_counts(t)
        buckets[sid]['ic'] += ic
        buckets[sid]['n'] += max(1.0, total)
        buckets[sid]['conf'] += cr if cr <= 1.0 else 1.0
    out = {}
    for sid, b in buckets.items():
        cr = b['conf'] / max(1.0, b['n'])
        out[sid] = causal_coherence_score(b['ic'], b['n'], cr)
    return out


def run_live(ranking_path: Path, coherence_path: Path, jsonl: Path, db: Path) -> dict:
    entries = load_ranking(ranking_path)
    if not entries:
        return {'status': 'insufficient_data', 'n': 0, 'ts': _now()}
    hist = load_history(coherence_path)
    events = []
    state = accumulate(entries, hist, events)
    if state['n_updated'] == 0:
        state['status'] = 'insufficient_data'
        state['reason'] = 'no entries with both interventional_flag and confound_flag'
        return state
    state['status'] = 'ok'
    _atomic_write(coherence_path, state)
    persist_events(events, jsonl, db)
    return state


def _self_test() -> int:
    tasks = layer1_demo(random.Random(3))
    assert len(tasks) == 50, len(tasks)
    scores = scores_from_tasks(tasks)
    a = scores['A']
    b = scores['B']
    assert a >= 0.75, 'A=%s expected >=0.75' % a
    assert b <= 0.50, 'B=%s expected <=0.50' % b
    assert abs(a - b) > 0.1, (a, b)
    # Hard core: outcome_correct alone must NOT increase the score
    hist = {'skills': {'C': {'causal_coherence_score': 0.40, 'n': 1, 'history': []}}}
    events = []
    outcome_only = {'skill_id': 'C', 'outcome_correct': True, 'episode_id': 'x'}
    assert not has_causal_structure(outcome_only)
    st = accumulate([outcome_only], hist, events)
    assert st['n_updated'] == 0
    assert abs(st['skills']['C']['causal_coherence_score'] - 0.40) < 1e-12
    assert events == []
    # Structure present: score may update
    structured = {
        'skill_id': 'C', 'interventional_flag': True, 'confound_flag': True,
        'intervention_validated': True, 'interventional_correct': 1.0,
        'confound_flagged': False, 'total': 1.0, 'episode_id': 'y',
    }
    events2 = []
    st2 = accumulate([structured], hist, events2)
    assert st2['n_updated'] == 1
    assert st2['skills']['C']['causal_coherence_score'] >= 0.75
    assert events2 and events2[0]['score_delta'] != 0
    tmp = COHERENCE_PATH.with_name(COHERENCE_PATH.stem + '_test_' + uuid.uuid4().hex + COHERENCE_PATH.suffix)
    tmp_jsonl = EVENTS_JSONL.with_name(EVENTS_JSONL.stem + '_test_' + uuid.uuid4().hex + EVENTS_JSONL.suffix)
    tmp_db = EVENTS_DB.with_name(EVENTS_DB.stem + '_test_' + uuid.uuid4().hex + EVENTS_DB.suffix)
    try:
        _atomic_write(tmp, st2)
        persist_events(events2, tmp_jsonl, tmp_db)
        assert json.loads(tmp.read_text(encoding='utf-8'))['n_updated'] == 1
        assert tmp_jsonl.exists()
        conn = sqlite3.connect(str(tmp_db), timeout=30)
        try:
            conn.execute('PRAGMA journal_mode=WAL')
            n = conn.execute('SELECT COUNT(*) FROM causal_events').fetchone()[0]
            assert n == 1
        finally:
            conn.close()
    finally:
        for p in (tmp, tmp_jsonl, tmp_db, tmp.with_suffix(tmp.suffix + '.lock'),
                  tmp_jsonl.with_suffix('.lock'), tmp_db.with_suffix('.lock')):
            Path(p).unlink(missing_ok=True)
        wal = Path(str(tmp_db) + '-wal')
        shm = Path(str(tmp_db) + '-shm')
        wal.unlink(missing_ok=True)
        shm.unlink(missing_ok=True)
    print('[causal-regret-minimizer] --self-test PASS A=%.3f B=%.3f' % (a, b))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description='Causal-critique epistemic regret minimizer')
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--run', action='store_true')
    args = ap.parse_args()
    if args.self_test:
        try:
            return _self_test()
        except Exception as exc:
            print('[causal-regret-minimizer] --self-test FAIL: %s' % exc)
            return 1
    try:
        state = run_live(RANKING_PATH, COHERENCE_PATH, EVENTS_JSONL, EVENTS_DB)
        slim = {k: state[k] for k in state if k != 'skills'}
        slim['n_skills'] = len(state.get('skills') or {})
        print(json.dumps(slim))
    except Exception as exc:
        print(json.dumps({'status': 'error', 'reason': str(exc)}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
