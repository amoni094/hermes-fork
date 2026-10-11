#!/usr/bin/env python3
"""iss-justification-gate.py — Passivity/sector/nyquist certificate gate.

Scores ONLY the three geometric conditions required by Khalil ISS composition:
  1. passivity index (pid-passivity-index.json)
  2. sector-bounded nonlinearity / circle criterion (pid-circle-criterion.json)
  3. Nyquist–timescale bridge (nyquist-timescale-bridge.json)

The Lyapunov / ISS / two-timescale certificates are the responsibility of
loop-pid-iss-wrapper.py — this gate does NOT read loop-stability-composite.json.
The wrapper ANDs its own lyapunov_ok/iss_ok/two_timescale_ok with this gate's
justified_ok. Reading composite here would create a circular dependency (deadlock).

ADV21-013 fix (AUDIT-14): removed composite dependency from justify().
ADV2-002: missing prereqs emit failed:prereqs_missing (blocking, not warning).
ADV2-007: vacuous certs (n=0 / omitted n / n<min_n) are invalid.
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
OUT = CACHE / 'iss-justification.json'

CERT_MIN_N = 5


def _atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    os.replace(tmp, path)


def _obs_count(d: dict) -> int | None:
    """Observation count if the prereq JSON records one; None if unknown.

    Passivity/circle use `n`. Nyquist bridge uses `n` or `nyquist_n_aliased`.
    Missing `n` is not treated as zero — that would break unit tests that
    pass only `{alarm: False}` and would also mis-read a valid nyquist
    certificate that simply has zero aliased jobs *after* real sampling.
    """
    if not isinstance(d, dict) or d.get('_missing'):
        return None
    for key in ('n', 'nyquist_n_aliased'):
        if key in d and d[key] is not None:
            try:
                return int(d[key])
            except (TypeError, ValueError):
                continue
    return None


def _cert_valid(data, key_prefix, min_n=CERT_MIN_N) -> bool:
    """ADV2-007: a certificate is valid only if present, not alarming, and n>=min_n.

    Vacuous alarm=false with n=0 or omitted n is NOT a certificate.
    key_prefix is reserved for log context; n-insufficient uses a shared token.
    """
    del key_prefix  # log token is shared: cert_invalid:n_insufficient
    if not isinstance(data, dict) or data.get('_missing'):
        return False
    if data.get('alarm', False):
        return False
    n = _obs_count(data)
    if n is None or n < min_n:
        return False
    return True


def justify(passivity: dict, circle: dict, nyquist_bridge: dict) -> dict:
    """Score passivity/sector/nyquist ONLY. No composite dependency.

    AUDIT-14 fix: the original signature accepted composite as the first arg
    and read composite.overall_ok, creating a circular dependency with
    loop-pid-iss-wrapper.py. The wrapper is responsible for Lyapunov/ISS/
    two-timescale; this gate is responsible only for geometric prerequisites.

    Fail-closed on n=0: alarm=false with n=0 is vacuous (no observations),
    not a certificate. When all three prereqs explicitly report n=0,
    justified_ok=false with reason='insufficient_data: no observations'.
    """
    # ADV21-013 / ADV2-002: missing prereq files => not justified (fail-closed)
    pas_missing = bool(passivity.get('_missing'))
    cir_missing = bool(circle.get('_missing'))
    nyq_missing = bool(nyquist_bridge.get('_missing'))
    n_pas = _obs_count(passivity)
    n_cir = _obs_count(circle)
    n_nyq = _obs_count(nyquist_bridge)
    # Vacuous pass: every prereq file exists and reports zero observations.
    all_zero = (n_pas == 0 and n_cir == 0 and n_nyq == 0)
    if all_zero:
        return {
            'passivity_ok': False,
            'circle_ok': False,
            'nyquist_ok': False,
            'justified_ok': False,
            'alarm': True,
            'insufficient_data': True,
            'n_passivity': n_pas,
            'n_circle': n_cir,
            'n_nyquist': n_nyq,
            'reason': 'insufficient_data: no observations',
            'theorem': 'Khalil ISS small-gain requires ISS (passive, in-sector) subsystems; ADV21-013',
        }
    # Calibrated ceiling for THIS PID (Kp=1, Ki=0.15, Kd=0.4), not a
    # settle-fraction. N_settle≈1/(Ki*Ts)≈7 ⇒ ~0.035 of n≈200 pairs if only
    # windup were non-passive. 0.15 is ~4× that budget (noise around settle)
    # and must NOT be raised to match a live ratio: 0.22 is persistent
    # mid/late violation, a true positive. mean_supply>=0 is not a bypass
    # (W24-ADV-001/002; PID e,u same sign by construction). See
    # profiles/fork/cache/iss-threshold-justification.md.
    VIOLATION_RATIO_MAX = 0.15
    justification_log = []
    violation_ratio = float(passivity.get('violation_ratio', 0.0) or 0.0)
    for d in (passivity, circle, nyquist_bridge):
        if d.get('_missing'):
            continue
        n = _obs_count(d)
        if n is None or n < CERT_MIN_N:
            justification_log.append('cert_invalid:n_insufficient')
    pas_ok = _cert_valid(passivity, 'pas') and (violation_ratio <= VIOLATION_RATIO_MAX)
    if not pas_ok and violation_ratio > VIOLATION_RATIO_MAX:
        justification_log.append(f'passivity_violation_ratio={violation_ratio:.3f} > {VIOLATION_RATIO_MAX}')
    cir_ok = _cert_valid(circle, 'cir')
    nyq_ok = _cert_valid(nyquist_bridge, 'nyq')
    justified = pas_ok and cir_ok and nyq_ok
    missing_parts = []
    if pas_missing: missing_parts.append('pid-passivity-index')
    if cir_missing: missing_parts.append('pid-circle-criterion')
    if nyq_missing: missing_parts.append('nyquist-timescale-bridge')
    failed_parts = []
    if not pas_ok and not pas_missing: failed_parts.append('passivity')
    if not cir_ok and not cir_missing: failed_parts.append('circle_criterion')
    if not nyq_ok and not nyq_missing: failed_parts.append('nyquist')
    reason_parts = []
    if missing_parts:
        reason_parts.append(f'missing: {", ".join(missing_parts)}')
        # ADV2-002: wrapper must treat missing prereqs as a real failure, not warning_only
        reason_parts.append('failed:prereqs_missing')
    if failed_parts:
        reason_parts.append(f'failed: {", ".join(failed_parts)}')
    if justification_log:
        reason_parts.extend(justification_log)
    return {
        'passivity_ok': pas_ok,
        'pas_ok': pas_ok,
        'circle_ok': cir_ok,
        'nyquist_ok': nyq_ok,
        'justified_ok': justified,
        'alarm': not justified,
        'insufficient_data': False,
        'n_passivity': n_pas,
        'n_circle': n_cir,
        'n_nyquist': n_nyq,
        'violation_ratio': violation_ratio,
        'justification_log': justification_log,
        'reason': '; '.join(reason_parts) if reason_parts else None,
        'theorem': 'Khalil ISS small-gain requires ISS (passive, in-sector) subsystems; ADV21-013',
    }


def _load(name: str) -> dict:
    """ADV21-013: missing file returns sentinel so justify() fails closed."""
    try:
        obj = json.loads((CACHE / name).read_text())
        return obj if isinstance(obj, dict) else {'_missing': True}
    except (OSError, json.JSONDecodeError):
        return {'_missing': True}


def run() -> dict:
    out = justify(
        _load('pid-passivity-index.json'),
        _load('pid-circle-criterion.json'),
        _load('nyquist-timescale-bridge.json'),
    )
    out['ts'] = datetime.now(timezone.utc).isoformat()
    try:
        _atomic_write(OUT, out)
        out['output'] = str(OUT)
    except OSError as exc:
        out['write_error'] = str(exc)
    return out


def self_test() -> int:
    failures = []
    ok_cert = {'n': 12, 'alarm': False}
    # All prereqs ok with n>=min_n -> justified_ok=True, alarm=False
    r = justify(ok_cert, ok_cert, ok_cert)
    if r['alarm'] or not r['justified_ok']:
        failures.append('all ok should pass')
    # Passivity fails -> not justified, alarm
    r2 = justify({'n': 12, 'alarm': True}, ok_cert, ok_cert)
    if not r2['alarm'] or r2['justified_ok']:
        failures.append('passivity should unjustify')
    # All fail (no composite dep means alarm=True when any prereq fails)
    r3 = justify({'n': 12, 'alarm': True}, {'n': 12, 'alarm': True}, {'n': 12, 'alarm': True})
    if not r3['alarm'] or r3['justified_ok']:
        failures.append('all failed should alarm')
    # Missing passivity -> fail-closed + failed:prereqs_missing (ADV2-002)
    r4 = justify({'_missing': True}, ok_cert, ok_cert)
    if r4['justified_ok'] or not r4['alarm']:
        failures.append('missing passivity must fail closed')
    if 'failed:prereqs_missing' not in (r4.get('reason') or ''):
        failures.append('one missing file must emit failed:prereqs_missing')
    # All missing -> fail-closed (ADV2-002 a)
    r5 = justify({'_missing': True}, {'_missing': True}, {'_missing': True})
    if r5['justified_ok'] or not r5['alarm']:
        failures.append('all missing must fail closed')
    if 'failed:prereqs_missing' not in (r5.get('reason') or ''):
        failures.append('all missing must emit failed:prereqs_missing')
    # n=0 on all prereqs is vacuous, not a certificate (fail-closed)
    r6 = justify(
        {'n': 0, 'alarm': False},
        {'n': 0, 'alarm': False},
        {'nyquist_n_aliased': 0, 'alarm': False},
    )
    if r6['justified_ok'] or not r6['alarm']:
        failures.append('n=0 all prereqs must fail closed')
    if r6.get('reason') != 'insufficient_data: no observations':
        failures.append(f'n=0 reason mismatch: {r6.get("reason")}')
    if not r6.get('insufficient_data'):
        failures.append('n=0 must set insufficient_data')
    # Mixed: real n on all three (nyquist n, not merely zero aliases)
    r7 = justify(
        {'n': 12, 'alarm': False},
        {'n': 12, 'alarm': False},
        {'n': 12, 'nyquist_n_aliased': 0, 'alarm': False},
    )
    if not r7['justified_ok'] or r7['alarm'] or r7.get('insufficient_data'):
        failures.append('real n with zero aliases should pass')
    # ADV2-007: n=0 / omitted n / n=3 are cert_invalid
    r_n0 = justify(ok_cert, ok_cert, {'n': 0, 'alarm': False})
    if r_n0['justified_ok'] or r_n0.get('nyquist_ok'):
        failures.append('n=0 cert must be invalid')
    if 'cert_invalid:n_insufficient' not in (r_n0.get('reason') or '') and 'cert_invalid:n_insufficient' not in (r_n0.get('justification_log') or []):
        failures.append('n=0 must log cert_invalid:n_insufficient')
    r_none = justify(ok_cert, ok_cert, {'alarm': False})
    if r_none['justified_ok'] or r_none.get('nyquist_ok'):
        failures.append('omitted n cert must be invalid')
    if 'cert_invalid:n_insufficient' not in (r_none.get('reason') or '') and 'cert_invalid:n_insufficient' not in (r_none.get('justification_log') or []):
        failures.append('omitted n must log cert_invalid:n_insufficient')
    r_n3 = justify(ok_cert, ok_cert, {'n': 3, 'alarm': False})
    if r_n3['justified_ok'] or r_n3.get('nyquist_ok'):
        failures.append('n=3 cert must be invalid')
    if 'cert_invalid:n_insufficient' not in (r_n3.get('reason') or '') and 'cert_invalid:n_insufficient' not in (r_n3.get('justification_log') or []):
        failures.append('n=3 must log cert_invalid:n_insufficient')
    if failures:
        print(json.dumps({'self_test': 'FAIL', 'failures': failures}))
        return 1
    print(json.dumps({'self_test': 'PASS', 'n_checks': 12}))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument('--self-test', action='store_true')
    args = p.parse_args(argv)
    if args.self_test:
        return self_test()
    out = run()
    print(json.dumps({k: out.get(k) for k in ('justified_ok', 'pas_ok', 'alarm', 'reason', 'output')}))
    return 1 if out.get('write_error') else 0  # ADV2-017: alarm is not a process failure


if __name__ == '__main__':
    sys.exit(main())
