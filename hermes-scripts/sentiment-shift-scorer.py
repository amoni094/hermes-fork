#!/usr/bin/env python3
"""Empirical-Bayes shrinkage of per-skill side-effect rates (memory-write trigger)."""
from __future__ import annotations
import argparse, fcntl, json, math, os, sys, tempfile, uuid
from collections import defaultdict
from datetime import datetime, timezone, UTC
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', 'fork')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base
CACHE = _hermes_root / 'cache'
CALIB = CACHE / 'calibration-log.jsonl'
OUT_PATH = CACHE / 'sentiment-shift.json'


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _atomic_write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix('.lock')
    tmp = path.with_name(path.name + '.tmp')
    with open(str(lock_path), 'a', encoding='utf-8') as lf:
        fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
        try:
            tmp.write_text(json.dumps(obj, indent=2) + '\n', encoding='utf-8')
            os.replace(str(tmp), str(path))
        finally:
            try:
                fcntl.flock(lf.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass


def james_stein_shrink(raw: dict, global_mean: float, between_var: float) -> tuple:
    """Return (shrunk dict, B coefficient). B -> 1 as between_var -> 0."""
    if between_var <= 1e-12:
        B = 1.0
    else:
        # B = sigma2 / (sigma2 + tau2); use within~mean residual as sigma2 proxy
        sigma2 = 0.05
        B = sigma2 / (sigma2 + between_var)
    B = max(0.0, min(1.0, B))
    shrunk = {k: (1.0 - B) * v + B * global_mean for k, v in raw.items()}
    return shrunk, B


def score(groups: dict) -> dict:
    if not groups:
        return {'status': 'insufficient_data', 'n_skills': 0, 'ts': _now()}
    raw = {}
    for k, xs in groups.items():
        if not xs:
            continue
        raw[k] = sum(xs) / len(xs)
    if len(raw) < 2:
        return {'status': 'insufficient_data', 'n_skills': len(raw), 'ts': _now()}
    vals = list(raw.values())
    mu = sum(vals) / len(vals)
    between = sum((v - mu) ** 2 for v in vals) / (len(vals) - 1)
    shrunk, B = james_stein_shrink(raw, mu, between)
    deltas = {k: shrunk[k] - mu for k in shrunk}
    flags = [k for k, d in deltas.items() if abs(d) > 0.15]
    return {
        'status': 'ok',
        'ts': _now(),
        'n_skills': len(raw),
        'global_mean': mu,
        'between_var': between,
        'shrinkage_B': B,
        'n_flagged': len(flags),
        'flagged': flags[:30],
        'sensitivity_stability_rate': 1.0 - min(1.0, len(flags) / max(1, len(raw))),
    }


def load_groups(path: Path, limit: int = 8000) -> dict:
    groups = defaultdict(list)
    if not path.exists():
        return {}
    n = 0
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(rec, dict):
                    continue
                if rec.get('scope') == 'ue_blackbox':
                    continue
                skill = rec.get('scope') or rec.get('skill') or rec.get('tool_name') or rec.get('tool')
                if not skill:
                    continue
                conf = rec.get('predicted_confidence', rec.get('confidence', rec.get('score')))
                try:
                    v = float(conf)
                except (TypeError, ValueError):
                    continue
                groups[str(skill)].append(max(0.0, min(1.0, v)))
                n += 1
                if n >= limit:
                    # keep streaming but only last-ish: stop at limit from start is ok
                    break
    except OSError:
        return {}
    return dict(groups)


def run() -> dict:
    try:
        groups = load_groups(CALIB)
        out = score(groups)
        if out.get('status') != 'insufficient_data':
            _atomic_write(OUT_PATH, out)
        return out
    except Exception as e:
        return {'status': 'error', 'reason': str(e), 'ts': _now()}


def _self_test() -> int:
    empty = score({})
    assert empty['status'] == 'insufficient_data'
    high_var = {'a': [0.9, 0.95], 'b': [0.1, 0.05], 'c': [0.5, 0.55]}
    r1 = score(high_var)
    low_var = {'a': [0.51, 0.52], 'b': [0.49, 0.50], 'c': [0.50, 0.51]}
    r2 = score(low_var)
    assert r2['shrinkage_B'] > r1['shrinkage_B']
    tmp = Path(tempfile.gettempdir()) / ('sent-test-' + uuid.uuid4().hex + '.json')
    _atomic_write(tmp, r2)
    tmp.unlink(missing_ok=True)
    print('[sentiment-shift-scorer] --self-test PASS B_highvar={:.3f} B_lowvar={:.3f}'.format(r1['shrinkage_B'], r2['shrinkage_B']))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true')
    args = ap.parse_args()
    if args.self_test:
        try:
            return _self_test()
        except Exception as exc:
            print(f'[sentiment-shift-scorer] --self-test FAIL: {exc}')
            return 1
    out = run()
    print(json.dumps(out))
    return 0


if __name__ == '__main__':
    sys.exit(main())
