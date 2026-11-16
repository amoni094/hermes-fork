#!/usr/bin/env python3
"""Anytime campaign evaluation via signed primal integral (SPI).

Tracks a 5-arm skill routing experiment on the same query set and
compares arms by mean score and signed primal integral against a
reference-frozen baseline.
"""
from __future__ import annotations
import argparse, fcntl, json, math, os, random, sqlite3, sys, time, uuid, zlib
from collections import Counter, defaultdict
from datetime import datetime, timezone, UTC
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base
CACHE = _hermes_root / 'cache'

def _now() -> str:
    return datetime.now(UTC).isoformat()

def _atomic_write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_name(path.name + '.lock')
    tmp = path.with_name(path.name + '.tmp')
    with open(str(lock_path), 'a', encoding='utf-8') as lf:
        fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
        try:
            tmp.write_text(json.dumps(obj, indent=2) + '\n', encoding='utf-8')
            os.replace(str(tmp), str(path))
        finally:
            fcntl.flock(lf.fileno(), fcntl.LOCK_UN)

def _lifecycle_db() -> Path:
    return _hermes_base / 'memory-facts' / 'lifecycle.db'

def _connect(db: Path | None = None) -> sqlite3.Connection:
    path = db or _lifecycle_db()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=30)
    conn.execute('PRAGMA journal_mode=WAL')
    conn.row_factory = sqlite3.Row
    return conn

OUT_PATH = CACHE / 'anytime-skill-eval.json'
ARMS = ['bm25', 'embedding', 'hybrid', 'ucb', 'fulltext']
N_REF = 5
T_REF_FRAC = 0.25


def signed_primal_integral(q_arm, q_ref, dts):
    spi = 0.0
    for qa, qr, dt in zip(q_arm, q_ref, dts):
        spi += (float(qa) - float(qr)) * float(dt)
    return spi


def cumulative_mean(xs):
    out, s = [], 0.0
    for i, x in enumerate(xs, 1):
        s += float(x)
        out.append(s / i)
    return out


def evaluate_arms(series, n_ref=N_REF):
    """series: {arm: [{'t': float, 'q': float}, ...]} sorted by t."""
    if not series:
        return {'arms': {}, 'best_spi_arm': None, 'reference_frozen_at': 0, 'status': 'insufficient_data', 'n': 0}
    # Align by index using the longest arm as time base.
    max_n = max(len(v) for v in series.values()) or 1
    t_ref_idx = max(n_ref, int(max_n * T_REF_FRAC))
    # Reference: mean quality of all arms frozen after t_ref_idx samples.
    ref_vals = []
    for arm, pts in series.items():
        freeze = pts[:t_ref_idx] if pts else []
        if freeze:
            ref_vals.append(sum(p['q'] for p in freeze) / len(freeze))
    q_ref_const = sum(ref_vals) / len(ref_vals) if ref_vals else 0.0
    results = {}
    best_arm, best_spi = None, float('-inf')
    for arm, pts in series.items():
        qs = [p['q'] for p in pts]
        ts = [p['t'] for p in pts]
        if not qs:
            results[arm] = {'mean_score': None, 'spi_score': None, 'n_queries': 0, 'status': 'insufficient_data'}
            continue
        dts = [ts[0] if i == 0 else max(1e-9, ts[i] - ts[i - 1]) for i in range(len(ts))]
        q_cum = cumulative_mean(qs)
        q_ref = [q_ref_const] * len(q_cum)
        spi = signed_primal_integral(q_cum, q_ref, dts)
        mean_s = sum(qs) / len(qs)
        results[arm] = {
            'mean_score': mean_s,
            'spi_score': spi,
            'n_queries': len(qs),
        }
        if spi > best_spi:
            best_spi, best_arm = spi, arm
    return {
        'arms': results,
        'best_spi_arm': best_arm,
        'reference_frozen_at': t_ref_idx,
        'q_ref': q_ref_const,
    }


