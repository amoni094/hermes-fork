#!/usr/bin/env python3
"""Learning the Cost of Reliable Inference — cost/quality provider routing.

Maintains per-provider Bayesian quality posterior and mean cost from
skill-latency.jsonl, then selects argmin(cost) among providers whose
posterior quality meets the threshold.
"""
from __future__ import annotations

import os
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', 'fork')
_hermes_root = (
    (_hermes_base / 'profiles' / _hermes_profile)
    if _hermes_profile and 'profiles' not in str(_hermes_base)
    else _hermes_base
)

import argparse
import fcntl
import json
import math
import sys
import uuid
from collections import defaultdict
from datetime import datetime, timezone, UTC

CACHE = _hermes_root / 'cache'
OUT_PATH = CACHE / 'provider-routing-state.json'
LATENCY_LOG = CACHE / 'skill-latency.jsonl'
QUALITY_THRESHOLD = 0.70
MIN_N = 5
SENTINELS = frozenset({'audit_latency', 'audit_latency_nopre', 'ue_blackbox'})


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _atomic_write_json(path: Path, obj) -> None:
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


def _load_latency(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    try:
        with path.open(encoding='utf-8') as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(rec, dict):
                    continue
                name = rec.get('tool_name') or rec.get('provider') or rec.get('name')
                if not name or name in SENTINELS:
                    continue
                rows.append(rec)
    except OSError:
        return []
    return rows


def _stats_from_rows(rows: list[dict]) -> dict:
    buckets: dict[str, dict] = defaultdict(lambda: {
        'costs': [],
        'quality_passes': 0,
        'quality_total': 0,
    })
    for rec in rows:
        name = str(rec.get('tool_name') or rec.get('provider') or rec.get('name'))
        cost = rec.get('elapsed_ms')
        if cost is None:
            cost = rec.get('cost')
        try:
            cost_f = float(cost)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(cost_f) or cost_f < 0:
            continue
        size = rec.get('result_size')
        try:
            size_f = float(size) if size is not None else 1.0
        except (TypeError, ValueError):
            size_f = 0.0
        b = buckets[name]
        b['costs'].append(cost_f)
        b['quality_total'] += 1
        if size_f > 0:
            b['quality_passes'] += 1
    out = {}
    for name, b in buckets.items():
        costs = b['costs']
        n = len(costs)
        if n == 0:
            continue
        mean = sum(costs) / n
        var = sum((c - mean) ** 2 for c in costs) / n
        passes = b['quality_passes']
        total = b['quality_total']
        # Beta(1+passes, 1+fails) posterior mean
        fails = max(total - passes, 0)
        posterior = (1.0 + passes) / (2.0 + total)
        out[name] = {
            'cost_mean': round(mean, 4),
            'cost_var': round(var, 4),
            'quality_passes': passes,
            'quality_total': total,
            'posterior_quality': round(posterior, 6),
            'n': n,
            'fails': fails,
        }
    return out


def pareto_coverage(eligible: list[dict], all_providers: list[dict]) -> float:
    if not all_providers:
        return 0.0
    # fraction of routed (eligible) providers that are undominated in cost vs 1-quality
    undom = 0
    for p in eligible:
        dominated = False
        for q in all_providers:
            if q is p:
                continue
            better_cost = q['cost_mean'] <= p['cost_mean']
            better_q = q['posterior_quality'] >= p['posterior_quality']
            strictly = (q['cost_mean'] < p['cost_mean'] or q['posterior_quality'] > p['posterior_quality'])
            if better_cost and better_q and strictly:
                dominated = True
                break
        if not dominated:
            undom += 1
    return undom / max(len(eligible), 1)


def route(providers: dict, threshold: float = QUALITY_THRESHOLD, min_n: int = MIN_N) -> dict:
    ts = _now()
    if not providers:
        return {
            'ts': ts,
            'status': 'insufficient_data',
            'reason': 'no_provider_rows',
            'providers': {},
            'selected': None,
            'quality_threshold': threshold,
            'n_providers': 0,
        }
    eligible = []
    skipped_n = []
    skipped_q = []
    for name, st in providers.items():
        rec = {'name': name, **st}
        if st['n'] < min_n:
            skipped_n.append(name)
            continue
        if st['posterior_quality'] < threshold:
            skipped_q.append(name)
            continue
        eligible.append(rec)
    if not eligible:
        return {
            'ts': ts,
            'status': 'insufficient_data',
            'reason': 'no_provider_meets_threshold',
            'providers': providers,
            'selected': None,
            'quality_threshold': threshold,
            'n_providers': len(providers),
            'skipped_low_n': skipped_n,
            'skipped_low_quality': skipped_q,
        }
    eligible.sort(key=lambda r: (r['cost_mean'], -r['posterior_quality']))
    chosen = eligible[0]
    all_list = [{'name': n, **st} for n, st in providers.items()]
    return {
        'ts': ts,
        'status': 'ok',
        'providers': providers,
        'selected': chosen['name'],
        'selected_cost_mean': chosen['cost_mean'],
        'selected_posterior_quality': chosen['posterior_quality'],
        'quality_threshold': threshold,
        'n_providers': len(providers),
        'n_eligible': len(eligible),
        'pareto_coverage': round(pareto_coverage(eligible, all_list), 4),
        'skipped_low_n': skipped_n,
        'skipped_low_quality': skipped_q,
        'last_updated': ts,
    }


def run(latency_path: Path | None = None, out_path: Path | None = None,
        threshold: float = QUALITY_THRESHOLD) -> dict:
    src = latency_path if latency_path is not None else LATENCY_LOG
    dest = out_path if out_path is not None else OUT_PATH
    rows = _load_latency(src)
    providers = _stats_from_rows(rows)
    result = route(providers, threshold=threshold)
    _atomic_write_json(dest, result)
    return result


def _self_test() -> int:
    td = Path('/tmp') / ('pqr-' + uuid.uuid4().hex[:10])
    td.mkdir(parents=True, exist_ok=True)
    try:
        log = td / 'skill-latency.jsonl'
        lines = []
        for i in range(12):
            lines.append(json.dumps({
                'tool_name': 'cheap_ok', 'elapsed_ms': 100.0 + i, 'result_size': 10,
            }))
        for i in range(12):
            lines.append(json.dumps({
                'tool_name': 'expensive_ok', 'elapsed_ms': 900.0 + i, 'result_size': 10,
            }))
        for i in range(12):
            lines.append(json.dumps({
                'tool_name': 'cheap_bad', 'elapsed_ms': 50.0, 'result_size': 0 if i < 10 else 1,
            }))
        lines.append(json.dumps({'tool_name': 'audit_latency', 'elapsed_ms': 1, 'result_size': 2}))
        log.write_text('\n'.join(lines) + '\n', encoding='utf-8')
        out = td / ('provider-routing-state_test_' + uuid.uuid4().hex + '.json')
        r = run(latency_path=log, out_path=out, threshold=0.70)
        assert r['status'] == 'ok', r
        assert r['selected'] == 'cheap_ok', r['selected']
        assert 'cheap_bad' in r['skipped_low_quality']
        loaded = json.loads(out.read_text(encoding='utf-8'))
        assert loaded['selected'] == 'cheap_ok'
        empty = run(latency_path=td / 'missing.jsonl', out_path=td / 'empty.json')
        assert empty['status'] == 'insufficient_data'
        print(json.dumps({
            'status': 'ok',
            'self_test': True,
            'selected': r['selected'],
            'n_providers': r['n_providers'],
        }))
        return 0
    finally:
        for q in sorted(td.rglob('*'), reverse=True):
            try:
                q.unlink() if q.is_file() else q.rmdir()
            except OSError:
                pass
        try:
            td.rmdir()
        except OSError:
            pass


def main() -> int:
    ap = argparse.ArgumentParser(description='Cost-quality provider routing')
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--run', action='store_true', help='cron default; same as no flags')
    ap.add_argument('--threshold', type=float, default=QUALITY_THRESHOLD)
    args = ap.parse_args()
    if args.self_test:
        try:
            return _self_test()
        except Exception as exc:
            print(json.dumps({'status': 'error', 'self_test': True, 'reason': str(exc)}))
            return 1
    try:
        r = run(threshold=args.threshold)
        slim = {k: r[k] for k in r if k != 'providers'}
        print(json.dumps(slim, default=str))
        return 0
    except Exception as exc:
        print(json.dumps({'status': 'error', 'reason': str(exc), 'ts': _now()}))
        return 0


if __name__ == '__main__':
    sys.exit(main())
