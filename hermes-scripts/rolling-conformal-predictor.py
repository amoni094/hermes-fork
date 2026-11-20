#!/usr/bin/env python3
"""Rolling-window conformal prediction for sequential eval scores.

Bare cron run ingests the last W scores from calibration-log / eval-scores
(skipping scope==ue_blackbox), writes rolling-conformal-state.json, persists
rolling-calibration.db, and reports empirical_coverage_rate.

Also absorbs Wasserstein-robust expansion (--mode wasserstein).
"""
from __future__ import annotations
import argparse, fcntl, json, math, os, random, sqlite3, sys, tempfile, uuid
from datetime import datetime, timezone, UTC
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', 'fork')
if _hermes_base.name != '.hermes' and _hermes_base.parent.name == 'profiles':
    _hermes_base = _hermes_base.parent.parent
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base
CACHE = _hermes_root / 'cache'

def _now() -> str:
    return datetime.now(UTC).isoformat()

def _atomic_write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(path.suffix + '.lock') if path.suffix else path.with_name(path.name + '.lock')
    tmp = path.with_name(path.name + '.tmp')
    payload = json.dumps(obj, indent=2) + '\n'
    with open(str(lock_path), 'a', encoding='utf-8') as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        try:
            tmp.write_text(payload, encoding='utf-8')
            os.replace(str(tmp), str(path))
        finally:
            fcntl.flock(lf, fcntl.LOCK_UN)

def _temp_out(prefix: str) -> Path:
    return Path(tempfile.gettempdir()) / (f'{prefix}-{uuid.uuid4().hex}.json')

OUT_PATH = CACHE / 'rolling-conformal-state.json'
WASSERSTEIN_OUT = CACHE / 'wasserstein-calibration.json'
DB_PATH = CACHE / 'rolling-calibration.db'
W = 50
ALPHA = 0.1
MAX_LOAD = 2000


def interval(window, alpha=ALPHA):
    ys = sorted(float(x) for x in window)
    n = len(ys)
    if n == 0:
        return None, None
    lo_rank = math.floor(alpha / 2.0 * (n + 1))
    hi_rank = math.ceil((1.0 - alpha / 2.0) * (n + 1)) - 1
    lo_rank = min(n - 1, max(0, lo_rank))
    hi_rank = min(n - 1, max(0, hi_rank))
    return ys[lo_rank], ys[hi_rank]


def epsilon_radius(n, alpha=ALPHA):
    n = int(n)
    if n <= 0:
        return None
    alpha = min(0.999, max(1e-9, float(alpha)))
    return math.sqrt(2.0 * math.log(1.0 / alpha) / n)


def interval_from_cal(cal, alpha=ALPHA):
    return interval(cal, alpha=alpha)


def calibrate_wasserstein(calibration, alpha=ALPHA):
    cal = []
    for x in calibration or []:
        try:
            cal.append(float(x))
        except (TypeError, ValueError):
            continue
    n = len(cal)
    if n == 0:
        return {
            'epsilon': None,
            'alpha': alpha,
            'n_calibration': 0,
            'coverage_guarantee': None,
            'prediction_interval': None,
            'unexpanded_interval': None,
            'status': 'insufficient_data',
            'ts': _now(),
        }
    eps = epsilon_radius(n, alpha)
    lo, hi = interval_from_cal(cal, alpha)
    lo_r = max(0.0, lo - eps)
    hi_r = min(1.0, hi + eps) if hi <= 1.5 else hi + eps
    return {
        'epsilon': eps,
        'alpha': alpha,
        'n_calibration': n,
        'coverage_guarantee': 1.0 - alpha,
        'prediction_interval': [lo_r, hi_r],
        'unexpanded_interval': [lo, hi],
        'status': 'ok',
        'ts': _now(),
    }


def update_state(score, state=None, w=W, alpha=ALPHA):
    state = dict(state or {})
    window = list(state.get('window') or [])
    try:
        window.append(float(score))
    except (TypeError, ValueError):
        pass
    if len(window) > w:
        window = window[-w:]
    n = len(window)
    if n == 0:
        return {
            'window': window,
            'q_lo': None,
            'q_hi': None,
            'alpha': alpha,
            'W': w,
            'n': 0,
            'latest_score': None,
            'empirical_coverage_rate': None,
            'status': 'insufficient_data',
            'ts': _now(),
        }
    lo, hi = interval(window, alpha=alpha)
    return {
        'window': window,
        'q_lo': lo,
        'q_hi': hi,
        'alpha': alpha,
        'W': w,
        'n': n,
        'latest_score': window[-1] if window else None,
        'empirical_coverage_rate': None,
        'status': 'ok',
        'ts': _now(),
    }


def empirical_coverage(scores, w=W, alpha=ALPHA, hold=50):
    xs = []
    for s in scores or []:
        try:
            xs.append(float(s))
        except (TypeError, ValueError):
            continue
    if len(xs) < w + 10:
        return None, 0
    cal, test = xs[:w], xs[w:w + hold]
    lo, hi = interval(cal, alpha=alpha)
    if lo is None or hi is None:
        return None, 0
    hits = sum(1 for v in test if lo - 1e-12 <= v <= hi + 1e-12)
    return hits / float(len(test)), len(test)


