#!/usr/bin/env python3
"""The Delegation Blind Spot - Auditing Product Decisions from Agent Choices.

A decision is resolvable (interval width <= epsilon) iff observation channel
+ value contrast yield a confidence region concentrating at O(1/sqrt(n)).
Unresolved decisions are flagged structurally_ambiguous, never data_limited.
"""
from __future__ import annotations

import os
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base

import argparse
import fcntl
import json
import math
import random
import sqlite3
import sys
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone

CACHE = _hermes_root / 'cache'
OUT_PATH = CACHE / 'decision_audit_state.json'
Z_WILSON = 1.96
CONTRAST_EPS = 0.05
DET_MAX = 0.10
SIM_MAX = 0.15
AMB_MIN = 0.20


def _true_home(base: Path) -> Path:
    p = Path(base)
    if p.name != '.hermes' and p.parent.name == 'profiles':
        return p.parent.parent
    return p


LIFECYCLE_DB = _true_home(_hermes_base) / 'memory-facts' / 'lifecycle.db'


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _coerce_float(v, default=0.0) -> float:
    try:
        x = float(v)
        if not math.isfinite(x):
            return default
        return x
    except (TypeError, ValueError):
        return default


def _coerce_int(v, default=0) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def _atomic_write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(path.suffix + '.lock') if path.suffix else path.with_name(path.name + '.lock')
    tmp = path.with_name(path.name + '.tmp')
    payload = json.dumps(obj, indent=2) + '\n'
    with open(str(lock_path), 'a', encoding='utf-8') as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        try:
            tmp.write_text(payload, encoding='utf-8')
            tmp.replace(path)
        finally:
            fcntl.flock(lf, fcntl.LOCK_UN)


def wilson_width(p: float, n: float, z: float = Z_WILSON) -> float:
    """Width of Wilson score interval for a Bernoulli parameter. O(1/sqrt(n))."""
    p = max(0.0, min(1.0, _coerce_float(p)))
    n = max(1.0, _coerce_float(n, 1.0))
    z2 = z * z
    denom = 1.0 + z2 / n
    inner = p * (1.0 - p) / n + z2 / (4.0 * n * n)
    margin = z * math.sqrt(max(0.0, inner)) / denom
    w = 2.0 * margin
    if not math.isfinite(w):
        return 1.0
    return max(0.0, min(1.0, w))


def observation_max_p(channel) -> float:
    if not channel:
        return 0.0
    if isinstance(channel, dict):
        vals = [_coerce_float(v) for v in channel.values()]
    else:
        vals = [_coerce_float(v) for v in channel]
    s = sum(vals)
    if s <= 0:
        return 0.0
    return max(vals) / s


def decision_interval_width(channel, value_contrast: float, n: float) -> float:
    """Identification width: concentrates iff contrast is bounded away from 0.

    If |value_contrast| < CONTRAST_EPS the optimal routing is not identified
    even as n -> inf; width is floored above AMB_MIN (structurally_ambiguous).
    Otherwise Wilson width of the dominant observation probability, which is
    O(1/sqrt(n)).
    """
    p_hat = observation_max_p(channel)
    w = wilson_width(p_hat, n)
    contrast = abs(_coerce_float(value_contrast))
    if contrast < CONTRAST_EPS:
        return max(w, AMB_MIN + 0.01)
    return min(1.0, w)


def classify(width: float) -> str:
    w = _coerce_float(width, 1.0)
    if w < DET_MAX:
        return 'resolvable_deterministic'
    if w < SIM_MAX:
        return 'resolvable_simulation'
    return 'structurally_ambiguous'


def parse_flags(raw) -> list:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(x) for x in raw if str(x).strip()]
    s = str(raw).strip()
    if not s:
        return []
    try:
        v = json.loads(s)
    except (json.JSONDecodeError, TypeError):
        return [t.strip() for t in s.split(',') if t.strip()]
    if isinstance(v, list):
        return [str(x) for x in v if str(x).strip()]
    if isinstance(v, dict):
        return [str(k) for k in v.keys()]
    return [str(v)]


