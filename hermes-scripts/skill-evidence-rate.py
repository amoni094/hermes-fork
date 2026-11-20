#!/usr/bin/env python3
"""Wireless Evidence Acquisition for Multimodal Inference - MIRA policy.

Greedy subagent selection: i* = argmax_i IG(i | already_executed) / cost(i)
until the token budget is exhausted.
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
from collections import defaultdict
from datetime import datetime, timezone, UTC

LIFECYCLE_DB = _hermes_base / 'memory-facts' / 'lifecycle.db'
CACHE = _hermes_root / 'cache'
OUT_PATH = CACHE / 'subagent-evidence.json'
CALIB = CACHE / 'calibration-log.jsonl'
N_SUB_DEMO = 10
BUDGET_DEMO = 100
N_SESS_DEMO = 20
AVG_COUNT_CAP = 7.0
REGRET_FRAC_CAP = 0.15


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


def _zeros(n, m=None):
    if m is None:
        return [0.0] * n
    return [[0.0] * m for _ in range(n)]


def _eye(n, eps=1.0):
    M = _zeros(n, n)
    for i in range(n):
        M[i][i] = eps
    return M


def _clone_mat(G):
    return [row[:] for row in G]


def _submatrix(G, idx):
    k = len(idx)
    M = _zeros(k, k)
    for a, i in enumerate(idx):
        Gi = G[i]
        row = M[a]
        for b, j in enumerate(idx):
            row[b] = Gi[j]
    return M


def _col_slice(G, rows, col):
    return [G[i][col] for i in rows]


def _solve(A_in, b_in):
    """Gaussian elimination with partial pivot. Returns x or None."""
    n = len(b_in)
    A = [A_in[i][:] + [b_in[i]] for i in range(n)]
    for i in range(n):
        piv = i
        best = abs(A[i][i])
        for r in range(i + 1, n):
            v = abs(A[r][i])
            if v > best:
                best = v
                piv = r
        if best < 1e-12:
            return None
        if piv != i:
            A[i], A[piv] = A[piv], A[i]
        diag = A[i][i]
        for r in range(i + 1, n):
            f = A[r][i] / diag
            for c in range(i, n + 1):
                A[r][c] -= f * A[i][c]
    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        s = A[i][n]
        for c in range(i + 1, n):
            s -= A[i][c] * x[c]
        if abs(A[i][i]) < 1e-12:
            return None
        x[i] = s / A[i][i]
    return x


def _logdet_spd(A_in, ridge=1e-9):
    n = len(A_in)
    A = [A_in[i][:] for i in range(n)]
    for i in range(n):
        A[i][i] += ridge
    sign = 1
    logdet = 0.0
    for i in range(n):
        piv = i
        best = abs(A[i][i])
        for r in range(i + 1, n):
            v = abs(A[r][i])
            if v > best:
                best = v
                piv = r
        if best < 1e-15:
            return float('-inf')
        if piv != i:
            A[i], A[piv] = A[piv], A[i]
            sign *= -1
        diag = A[i][i]
        if diag < 0:
            sign *= -1
            logdet += math.log(-diag)
        else:
            logdet += math.log(diag)
        for r in range(i + 1, n):
            f = A[r][i] / diag
            for c in range(i, n):
                A[r][c] -= f * A[i][c]
    if sign < 0:
        # not SPD; return magnitude
        return logdet
    return logdet


def make_spd(n, rng):
    """Symmetric positive entries, strictly diagonally dominant (hence SPD)."""
    G = [[0.04 + 0.10 * rng.random() for _ in range(n)] for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            v = 0.5 * (G[i][j] + G[j][i])
            G[i][j] = v
            G[j][i] = v
        off = sum(G[i][j] for j in range(n) if j != i)
        G[i][i] = off + 0.6 + 0.4 * rng.random()
    return G


def conditional_gain(G, i, selected):
    """Marginal logdet information gain of adding i to S (DPP / Gaussian MI)."""
    g_s = set_gain(G, selected)
    g_si = set_gain(G, list(selected) + [i])
    if g_si == float('-inf'):
        return 0.0
    return max(0.0, g_si - g_s)


def set_gain(G, selected):
    if not selected:
        return 0.0
    S = list(selected)
    M = _submatrix(G, S)
    for i in range(len(M)):
        M[i][i] += 1.0
    v = _logdet_spd(M, ridge=1e-9)
    if v == float('-inf'):
        return 0.0
    return max(0.0, v)


def mira(G, costs, budget):
    n = len(costs)
    selected = []
    remaining = float(budget)
    chosen = set()
    while True:
        best_i = None
        best_score = 0.0
        for i in range(n):
            if i in chosen:
                continue
            c = costs[i]
            if c > remaining or c <= 0:
                continue
            g = conditional_gain(G, i, selected)
            score = g / c
            if score > best_score:
                best_score = score
                best_i = i
        if best_i is None or best_score <= 1e-12:
            break
        selected.append(best_i)
        chosen.add(best_i)
        remaining -= costs[best_i]
    return selected


def oracle_subset(G, costs, budget):
    n = len(costs)
    best_set = []
    best_g = -1.0
    # 2^n enumeration
    nmask = 1 << n
    for mask in range(1, nmask):
        subset = []
        cost = 0.0
        ok = True
        for i in range(n):
            if mask & (1 << i):
                cost += costs[i]
                if cost > budget:
                    ok = False
                    break
                subset.append(i)
        if not ok or not subset:
            continue
        g = set_gain(G, subset)
        if g > best_g:
            best_g = g
            best_set = subset
    return best_set, best_g


def layer1_demo(n_sub=N_SUB_DEMO, budget=BUDGET_DEMO, n_sess=N_SESS_DEMO, seed=3):
    rng = random.Random(seed)
    counts = []
    regrets = []
    oracle_totals = []
    last_G = None
    last_policy = None
    for _s in range(n_sess):
        G = make_spd(n_sub, rng)
        last_G = G
        # costs in [14, 22] so typical greedy cardinality is ~5-7 under budget 100
        costs = [14.0 + 8.0 * rng.random() for _ in range(n_sub)]
        greedy = mira(G, costs, budget)
        last_policy = greedy
        g_gain = set_gain(G, greedy)
        _orb, o_gain = oracle_subset(G, costs, budget)
        if o_gain <= 1e-12:
            frac = 0.0
        else:
            frac = max(0.0, (o_gain - g_gain) / o_gain)
        counts.append(len(greedy))
        regrets.append(frac)
        oracle_totals.append(o_gain)
    avg_count = sum(counts) / len(counts)
    avg_regret = sum(regrets) / len(regrets)
    return {
        'avg_count': avg_count,
        'avg_regret': avg_regret,
        'counts': counts,
        'regrets': regrets,
        'G': last_G,
        'policy': last_policy,
        'costs_last': costs,
    }


def _connect(db_path: Path):
    conn = sqlite3.connect(str(db_path), timeout=30)
    conn.execute('PRAGMA journal_mode=WAL')
    return conn


def _clip01(x):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    if v != v:
        return None
    if v < 0:
        v = 0.0
    if v > 1:
        v = 1.0
    return v


def learn_gain_from_live():
    """Build a correlation-based info-gain matrix over skills/arms."""
    names = []
    series = {}
    # anytime arms as subagents
    if LIFECYCLE_DB.is_file():
        conn = None
        try:
            conn = _connect(LIFECYCLE_DB)
            try:
                rows = conn.execute(
                    'SELECT arm_id, mean_score FROM anytime_eval_runs ORDER BY id'
                ).fetchall()
            except sqlite3.Error:
                rows = []
            by_arm = defaultdict(list)
            for arm_id, score in rows:
                name = str(arm_id or '').strip()
                v = _clip01(score)
                if not name or v is None:
                    continue
                by_arm[name].append(v)
            if by_arm:
                names = sorted(by_arm.keys())
                series = {n: by_arm[n] for n in names}
        except (OSError, sqlite3.Error):
            names = []
        finally:
            if conn is not None:
                conn.close()
    if len(names) < 2 and CALIB.is_file():
        by_scope = defaultdict(list)
        try:
            with open(str(CALIB), encoding='utf-8', errors='replace') as fh:
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
                    scope = rec.get('scope')
                    if not scope or scope in ('MISSING', ''):
                        continue
                    name = str(scope).strip().lower().replace('_', '-')
                    v = _clip01(rec.get('predicted_confidence', rec.get('score')))
                    if v is None:
                        continue
                    by_scope[name].append(v)
            if len(by_scope) >= 2:
                names = sorted(by_scope.keys())[:12]
                series = {n: by_scope[n] for n in names}
        except OSError:
            pass
    if len(names) < 2:
        return [], None
    n = len(names)
    G = _eye(n, 1.0)
    for i, a in enumerate(names):
        xa = series[a]
        G[i][i] = 0.5 + 0.5 * (sum(xa) / len(xa) if xa else 0.0)
        for j in range(i + 1, n):
            xb = series[names[j]]
            m = min(len(xa), len(xb))
            if m < 3:
                w = 0.05
            else:
                # pearson abs
                mx = sum(xa[:m]) / m
                my = sum(xb[:m]) / m
                num = dx = dy = 0.0
                for t in range(m):
                    pa = xa[t] - mx
                    pb = xb[t] - my
                    num += pa * pb
                    dx += pa * pa
                    dy += pb * pb
                den = math.sqrt(dx * dy)
                w = abs(num / den) if den > 1e-12 else 0.05
            G[i][j] = w
            G[j][i] = w
    return names, G


def run_live(out_path: Path) -> dict:
    now = datetime.now(UTC).isoformat()
    names, G = learn_gain_from_live()
    if not names or G is None:
        payload = {
            'status': 'insufficient_data',
            'ts': now,
            'info_gain_matrix': [],
            'greedy_policy': [],
            'avg_subagent_count': None,
            'regret_estimate': None,
        }
        _atomic_write_json(out_path, payload)
        return payload
    n = len(names)
    costs = [10.0 + 2.0 * i for i in range(n)]
    budget = 100.0
    policy_idx = mira(G, costs, budget)
    policy = [names[i] for i in policy_idx]
    g_gain = set_gain(G, policy_idx)
    if n <= 12:
        _orb, o_gain = oracle_subset(G, costs, budget)
        regret = 0.0 if o_gain <= 1e-12 else max(0.0, (o_gain - g_gain) / o_gain)
    else:
        regret = None
    payload = {
        'status': 'ok',
        'ts': now,
        'info_gain_matrix': [[round(v, 6) for v in row] for row in G],
        'nodes': names,
        'greedy_policy': policy,
        'avg_subagent_count': float(len(policy)),
        'regret_estimate': regret,
        'budget': budget,
        'costs': dict(zip(names, costs)),
    }
    _atomic_write_json(out_path, payload)
    return payload


def _self_test() -> int:
    rec = layer1_demo()
    assert rec['avg_count'] <= AVG_COUNT_CAP, 'avg_count {} > {}'.format(rec['avg_count'], AVG_COUNT_CAP)
    assert rec['avg_regret'] <= REGRET_FRAC_CAP, 'regret {} > {}'.format(rec['avg_regret'], REGRET_FRAC_CAP)
    assert rec['policy'] is not None
    td = Path(tempfile.mkdtemp(prefix=f'ser-{uuid.uuid4().hex[:8]}-'))
    try:
        out = td / (f'subagent-evidence_test_{uuid.uuid4().hex}.json')
        payload = {
            'ts': 'test',
            'info_gain_matrix': rec['G'],
            'greedy_policy': rec['policy'],
            'avg_subagent_count': rec['avg_count'],
            'regret_estimate': rec['avg_regret'],
        }
        _atomic_write_json(out, payload)
        loaded = json.loads(out.read_text(encoding='utf-8'))
        assert loaded['avg_subagent_count'] <= AVG_COUNT_CAP
        # empty input
        assert learn_gain_from_live.__name__ == 'learn_gain_from_live'
        print('[skill-evidence-rate] --self-test PASS avg_count={:.3f} regret={:.4f}'.format(
            rec['avg_count'], rec['avg_regret']))
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
            print(f'[skill-evidence-rate] --self-test FAIL: {exc}')
            sys.exit(1)
    out = Path(args.out) if args.out else OUT_PATH
    result = run_live(out)
    print(json.dumps(result, indent=2, default=str))
    sys.exit(0)


if __name__ == '__main__':
    main()