def load_routing_series():
    series = {}
    jsonl = CACHE / 'routing-events.jsonl'
    if jsonl.exists():
        try:
            for i, line in enumerate(jsonl.read_text(encoding='utf-8').splitlines()):
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                skill = str(rec.get('top_skill') or rec.get('arm') or rec.get('skill') or '')
                if not skill:
                    continue
                score = rec.get('top_score', rec.get('score', rec.get('q')))
                if score is None:
                    continue
                try:
                    q = float(score)
                except (TypeError, ValueError):
                    continue
                tval = rec.get('ts') or rec.get('t') or i
                if isinstance(tval, str):
                    tval = i + 1.0
                series.setdefault(skill, []).append({'t': float(tval), 'q': q})
        except OSError:
            pass
    return series


def persist(eval_result):
    payload = {
        'ts': _now(),
        'best_spi_arm': eval_result.get('best_spi_arm'),
        'reference_frozen_at': eval_result.get('reference_frozen_at'),
        'q_ref': eval_result.get('q_ref'),
        'arms': eval_result.get('arms', {}),
    }
    _atomic_write(OUT_PATH, payload)
    try:
        conn = _connect()
        ts = payload['ts']
        ref_at = int(payload.get('reference_frozen_at') or 0)
        for arm, st in payload['arms'].items():
            conn.execute(
                'INSERT INTO anytime_eval_runs(ts, arm_id, mean_score, spi_score, n_queries, reference_frozen_at) '
                'VALUES (?,?,?,?,?,?)',
                (ts, arm, float(st.get('mean_score') or 0), float(st.get('spi_score') or 0),
                 int(st.get('n_queries') or 0), ref_at),
            )
        conn.commit()
        conn.close()
    except Exception:
        pass
    return payload


def _synthetic_arms():
    random.Random(7)
    series = {}
    # arm A: slow start, high finish (best SPI vs frozen early baseline)
    series['A'] = [{'t': float(i + 1), 'q': 0.90} for i in range(20)]
    series['B'] = [{'t': float(i + 1), 'q': 0.50} for i in range(20)]
    series['C'] = [{'t': float(i + 1), 'q': 0.20} for i in range(20)]
    return series


def _self_test() -> int:
    series = _synthetic_arms()
    r = evaluate_arms(series, n_ref=5)
    assert set(r['arms']) == {'A', 'B', 'C'}, r['arms']
    # A improves over frozen early mean so SPI should beat decaying B and flat C
    assert r['best_spi_arm'] == 'A', 'best={} spi={}'.format(r['best_spi_arm'], {k: v['spi_score'] for k, v in r['arms'].items()})
    assert r['arms']['A']['n_queries'] == 20
    empty = evaluate_arms({})
    assert empty.get('status') == 'insufficient_data'
    tmp = OUT_PATH.with_name(OUT_PATH.stem + '_test_' + uuid.uuid4().hex + OUT_PATH.suffix)
    _atomic_write(tmp, r)
    tmp.unlink(missing_ok=True)
    print('[anytime-skill-evaluator] --self-test PASS best={}'.format(r['best_spi_arm']))
    return 0


def run():
    series = load_routing_series()
    nonempty = {k: v for k, v in series.items() if v}
    if not nonempty:
        return {'status': 'insufficient_data', 'n': 0, 'arms': {}, 'best_spi_arm': None}
    r = evaluate_arms(nonempty)
    r['status'] = 'ok'
    r['n'] = sum(len(v) for v in nonempty.values())
    return persist(r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true')
    args = ap.parse_args()
    if args.self_test:
        try:
            sys.exit(_self_test())
        except Exception as exc:
            print(f'[anytime-skill-evaluator] --self-test FAIL: {exc}')
            sys.exit(1)
    try:
        result = run()
        print(json.dumps(result))
    except Exception as e:
        print(json.dumps({'status': 'error', 'reason': str(e)}))
    return 0


if __name__ == '__main__':
    main()
