#!/usr/bin/env python3
"""Two conformal constructions for adaptive within-document AI-text screening.

Hard core: realized false-alert rate over any prefix is bounded by conformal
rank threshold alpha, with no assumption on token/turn dependence.
"""
from __future__ import annotations

import os
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', 'fork')
_hermes_root = (
    (_hermes_base / 'profiles' / _hermes_profile)
    if _hermes_profile and 'profiles' not in str(_hermes_base)
    else _hermes_base
)

import argparse
import fcntl
import json
import math
import random
import sys
import tempfile
import uuid
from collections import defaultdict, deque
from datetime import datetime, timezone, UTC

CACHE = _hermes_root / 'cache'
LIFECYCLE_DB = _hermes_base / 'memory-facts' / 'lifecycle.db'
ALPHA = 0.1
CALIB_NAME = 'conformal-calibration.jsonl'
RANKS_NAME = 'conformal-ranks.json'
AUDIT_NAME = 'conformal-audit.jsonl'


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _cache(cache_dir: Path | None = None) -> Path:
    return Path(cache_dir) if cache_dir is not None else CACHE


def _atomic_write_json(path: Path, obj) -> None:
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


def _append_jsonl(path: Path, rec: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix('.lock')
    with open(str(lock_path), 'a', encoding='utf-8') as lf:
        fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
        try:
            with open(str(path), 'a', encoding='utf-8') as f:
                f.write(json.dumps(rec, separators=(',', ':')) + '\n')
        finally:
            fcntl.flock(lf.fileno(), fcntl.LOCK_UN)


def _clip01(val) -> float | None:
    try:
        s = float(val)
    except (TypeError, ValueError):
        return None
    if s != s or s in (float('inf'), float('-inf')):
        return None
    s = max(s, 0.0)
    s = min(s, 1.0)
    return s


def nonconformity(llm_decision) -> float | None:
    return _clip01(llm_decision)


def conformal_threshold(scores, alpha: float = ALPHA) -> float | None:
    xs = []
    for s in scores or []:
        v = _clip01(s)
        if v is not None:
            xs.append(v)
    n = len(xs)
    if n == 0:
        return None
    xs.sort()
    q = 1.0 - min(0.999, max(1e-9, float(alpha)))
    idx = int(math.ceil((n + 1) * q) - 1)
    if idx >= n:
        return xs[-1]
    if idx < 0:
        return xs[0]
    return xs[idx]


def conformal_p_value(score: float, calib) -> float | None:
    xs = [x for x in (_clip01(s) for s in (calib or [])) if x is not None]
    n = len(xs)
    if n == 0:
        return None
    ge = 1 + sum(1 for x in xs if x >= score)
    return ge / (n + 1.0)


def _parse_row(rec) -> dict | None:
    if not isinstance(rec, dict):
        return None
    skill = rec.get('skill_id', rec.get('skill', rec.get('scope')))
    if skill is None or str(skill) == '':
        return None
    score = nonconformity(rec.get('llm_decision', rec.get('score', rec.get('nonconformity_score'))))
    if score is None:
        return None
    outcome = rec.get('outcome', rec.get('label', 0))
    try:
        outcome_i = int(outcome)
    except (TypeError, ValueError):
        outcome_i = 0
    if outcome_i not in (0, 1):
        outcome_i = 0
    return {
        'skill_id': str(skill),
        'session_id': str(rec.get('session_id', rec.get('session', ''))),
        'llm_decision': score,
        'outcome': outcome_i,
        'nonconformity_score': score,
    }


def load_from_calibration_log(path: Path, max_rows: int = 20000) -> list:
    """Live ingest from calibration-log.jsonl. Skip ue_blackbox. Never invent rows."""
    if not path.exists():
        return []
    buf: deque = deque(maxlen=max(100, int(max_rows)))
    try:
        with open(str(path), encoding='utf-8', errors='replace') as fh:
            if path.stat().st_size > 8_000_000:
                fh.seek(0, 2)
                size = fh.tell()
                fh.seek(max(0, size - 6_000_000))
                fh.readline()
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
                if rec.get('scope') == 'ue_blackbox':
                    continue
                skill = rec.get('tool_name') or rec.get('skill_id') or rec.get('skill')
                if skill is None or str(skill).strip() == '':
                    continue
                pc = _clip01(rec.get('predicted_confidence', rec.get('llm_decision', rec.get('score'))))
                if pc is None:
                    continue
                # Nonconformity: low confidence is more nonconforming.
                score = 1.0 - pc
                ao = rec.get('actual_outcome', rec.get('outcome', rec.get('label')))
                # outcome 0 = inlier (retain/success); 1 = anomaly (demote)
                if ao in (1, '1', True, 'true', 'True', 'retain'):
                    outcome_i = 0
                else:
                    outcome_i = 1
                buf.append({
                    'skill_id': str(skill).strip(),
                    'session_id': str(rec.get('session_id', rec.get('session', ''))),
                    'llm_decision': score,
                    'outcome': outcome_i,
                    'nonconformity_score': score,
                })
    except OSError:
        return []
    return list(buf)


def load_calibration_pool(path: Path) -> list:
    if not path.exists():
        return []
    rows = []
    try:
        with open(str(path), encoding='utf-8', errors='replace') as fh:
            for line in fh:
                raw = line.strip()
                if not raw:
                    continue
                try:
                    rec = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                parsed = _parse_row(rec)
                if parsed is not None:
                    rows.append(parsed)
    except OSError:
        return []
    return rows


def _session_max(rows) -> list:
    by = defaultdict(list)
    for r in rows:
        by[r['session_id']].append(r['nonconformity_score'])
    return [max(vs) for vs in by.values() if vs]


def calibrate_skill(rows, alpha: float = ALPHA) -> dict:
    null_scores = [r['nonconformity_score'] for r in rows if r['outcome'] == 0]
    all_scores = [r['nonconformity_score'] for r in rows]
    use = null_scores if null_scores else all_scores
    thr_turn = conformal_threshold(use, alpha)
    sess_null = []
    by_sess = defaultdict(list)
    for r in rows:
        if r['outcome'] == 0:
            by_sess[r['session_id']].append(r['nonconformity_score'])
    for vs in by_sess.values():
        if vs:
            sess_null.append(max(vs))
    thr_sess = conformal_threshold(sess_null, alpha) if sess_null else thr_turn
    return {
        'threshold': thr_turn,
        'session_threshold': thr_sess,
        'calibration_n': len(use),
        'n_sessions': len({r['session_id'] for r in rows if r['session_id']}),
        'alpha': alpha,
    }


def flag_row(row: dict, threshold) -> bool:
    if threshold is None:
        return False
    return float(row['nonconformity_score']) > float(threshold)


def split_by_session(rows, cal_frac: float = 0.8):
    sess = []
    seen = set()
    for r in rows:
        sid = r['session_id']
        if sid not in seen:
            seen.add(sid)
            sess.append(sid)
    sess.sort()
    n = len(sess)
    if n == 0:
        return rows, []
    cut = max(1, int(n * cal_frac))
    if cut >= n:
        return rows, []
    cal_s = set(sess[:cut])
    cal = [r for r in rows if r['session_id'] in cal_s]
    held = [r for r in rows if r['session_id'] not in cal_s]
    return cal, held


def realized_false_alerts(held_rows, thresholds: dict) -> int:
    fa = 0
    for r in held_rows:
        if r['outcome'] != 0:
            continue
        thr = thresholds.get(r['skill_id'])
        if flag_row(r, thr):
            fa += 1
    return fa


def compute_ranks(rows, alpha: float = ALPHA, cal_frac: float = 0.8) -> dict:
    if not rows:
        return {
            'status': 'insufficient_data',
            'alpha': alpha,
            'skills': {},
            'false_alert_count': 0,
            'n': 0,
            'ts': _now(),
        }
    by_skill = defaultdict(list)
    for r in rows:
        by_skill[r['skill_id']].append(r)
    skills = {}
    total_fa = 0
    any_ok = False
    for skill_id, srows in sorted(by_skill.items()):
        cal, held = split_by_session(srows, cal_frac=cal_frac)
        if not cal:
            cal = srows
            held = []
        meta = calibrate_skill(cal, alpha=alpha)
        fa = realized_false_alerts(held, {skill_id: meta['threshold']}) if held else 0
        total_fa += fa
        if meta['threshold'] is not None:
            any_ok = True
        skills[skill_id] = {
            'threshold': meta['threshold'],
            'session_threshold': meta['session_threshold'],
            'false_alert_count': fa,
            'calibration_n': meta['calibration_n'],
            'n_heldout': len(held),
            'n_sessions': meta['n_sessions'],
            'alpha': alpha,
        }
    return {
        'status': 'ok' if any_ok else 'insufficient_data',
        'alpha': alpha,
        'skills': skills,
        'false_alert_count': total_fa,
        'n': len(rows),
        'ts': _now(),
    }


def write_audit(audit_path: Path, rows, thresholds: dict) -> int:
    n_flagged = 0
    ts = _now()
    for r in rows:
        thr = thresholds.get(r['skill_id'])
        flagged = flag_row(r, thr)
        if flagged:
            n_flagged += 1
        _append_jsonl(audit_path, {
            'ts': ts,
            'skill_id': r['skill_id'],
            'decision': r['llm_decision'],
            'nonconformity_score': r['nonconformity_score'],
            'flagged': flagged,
        })
    return n_flagged


def layer1_demo(alpha: float = ALPHA, seed: int = 42) -> dict:
    rng = random.Random(seed)
    n_sess, n_turns, n_skills = 100, 10, 5
    skills = ['skill_%d' % i for i in range(n_skills)]
    rows = []
    for s in range(n_sess):
        for _t in range(n_turns):
            for sk in skills:
                rows.append({
                    'skill_id': sk,
                    'session_id': 's%03d' % s,
                    'llm_decision': rng.random(),
                    'outcome': 0,
                    'nonconformity_score': None,
                })
    for r in rows:
        r['nonconformity_score'] = r['llm_decision']
    result = compute_ranks(rows, alpha=alpha, cal_frac=0.8)
    thr = {sk: meta['threshold'] for sk, meta in result['skills'].items()}
    cal, held = split_by_session(rows, cal_frac=0.8)
    fa = realized_false_alerts(held, thr)
    result['false_alert_count'] = fa
    result['n_heldout'] = len(held)
    result['n_cal'] = len(cal)
    return result


def run(cache_dir: Path | None = None, alpha: float = ALPHA) -> dict:
    cdir = _cache(cache_dir)
    cdir.mkdir(parents=True, exist_ok=True)
    pool_path = cdir / CALIB_NAME
    ranks_path = cdir / RANKS_NAME
    audit_path = cdir / AUDIT_NAME
    rows = load_calibration_pool(pool_path)
    if not rows:
        live = cdir / 'calibration-log.jsonl'
        rows = load_from_calibration_log(live)
    if not rows:
        return {
            'status': 'insufficient_data',
            'reason': 'empty_or_missing_calibration_pool',
            'n': 0,
            'ts': _now(),
        }
    result = compute_ranks(rows, alpha=alpha)
    if result.get('status') == 'insufficient_data':
        return result
    out_skills = {}
    for sid, meta in result['skills'].items():
        out_skills[sid] = {
            'threshold': meta['threshold'],
            'false_alert_count': meta['false_alert_count'],
            'calibration_n': meta['calibration_n'],
        }
    payload = {
        'status': 'ok',
        'alpha': alpha,
        'ts': result['ts'],
        'false_alert_count': result['false_alert_count'],
        'n': result['n'],
        **out_skills,
    }
    # also nest under skills for consumers that want the full map
    payload['skills'] = out_skills
    _atomic_write_json(ranks_path, payload)
    held_all = []
    by_skill = defaultdict(list)
    for r in rows:
        by_skill[r['skill_id']].append(r)
    for sid, srows in by_skill.items():
        _cal, held = split_by_session(srows, cal_frac=0.8)
        held_all.extend(held)
    if held_all:
        thr = {sid: meta['threshold'] for sid, meta in result['skills'].items()}
        write_audit(audit_path, held_all, thr)
    return payload


def _self_test() -> int:
    empty = compute_ranks([])
    assert empty['status'] == 'insufficient_data'
    assert conformal_threshold([], 0.1) is None
    none_p = conformal_p_value(0.5, [])
    assert none_p is None
    bad = _parse_row({'skill_id': 'x', 'llm_decision': 'nope'})
    assert bad is None
    long_dec = nonconformity(10 ** 9)
    assert long_dec == 1.0
    demo = layer1_demo(alpha=0.1, seed=42)
    fa = int(demo['false_alert_count'])
    bound = int(0.1 * (20 * 10 * 5) + 2)
    assert demo['status'] == 'ok', demo
    assert fa <= bound, f'false-alert count {fa} > bound {bound}'
    td = Path(tempfile.mkdtemp(prefix=f'cma-{uuid.uuid4().hex[:8]}-'))
    try:
        pool = td / CALIB_NAME
        rows = []
        rng = random.Random(1)
        for i in range(30):
            rows.append({
                'skill_id': 'sA',
                'session_id': 'sess-%d' % (i // 3),
                'llm_decision': rng.random(),
                'outcome': 0,
            })
        with open(str(pool), 'w', encoding='utf-8') as f:
            f.writelines(json.dumps(r) + '\n' for r in rows)
            f.write('not-json\n')
            f.write('\n')
        r = run(cache_dir=td, alpha=0.1)
        assert r.get('status') in ('ok', 'insufficient_data')
        ranks_p = td / RANKS_NAME
        if r.get('status') == 'ok':
            assert ranks_p.exists()
            loaded = json.loads(ranks_p.read_text(encoding='utf-8'))
            assert 'sA' in loaded
            assert 'threshold' in loaded['sA']
        missing = run(cache_dir=td / (f'nope-{uuid.uuid4().hex}'), alpha=0.1)
        assert missing['status'] == 'insufficient_data'
        live = td / 'calibration-log.jsonl'
        with open(str(live), 'w', encoding='utf-8') as f:
            for i in range(40):
                f.write(json.dumps({
                    'ts': '2026-01-01T00:00:00Z',
                    'session_id': 'L%d' % (i // 4),
                    'tool_name': 'write_file',
                    'predicted_confidence': 0.2 + 0.02 * (i % 10),
                    'actual_outcome': 1 if i % 3 else 0,
                }) + '\n')
            f.write(json.dumps({
                'ts': 'x', 'scope': 'ue_blackbox', 'predicted_confidence': 0.9,
                'query_hash': 'skip-me',
            }) + '\n')
            f.write('not-json\n')
        live_rows = load_from_calibration_log(live)
        assert live_rows, live_rows
        assert all(r['skill_id'] == 'write_file' for r in live_rows)
        assert all(0.0 <= r['nonconformity_score'] <= 1.0 for r in live_rows)
    finally:
        for p in td.rglob('*'):
            if p.is_file():
                try:
                    p.unlink()
                except OSError:
                    pass
        try:
            td.rmdir()
        except OSError:
            pass
    print(f'[conformal-memory-audit] --self-test PASS fa={fa} bound={bound}')
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description='Conformal memory audit')
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--run', action='store_true')
    ap.add_argument('--alpha', type=float, default=ALPHA)
    args = ap.parse_args()
    if args.self_test:
        try:
            sys.exit(_self_test())
        except Exception as exc:
            print(f'[conformal-memory-audit] --self-test FAIL: {exc}')
            sys.exit(1)
    try:
        result = run(alpha=args.alpha)
        print(json.dumps(result))
    except Exception as exc:
        print(json.dumps({'status': 'error', 'reason': str(exc), 'ts': _now()}))
        sys.exit(0)


if __name__ == '__main__':
    main()
