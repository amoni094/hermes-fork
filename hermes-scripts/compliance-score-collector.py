#!/usr/bin/env python3
"""Compliance score collector.

Scans tool_review_log and appends (accuracy, explainability, robustness)
triples to compliance-scores.jsonl. Also exposes on_post_tool_call for the
companion hook. Stdlib only. Fail-open.
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
import sqlite3
import sys
import tempfile
import uuid
from datetime import datetime, timezone, UTC

CACHE = _hermes_root / 'cache'
OUT_PATH = CACHE / 'compliance-scores.jsonl'
STATE_PATH = CACHE / 'compliance-score-collector-state.json'
LIFECYCLE_DB = _hermes_base / 'memory-facts' / 'lifecycle.db'
DEFAULT_ROBUSTNESS = 0.8


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
        with open(str(path), 'a', encoding='utf-8') as f:
            f.write(json.dumps(record, default=str) + '\n')


def _connect(db_path: Path):
    conn = sqlite3.connect(str(db_path), timeout=30)
    conn.execute('PRAGMA journal_mode=WAL')
    return conn


def score_from_result(result, tool_name: str = '', session_id: str = '') -> dict:
    accuracy = 1.0 if result is not None else 0.0
    explainability = 0.5
    if isinstance(result, dict):
        if any(k in result for k in ('reasoning', 'explanation', 'reason', 'explain')):
            explainability = 1.0
    elif isinstance(result, str):
        low = result.lower()
        if 'because' in low or 'reason' in low or 'explain' in low:
            explainability = 1.0
    rec = {
        'ts': _now(),
        'tool_name': tool_name or '',
        'accuracy': float(accuracy),
        'explainability': float(explainability),
        'robustness': float(DEFAULT_ROBUSTNESS),
        'session_id': session_id or '',
    }
    return rec


_POS_OUTCOMES = {'ok', 'success', 'pass', 'true', '1'}
_NEG_OUTCOMES = {'fail', 'error', 'failed', 'false', '0', 'timeout'}


def _clip01(x: float) -> float:
    if x != x:
        return 0.0
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return float(x)


def _label_from_outcome(outcome: str):
    o = str(outcome or '').strip().lower()
    if o in _POS_OUTCOMES:
        return 1.0
    if o in _NEG_OUTCOMES:
        return 0.0
    return None


def pav_isotonic(xs: list[float], ys: list[float]) -> list[float]:
    """Pool Adjacent Violators isotonic regression (nondecreasing in x)."""
    n = len(xs)
    if n == 0:
        return []
    order = sorted(range(n), key=lambda i: (xs[i], i))
    blocks = []
    for i in order:
        blocks.append({'w': 1.0, 's': float(ys[i]), 'idx': [i]})
        while len(blocks) >= 2:
            a, b = blocks[-2], blocks[-1]
            mean_a = a['s'] / a['w']
            mean_b = b['s'] / b['w']
            if mean_a <= mean_b + 1e-15:
                break
            blocks[-2] = {
                'w': a['w'] + b['w'],
                's': a['s'] + b['s'],
                'idx': a['idx'] + b['idx'],
            }
            blocks.pop()
    fitted = [0.0] * n
    for blk in blocks:
        v = _clip01(blk['s'] / blk['w'])
        for i in blk['idx']:
            fitted[i] = v
    return fitted


def youden_threshold(scores: list[float], labels: list[float]) -> float | None:
    """Maximize TPR-FPR on unique score thresholds. None if no binary labels."""
    pairs = [(s, l) for s, l in zip(scores, labels) if l in (0.0, 1.0)]
    if len(pairs) < 4:
        return None
    n_pos = sum(1 for _, l in pairs if l == 1.0)
    n_neg = len(pairs) - n_pos
    if n_pos == 0 or n_neg == 0:
        return None
    best_t, best_j = 0.5, -1.0
    for t in sorted({p[0] for p in pairs}):
        tp = sum(1 for s, l in pairs if s >= t and l == 1.0)
        fp = sum(1 for s, l in pairs if s >= t and l == 0.0)
        tpr = tp / n_pos
        fpr = fp / n_neg
        j = tpr - fpr
        if j > best_j:
            best_j, best_t = j, t
    return float(best_t)


def score_from_review_row(row: dict) -> dict:
    score = row.get('score')
    outcome = str(row.get('outcome') or '')
    label = _label_from_outcome(outcome)
    try:
        raw = float(score) if score is not None else None
    except (TypeError, ValueError):
        raw = None
    if raw is not None:
        raw = _clip01(raw)
    if label is not None:
        accuracy = float(label)
        uncalibrated = raw if raw is not None else float(label)
    elif raw is not None:
        accuracy = raw
        uncalibrated = raw
    else:
        accuracy = 0.0
        uncalibrated = 0.0
    notes = row.get('notes')
    explainability = 1.0 if notes else 0.5
    return {
        'ts': row.get('ts') or _now(),
        'tool_name': row.get('tool_name') or '',
        'accuracy': float(accuracy),
        'uncalibrated_accuracy': float(uncalibrated),
        'label': label,
        'explainability': float(explainability),
        'robustness': float(DEFAULT_ROBUSTNESS),
        'session_id': row.get('session_id') or '',
        'source': 'tool_review_log',
        'review_id': row.get('id'),
        'outcome': outcome,
    }


def on_post_tool_call(tool_name: str = '', args=None, result=None, session_id: str = '',
                      out_path: Path | None = None, **kwargs):
    try:
        rec = score_from_result(result, tool_name=tool_name, session_id=str(session_id or ''))
        _append_jsonl(out_path or OUT_PATH, rec)
        return rec
    except Exception:
        return None


def collect(db_path: Path, out_path: Path, state_path: Path, limit: int = 200) -> dict:
    if not db_path.exists():
        return {'status': 'insufficient_data', 'reason': 'missing_db', 'written': 0}
    state = {'last_id': 0}
    if state_path.exists():
        try:
            obj = json.loads(state_path.read_text(encoding='utf-8'))
            if isinstance(obj, dict):
                state['last_id'] = int(obj.get('last_id') or 0)
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            state = {'last_id': 0}
    conn = None
    written = 0
    last_id = state['last_id']
    try:
        conn = _connect(db_path)
        tabs = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if 'tool_review_log' not in tabs:
            return {'status': 'insufficient_data', 'reason': 'no_table', 'written': 0}
        rows = conn.execute(
            'SELECT id, ts, session_id, tool_name, latency_ms, outcome, score, notes '
            'FROM tool_review_log WHERE id > ? ORDER BY id LIMIT ?',
            (last_id, int(limit)),
        ).fetchall()
        if not rows:
            return {'status': 'insufficient_data', 'reason': 'no_new_rows', 'written': 0, 'last_id': last_id}
        cols = ['id', 'ts', 'session_id', 'tool_name', 'latency_ms', 'outcome', 'score', 'notes']
        batch = []
        for tup in rows:
            rec = score_from_review_row(dict(zip(cols, tup)))
            batch.append(rec)
            last_id = int(tup[0])
        xs = [float(r.get('uncalibrated_accuracy') or 0.0) for r in batch]
        ys = []
        for r in batch:
            lab = r.get('label')
            ys.append(float(lab) if lab is not None else float(r.get('uncalibrated_accuracy') or 0.0))
        fitted = pav_isotonic(xs, ys)
        labels = [float(r['label']) for r in batch if r.get('label') is not None]
        scores_l = [
            float(r['uncalibrated_accuracy'])
            for r in batch if r.get('label') is not None
        ]
        thr = youden_threshold(scores_l, labels) if labels else None
        for rec, fit in zip(batch, fitted):
            rec['accuracy'] = float(fit)
            rec['calibrated'] = True
            if thr is not None:
                rec['threshold'] = float(thr)
                rec['threshold_pred'] = 1.0 if rec['uncalibrated_accuracy'] >= thr else 0.0
            _append_jsonl(out_path, rec)
            written += 1
        cal_path = (out_path.parent if out_path is not None else CACHE) / 'compliance-calibration.json'
        try:
            mean_raw = sum(xs) / len(xs) if xs else 0.0
            mean_fit = sum(fitted) / len(fitted) if fitted else 0.0
            mean_label = (sum(labels) / len(labels)) if labels else None
            _atomic_write(cal_path, {
                'ts': _now(),
                'n': len(batch),
                'mean_uncalibrated': mean_raw,
                'mean_calibrated': mean_fit,
                'mean_label': mean_label,
                'youden_threshold': thr,
                'theorem': 'PAV isotonic calibration; Youden threshold on outcome labels',
            })
        except OSError:
            pass
        _atomic_write(state_path, {'last_id': last_id, 'ts': _now()})
        return {'status': 'ok', 'written': written, 'last_id': last_id, 'mean_calibrated': (sum(fitted) / len(fitted) if fitted else None)}
    except sqlite3.Error as exc:
        return {'status': 'error', 'reason': str(exc), 'written': written}
    finally:
        if conn is not None:
            conn.close()


def _self_test() -> int:
    td = Path(tempfile.mkdtemp(prefix='csc-'))
    try:
        out = td / ('compliance-scores_test_' + uuid.uuid4().hex + '.jsonl')
        rec = on_post_tool_call(
            tool_name='read_file',
            result={'ok': True, 'reasoning': 'file existed'},
            session_id='sess-test',
            out_path=out,
        )
        assert rec is not None
        assert rec['accuracy'] == 1.0
        assert rec['explainability'] == 1.0
        lines = out.read_text(encoding='utf-8').splitlines()
        assert len(lines) == 1, lines
        parsed = json.loads(lines[0])
        assert parsed['tool_name'] == 'read_file'
        none_rec = score_from_result(None, tool_name='x')
        assert none_rec['accuracy'] == 0.0
        labeled = score_from_review_row({'outcome': 'ok', 'score': 0.2, 'notes': 'because'})
        assert labeled['label'] == 1.0
        assert labeled['accuracy'] == 1.0
        assert labeled['uncalibrated_accuracy'] == 0.2
        fit = pav_isotonic([0.1, 0.4, 0.9], [0.0, 1.0, 1.0])
        assert fit[0] <= fit[1] <= fit[2] + 1e-12
        db = td / 'lc.db'
        conn = sqlite3.connect(str(db), timeout=30)
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute(
            'CREATE TABLE tool_review_log (id INTEGER PRIMARY KEY, ts TEXT, session_id TEXT, '
            'tool_name TEXT, latency_ms REAL, outcome TEXT, score REAL, notes TEXT)'
        )
        conn.execute(
            'INSERT INTO tool_review_log (ts, session_id, tool_name, latency_ms, outcome, score, notes) '
            'VALUES (?,?,?,?,?,?,?)',
            (_now(), 's1', 'terminal', 12.0, 'ok', 1.0, 'because it worked'),
        )
        conn.commit()
        conn.close()
        state = td / 'state.json'
        r = collect(db, out, state, limit=50)
        assert r.get('written') == 1, r
        missing = collect(td / 'nope.db', out, state)
        assert missing.get('status') == 'insufficient_data'
    finally:
        import shutil
        shutil.rmtree(td, ignore_errors=True)
    print('[compliance-score-collector] --self-test PASS')
    return 0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--run', action='store_true')
    ap.add_argument('--db', default=str(LIFECYCLE_DB))
    ap.add_argument('--out', default=str(OUT_PATH))
    ap.add_argument('--state', default=str(STATE_PATH))
    ap.add_argument('--limit', type=int, default=200)
    args = ap.parse_args()
    if args.self_test:
        try:
            sys.exit(_self_test())
        except Exception as exc:
            print(f'[compliance-score-collector] --self-test FAIL: {exc}')
            sys.exit(1)
    try:
        result = collect(Path(args.db), Path(args.out), Path(args.state), limit=int(args.limit))
        print(json.dumps(result, indent=2, default=str))
        sys.exit(0)
    except Exception as exc:
        print(json.dumps({'status': 'error', 'reason': str(exc)}))
        sys.exit(0)


if __name__ == '__main__':
    main()
