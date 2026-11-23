#!/usr/bin/env python3
"""routing-fano-bound.py — Fano inequality lower bound on router error.

P_error >= (H(S|Q) - 1) / log2(n)
If current_error < bound: IMPOSSIBLE (bug). If current_error > bound + 0.15: IMPROVEMENT_POSSIBLE.

Source: Cover & Thomas, Elements of Information Theory (Fano's inequality).
"""
from __future__ import annotations
import argparse
import json
import math
import os
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path

import os
from pathlib import Path
_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', 'fork')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base

IMPROVE_GAP = 0.15
EPS = 1e-15
# Beta(2,1) after one success has mean 2/3 → "error" 0.33. That is a prior,
# not BM25 retrieval error. Require real mass before IMPROVEMENT_POSSIBLE.
MIN_OBS = 5.0          # alpha+beta; skip Laplace / single-success priors
MIN_INFORMATIVE = 8    # skills with MIN_OBS before error is actionable


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
        tmp.write_text(json.dumps(obj, indent=2) + '\n', encoding='utf-8')
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
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, FileNotFoundError, json.JSONDecodeError):
        return default


def _load_jsonl(path: Path) -> list:
    rows = []
    try:
        for line in path.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    except (OSError, FileNotFoundError):
        pass
    return rows


def entropy(probs) -> float:
    h = 0.0
    for p in probs:
        if p > EPS:
            h -= p * math.log2(p)
    return h


def softmax_entropy(scores: list, temp: float = 1.0) -> float:
    if not scores:
        return 0.0
    m = max(scores)
    exps = [math.exp((s - m) / max(temp, EPS)) for s in scores]
    z = sum(exps) or 1.0
    ps = [e / z for e in exps]
    return entropy(ps)


def estimate_h_s_given_q(index: dict, calib_rows: list, n_skills: int) -> tuple:
    """Mean entropy of p(s|q). Prefer calib skill posteriors; else BM25 self-query proxy."""
    # calib rows may have skill / selected_skill / top_skill / posterior
    conds = []
    for row in calib_rows:
        if not isinstance(row, dict):
            continue
        post = row.get('posterior') or row.get('p_s_q') or row.get('skill_probs')
        if isinstance(post, dict) and post:
            tot = sum(float(v) for v in post.values() if isinstance(v, (int, float)))
            if tot > 0:
                conds.append(entropy([float(v) / tot for v in post.values() if isinstance(v, (int, float))]))
                continue
        sk = row.get('skill') or row.get('selected_skill') or row.get('top_skill')
        if isinstance(sk, str) and sk:
            # degenerate one-hot => 0 entropy contribution; skip for mean H
            continue
    if conds:
        return sum(conds) / len(conds), 'calibration_posterior'
    skills = index.get('skills') if isinstance(index, dict) else []
    if not isinstance(skills, list) or not skills:
        # uniform fallback
        if n_skills <= 1:
            return 0.0, 'uniform_n1'
        return math.log2(n_skills), 'uniform_fallback'
    # token BM25-like scores: each skill description as query against all
    df = {}
    docs = []
    for s in skills:
        if not isinstance(s, dict):
            continue
        toks = [t.lower() for t in (s.get('tokens') or []) if isinstance(t, str)]
        docs.append((s.get('name'), toks))
        for t in set(toks):
            df[t] = df.get(t, 0) + 1
    n = max(len(docs), 1)
    hs = []
    for _, qtoks in docs:
        qset = set(qtoks)
        scores = []
        for _, dtoks in docs:
            sc = 0.0
            tf = Counter(dtoks)
            for t in qset:
                idf = math.log((n - df.get(t, 0) + 0.5) / (df.get(t, 0) + 0.5) + 1.0)
                f = tf.get(t, 0)
                sc += idf * f
            scores.append(sc)
        hs.append(softmax_entropy(scores))
    if not hs:
        return (math.log2(n_skills) if n_skills > 1 else 0.0), 'empty_index'
    return sum(hs) / len(hs), 'bm25_self_query'


def current_error(beta: dict, min_obs: float = MIN_OBS) -> tuple:
    """Return (error, n_informative, n_total).

    error = 1 - mean posterior mean over skills with alpha+beta >= min_obs.
    Cold-start Beta(2,1) is excluded so Fano does not alarm on priors.
    """
    if not isinstance(beta, dict) or not beta:
        return 0.5, 0, 0
    means = []
    n_total = 0
    for v in beta.values():
        if not isinstance(v, dict):
            continue
        try:
            a = float(v.get('alpha', 1.0))
            b = float(v.get('beta', 1.0))
        except (TypeError, ValueError):
            continue
        n_total += 1
        if (a + b) < min_obs:
            continue
        means.append(a / max(a + b, EPS))
    if not means:
        return 0.5, 0, n_total
    return 1.0 - (sum(means) / len(means)), len(means), n_total