def channel_from_flags(flags: list, success_rate: float) -> list:
    if flags:
        cnt = Counter(flags)
        total = sum(cnt.values()) or 1
        skills = sorted(cnt)
        return [cnt[s] / total for s in skills]
    p = max(0.0, min(1.0, success_rate))
    return [p, 1.0 - p]


def audit_episode(episode_id, subtask_count, success_rate, flags) -> dict:
    n = max(1, _coerce_int(subtask_count, 1))
    sr = max(0.0, min(1.0, _coerce_float(success_rate)))
    fl = parse_flags(flags)
    channel = channel_from_flags(fl, sr)
    contrast = abs(sr - 0.5) * 2.0
    width = decision_interval_width(channel, contrast, n)
    return {
        'episode_id': str(episode_id),
        'verdict': classify(width),
        'interval_width': round(width, 6),
        'observation_channel': channel,
        'value_contrast': round(contrast, 6),
        'n': n,
    }


def aggregate_rows(rows) -> list:
    groups = defaultdict(lambda: {'n': 0.0, 'succ_w': 0.0, 'flags': []})
    for row in rows:
        if isinstance(row, dict):
            eid = row.get('episode_id')
            n = _coerce_int(row.get('subtask_count'), 1)
            sr = _coerce_float(row.get('success_rate'))
            flags = row.get('audit_flags')
        else:
            eid = row[0]
            n = _coerce_int(row[1], 1)
            sr = _coerce_float(row[2])
            flags = row[3] if len(row) > 3 else ''
        if eid is None:
            continue
        g = groups[str(eid)]
        nn = max(1, n)
        g['n'] += nn
        g['succ_w'] += sr * nn
        g['flags'].extend(parse_flags(flags))
    out = []
    for eid, g in groups.items():
        n = max(1.0, g['n'])
        sr = g['succ_w'] / n
        out.append(audit_episode(eid, n, sr, g['flags']))
    return out


def summarize(episodes: list) -> dict:
    det = sum(1 for e in episodes if e['verdict'] == 'resolvable_deterministic')
    sim = sum(1 for e in episodes if e['verdict'] == 'resolvable_simulation')
    amb = sum(1 for e in episodes if e['verdict'] == 'structurally_ambiguous')
    return {
        'ts': _now(),
        'n_decisions': len(episodes),
        'resolvable_det': det,
        'resolvable_sim': sim,
        'ambiguous': amb,
        'episodes': [{'episode_id': e['episode_id'], 'verdict': e['verdict'],
                      'interval_width': e['interval_width']} for e in episodes],
    }


def _connect(db: Path):
    conn = sqlite3.connect(str(db), timeout=30)
    conn.execute('PRAGMA journal_mode=WAL')
    conn.row_factory = sqlite3.Row
    return conn


def load_live_rows(db: Path):
    if not db.exists():
        return []
    conn = _connect(db)
    try:
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if 'delegation_audit' not in tables:
            return []
        return conn.execute(
            'SELECT episode_id, subtask_count, success_rate, audit_flags FROM delegation_audit'
        ).fetchall()
    finally:
        conn.close()


def multinomial_channel(probs, n_draws, rng) -> list:
    k = len(probs)
    counts = [0] * k
    idx = list(range(k))
    for _ in range(n_draws):
        counts[rng.choices(idx, weights=probs, k=1)[0]] += 1
    tot = float(n_draws) if n_draws else 1.0
    return [c / tot for c in counts]


