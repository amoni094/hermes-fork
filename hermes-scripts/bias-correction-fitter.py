#!/usr/bin/env python3
"""Bias-correction fitter: Bradley-Terry MAP from pairwise comparisons."""
from __future__ import annotations
import argparse, fcntl, json, math, os, sys, tempfile, uuid
from collections import defaultdict
from datetime import datetime, timezone, UTC
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', 'fork')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base
CACHE = _hermes_root / 'cache'
PAIR_PATH = CACHE / 'pairwise-comparisons.jsonl'
OUT_PATH = CACHE / 'skill-ranking-posterior.json'


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


def kendall_tau(xs: list, ys: list) -> float:
    n = len(xs)
    if n < 2:
        return 0.0
    conc = disc = 0
    for i in range(n):
        for j in range(i + 1, n):
            dx = xs[i] - xs[j]
            dy = ys[i] - ys[j]
            if dx == 0 or dy == 0:
                continue
            if (dx > 0 and dy > 0) or (dx < 0 and dy < 0):
                conc += 1
            else:
                disc += 1
    tot = conc + disc
    return 0.0 if tot == 0 else (conc - disc) / tot


def fit_bt(pairs: list, iters: int = 80) -> dict:
    """Bradley-Terry MM (Zermelo) plus a first-listed position-bias term."""
    if len(pairs) < 8:
        return {'status': 'insufficient_data', 'n': len(pairs), 'ts': _now()}
    items = sorted({str(p.get('winner')) for p in pairs} | {str(p.get('loser')) for p in pairs} - {'None'})
    if len(items) < 2:
        return {'status': 'insufficient_data', 'n': len(pairs), 'n_items': len(items), 'ts': _now()}
    wins = {it: 0.0 for it in items}
    n_ij = {(i, j): 0.0 for i in items for j in items if i != j}
    pos_n = pos_first_win = 0.0
    for p in pairs:
        w, l = str(p.get('winner')), str(p.get('loser'))
        if w not in wins or l not in wins or w == l:
            continue
        wins[w] += 1.0
        n_ij[(w, l)] += 1.0
        n_ij[(l, w)] += 1.0
        order = str(p.get('position_order') or p.get('judge_position_order') or '')
        if order.startswith('winner_first') or order == '0':
            pos_n += 1.0
            pos_first_win += 1.0
        elif order.startswith('loser_first') or order == '1':
            pos_n += 1.0
    strength = {it: 1.0 for it in items}
    for _ in range(iters):
        nxt = {}
        for i in items:
            denom = 0.0
            for j in items:
                if i == j:
                    continue
                n = n_ij[(i, j)]
                if n:
                    denom += n / (strength[i] + strength[j])
            nxt[i] = (wins[i] / denom) if denom > 0 else strength[i]
        ssum = sum(nxt.values()) or 1.0
        strength = {k: v / ssum * len(items) for k, v in nxt.items()}
    # log-strength, centered
    logs = {k: math.log(max(v, 1e-12)) for k, v in strength.items()}
    mean_s = sum(logs.values()) / len(logs)
    posterior = {k: v - mean_s for k, v in logs.items()}
    ranked = sorted(posterior.items(), key=lambda kv: kv[1], reverse=True)
    pos_bias = (pos_first_win / pos_n - 0.5) if pos_n else 0.0
    return {
        'status': 'ok',
        'ts': _now(),
        'n': len(pairs),
        'n_items': len(items),
        'position_bias': pos_bias,
        'top': [k for k, _ in ranked[:10]],
        'posterior_means': dict(ranked[:40]),
    }


def load_pairs(path: Path) -> list:
    if not path.exists():
        return []
    pairs = []
    try:
        for line in path.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(rec, dict) and rec.get('winner') and rec.get('loser'):
                pairs.append(rec)
    except OSError:
        return []
    return pairs


def run() -> dict:
    try:
        pairs = load_pairs(PAIR_PATH)
        out = fit_bt(pairs)
        if out.get('status') != 'insufficient_data':
            _atomic_write(OUT_PATH, out)
        return out
    except Exception as e:
        return {'status': 'error', 'reason': str(e), 'ts': _now()}


def _self_test() -> int:
    empty = fit_bt([])
    assert empty['status'] == 'insufficient_data'
    items = ['a', 'b', 'c', 'd', 'e']
    truth = {it: float(i) for i, it in enumerate(items)}  # e strongest
    rng_pairs = []
    for _rep in range(10):
        for i in range(5):
            for j in range(5):
                if i == j:
                    continue
                wi, wj = items[i], items[j]
                if truth[wi] >= truth[wj]:
                    winner, loser = wi, wj
                else:
                    winner, loser = wj, wi
                rng_pairs.append({'winner': winner, 'loser': loser})
    r = fit_bt(rng_pairs)
    assert r['status'] == 'ok'
    means = [r['posterior_means'].get(it, 0.0) for it in items]
    tau = kendall_tau(means, [truth[it] for it in items])
    assert tau >= 0.85, tau
    tmp = Path(tempfile.gettempdir()) / ('bt-test-' + uuid.uuid4().hex + '.json')
    _atomic_write(tmp, r)
    tmp.unlink(missing_ok=True)
    print(f'[bias-correction-fitter] --self-test PASS tau={tau:.3f}')
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true')
    args = ap.parse_args()
    if args.self_test:
        try:
            return _self_test()
        except Exception as exc:
            print(f'[bias-correction-fitter] --self-test FAIL: {exc}')
            return 1
    out = run()
    print(json.dumps({k: out.get(k) for k in out if k != 'posterior_means'}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
