#!/usr/bin/env python3
"""Cross-model autoscaler: per-tool latency p50/p95 plus llm-autoscaler base rec.

Reads cache/skill-latency.jsonl, groups by tool_name, flags tools with
p95 > 10s as model-switch candidates. Extends cache/autoscaler-recommendation.json.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import shutil
import sys
import tempfile
import uuid
from collections import defaultdict
from datetime import datetime, timezone, UTC
from pathlib import Path


def _hermes_home() -> Path:
    env = os.environ.get('HERMES_HOME', '').strip()
    p = Path(env) if env else Path.home() / '.hermes'
    if p.name != '.hermes' and p.parent.name == 'profiles':
        return p.parent.parent
    return p


def _profile_name() -> str:
    profile = os.environ.get('HERMES_PROFILE', 'fork').strip()
    if profile:
        return profile
    raw = os.environ.get('HERMES_HOME', '').strip()
    if raw:
        p = Path(raw)
        if p.parent.name == 'profiles':
            return p.name
    if (_hermes_home() / 'profiles' / 'fork').exists():
        return 'fork'
    return ''


_hermes_base = _hermes_home()
_hermes_profile = _profile_name()
_hermes_root = (
    (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile else _hermes_base
)
CACHE = _hermes_root / 'cache'
LATENCY_PATH = CACHE / 'skill-latency.jsonl'
BASE_REC_PATH = CACHE / 'autoscaler-recommendation.json'
OUT_PATH = CACHE / 'cross-model-autoscaler.json'

MIN_ROWS = 100
MIN_PER_TOOL = 5
P95_SWITCH_MS = 10000.0  # 10s


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _atomic_write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_suffix('.lock')
    with open(lock, 'w', encoding='utf-8') as lf:
        fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
        tmp = path.with_name(path.name + '.tmp')
        tmp.write_text(json.dumps(obj, indent=2) + '\n', encoding='utf-8')
        os.replace(str(tmp), str(path))


def _percentile(xs: list[float], p: float) -> float:
    ys = sorted(xs)
    n = len(ys)
    if n == 1:
        return ys[0]
    k = (n - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, n - 1)
    if f == c:
        return ys[f]
    return ys[f] + (ys[c] - ys[f]) * (k - f)


def _elapsed_ms(row: dict) -> float | None:
    for k in ('elapsed_ms', 'latency_ms', 'duration_ms', 'ms'):
        if k in row and row[k] is not None:
            try:
                v = float(row[k])
            except (TypeError, ValueError):
                continue
            if v >= 0:
                return v
    for k in ('elapsed_s', 'latency_s', 'duration_s'):
        if k in row and row[k] is not None:
            try:
                v = float(row[k]) * 1000.0
            except (TypeError, ValueError):
                continue
            if v >= 0:
                return v
    return None


def _tool_name(row: dict) -> str | None:
    for k in ('tool_name', 'tool', 'name', 'skill'):
        v = row.get(k)
        if v:
            return str(v)
    return None


def load_latency(path: Path) -> tuple[int, dict[str, list[float]]]:
    by: dict[str, list[float]] = defaultdict(list)
    n = 0
    if not path.exists():
        return 0, {}
    with path.open(encoding='utf-8') as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(row, dict):
                continue
            name = _tool_name(row)
            ms = _elapsed_ms(row)
            if not name or ms is None:
                continue
            by[name].append(ms)
            n += 1
    return n, by


def load_base_rec(path: Path):
    if not path.exists():
        return None
    try:
        obj = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return None
    return obj if isinstance(obj, dict) else None


def summarize_tools(by: dict[str, list[float]]) -> list[dict]:
    out = []
    for name, xs in by.items():
        if len(xs) < MIN_PER_TOOL:
            continue
        p50 = _percentile(xs, 50)
        p95 = _percentile(xs, 95)
        out.append({
            'tool_name': name,
            'n': len(xs),
            'p50_ms': p50,
            'p95_ms': p95,
            'mean_ms': sum(xs) / len(xs),
            'switch_candidate': p95 > P95_SWITCH_MS,
        })
    out.sort(key=lambda d: -d['p95_ms'])
    return out


def run(latency_path: Path | None = None, rec_path: Path | None = None) -> dict:
    lp = Path(latency_path) if latency_path is not None else LATENCY_PATH
    rp = Path(rec_path) if rec_path is not None else BASE_REC_PATH
    n, by = load_latency(lp)
    base = load_base_rec(rp)
    if n < MIN_ROWS:
        return {
            'status': 'insufficient_data',
            'reason': f'skill-latency.jsonl has {n} rows (need {MIN_ROWS})',
            'ts': _now(),
            'n_rows': n,
            'n_tools': len(by),
            'tools': [],
            'switch_candidates': [],
            'base_recommendation': base,
        }
    tools = summarize_tools(by)
    cands = [t for t in tools if t['switch_candidate']]
    rec_backend = (base or {}).get('recommended_backend') if base else None
    if rec_backend and cands:
        recommendation = f'switch high-p95 tools toward {rec_backend}'
    elif not cands:
        recommendation = 'no switch candidates (all p95 <= 10s)'
    else:
        recommendation = 'high-p95 tools without base backend rec'
    return {
        'status': 'ok',
        'ts': _now(),
        'n_rows': n,
        'n_tools': len(tools),
        'p95_switch_ms': P95_SWITCH_MS,
        'n_switch_candidates': len(cands),
        'switch_candidates': cands,
        'tools': tools,
        'base_recommendation': {
            'recommended_backend': (base or {}).get('recommended_backend'),
            'reason': (base or {}).get('reason'),
            'source': (base or {}).get('source'),
            'status': (base or {}).get('status'),
            'n_backends': (base or {}).get('n_backends'),
            'pareto_front': (base or {}).get('pareto_front'),
        } if base else None,
        'recommendation': recommendation,
    }


def _self_test() -> int:
    td = Path(tempfile.mkdtemp(prefix=f'cma-{uuid.uuid4().hex[:8]}-'))
    try:
        lat = td / 'skill-latency.jsonl'
        rec = td / 'autoscaler-recommendation.json'
        rows = []
        for i in range(60):
            rows.append({'tool_name': 'fast_tool', 'elapsed_ms': 20.0 + i})
        for i in range(60):
            rows.append({'tool_name': 'slow_tool', 'elapsed_ms': 12000.0 + i * 10})
        lat.write_text('\n'.join(json.dumps(r) for r in rows) + '\n', encoding='utf-8')
        rec.write_text(json.dumps({
            'status': 'ok',
            'recommended_backend': 'claude-haiku-4-5',
            'reason': 'test',
            'source': 'synthetic',
            'n_backends': 1,
            'pareto_front': [{'name': 'claude-haiku-4-5'}],
        }), encoding='utf-8')
        r = run(latency_path=lat, rec_path=rec)
        assert r['status'] == 'ok', r
        names = {t['tool_name'] for t in r['tools']}
        assert names == {'fast_tool', 'slow_tool'}, names
        cands = {t['tool_name'] for t in r['switch_candidates']}
        assert cands == {'slow_tool'}, cands
        assert r['base_recommendation']['recommended_backend'] == 'claude-haiku-4-5'
        missing = run(latency_path=td / 'nope.jsonl', rec_path=td / 'nope2.json')
        assert missing['status'] == 'insufficient_data'
        print('[cross-model-autoscaler] --self-test PASS n_rows={} cands={}'.format(
            r['n_rows'], r['n_switch_candidates']))
        return 0
    finally:
        shutil.rmtree(td, ignore_errors=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true')
    args = ap.parse_args()
    if args.self_test:
        try:
            return _self_test()
        except Exception as exc:
            print(f'[cross-model-autoscaler] --self-test FAIL: {exc}')
            return 1
    try:
        r = run()
        _atomic_write(OUT_PATH, r)
        slim = {k: r[k] for k in r if k != 'tools'}
        slim['top_tools'] = (r.get('tools') or [])[:8]
        print(json.dumps(slim))
        return 0
    except Exception as exc:
        print(json.dumps({'status': 'error', 'reason': str(exc), 'ts': _now()}))
        return 1


if __name__ == '__main__':
    sys.exit(main())
