#!/usr/bin/env python3
"""Score robustness of a feedback/eval trajectory under bounded perturbations."""
from __future__ import annotations
import argparse, json, math, os, random, sqlite3, sys, tempfile, uuid
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
    os.replace(str(tmp), str(path))

def _lifecycle_db() -> Path:
    return _hermes_root / 'memory-facts' / 'lifecycle.db'

def _temp_out(prefix: str) -> Path:
    return Path(tempfile.gettempdir()) / (f'{prefix}-{uuid.uuid4().hex}.json')

OUT_PATH = CACHE / 'feedback-robustness.json'
EPS = 0.05
TRIALS = 40


def load_scores():
    p = CACHE / 'eval-scores.jsonl'
    xs = []
    if not p.exists():
        return xs
    try:
        for line in p.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                xs.append(float(rec.get('score', rec.get('value', rec))))
            except (json.JSONDecodeError, TypeError, ValueError):
                try:
                    xs.append(float(line))
                except ValueError:
                    continue
    except OSError:
        return []
    return xs


def robustness(scores, eps=EPS, trials=TRIALS, seed=0):
    ys = []
    for s in scores or []:
        try:
            ys.append(float(s))
        except (TypeError, ValueError):
            continue
    n = len(ys)
    if n == 0:
        return {
            'robustness_score': None,
            'base_mean': None,
            'worst_mean': None,
            'eps': eps,
            'trials': trials,
            'n': 0,
            'status': 'insufficient_data',
            'ts': _now(),
        }
    rng = random.Random(seed)
    base = sum(ys) / n
    worst = base
    for _ in range(trials):
        pert = [max(0.0, min(1.0, y + rng.uniform(-eps, eps))) for y in ys]
        m = sum(pert) / n
        worst = min(worst, m)
    score = 1.0 - abs(base - worst) / max(eps, 1e-9)
    score = max(0.0, min(1.0, score))
    return {
        'robustness_score': score,
        'base_mean': base,
        'worst_mean': worst,
        'eps': eps,
        'trials': trials,
        'n': n,
        'status': 'ok',
        'ts': _now(),
    }


def _self_test() -> int:
    empty = robustness([])
    assert empty['status'] == 'insufficient_data'
    assert empty['robustness_score'] is None
    r = robustness([0.5] * 30, eps=0.05, trials=20, seed=1)
    assert 0.0 <= r['robustness_score'] <= 1.0
    tmp = _temp_out('feedback-rob')
    _atomic_write(tmp, r)
    try:
        tmp.unlink(missing_ok=True)
    except OSError:
        pass
    print('[feedback-robustness-scorer] --self-test PASS score={:.3f}'.format(r['robustness_score']))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true')
    args = ap.parse_args()
    if args.self_test:
        try:
            sys.exit(_self_test())
        except Exception as exc:
            print(f'[feedback-robustness-scorer] --self-test FAIL: {exc}')
            sys.exit(1)
    try:
        r = robustness(load_scores())
        if r.get('status') != 'insufficient_data':
            _atomic_write(OUT_PATH, r)
        print(json.dumps(r))
    except Exception:
        pass


if __name__ == '__main__':
    main()
