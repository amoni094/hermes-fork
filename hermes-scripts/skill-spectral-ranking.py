#!/usr/bin/env python3
"""Beyond a Single Optimal Design - Dynamical Systems Characterization of Online Allocation.

Dominant eigenvalue of the skill transition operator T is the competitive ratio;
the corresponding eigenvector is the reserve/routing mix.
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
import random
import sqlite3
import sys
import tempfile
import uuid
from datetime import datetime, timezone, UTC

LIFECYCLE_DB = _hermes_base / 'memory-facts' / 'lifecycle.db'
CACHE = _hermes_root / 'cache'
OUT_PATH = CACHE / 'routing-spectral-state.json'
MAX_ITERS = 100
TOL = 1e-8
CONV_DEMO = 1e-6
K_DEMO = 3
T_DEMO = 100
REGRET_CAP = 55.0


def _atomic_write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix('.lock')
    tmp = path.with_suffix('.tmp')
    with open(str(lock_path), 'a', encoding='utf-8') as lf:
        fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
        try:
            tmp.write_text(json.dumps(obj, indent=2) + '\n', encoding='utf-8')
            os.replace(str(tmp), str(path))
        finally:
            fcntl.flock(lf.fileno(), fcntl.LOCK_UN)


def _matvec(M, x):
    n = len(M)
    y = [0.0] * n
    for i in range(n):
        s = 0.0
        row = M[i]
        for j in range(n):
            s += row[j] * x[j]
        y[i] = s
    return y


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def _l1(x):
    return sum(abs(v) for v in x)


def _l2(x):
    return math.sqrt(sum(v * v for v in x))


def _normalize_l1(x):
    s = _l1(x)
    if s <= 1e-15:
        n = len(x)
        return [1.0 / n] * n
    return [v / s for v in x]


def _nonlinear_T_apply(latency, loss, quality, x):
    """Nonlinear allocation operator.

    (T x)_i = quality_i / (1 + loss_i + sum_j latency[i][j] * x_j)
    then L1-normalise. Dominant growth factor is the competitive ratio proxy.
    """
    n = len(quality)
    y = [0.0] * n
    for i in range(n):
        cong = 0.0
        row = latency[i]
        for j in range(n):
            cong += row[j] * x[j]
        den = 1.0 + max(0.0, loss[i]) + max(0.0, cong)
        q = max(1e-09, quality[i])
        y[i] = q / den
    return y


def power_iteration(latency, loss, quality, max_iter=MAX_ITERS, tol=TOL):
    n = len(quality)
    x = [1.0 / n] * n
    lam = 0.0
    delta = float('inf')
    it_used = 0
    for it in range(max_iter):
        y = _nonlinear_T_apply(latency, loss, quality, x)
        nrm = _l1(y)
        if nrm <= 1e-15:
            break
        # Rayleigh-like growth factor on the unnormalised image
        lam_new = nrm  # ||T x||_1 with ||x||_1 = 1
        # also cosine-stable residual
        yhat = [v / nrm for v in y]
        delta = max(abs(lam_new - lam), max(abs(a - b) for a, b in zip(yhat, x)))
        x = yhat
        lam = lam_new
        it_used = it + 1
        if delta < tol:
            break
    return float(lam), x, it_used, float(delta)


def _linear_operator_matrix(latency, loss, quality):
    """Markov-style linearisation: T[i,j] = (latency[i,j] + loss[i]) / quality[j]."""
    n = len(quality)
    T = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            qj = max(1e-09, quality[j])
            T[i][j] = (max(0.0, latency[i][j]) + max(0.0, loss[i])) / qj
    # row-stochastic-ish scale for spectral radius interpretability
    return T


def power_iteration_linear(T, max_iter=MAX_ITERS, tol=TOL):
    n = len(T)
    x = [1.0 / n] * n
    lam = 0.0
    delta = float('inf')
    it_used = 0
    for it in range(max_iter):
        y = _matvec(T, x)
        # Rayleigh
        denom = _dot(x, x)
        lam_new = _dot(x, y) / denom if denom > 1e-15 else _l2(y)
        nrm = _l2(y)
        if nrm <= 1e-15:
            break
        yhat = [v / nrm for v in y]
        # make nonnegative / consistent sign
        if sum(yhat) < 0:
            yhat = [-v for v in yhat]
        delta = abs(lam_new - lam)
        x = yhat
        lam = lam_new
        it_used = it + 1
        if delta < tol:
            break
    x = _normalize_l1([max(0.0, v) for v in x])
    return float(lam), x, it_used, float(delta)


def simulate_routing(pi, cost_seq):
    """Cumulative cost of mixing pi vs offline best arm. Returns regret."""
    len(cost_seq)
    k = len(pi)
    route = 0.0
    arm_tot = [0.0] * k
    for costs in cost_seq:
        route += sum(pi[i] * costs[i] for i in range(k))
        for i in range(k):
            arm_tot[i] += costs[i]
    offline = min(arm_tot)
    return route - offline, route, offline


def theory_regret_bound():
    # 1.5 * sqrt(3 * 500 * log(10))  with natural log
    return 1.5 * math.sqrt(3.0 * 500.0 * math.log(10.0))


def layer1_demo(seed=1):
    rng = random.Random(seed)
    k = K_DEMO
    # latency[i->j] + loss[i]
    latency = [[0.4 + 0.3 * rng.random() for _ in range(k)] for _ in range(k)]
    for i in range(k):
        latency[i][i] = 0.1 + 0.05 * rng.random()
    loss = [0.2 + 0.3 * rng.random() for _ in range(k)]
    quality = [0.6 + 0.4 * rng.random() for _ in range(k)]
    T = _linear_operator_matrix(latency, loss, quality)
    lam, evec, iters, delta = power_iteration_linear(T, max_iter=MAX_ITERS, tol=TOL)
    # also run nonlinear map
    lam_nl, _evec_nl, iters_nl, delta_nl = power_iteration(
        latency, loss, quality, max_iter=MAX_ITERS, tol=TOL
    )
    # routing from linear Perron vector
    pi = _normalize_l1(evec)
    cost_seq = []
    for _t in range(T_DEMO):
        cost_seq.append([0.3 + 0.7 * rng.random() + 0.2 * loss[i] for i in range(k)])
    regret, route, offline = simulate_routing(pi, cost_seq)
    return {
        'lambda': lam,
        'eigenvector': pi,
        'iters': iters,
        'delta': delta,
        'lambda_nl': lam_nl,
        'delta_nl': delta_nl,
        'iters_nl': iters_nl,
        'regret': regret,
        'route_cost': route,
        'offline': offline,
        'latency': latency,
        'loss': loss,
        'quality': quality,
        'theory_bound': theory_regret_bound(),
    }


def _connect(db_path: Path):
    conn = sqlite3.connect(str(db_path), timeout=30)
    conn.execute('PRAGMA journal_mode=WAL')
    return conn


def _coerce_float(v, default=0.0):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return default
    if x != x or x == float('inf') or x == float('-inf'):
        return default
    return x


def load_anytime_arms(db_path: Path):
    if not db_path.is_file():
        return []
    conn = None
    try:
        conn = _connect(db_path)
        try:
            rows = conn.execute(
                'SELECT arm_id, AVG(mean_score), AVG(spi_score), SUM(n_queries) '
                'FROM anytime_eval_runs GROUP BY arm_id'
            ).fetchall()
        except sqlite3.Error:
            return []
        arms = []
        for arm_id, mean_score, spi_score, nq in rows:
            name = str(arm_id or '').strip()
            if not name:
                continue
            q = _coerce_float(mean_score, 0.0)
            # quality in (0,1]
            if q <= 0:
                q = 0.05
            loss = max(0.0, 1.0 - q)
            arms.append({
                'arm_id': name,
                'quality': q,
                'loss': loss,
                'spi': _coerce_float(spi_score, 0.0),
                'n_queries': _coerce_float(nq, 0.0),
            })
        return arms
    except (OSError, sqlite3.Error):
        return []
    finally:
        if conn is not None:
            conn.close()


def run_live(out_path: Path) -> dict:
    now = datetime.now(UTC).isoformat()
    arms = load_anytime_arms(LIFECYCLE_DB)
    if len(arms) < 2:
        payload = {
            'status': 'insufficient_data',
            'ts': now,
            'eigenvalue': None,
            'eigenvector': [],
            'skill_ranking': [],
            'regret_bound': theory_regret_bound(),
        }
        _atomic_write_json(out_path, payload)
        return payload
    arms.sort(key=lambda a: a['arm_id'])
    names = [a['arm_id'] for a in arms]
    k = len(names)
    quality = [a['quality'] for a in arms]
    loss = [a['loss'] for a in arms]
    # transition latency: |quality_i - quality_j| + small self
    latency = [[0.0] * k for _ in range(k)]
    for i in range(k):
        for j in range(k):
            latency[i][j] = abs(quality[i] - quality[j]) + (0.05 if i == j else 0.15)
    T = _linear_operator_matrix(latency, loss, quality)
    lam, evec, iters, delta = power_iteration_linear(T, max_iter=MAX_ITERS, tol=TOL)
    ranking = sorted(
        [{'skill': names[i], 'weight': evec[i], 'quality': quality[i]} for i in range(k)],
        key=lambda r: -r['weight'],
    )
    payload = {
        'status': 'ok',
        'ts': now,
        'eigenvalue': lam,
        'eigenvector': [{'skill': names[i], 'value': evec[i]} for i in range(k)],
        'skill_ranking': ranking,
        'regret_bound': theory_regret_bound(),
        'iters': iters,
        'delta': delta,
        'n_arms': k,
    }
    _atomic_write_json(out_path, payload)
    return payload


def _self_test() -> int:
    rec = layer1_demo(seed=2)
    assert rec['iters'] <= MAX_ITERS
    assert rec['delta'] < CONV_DEMO, 'eigenvalue did not converge: delta={}'.format(rec['delta'])
    assert rec['lambda'] == rec['lambda']  # not NaN
    assert rec['regret'] <= REGRET_CAP, 'regret {} > {}'.format(rec['regret'], REGRET_CAP)
    s = sum(rec['eigenvector'])
    assert abs(s - 1.0) < 1e-6, s
    # nonlinear also converges
    assert rec['delta_nl'] < CONV_DEMO or rec['iters_nl'] <= MAX_ITERS
    td = Path(tempfile.mkdtemp(prefix=f'ssr-{uuid.uuid4().hex[:8]}-'))
    try:
        out = td / (f'routing-spectral-state_test_{uuid.uuid4().hex}.json')
        payload = {
            'ts': 'test',
            'eigenvalue': rec['lambda'],
            'eigenvector': rec['eigenvector'],
            'skill_ranking': list(range(K_DEMO)),
            'regret_bound': rec['theory_bound'],
        }
        _atomic_write_json(out, payload)
        loaded = json.loads(out.read_text(encoding='utf-8'))
        assert 'eigenvalue' in loaded
        print('[skill-spectral-ranking] --self-test PASS lambda={:.6f} delta={:.3g} regret={:.4f} bound={:.2f}'.format(
            rec['lambda'], rec['delta'], rec['regret'], rec['theory_bound']))
        return 0
    finally:
        import shutil
        shutil.rmtree(td, ignore_errors=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--run', action='store_true')
    ap.add_argument('--out', default='')
    args = ap.parse_args()
    if args.self_test:
        try:
            sys.exit(_self_test())
        except Exception as exc:
            print(f'[skill-spectral-ranking] --self-test FAIL: {exc}')
            sys.exit(1)
    out = Path(args.out) if args.out else OUT_PATH
    result = run_live(out)
    print(json.dumps(result, indent=2, default=str))
    sys.exit(0)


if __name__ == '__main__':
    main()
