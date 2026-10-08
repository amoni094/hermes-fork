#!/usr/bin/env python3
"""loop-rollout-horizon.py — Bertsekas one-step rollout when PID model fails.

If loop-model-comparison prefers M1 (random walk) or CUSUM alarms, the
linear PID policy is not a valid base. Roll out one-step costs of
HALT / PATCH / REPLAN / ESCALATE using last error e.

Usage:
  python3 loop-rollout-horizon.py --self-test
  python3 loop-rollout-horizon.py
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base
CACHE = _hermes_root / 'cache'
OUT = CACHE / 'loop-rollout-horizon.json'


def _atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    os.replace(tmp, path)


def _load(name: str) -> dict:
    try:
        obj = json.loads((CACHE / name).read_text())
        return obj if isinstance(obj, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def rollout(e: float, pid_model_ok: bool, cusum_alarm: bool) -> dict:
    # Approximate one-step costs (Bertsekas Q for base policy)
    costs = {
        'HALT': 0.0 if e < 0.15 else 2.0 + e,
        'PATCH': 0.4 + 0.6 * e if pid_model_ok and not cusum_alarm else 1.5 + e,
        'REPLAN': 0.8 + 0.3 * e,
        'ESCALATE': 1.2 if (not pid_model_ok or cusum_alarm) else 2.0,
    }
    best = min(costs, key=costs.get)
    pid_action = 'HALT' if e < 0.15 else 'PATCH'
    return {
        'e': e,
        'pid_model_ok': pid_model_ok,
        'cusum_alarm': cusum_alarm,
        'costs': costs,
        'rollout_action': best,
        'pid_action': pid_action,
        'disagrees_with_pid': best != pid_action,
        'alarm': (not pid_model_ok or cusum_alarm) and best != pid_action,
        'theorem': 'Bertsekas rollout / one-step lookahead when base PID is misspecified',
    }


def last_e() -> float:
    for p in (CACHE / 'loop-pid-state.json', _hermes_base / 'cache' / 'loop-pid-state.json'):
        try:
            d = json.loads(p.read_text())
            hist = d.get('history') or []
            if hist:
                return float(hist[-1].get('e') or 0)
            return float(d.get('e') or 0)
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            continue
    return 0.0


def run() -> dict:
    cmp_ = _load('loop-model-comparison.json')
    cusum = _load('loop-cusum-changepoint.json')
    pid_ok = cmp_.get('preferred_model', 'M0') == 'M0' and (cmp_.get('recommendation') != 'switch_to_mpc_rollout')
    out = rollout(last_e(), pid_ok, bool(cusum.get('alarm')))
    out['ts'] = datetime.now(timezone.utc).isoformat()
    try:
        _atomic_write(OUT, out)
        out['output'] = str(OUT)
    except OSError as exc:
        out['write_error'] = str(exc)
    return out


def self_test() -> int:
    failures = []
    r = rollout(0.05, True, False)
    if r['rollout_action'] != 'HALT' or r['alarm']:
        failures.append(f'small e HALT {r}')
    r2 = rollout(0.9, False, True)
    if r2['pid_action'] != 'PATCH':
        failures.append('pid would PATCH')
    if r2['rollout_action'] == 'PATCH':
        failures.append(f'misspecified should not PATCH {r2}')
    if not r2['alarm']:
        failures.append('should alarm on disagreement')
    if failures:
        print(json.dumps({'self_test': 'FAIL', 'failures': failures}))
        return 1
    print(json.dumps({'self_test': 'PASS'}))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument('--self-test', action='store_true')
    args = p.parse_args(argv)
    if args.self_test:
        return self_test()
    out = run()
    print(json.dumps({k: out.get(k) for k in ('rollout_action', 'pid_action', 'disagrees_with_pid', 'alarm', 'output')}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
