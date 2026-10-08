#!/usr/bin/env python3
"""routing-alarm-bridge.py — promote routing JSON `alarm` flags to *-alarm.json.

Consumes cache/routing-*.json, skill-description-entropy.json, skill-composition-gf.json,
routing-conflicts.jsonl. Writes cache/<stem>-alarm.json so alarm-aggregator glob picks them up.
Does not rewrite files already named *-alarm.json.

Source: Wave 21B saturation (wiring / dark-output close).
"""
from __future__ import annotations
import argparse
import json
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


def _severity(data: dict) -> str:
    if str(data.get('severity', '')).upper() in ('HIGH', 'MEDIUM', 'LOW'):
        return str(data['severity']).upper()
    blob = json.dumps(data).lower()
    if data.get('impossible') or data.get('status') == 'IMPOSSIBLE':
        return 'HIGH'
    if any(k in blob for k in ('critical', 'impossible', 'threshold_breach', 'replica_symmetry')):
        return 'HIGH'
    if data.get('alarm') or data.get('conflict') or data.get('rsb'):
        if any(k in blob for k in ('fragmented', 'clique', 'degenerate', 'stuck', 'blowup')):
            return 'MEDIUM'
        return 'LOW'
    return 'INFO'


def _is_active(data: dict) -> bool:
    if data.get('alarm') is True:
        return True
    if data.get('conflict') is True:
        return True
    if data.get('rsb') is True:
        return True
    if data.get('impossible') is True:
        return True
    if data.get('status') in ('IMPOSSIBLE', 'IMPROVEMENT_POSSIBLE'):
        return True
    if int(data.get('n_flagged') or 0) > 0:
        return True
    alarms = data.get('alarms')
    if isinstance(alarms, list) and len(alarms) > 0:
        return True
    return False


def _candidates(cache: Path) -> list:
    out = []
    for pat in ('routing-*.json', 'skill-description-entropy.json', 'skill-composition-gf.json'):
        out.extend(cache.glob(pat))
    # unique, skip alarm/summary/state dumps that already match glob
    seen = set()
    files = []
    for p in out:
        if p.name in seen:
            continue
        seen.add(p.name)
        if p.name.endswith('-alarm.json'):
            continue
        if p.name in ('alarm-summary.json',):
            continue
        files.append(p)
    return files


def promote(cache: Path) -> dict:
    promoted = []
    skipped = []
    for fpath in _candidates(cache):
        try:
            data = json.loads(fpath.read_text())
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        stem = fpath.stem
        dest = cache / (stem + '-alarm.json')
        active = _is_active(data)
        payload = {
            'source': stem,
            'alarm': bool(active),
            'severity': _severity(data) if active else 'INFO',
            'reason': data.get('reason') or data.get('status') or ('alarm' if active else 'ok'),
            'ts': time.time(),
            'bridged_from': fpath.name,
        }
        # ADV21-010: always rewrite sidecar (alarm=true or false) so 2h TTL window stays open
        if active:
            payload['msg'] = payload['reason']
        _atomic_write_json(dest, payload)
        if active:
            promoted.append(stem)
        else:
            skipped.append(stem)
    # conflicts jsonl
    cl = cache / 'routing-conflicts.jsonl'
    n_conf = 0
    if cl.exists():
        try:
            cutoff = time.time() - 86400.0
            n_conf = 0
            for line in cl.read_text(encoding='utf-8', errors='replace').splitlines():
                try:
                    row = json.loads(line)
                    if float(row.get('ts', 0)) >= cutoff:
                        n_conf += 1
                except Exception:
                    pass
        except OSError:
            n_conf = 0
        if n_conf > 0:
            payload = {
                'source': 'routing-conflicts',
                'alarm': True,
                'severity': 'MEDIUM',
                'reason': 'exp3_bm25_disagreement',
                'n_conflicts': n_conf,
                'ts': time.time(),
                'bridged_from': 'routing-conflicts.jsonl',
            }
            _atomic_write_json(cache / 'routing-conflicts-alarm.json', payload)
            promoted.append('routing-conflicts')
    return {
        'ts': time.time(),
        'promoted': promoted,
        'skipped': skipped,
        'n_promoted': len(promoted),
        'alarm': len(promoted) > 0,
        'reason': 'promoted' if promoted else 'ok',
    }


def run(cache=None) -> dict:
    cache = cache or _cache_dir()
    result = promote(cache)
    try:
        _atomic_write_json(cache / 'routing-alarm-bridge.json', result)
    except Exception:
        pass
    return result


def self_test() -> dict:
    failures = []
    try:
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d / 'routing-pac-bayes.json').write_text(json.dumps({
                'alarm': True, 'reason': 'gen_error_bound>0.3', 'gen_error_bound': 0.5
            }))
            (d / 'routing-ok.json').write_text(json.dumps({'alarm': False, 'reason': 'ok'}))
            (d / 'routing-hamming-alarm.json').write_text(json.dumps({'alarm': True}))
            import time as _t2
            (d / 'routing-conflicts.jsonl').write_text(json.dumps({'alarm':'CONFLICT','ts':_t2.time()}) + '\n')
            r = run(cache=d)
            assert (d / 'routing-pac-bayes-alarm.json').exists()
            alarm = json.loads((d / 'routing-pac-bayes-alarm.json').read_text())
            assert alarm['alarm'] is True
            # ADV21-010: always-rewrite means ok-alarm.json exists with alarm=False
            if (d / 'routing-ok-alarm.json').exists():
                ok_data = json.loads((d / 'routing-ok-alarm.json').read_text())
                assert ok_data['alarm'] is False, f"ok sidecar should have alarm=False: {ok_data}"
            # already *-alarm.json must not be re-bridged as *-alarm-alarm
            assert not (d / 'routing-hamming-alarm-alarm.json').exists()
            assert (d / 'routing-conflicts-alarm.json').exists()
            json.dumps(r)
    except Exception as e:
        failures.append(f'bridge: {e}')
    try:
        with tempfile.TemporaryDirectory() as td:
            r = run(cache=Path(td))
            assert r['n_promoted'] == 0
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