def layer1_demo(rng=None) -> dict:
    """50 simulated agent decisions, 10 skill routings each."""
    rng = rng or random.Random(42)
    n_skills = 10
    episodes = []
    # 20 deterministic extractor: one-hot channel, high contrast, n large enough
    for i in range(20):
        channel = [0.0] * n_skills
        channel[0] = 1.0
        rec = {
            'episode_id': 'det-%02d' % i,
            'kind': 'deterministic',
            'observation_channel': channel,
            'value_contrast': 0.90,
            'n': 80,
        }
        rec['interval_width'] = decision_interval_width(channel, rec['value_contrast'], rec['n'])
        rec['verdict'] = classify(rec['interval_width'])
        episodes.append(rec)
    # 15 simulation: 2000 multinomial draws from a peaked routing dist
    peaked = [0.62] + [0.38 / 9.0] * 9
    for i in range(15):
        channel = multinomial_channel(peaked, 2000, rng)
        rec = {
            'episode_id': 'sim-%02d' % i,
            'kind': 'simulation',
            'observation_channel': channel,
            'value_contrast': 0.55,
            'n': 2000,
        }
        rec['interval_width'] = decision_interval_width(channel, rec['value_contrast'], rec['n'])
        rec['verdict'] = classify(rec['interval_width'])
        episodes.append(rec)
    # 15 structurally ambiguous: uniform routing, near-zero contrast (non-identified)
    uniform = [1.0 / n_skills] * n_skills
    for i in range(15):
        channel = multinomial_channel(uniform, 2000, rng)
        rec = {
            'episode_id': 'amb-%02d' % i,
            'kind': 'ambiguous',
            'observation_channel': channel,
            'value_contrast': 0.0,
            'n': 2000,
        }
        rec['interval_width'] = decision_interval_width(channel, rec['value_contrast'], rec['n'])
        rec['verdict'] = classify(rec['interval_width'])
        episodes.append(rec)
    return {'episodes': episodes, 'summary': summarize(episodes)}


def run_live(out_path: Path) -> dict:
    rows = load_live_rows(LIFECYCLE_DB)
    if not rows:
        return {'status': 'insufficient_data', 'n_decisions': 0, 'ts': _now()}
    episodes = aggregate_rows(rows)
    if not episodes:
        return {'status': 'insufficient_data', 'n_decisions': 0, 'ts': _now()}
    state = summarize(episodes)
    state['status'] = 'ok'
    _atomic_write(out_path, state)
    return state


def _self_test() -> int:
    demo = layer1_demo(random.Random(7))
    eps = demo['episodes']
    assert len(eps) == 50, len(eps)
    det = [e for e in eps if e['kind'] == 'deterministic']
    sim = [e for e in eps if e['kind'] == 'simulation']
    amb = [e for e in eps if e['kind'] == 'ambiguous']
    assert len(det) == 20 and len(sim) == 15 and len(amb) == 15
    for e in det:
        assert e['interval_width'] < DET_MAX, e
        assert e['verdict'] == 'resolvable_deterministic', e
    for e in sim:
        assert e['interval_width'] < SIM_MAX, e
    for e in amb:
        assert e['interval_width'] > AMB_MIN, e
        assert e['verdict'] == 'structurally_ambiguous', e
        assert 'data_limited' not in e['verdict']
    # Wilson concentrates: doubling n shrinks width for identified decisions
    w1 = wilson_width(0.8, 50)
    w2 = wilson_width(0.8, 200)
    assert w2 < w1, (w1, w2)
    empty = aggregate_rows([])
    assert empty == []
    tmp = OUT_PATH.with_name(OUT_PATH.stem + '_test_' + uuid.uuid4().hex + OUT_PATH.suffix)
    try:
        _atomic_write(tmp, demo['summary'])
        loaded = json.loads(tmp.read_text(encoding='utf-8'))
        assert loaded['n_decisions'] == 50
        assert 'resolvable_det' in loaded
    finally:
        tmp.unlink(missing_ok=True)
        lp = tmp.with_suffix(tmp.suffix + '.lock')
        lp.unlink(missing_ok=True)
    print('[delegation-blind-spot-audit] --self-test PASS n=50 det=%s sim=%s amb=%s' % (
        demo['summary']['resolvable_det'], demo['summary']['resolvable_sim'], demo['summary']['ambiguous']))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description='Delegation blind-spot decision audit')
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--run', action='store_true')
    args = ap.parse_args()
    if args.self_test:
        try:
            return _self_test()
        except Exception as exc:
            print('[delegation-blind-spot-audit] --self-test FAIL: %s' % exc)
            return 1
    try:
        state = run_live(OUT_PATH)
        slim = {k: state[k] for k in state if k != 'episodes'}
        if 'episodes' in state:
            slim['n_episodes_listed'] = len(state.get('episodes') or [])
        print(json.dumps(slim))
    except Exception as exc:
        print(json.dumps({'status': 'error', 'reason': str(exc)}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
