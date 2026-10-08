#!/usr/bin/env python3
"""wave21c-alarm-bridge.py — Re-emit 21C reports as *-alarm.json for aggregator.

alarm-aggregator.py only scans cache/*-alarm.json and ignores files older than
2h. Daily 21C reports would vanish; this bridge re-reads the latest reports
every 30m and writes fresh sidecars.

Usage:
  python3 wave21c-alarm-bridge.py --self-test
  python3 wave21c-alarm-bridge.py
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

# (report filename, alarm-key or callable, default severity)
SOURCES = [
    ('loop-stability-composite.json', 'alarm', 'HIGH'),
    ('shadow-sprt-decisions.json', None, 'MEDIUM'),  # special: n_promote without FO handled elsewhere
    ('governance-conflict-summary.json', None, 'HIGH'),
    ('governance-falsifiability-report.json', 'alarm', 'HIGH'),
    ('loop-model-comparison.json', None, 'MEDIUM'),
    ('callgraph-taint-report.json', 'alarm', 'HIGH'),
    ('nyquist-timescale-bridge.json', 'alarm', 'MEDIUM'),
    ('loop-cusum-changepoint.json', 'alarm', 'MEDIUM'),
    ('sprt-falsifiability-handshake.json', 'alarm', 'HIGH'),
    ('governance-conflict-epistemic.json', 'alarm', 'HIGH'),
    ('pid-passivity-index.json', 'alarm', 'MEDIUM'),
    ('pid-circle-criterion.json', 'alarm', 'MEDIUM'),
    ('session-type-tool-protocol.json', 'alarm', 'LOW'),
    ('ltl-promotion-invariant.json', 'alarm', 'HIGH'),
    ('loop-rollout-horizon.json', 'alarm', 'LOW'),
    ('sprt-measurement-tamper.json', 'alarm', 'HIGH'),
    ('soares-halt-liveness.json', 'alarm', 'HIGH'),
    ('cusum-gain-freeze.json', 'alarm', 'MEDIUM'),
    ('sprt-inner-outer-alignment.json', 'alarm', 'HIGH'),
    ('iss-justification.json', 'alarm', 'HIGH'),
    ('sprt-truncation.json', 'alarm', 'MEDIUM'),
    ('promotion-at-most-once.json', 'alarm', 'HIGH'),
    ('sprt-effective-decision.json', 'alarm', 'MEDIUM'),
    ('wave21c-invariants.json', 'alarm', 'HIGH'),
]


def _atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    os.replace(tmp, path)


def _load(name: str) -> dict:
    p = CACHE / name
    try:
        obj = json.loads(p.read_text(encoding='utf-8'))
        return obj if isinstance(obj, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _is_alarm(name: str, data: dict, key) -> tuple[bool, str]:
    if not data:
        return False, 'missing report'
    if name == 'shadow-sprt-decisions.json':
        # SPRT CONTINUE is not an alarm; REJECT is informational; veto is
        n_veto = sum(1 for d in data.get('decisions') or [] if d.get('error_rate_veto'))
        return n_veto > 0, f'error_rate_veto n={n_veto}'
    if name == 'governance-conflict-summary.json':
        n = int(data.get('n_conflicts') or 0)
        return n > 0, f'n_conflicts={n}'
    if name == 'loop-model-comparison.json':
        rec = data.get('recommendation') or ''
        return rec == 'switch_to_mpc_rollout', rec or 'ok'
    if key and data.get(key):
        return True, str(data.get('alarm_reason') or data.get('reason') or data.get('note') or 'alarm')
    if data.get('alarm'):
        return True, str(data.get('reason') or data.get('note') or 'alarm')
    return False, 'ok'


def emit_sidecar(source_stem: str, alarm: bool, severity: str, msg: str) -> dict:
    payload = {
        'alarm': bool(alarm),
        'severity': severity if alarm else 'ok',
        'msg': msg,
        'reason': msg,
        'source': source_stem,
        'ts': datetime.now(timezone.utc).isoformat(),
        'theorem': 'alarm-aggregator *-alarm.json contract; 2h TTL refresh',
    }
    out = CACHE / f'wave21c-{source_stem}-alarm.json'
    try:
        _atomic_write(out, payload)
        payload['output'] = str(out)
    except OSError as exc:
        payload['write_error'] = str(exc)
    return payload


def run() -> dict:
    emitted = []
    n_active = 0
    for fname, key, sev in SOURCES:
        data = _load(fname)
        alarm, msg = _is_alarm(fname, data, key)
        stem = fname.replace('.json', '')
        # Always refresh sidecar so aggregator 2h window stays open
        rec = emit_sidecar(stem, alarm, sev, msg)
        emitted.append({'source': fname, 'alarm': alarm, 'severity': sev if alarm else 'ok'})
        if alarm:
            n_active += 1
    summary = {
        'ts': datetime.now(timezone.utc).isoformat(),
        'n_sources': len(SOURCES),
        'n_active': n_active,
        'emitted': emitted,
        'alarm': n_active > 0,
    }
    try:
        _atomic_write(CACHE / 'wave21c-alarm-bridge.json', summary)
    except OSError:
        pass
    return summary


def self_test() -> int:
    failures = []
    a, msg = _is_alarm('loop-stability-composite.json', {'alarm': True, 'alarm_reason': 'x'}, 'alarm')
    if not a:
        failures.append('composite alarm')
    a, _ = _is_alarm('governance-conflict-summary.json', {'n_conflicts': 2}, None)
    if not a:
        failures.append('conflicts')
    a, _ = _is_alarm('loop-model-comparison.json', {'recommendation': 'keep_pid'}, None)
    if a:
        failures.append('keep_pid should not alarm')
    a, _ = _is_alarm('shadow-sprt-decisions.json', {'decisions': [{'error_rate_veto': True}]}, None)
    if not a:
        failures.append('veto should alarm')
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
    print(json.dumps({'n_sources': out['n_sources'], 'n_active': out['n_active'], 'alarm': out['alarm']}))
    return 0  # cron-safe; aggregator owns exit-1


if __name__ == '__main__':
    sys.exit(main())
