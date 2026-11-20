#!/usr/bin/env python3
"""Online conformal prediction intervals for skill success.

Rolling calibration buffer of (skill_id, outcome); quantile intervals
with finite-sample correction. Also bagged bootstrap-of-means intervals
absorbed from skill-calibrated-posterior.py.

Writes skill_confidence_intervals.json and routing-calibrated-posterior.json.
"""
from __future__ import annotations
import argparse, json, os, random, sqlite3, sys, tempfile, uuid
from collections import defaultdict, deque
from datetime import datetime, timezone, UTC
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', 'fork')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base
CACHE = _hermes_root / 'cache'
OUT_PATH = CACHE / 'skill_confidence_intervals.json'
POSTERIOR_OUT = CACHE / 'routing-calibrated-posterior.json'
DB_PATH = CACHE / 'skill_calibration.db'


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _atomic_write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(obj, indent=2) + '\n', encoding='utf-8')
    os.replace(str(tmp), str(path))


def _true_home(base: Path) -> Path:
    q = Path(base)
    if q.name != '.hermes' and q.parent.name == 'profiles':
        return q.parent.parent
    return q


def _lifecycle_db() -> Path:
    return _true_home(_hermes_base) / 'memory-facts' / 'lifecycle.db'


def _temp_out(prefix: str) -> Path:
    return Path(tempfile.gettempdir()) / (f'{prefix}-{uuid.uuid4().hex}.json')


def conformal_quantile(residuals, alpha, n=None):
    if not residuals:
        return None
    n = n if n is not None else len(residuals)
    level = min(1.0, (1 - alpha) * (1 + 1.0 / max(n, 1)))
    ys = sorted(residuals)
    idx = min(len(ys) - 1, max(0, int(level * len(ys)) - (0 if level >= 1 else 1)))
    idx = max(0, min(len(ys) - 1, idx))
    return float(ys[idx])


def intervals_for(calls, window=200, alpha=0.1):
    buf = deque(maxlen=window)
    last = {}
    for skill, y in calls:
        buf.append((skill, float(y)))
        by = defaultdict(list)
        for s, v in buf:
            by[s].append(v)
        if skill in by and len(by[skill]) >= 5:
            xs = by[skill]
            mean = sum(xs) / len(xs)
            resid = [abs(v - mean) for v in xs]
            q = conformal_quantile(resid, alpha, n=len(xs))
            if q is None:
                continue
            last[skill] = {
                'n': len(xs),
                'mean': mean,
                'lo': max(0.0, mean - q),
                'hi': min(1.0, mean + q),
                'width': min(1.0, mean + q) - max(0.0, mean - q),
            }
    return last


def empirical_coverage(calls, window=100, alpha=0.1, hold=100):
    cal, test = calls[:window], calls[window:window + hold]
    iv = intervals_for(cal, window=window, alpha=alpha)
    hits = tot = 0
    by = defaultdict(list)
    for s, y in test:
        by[s].append(y)
    for s, ys in by.items():
        if s not in iv:
            continue
        rate = sum(ys) / len(ys)
        tot += 1
        if iv[s]['lo'] - 1e-9 <= rate <= iv[s]['hi'] + 1e-9:
            hits += 1
    if tot == 0:
        return None, 0
    return (hits / tot), tot


def _quantile(xs, q):
    if not xs:
        return None
    ys = sorted(xs)
    i = min(len(ys) - 1, max(0, int(q * (len(ys) - 1))))
    return float(ys[i])


def bagged_intervals(outcomes, B=100, alpha=0.1, rng=None):
    rng = rng or random.Random(0)
    out = {}
    lo_q, hi_q = alpha / 2, 1 - alpha / 2
    for skill, ys in outcomes.items():
        n = len(ys)
        if n == 0:
            continue
        means = []
        for _ in range(B):
            s = sum(ys[rng.randrange(n)] for _ in range(n))
            means.append(s / n)
        lo = _quantile(means, lo_q)
        hi = _quantile(means, hi_q)
        if lo is None or hi is None:
            continue
        out[skill] = {
            'n': n,
            'mean': sum(ys) / n,
            'lo': lo,
            'hi': hi,
            'width': hi - lo,
        }
    return out


