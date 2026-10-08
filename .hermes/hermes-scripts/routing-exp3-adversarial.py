#!/usr/bin/env python3
"""routing-exp3-adversarial.py — EXP3 mixed strategy over skills.

p_i = (1-gamma) w_i/sum(w) + gamma/n, gamma=0.1
w_i *= exp(gamma * reward_i / (n * p_i))
E[regret] <= sqrt(2 * T * n * log(n))

Conflict alarm when BM25 top-1 and EXP3 top-1 disagree with gap > 0.15.

Source: Auer et al. EXP3; Borodin & El-Yaniv online computation.
"""
from __future__ import annotations
import argparse
import json
import math
import os
import random
import sys
import tempfile
import time
from pathlib import Path

import os
from pathlib import Path
_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base

GAMMA = 0.1
GAP = 0.15
EPS = 1e-15


def _cache_dir() -> Path:
    override = os.environ.get('HERMES_CACHE_DIR', '').strip()
    p = Path(override) if override else (_hermes_root / 'cache')
    try:
        p.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return p


def _atomic_write_json(path: Path, obj) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + '.tmp')
        tmp.write_text(json.dumps(obj, indent=2) + '\n')
        os.replace(str(tmp), str(path))
    except Exception:
        try:
            tmp = path.with_suffix(path.suffix + '.tmp')
            if tmp.exists():
                tmp.unlink()
        except Exception:
            pass


def _load_json(path: Path, default):
    try:
        return json.loads(path.read_text())
    except (OSError, FileNotFoundError, json.JSONDecodeError):
        return default


def _append_jsonl(path: Path, obj: dict) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'a') as f:
            f.write(json.dumps(obj) + '\n')
    except Exception:
        pass


def mixed_strategy(weights: list, gamma: float = GAMMA) -> list:
    n = len(weights)
    if n == 0:
        return []
    s = sum(max(EPS, w) for w in weights) or float(n)
    return [(1.0 - gamma) * (max(EPS, w) / s) + gamma / n for w in weights]


def exp3_update(weights: list, played: int, reward: float, gamma: float = GAMMA) -> list:
    n = len(weights)
    p = mixed_strategy(weights, gamma)
    if not p or played < 0 or played >= n:
        return list(weights)
    pi = max(p[played], EPS)
    # clip reward
    r = 0.0 if reward < 0 else (1.0 if reward > 1 else float(reward))
    scale = math.exp(gamma * r / (n * pi))
    out = list(weights)
    out[played] = max(EPS, out[played] * scale)
    # prevent overflow: renormalize if max huge
    mx = max(out)
    if mx > 1e12:
        out = [w / mx for w in out]
    return out


def regret_bound(t: int, n: int) -> float:
    if t <= 0 or n <= 1:
        return 0.0
    return math.sqrt(2.0 * t * n * math.log(n))


def skill_names_from_index(index: dict, beta: dict) -> list:
    names = []
    skills = index.get('skills') if isinstance(index, dict) else None
    if isinstance(skills, list):
        names = [s.get('name') for s in skills if isinstance(s, dict) and s.get('name')]
    if not names and isinstance(beta, dict):
        names = sorted(beta.keys())
    return [str(x) for x in names]


def bm25_self_scores(index: dict, names: list) -> dict:
    """Static distinctiveness proxy when no query: IDF-weighted token count."""
    skills = index.get('skills') if isinstance(index, dict) else []
    df = {}
    by_name = {}
    n = 0
    if isinstance(skills, list):
        for s in skills:
            if not isinstance(s, dict):
                continue
            name = s.get('name')
            toks = [t.lower() for t in (s.get('tokens') or []) if isinstance(t, str)]
            if not name:
                continue
            n += 1
            by_name[name] = toks
            for t in set(toks):
                df[t] = df.get(t, 0) + 1
    n = max(n, 1)
    scores = {}
    for name in names:
        toks = by_name.get(name, [])
        sc = 0.0
        for t in toks:
            idf = math.log((n - df.get(t, 0) + 0.5) / (df.get(t, 0) + 0.5) + 1.0)
            sc += idf
        scores[name] = sc
    return scores


def top1(pairs: list) -> tuple:
    """pairs: (name, score). Returns (name, score, gap_to_second)."""
    if not pairs:
        return None, 0.0, 0.0
    pairs = sorted(pairs, key=lambda x: -x[1])
    name, sc = pairs[0]
    gap = sc - pairs[1][1] if len(pairs) > 1 else sc
    return name, sc, gap


