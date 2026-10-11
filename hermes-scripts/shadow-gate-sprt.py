#!/usr/bin/env python3
"""shadow-gate-sprt.py — Wald SPRT for shadow-feature promotion.

Replaces the fixed-sample rule (n>=20 AND mean>=3.5 AND error_rate<10%)
with a sequential probability ratio test that controls Type I/II error.

H0: mean_score <= 3.0  (not good enough)   f0 = Normal(3.0, 1)
H1: mean_score >= 4.0  (clearly good)      f1 = Normal(4.0, 1)
LLR increment for N(mu,1): log(f1/f0) = x - 3.5
A = log((1-beta)/alpha) = log(19)   (alpha=beta=0.05)
B = log(beta/(1-alpha)) = log(1/19)

Decision: LLR > A => PROMOTE; LLR < B => REJECT; else CONTINUE.

Hard veto (Amodei safe exploration): error_rate >= 0.10 cannot PROMOTE.

Runs ALONGSIDE shadow-gate-nightly.py; does not replace it.

Usage:
  python3 shadow-gate-sprt.py --self-test
  python3 shadow-gate-sprt.py
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base

OUT_PATH = _hermes_root / 'cache' / 'shadow-sprt-decisions.json'
ALPHA = 0.05
BETA = 0.05
MU0 = 3.0
MU1 = 4.0
SIGMA = 1.0
A = math.log((1.0 - BETA) / ALPHA)  # log(19)
B = math.log(BETA / (1.0 - ALPHA))  # log(1/19)
ERROR_RATE_VETO = 0.10
N_MIN_POWER = 50
A_BOOT_TTL_HOURS = 48
CAL_PATH = _hermes_root / 'cache' / 'block-bootstrap-sprt.json'


def _load_a_boot() -> tuple[float | None, bool]:
    """Load block-bootstrap A. Missing/stale/too-low calibration => None (fail-closed)."""
    a_wald = math.log((1.0 - BETA) / ALPHA)
    try:
        import time
        data = json.loads(CAL_PATH.read_text(encoding='utf-8'))
        age_h = (time.time() - CAL_PATH.stat().st_mtime) / 3600
        if age_h > A_BOOT_TTL_HOURS:
            return None, False
        cal = data.get('calibration') if isinstance(data.get('calibration'), dict) else data
        if not isinstance(cal, dict):
            cal = data if isinstance(data, dict) else {}
        raw = cal.get('A_boot', data.get('A_boot') if isinstance(data, dict) else None)
        if raw is None:
            return None, False
        a_boot = float(raw)
        if a_boot >= a_wald:
            return a_boot, True
        return None, False
    except Exception:
        return None, False


a_effective: float | None = None
boot_calibrated = False


def _atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    os.replace(tmp, path)


def llr_increment(x: float, mu0: float = MU0, mu1: float = MU1, sigma: float = SIGMA) -> float:
    """log f1(x)/f0(x) for Normal(mu, sigma^2). For sigma=1, mu0=3, mu1=4: x-3.5."""
    v = float(sigma) ** 2
    return ((float(x) - mu0) ** 2 - (float(x) - mu1) ** 2) / (2.0 * v)


def sprt_decision(scores: list[float], alpha: float = ALPHA, beta: float = BETA,
                  mu0: float = MU0, mu1: float = MU1, a_override=None) -> dict:
    a = a_override if a_override is not None else math.log((1-beta)/alpha)
    b = math.log(beta / (1.0 - alpha))
    llr = 0.0
    n = 0
    decision = 'CONTINUE'
    reason = 'sprt'
    for x in scores:
        llr += llr_increment(float(x), mu0=mu0, mu1=mu1)
        n += 1
        if llr > a:
            decision = 'PROMOTE'
            break
        if llr < b:
            decision = 'REJECT'
            break
    # ADV-013: power floor uses available sample size, not Wald stopping time.
    if decision == 'PROMOTE' and len(scores) < N_MIN_POWER:
        decision = 'CONTINUE'
        reason = 'n_below_power_floor'
    return {
        'decision': decision,
        'llr': llr,
        'n': n,
        'n_scores': len(scores),
        'A': a,
        'B': b,
        'mean': (sum(scores) / len(scores)) if scores else None,
        'reason': reason,
    }


def _mean_of_score_blob(blob) -> float | None:
    if blob is None:
        return None
    if isinstance(blob, (int, float)) and not isinstance(blob, bool):
        return float(blob)
    if isinstance(blob, dict):
        vals = []
        for v in blob.values():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                vals.append(float(v))
        if vals:
            return sum(vals) / len(vals)
    return None


def extract_score(rec: dict) -> float | None:
    for key in ('mean_score', 'score', 'overall', 'rating'):
        if key in rec:
            s = _mean_of_score_blob(rec.get(key))
            if s is not None:
                return s
    s = _mean_of_score_blob(rec.get('scores'))
    if s is not None:
        return s
    return None


def extract_flag(rec: dict) -> str:
    for key in ('flag', 'feature', 'name', 'skill', 'id'):
        v = rec.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return 'jev_turn_score'


def extract_error_flag(rec: dict) -> bool | None:
    if 'error' in rec and isinstance(rec['error'], bool):
        return rec['error']
    errs = rec.get('errors')
    if isinstance(errs, list):
        return len(errs) > 0
    if 'error_rate' in rec:
        try:
            return float(rec['error_rate']) > 0
        except (TypeError, ValueError):
            return None
    return None


def _read_jsonl(path: Path) -> list[dict]:
    rows = []
    try:
        text = path.read_text(encoding='utf-8')
    except OSError:
        return rows
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def load_telemetry() -> list[dict]:
    rows: list[dict] = []
    candidates = [
        _hermes_root / 'cache' / 'jev-turn-scores.jsonl',
        _hermes_base / 'cache' / 'jev-turn-scores.jsonl',
        _hermes_root / 'logs' / 'jev-turn-scores.jsonl',
    ]
    # H-I7: shadow paths
    try:
        shadow = _hermes_root / 'cache' / 'shadow-telemetry'
        if shadow.is_dir():
            candidates.extend(sorted(shadow.glob('*.jsonl')))
    except OSError:
        pass
    seen = set()
    for p in candidates:
        try:
            rp = str(p.resolve()) if p.exists() else str(p)
        except OSError:
            continue
        if rp in seen:
            continue
        seen.add(rp)
        try:
            if p.is_file():
                rows.extend(_read_jsonl(p))
        except OSError:
            continue
    return rows


def evaluate_groups(rows: list[dict]) -> list[dict]:
    groups: dict[str, list[dict]] = {}
    for rec in rows:
        groups.setdefault(extract_flag(rec), []).append(rec)
    out = []
    for flag, recs in sorted(groups.items()):
        scores = []
        err_flags = []
        for rec in recs:
            s = extract_score(rec)
            if s is None:
                continue
            scores.append(s)
            ef = extract_error_flag(rec)
            if ef is not None:
                err_flags.append(1.0 if ef else 0.0)
        sprt = sprt_decision(scores, a_override=a_effective)
        numeric_rates: list[float] = []
        for rec in recs:
            if 'error_rate' not in rec or rec.get('error_rate') is None:
                continue
            try:
                numeric_rates.append(float(rec['error_rate']))
            except (TypeError, ValueError):
                continue
        if numeric_rates:
            error_rate: float | None = sum(numeric_rates) / len(numeric_rates)
        elif err_flags:
            error_rate = sum(err_flags) / len(err_flags)
        else:
            error_rate = None
        error_rate_unknown = error_rate is None
        if error_rate_unknown:
            error_rate = 0.0
        decision = sprt['decision']
        veto = False
        # ADV2-001/006: never PROMOTE on high or unknown error rate.
        if decision == 'PROMOTE' and (error_rate_unknown or (error_rate is not None and error_rate >= ERROR_RATE_VETO)):
            decision = 'CONTINUE'
            veto = True
        # ADV2-001: unpack SPRT first; local decision/veto always win.
        result = {**sprt}
        result['flag'] = flag
        result['decision'] = decision
        result['error_rate_veto'] = veto
        result['error_rate'] = error_rate
        result['error_rate_unknown'] = error_rate_unknown
        result['n_records'] = len(recs)
        if error_rate_unknown:
            result['note'] = 'error_rate_unknown'
        out.append(result)
    return out


def run() -> dict:
    global a_effective, boot_calibrated
    a_effective, boot_calibrated = _load_a_boot()
    calibration_missing = a_effective is None
    try:  # ADV21-022: H-I7 wrap — never crash cron caller
        rows = load_telemetry()
    except Exception:
        rows = []
    if calibration_missing:
        groups: dict[str, list[dict]] = {}
        for rec in rows:
            groups.setdefault(extract_flag(rec), []).append(rec)
        decisions = []
        for flag, recs in sorted(groups.items()):
            decisions.append({
                'flag': flag,
                'decision': 'HOLD',
                'reason': 'calibration_missing',
                'n_records': len(recs),
                'n': len(recs),
                'error_rate_veto': False,
                'error_rate': None,
            })
    else:
        try:
            decisions = evaluate_groups(rows)
        except Exception:
            decisions = []
    summary = {
        'ts': datetime.now(timezone.utc).isoformat(),
        'theorem': 'Wald Sequential Analysis SPRT; alpha=beta=0.05; N(3,1) vs N(4,1)',
        'A': A,
        'A_effective': a_effective,
        'boot_calibrated': boot_calibrated,
        'calibration_missing': calibration_missing,
        'B': B,
        'n_records': len(rows),
        'n_flags': len(decisions),
        'n_promote': sum(1 for d in decisions if d['decision'] == 'PROMOTE'),
        'n_reject': sum(1 for d in decisions if d['decision'] == 'REJECT'),
        'n_continue': sum(1 for d in decisions if d['decision'] == 'CONTINUE'),
        'n_hold': sum(1 for d in decisions if d['decision'] == 'HOLD'),
        'decisions': decisions,
    }
    try:
        _atomic_write(OUT_PATH, summary)
        summary['output'] = str(OUT_PATH)
    except OSError as exc:
        summary['write_error'] = str(exc)
    return summary


def self_test() -> int:
    failures = []
    # ADV21-022: verify evaluate_groups returns non-empty on real input
    try:
        synthetic = [{'flag': 'test', 'score': 4.5}] * 5
        ev = evaluate_groups(synthetic)
        if not ev:
            failures.append('evaluate_groups returned empty on non-empty input')
    except Exception as exc:
        failures.append(f'evaluate_groups raised: {exc}')
    # Closed form: sigma=1, mu0=3, mu1=4 => increment = x - 3.5
    inc = llr_increment(4.0)
    if abs(inc - 0.5) > 1e-9:
        failures.append(f'llr_increment(4)={inc} expected 0.5')
    inc0 = llr_increment(3.0)
    if abs(inc0 - (-0.5)) > 1e-9:
        failures.append(f'llr_increment(3)={inc0} expected -0.5')
    # ADV-013: n=10 (and n=9) high scores must CONTINUE, not PROMOTE
    d = sprt_decision([4.5] * 10)
    if d['decision'] != 'CONTINUE':
        failures.append(f'n=10 expected CONTINUE got {d}')
    if d.get('reason') != 'n_below_power_floor':
        failures.append(f'n=10 reason {d.get("reason")}')
    d9 = sprt_decision([4.5] * 9)
    if d9['decision'] != 'CONTINUE':
        failures.append(f'n=9 expected CONTINUE got {d9}')
    # PROMOTE only after power floor: 50 high scores
    d = sprt_decision([4.5] * 50)
    if d['decision'] != 'PROMOTE':
        failures.append(f'expected PROMOTE got {d}')
    # REJECT: many 2.0 scores. increment=-1.5; |B|~2.94 => 2 samples
    d = sprt_decision([2.0] * 10)
    if d['decision'] != 'REJECT':
        failures.append(f'expected REJECT got {d}')
    # CONTINUE: scores at 3.5, increment=0
    d = sprt_decision([3.5] * 5)
    if d['decision'] != 'CONTINUE':
        failures.append(f'expected CONTINUE got {d}')
    # error-rate veto
    recs = [{'flag': 'f', 'mean_score': 5.0, 'errors': ['x']} for _ in range(20)]
    ev = evaluate_groups(recs)
    if not ev or ev[0]['decision'] == 'PROMOTE' and not ev[0]['error_rate_veto']:
        # high scores would promote, but errors should veto
        if ev and ev[0]['decision'] == 'PROMOTE':
            failures.append('error_rate veto failed to block PROMOTE')
    # ADV2-001: error_rate=0.15 must clobber SPRT PROMOTE (n>=N_MIN_POWER).
    recs_001 = [{'flag': 'adv2001', 'mean_score': 5.0, 'error_rate': 0.15} for _ in range(50)]
    ev001 = evaluate_groups(recs_001)
    if not ev001:
        failures.append('ADV2-001 evaluate_groups empty')
    else:
        if ev001[0]['decision'] != 'CONTINUE':
            failures.append(f'ADV2-001 expected CONTINUE got {ev001[0]["decision"]}')
        if not ev001[0].get('error_rate_veto'):
            failures.append('ADV2-001 error_rate_veto not set')
        if ev001[0].get('decision') == ev001[0].get('reason') == 'sprt' and ev001[0]['decision'] == 'PROMOTE':
            failures.append('ADV2-001 **sprt overwrote veto')
    # ADV2-006: missing error fields -> CONTINUE + error_rate_unknown
    recs_006 = [{'flag': 'adv2006', 'mean_score': 5.0} for _ in range(50)]
    ev006 = evaluate_groups(recs_006)
    if not ev006:
        failures.append('ADV2-006 evaluate_groups empty')
    else:
        if ev006[0]['decision'] != 'CONTINUE':
            failures.append(f'ADV2-006 expected CONTINUE got {ev006[0]["decision"]}')
        if ev006[0].get('error_rate_unknown') is not True:
            failures.append(f'ADV2-006 error_rate_unknown={ev006[0].get("error_rate_unknown")}')
        if ev006[0].get('note') != 'error_rate_unknown':
            failures.append(f'ADV2-006 note={ev006[0].get("note")}')
    a_eff, _boot = _load_a_boot()
    a_wald = math.log((1.0 - BETA) / ALPHA)
    if a_eff is not None and a_eff < a_wald:
        failures.append(f'A_effective={a_eff} < A_wald={a_wald} (never lowers threshold)')
    # ADV-003: missing calibration file => all HOLD, calibration_missing=True
    global CAL_PATH, OUT_PATH
    orig_cal, orig_out = CAL_PATH, OUT_PATH
    try:
        import tempfile
        td = Path(tempfile.mkdtemp())
        CAL_PATH = td / 'missing-block-bootstrap-sprt.json'
        OUT_PATH = td / 'shadow-sprt-decisions.json'
        a_miss, boot_miss = _load_a_boot()
        if a_miss is not None or boot_miss:
            failures.append(f'missing-cal-load: a={a_miss} boot={boot_miss}')
        out_miss = run()
        if not out_miss.get('calibration_missing'):
            failures.append('calibration_missing not True')
        if any(d.get('decision') != 'HOLD' for d in (out_miss.get('decisions') or [])):
            failures.append(f'expected all HOLD got {out_miss.get("decisions")}')
        if out_miss.get('n_promote'):
            failures.append('calibration_missing still promoted')
    except Exception as exc:
        failures.append(f'calibration_missing test raised: {exc}')
    finally:
        CAL_PATH, OUT_PATH = orig_cal, orig_out
    if failures:
        print(json.dumps({'self_test': 'FAIL', 'failures': failures}))
        return 1
    print(json.dumps({'self_test': 'PASS', 'A': A, 'B': B, 'A_effective': a_eff, 'boot_calibrated': _boot}))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument('--self-test', action='store_true')
    args = p.parse_args(argv)
    if args.self_test:
        return self_test()
    out = run()
    print(json.dumps({
        'n_flags': out.get('n_flags'),
        'n_promote': out.get('n_promote'),
        'n_reject': out.get('n_reject'),
        'n_continue': out.get('n_continue'),
        'output': out.get('output'),
    }))
    return 0


if __name__ == '__main__':
    sys.exit(main())
