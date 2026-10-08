#!/usr/bin/env python3
"""loop-pid-iss-wrapper.py — Composite Lyapunov + ISS + two-timescale check.

Khalil Nonlinear Systems Ch 9 (ISS), Sontag ISS small-gain, Khalil Ch 11
two-time-scale singular perturbation. loop-pid.py is Hermes-owned
(~/.hermes/scripts/); this wrapper does not patch it.

Calls, in order:
  1. loop-pid.py lyapunov-check  (falls back to --check)
  2. iss-small-gain-check.py --check  (falls back to default run)
  3. two-timescale-check.py --check   (falls back to default run)

Merges {lyapunov_ok, iss_ok, two_timescale_ok, overall_ok}.
ALARM if any check fails. Writes cache/loop-stability-composite.json.

Usage:
  python3 loop-pid-iss-wrapper.py --self-test
  python3 loop-pid-iss-wrapper.py [--check]
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base

OUT_PATH = _hermes_root / 'cache' / 'loop-stability-composite.json'
PYTHON = sys.executable or 'python3'


def _atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    os.replace(tmp, path)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _find_script(name: str) -> Path | None:
    candidates = [
        _hermes_base / 'scripts' / name,
        _hermes_base / 'hermes-scripts' / name,
        _hermes_root / 'scripts' / name,
        Path(__file__).resolve().parent / name,
    ]
    for p in candidates:
        try:
            if p.is_file():
                return p
        except OSError:
            continue
    return None


def _extract_json(stdout: str) -> dict:
    """Take the last JSON object printed on stdout."""
    text = (stdout or '').strip()
    if not text:
        return {}
    # Prefer last complete {...} block
    last = None
    buf = []
    depth = 0
    for ch in text:
        if ch == '{':
            if depth == 0:
                buf = ['{']
            else:
                buf.append(ch)
            depth += 1
        elif ch == '}':
            if depth:
                buf.append(ch)
                depth -= 1
                if depth == 0:
                    last = ''.join(buf)
        elif depth:
            buf.append(ch)
    if last:
        try:
            obj = json.loads(last)
            return obj if isinstance(obj, dict) else {}
        except json.JSONDecodeError:
            pass
    for line in reversed(text.splitlines()):
        line = line.strip()
        if line.startswith('{') and line.endswith('}'):
            try:
                obj = json.loads(line)
                if isinstance(obj, dict):
                    return obj
            except json.JSONDecodeError:
                continue
    return {}


def _run_argv(argv: list[str], timeout: int = 60) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=os.environ.copy(),
        )
        return proc.returncode, proc.stdout or '', proc.stderr or ''
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 2, '', str(exc)


def run_loop_pid_check(script: Path | None) -> dict:
    result = {
        'ok': False,
        'available': False,
        'rc': None,
        'parsed': {},
        'argv': [],
        'error': None,
    }
    if script is None:
        result['error'] = 'loop-pid.py not found'
        return result
    attempts = [
        [PYTHON, str(script), 'lyapunov-check'],
        [PYTHON, str(script), '--check'],
        [PYTHON, str(script), 'status'],
    ]
    last_rc, last_out, last_err = 2, '', ''
    for argv in attempts:
        rc, out, err = _run_argv(argv)
        last_rc, last_out, last_err = rc, out, err
        parsed = _extract_json(out)
        # argparse unknown-arg typically rc=2
        if rc == 2 and 'unrecognized' in (err + out).lower():
            continue
        result['available'] = True
        result['rc'] = rc
        result['parsed'] = parsed
        result['argv'] = argv[2:]
        if 'lyapunov_stable' in parsed:
            result['ok'] = bool(parsed.get('lyapunov_stable')) and rc == 0
            return result
        if 'lyapunov_ok' in parsed:
            result['ok'] = bool(parsed.get('lyapunov_ok')) and rc == 0
            return result
        if parsed.get('error') == 'insufficient_history':
            # Not a stability failure — observability gap (Khalil). Treat as
            # not-ok for composite but tagged so ALARM is observability not ISS.
            result['ok'] = False
            result['error'] = 'insufficient_history'
            return result
        if rc == 0:
            result['ok'] = True
            return result
        # non-zero with parsed payload: fail
        if parsed:
            result['ok'] = False
            return result
    result['available'] = True
    result['rc'] = last_rc
    result['parsed'] = _extract_json(last_out)
    result['error'] = (last_err or last_out)[:400] or 'loop-pid check failed'
    result['ok'] = last_rc == 0
    return result


def run_simple_check(script: Path | None, label: str) -> dict:
    result = {
        'ok': False,
        'available': False,
        'rc': None,
        'parsed': {},
        'argv': [],
        'error': None,
    }
    if script is None:
        result['error'] = f'{label} not found'
        return result
    for extra in (['--check'], []):
        argv = [PYTHON, str(script), *extra]
        rc, out, err = _run_argv(argv)
        if rc == 2 and 'unrecognized' in (err + out).lower():
            continue
        parsed = _extract_json(out)
        result['available'] = True
        result['rc'] = rc
        result['parsed'] = parsed
        result['argv'] = extra
        if label == 'iss':
            if 'small_gain_ok' in parsed:
                result['ok'] = bool(parsed.get('small_gain_ok')) and rc == 0
                return result
        if label == 'two_timescale':
            if 'ok' in parsed:
                result['ok'] = bool(parsed.get('ok')) and rc == 0
                return result
        result['ok'] = rc == 0
        return result
    result['error'] = f'{label} check failed'
    return result


def merge_results(lyap: dict, iss: dict, ts: dict) -> dict:
    lyapunov_ok = bool(lyap.get('ok'))
    iss_ok = bool(iss.get('ok'))
    two_timescale_ok = bool(ts.get('ok'))
    overall_ok = lyapunov_ok and iss_ok and two_timescale_ok
    alarm = not overall_ok
    return {
        'ts': _now(),
        'theorem': 'Khalil Ch 9 ISS small-gain + Lyapunov decrease; Khalil Ch 11 two-time-scale',
        'lyapunov_ok': lyapunov_ok,
        'iss_ok': iss_ok,
        'two_timescale_ok': two_timescale_ok,
        'overall_ok': overall_ok,
        'alarm': alarm,
        'alarm_reason': None if overall_ok else 'one or more stability checks failed',
        'components': {
            'lyapunov': {k: lyap.get(k) for k in ('ok', 'available', 'rc', 'error', 'argv')},
            'iss': {k: iss.get(k) for k in ('ok', 'available', 'rc', 'error', 'argv')},
            'two_timescale': {k: ts.get(k) for k in ('ok', 'available', 'rc', 'error', 'argv')},
        },
        'lyapunov_detail': lyap.get('parsed') or {},
        'iss_detail': iss.get('parsed') or {},
        'two_timescale_detail': ts.get('parsed') or {},
    }


def run() -> dict:
    lyap = run_loop_pid_check(_find_script('loop-pid.py'))
    iss = run_simple_check(_find_script('iss-small-gain-check.py'), 'iss')
    ts = run_simple_check(_find_script('two-timescale-check.py'), 'two_timescale')
    merged = merge_results(lyap, iss, ts)
    try:
        _atomic_write(OUT_PATH, merged)
        merged['output'] = str(OUT_PATH)
    except OSError as exc:
        merged['write_error'] = str(exc)
    return merged


def self_test() -> int:
    failures = []
    ok_all = merge_results({'ok': True}, {'ok': True}, {'ok': True})
    if not ok_all['overall_ok'] or ok_all['alarm']:
        failures.append('all-ok should have overall_ok and no alarm')
    bad = merge_results({'ok': True}, {'ok': False}, {'ok': True})
    if bad['overall_ok'] or not bad['alarm'] or bad['iss_ok']:
        failures.append('iss fail should alarm')
    parsed = _extract_json('noise\n{"lyapunov_stable": true, "x": 1}\n')
    if parsed.get('lyapunov_stable') is not True:
        failures.append('json extract failed')
    # missing child scripts must not raise
    missing = run_loop_pid_check(None)
    if missing.get('ok') or missing.get('available'):
        failures.append('missing loop-pid should be unavailable')
    if failures:
        print(json.dumps({'self_test': 'FAIL', 'failures': failures}))
        return 1
    print(json.dumps({'self_test': 'PASS', 'n_checks': 4}))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument('--self-test', action='store_true')
    p.add_argument('--check', action='store_true', help='run composite check (default)')
    args = p.parse_args(argv)
    if args.self_test:
        return self_test()
    out = run()
    print(json.dumps({
        'lyapunov_ok': out['lyapunov_ok'],
        'iss_ok': out['iss_ok'],
        'two_timescale_ok': out['two_timescale_ok'],
        'overall_ok': out['overall_ok'],
        'alarm': out['alarm'],
        'output': out.get('output'),
    }))
    if out.get('alarm'):
        print('ALARM: loop-stability-composite failed')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
