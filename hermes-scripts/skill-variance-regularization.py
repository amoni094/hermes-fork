#!/usr/bin/env python3
"""Rerank skills by empirical confidence-interval width (variance regularizer).

Reads skill_confidence_intervals.json when present; otherwise computes
Hoeffding/Wilson-style widths from anytime_eval_log. Writes skill-confidence.json.
Fail-open. stdlib only. No synthetic skills when inputs are empty.
"""
from __future__ import annotations
import argparse, fcntl, json, math, os, sqlite3, sys, tempfile, uuid
from collections import defaultdict
from datetime import datetime, timezone, UTC
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
if _hermes_base.name != '.hermes' and _hermes_base.parent.name == 'profiles':
    _hermes_base = _hermes_base.parent.parent
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base
CACHE = _hermes_root / 'cache'
LIFECYCLE_DB = _hermes_base / 'memory-facts' / 'lifecycle.db'
OUT_PATH = CACHE / 'skill-confidence.json'
INTERVALS_PATH = CACHE / 'skill_confidence_intervals.json'
LAM = 0.5
Z = 1.96


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


def wilson_width(p, n, z=Z):
    p = max(0.0, min(1.0, float(p)))
    n = max(1.0, float(n))
    z2 = z * z
    denom = 1.0 + z2 / n
    inner = p * (1.0 - p) / n + z2 / (4.0 * n * n)
    margin = z * math.sqrt(max(0.0, inner)) / denom
    return max(0.0, min(1.0, 2.0 * margin))


def regularize(skills, lam=LAM):
    ranked = []
    for name, rec in (skills or {}).items():
        try:
            mean = float(rec.get('mean', 0.0))
        except (TypeError, ValueError):
            mean = 0.0
        try:
            width = float(rec.get('width', rec.get('hi', 1.0) - rec.get('lo', 0.0)))
        except (TypeError, ValueError):
            width = 1.0
        try:
            n = int(rec.get('n') or 0)
        except (TypeError, ValueError):
            n = 0
        score = mean - lam * width
        ranked.append({
            'skill': str(name),
            'mean': mean,
            'width': width,
            'n': n,
            'regularized': score,
        })
    ranked.sort(key=lambda r: (-r['regularized'], r['width'], -r['n'], r['skill']))
    return ranked


def variance_metric(ranked):
    if not ranked:
        return None
    return sum(r['width'] for r in ranked) / float(len(ranked))


def load_intervals(path=None):
    p = path or INTERVALS_PATH
    if not p.exists():
        return {}
    try:
        obj = json.loads(p.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(obj, dict):
        return {}
    skills = obj.get('skills') or obj.get('bagged') or {}
    if not isinstance(skills, dict):
        return {}
    out = {}
    for k, v in skills.items():
        if not isinstance(v, dict):
            continue
        out[str(k)] = v
    return out


def load_from_eval_log(db_path=None, limit=8000):
    db = Path(db_path) if db_path else LIFECYCLE_DB
    if not db.exists():
        return {}
    conn = sqlite3.connect(str(db), timeout=30)
    try:
        conn.execute('PRAGMA journal_mode=WAL')
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if 'anytime_eval_log' not in tables:
            return {}
        rows = conn.execute(
            'SELECT skill_id, eval_score FROM anytime_eval_log ORDER BY id DESC LIMIT ?',
            (limit,),
        ).fetchall()
    except Exception:
        return {}
    finally:
        conn.close()
    by = defaultdict(list)
    for skill, score in rows:
        if not skill:
            continue
        try:
            y = float(score)
        except (TypeError, ValueError):
            continue
        y = 1.0 if y > 1.0 else (max(y, 0.0))
        by[str(skill)].append(y)
    out = {}
    for sk, ys in by.items():
        n = len(ys)
        if n < 5:
            continue
        mean = sum(ys) / n
        w = wilson_width(mean, n)
        out[sk] = {
            'n': n,
            'mean': mean,
            'lo': max(0.0, mean - w / 2.0),
            'hi': min(1.0, mean + w / 2.0),
            'width': w,
        }
    return out


def run(out_path=None, intervals_path=None, db_path=None, lam=LAM, skills=None):
    src = 'intervals'
    if skills is None:
        skills = load_intervals(intervals_path)
        if not skills:
            skills = load_from_eval_log(db_path=db_path)
            src = 'anytime_eval_log'
    if not skills:
        return {'status': 'insufficient_data', 'n': 0, 'variance_metric': None, 'ts': _now()}
    ranked = regularize(skills, lam=lam)
    var = variance_metric(ranked)
    dest = out_path or OUT_PATH
    prev_var = None
    if dest.exists():
        try:
            prev = json.loads(dest.read_text(encoding='utf-8'))
            prev_var = prev.get('variance_metric')
        except (OSError, json.JSONDecodeError):
            prev_var = None
    delta = None
    if prev_var is not None and var is not None:
        try:
            delta = float(var) - float(prev_var)
        except (TypeError, ValueError):
            delta = None
    payload = {
        'ts': _now(),
        'status': 'ok',
        'source': src,
        'lambda': lam,
        'n': len(ranked),
        'variance_metric': var,
        'variance_delta': delta,
        'ranking': ranked[:50],
    }
    _atomic_write(dest, payload)
    return payload


def _self_test() -> int:
    empty = run(skills={}, out_path=_temp_out('var-empty'))
    assert empty['status'] == 'insufficient_data'
    skills = {
        'stable': {'mean': 0.80, 'width': 0.05, 'n': 200, 'lo': 0.775, 'hi': 0.825},
        'noisy': {'mean': 0.85, 'width': 0.40, 'n': 20, 'lo': 0.65, 'hi': 1.05},
        'weak': {'mean': 0.40, 'width': 0.10, 'n': 80, 'lo': 0.35, 'hi': 0.45},
    }
    tmp = _temp_out('var-reg')
    r = run(skills=skills, out_path=tmp, lam=0.5)
    assert r['status'] == 'ok'
    names = [x['skill'] for x in r['ranking']]
    assert names[0] == 'stable', names
    assert 'noisy' in names
    w = wilson_width(0.8, 50)
    w2 = wilson_width(0.8, 200)
    assert w2 < w
    try:
        tmp.unlink(missing_ok=True)
        tmp.with_suffix(tmp.suffix + '.lock').unlink(missing_ok=True)
    except OSError:
        pass
    print('[skill-variance-regularization] --self-test PASS top={} var={}'.format(names[0], r['variance_metric']))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--run', action='store_true')
    ap.add_argument('--lambda', dest='lam', type=float, default=LAM)
    args = ap.parse_args()
    if args.self_test:
        try:
            sys.exit(_self_test())
        except Exception as exc:
            print(f'[skill-variance-regularization] --self-test FAIL: {exc}')
            sys.exit(1)
    try:
        payload = run(lam=args.lam)
        public = {k: payload[k] for k in payload if k != 'ranking'}
        public['n_ranked'] = len(payload.get('ranking') or [])
        print(json.dumps(public))
    except Exception as e:
        print(json.dumps({'status': 'error', 'reason': str(e)}))
        sys.exit(0)


if __name__ == '__main__':
    main()
