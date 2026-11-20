#!/usr/bin/env python3
"""Post-process tool/subagent outputs: TV-distance alignment + persist gate."""
from __future__ import annotations
import argparse, fcntl, json, math, os, sys, tempfile, uuid
from collections import Counter
from datetime import datetime, timezone, UTC
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', 'fork')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base
CACHE = _hermes_root / 'cache'
CALIB = CACHE / 'calibration-log.jsonl'
OUT_PATH = CACHE / 'alignment_stats.json'
POOL_PATH = CACHE / 'tool-result-pool.jsonl'


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


def tv_distance(p: dict, q: dict) -> float:
    keys = set(p) | set(q)
    if not keys:
        return 0.0
    return 0.5 * sum(abs(p.get(k, 0.0) - q.get(k, 0.0)) for k in keys)


def _norm(counter: Counter, n: int) -> dict:
    if n <= 0:
        return {}
    return {k: v / n for k, v in counter.items()}


def _bucket_conf(x) -> str:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return 'unknown'
    if v < 0.4:
        return 'low'
    if v < 0.7:
        return 'mid'
    return 'high'


def load_rows(path: Path, limit: int = 4000) -> list:
    if not path.exists():
        return []
    rows = []
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
                rows.append(rec)
    except OSError:
        return []
    return rows[-limit:]


def align(rows: list) -> dict:
    n = len(rows)
    if n < 20:
        return {'status': 'insufficient_data', 'n': n, 'ts': _now()}
    split = max(10, n // 2)
    hist, recent = rows[:split], rows[split:]
    def dist(xs):
        c = Counter()
        for r in xs:
            c[_bucket_conf(r.get('predicted_confidence', r.get('confidence', r.get('score'))))] += 1
        return _norm(c, len(xs))
    target, emp = dist(hist), dist(recent)
    tv = tv_distance(emp, target)
    persist = tv <= 0.25
    return {
        'status': 'ok',
        'ts': _now(),
        'n': n,
        'n_hist': len(hist),
        'n_recent': len(recent),
        'tv_distance': tv,
        'persist_ok': persist,
        'target': target,
        'empirical': emp,
        'memory_write_gate': 'allow' if persist else 'hold',
    }


def run() -> dict:
    try:
        rows = load_rows(CALIB)
        out = align(rows)
        if out.get('status') != 'insufficient_data':
            _atomic_write(OUT_PATH, out)
        return out
    except Exception as e:
        return {'status': 'error', 'reason': str(e), 'ts': _now()}


def _self_test() -> int:
    empty = align([])
    assert empty['status'] == 'insufficient_data'
    rows = [{'predicted_confidence': 0.8} for _ in range(40)] + [{'predicted_confidence': 0.2} for _ in range(40)]
    r = align(rows)
    assert r['status'] == 'ok'
    assert 0.0 <= r['tv_distance'] <= 1.0
    assert abs(tv_distance({'a': 1.0}, {'a': 1.0})) < 1e-12
    tmp = Path(tempfile.gettempdir()) / ('align-test-' + uuid.uuid4().hex + '.json')
    _atomic_write(tmp, r)
    tmp.unlink(missing_ok=True)
    print('[output-alignment-filter] --self-test PASS tv={:.3f}'.format(r['tv_distance']))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true')
    args = ap.parse_args()
    if args.self_test:
        try:
            return _self_test()
        except Exception as exc:
            print(f'[output-alignment-filter] --self-test FAIL: {exc}')
            return 1
    out = run()
    print(json.dumps(out))
    return 0


if __name__ == '__main__':
    sys.exit(main())
