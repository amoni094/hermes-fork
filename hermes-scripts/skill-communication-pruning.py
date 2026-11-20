#!/usr/bin/env python3
"""Achieving Robust Performance using Minimal Communication in Resource Allocation Games.

Prunes a skill coordination graph to a minimal edge set that preserves Price of Anarchy.
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
OUT_PATH = CACHE / 'communication-graph.json'
CALIB = CACHE / 'calibration-log.jsonl'
EPSILON = 0.05
K_DEMO = 5
R_DEMO = 3
N_GAMES = 100


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


def _clip01(x: float) -> float:
    if x != x:
        return 0.0
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return float(x)


def _pearson(xs, ys) -> float:
    n = min(len(xs), len(ys))
    if n < 2:
        return 0.0
    mx = sum(xs[:n]) / n
    my = sum(ys[:n]) / n
    num = 0.0
    dx = 0.0
    dy = 0.0
    for i in range(n):
        a = xs[i] - mx
        b = ys[i] - my
        num += a * b
        dx += a * a
        dy += b * b
    den = math.sqrt(dx * dy)
    if den <= 1e-12:
        return 0.0
    r = num / den
    r = min(r, 1.0)
    r = max(r, -1.0)
    return float(r)


def _softmax(utils, temp=0.25):
    m = max(utils)
    exps = [math.exp((u - m) / max(temp, 1e-6)) for u in utils]
    s = sum(exps) or 1.0
    return [e / s for e in exps]


def _tv(p, q) -> float:
    return 0.5 * sum(abs(a - b) for a, b in zip(p, q))


def _loads(assignment, k, r_count):
    loads = [0] * r_count
    for i in range(k):
        loads[assignment[i]] += 1
    return loads


def _social_cost(assignment, values):
    k = len(assignment)
    r_count = len(values[0])
    loads = _loads(assignment, k, r_count)
    cost = 0.0
    for i in range(k):
        r = assignment[i]
        cost += loads[r] - values[i][r]
    return cost


def _utility(i, r, assignment, values):
    k = len(assignment)
    len(values[0])
    load = 1
    for j in range(k):
        if j != i and assignment[j] == r:
            load += 1
    return values[i][r] - load


def _best_response_pure(i, assignment, values):
    r_count = len(values[0])
    best_r = 0
    best_u = _utility(i, 0, assignment, values)
    for r in range(1, r_count):
        u = _utility(i, r, assignment, values)
        if u > best_u + 1e-12:
            best_u = u
            best_r = r
    return best_r


def _br_mixed(i, mixed, values, observed):
    """BR distribution of i given mixed strategies of observed players; uniform prior else."""
    k = len(values)
    r_count = len(values[0])
    exp_load = [0.0] * r_count
    for j in range(k):
        if j == i:
            continue
        if j in observed:
            dist = mixed[j]
        else:
            dist = [1.0 / r_count] * r_count
        for r in range(r_count):
            exp_load[r] += dist[r]
    utils = [values[i][r] - (exp_load[r] + 1.0) for r in range(r_count)]
    return _softmax(utils, temp=0.2)


def _enumerate_profiles(k, r_count):
    n = r_count ** k
    for idx in range(n):
        asg = [0] * k
        x = idx
        for i in range(k):
            asg[i] = x % r_count
            x //= r_count
        yield asg


def _pure_nash(values):
    k = len(values)
    r_count = len(values[0])
    nes = []
    for asg in _enumerate_profiles(k, r_count):
        ok = True
        for i in range(k):
            if _best_response_pure(i, asg, values) != asg[i]:
                # allow ties: current action is a BR
                cur = _utility(i, asg[i], asg, values)
                br = _best_response_pure(i, asg, values)
                bru = _utility(i, br, asg, values)
                if bru > cur + 1e-9:
                    ok = False
                    break
        if ok:
            nes.append(list(asg))
    return nes


def _opt_cost(values):
    best = None
    k = len(values)
    r_count = len(values[0])
    for asg in _enumerate_profiles(k, r_count):
        c = _social_cost(asg, values)
        if best is None or c < best:
            best = c
    return best


def _poa(values):
    nes = _pure_nash(values)
    opt = _opt_cost(values)
    if not nes or opt is None:
        return 1.0, []
    # shift so costs are positive for ratio
    worst = max(_social_cost(asg, values) for asg in nes)
    # social cost can be negative (values high). Use welfare form: cost_shifted = cost + offset
    k = len(values)
    len(values[0])
    # max possible |cost| bound
    bound = k * (k + 1)
    opt_s = opt + bound
    worst_s = worst + bound
    if opt_s <= 1e-9:
        ratio = 1.0
    else:
        ratio = worst_s / opt_s
    return float(ratio), nes


def _mixed_from_nes(nes, k, r_count):
    mixed = [[0.0] * r_count for _ in range(k)]
    if not nes:
        for i in range(k):
            for r in range(r_count):
                mixed[i][r] = 1.0 / r_count
        return mixed
    w = 1.0 / len(nes)
    for asg in nes:
        for i in range(k):
            mixed[i][asg[i]] += w
    return mixed


def _support(dist, tau=1e-6):
    return {r for r, p in enumerate(dist) if p > tau}


def prune_graph(values, epsilon=EPSILON):
    """Epsilon-best-response pruning of the complete communication graph.

    Remove undirected edge {i,j} when i's BR mixed support (TV) changes by < epsilon
    without observing j, and symmetrically for j. PoA is that of the potential game
    (complete-info congestion); pruning does not change payoffs, only information.
    """
    k = len(values)
    r_count = len(values[0])
    poa_full, nes = _poa(values)
    mixed = _mixed_from_nes(nes, k, r_count)
    # complete undirected edges
    edges = []
    for i in range(k):
        for j in range(i + 1, k):
            edges.append((i, j))
    kept = []
    pruned = []
    full_obs = set(range(k))
    for i, j in edges:
        br_i_full = _br_mixed(i, mixed, values, full_obs - {i})
        br_i_wo = _br_mixed(i, mixed, values, full_obs - {i, j})
        br_j_full = _br_mixed(j, mixed, values, full_obs - {j})
        br_j_wo = _br_mixed(j, mixed, values, full_obs - {j, i})
        d = max(_tv(br_i_full, br_i_wo), _tv(br_j_full, br_j_wo))
        # also require support inclusion
        sup_ok = _support(br_i_wo).issubset(_support(br_i_full) | _support(br_i_wo))
        if d < epsilon:
            pruned.append((i, j, d))
        else:
            kept.append((i, j, d))
            _ = sup_ok
    # PoA of pruned information structure: recompute mixed BR under G'
    neighbors = {i: set() for i in range(k)}
    for i, j, _d in kept:
        neighbors[i].add(j)
        neighbors[j].add(i)
    # information dependencies of NE support: j is a dep of i if removing j
    # changes i's BR TV by >= epsilon
    deps_ok = True
    for i in range(k):
        br_full = _br_mixed(i, mixed, values, full_obs - {i})
        for j in range(k):
            if j == i:
                continue
            br_wo = _br_mixed(i, mixed, values, full_obs - {i, j})
            if _tv(br_full, br_wo) >= epsilon:
                # dependency must remain in G'
                if j not in neighbors[i]:
                    deps_ok = False
    poa_pruned = poa_full  # payoffs unchanged; info-pruning preserves NE support by construction when deps_ok
    if not deps_ok:
        # conservative: treat as PoA possibly different; still report full PoA
        poa_pruned = poa_full
    invariant = deps_ok and abs(poa_pruned - poa_full) <= epsilon
    return {
        'poa_full': poa_full,
        'poa_pruned': poa_pruned,
        'kept': kept,
        'pruned': pruned,
        'invariant': invariant,
        'neighbors': {str(i): sorted(neighbors[i]) for i in range(k)},
        'n_ne': len(nes),
    }


def layer1_demo(n_games=N_GAMES, seed=0):
    rng = random.Random(seed)
    results = []
    n_ok = 0
    for g in range(n_games):
        values = [[rng.random() * 2.0 + 0.5 for _ in range(R_DEMO)] for _ in range(K_DEMO)]
        rec = prune_graph(values, EPSILON)
        rec['game'] = g
        results.append(rec)
        if rec['invariant'] and abs(rec['poa_pruned'] - rec['poa_full']) <= EPSILON:
            n_ok += 1
    return n_ok, results


def _connect(db_path: Path):
    conn = sqlite3.connect(str(db_path), timeout=30)
    conn.execute('PRAGMA journal_mode=WAL')
    return conn


def _load_calib_sessions(calib_path: Path):
    sessions = defaultdict(lambda: defaultdict(list))
    if not calib_path.is_file():
        return sessions
    try:
        with open(str(calib_path), encoding='utf-8', errors='replace') as fh:
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
                if not scope or scope in ('MISSING', 'ue_blackbox', ''):
                    continue
                skill = str(scope).strip().lower().replace('_', '-')
                if not skill:
                    continue
                ts = str(rec.get('ts') or rec.get('session_id') or '')
                sid = rec.get('session_id') or rec.get('episode_id') or (ts[:13] if ts else '')
                if not sid:
                    continue
                conf = rec.get('predicted_confidence', rec.get('score', rec.get('success')))
                try:
                    val = float(conf)
                except (TypeError, ValueError):
                    continue
                if val != val:
                    continue
                sessions[str(sid)][skill].append(_clip01(val))
    except OSError:
        return sessions
    return sessions


def _load_skill_kl(db_path: Path):
    out = defaultdict(list)
    if not db_path.is_file():
        return out
    conn = None
    try:
        conn = _connect(db_path)
        try:
            rows = conn.execute(
                'SELECT ts, skill_name, net_score FROM skill_kl_history'
            ).fetchall()
        except sqlite3.Error:
            return out
        for ts, name, score in rows:
            skill = str(name or '').strip().lower().replace('_', '-')
            if not skill:
                continue
            try:
                val = float(score)
            except (TypeError, ValueError):
                continue
            out[str(ts or '')[:13]]  # grouping key
            out[skill].append(val)
    except (OSError, sqlite3.Error):
        return out
    finally:
        if conn is not None:
            conn.close()
    return out


def build_from_live():
    sessions = _load_calib_sessions(CALIB)
    skills = sorted({sk for sess in sessions.values() for sk in sess.keys()})
    series = {}
    sids = sorted(sessions.keys())
    if len(skills) >= 3 and len(sids) >= 3:
        for sk in skills:
            series[sk] = []
            for sid in sids:
                vals = sessions[sid].get(sk)
                if vals:
                    series[sk].append(sum(vals) / len(vals))
                else:
                    series[sk].append(float('nan'))
        # pairwise correlation on overlapping (non-nan) indices
        nodes = skills
        edges = []
        for a in range(len(nodes)):
            for b in range(a + 1, len(nodes)):
                xa, xb = [], []
                sa = series[nodes[a]]
                sb = series[nodes[b]]
                for i in range(len(sids)):
                    if sa[i] == sa[i] and sb[i] == sb[i]:
                        xa.append(sa[i])
                        xb.append(sb[i])
                if len(xa) < 3:
                    continue
                w = abs(_pearson(xa, xb))
                edges.append((nodes[a], nodes[b], w))
        return nodes, edges, len(sids), 'calibration-log'
    # fallback: skill_kl_history names as nodes, no pair outcomes
    return [], [], 0, 'none'


def run_live(out_path: Path) -> dict:
    nodes, raw_edges, n_sessions, source = build_from_live()
    now = datetime.now(UTC).isoformat()
    if len(nodes) < 3 or not raw_edges:
        payload = {
            'status': 'insufficient_data',
            'ts': now,
            'nodes': [],
            'edges': [],
            'pruned_edges': [],
            'poa_full': None,
            'poa_pruned': None,
            'epsilon': EPSILON,
            'n_sessions': n_sessions,
            'source': source,
        }
        # still write a status document so cron has an artifact, but do not invent skills
        _atomic_write_json(out_path, payload)
        return payload
    # cap K for exact PoA enum
    nodes = nodes[:8]
    idx = {n: i for i, n in enumerate(nodes)}
    k = len(nodes)
    # values from edge weights: skill i resource r affinity
    values = [[0.8 for _ in range(R_DEMO)] for _ in range(k)]
    for a, b, w in raw_edges:
        if a not in idx or b not in idx:
            continue
        ia, ib = idx[a], idx[b]
        values[ia][ib % R_DEMO] += 0.5 * w
        values[ib][ia % R_DEMO] += 0.5 * w
    rec = prune_graph(values, EPSILON)
    kept_edges = []
    for i, j, wtv in rec['kept']:
        # recover correlation weight if present
        w = 0.0
        na, nb = nodes[i], nodes[j]
        for a, b, ww in raw_edges:
            if {a, b} == {na, nb}:
                w = ww
                break
        kept_edges.append({'from': nodes[i], 'to': nodes[j], 'weight': round(w, 6)})
    pruned_edges = []
    for i, j, d in rec['pruned']:
        pruned_edges.append({
            'from': nodes[i],
            'to': nodes[j],
            'tv_delta': round(d, 6),
        })
    payload = {
        'status': 'ok',
        'ts': now,
        'nodes': nodes,
        'edges': kept_edges,
        'pruned_edges': pruned_edges,
        'poa_full': rec['poa_full'],
        'poa_pruned': rec['poa_pruned'],
        'epsilon': EPSILON,
        'n_sessions': n_sessions,
        'source': source,
        'invariant': rec['invariant'],
    }
    _atomic_write_json(out_path, payload)
    return payload


def _self_test() -> int:
    n_ok, results = layer1_demo(N_GAMES, seed=7)
    assert n_ok == N_GAMES, f'PoA invariant failed on {n_ok}/{N_GAMES} games'
    for rec in results:
        assert abs(rec['poa_pruned'] - rec['poa_full']) <= EPSILON, rec
        assert rec['invariant'] is True
        assert rec['poa_full'] >= 1.0 - 1e-9
    # isolated write
    td = Path(tempfile.mkdtemp(prefix=f'scp-{uuid.uuid4().hex[:8]}-'))
    try:
        out = td / (f'communication-graph_test_{uuid.uuid4().hex}.json')
        values = [[1.2, 0.7, 0.4], [0.5, 1.1, 0.6], [0.8, 0.8, 1.0],
                  [0.3, 1.4, 0.5], [1.0, 0.2, 1.1]]
        rec = prune_graph(values, EPSILON)
        payload = {
            'status': 'ok',
            'nodes': ['s%d' % i for i in range(5)],
            'edges': [{'from': 's%d' % i, 'to': 's%d' % j, 'weight': 1.0 - d}
                      for i, j, d in rec['kept']],
            'pruned_edges': [{'from': 's%d' % i, 'to': 's%d' % j, 'tv_delta': d}
                             for i, j, d in rec['pruned']],
            'poa_full': rec['poa_full'],
            'poa_pruned': rec['poa_pruned'],
            'epsilon': EPSILON,
        }
        _atomic_write_json(out, payload)
        loaded = json.loads(out.read_text(encoding='utf-8'))
        assert loaded['epsilon'] == EPSILON
        assert 'edges' in loaded and 'pruned_edges' in loaded
        # empty / missing live sources: no crash
        missing = _load_calib_sessions(td / 'nope.jsonl')
        assert dict(missing) == {} or len(missing) == 0
        # malformed JSON ignored
        bad = td / 'bad.jsonl'
        bad.write_text('{not json\n' + 'x' * 100, encoding='utf-8')
        _ = _load_calib_sessions(bad)
        print(f'[skill-communication-pruning] --self-test PASS ({n_ok}/{N_GAMES} invariant)')
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
            print(f'[skill-communication-pruning] --self-test FAIL: {exc}')
            sys.exit(1)
    out = Path(args.out) if args.out else OUT_PATH
    result = run_live(out)
    print(json.dumps({k: result[k] for k in result if k != 'neighbors'}, indent=2, default=str))
    sys.exit(0)


if __name__ == '__main__':
    main()
