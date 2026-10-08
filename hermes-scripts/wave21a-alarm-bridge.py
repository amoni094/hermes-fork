#!/usr/bin/env python3
"""wave21a-alarm-bridge.py — Re-emit Wave 21A memory/IT reports as *-alarm.json.

alarm-aggregator.py only scans cache/*-alarm.json (2h TTL). Channel-capacity,
Fano, SPRT, conductance, OT, AEP, RD-converse, and recursive 21A extras write
plain JSON; this bridge refreshes sidecars every 15 min.

Usage:
  python3 wave21a-alarm-bridge.py --self-test
  python3 wave21a-alarm-bridge.py
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import os
from pathlib import Path
_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base

CACHE = _hermes_root / 'cache'

# (filename, alarm extractor kind, severity)
SOURCES = [
    ('context-channel-capacity.json', 'alarm_flag', 'HIGH'),
    ('memory-fano-bound.json', 'alarm_flag', 'HIGH'),
    ('compaction-rd-converse.json', 'alarm_flag', 'HIGH'),
    ('compaction-aep-typical-set.json', 'alarm_flag', 'MEDIUM'),
    ('memory-conductance-ttl.json', 'conductance', 'MEDIUM'),
    ('memory-adaptive-rank.json', 'rank', 'LOW'),
    ('memory-ot-decay.json', 'alarm_flag', 'MEDIUM'),  # ADV21-016: W1/decay_needed
    ('memory-ttl-floor-merge.json', 'alarm_flag', 'MEDIUM'),  # WIRE-004
    ('compaction-chain-rule-mi.json', 'alarm_flag', 'MEDIUM'),
    ('memory-sanov-ld.json', 'alarm_flag', 'MEDIUM'),
    ('memory-optional-stopping.json', 'alarm_flag', 'HIGH'),
    ('memory-dkw-ue.json', 'alarm_flag', 'MEDIUM'),
    ('memory-jl-distortion.json', 'alarm_flag', 'MEDIUM'),
    ('memory-hitting-time.json', 'alarm_flag', 'LOW'),
    ('memory-haar-mra.json', 'alarm_flag', 'LOW'),
    ('memory-displacement-convexity.json', 'alarm_flag', 'MEDIUM'),
    ('memory-bethe-free-energy.json', 'alarm_flag', 'LOW'),
    ('memory-lp-dct-gate.json', 'alarm_flag', 'MEDIUM'),
    ('memory-malliavin-ibp.json', 'alarm_flag', 'LOW'),
    ('memory-kraft-code.json', 'alarm_flag', 'MEDIUM'),
    ('memory-matrix-bernstein.json', 'alarm_flag', 'LOW'),
    ('memory-gelman-shrink.json', 'alarm_flag', 'LOW'),
    ('memory-log-ode-sig.json', 'alarm_flag', 'LOW'),
    ('memory-bits-back.json', 'alarm_flag', 'LOW'),
    ('memory-portmanteau.json', 'alarm_flag', 'MEDIUM'),
    ('memory-heisenberg-tf.json', 'alarm_flag', 'LOW'),
    ('memory-renorm-counterterm.json', 'alarm_flag', 'LOW'),
    ('kl-curvature-alarm.json', 'alarm_flag', 'HIGH'),  # ADV21-011 / kind=alarm was a no-op
    ('memory-signature-rerank.json', 'alarm_flag', 'LOW'),  # ADV21-019
]


def _atomic_write(path: Path, data: dict) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + '.tmp')
        tmp.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
        os.replace(tmp, path)
    except Exception:
        pass


def _load(name: str):
    p = CACHE / name
    try:
        if not p.exists():
            return None
        obj = json.loads(p.read_text(encoding='utf-8'))
        return obj
    except Exception:
        return None


def _load_jsonl_last(name: str) -> dict:
    p = CACHE / name
    last = {}
    try:
        if not p.exists():
            return last
        for line in p.read_text(encoding='utf-8', errors='replace').splitlines():
            s = line.strip()
            if not s.startswith('{'):
                continue
            try:
                obj = json.loads(s)
            except Exception:
                continue
            if isinstance(obj, dict):
                last = obj
    except Exception:
        return last
    return last


def is_alarm(kind: str, data) -> tuple:
    if data is None:
        return False, 'missing'
    if not isinstance(data, dict):
        return False, 'not_dict'
    if kind in ('alarm_flag', 'alarm'):
        a = bool(data.get('alarm'))
        return a, str(data.get('reason') or data.get('msg') or data.get('note') or ('alarm' if a else 'ok'))
    if kind == 'conductance':
        phi = data.get('conductance')
        try:
            phi_f = float(phi)
        except (TypeError, ValueError):
            return False, 'ok'
        # Cheeger near-zero => mixing / TTL floor blows up
        if phi_f < 1e-4:
            return True, f'conductance={phi_f}'
        return False, f'conductance={phi_f}'
    if kind == 'rank':
        ve = data.get('variance_explained')
        try:
            v = float(ve)
        except (TypeError, ValueError):
            return False, 'ok'
        if 0.0 < v < 0.9:
            return True, f'variance_explained={v}'
        return False, 'ok'
    if kind == 'pinsker':
        # Back-compat: prefer W1/alarm over pinsker_ok (ADV21-016)
        if data.get('alarm') is True or data.get('decay_needed') is True:
            return True, str(data.get('reason') or 'w1_geodesic_displacement')
        try:
            w1 = float(data.get('w1_distance') or 0.0)
        except (TypeError, ValueError):
            w1 = 0.0
        if w1 > 0.25:
            return True, f'w1={w1}'
        return False, 'ok'
    return False, 'ok'


def sprt_alarm() -> tuple:
    last = _load_jsonl_last('memory-sprt-decisions.jsonl')
    if not last:
        return False, 'missing'
    if last.get('decision') == 'DENY':
        return True, f"sprt_deny llr={last.get('llr')}"
    return False, str(last.get('decision') or 'ok')


def emit_sidecar(stem: str, alarm: bool, severity: str, msg: str) -> dict:
    payload = {
        'alarm': bool(alarm),
        'severity': severity if alarm else 'ok',
        'msg': msg,
        'reason': msg,
        'source': stem,
        'ts': datetime.now(timezone.utc).isoformat(),
        'theorem': 'alarm-aggregator *-alarm.json contract; 2h TTL refresh',
    }
    out = CACHE / f'wave21a-{stem}-alarm.json'
    _atomic_write(out, payload)
    payload['output'] = str(out)
    return payload


def run() -> dict:
    emitted = []
    n_active = 0
    for fname, kind, sev in SOURCES:
        data = _load(fname)
        alarm, msg = is_alarm(kind, data)
        stem = fname.replace('.json', '')
        rec = emit_sidecar(stem, alarm, sev, msg)
        emitted.append({'source': fname, 'alarm': alarm})
        if alarm:
            n_active += 1
    sa, sm = sprt_alarm()
    emit_sidecar('memory-sprt-decisions', sa, 'HIGH', sm)
    emitted.append({'source': 'memory-sprt-decisions.jsonl', 'alarm': sa})
    if sa:
        n_active += 1
    summary = {
        'ts': datetime.now(timezone.utc).isoformat(),
        'n_sources': len(SOURCES) + 1,
        'n_active': n_active,
        'emitted': emitted,
        'alarm': n_active > 0,
    }
    _atomic_write(CACHE / 'wave21a-alarm-bridge.json', summary)
    return summary


def self_test() -> int:
    a, _ = is_alarm('alarm_flag', {'alarm': True, 'reason': 'x'})
    assert a is True
    a, _ = is_alarm('alarm_flag', {'alarm': False})
    assert a is False
    a, _ = is_alarm('conductance', {'conductance': 1e-6})
    assert a is True
    a, _ = is_alarm('conductance', {'conductance': 0.2})
    assert a is False
    a, _ = is_alarm('rank', {'variance_explained': 0.5})
    assert a is True
    a, _ = is_alarm('rank', {'variance_explained': 0.95})
    assert a is False
    a, _ = is_alarm('pinsker', {'w1_distance': 0.9, 'decay_needed': True, 'alarm': True})
    assert a is True
    a, _ = is_alarm('pinsker', {'w1_distance': 0.0, 'pinsker_ok': False})
    assert a is False  # pinsker_ok alone must not alarm
    a, _ = is_alarm('alarm', {'alarm': True})
    assert a is True
    a, _ = is_alarm('alarm_flag', None)
    assert a is False
    print('PASS wave21a-alarm-bridge self-test')
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--self-test', action='store_true')
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    try:
        out = run()
        print(json.dumps({'n_sources': out['n_sources'], 'n_active': out['n_active'], 'alarm': out['alarm']}))
        return 0
    except Exception as exc:
        print(json.dumps({'alarm': False, 'fail_open': str(exc)}))
        return 0


if __name__ == '__main__':
    raise SystemExit(main())