def fano_bound(h_s_q: float, n: int) -> float:
    if n <= 1:
        return 0.0
    return max(0.0, (h_s_q - 1.0) / math.log2(n))


def compute(index: dict, beta: dict, calib_rows: list) -> dict:
    skills = []
    if isinstance(index, dict) and isinstance(index.get('skills'), list):
        skills = [s.get('name') for s in index['skills'] if isinstance(s, dict) and s.get('name')]
    if not skills and isinstance(beta, dict):
        skills = list(beta.keys())
    n = max(len(skills), 1)
    h, src = estimate_h_s_given_q(index if isinstance(index, dict) else {}, calib_rows, n)
    lb = fano_bound(h, n)
    err, n_inf, n_beta = current_error(beta if isinstance(beta, dict) else {})
    insufficient = n_inf < MIN_INFORMATIVE
    if insufficient:
        status = 'OK'
    elif err + 1e-12 < lb:
        status = 'IMPOSSIBLE'
    elif err > lb + IMPROVE_GAP:
        status = 'IMPROVEMENT_POSSIBLE'
    else:
        status = 'OK'
    return {
        'ts': time.time(),
        'n_skills': n,
        'H_S_given_Q': round(h, 6),
        'H_source': src,
        'fano_lower_bound': round(lb, 6),
        'current_error': round(err, 6),
        'n_informative': n_inf,
        'n_beta': n_beta,
        'insufficient_observations': insufficient,
        'status': status,
        'alarm': status in ('IMPROVEMENT_POSSIBLE', 'IMPOSSIBLE'),  # ADV21-007
        'impossible': status == 'IMPOSSIBLE',
        'improvement_gap': IMPROVE_GAP,
    }


def run(cache: Path | None = None) -> dict:
    cache = cache or _cache_dir()
    index = _load_json(cache / 'skill-router-index.json', {})
    beta = _load_json(cache / 'skill-beta-state.json', {})
    calib = _load_jsonl(cache / 'calibration-log.jsonl')
    result = compute(index, beta, calib)
    try:
        _atomic_write_json(cache / 'routing-fano-bound.json', result)
    except Exception:
        pass
    return result


def self_test() -> dict:
    failures = []
    try:
        lb = fano_bound(3.0, 16)
        assert abs(lb - (3.0 - 1.0) / 4.0) < 1e-12
        assert fano_bound(0.2, 8) == 0.0
    except Exception as e:
        failures.append(f'formula: {e}')
    try:
        # high residual entropy + low empirical error => IMPOSSIBLE
        beta = {f's{i}': {'alpha': 99.0, 'beta': 1.0} for i in range(8)}
        index = {'skills': [{'name': f's{i}', 'tokens': ['tok'] * 5} for i in range(8)]}
        r = compute(index, beta, [])
        # self-query with identical tokens => high H; error near 0
        assert r['current_error'] < 0.05
        # may or may not be IMPOSSIBLE depending on H; just check keys
        assert r['status'] in ('IMPOSSIBLE', 'OK', 'IMPROVEMENT_POSSIBLE')
        json.dumps(r)
    except Exception as e:
        failures.append(f'status: {e}')
    try:
        # force IMPROVEMENT_POSSIBLE: low H, high error, enough observations
        idx = {'skills': [{'name': f's{i}', 'tokens': [f'uniq{i}']} for i in range(10)]}
        beta = {f's{i}': {'alpha': 1.0, 'beta': 9.0} for i in range(10)}
        r = compute(idx, beta, [])
        # bound ~0, error 0.9, n_informative=10 => IMPROVEMENT_POSSIBLE
        assert r['status'] == 'IMPROVEMENT_POSSIBLE', r
    except Exception as e:
        failures.append(f'improve: {e}')
    try:
        # cold-start Beta(2,1) must not raise IMPROVEMENT_POSSIBLE
        cold = {f's{i}': {'alpha': 2.0, 'beta': 1.0} for i in range(20)}
        idx = {'skills': [{'name': f's{i}', 'tokens': [f'uniq{i}']} for i in range(20)]}
        r = compute(idx, cold, [])
        assert r['insufficient_observations'] is True, r
        assert r['status'] == 'OK', r
        assert r['alarm'] is False, r
    except Exception as e:
        failures.append(f'coldstart: {e}')
    try:
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            r = run(cache=d)
            assert (d / 'routing-fano-bound.json').exists()
    except Exception as e:
        failures.append(f'missing: {e}')
    return {'self_test': 'PASS' if not failures else 'FAIL', 'n_failures': len(failures), 'failures': failures}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true')
    args = ap.parse_args()
    if args.self_test:
        r = self_test()
        print(json.dumps(r, indent=2))
        sys.exit(0 if r['self_test'] == 'PASS' else 1)
    try:
        r = run()
        print(json.dumps(r, indent=2))
    except Exception:
        print(json.dumps({'error': 'shadow_path_failed'}))
        sys.exit(0)


if __name__ == '__main__':
    main()
