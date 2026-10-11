#!/usr/bin/env python3
"""loop-pid-iss-wrapper.py — Composite Lyapunov + ISS + two-timescale check.

Khalil Nonlinear Systems Ch 9 (ISS), Sontag ISS small-gain, Khalil Ch 11
two-time-scale singular perturbation. loop-pid.py is Hermes-owned
(~/.hermes/scripts/); this wrapper does not patch it.

Calls, in order:
  1. loop-pid.py lyapunov-check  (falls back to --check)
  2. iss-small-gain-check.py --check  (falls back to default run)
  3. two-timescale-check.py --check   (falls back to default run)

Merges {lyapunov_ok, iss_ok, two_timescale_ok, justification_ok, overall_ok}.

overall_ok = lyapunov_ok AND iss_ok AND two_timescale_ok AND justification_ok.
justification_ok delegates to iss-justification-gate.py (passivity + circle + nyquist).
Missing gate files -> justification_ok = False (fail-closed, per ADV21-013 / WIRE-016).
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


def interpret_loop_pid_json(parsed: dict, rc: int) -> dict:
    """Map loop-pid JSON + rc to a lyapunov result. Never infer ok from rc==0.

    ADV2-008: JSON with only status=ok and rc=0 is NOT a Lyapunov pass.
    ADV2-014: status=insufficient_data is unmeasured (ok=None), not ok=True.
    """
    result = {
        'ok': False,
        'available': True,
        'rc': rc,
        'parsed': parsed if isinstance(parsed, dict) else {},
        'argv': [],
        'error': None,
    }
    parsed = result['parsed']
    if 'lyapunov_stable' in parsed:
        result['ok'] = bool(parsed.get('lyapunov_stable')) and rc == 0
        result['lyapunov_status'] = 'lyapunov_ok' if result['ok'] else 'lyapunov_fail'
        return result
    if 'lyapunov_ok' in parsed:
        result['ok'] = bool(parsed.get('lyapunov_ok')) and rc == 0
        result['lyapunov_status'] = 'lyapunov_ok' if result['ok'] else 'lyapunov_fail'
        return result
    if (
        parsed.get('error') == 'insufficient_history'
        or parsed.get('insufficient_history')
        or parsed.get('status') == 'insufficient_data'
    ):
        result['ok'] = None
        result['error'] = parsed.get('error') or 'insufficient_history'
        result['lyapunov_status'] = 'lyapunov_insufficient_data'
        return result
    result['ok'] = False
    result['reason'] = 'no_lyapunov_certificate'
    result['lyapunov_status'] = 'no_lyapunov_certificate'
    return result


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
        interpreted = interpret_loop_pid_json(parsed, rc)
        interpreted['available'] = True
        interpreted['argv'] = argv[2:]
        return interpreted
    result['available'] = True
    result['rc'] = last_rc
    result['parsed'] = _extract_json(last_out)
    result['error'] = (last_err or last_out)[:400] or 'loop-pid check failed'
    result['ok'] = False
    result['reason'] = 'no_lyapunov_certificate'
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


def run_iss_justification(script: Path | None) -> dict | None:
    """Run iss-justification-gate.py. Missing or failed script -> None (WIRE-016).

    Staleness check: if the justification gate script exists but the prereq cache files
    (pid-passivity-index.json, pid-circle-criterion.json, nyquist-timescale-bridge.json)
    are older than MAX_PREREQ_AGE_HOURS hours, log the staleness reason separately but
    still fail-closed to avoid silently passing on stale data.
    """
    MAX_PREREQ_AGE_HOURS = 4
    if script is None:
        return None
    # Check prereq cache file ages (fail-closed if stale)
    script_dir = script.parent if script else None
    if script_dir is not None:
        # Prereq cache files: passivity, circle, nyquist (NOT composite — gate no longer reads it)
        _hermes_home = Path(os.environ.get('HERMES_HOME', Path.home() / '.hermes'))
        _profile = os.environ.get('HERMES_PROFILE', '')
        if _profile:
            cache_dir = _hermes_home / 'profiles' / _profile / 'cache'
        else:
            cache_dir = _hermes_home / 'cache'
        prereq_files = [
            cache_dir / 'pid-passivity-index.json',
            cache_dir / 'pid-circle-criterion.json',
            cache_dir / 'nyquist-timescale-bridge.json',
        ]
        import time as _time
        stale = []
        for pf in prereq_files:
            try:
                age_h = (_time.time() - pf.stat().st_mtime) / 3600
                if age_h > MAX_PREREQ_AGE_HOURS:
                    stale.append(f'{pf.name}(age={age_h:.1f}h)')
            except OSError:
                pass  # missing handled by iss-justification-gate itself (fail-closed)
        if stale:
            return {
                'justified_ok': False,
                'alarm': True,
                'reason': f'prereq cache files stale (>{MAX_PREREQ_AGE_HOURS}h): {", ".join(stale)}',
                'stale_prereqs': stale,
            }
    rc, out, err = _run_argv([PYTHON, str(script)])
    parsed = _extract_json(out)
    if not parsed:
        # gate unavailable -> None so merge_results fail-closes (WIRE-016)
        return None
    return parsed


def merge_results(lyap: dict, iss: dict, ts: dict, justification: dict | None = None) -> dict:
    # lyapunov_ok: True / False / None (None = unmeasured, insufficient_history / insufficient_data).
    # overall_ok is False only on a *measured* Lyapunov failure, not on None.
    parsed = lyap.get('parsed') or {}
    lyap_error = lyap.get('error') or parsed.get('error')
    lyap_status = lyap.get('lyapunov_status') or parsed.get('status')
    if (
        lyap.get('ok') is None
        or lyap_error == 'insufficient_history'
        or lyap_status in ('insufficient_data', 'lyapunov_insufficient_data')
        or parsed.get('status') == 'insufficient_data'
    ):
        lyapunov_ok = None
    else:
        lyapunov_ok = bool(lyap.get('ok'))
    iss_ok = bool(iss.get('ok'))
    two_timescale_ok = bool(ts.get('ok'))
    # WIRE-016 / ADV2-002: missing or failed justification ALWAYS blocks overall_ok.
    # No warning_only path.
    if justification is None:
        justification = {'justified_ok': False, 'alarm': True, 'reason': 'justification_gate_missing'}
        justification_ok = False
        gate_missing = True
    else:
        justification_ok = bool(justification.get('justified_ok'))
        gate_missing = False
    lyapunov_unmeasured = lyapunov_ok is None
    lyapunov_blocks = lyapunov_ok is False
    overall_ok = (not lyapunov_blocks) and iss_ok and two_timescale_ok and justification_ok
    justification_contributing = True
    justification_not_measured = False
    alarm = not overall_ok
    alarm_parts = []
    warning_parts = []
    if lyapunov_blocks:
        alarm_parts.append('lyapunov_fail')
    elif lyapunov_unmeasured:
        warning_parts.append('lyapunov_insufficient_data')
    if not iss_ok:
        alarm_parts.append('iss_small_gain')
    if not two_timescale_ok:
        alarm_parts.append('two_timescale')
    if not justification_ok:
        if gate_missing:
            alarm_parts.append('justification_gate_missing')
        else:
            alarm_parts.append(f"iss_justification({justification.get('reason', 'failed')})")
    lyapunov_status = (
        'lyapunov_insufficient_data' if lyapunov_unmeasured
        else ('lyapunov_ok' if lyapunov_ok else 'lyapunov_fail')
    )
    return {
        'ts': _now(),
        'theorem': (
            'Khalil Ch 9 ISS small-gain + Lyapunov decrease; Khalil Ch 11 two-time-scale; '
            'ADV21-013 passivity/circle/nyquist justification (AUDIT-14: no circular dep)'
        ),
        'lyapunov_ok': lyapunov_ok,
        'lyapunov_status': lyapunov_status,
        'iss_ok': iss_ok,
        'two_timescale_ok': two_timescale_ok,
        'justification_ok': justification_ok,
        'justification_not_measured': justification_not_measured,
        'justification_contributing': justification_contributing,
        'overall_ok': overall_ok,
        'alarm': alarm,
        'alarm_reason': (', '.join(alarm_parts)) if alarm_parts else None,
        'warning': (', '.join(warning_parts)) if warning_parts else None,
        'components': {
            'lyapunov': {k: lyap.get(k) for k in ('ok', 'available', 'rc', 'error', 'argv', 'lyapunov_status')},
            'iss': {k: iss.get(k) for k in ('ok', 'available', 'rc', 'error', 'argv')},
            'two_timescale': {k: ts.get(k) for k in ('ok', 'available', 'rc', 'error', 'argv')},
            'justification': {k: justification.get(k) for k in ('justified_ok', 'alarm', 'reason', 'passivity_ok', 'circle_ok', 'nyquist_ok', 'insufficient_data')},
        },
        'lyapunov_detail': lyap.get('parsed') or {},
        'iss_detail': iss.get('parsed') or {},
        'two_timescale_detail': ts.get('parsed') or {},
        'justification_detail': justification,
    }


def run() -> dict:
    lyap = run_loop_pid_check(_find_script('loop-pid.py'))
    iss = run_simple_check(_find_script('iss-small-gain-check.py'), 'iss')
    ts = run_simple_check(_find_script('two-timescale-check.py'), 'two_timescale')
    # Wire ISS justification gate as a hard 4th component (ADV21-013 / WIRE-016).
    justification = run_iss_justification(_find_script('iss-justification-gate.py'))
    merged = merge_results(lyap, iss, ts, justification)
    try:
        _atomic_write(OUT_PATH, merged)
        merged['output'] = str(OUT_PATH)
    except OSError as exc:
        merged['write_error'] = str(exc)
    return merged


def self_test() -> int:
    failures = []
    just_ok = {'justified_ok': True, 'alarm': False, 'reason': None}
    just_fail = {'justified_ok': False, 'alarm': True, 'reason': 'failed: passivity'}
    just_not_measured = {'justified_ok': False, 'alarm': True, 'reason': 'missing: pid-passivity-index, pid-circle-criterion, nyquist-timescale-bridge; failed:prereqs_missing'}
    just_one_missing = {'justified_ok': False, 'alarm': True, 'reason': 'missing: pid-passivity-index; failed:prereqs_missing'}
    just_stale = {'justified_ok': False, 'alarm': True, 'reason': 'prereq stale', 'stale_prereqs': ['pid-passivity-index.json(age=5.0h)']}

    # 1. All ok: overall_ok=True, no alarm
    ok_all = merge_results({'ok': True}, {'ok': True}, {'ok': True}, just_ok)
    if not ok_all['overall_ok'] or ok_all['alarm']:
        failures.append('all-ok should have overall_ok and no alarm')

    # 2. ISS fails: overall_ok=False, alarm
    bad = merge_results({'ok': True}, {'ok': False}, {'ok': True}, just_ok)
    if bad['overall_ok'] or not bad['alarm'] or bad['iss_ok']:
        failures.append('iss fail should alarm')

    # 3. Justification measured-and-failed: blocks overall_ok
    bad_just = merge_results({'ok': True}, {'ok': True}, {'ok': True}, just_fail)
    if bad_just['overall_ok'] or not bad_just['alarm']:
        failures.append('measured-and-failed justification should block overall_ok')
    if bad_just.get('justification_not_measured'):
        failures.append('measured-and-failed should NOT be flagged as not_measured')

    # 4. ADV2-002 (a): all prereq files missing -> overall_ok=False (no warning_only)
    not_meas = merge_results({'ok': True}, {'ok': True}, {'ok': True}, just_not_measured)
    if not_meas['overall_ok'] or not not_meas['alarm']:
        failures.append('all-missing prereqs must block overall_ok')
    if not_meas.get('justification_ok'):
        failures.append('all-missing prereqs must set justification_ok=False')

    # 4b. ADV2-002 (b): one file missing -> overall_ok=False
    one_miss = merge_results({'ok': True}, {'ok': True}, {'ok': True}, just_one_missing)
    if one_miss['overall_ok'] or not one_miss['alarm']:
        failures.append('one missing prereq must block overall_ok')

    # 5. Stale prereqs: treated as failure (blocks)
    stale_res = merge_results({'ok': True}, {'ok': True}, {'ok': True}, just_stale)
    if stale_res['overall_ok']:
        failures.append('stale justification prereqs should block overall_ok')

    # 6. WIRE-016: justification=None -> overall_ok=False, justification_gate_missing
    no_just = merge_results({'ok': True}, {'ok': True}, {'ok': True})
    if no_just['overall_ok']:
        failures.append('None justification must block overall_ok')
    if 'justification_gate_missing' not in (no_just.get('alarm_reason') or ''):
        failures.append('None justification must set reason justification_gate_missing')

    # 7. JSON extract
    parsed = _extract_json('noise\n{"lyapunov_stable": true, "x": 1}\n')
    if parsed.get('lyapunov_stable') is not True:
        failures.append('json extract failed')

    # 8. Missing child scripts must not raise
    missing = run_loop_pid_check(None)
    if missing.get('ok') or missing.get('available'):
        failures.append('missing loop-pid should be unavailable')

    # 9. Missing justification gate script -> None -> overall_ok=False (WIRE-016)
    miss_just = run_iss_justification(None)
    if miss_just is not None:
        failures.append('missing iss-justification-gate should return None')
    miss_merged = merge_results({'ok': True}, {'ok': True}, {'ok': True}, miss_just)
    if miss_merged['overall_ok']:
        failures.append('iss-justification missing must set overall_ok=False')

    # 10. insufficient_history => lyapunov_ok=None, WARNING not ALARM
    insuf = merge_results(
        {'ok': None, 'error': 'insufficient_history'},
        {'ok': True},
        {'ok': True},
        just_ok,
    )
    if insuf['lyapunov_ok'] is not None:
        failures.append('insufficient_history must set lyapunov_ok=None')
    if insuf.get('lyapunov_status') != 'lyapunov_insufficient_data':
        failures.append('insufficient_history status mismatch')
    if not insuf['overall_ok']:
        failures.append('unmeasured lyapunov must not fail overall_ok')
    if insuf['alarm']:
        failures.append('unmeasured lyapunov must not ALARM')
    if 'lyapunov_insufficient_data' not in (insuf.get('warning') or ''):
        failures.append('unmeasured lyapunov must emit WARNING')

    # 11. measured Lyapunov failure still alarms
    fail_lyap = merge_results({'ok': False}, {'ok': True}, {'ok': True}, just_ok)
    if fail_lyap['lyapunov_ok'] is not False:
        failures.append('measured lyapunov fail must be False not None')
    if fail_lyap['overall_ok'] or not fail_lyap['alarm']:
        failures.append('measured lyapunov fail must ALARM')
    if fail_lyap.get('lyapunov_status') != 'lyapunov_fail':
        failures.append('measured fail status mismatch')

    # 12. ADV2-008: JSON with only status=ok and rc=0 is NOT a Lyapunov pass
    vacuous = interpret_loop_pid_json({'status': 'ok'}, 0)
    if vacuous.get('ok') is not False:
        failures.append('rc==0 without lyapunov cert must set ok=False')
    if vacuous.get('reason') != 'no_lyapunov_certificate':
        failures.append('rc==0 without lyapunov cert must set no_lyapunov_certificate')

    # 13. ADV2-014: status=insufficient_data is unmeasured, not ok=True
    insuf_data = interpret_loop_pid_json({'status': 'insufficient_data'}, 0)
    if insuf_data.get('ok') is not None:
        failures.append('insufficient_data must set ok=None not True/False')
    insuf_merged = merge_results(insuf_data, {'ok': True}, {'ok': True}, just_ok)
    if insuf_merged['lyapunov_ok'] is not None:
        failures.append('insufficient_data merge must set lyapunov_ok=None')
    if insuf_merged['lyapunov_ok'] is True:
        failures.append('insufficient_data must NOT be treated as ok=True')
    if insuf_merged['alarm']:
        failures.append('insufficient_data must be warning not alarm when other gates pass')

    if failures:
        print(json.dumps({'self_test': 'FAIL', 'failures': failures}))
        return 1
    print(json.dumps({'self_test': 'PASS', 'n_checks': 14}))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument('--self-test', action='store_true')
    p.add_argument('--check', action='store_true', help='run composite check (default)')
    args = p.parse_args(argv)
    if args.self_test:
        return self_test()
    out = run()
    payload = {
        'lyapunov_ok': out['lyapunov_ok'],
        'lyapunov_status': out.get('lyapunov_status'),
        'iss_ok': out['iss_ok'],
        'two_timescale_ok': out['two_timescale_ok'],
        'overall_ok': out['overall_ok'],
        'alarm': out['alarm'],
        'warning': out.get('warning'),
        'output': out.get('output'),
    }
    print(json.dumps(payload))
    if out.get('warning') and not out.get('alarm'):
        print('WARNING: ' + str(out.get('warning')))
    if out.get('alarm'):
        print('ALARM: loop-stability-composite failed')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
