#!/usr/bin/env python3
"""routing-wald-sprt.py — Wald SPRT explore/exploit stop for each skill arm.

H0: p = p0 (useless, default 0.5) vs H1: p = p1 (useful, default 0.7)
Lambda_n = n * KL; stop EXPLOIT if logLR >= A, ABANDON if logLR <= B.

Source: Wald Sequential Analysis; Lattimore bandits stopping.
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

P0 = 0.5
P1 = 0.7
ALPHA = 0.05
BETA = 0.05
EPS = 1e-12


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


def _clip_p(p: float) -> float:
    return min(1.0 - EPS, max(EPS, p))


def bernoulli_loglr(successes: float, failures: float, p0: float = P0, p1: float = P1) -> float:
    s = max(0.0, successes)
    f = max(0.0, failures)
    p0, p1 = _clip_p(p0), _clip_p(p1)
    return s * math.log(p1 / p0) + f * math.log((1.0 - p1) / (1.0 - p0))


def thresholds(alpha: float = ALPHA, beta: float = BETA) -> tuple:
    A = math.log((1.0 - beta) / max(alpha, EPS))
    B = math.log(beta / max(1.0 - alpha, EPS))
    return A, B


def decide(alpha_s: float, beta_s: float, p0=P0, p1=P1, alpha=ALPHA, beta=BETA) -> dict:
    # observations exclude prior: successes = alpha-1, failures = beta-1
    s = max(0.0, alpha_s - 1.0)
    f = max(0.0, beta_s - 1.0)
    llr = bernoulli_loglr(s, f, p0, p1)
    A, B = thresholds(alpha, beta)
    if llr >= A:
        decision = 'EXPLOIT'
    elif llr <= B:
        decision = 'ABANDON'
    else:
        decision = 'CONTINUE'
    return {
        'successes': s, 'failures': f, 'llr': round(llr, 6),
        'A': round(A, 6), 'B': round(B, 6), 'decision': decision,
        'n': s + f,
    }


def compute(beta_state: dict) -> dict:
    A, B = thresholds()
    rows = []
    counts = {'EXPLOIT': 0, 'ABANDON': 0, 'CONTINUE': 0}
    if isinstance(beta_state, dict):
        for name, entry in sorted(beta_state.items()):
            if not isinstance(entry, dict):
                continue
            try:
                a = float(entry.get('alpha', 1.0))
                b = float(entry.get('beta', 1.0))
            except (TypeError, ValueError):
                continue
            d = decide(a, b)
            d['skill'] = name
            rows.append(d)
            counts[d['decision']] += 1
    return {
        'ts': time.time(),
        'p0': P0, 'p1': P1, 'alpha': ALPHA, 'beta_err': BETA,
        'A': round(A, 6), 'B': round(B, 6),
        'counts': counts,
        'alarm': counts['ABANDON'] > 0,
        'skills': rows,
    }


def run(cache: Path | None = None) -> dict:
    cache = cache or _cache_dir()
    beta = _load_json(cache / 'skill-beta-state.json', {})
    result = compute(beta if isinstance(beta, dict) else {})
    try:
        _atomic_write_json(cache / 'routing-wald-sprt.json', result)
    except Exception:
        pass
    return result


def self_test() -> dict:
    failures = []
    try:
        # many successes -> EXPLOIT
        d = decide(40, 1)
        assert d['decision'] == 'EXPLOIT', d
        d2 = decide(1, 40)
        assert d2['decision'] == 'ABANDON', d2
        d3 = decide(2, 2)
        assert d3['decision'] == 'CONTINUE', d3
    except Exception as e:
        failures.append(f'decide: {e}')
    try:
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d / 'skill-beta-state.json').write_text(json.dumps({
                'good': {'alpha': 40, 'beta': 1},
                'bad': {'alpha': 1, 'beta': 40},
            }))
            r = run(cache=d)
            assert r['counts']['EXPLOIT'] == 1
            assert r['counts']['ABANDON'] == 1
            json.dumps(r)
    except Exception as e:
        failures.append(f'io: {e}')
    try:
        r = compute({})
        assert r['counts']['CONTINUE'] == 0
    except Exception as e:
        failures.append(f'empty: {e}')
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
        print(json.dumps(run(), indent=2))
    except Exception:
        print(json.dumps({'error': 'shadow_path_failed'}))
        sys.exit(0)


if __name__ == '__main__':
    main()