def load_outcomes():
    by = defaultdict(list)
    db = _lifecycle_db()
    try:
        if not db.exists():
            return {}
        conn = sqlite3.connect('file:' + str(db) + '?mode=ro', uri=True, timeout=30)
        try:
            conn.execute('PRAGMA journal_mode=WAL')
            tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            for t in ('skill_outcomes', 'routing_events', 'skill_calls'):
                if t not in tables:
                    continue
                cols = {r[1] for r in conn.execute('PRAGMA table_info(' + t + ')')}
                sk = 'skill' if 'skill' in cols else ('skill_id' if 'skill_id' in cols else None)
                suc = 'success' if 'success' in cols else ('outcome' if 'outcome' in cols else None)
                if sk and suc:
                    for skill, val in conn.execute('SELECT ' + sk + ', ' + suc + ' FROM ' + t + ' LIMIT 5000'):
                        by[str(skill)].append(1 if val in (1, True, '1', 'success', 'ok') else 0)
            if not by and 'anytime_eval_log' in tables:
                for skill, val in conn.execute('SELECT skill_id, eval_score FROM anytime_eval_log ORDER BY id DESC LIMIT 8000'):
                    if not skill:
                        continue
                    try:
                        y = float(val)
                    except (TypeError, ValueError):
                        continue
                    y = 1.0 if y > 1.0 else (max(y, 0.0))
                    by[str(skill)].append(y)
            if not by and 'tool_review_log' in tables:
                for tool, outcome, score in conn.execute('SELECT tool_name, outcome, score FROM tool_review_log ORDER BY id DESC LIMIT 8000'):
                    if not tool:
                        continue
                    if score is not None:
                        try:
                            y = float(score)
                            y = 1.0 if y > 1.0 else (max(y, 0.0))
                        except (TypeError, ValueError):
                            y = 1.0 if str(outcome).lower() in ('ok', 'success', '1', 'true') else 0.0
                    else:
                        y = 1.0 if str(outcome).lower() in ('ok', 'success', '1', 'true') else 0.0
                    by[str(tool)].append(y)
        finally:
            conn.close()
    except Exception:
        return {}
    return dict(by)


def _write_skill_db(payload, db_path):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), timeout=30)
    conn.execute('PRAGMA journal_mode=WAL')
    try:
        conn.execute('CREATE TABLE IF NOT EXISTS skill_conf (skill TEXT, n INT, lo REAL, hi REAL, ts TEXT)')
        for sk, rec in (payload.get('skills') or {}).items():
            conn.execute('INSERT INTO skill_conf VALUES (?,?,?,?,?)',
                         (sk, rec['n'], rec['lo'], rec['hi'], payload['ts']))
        conn.commit()
    finally:
        conn.close()


def run(window=200, alpha=0.1, B=100, out_path=None, posterior_path=None, db_path=None, outcomes=None, calls=None):
    outcomes = dict(outcomes) if outcomes is not None else load_outcomes()
    if calls is None:
        calls = []
        for sk, ys in outcomes.items():
            for y in ys:
                calls.append((sk, y))
    if not calls and not outcomes:
        payload = {
            'ts': _now(),
            'window': window,
            'alpha': alpha,
            'B': B,
            'skills': {},
            'n': 0,
            'status': 'insufficient_data',
            'synthetic': False,
        }
        return payload
    skills = intervals_for(calls, window=window, alpha=alpha)
    bagged = bagged_intervals(outcomes, B=B, alpha=alpha, rng=random.Random(1)) if outcomes else {}
    payload = {
        'ts': _now(),
        'window': window,
        'alpha': alpha,
        'B': B,
        'skills': skills,
        'bagged': bagged,
        'n': len(calls),
        'status': 'ok' if skills or bagged else 'insufficient_data',
        'synthetic': False,
    }
    dest = out_path or OUT_PATH
    post = posterior_path or POSTERIOR_OUT
    if payload['status'] != 'insufficient_data':
        _atomic_write(dest, payload)
        alias = {
            'ts': payload['ts'],
            'alpha': alpha,
            'B': B,
            'synthetic': False,
            'skills': bagged or skills,
            'status': payload['status'],
        }
        _atomic_write(post, alias)
        try:
            _write_skill_db(payload if skills else {'ts': payload['ts'], 'skills': bagged}, db_path or DB_PATH)
        except Exception:
            pass
    return payload


