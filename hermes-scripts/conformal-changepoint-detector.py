#!/usr/bin/env python3
"""(eval-only) Conformal martingale changepoint detector on sequential eval scores
and per-turn agent behavior vectors (skill entropy, error rate, output size).

Writes conformal-changepoint.json (compat) and changepoint-state.json
(e_value, last_computed_turn, alert_flag). Fail-open. stdlib only.
"""
from __future__ import annotations
import argparse, fcntl, json, math, os, random, sys, tempfile, uuid
from datetime import datetime, timezone, UTC
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', 'fork')
if _hermes_base.name != '.hermes' and _hermes_base.parent.name == 'profiles':
    _hermes_base = _hermes_base.parent.parent
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base
CACHE = _hermes_root / 'cache'

def _now() -> str:
    return datetime.now(UTC).isoformat()

def _atomic_write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(path.suffix + '.lock') if path.suffix else path.with_name(path.name + '.lock')
    tmp = path.with_name(path.name + '.tmp')
    payload = json.dumps(obj, indent=2) + '\n'
    with open(str(lock_path), 'a', encoding='utf-8') as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        try:
            tmp.write_text(payload, encoding='utf-8')
            os.replace(str(tmp), str(path))
        finally:
            fcntl.flock(lf, fcntl.LOCK_UN)

def _temp_out(prefix: str) -> Path:
    return Path(tempfile.gettempdir()) / (f'{prefix}-{uuid.uuid4().hex}.json')

OUT_PATH = CACHE / 'conformal-changepoint.json'
STATE_PATH = CACHE / 'changepoint-state.json'
ALPHA = 0.05
EPSILON = 0.2
WINDOW = 500
BEHAVIOR_PATH = CACHE / 'turn-behavior.jsonl'


def p_value_rank(x, history):
    n = len(history)
    if n == 0:
        return None
    le = sum(1 for h in history if h <= x)
    return (1.0 + le) / (n + 1.0)


def detect(scores, alpha=ALPHA, epsilon=EPSILON):
    xs = []
    for s in scores or []:
        try:
            v = float(s)
        except (TypeError, ValueError):
            continue
        if v != v:
            continue
        xs.append(v)
    if WINDOW and len(xs) > WINDOW:
        xs = xs[-WINDOW:]
    n = len(xs)
    if n == 0:
        return {
            'detected': None,
            'changepoint_detected': None,
            'index': None,
            'martingale': None,
            'e_value': None,
            'alert_flag': False,
            'last_computed_turn': None,
            'alpha': alpha,
            'n': 0,
            'status': 'insufficient_data',
            'ts': _now(),
        }
    log_m = 0.0
    idx = None
    martingale = 1.0
    thresh = 1.0 / max(alpha, 1e-12)
    eps = min(max(float(epsilon), 1e-6), 0.99)
    for t in range(1, n):
        pv = p_value_rank(xs[t], xs[:t])
        if pv is None:
            continue
        pv = min(max(pv, 1e-12), 1.0)
        log_m = max(0.0, log_m + math.log(eps) + (eps - 1.0) * math.log(pv))
        martingale = math.exp(min(log_m, 40.0))
        if idx is None and martingale >= thresh:
            idx = t
    return {
        'detected': idx is not None,
        'changepoint_detected': idx is not None,
        'index': idx,
        'martingale': martingale,
        'e_value': martingale,
        'alert_flag': bool(idx is not None),
        'last_computed_turn': n,
        'alpha': alpha,
        'epsilon': eps,
        'n': n,
        'status': 'ok',
        'ts': _now(),
    }


def _behavior_scalar(rec):
    try:
        ent = float(rec.get('skill_entropy', 0.5))
    except (TypeError, ValueError):
        ent = 0.5
    suc = rec.get('success')
    err = 0.0 if suc in (True, 1, '1', 'true', 'ok', 'success') else 1.0
    try:
        tok = float(rec.get('token_estimate') or 0.0)
    except (TypeError, ValueError):
        tok = 0.0
    size = math.log1p(max(0.0, tok)) / 10.0
    return 0.5 * max(0.0, min(2.0, ent)) + 0.4 * err + 0.1 * size


def load_behavior_scores(path=None, window=WINDOW):
    p = path or BEHAVIOR_PATH
    xs = []
    last_ts = None
    if not p.exists():
        return xs, last_ts
    try:
        with p.open(encoding='utf-8', errors='replace') as fh:
            for line in fh:
                raw = line.strip()
                if not raw:
                    continue
                try:
                    rec = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if not isinstance(rec, dict):
                    continue
                xs.append(_behavior_scalar(rec))
                last_ts = rec.get('ts') or rec.get('turn_id') or last_ts
    except OSError:
        return [], None
    if window and len(xs) > window:
        xs = xs[-window:]
    return xs, last_ts


def load_scores():
    """Prefer calibration-log; skip scope==ue_blackbox entirely (no tool_name fallback)."""
    calib = CACHE / 'calibration-log.jsonl'
    xs = []
    if calib.exists():
        try:
            with calib.open(encoding='utf-8', errors='replace') as fh:
                for line in fh:
                    raw = line.strip()
                    if not raw:
                        continue
                    try:
                        rec = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    if not isinstance(rec, dict):
                        continue
                    if rec.get('scope') == 'ue_blackbox':
                        continue
                    raw_score = rec.get('predicted_confidence')
                    if raw_score is None:
                        continue
                    try:
                        xs.append(float(raw_score))
                    except (TypeError, ValueError):
                        continue
        except OSError:
            xs = []
        if xs:
            return xs[-WINDOW:] if len(xs) > WINDOW else xs
    p = CACHE / 'eval-scores.jsonl'
    if not p.exists():
        return xs
    try:
        for line in p.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                if not isinstance(rec, dict):
                    continue
                if rec.get('scope') == 'ue_blackbox':
                    continue
                xs.append(float(rec.get('score', rec.get('value'))))
            except (json.JSONDecodeError, TypeError, ValueError):
                continue
    except OSError:
        return []
    return xs[-WINDOW:] if len(xs) > WINDOW else xs


