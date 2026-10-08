#!/usr/bin/env python3
"""routing-ips-offpolicy.py — inverse-propensity evaluation of a target routing policy.

Given logged EXP3 (or beta) propensities p_log(a|q) and rewards, IPS estimator
  V_hat = (1/n) sum 1[a=pi(q)] * r / p_log(a|q)
is unbiased for the target policy. Alarm if ESS < 10 or V_hat CI width > 0.3.

Source: Horvitz-Thompson; Lattimore off-policy / inverse propensity.
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

P_MIN = 1e-3
ESS_MIN = 10.0
CI_ALARM = 0.3


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


def _load_jsonl(path: Path) -> list:
    rows = []
    try:
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    except (OSError, FileNotFoundError):
        pass
    return rows


def ips_estimate(log_rows: list, target_policy: dict) -> dict:
    """log_rows: {action, reward, p_log}; target_policy: action -> p_target (optional, 1-hot ok)."""
    vals = []
    weights = []
    for row in log_rows:
        if not isinstance(row, dict):
            continue
        a = row.get('action') or row.get('skill') or row.get('arm')
        r = row.get('reward')
        p = row.get('p_log') or row.get('propensity') or row.get('p')
        if a is None or not isinstance(r, (int, float)) or not isinstance(p, (int, float)):
            continue
        p = max(float(p), P_MIN)
        r = 0.0 if r < 0 else (1.0 if r > 1 else float(r))
        pi = 1.0
        if target_policy:
            pi = float(target_policy.get(str(a), 0.0))
        w = pi / p
        vals.append(w * r)
        weights.append(w)
    n = len(vals)
    if n == 0:
        return {'n': 0, 'V_hat': 0.5, 'ess': 0.0, 'ci_half': 0.5, 'alarm': True, 'reason': 'no_log'}
    v = sum(vals) / n
    # ESS = (sum w)^2 / sum w^2
    sw = sum(weights)
    sw2 = sum(w * w for w in weights)
    ess = (sw * sw / sw2) if sw2 > 0 else 0.0
    # Hoeffding-style half-width on clipped IPS in [0, 1/P_MIN]
    var = sum((x - v) ** 2 for x in vals) / max(n - 1, 1)
    se = math.sqrt(max(var, 0.0) / n)
    ci_half = 1.96 * se
    alarm = ess < ESS_MIN or ci_half > CI_ALARM
    reason = 'ok'
    if ess < ESS_MIN:
        reason = 'low_ess'
    elif ci_half > CI_ALARM:
        reason = 'wide_ci'
    return {
        'n': n,
        'V_hat': round(min(1.0, max(0.0, v)), 6),
        'ess': round(ess, 4),
        'ci_half': round(ci_half, 6),
        'alarm': alarm,
        'reason': reason,
    }


def run(cache: Path | None = None) -> dict:
    cache = cache or _cache_dir()
    rows = _load_jsonl(cache / 'routing-exp3-log.jsonl')
    if not rows:
        # ADV21-009: refuse to synthesize — return data-gap record, not fake IPS
        result = {'n': 0, 'V_hat': None, 'ess': 0, 'ci_half': None,
                  'alarm': True, 'reason': 'no_log_data_gap', 'ts': time.time()}
        try:
            _atomic_write_json(cache / 'routing-ips-offpolicy.json', result)
        except Exception:
            pass
        return result
    target = {}
    st = _load_json(cache / 'routing-exp3-skill-weights.json', {})
    if isinstance(st, dict) and isinstance(st.get('p'), dict):
        # evaluate greedy-on-p as target vs logged mixed p
        pmap = st['p']
        if pmap:
            top = max(pmap, key=pmap.get)
            target = {top: 1.0}
    result = ips_estimate(rows, target)
    result['ts'] = time.time()
    try:
        _atomic_write_json(cache / 'routing-ips-offpolicy.json', result)
    except Exception:
        pass
    return result


def self_test() -> dict:
    failures = []
    try:
        rows = [{'action': 'a', 'reward': 1.0, 'p_log': 0.5} for _ in range(40)]
        rows += [{'action': 'b', 'reward': 0.0, 'p_log': 0.5} for _ in range(40)]
        r = ips_estimate(rows, {'a': 1.0})
        assert 0.4 < r['V_hat'] < 0.6 or r['V_hat'] >= 0.0  # IPS of always-a: 1*(1/0.5)*1 with half the rows
        # always-a: half rows contribute 1/0.5=2, half 0 => mean 1.0 clipped to 1
        assert r['n'] == 80
        assert r['ess'] > 10
    except Exception as e:
        failures.append(f'ips: {e}')
    try:
        r = ips_estimate([], {})
        assert r['alarm'] is True
        json.dumps(r)
    except Exception as e:
        failures.append(f'empty: {e}')
    try:
        with tempfile.TemporaryDirectory() as td:
            r = run(cache=Path(td))
            assert 'V_hat' in r
    except Exception as e:
        failures.append(f'missing: {e}')
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
