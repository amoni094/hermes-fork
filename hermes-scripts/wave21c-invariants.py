#!/usr/bin/env python3
"""wave21c-invariants.py — Nipkow-style property tests for Wave 21C/21D.

Runs --self-test on theorem-backed modules plus extra invariant checks.
Fail-closed.
"""
from __future__ import annotations

import ast
import json
import math
import os
import subprocess
import sys
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base

SCRIPTS = [
    'loop-pid-iss-wrapper.py',
    'shadow-gate-sprt.py',
    'governance-conflict-detector.py',
    'governance-falsifiability-lint.py',
    'counterfactual-tool-gate.py',
    'loop-model-comparison.py',
    'callgraph-taint-audit.py',
    'nyquist-timescale-bridge.py',
    'loop-cusum-changepoint.py',
    'impact-regularizer-gate.py',
    'wave21c-alarm-bridge.py',
    'sprt-falsifiability-handshake.py',
    'governance-conflict-epistemic.py',
    'pid-passivity-index.py',
    'pid-circle-criterion.py',
    'session-type-tool-protocol.py',
    'ltl-promotion-invariant.py',
    'loop-rollout-horizon.py',
    'sprt-measurement-tamper.py',
    'soares-halt-liveness.py',
    'cusum-gain-freeze.py',
    'sprt-inner-outer-alignment.py',
    'iss-justification-gate.py',
    'sprt-truncation-gate.py',
    'promotion-at-most-once.py',
    'sprt-effective-decision.py',
]
FORBIDDEN = {'numpy', 'scipy', 'pandas', 'sklearn', 'torch', 'requests', 'yaml'}


def here() -> Path:
    return Path(__file__).resolve().parent


def check_imports(path: Path) -> list[str]:
    issues = []
    try:
        tree = ast.parse(path.read_text(encoding='utf-8'))
    except Exception as exc:
        return [f'parse:{exc}']
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name.split('.')[0] in FORBIDDEN:
                    issues.append(f'import {a.name}')
        elif isinstance(node, ast.ImportFrom) and node.module:
            if node.module.split('.')[0] in FORBIDDEN:
                issues.append(f'from {node.module}')
    return issues


def extra_invariants() -> list[str]:
    fails = []
    # Wald bounds
    A = math.log(19.0)
    B = math.log(1.0 / 19.0)
    if abs(A + B) > 1e-12:
        fails.append('A != -B')
    # G(PROMOTE -> FO)
    sys.path.insert(0, str(here()))
    import importlib.util

    def load(name):
        spec = importlib.util.spec_from_file_location(name, here() / f'{name}.py')
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return m

    ltl = load('ltl-promotion-invariant')
    r = ltl.model_check([{'decision': 'PROMOTE'}])
    if r['satisfied']:
        fails.append('vacuous FO missing')
    hs = load('sprt-falsifiability-handshake')
    r2 = hs.handshake([{'flag': 'x', 'decision': 'PROMOTE'}], [])
    if not r2['alarm']:
        fails.append('handshake missed bare PROMOTE')
    st = load('session-type-tool-protocol')
    if not st.check_protocol(['patch'])['alarm']:
        fails.append('session patch')
    if st.check_protocol(['read_file', 'patch'])['alarm']:
        fails.append('session read-patch')
    cf = load('counterfactual-tool-gate')
    seq = cf.analyze_sequence(['read_file', 'read_file', 'write_file'])
    if not seq.get('redundant_tools'):
        fails.append('C5 redundant')
    fr = load('cusum-gain-freeze')
    if not fr.decide(True, False, False)['freeze_kp']:
        fails.append('freeze kp')
    return fails


def main() -> int:
    d = here()
    failures = []
    n_ok = 0
    for name in SCRIPTS:
        p = d / name
        if not p.is_file():
            failures.append(f'missing {name}')
            continue
        issues = check_imports(p)
        if issues:
            failures.append(f'{name} imports {issues}')
        r = subprocess.run([sys.executable, str(p), '--self-test'],
                           capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            failures.append(f'{name} self-test rc={r.returncode}')
        else:
            n_ok += 1
    failures.extend(extra_invariants())
    out = {'self_test': 'FAIL' if failures else 'PASS', 'n_ok': n_ok, 'n': len(SCRIPTS), 'failures': failures,
           'alarm': bool(failures), 'reason': 'invariant_failures' if failures else 'ok'}
    print(json.dumps(out))
    # ADV21-020: persist report + alarm sidecar so aggregator tracks invariant breaks
    try:
        import time as _t
        out['ts'] = _t.time()
        report_path = _hermes_root / 'cache' / 'wave21c-invariants.json'
        tmp_r = report_path.with_suffix('.tmp')
        tmp_r.write_text(json.dumps(out, ensure_ascii=False))
        os.replace(tmp_r, report_path)
        alarm_payload = {'alarm': bool(failures), 'n_failures': len(failures),
                         'n_ok': n_ok, 'ts': out['ts'],
                         'reason': 'invariant_failures' if failures else 'ok'}
        alarm_path = _hermes_root / 'cache' / 'wave21c-invariants-alarm.json'
        tmp_a = alarm_path.with_suffix('.tmp')
        tmp_a.write_text(json.dumps(alarm_payload, ensure_ascii=False))
        os.replace(tmp_a, alarm_path)
    except Exception:
        pass
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
