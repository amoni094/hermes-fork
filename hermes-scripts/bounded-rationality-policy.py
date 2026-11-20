#!/usr/bin/env python3
"""Policy Complexity, Reaction Time, and Bounded Rationality.

Models skill dispatch as a bounded-rationality knapsack: maximize quality
subject to a complexity budget. Stdlib only. Profile-aware.
"""
from __future__ import annotations

import os
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', 'fork')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base

import argparse
import fcntl
import json
import sqlite3
import sys
import tempfile
import uuid
from datetime import datetime, timezone, UTC

CACHE = _hermes_root / 'cache'
OUT_PATH = CACHE / 'bounded-rationality-state.json'
LIFECYCLE_DB = _hermes_base / 'memory-facts' / 'lifecycle.db'


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


def _connect(db_path: Path):
    conn = sqlite3.connect(str(db_path), timeout=30)
    conn.execute('PRAGMA journal_mode=WAL')
    return conn


def knapsack(items, budget: int):
    """0-1 knapsack. items: list of dicts with name, complexity (int>=0), quality (float).

    Returns (selected_items, total_quality, total_complexity).
    """
    n = len(items)
    B = max(0, int(budget))
    costs = []
    values = []
    for it in items:
        try:
            c = int(it['complexity'])
        except (TypeError, ValueError, KeyError):
            c = 1
        c = max(c, 0)
        try:
            q = float(it['quality'])
        except (TypeError, ValueError, KeyError):
            q = 0.0
        if q != q:
            q = 0.0
        costs.append(c)
        values.append(q)
    # DP: dp[b] = (quality, mask-not-used; reconstruct via choice)
    dp = [0.0] * (B + 1)
    take = [[False] * (B + 1) for _ in range(n)]
    for i in range(n):
        c = costs[i]
        q = values[i]
        for b in range(B, c - 1, -1):
            cand = dp[b - c] + q
            if cand > dp[b]:
                dp[b] = cand
                take[i][b] = True
    selected_idx = []
    b = B
    for i in range(n - 1, -1, -1):
        if b >= 0 and take[i][b]:
            selected_idx.append(i)
            b -= costs[i]
    selected_idx.reverse()
    selected = [items[i] for i in selected_idx]
    total_q = sum(values[i] for i in selected_idx)
    total_c = sum(costs[i] for i in selected_idx)
    return selected, float(total_q), int(total_c)


def frontier(items, max_b: int):
    pts = []
    prev_q = None
    upper = max(0, int(max_b))
    for b in range(upper + 1):
        _, q, c = knapsack(items, b)
        if prev_q is None or q != prev_q:
            pts.append({'complexity': int(c), 'quality': float(q), 'budget': int(b)})
            prev_q = q
    return pts


