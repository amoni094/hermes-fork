#!/usr/bin/env python3
"""loop-cusum-changepoint.py — Page CUSUM on PID error (Wald/Page).

Detects a mean shift in loop-pid error that would invalidate fixed PID gains.
Two-sided CUSUM: S+ and S- with allowance k and threshold h.
Alarm => recommend retune / switch to MPC (pairs with loop-model-comparison).

ADV2-013: mu0 is loaded from loop-cusum-baseline.json only (never recomputed
from xs[:50]). S+/S- persist in cache/cusum-state.json. Stale h* (>72h) falls
back to H_DEFAULT with calibration_warning (not fail-closed).

Usage:
  python3 loop-cusum-changepoint.py --self-test
  python3 loop-cusum-changepoint.py
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone, UTC
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base

OUT_PATH = _hermes_root / 'cache' / 'loop-cusum-changepoint.json'
BASELINE_PATH = _hermes_root / 'cache' / 'loop-cusum-baseline.json'
STATE_PATH = _hermes_root / 'cache' / 'cusum-state.json'
CAL_PATH = _hermes_root / 'cache' / 'cusum-h-calibration.json'
K_DEFAULT = 0.25
H_DEFAULT = 4.0
H_CALIBRATION_TTL_HOURS = 72


def _atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    os.replace(tmp, path)


def cusum(xs: list[float], mu0: float = 0.0, k: float = K_DEFAULT, h: float = H_DEFAULT,
          s_pos: float = 0.0, s_neg: float = 0.0) -> dict:
    sp = float(s_pos)
    sm = float(s_neg)
    max_sp = sp
    max_sm = sm
    alarm_at = None
    for i, x in enumerate(xs):
        sp = max(0.0, sp + (x - mu0) - k)
        sm = max(0.0, sm - (x - mu0) - k)
        max_sp = max(max_sp, sp)
        max_sm = max(max_sm, sm)
        if alarm_at is None and (sp > h or sm > h):
            alarm_at = i
    return {
        'n': len(xs),
        'mu0': mu0,
        'k': k,
        'h': h,
        'S_plus': sp,
        'S_minus': sm,
        'max_S_plus': max_sp,
        'max_S_minus': max_sm,
        'alarm': alarm_at is not None or sp > h or sm > h,
        'alarm_index': alarm_at,
        'theorem': 'Page CUSUM; Wald sequential analysis',
    }


def load_errors() -> list[float]:
    xs: list[float] = []
    for p in (
        _hermes_root / 'cache' / 'loop-pid-state.json',
        _hermes_base / 'cache' / 'loop-pid-state.json',
    ):
        try:
            if not p.is_file():
                continue
            data = json.loads(p.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError):
            continue
        for step in data.get('history') or []:
            if isinstance(step, dict) and 'e' in step:
                try:
                    xs.append(float(step['e']))
                except (TypeError, ValueError):
                    continue
        if xs:
            return xs
    return xs


def load_mu0(xs: list[float], baseline_path: Path | None = None) -> tuple[float, bool]:
    """Load frozen mu0 from baseline ONLY. Do not recompute from xs[:50].

    If baseline missing: mean(xs) fallback and baseline_warning=True.
    """
    path = baseline_path if baseline_path is not None else BASELINE_PATH
    try:
        bl = json.loads(path.read_text(encoding='utf-8'))
        if 'mu0' not in bl:
            raise KeyError('mu0')
        return float(bl['mu0']), False
    except Exception:
        mu0 = (sum(xs) / len(xs)) if xs else 0.0
        return mu0, True


def load_cusum_state(path: Path | None = None) -> dict:
    p = path if path is not None else STATE_PATH
    try:
        data = json.loads(p.read_text(encoding='utf-8'))
        return {
            'S_pos': float(data.get('S_pos', 0.0) or 0.0),
            'S_neg': float(data.get('S_neg', 0.0) or 0.0),
            'n_seen': int(data.get('n_seen', 0) or 0),
            'fresh_start': False,
        }
    except Exception:
        return {'S_pos': 0.0, 'S_neg': 0.0, 'n_seen': 0, 'fresh_start': True}


def save_cusum_state(s_pos: float, s_neg: float, n_seen: int = 0, path: Path | None = None) -> None:
    p = path if path is not None else STATE_PATH
    payload = {
        'S_pos': float(s_pos),
        'S_neg': float(s_neg),
        'last_update_ts': datetime.now(UTC).isoformat(),
        'n_seen': int(n_seen),
    }
    _atomic_write(p, payload)


def load_h_effective(cal_path: Path | None = None) -> tuple[float, bool, float]:
    """h* when available and mtime < 72h; else H_DEFAULT with calibration_warning.

    Do NOT fail-closed on missing/stale h* — warn only (ADV2-013).
    """
    p = cal_path if cal_path is not None else CAL_PATH
    try:
        age_h = (time.time() - p.stat().st_mtime) / 3600.0
        if age_h >= H_CALIBRATION_TTL_HOURS:
            return H_DEFAULT, True, K_DEFAULT
        cal = json.loads(p.read_text(encoding='utf-8'))
        h_star = cal.get('h_star')
        if h_star is None:
            return H_DEFAULT, True, K_DEFAULT
        k = float(cal.get('k', K_DEFAULT))
        return float(h_star), False, k
    except Exception:
        return H_DEFAULT, True, K_DEFAULT


def run() -> dict:
    xs = load_errors()
    mu0, baseline_warning = load_mu0(xs)
    if baseline_warning:
        try:
            _atomic_write(BASELINE_PATH, {'mu0': mu0, 'n': len(xs)})
        except Exception:
            pass
    state = load_cusum_state()
    h_effective, calibration_warning, k_effective = load_h_effective()
    n_seen = state['n_seen']
    if n_seen < 0 or n_seen > len(xs):
        xs_new = xs
        n_after = len(xs)
    else:
        xs_new = xs[n_seen:]
        n_after = len(xs)
    out = cusum(
        xs_new,
        mu0=mu0,
        k=k_effective,
        h=h_effective,
        s_pos=state['S_pos'],
        s_neg=state['S_neg'],
    )
    out['n'] = len(xs)
    out['n_new'] = len(xs_new)
    out['baseline_warning'] = baseline_warning
    out['fresh_start'] = state['fresh_start']
    out['calibration_warning'] = calibration_warning
    out['h_effective'] = h_effective
    out['ts'] = datetime.now(UTC).isoformat()
    out['recommendation'] = 'retune_pid_or_mpc' if out['alarm'] else 'pid_gains_stable'
    try:
        save_cusum_state(out['S_plus'], out['S_minus'], n_after)
    except OSError as exc:
        out['state_write_error'] = str(exc)
    try:
        _atomic_write(OUT_PATH, out)
        out['output'] = str(OUT_PATH)
    except OSError as exc:
        out['write_error'] = str(exc)
    return out


def self_test() -> int:
    import tempfile
    failures = []
    # in-control noise around 0
    ok = cusum([0.05, -0.04, 0.03, -0.02, 0.01] * 4, mu0=0.0, k=0.25, h=4.0)
    if ok['alarm']:
        failures.append('in-control should not alarm')
    ok_hstar = cusum([0.05, -0.04, 0.03, -0.02, 0.01] * 4, mu0=0.0, k=0.25, h=17.9)
    if ok_hstar['alarm']:
        failures.append('in-control noise should not alarm at h=17.9')
    # step change to 2.0
    xs = [0.0] * 8 + [2.0] * 12
    bad = cusum(xs, mu0=0.0, k=0.25, h=4.0)
    if not bad['alarm']:
        failures.append('step change should alarm at h=4')

    td = Path(tempfile.mkdtemp(prefix='cusum-adv2-013-'))
    state_p = td / 'cusum-state.json'
    base_p = td / 'loop-cusum-baseline.json'
    cal_p = td / 'cusum-h-calibration.json'

    # (a) S+/S- persist across two calls
    r1 = cusum([1.0, 1.0], mu0=0.0, k=0.25, h=4.0, s_pos=0.0, s_neg=0.0)
    save_cusum_state(r1['S_plus'], r1['S_minus'], n_seen=2, path=state_p)
    st = load_cusum_state(state_p)
    if st['fresh_start'] or abs(st['S_pos'] - r1['S_plus']) > 1e-12 or abs(st['S_neg'] - r1['S_minus']) > 1e-12:
        failures.append('S+/S- must persist across save/load')
    r2 = cusum([1.0], mu0=0.0, k=0.25, h=4.0, s_pos=st['S_pos'], s_neg=st['S_neg'])
    r_all = cusum([1.0, 1.0, 1.0], mu0=0.0, k=0.25, h=4.0)
    if abs(r2['S_plus'] - r_all['S_plus']) > 1e-12:
        failures.append('persisted S must continue CUSUM across two calls')
    st_miss = load_cusum_state(td / 'missing-state.json')
    if not st_miss['fresh_start'] or st_miss['S_pos'] != 0.0 or st_miss['S_neg'] != 0.0:
        failures.append('missing state must fresh_start with S+=S-=0')

    # (b) mu0 from baseline, not from xs
    _atomic_write(base_p, {'mu0': 1.5, 'n': 10})
    mu0_b, warn_b = load_mu0([10.0] * 80, baseline_path=base_p)
    if abs(mu0_b - 1.5) > 1e-12 or warn_b:
        failures.append('mu0 must come from baseline not xs[:50]')
    mu0_fb, warn_fb = load_mu0([2.0, 4.0], baseline_path=td / 'no-baseline.json')
    if not warn_fb or abs(mu0_fb - 3.0) > 1e-12:
        failures.append('missing baseline must warn and use mean(xs)')

    # (c) stale calibration emits warning and uses H_DEFAULT
    _atomic_write(cal_p, {'h_star': 17.9, 'hit_target': True, 'k': 0.25})
    stale_mtime = time.time() - 80 * 3600
    os.utime(cal_p, (stale_mtime, stale_mtime))
    h_stale, cal_warn, k_stale = load_h_effective(cal_p)
    if h_stale != H_DEFAULT or not cal_warn:
        failures.append('stale calibration must warn and use H_DEFAULT')
    os.utime(cal_p, None)
    h_fresh, cal_warn_fresh, k_fresh = load_h_effective(cal_p)
    if abs(h_fresh - 17.9) > 1e-12 or cal_warn_fresh:
        failures.append('fresh h* should be used without warning')
    h_miss, cal_warn_miss, _k = load_h_effective(td / 'no-cal.json')
    if h_miss != H_DEFAULT or not cal_warn_miss:
        failures.append('missing calibration must warn and use H_DEFAULT')

    if failures:
        print(json.dumps({'self_test': 'FAIL', 'failures': failures}))
        return 1
    print(json.dumps({'self_test': 'PASS', 'alarm_index': bad['alarm_index']}))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument('--self-test', action='store_true')
    args = p.parse_args(argv)
    if args.self_test:
        return self_test()
    out = run()
    print(json.dumps({k: out.get(k) for k in (
        'n', 'alarm', 'alarm_index', 'recommendation', 'output')}))
    return 1 if out.get('alarm') else 0


if __name__ == '__main__':
    sys.exit(main())