def load_state(path=None):
    p = path or OUT_PATH
    if not p.exists():
        return {'window': []}
    try:
        return json.loads(p.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return {'window': []}


def _append_scores_from_jsonl(path, xs, limit=MAX_LOAD):
    if not path.exists():
        return
    try:
        with path.open(encoding='utf-8', errors='replace') as fh:
            for line in fh:
                raw = line.strip()
                if not raw:
                    continue
                try:
                    rec = json.loads(raw)
                except json.JSONDecodeError:
                    try:
                        xs.append(float(raw))
                    except ValueError:
                        continue
                    continue
                if not isinstance(rec, dict):
                    continue
                if rec.get('scope') == 'ue_blackbox':
                    continue
                raw_score = rec.get('predicted_confidence', rec.get('score', rec.get('value')))
                if raw_score is None:
                    continue
                try:
                    xs.append(float(raw_score))
                except (TypeError, ValueError):
                    continue
    except OSError:
        return
    if len(xs) > limit:
        del xs[:-limit]


def load_cal():
    xs = []
    _append_scores_from_jsonl(CACHE / 'eval-scores.jsonl', xs)
    if len(xs) < 10:
        _append_scores_from_jsonl(CACHE / 'calibration-log.jsonl', xs)
    return xs


def persist_db(scores, db_path=None):
    db_path = db_path or DB_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), timeout=30)
    try:
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('CREATE TABLE IF NOT EXISTS scores (ts TEXT, score REAL)')
        conn.execute('DELETE FROM scores')
        ts = _now()
        conn.executemany('INSERT INTO scores VALUES (?,?)', [(ts, float(s)) for s in scores])
        conn.commit()
    finally:
        conn.close()


def _self_test() -> int:
    lo, hi = interval([], 0.1)
    assert lo is None and hi is None
    st = update_state(None, {'window': []})
    assert st['status'] == 'insufficient_data'
    st = {'window': []}
    rng = random.Random(5)
    for _ in range(60):
        st = update_state(rng.gauss(0.6, 0.05), st, w=50, alpha=0.1)
    assert st['n'] == 50 and st['status'] == 'ok'
    empty_w = calibrate_wasserstein([])
    assert empty_w['status'] == 'insufficient_data'
    assert empty_w['epsilon'] is None
    cal = [0.4 + i * 0.01 for i in range(40)]
    r = calibrate_wasserstein(cal, alpha=0.1)
    assert r['epsilon'] > 0
    assert r['prediction_interval'][0] <= r['unexpanded_interval'][0] + 1e-12
    assert r['prediction_interval'][1] >= r['unexpanded_interval'][1] - 1e-12
    rng = random.Random(9)
    seq = [rng.gauss(0.6, 0.04) for _ in range(200)]
    cov, tot = empirical_coverage(seq, w=80, alpha=0.1, hold=80)
    assert tot == 80 and cov is not None and cov >= 0.80, (cov, tot)
    tmp = _temp_out('rolling-conformal')
    wtmp = _temp_out('wasserstein')
    dbt = Path(tempfile.gettempdir()) / (f'rollcal-{uuid.uuid4().hex}.db')
    _atomic_write(tmp, {k: st[k] for k in st if k != 'window'})
    _atomic_write(wtmp, r)
    persist_db(seq[-50:], db_path=dbt)
    assert dbt.exists()
    try:
        tmp.unlink(missing_ok=True)
        wtmp.unlink(missing_ok=True)
        dbt.unlink(missing_ok=True)
        Path(str(dbt) + '-wal').unlink(missing_ok=True)
        Path(str(dbt) + '-shm').unlink(missing_ok=True)
        tmp.with_suffix(tmp.suffix + '.lock').unlink(missing_ok=True)
        wtmp.with_suffix(wtmp.suffix + '.lock').unlink(missing_ok=True)
    except OSError:
        pass
    print('[rolling-conformal-predictor] --self-test PASS [{:.3f}, {:.3f}] eps={:.4f} cov={}'.format(
        st['q_lo'], st['q_hi'], r['epsilon'], cov))
    return 0


def run(alpha=ALPHA, w=W, out_path=None, db_path=None):
    xs = load_cal()
    if not xs:
        return {
            'status': 'insufficient_data',
            'n': 0,
            'q_lo': None,
            'q_hi': None,
            'empirical_coverage_rate': None,
            'ts': _now(),
        }
    window = xs[-w:]
    lo, hi = interval(window, alpha=alpha)
    cov, tot = empirical_coverage(xs[-(w + 80):], w=min(w, max(10, len(xs) // 2)), alpha=alpha, hold=80)
    st = {
        'window': window,
        'q_lo': lo,
        'q_hi': hi,
        'alpha': alpha,
        'W': w,
        'n': len(window),
        'latest_score': window[-1],
        'empirical_coverage_rate': cov,
        'coverage_n': tot,
        'n_source': len(xs),
        'status': 'ok',
        'ts': _now(),
    }
    dest = out_path or OUT_PATH
    _atomic_write(dest, st)
    try:
        persist_db(window, db_path=db_path or DB_PATH)
    except Exception:
        pass
    return st


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--score', type=float, default=None)
    ap.add_argument('--mode', choices=['scores', 'wasserstein'], default='scores')
    ap.add_argument('--alpha', type=float, default=ALPHA)
    args = ap.parse_args()
    if args.self_test:
        try:
            sys.exit(_self_test())
        except Exception as exc:
            print(f'[rolling-conformal-predictor] --self-test FAIL: {exc}')
            sys.exit(1)
    try:
        if args.mode == 'wasserstein':
            r = calibrate_wasserstein(load_cal(), alpha=args.alpha)
            if r.get('status') != 'insufficient_data':
                _atomic_write(WASSERSTEIN_OUT, r)
            print(json.dumps(r))
            return
        if args.score is not None:
            st = update_state(args.score, load_state())
            if st.get('status') != 'insufficient_data':
                _atomic_write(OUT_PATH, st)
            print(json.dumps({k: st[k] for k in st if k != 'window'} | {'n': st['n']}))
            return
        st = run(alpha=args.alpha)
        print(json.dumps({k: st[k] for k in st if k != 'window'}))
    except Exception:
        pass


if __name__ == '__main__':
    main()