def _self_test() -> int:
    assert conformal_quantile([], 0.1) is None
    cov, tot = empirical_coverage([], window=10, hold=10)
    assert cov is None and tot == 0
    empty = run(outcomes={}, calls=[], out_path=_temp_out('sk-empty'))
    assert empty['status'] == 'insufficient_data'
    rng = random.Random(0)
    ok = 0
    for trial in range(50):
        calls = []
        for i in range(300):
            p = 0.7 if (i % 4) else 0.55
            calls.append(('s%d' % (i % 4), 1 if rng.random() < p else 0))
        cov, tot = empirical_coverage(calls, window=100, alpha=0.1, hold=100)
        if tot and cov is not None and 0.70 <= cov <= 1.0:
            ok += 1
    assert ok >= 35, 'coverage trials ok=%d/50' % ok
    calls = [('s%d' % (i % 3), 1 if rng.random() < 0.65 else 0) for i in range(400)]
    iv100 = intervals_for(calls[:100], window=100)
    iv200 = intervals_for(calls[:200], window=200)
    w100 = sum(v['width'] for v in iv100.values()) / max(1, len(iv100))
    w200 = sum(v['width'] for v in iv200.values()) / max(1, len(iv200))
    assert w200 <= w100 * 1.05 + 1e-9, f'width 100={w100} 200={w200}'
    outcomes = {}
    for k in range(5):
        p = 0.4 + 0.1 * k
        outcomes['s%d' % k] = [1 if rng.random() < p else 0 for _ in range(100)]
    hits = 0
    for seed in (1, 2):
        iv = bagged_intervals(outcomes, B=100, alpha=0.1, rng=random.Random(seed))
        for sk, emp in outcomes.items():
            emp_mean = sum(emp) / len(emp)
            if iv[sk]['lo'] - 1e-9 <= emp_mean <= iv[sk]['hi'] + 1e-9:
                hits += 1
    assert hits >= 9, 'coverage hits=%d/10' % hits
    tmp = _temp_out('skill-conf')
    post = _temp_out('posterior')
    db_tmp = Path(tempfile.gettempdir()) / (f'skill-cal-{uuid.uuid4().hex}.db')
    r = run(outcomes=outcomes, out_path=tmp, posterior_path=post, db_path=db_tmp, B=50)
    assert r['status'] == 'ok'
    assert tmp.exists() and post.exists()
    try:
        tmp.unlink(missing_ok=True)
        post.unlink(missing_ok=True)
        db_tmp.unlink(missing_ok=True)
    except OSError:
        pass
    print('[skill_confidence_calibration] --self-test PASS')
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--window', type=int, default=200)
    ap.add_argument('--alpha', type=float, default=0.1)
    ap.add_argument('--B', type=int, default=100)
    args = ap.parse_args()
    if args.self_test:
        try:
            sys.exit(_self_test())
        except Exception as exc:
            print(f'[skill_confidence_calibration] --self-test FAIL: {exc}')
            sys.exit(1)
    try:
        payload = run(window=args.window, alpha=args.alpha, B=args.B)
        {k: payload[k] for k in payload if k not in ('bagged',)}
        print(json.dumps({'status': payload.get('status'), 'n': payload.get('n'), 'n_skills': len(payload.get('skills') or {})}))
    except Exception:
        pass


if __name__ == '__main__':
    main()
