#!/usr/bin/env python3
"""sprt-effective-decision.py — Merge SPRT + vetoes into one effective decision.

Raw SPRT PROMOTE is not executable if handshake HOLDs, truncation REJECTS,
inner/outer misaligns, or measurement tamper alarms. This is the file other
systems should read.

Priority (fail-closed): TAMPER > TRUNCATE_REJECT > HOLD_NO_FO > INNER_OUTER > SPRT.

Usage:
  python3 sprt-effective-decision.py --self-test
  python3 sprt-effective-decision.py
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
CACHE = _hermes_root / 'cache'
OUT = CACHE / 'sprt-effective-decision.json'
EFFECTIVE_SHADOW = CACHE / 'effective-shadow-decisions.json'
MSPRT_TTL_HOURS = 26
INPUT_TTL_HOURS = 25.0  # ADV2-020: daily-cron mtime window (integrity substitute)

VETO_FILES = {
    'tamper': 'sprt-measurement-tamper.json',
    'truncation': 'sprt-truncation.json',
    'handshake': 'sprt-falsifiability-handshake.json',
}


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


def _load_required(path: Path, required_mtime: float | None = None) -> dict:
    """Fail-closed JSON load. Missing/corrupt/stale vs required_mtime raises."""
    if not path.exists():
        raise FileNotFoundError(str(path))
    try:
        obj = json.loads(path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as exc:
        raise ValueError(f'invalid json: {path}') from exc
    if not isinstance(obj, dict):
        raise ValueError(f'not a dict: {path}')
    if required_mtime is not None and path.stat().st_mtime < required_mtime:
        raise ValueError('stale veto file')
    return obj


def _age_h(path: Path, now: float | None = None) -> float:
    return ((now if now is not None else time.time()) - path.stat().st_mtime) / 3600.0


def merge(sprt: dict, handshake: dict, trunc: dict, inner: dict, tamper: dict,
          msprt: dict | None = None, input_holds: list[str] | None = None) -> dict:
    tamper_on = bool(tamper.get('alarm'))
    hold_flags = {h.get('flag') for h in (handshake.get('holds') or [])}
    trunc_flags = {f.get('flag') for f in (trunc.get('forced') or [])}
    mesa_flags = {f.get('flag') for f in (inner.get('flags') or [])}
    # mSPRT gate: Johari et al. arXiv:1512.04922 always-valid p.
    # Wald PROMOTE is fail-closed: missing/stale mSPRT file or missing flag => HOLD.
    msprt_decisions: dict[str, str] = {}
    if msprt is not None and isinstance(msprt.get('decisions'), list):
        for md in msprt['decisions']:
            f = md.get('flag')
            if f:
                msprt_decisions[f] = md.get('decision', 'CONTINUE')
    file_holds = [r for r in (input_holds or []) if r]
    out_decisions = []
    n_blocked = 0
    for d in sprt.get('decisions') or []:
        flag = d.get('flag')
        raw = d.get('decision')
        eff = raw
        reason = 'sprt'
        if tamper_on and raw == 'PROMOTE':
            eff, reason = 'HOLD', 'measurement_tamper'
        elif flag in trunc_flags:
            eff, reason = 'REJECT', 'truncated'
        elif flag in hold_flags:
            eff, reason = 'HOLD', 'no_failure_observable'
        elif flag in mesa_flags:
            eff, reason = 'HOLD', 'inner_outer_misaligned'
        elif raw == 'PROMOTE' and file_holds:
            # ADV2-003/020: missing or stale veto/input files fail-closed (not PROMOTE).
            eff, reason = 'HOLD', file_holds[0]
        elif raw == 'PROMOTE':
            if msprt is not None:
                if flag not in msprt_decisions:
                    eff, reason = 'HOLD', 'msprt_no_data_for_flag'
                elif msprt_decisions[flag] != 'PROMOTE':
                    eff, reason = 'HOLD', 'msprt_not_promote'
            else:
                eff, reason = 'HOLD', 'msprt_file_missing'
        if eff != raw:
            n_blocked += 1
        row = {'flag': flag, 'raw': raw, 'effective': eff, 'reason': reason}
        if file_holds:
            row['input_holds'] = list(file_holds)
        out_decisions.append(row)
    n_promote = sum(1 for x in out_decisions if x['effective'] == 'PROMOTE')
    # Freshness audit of A_boot calibration. shadow-gate-sprt.py already applied
    # A_boot internally; this does not block merge.
    boot_ok, boot_warn = _boot_calibration_audit()
    out = {
        'decisions': out_decisions,
        'n_blocked': n_blocked,
        'n_effective_promote': n_promote,
        'alarm': n_blocked > 0,
        'msprt_wired': bool(msprt_decisions),
        'boot_calibration_checked': boot_ok,
        'input_holds': list(file_holds),
        'theorem': 'Fail-closed: TAMPER>TRUNCATE>HOLD_FO>INNER_OUTER>mSPRT>Wald (Johari arXiv:1512.04922)',
    }
    if boot_warn:
        out['calibration_warning'] = boot_warn
    return out



BOOT_CAL_MAX_AGE_H = 48.0
BOOT_A_MIN = 10.0


def _boot_calibration_audit() -> tuple[bool, str | None]:
    """Load block-bootstrap-sprt.json: exists, mtime < 48h, A_effective > 10.0.

    Failures emit calibration_warning; they do not block (freshness audit only).
    """
    path = CACHE / 'block-bootstrap-sprt.json'
    if not path.exists():
        return False, 'missing_block_bootstrap_sprt'
    age_h = (time.time() - path.stat().st_mtime) / 3600.0
    if age_h >= BOOT_CAL_MAX_AGE_H:
        return False, f'stale_block_bootstrap_sprt_h={age_h:.1f}'
    try:
        obj = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(obj, dict):
            return False, 'unreadable_block_bootstrap_sprt'
    except (OSError, json.JSONDecodeError):
        return False, 'unreadable_block_bootstrap_sprt'
    cal = obj.get('calibration') if isinstance(obj.get('calibration'), dict) else {}
    a = obj.get('A_effective')
    if a is None:
        a = cal.get('A_effective')
    if a is None:
        # live calibrator writes A_boot; treat as A_effective for the >10.0 check
        a = obj.get('A_boot', cal.get('A_boot'))
    try:
        a_f = float(a)
    except (TypeError, ValueError):
        return False, 'missing_A_effective'
    if a_f <= BOOT_A_MIN:
        return False, f'A_effective_too_small={a_f}'
    return True, None


def _load_msprt(now: float | None = None, ttl_hours: float = MSPRT_TTL_HOURS,
                path: Path | None = None) -> dict | None:
    """Return mSPRT JSON or None if missing/stale (fail-closed)."""
    msprt_path = path if path is not None else (CACHE / 'msprt-shadow-gate.json')
    if not msprt_path.exists():
        return None
    age_h = ((now if now is not None else time.time()) - msprt_path.stat().st_mtime) / 3600
    if age_h > ttl_hours:
        return None
    try:
        obj = json.loads(msprt_path.read_text())
        return obj if isinstance(obj, dict) else {}
    except (OSError, json.JSONDecodeError):
        return None


def _load_vetoes(shadow_mtime: float | None, now: float | None = None,
                 cache: Path | None = None) -> tuple[dict[str, dict], list[str]]:
    """Load tamper/truncation/handshake fail-closed. Missing/stale -> HOLD reasons."""
    root = cache if cache is not None else CACHE
    ts = now if now is not None else time.time()
    loaded: dict[str, dict] = {}
    holds: list[str] = []
    for name, fname in VETO_FILES.items():
        path = root / fname
        try:
            if path.exists():
                age = _age_h(path, ts)
                if age > INPUT_TTL_HOURS:
                    holds.append(f'input_stale:{name}:{age:.1f}h')
            loaded[name] = _load_required(path, required_mtime=shadow_mtime)
        except (FileNotFoundError, ValueError):
            holds.append(f'veto_file_missing:{name}')
            loaded[name] = {}
    return loaded, holds


def run() -> dict:
    shadow_path = CACHE / 'shadow-sprt-decisions.json'
    now = time.time()
    input_holds: list[str] = []
    shadow_mtime: float | None = None
    if shadow_path.exists():
        shadow_mtime = shadow_path.stat().st_mtime
        age = _age_h(shadow_path, now)
        if age > INPUT_TTL_HOURS:
            input_holds.append(f'input_stale:shadow:{age:.1f}h')
        try:
            shadow = _load_required(shadow_path)
        except (FileNotFoundError, ValueError):
            shadow = {}
            input_holds.append('veto_file_missing:shadow')
    else:
        shadow = {}
    vetoes, veto_holds = _load_vetoes(shadow_mtime, now=now)
    input_holds.extend(veto_holds)
    msprt_path = CACHE / 'msprt-shadow-gate.json'
    if msprt_path.exists():
        age = _age_h(msprt_path, now)
        if age > INPUT_TTL_HOURS:
            input_holds.append(f'input_stale:msprt:{age:.1f}h')
    out = merge(
        shadow,
        vetoes.get('handshake') or {},
        vetoes.get('truncation') or {},
        _load('sprt-inner-outer-alignment.json'),
        vetoes.get('tamper') or {},
        msprt=_load_msprt(),
        input_holds=input_holds,
    )
    out['ts'] = datetime.now(UTC).isoformat()
    n_by_flag = {d.get('flag'): d.get('n') for d in (shadow.get('decisions') or []) if isinstance(d, dict)}
    eff_shadow = {
        'decisions': [
            {
                'flag': e.get('flag'),
                'decision': e.get('effective'),
                'n': n_by_flag.get(e.get('flag')),
                'raw': e.get('raw'),
                'reason': e.get('reason'),
            }
            for e in (out.get('decisions') or [])
        ],
        'ts': out['ts'],
    }
    try:
        _atomic_write(OUT, out)
        _atomic_write(EFFECTIVE_SHADOW, eff_shadow)
        out['output'] = str(OUT)
        out['effective_shadow'] = str(EFFECTIVE_SHADOW)
    except OSError as exc:
        out['write_error'] = str(exc)
    return out


def self_test() -> int:
    failures = []
    r = merge(
        {'decisions': [
            {'flag': 'a', 'decision': 'PROMOTE'},
            {'flag': 'b', 'decision': 'PROMOTE'},
            {'flag': 'c', 'decision': 'CONTINUE'},
        ]},
        {'holds': [{'flag': 'a'}]},
        {'forced': [{'flag': 'c'}]},
        {'flags': [{'flag': 'b'}]},
        {'alarm': False},
    )
    by = {x['flag']: x['effective'] for x in r['decisions']}
    if by['a'] != 'HOLD' or by['b'] != 'HOLD' or by['c'] != 'REJECT':
        failures.append(str(by))
    r2 = merge({'decisions': [{'flag': 'z', 'decision': 'PROMOTE'}]},
               {}, {}, {}, {'alarm': True})
    if r2['decisions'][0]['effective'] != 'HOLD':
        failures.append('tamper')
    # mSPRT gate: Wald PROMOTE blocked when mSPRT says CONTINUE
    r3 = merge(
        {'decisions': [{'flag': 'm', 'decision': 'PROMOTE'}, {'flag': 'n', 'decision': 'PROMOTE'}]},
        {}, {}, {}, {'alarm': False},
        msprt={'decisions': [{'flag': 'm', 'decision': 'CONTINUE'}, {'flag': 'n', 'decision': 'PROMOTE'}]},
    )
    by3 = {x['flag']: x['effective'] for x in r3['decisions']}
    if by3.get('m') != 'HOLD' or by3.get('n') != 'PROMOTE':
        failures.append(f'msprt-gate: {by3}')
    if not r3.get('msprt_wired'):
        failures.append('msprt_wired flag missing')
    # ADV-002 (a): flag absent from mSPRT decisions -> HOLD
    r_a = merge(
        {'decisions': [{'flag': 'absent', 'decision': 'PROMOTE'}]},
        {}, {}, {}, {'alarm': False},
        msprt={'decisions': [{'flag': 'other', 'decision': 'PROMOTE'}]},
    )
    if r_a['decisions'][0]['effective'] != 'HOLD' or r_a['decisions'][0]['reason'] != 'msprt_no_data_for_flag':
        failures.append(f'msprt-absent-flag: {r_a["decisions"][0]}')
    # ADV-002 (b): mSPRT=None (file missing) -> HOLD
    r_b = merge(
        {'decisions': [{'flag': 'x', 'decision': 'PROMOTE'}]},
        {}, {}, {}, {'alarm': False},
        msprt=None,
    )
    if r_b['decisions'][0]['effective'] != 'HOLD' or r_b['decisions'][0]['reason'] != 'msprt_file_missing':
        failures.append(f'msprt-none: {r_b["decisions"][0]}')
    # ADV-002 (c): mSPRT PROMOTE -> Wald PROMOTE preserved (r3 flag n)
    if by3.get('n') != 'PROMOTE':
        failures.append('msprt-promote-preserved')
    # ADV-002 (d): stale file -> HOLD (_load_msprt returns None)
    import tempfile
    td = Path(tempfile.mkdtemp())
    stale = td / 'msprt-shadow-gate.json'
    stale.write_text(json.dumps({'decisions': [{'flag': 'x', 'decision': 'PROMOTE'}]}), encoding='utf-8')
    old_mtime = time.time() - (MSPRT_TTL_HOURS + 1) * 3600
    os.utime(stale, (old_mtime, old_mtime))
    loaded_stale = _load_msprt(path=stale)
    if loaded_stale is not None:
        failures.append(f'stale-msprt-not-none: {loaded_stale}')
    r_d = merge(
        {'decisions': [{'flag': 'x', 'decision': 'PROMOTE'}]},
        {}, {}, {}, {'alarm': False},
        msprt=loaded_stale,
    )
    if r_d['decisions'][0]['effective'] != 'HOLD' or r_d['decisions'][0]['reason'] != 'msprt_file_missing':
        failures.append(f'msprt-stale: {r_d["decisions"][0]}')
    fresh = td / 'msprt-fresh.json'
    fresh.write_text(json.dumps({'decisions': [{'flag': 'x', 'decision': 'PROMOTE'}]}), encoding='utf-8')
    if _load_msprt(path=fresh) is None:
        failures.append('fresh-msprt-should-load')
    if 'boot_calibration_checked' not in r:
        failures.append('boot_calibration_checked missing from merge()')
    # ADV2-003: missing veto files fail-closed (HOLD), not PROMOTE.
    sprt_ok = {'decisions': [{'flag': 'ok', 'decision': 'PROMOTE'}]}
    msprt_ok = {'decisions': [{'flag': 'ok', 'decision': 'PROMOTE'}]}
    td_v = Path(tempfile.mkdtemp())
    shadow_p = td_v / 'shadow-sprt-decisions.json'
    shadow_p.write_text(json.dumps(sprt_ok), encoding='utf-8')
    shadow_mt = shadow_p.stat().st_mtime
    for fname, body in (
        ('sprt-measurement-tamper.json', {'alarm': False}),
        ('sprt-truncation.json', {'forced': []}),
        ('sprt-falsifiability-handshake.json', {'holds': []}),
    ):
        (td_v / fname).write_text(json.dumps(body), encoding='utf-8')
    os.utime(shadow_p, (shadow_mt, shadow_mt))
    all_ok, holds_ok = _load_vetoes(shadow_p.stat().st_mtime, cache=td_v)
    r_ok = merge(sprt_ok, all_ok['handshake'], all_ok['truncation'], {}, all_ok['tamper'],
                 msprt=msprt_ok, input_holds=holds_ok)
    if r_ok['decisions'][0]['effective'] != 'PROMOTE':
        failures.append(f'ADV2-003 all-present: {r_ok["decisions"][0]} holds={holds_ok}')
    for missing_name in ('tamper', 'truncation', 'handshake'):
        td_m = Path(tempfile.mkdtemp())
        sp = td_m / 'shadow-sprt-decisions.json'
        sp.write_text(json.dumps(sprt_ok), encoding='utf-8')
        for fname, body in (
            ('sprt-measurement-tamper.json', {'alarm': False}),
            ('sprt-truncation.json', {'forced': []}),
            ('sprt-falsifiability-handshake.json', {'holds': []}),
        ):
            if VETO_FILES[missing_name] == fname:
                continue
            (td_m / fname).write_text(json.dumps(body), encoding='utf-8')
        loaded_m, holds_m = _load_vetoes(sp.stat().st_mtime, cache=td_m)
        r_m = merge(sprt_ok, loaded_m.get('handshake') or {}, loaded_m.get('truncation') or {},
                    {}, loaded_m.get('tamper') or {}, msprt=msprt_ok, input_holds=holds_m)
        if r_m['decisions'][0]['effective'] != 'HOLD':
            failures.append(f'ADV2-003 {missing_name} missing not HOLD: {r_m["decisions"][0]}')
        if not any(h.startswith(f'veto_file_missing:{missing_name}') for h in holds_m):
            failures.append(f'ADV2-003 {missing_name} reason missing: {holds_m}')
    # _load_required: missing raises FileNotFoundError; bad json raises ValueError
    try:
        _load_required(td_v / 'no-such.json')
        failures.append('_load_required missing did not raise')
    except FileNotFoundError:
        pass
    bad = td_v / 'bad.json'
    bad.write_text('{not json', encoding='utf-8')
    try:
        _load_required(bad)
        failures.append('_load_required corrupt did not raise')
    except ValueError:
        pass
    # ADV2-020: input older than 25h -> input_stale HOLD
    old_v = td_v / 'sprt-measurement-tamper.json'
    old_t = time.time() - (INPUT_TTL_HOURS + 1) * 3600
    os.utime(old_v, (old_t, old_t))
    # also bump shadow so required_mtime doesn't fire first
    os.utime(shadow_p, (old_t - 10, old_t - 10))
    loaded_stale_v, holds_stale = _load_vetoes(shadow_p.stat().st_mtime, cache=td_v)
    if not any(h.startswith('input_stale:tamper:') for h in holds_stale):
        failures.append(f'ADV2-020 expected input_stale:tamper, got {holds_stale}')
    r_stale = merge(sprt_ok, loaded_stale_v.get('handshake') or {},
                    loaded_stale_v.get('truncation') or {}, {},
                    loaded_stale_v.get('tamper') or {}, msprt=msprt_ok,
                    input_holds=holds_stale)
    if r_stale['decisions'][0]['effective'] != 'HOLD':
        failures.append(f'ADV2-020 stale not HOLD: {r_stale["decisions"][0]}')
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
    print(json.dumps({k: out.get(k) for k in ('n_blocked', 'n_effective_promote', 'alarm', 'output')}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
