#!/usr/bin/env python3
"""impact-regularizer-gate.py — Amodei cat.3 side-effect footprint.

Complements counterfactual-tool-gate.py (redundant reads) with a write/exec
ratio check: side-effecting tools / total tools. Ratio > 0.5 => WARN.

Usage:
  python3 impact-regularizer-gate.py --self-test
  python3 impact-regularizer-gate.py --sequence read_file,write_file,terminal
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base


SIDE_EFFECT = {
    'write_file', 'patch', 'terminal', 'execute_code', 'skill_manage',
    'browser_click', 'browser_type', 'tool_call', 'process_manage',
    'os.replace', 'shutil.move',
}
READ_ONLY = {
    'read_file', 'search_files', 'web_search', 'web_extract', 'hermes_web_search',
    'browser_navigate', 'browser_snapshot', 'skill_view', 'tool_describe',
    'vision_analyze', 'session_search', 'todo_list',
}
WARN_RATIO = 0.5


def analyze(tools: list[str]) -> dict:
    names = [str(t).strip() for t in tools if str(t).strip()]
    n_side = sum(1 for t in names if t in SIDE_EFFECT)
    n_read = sum(1 for t in names if t in READ_ONLY)
    total = len(names) if names else 0
    ratio = (n_side / total) if total else 0.0
    return {
        'sequence': names,
        'n_side_effect': n_side,
        'n_read_only': n_read,
        'side_effect_ratio': ratio,
        'alarm': ratio > WARN_RATIO,
        'theorem': 'Amodei Concrete Problems cat.3 impact regularizer / minimal footprint',
    }


def self_test() -> int:
    failures = []
    r = analyze(['read_file', 'write_file', 'terminal'])
    if abs(r['side_effect_ratio'] - 2 / 3) > 1e-9 or not r['alarm']:
        failures.append(f'expected 2/3 alarm, got {r}')
    r2 = analyze(['read_file', 'search_files', 'write_file'])
    if r2['alarm']:
        failures.append('1/3 should not alarm')
    if failures:
        print(json.dumps({'self_test': 'FAIL', 'failures': failures}))
        return 1
    print(json.dumps({'self_test': 'PASS'}))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument('--self-test', action='store_true')
    p.add_argument('--sequence', default='')
    args = p.parse_args(argv)
    if args.self_test:
        return self_test()
    seq = [t for t in args.sequence.split(',') if t.strip()]
    out = analyze(seq)
    print(json.dumps(out, indent=2))
    # ADV21-012: persist alarm JSON when called with a sequence (not no-arg cron)
    if seq:
        try:
            import time as _t
            alarm_path = _hermes_root / 'cache' / 'impact-regularizer-alarm.json'
            payload = {'alarm': bool(out.get('alarm')), 'ratio': out.get('side_effect_ratio'),
                       'ts': _t.time(), 'reason': 'high_side_effect_ratio' if out.get('alarm') else 'ok'}
            tmp_a = alarm_path.with_suffix('.tmp')
            tmp_a.write_text(json.dumps(payload, ensure_ascii=False))
            os.replace(tmp_a, alarm_path)
        except Exception:
            pass
    return 1 if out.get('alarm') else 0


if __name__ == '__main__':
    sys.exit(main())
