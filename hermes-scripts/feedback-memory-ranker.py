#!/usr/bin/env python3
"""UCB episode-replay ranker for tool sequences."""
from __future__ import annotations
import os
from pathlib import Path
_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', 'fork')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base
import argparse
import json
import math
from collections import defaultdict
from datetime import datetime, timezone, UTC

CACHE = _hermes_root / 'cache'
STATE_PATH = CACHE / 'feedback-memory-ranker-state.json'

def _atomic_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(data, indent=2))
    os.replace(tmp, path)

def ucb_score(success: float, trials: float, total: float, alpha: float = 1.0,
              beta: float = 1.0, c: float = 1.5) -> float:
    trials = max(float(trials), 0.0)
    mean = (success + alpha) / (trials + beta)
    bonus = c * math.sqrt(math.log(max(total, 1.0) + 1.0) / max(trials, 1.0))
    return mean + bonus

def _seq_key(seq) -> str:
    if isinstance(seq, (list, tuple)):
        return ' > '.join(str(x) for x in seq)
    return str(seq)

def aggregate_episodes(episodes: list) -> dict:
    stats = defaultdict(lambda: {'success': 0.0, 'trials': 0})
    for ep in episodes or []:
        key = _seq_key(ep.get('tool_sequence') or ep.get('sequence') or '')
        if not key:
            continue
        ok = ep.get('success_bool')
        if ok is None:
            ok = bool(ep.get('success'))
        stats[key]['trials'] += 1
        stats[key]['success'] += 1.0 if ok else 0.0
    return dict(stats)

def rank_sequences(episodes: list, c: float = 1.5) -> list:
    stats = aggregate_episodes(episodes)
    total = sum(v['trials'] for v in stats.values()) or 1
    ranked = []
    for key, st in stats.items():
        score = ucb_score(st['success'], st['trials'], total, c=c)
        mean = st['success'] / max(st['trials'], 1)
        ranked.append({'sequence': key, 'ucb': round(score, 6),
                       'mean_success': round(mean, 6), 'trials': st['trials']})
    ranked.sort(key=lambda x: (-x['ucb'], -x['mean_success'], x['sequence']))
    return ranked

def ranking_consistency(a: list, b: list) -> float:
    ka = [x['sequence'] for x in a]
    kb = [x['sequence'] for x in b]
    if not ka and not kb:
        return 1.0
    n = max(len(ka), len(kb), 1)
    same = sum(1 for i, s in enumerate(ka) if i < len(kb) and s == kb[i])
    return same / n

def correctness_lift(ranked: list, baseline_mean: float) -> float:
    if not ranked:
        return 0.0
    return ranked[0]['mean_success'] - baseline_mean

def layer1_demo() -> None:
    episodes = []
    for _ in range(30):
        episodes.append({'tool_sequence': ['search', 'read', 'write'], 'success_bool': True})
    for _ in range(20):
        episodes.append({'tool_sequence': ['search', 'browse'], 'success_bool': False})
    for _ in range(10):
        episodes.append({'tool_sequence': ['search', 'browse'], 'success_bool': True})
    r1 = rank_sequences(episodes)
    r2 = rank_sequences(list(reversed(episodes)))
    assert r1[0]['sequence'] == 'search > read > write', r1[0]
    cons = ranking_consistency(r1, r2)
    assert cons == 1.0, cons
    overall = sum(1 for e in episodes if e['success_bool']) / len(episodes)
    lift = correctness_lift(r1, overall)
    assert lift >= 0.15, lift
    print('[layer1] PASS lift={:.3f} consistency={} top={}'.format(lift, cons, r1[0]['sequence']))

def main() -> None:
    pa = argparse.ArgumentParser()
    pa.add_argument('--layer1', action='store_true')
    pa.add_argument('--self-test', action='store_true')
    pa.add_argument('--episodes', type=str, default='')
    args = pa.parse_args()
    if args.layer1 or args.self_test:
        layer1_demo()
        return
    episodes = []
    if args.episodes:
        p = Path(args.episodes)
        raw = p.read_text(encoding='utf-8') if p.exists() else args.episodes
        try:
            episodes = json.loads(raw)
        except json.JSONDecodeError:
            episodes = []
    ranked = rank_sequences(episodes)
    out = {'ts': datetime.now(UTC).isoformat(), 'n_episodes': len(episodes), 'ranked': ranked[:20]}
    _atomic_json(STATE_PATH, out)
    print(json.dumps(out, indent=2))

if __name__ == '__main__':
    main()
