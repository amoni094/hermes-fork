#!/usr/bin/env python3
"""routing-pac-bayes-bound.py — McAllester PAC-Bayes bound on skill-router error.

Prior P = uniform over skills. Posterior Q = normalized beta-bandit means.
gen_error <= emp_error + sqrt( (KL(Q||P) + log(2*sqrt(m)/delta)) / (2m) )

Alarm if gen_error_bound > 0.3.

Source: Shalev-Shwartz Understanding ML; McAllester PAC-Bayes.
"""
from __future__ import annotations
import argparse
import json
import math
import os
import sys
import tempfile
import time
from pathlib import Path

import os
from pathlib import Path
_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base

DELTA = 0.05
ALARM_THRESH = 0.3
EPS = 1e-15


def _cache_dir() -> Path:
    override = os.environ.get('HERMES_CACHE_DIR', '').strip()
    p = Path(override) if override else (_hermes_root / 'cache')
    try:
        p.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return p


def _atomic_write_json(path: Path, obj) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + '.tmp')
        tmp.write_text(json.dumps(obj, indent=2) + '\n')
        os.replace(str(tmp), str(path))
    except Exception:
        try:
            tmp = path.with_suffix(path.suffix + '.tmp')
            if tmp.exists():
                tmp.unlink()
        except Exception:
            pass


def _load_json(path: Path, default):
    try:
        return json.loads(path.read_text())
    except (OSError, FileNotFoundError, json.JSONDecodeError):
        return default


def _kl_categorical(q: list, p: list) -> float:
    """KL(Q||P) = sum q log(q/p). 0-log-0 := 0. Pure Python."""
    kl = 0.0
    for qi, pi in zip(q, p):
        if qi <= 0.0:
            continue
        denom = pi if pi > EPS else EPS
        kl += qi * math.log(qi / denom)
    return max(0.0, kl)


def compute_bound(beta_state: dict, delta: float = DELTA) -> dict:
    names = sorted(beta_state.keys()) if isinstance(beta_state, dict) else []
    n = len(names)
    if n == 0:
        return {
            'n_skills': 0,
            'm': 0,
            'emp_error': 0.5,
            'kl_qp': 0.0,
            'gen_error_bound': 1.0,
            'alarm': True,
            'reason': 'empty_posterior',
        }
    means = []
    obs = []
    for name in names:
        entry = beta_state.get(name)
        if not isinstance(entry, dict):
            entry = {}
        try:
            a = float(entry.get('alpha', 1.0))
            b = float(entry.get('beta', 1.0))
        except (TypeError, ValueError):
            a, b = 1.0, 1.0
        a = max(a, EPS)
        b = max(b, EPS)
        means.append(a / (a + b))
        obs.append(max(0.0, a + b - 2.0))
    m = max(1.0, sum(obs))
    s = sum(means) or float(n)
    q = [x / s for x in means]
    p = [1.0 / n] * n
    kl = _kl_categorical(q, p)
    # ADV21-006: Q-weighted empirical error (McAllester Lhat(Q) = sum q_i * loss_i)
    emp_error = max(0.0, sum(q[i] * (1.0 - means[i]) for i in range(n)))
    # McAllester: L <= Lhat + sqrt( (KL + log(2 sqrt(m)/delta)) / (2m) )
    inner = kl + math.log(max(EPS, 2.0 * math.sqrt(m) / max(delta, EPS)))
    inner = max(0.0, inner)
    penalty = math.sqrt(inner / (2.0 * m))
    gen = min(1.0, max(0.0, emp_error + penalty))
    # ADV21-006: only alarm if bound is non-vacuous (m > KL + log term)
    vacuous = m < (kl + math.log(max(EPS, 2.0 / max(delta, EPS))))
    alarm = gen > ALARM_THRESH and not vacuous
    return {
        'n_skills': n,
        'm': int(m) if m == int(m) else m,
        'delta': delta,
        'emp_error': round(emp_error, 6),
        'kl_qp': round(kl, 6),
        'penalty': round(penalty, 6),
        'gen_error_bound': round(gen, 6),
        'alarm': alarm,
        'vacuous': vacuous,
        'alarm_threshold': ALARM_THRESH,
        'reason': 'gen_error_bound>0.3' if alarm else 'ok',
        'posterior_mass_top': sorted(
            [{'skill': names[i], 'q': round(q[i], 6), 'mean': round(means[i], 6)} for i in range(n)],
            key=lambda r: -r['q'],
        )[:8],
    }


def run(cache: Path | None = None) -> dict:
    cache = cache or _cache_dir()
    beta_path = cache / 'skill-beta-state.json'
    beta = _load_json(beta_path, {})
    if not isinstance(beta, dict):
        beta = {}
    result = compute_bound(beta)
    result['ts'] = time.time()
    result['source'] = str(beta_path)
    try:
        _atomic_write_json(cache / 'routing-pac-bayes.json', result)
    except Exception:
        pass
    return result


def self_test() -> dict:
    failures = []
    # 1. two-skill posterior, bound >= emp_error and finite
    try:
        st = {'a': {'alpha': 9.0, 'beta': 1.0}, 'b': {'alpha': 1.0, 'beta': 9.0}}
        r = compute_bound(st)
        assert r['gen_error_bound'] >= r['emp_error'] - 1e-9
        assert 0.0 <= r['gen_error_bound'] <= 1.0
        assert r['kl_qp'] > 0.0
        assert r['m'] >= 1
    except Exception as e:
        failures.append(f'bound-basic: {e}')
    # 2. empty state
    try:
        r = compute_bound({})
        assert r['n_skills'] == 0
        assert 'gen_error_bound' in r
    except Exception as e:
        failures.append(f'empty: {e}')
    # 3. malformed entries ignored / no crash
    try:
        r = compute_bound({'x': 'bad', 'y': {'alpha': 2, 'beta': 2}})
        assert 0.0 <= r['gen_error_bound'] <= 1.0
    except Exception as e:
        failures.append(f'malformed: {e}')
    # 4. isolated write
    try:
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d / 'skill-beta-state.json').write_text(json.dumps({
                's1': {'alpha': 3, 'beta': 1}, 's2': {'alpha': 1, 'beta': 3}
            }))
            r = run(cache=d)
            out = json.loads((d / 'routing-pac-bayes.json').read_text())
            assert out['n_skills'] == 2
            json.dumps(out)
    except Exception as e:
        failures.append(f'atomic-write: {e}')
    # 5. uniform posterior KL ~ 0
    try:
        st = {f's{i}': {'alpha': 2.0, 'beta': 2.0} for i in range(5)}
        r = compute_bound(st)
        assert r['kl_qp'] < 1e-9
    except Exception as e:
        failures.append(f'uniform-kl: {e}')
    return {'self_test': 'PASS' if not failures else 'FAIL', 'n_failures': len(failures), 'failures': failures}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true')
    args = ap.parse_args()
    if args.self_test:
        r = self_test()
        print(json.dumps(r, indent=2))
        sys.exit(0 if r['self_test'] == 'PASS' else 1)
    try:
        r = run()
        print(json.dumps(r, indent=2))
    except Exception:
        print(json.dumps({'error': 'shadow_path_failed', 'alarm': False}))
        sys.exit(0)


if __name__ == '__main__':
    main()