def simulate(n: int, t: int, gamma: float = GAMMA, seed: int = 0) -> dict:
    rng = random.Random(seed)
    w = [1.0 / n] * n
    best = 0
    cum_reward = 0.0
    opt = 0.0
    regrets = []
    for k in range(1, t + 1):
        p = mixed_strategy(w, gamma)
        # sample arm
        u = rng.random()
        acc = 0.0
        played = n - 1
        for i, pi in enumerate(p):
            acc += pi
            if u <= acc:
                played = i
                break
        reward = 1.0 if played == best else 0.0
        # stochastic noise on best
        if played == best and rng.random() < 0.1:
            reward = 0.0
        if played != best and rng.random() < 0.05:
            reward = 1.0
        w = exp3_update(w, played, reward, gamma)
        cum_reward += reward
        opt += 1.0  # expected opt slightly less; use deterministic OPT=always best
        regrets.append(opt - cum_reward)
    bound = regret_bound(t, n)
    # sublinear: regret/t at end < regret/t at t/5
    r_early = regrets[max(0, t // 5 - 1)] / max(1, t // 5)
    r_late = regrets[-1] / t
    return {
        'T': t, 'n': n, 'final_regret': regrets[-1],
        'bound': bound, 'regret_over_t_early': r_early,
        'regret_over_t_late': r_late,
        'sublinear': r_late <= r_early + 1e-9 and regrets[-1] <= bound * 3,
        'weights': w, 'p': mixed_strategy(w, gamma),
    }


def run(cache: Path | None = None, reward_skill: str | None = None,
        reward: float = 0.0, bm25_scores: dict | None = None) -> dict:
    cache = cache or _cache_dir()
    index = _load_json(cache / 'skill-router-index.json', {})
    beta = _load_json(cache / 'skill-beta-state.json', {})
    state_path = cache / 'routing-exp3-skill-weights.json'
    state = _load_json(state_path, {})
    names = skill_names_from_index(index if isinstance(index, dict) else {},
                                   beta if isinstance(beta, dict) else {})
    if not names:
        names = list((state.get('weights') or {}).keys()) or ['dummy']
    wmap = (state.get('weights') if isinstance(state, dict) else None) or {}
    weights = [float(wmap.get(nm, 1.0 / max(len(names), 1))) for nm in names]
    n = len(names)
    T = int(state.get('T', 0) or 0) if isinstance(state, dict) else 0
    if reward_skill and reward_skill in names:
        played = names.index(reward_skill)
        weights = exp3_update(weights, played, reward)
        T += 1
    p = mixed_strategy(weights)
    exp3_pairs = list(zip(names, p))
    e_name, e_sc, e_gap = top1(exp3_pairs)
    if bm25_scores is None:
        bm25_scores = bm25_self_scores(index if isinstance(index, dict) else {}, names)
    # normalize bm25 to simplex-ish for gap comparability
    mx = max(bm25_scores.values()) if bm25_scores else 0.0
    if mx > 0:
        b_pairs = [(k, v / mx) for k, v in bm25_scores.items() if k in set(names)]
    else:
        b_pairs = [(k, 0.0) for k in names]
    b_name, b_sc, b_gap = top1(b_pairs)
    conflict = bool(e_name and b_name and e_name != b_name and abs(e_sc - b_sc) > GAP)
    new_state = {
        'ts': time.time(),
        'T': T,
        'n': n,
        'gamma': GAMMA,
        'weights': {names[i]: weights[i] for i in range(n)},
        'p': {names[i]: p[i] for i in range(n)},
        'regret_bound': regret_bound(max(T, 1), max(n, 2)),
        'exp3_top1': e_name,
        'bm25_top1': b_name,
        'conflict': conflict,
    }
    _atomic_write_json(state_path, new_state)
    try:
        _atomic_write_json(cache / 'routing-exp3-state.json', new_state)
    except Exception:
        pass
    if conflict:
        # ADV21-008: rotate conflicts.jsonl — keep only last 24h to avoid stale permanent alarms
        conf_path = cache / 'routing-conflicts.jsonl'
        now = time.time()
        cutoff = now - 86400.0
        try:
            existing = []
            if conf_path.exists():
                for raw in conf_path.read_text(encoding='utf-8', errors='replace').splitlines():
                    try:
                        row = json.loads(raw)
                        if float(row.get('ts', 0)) >= cutoff:
                            existing.append(raw)
                    except Exception:
                        pass
            existing.append(json.dumps({'ts': now, 'alarm': 'CONFLICT',
                'exp3_top1': e_name, 'bm25_top1': b_name,
                'exp3_p': e_sc, 'bm25_score_norm': b_sc,
                'gap': abs(e_sc - b_sc)}, ensure_ascii=False))
            tmp_conf = conf_path.with_suffix('.tmp')
            tmp_conf.write_text('\n'.join(existing) + '\n', encoding='utf-8')
            os.replace(tmp_conf, conf_path)
        except Exception:
            pass
    return new_state


def self_test() -> dict:
    failures = []
    try:
        w = [0.5, 0.5]
        p = mixed_strategy(w, 0.1)
        assert abs(sum(p) - 1.0) < 1e-9
        assert all(x >= 0.1 / 2 - 1e-12 for x in p)
        w2 = exp3_update(w, 0, 1.0)
        assert w2[0] > w[0]
    except Exception as e:
        failures.append(f'update: {e}')
    try:
        sim = simulate(n=5, t=100, seed=7)
        assert sim['sublinear'], sim
        assert sim['final_regret'] >= 0
    except Exception as e:
        failures.append(f'sim-100: {e}')
    try:
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d / 'skill-beta-state.json').write_text(json.dumps({
                'alpha-skill': {'alpha': 8, 'beta': 1},
                'beta-skill': {'alpha': 1, 'beta': 8},
            }))
            r = run(cache=d, reward_skill='alpha-skill', reward=1.0,
                    bm25_scores={'alpha-skill': 0.1, 'beta-skill': 0.9})
            assert r['conflict'] is True
            assert (d / 'routing-conflicts.jsonl').exists()
            json.dumps(r)
    except Exception as e:
        failures.append(f'conflict: {e}')
    try:
        with tempfile.TemporaryDirectory() as td:
            r = run(cache=Path(td))
            assert 'weights' in r
    except Exception as e:
        failures.append(f'missing: {e}')
    return {'self_test': 'PASS' if not failures else 'FAIL', 'n_failures': len(failures), 'failures': failures}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--skill', default=None)
    ap.add_argument('--reward', type=float, default=0.0)
    args = ap.parse_args()
    if args.self_test:
        r = self_test()
        print(json.dumps(r, indent=2))
        sys.exit(0 if r['self_test'] == 'PASS' else 1)
    try:
        r = run(reward_skill=args.skill, reward=args.reward)
        print(json.dumps({k: v for k, v in r.items() if k != 'weights'}, indent=2))
    except Exception:
        print(json.dumps({'error': 'shadow_path_failed'}))
        sys.exit(0)


if __name__ == '__main__':
    main()