def _state_payload(r, source, last_ts=None):
    return {
        'e_value': r.get('e_value'),
        'last_computed_turn': last_ts if last_ts is not None else r.get('last_computed_turn'),
        'alert_flag': bool(r.get('alert_flag')),
        'index': r.get('index'),
        'martingale': r.get('martingale'),
        'n': r.get('n'),
        'alpha': r.get('alpha'),
        'source': source,
        'status': r.get('status'),
        'ts': r.get('ts') or _now(),
    }


def synthetic_session(rng, n, t_star=None):
    xs = []
    for t in range(n):
        if t_star is not None and t >= t_star:
            xs.append(0.5 * rng.random())
        else:
            xs.append(0.8 + 0.2 * rng.random())
    return xs


def kill_test(n_runs=40, n=120, t_star=80, alpha=0.05, seed=1):
    far = 0
    delays = []
    miss = 0
    for i in range(n_runs):
        rng = random.Random(seed + i)
        r0 = detect(synthetic_session(rng, n, None), alpha=alpha)
        if r0.get('changepoint_detected'):
            far += 1
        rng = random.Random(seed + 10_000 + i)
        r1 = detect(synthetic_session(rng, n, t_star), alpha=alpha)
        if r1.get('changepoint_detected') and r1.get('index') is not None:
            delays.append(r1['index'] - t_star)
        else:
            miss += 1
    mean_delay = (sum(delays) / len(delays)) if delays else None
    far_rate = far / float(n_runs)
    miss_rate = miss / float(n_runs)
    ok = (mean_delay is not None and mean_delay < 30.0 and far_rate < 0.05)
    return {
        'ok': ok,
        'n_runs': n_runs,
        'mean_detection_delay': mean_delay,
        'false_alarm_rate': far_rate,
        'miss_rate': miss_rate,
        'n_detected': len(delays),
    }


def _self_test() -> int:
    empty = detect([])
    assert empty['status'] == 'insufficient_data'
    assert empty['changepoint_detected'] is None
    rng = random.Random(1)
    stable = [rng.gauss(0.6, 0.03) for _ in range(40)]
    detect(stable, alpha=0.05)
    shifted = stable + [rng.gauss(0.15, 0.03) for _ in range(20)]
    r1 = detect(shifted, alpha=0.05)
    assert r1['n'] == 60
    kt = kill_test(n_runs=40, n=120, t_star=80, alpha=0.05, seed=3)
    assert kt['ok'], kt
    recs = [
        {'skill_entropy': 1.0, 'success': True, 'token_estimate': 10, 'ts': 't1'},
        {'skill_entropy': 0.2, 'success': False, 'token_estimate': 400, 'ts': 't2'},
    ]
    xs = [_behavior_scalar(r) for r in recs]
    assert xs[1] > xs[0]
    tmp = _temp_out('changepoint')
    stmp = _temp_out('changepoint-state')
    _atomic_write(tmp, r1)
    _atomic_write(stmp, _state_payload(r1, 'self-test'))
    try:
        tmp.unlink(missing_ok=True)
        stmp.unlink(missing_ok=True)
        tmp.with_suffix(tmp.suffix + '.lock').unlink(missing_ok=True)
        stmp.with_suffix(stmp.suffix + '.lock').unlink(missing_ok=True)
    except OSError:
        pass
    print('[conformal-changepoint-detector] --self-test PASS shift={} idx={} delay={} far={}'.format(
        r1['changepoint_detected'], r1['index'], kt['mean_detection_delay'], kt['false_alarm_rate']))
    return 0


def run(alpha=ALPHA, out_path=None, state_path=None):
    beh, last_ts = load_behavior_scores()
    source = 'turn-behavior'
    scores = beh
    if not scores:
        scores = load_scores()
        source = 'calibration-log'
        last_ts = None
    r = detect(scores, alpha=alpha)
    r['source'] = source
    if last_ts is not None:
        r['last_computed_turn'] = last_ts
    if r.get('status') != 'insufficient_data':
        dest = out_path or OUT_PATH
        sdest = state_path or STATE_PATH
        _atomic_write(dest, r)
        _atomic_write(sdest, _state_payload(r, source, last_ts))
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--run', action='store_true')
    ap.add_argument('--kill-test', action='store_true')
    ap.add_argument('--alpha', type=float, default=ALPHA)
    args = ap.parse_args()
    if args.self_test:
        try:
            sys.exit(_self_test())
        except Exception as exc:
            print(f'[conformal-changepoint-detector] --self-test FAIL: {exc}')
            sys.exit(1)
    if args.kill_test:
        kt = kill_test(n_runs=40, n=120, t_star=80, alpha=args.alpha)
        print(json.dumps(kt))
        sys.exit(0 if kt['ok'] else 1)
    try:
        r = run(alpha=args.alpha)
        public = {k: r[k] for k in r if k not in ('window',)}
        print(json.dumps(public))
    except Exception as e:
        print(json.dumps({'status': 'error', 'reason': str(e)}))
        sys.exit(0)


if __name__ == '__main__':
    main()