def load_items(db_path: Path) -> list:
    """Quality from skill_kl_history; complexity proxy from tracegrant_grants."""
    if not db_path.exists():
        return []
    conn = None
    try:
        conn = _connect(db_path)
        tabs = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        quality = {}
        if 'skill_kl_history' in tabs:
            rows = conn.execute(
                'SELECT skill_name, posterior_prob, net_score, ts FROM skill_kl_history ORDER BY ts'
            ).fetchall()
            for name, post, net, _ts in rows:
                if not name:
                    continue
                try:
                    q = float(post) if post is not None else float(net or 0.0)
                except (TypeError, ValueError):
                    continue
                if q != q:
                    continue
                q = max(q, 0.0)
                quality[str(name)] = q
        complexity = {}
        if 'tracegrant_grants' in tabs:
            grows = conn.execute(
                'SELECT caller, allowed_ns FROM tracegrant_grants'
            ).fetchall()
            counts = {}
            ns_len = {}
            for caller, allowed in grows:
                key = str(caller or 'unknown')
                counts[key] = counts.get(key, 0) + 1
                nlen = 1
                if allowed:
                    try:
                        parsed = json.loads(allowed) if isinstance(allowed, str) else allowed
                        if isinstance(parsed, list):
                            nlen = max(1, len(parsed))
                    except (json.JSONDecodeError, TypeError):
                        nlen = max(1, len(str(allowed)) // 8)
                ns_len[key] = ns_len.get(key, 0) + nlen
            for key, cnt in counts.items():
                avg_ns = ns_len[key] / float(cnt)
                complexity[key] = max(1, round(avg_ns + (cnt ** 0.5)))
        items = []
        if not quality:
            return []
        for i, name in enumerate(sorted(quality.keys())):
            q = quality[name]
            if name in complexity:
                c = complexity[name]
            else:
                c = max(1, min(8, (len(name) // 2) + 1 + (i % 3)))
            items.append({'name': name, 'complexity': int(c), 'quality': float(q)})
        return items
    except sqlite3.Error:
        return []
    finally:
        if conn is not None:
            conn.close()


def choose_budget(items) -> int:
    total = sum(int(it['complexity']) for it in items)
    min_c = min((max(0, int(it['complexity'])) for it in items), default=0)
    if total <= 0:
        return max(0, min_c)
    # Budget must admit at least the cheapest arm (Lattimore: forced exploration
    # when UCB/knapsack would otherwise select the empty set / max-regret policy).
    return max(min_c, max(1, total // 2))


def _force_explore(items):
    """Pick the cheapest positive-quality arm when knapsack is empty."""
    if not items:
        return [], 0.0, 0
    ranked = sorted(
        items,
        key=lambda it: (max(0, int(it['complexity'])), -float(it['quality'])),
    )
    pick = ranked[0]
    return [pick], float(pick['quality']), int(pick['complexity'])


def evaluate_policy(items, budget: int) -> dict:
    if not items:
        return {
            'status': 'insufficient_data',
            'n': 0,
            'budget_used': 0,
            'optimal_skills': [],
            'policy_regret': 0.0,
            'complexity_quality_frontier': [],
        }
    selected, pol_q, pol_c = knapsack(items, budget)
    exploration_forced = False
    if not selected:
        selected, pol_q, pol_c = _force_explore(items)
        exploration_forced = bool(selected)
    oracle_q = sum(float(it['quality']) for it in items)
    regret = float(oracle_q - pol_q)
    if regret < 0:
        regret = 0.0
    total_c = sum(int(it['complexity']) for it in items)
    front = frontier(items, total_c)
    return {
        'status': 'ok',
        'budget': int(budget),
        'budget_used': int(pol_c),
        'optimal_skills': [it['name'] for it in selected],
        'policy_quality': float(pol_q),
        'oracle_quality': float(oracle_q),
        'policy_regret': float(regret),
        'complexity_quality_frontier': front,
        'n_items': len(items),
        'feasible': bool(pol_c <= budget) or exploration_forced,
        'exploration_forced': exploration_forced,
    }


def run(db_path: Path, out_path: Path, budget=None) -> dict:
    items = load_items(db_path)
    if not items:
        return {'status': 'insufficient_data', 'n': 0}
    B = int(budget) if budget is not None else choose_budget(items)
    result = evaluate_policy(items, B)
    result['ts'] = _now()
    if result.get('status') == 'insufficient_data':
        return result
    payload = {
        'ts': result['ts'],
        'budget_used': result['budget_used'],
        'optimal_skills': result['optimal_skills'],
        'policy_regret': result['policy_regret'],
        'complexity_quality_frontier': result['complexity_quality_frontier'],
        'budget': result.get('budget'),
        'policy_quality': result.get('policy_quality'),
        'exploration_forced': bool(result.get('exploration_forced')),
        'n_items': result.get('n_items'),
        'oracle_quality': result.get('oracle_quality'),
    }
    _atomic_write(out_path, payload)
    result['written'] = str(out_path)
    return result


def _self_test() -> int:
    items = [
        {'name': '1', 'complexity': 1, 'quality': 0.9},
        {'name': '2', 'complexity': 2, 'quality': 0.8},
        {'name': '3', 'complexity': 3, 'quality': 0.7},
        {'name': '4', 'complexity': 4, 'quality': 0.6},
        {'name': '5', 'complexity': 5, 'quality': 0.5},
    ]
    selected, q, c = knapsack(items, 6)
    names = set(it['name'] for it in selected)
    # Spec mentioned 1+2 (q=1.7) or 1+3 (q=1.6); true optimum is 1+2+3 (c=6, q=2.4).
    assert c <= 6, (c, names, q)
    pair_12 = {'1', '2'}
    pair_13 = {'1', '3'}
    opt_123 = {'1', '2', '3'}
    assert names in (pair_12, pair_13, opt_123), names
    r = evaluate_policy(items, 6)
    assert r['policy_regret'] >= 0.0, r
    assert r['feasible'] is True
    assert r['budget_used'] <= 6
    empty_sel = evaluate_policy(
        [{'name': 'big', 'complexity': 9, 'quality': 0.8}],
        4,
    )
    assert empty_sel['exploration_forced'] is True, empty_sel
    assert empty_sel['optimal_skills'] == ['big'], empty_sel
    assert empty_sel['policy_quality'] > 0.0, empty_sel
    # pair 1+2 quality 1.7 must not beat the chosen policy
    assert r['policy_quality'] + 1e-9 >= 1.7, r
    td = Path(tempfile.mkdtemp(prefix='brp-'))
    try:
        db = td / 'lc.db'
        conn = sqlite3.connect(str(db), timeout=30)
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute(
            'CREATE TABLE skill_kl_history (id INTEGER PRIMARY KEY, ts TEXT, skill_name TEXT, '
            'posterior_prob REAL, prior_prob REAL, kl_contrib REAL, net_score REAL)'
        )
        conn.execute(
            'CREATE TABLE tracegrant_grants (grant_id TEXT, session_id TEXT, caller TEXT, '
            'source_type TEXT, allowed_ns TEXT, granted_at TEXT, revoked INTEGER, '
            'revoked_at TEXT, taint_path TEXT, decision_hash TEXT)'
        )
        conn.execute(
            'INSERT INTO skill_kl_history (ts, skill_name, posterior_prob, prior_prob, kl_contrib, net_score) '
            'VALUES (?,?,?,?,?,?)',
            (_now(), 'alpha', 0.9, 0.5, 0.1, 0.8),
        )
        conn.execute(
            'INSERT INTO tracegrant_grants (grant_id, session_id, caller, source_type, allowed_ns, granted_at, revoked, revoked_at, taint_path, decision_hash) '
            'VALUES (?,?,?,?,?,?,?,?,?,?)',
            ('g1', 's', 'alpha', 'internal', '["event","profile"]', _now(), 0, None, '', ''),
        )
        conn.commit()
        conn.close()
        out = td / ('bounded-rationality-state_test_' + uuid.uuid4().hex + '.json')
        live = run(db, out, budget=6)
        assert live.get('status') == 'ok', live
        assert live['budget_used'] <= 6
        assert live['policy_regret'] >= 0.0
        payload = json.loads(out.read_text(encoding='utf-8'))
        assert 'optimal_skills' in payload
        missing = run(td / 'nope.db', td / 'nope.json')
        assert missing.get('status') == 'insufficient_data', missing
    finally:
        import shutil
        shutil.rmtree(td, ignore_errors=True)
    print('[bounded-rationality-policy] --self-test PASS')
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description='Policy Complexity, Reaction Time, and Bounded Rationality')
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--run', action='store_true')
    ap.add_argument('--budget', type=int, default=None)
    ap.add_argument('--db', default=str(LIFECYCLE_DB))
    ap.add_argument('--out', default=str(OUT_PATH))
    args = ap.parse_args()
    if args.self_test:
        try:
            sys.exit(_self_test())
        except Exception as exc:
            print(f'[bounded-rationality-policy] --self-test FAIL: {exc}')
            sys.exit(1)
    try:
        result = run(Path(args.db), Path(args.out), budget=args.budget)
        print(json.dumps(result, indent=2, default=str))
        sys.exit(0)
    except Exception as exc:
        print(json.dumps({'status': 'error', 'reason': str(exc)}))
        sys.exit(0)


if __name__ == '__main__':
    main()
