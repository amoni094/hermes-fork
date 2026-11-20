#!/usr/bin/env python3
"""Multiplicative-weights resource sharing. n==0 is unmeasured, not a default eta."""
from __future__ import annotations
import argparse, fcntl, json, math, os, sys, uuid
from datetime import datetime, timezone, UTC
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', 'fork')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base
CACHE = _hermes_root / 'cache'
OUT_PATH = CACHE / 'randomized-resource-sharer.json'
ALLOC_STATE = CACHE / 'allocation-state.json'


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


def eta_of(n: int, T: int):
    if n <= 0 or T <= 0:
        return None
    return math.sqrt(math.log(max(n, 2)) / max(T, 1))


def run_mwu_losses(loss_rows: list[list[float]]) -> dict:
    if not loss_rows:
        return {
            'generated_at': _now(), 'n': 0, 'T': 0, 'eta': None,
            'final_weights': [], 'mean_loss': None, 'status': 'insufficient_data',
        }
    n = len(loss_rows[0])
    T = len(loss_rows)
    if n <= 0 or T <= 0:
        return {
            'generated_at': _now(), 'n': int(n), 'T': int(T), 'eta': None,
            'final_weights': [], 'mean_loss': None, 'status': 'insufficient_data',
        }
    eta = eta_of(n, T)
    w = [1.0] * n
    losses = []
    for loss in loss_rows:
        s = sum(w)
        p = [x / s for x in w]
        losses.append(sum(pi * li for pi, li in zip(p, loss)))
        w = [wi * math.exp(-eta * li) for wi, li in zip(w, loss)]
    return {
        'generated_at': _now(), 'n': n, 'T': T, 'eta': round(eta, 6),
        'final_weights': [round(x, 6) for x in w],
        'mean_loss': round(sum(losses) / T, 6), 'status': 'ok',
    }


def load_loss_rows(path: Path | None = None):
    src = path if path is not None else ALLOC_STATE
    if not src.exists():
        return []
    try:
        data = json.loads(src.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return []
    arms = data.get('arms') if isinstance(data, dict) else None
    if not isinstance(arms, dict) or not arms:
        return []
    # one-step loss = 1 - clipped utility/mean if present
    row = []
    for rec in arms.values():
        if isinstance(rec, dict):
            u = rec.get('mean', rec.get('utility', rec.get('n_allocated')))
        else:
            u = rec
        try:
            uf = float(u)
        except (TypeError, ValueError):
            return []
        row.append(max(0.0, min(1.0, 1.0 - uf if 0.0 <= uf <= 1.0 else 1.0 / (1.0 + abs(uf)))))
    if not row:
        return []
    return [row]


def run(state_path: Path | None = None, dest: Path | None = None, loss_rows=None) -> dict:
    rows = loss_rows if loss_rows is not None else load_loss_rows(state_path)
    r = run_mwu_losses(rows)
    _atomic_write(dest if dest is not None else OUT_PATH, r)
    return r


def self_test() -> dict:
    rows = [[0.1, 0.5, 0.9], [0.2, 0.4, 0.8], [0.15, 0.6, 0.7]]
    r = run_mwu_losses(rows)
    assert r['status'] == 'ok' and r['eta'] is not None
    z = run_mwu_losses([])
    assert z['status'] == 'insufficient_data' and z['eta'] is None
    assert eta_of(0, 10) is None
    tmp = OUT_PATH.with_name(OUT_PATH.stem + '_test_' + uuid.uuid4().hex + OUT_PATH.suffix)
    _atomic_write(tmp, r)
    try:
        assert tmp.exists()
    finally:
        tmp.unlink(missing_ok=True)
        tmp.with_suffix('.lock').unlink(missing_ok=True)
    return {'self_test': 'PASS', 'sample': r}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--run', action='store_true')
    args = ap.parse_args()
    if args.self_test:
        print(json.dumps(self_test(), indent=2, default=str))
        sys.exit(0)
    try:
        r = run()
        print(json.dumps(r, indent=2, default=str))
    except Exception as e:
        print(json.dumps({'status': 'error', 'reason': str(e), 'ts': _now()}))
    sys.exit(0)


if __name__ == '__main__':
    main()
