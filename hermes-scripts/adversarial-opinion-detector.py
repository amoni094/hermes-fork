#!/usr/bin/env python3
"""Detect strategic opinion manipulation via z-score and Grubbs test."""
from __future__ import annotations
import argparse, fcntl, json, math, os, sys, uuid
from datetime import datetime, timezone, UTC
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', 'fork')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base
CACHE = _hermes_root / 'cache'
OUT_PATH = CACHE / 'adversarial-opinion-report.json'
WEIGHTS = CACHE / 'consensus-weights.json'
Z_TH = 2.5
SKIP_KEYS = frozenset({'ts', 'status', 'n_arms', 'final_score', 'distortion_bound', 'reason'})


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
            fcntl.flock(lf.fileno(), fcntl.LOCK_UN)


def _mean_std(xs):
    n = len(xs)
    if n == 0:
        return 0.0, 0.0
    mu = sum(xs) / n
    var = sum((x - mu) ** 2 for x in xs) / n
    return mu, math.sqrt(var)


def grubbs_G(xs):
    mu, sd = _mean_std(xs)
    if sd <= 0:
        return 0.0, -1
    devs = [abs(x - mu) / sd for x in xs]
    i = max(range(len(devs)), key=lambda j: devs[j])
    return devs[i], i


def grubbs_critical(n, alpha=0.05):
    if n < 3:
        return 999.0
    t = 3.0 if n < 30 else 2.6
    return ((n - 1) / math.sqrt(n)) * math.sqrt(t * t / (n - 2 + t * t))


def detect(opinions):
    if not opinions:
        return {
            'ts': _now(), 'n': 0, 'status': 'insufficient_data',
            'mean': None, 'std': None, 'grubbs_G': None, 'grubbs_crit': None,
            'flags': [], 'n_flagged': 0,
        }
    labeled = []
    for i, o in enumerate(opinions):
        if isinstance(o, dict):
            labeled.append((str(o.get('id', i)), float(o.get('score', o.get('opinion', 0.0)))))
        elif isinstance(o, (tuple, list)) and len(o) == 2:
            labeled.append((str(o[0]), float(o[1])))
        else:
            labeled.append((str(i), float(o)))
    xs = [v for _, v in labeled]
    mu, sd = _mean_std(xs)
    flags = []
    for name, v in labeled:
        z = 0.0 if sd <= 0 else (v - mu) / sd
        if abs(z) > Z_TH:
            flags.append({'id': name, 'score': v, 'z': z, 'rule': 'zscore'})
    G, idx = grubbs_G(xs)
    crit = grubbs_critical(len(xs))
    if G > crit and 0 <= idx < len(labeled):
        name, v = labeled[idx]
        if not any(f['id'] == name for f in flags):
            flags.append({'id': name, 'score': v, 'G': G, 'rule': 'grubbs'})
        else:
            for f in flags:
                if f['id'] == name:
                    f['G'] = G
                    f['rule'] = f['rule'] + '+grubbs'
    return {
        'ts': _now(), 'n': len(xs), 'status': 'ok',
        'mean': mu, 'std': sd, 'grubbs_G': G, 'grubbs_crit': crit,
        'flags': flags, 'n_flagged': len(flags),
    }


def load_opinions(path: Path | None = None) -> list:
    src = path if path is not None else WEIGHTS
    if not src.exists():
        return []
    try:
        data = json.loads(src.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return []
    if isinstance(data, list):
        return data
    if not isinstance(data, dict):
        return []
    out = []
    for k, v in data.items():
        if k in SKIP_KEYS:
            continue
        if isinstance(v, (int, float)) and math.isfinite(float(v)):
            out.append((k, float(v)))
    return out


def run(src: Path | None = None, dest: Path | None = None) -> dict:
    r = detect(load_opinions(src))
    _atomic_write(dest if dest is not None else OUT_PATH, r)
    return r


def _self_test() -> int:
    opinions = [0.70, 0.72, 0.68, 0.71, 0.69, 0.73, 0.70, 9.5]
    r = detect(opinions)
    assert r['n_flagged'] >= 1
    assert any(abs(f['score'] - 9.5) < 1e-9 for f in r['flags'])
    empty = detect([])
    assert empty.get('status') == 'insufficient_data'
    tmp = OUT_PATH.with_name(OUT_PATH.stem + '_test_' + uuid.uuid4().hex + OUT_PATH.suffix)
    try:
        _atomic_write(tmp, r)
        loaded = json.loads(tmp.read_text(encoding='utf-8'))
        assert loaded['n_flagged'] >= 1
    finally:
        tmp.unlink(missing_ok=True)
        tmp.with_suffix('.lock').unlink(missing_ok=True)
    print('[adversarial-opinion-detector] --self-test PASS flagged={}'.format(r['n_flagged']))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--run', action='store_true')
    args = ap.parse_args()
    if args.self_test:
        try:
            sys.exit(_self_test())
        except Exception as exc:
            print(f'[adversarial-opinion-detector] --self-test FAIL: {exc}')
            sys.exit(1)
    try:
        r = run()
        print(json.dumps(r, default=str))
    except Exception as e:
        print(json.dumps({'status': 'error', 'reason': str(e), 'ts': _now()}))
    sys.exit(0)


if __name__ == '__main__':
    main()
