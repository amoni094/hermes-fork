#!/usr/bin/env python3
"""Sample skills proportional to information-rate proxy (score / latency)."""
from __future__ import annotations
import argparse, json, math, os, random, sqlite3, sys, time, uuid, zlib
from collections import Counter, defaultdict
from datetime import datetime, timezone, UTC
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', 'fork')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base
CACHE = _hermes_root / 'cache'

def _now() -> str:
    return datetime.now(UTC).isoformat()

def _atomic_write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(obj, indent=2) + '\n', encoding='utf-8')
    os.replace(tmp, path)

def _lifecycle_db() -> Path:
    return _hermes_root / 'memory-facts' / 'lifecycle.db'

def _connect(db: Path | None = None) -> sqlite3.Connection:
    path = db or _lifecycle_db()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn

OUT_PATH = CACHE / 'skill-sampling-policy.json'
SCORES_PATH = CACHE / 'skill-robustness-scores.json'
TEMP = 0.5


def softmax(xs, T=TEMP):
    T = max(1e-6, float(T))
    m = max(xs) if xs else 0.0
    exps = [math.exp((x - m) / T) for x in xs]
    s = sum(exps) or 1.0
    return [e / s for e in exps]


def load_skill_perf():
    p = SCORES_PATH
    skills = []
    if p.exists():
        try:
            data = json.loads(p.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError):
            data = None
        if isinstance(data, dict):
            items = data.get('skills') or data.get('scores') or data
            if isinstance(items, dict):
                for name, v in items.items():
                    if isinstance(v, dict):
                        score = float(v.get('score', v.get('robustness', v.get('mean', 0.5))) or 0.5)
                        lat = float(v.get('latency_ms', v.get('latency', 100.0)) or 100.0)
                    else:
                        try:
                            score, lat = float(v), 100.0
                        except (TypeError, ValueError):
                            continue
                    skills.append({'name': str(name), 'score': score, 'latency_ms': max(1.0, lat)})
            elif isinstance(items, list):
                for it in items:
                    if not isinstance(it, dict):
                        continue
                    name = it.get('name') or it.get('skill')
                    if not name:
                        continue
                    rs = it.get('robustness_score', it.get('score'))
                    if rs is None:
                        continue
                    try:
                        sc = float(rs)
                    except (TypeError, ValueError):
                        continue
                    skills.append({
                        'name': str(name),
                        'score': sc,
                        'latency_ms': max(1.0, float(it.get('latency_ms', 100.0) or 100.0)),
                    })
    return skills


def policy(skills, T=TEMP):
    if not skills:
        return {'ts': _now(), 'temperature': T, 'skills': [], 'status': 'insufficient_data', 'n': 0}
    rates = [s['score'] / s['latency_ms'] for s in skills]
    probs = softmax(rates, T=T)
    out = []
    for s, r, p in zip(skills, rates, probs):
        out.append({'name': s['name'], 'info_rate': r, 'sample_prob': p, 'score': s['score'], 'latency_ms': s['latency_ms']})
    return {
        'ts': _now(),
        'temperature': T,
        'skills': out,
        'status': 'ok',
        'n': len(out),
    }


def _self_test() -> int:
    skills = [
        {'name': 'fast', 'score': 1.0, 'latency_ms': 1.0},
        {'name': 'slow', 'score': 1.0, 'latency_ms': 100.0},
        {'name': 'mid', 'score': 0.5, 'latency_ms': 10.0},
    ]
    r = policy(skills, T=0.5)
    probs = {s['name']: s['sample_prob'] for s in r['skills']}
    assert abs(sum(probs.values()) - 1.0) < 1e-9
    assert probs['fast'] > probs['slow']
    tmp = OUT_PATH.with_name(OUT_PATH.stem + '_test_' + uuid.uuid4().hex + OUT_PATH.suffix)
    _atomic_write(tmp, r)
    tmp.unlink(missing_ok=True)
    print('[information-rate-skill-sampler] --self-test PASS fast={:.3f} slow={:.3f}'.format(probs['fast'], probs['slow']))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--temperature', type=float, default=TEMP)
    args = ap.parse_args()
    if args.self_test:
        try:
            sys.exit(_self_test())
        except Exception as exc:
            print(f'[information-rate-skill-sampler] --self-test FAIL: {exc}')
            sys.exit(1)
    r = policy(load_skill_perf(), T=args.temperature)
    if r.get('status') != 'insufficient_data':
        try:
            _atomic_write(OUT_PATH, r)
        except Exception:
            pass
    print(json.dumps(r))


if __name__ == '__main__':
    main()
