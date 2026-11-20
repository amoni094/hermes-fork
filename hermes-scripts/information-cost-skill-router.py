#!/usr/bin/env python3
"""Information-cost-aware skill router.

Scores skills as expected_return - beta * KL(posterior || marginal prior)
and updates the marginal prior by exponential moving average.
"""
from __future__ import annotations
import argparse, json, math, os, random, sqlite3, sys, time, uuid, zlib
from collections import Counter, defaultdict
from datetime import datetime, timezone, UTC
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', 'fork')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base
CACHE = _hermes_root / 'cache'

def _now() -> str:
    return datetime.now(UTC).isoformat()

def _atomic_write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(obj, indent=2) + '\n', encoding='utf-8')
    os.replace(tmp, path)

def _lifecycle_db() -> Path:
    return _hermes_root / 'memory-facts' / 'lifecycle.db'

def _connect(db: Path | None = None) -> sqlite3.Connection:
    path = db or _lifecycle_db()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.execute('PRAGMA journal_mode=WAL')
    conn.row_factory = sqlite3.Row
    return conn

OUT_PATH = CACHE / 'information-cost-router-state.json'
BETA = 0.1
EMA = 0.9
EPS = 1e-9


def kl_divergence(p, q, eps=EPS):
    s = 0.0
    keys = set(p) | set(q)
    for k in keys:
        pk = max(eps, float(p.get(k, 0.0)))
        qk = max(eps, float(q.get(k, 0.0)))
        s += pk * math.log(pk / qk)
    return s


def normalize(counts):
    tot = float(sum(counts.values())) or 1.0
    return {k: float(v) / tot for k, v in counts.items()}


def ema_prior(prior, posterior, lam=EMA):
    keys = set(prior) | set(posterior)
    out = {}
    for k in keys:
        out[k] = lam * float(prior.get(k, 0.0)) + (1.0 - lam) * float(posterior.get(k, 0.0))
    return normalize(out)


def score_skills(expected_return, posterior, prior, beta=BETA):
    kl = kl_divergence(posterior, prior)
    scores = {}
    for sk, er in expected_return.items():
        post_p = float(posterior.get(sk, 0.0))
        prior_p = float(prior.get(sk, 0.0))
        # per-skill KL contribution for logging
        pk = max(EPS, post_p)
        qk = max(EPS, prior_p)
        kl_contrib = pk * math.log(pk / qk)
        net = float(er) - beta * kl
        scores[sk] = {
            'expected_return': float(er),
            'kl_penalty': beta * kl,
            'kl_contrib': kl_contrib,
            'net_score': net,
            'posterior_prob': post_p,
            'prior_prob': prior_p,
        }
    return scores, kl


def load_skill_counts():
    counts = Counter()
    returns = defaultdict(list)
    jsonl = CACHE / 'routing-events.jsonl'
    if jsonl.exists():
        try:
            for line in jsonl.read_text(encoding='utf-8').splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                sk = rec.get('top_skill') or rec.get('skill')
                if not sk:
                    continue
                counts[str(sk)] += 1
                sc = rec.get('top_score', rec.get('score'))
                try:
                    returns[str(sk)].append(float(sc))
                except (TypeError, ValueError):
                    pass
        except OSError:
            pass
    return counts, returns


def persist(state):
    _atomic_write(OUT_PATH, state)
    try:
        conn = _connect()
        ts = state.get('last_updated') or _now()
        for sk, st in (state.get('skill_scores') or {}).items():
            conn.execute(
                'INSERT INTO skill_kl_history(ts, skill_name, posterior_prob, prior_prob, kl_contrib, net_score) '
                'VALUES (?,?,?,?,?,?)',
                (ts, sk, float(st.get('posterior_prob') or 0), float(st.get('prior_prob') or 0),
                 float(st.get('kl_contrib') or 0), float(st.get('net_score') or 0)),
            )
        conn.commit()
        conn.close()
    except Exception:
        pass
    return state


def run(beta=BETA):
    counts, returns = load_skill_counts()
    if not counts:
        return {'status': 'insufficient_data', 'n': 0, 'ranked': [], 'skill_scores': {}}
    posterior = normalize(counts)
    prev = {}
    if OUT_PATH.exists():
        try:
            prev = json.loads(OUT_PATH.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError):
            prev = {}
    prior = prev.get('marginal_prior') or dict(posterior)
    prior = ema_prior(prior, posterior)
    expected = {sk: (sum(vs) / len(vs) if vs else 0.0) for sk, vs in returns.items()}
    for sk in posterior:
        expected.setdefault(sk, 0.0)
    scores, kl = score_skills(expected, posterior, prior, beta=beta)
    ranked = sorted(scores, key=lambda s: scores[s]['net_score'], reverse=True)
    state = {
        'marginal_prior': prior,
        'beta': beta,
        'last_updated': _now(),
        'session_kl': kl,
        'ranked': ranked,
        'skill_scores': scores,
    }
    return persist(state)


def _self_test() -> int:
    # Concentrated posterior vs uniform prior => positive KL, ranking by net score
    prior = {'a': 0.5, 'b': 0.5}
    posterior = {'a': 0.9, 'b': 0.1}
    expected = {'a': 0.4, 'b': 0.9}
    scores, kl = score_skills(expected, posterior, prior, beta=0.1)
    assert kl > 0.0, f'kl={kl}'
    # b has higher return; KL penalty is session-level so ranking follows return
    assert scores['b']['net_score'] > scores['a']['net_score']
    new_prior = ema_prior(prior, posterior, lam=0.9)
    assert abs(sum(new_prior.values()) - 1.0) < 1e-9
    assert new_prior['a'] > prior['a']
    tmp = OUT_PATH.with_name(OUT_PATH.stem + '_test_' + uuid.uuid4().hex + OUT_PATH.suffix)
    _atomic_write(tmp, {'skill_scores': scores, 'session_kl': kl})
    tmp.unlink(missing_ok=True)
    print(f'[information-cost-skill-router] --self-test PASS kl={kl:.4f} ranked=b>a')
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--beta', type=float, default=BETA)
    args = ap.parse_args()
    if args.self_test:
        try:
            sys.exit(_self_test())
        except Exception as exc:
            print(f'[information-cost-skill-router] --self-test FAIL: {exc}')
            sys.exit(1)
    run(beta=args.beta)


if __name__ == '__main__':
    main()
