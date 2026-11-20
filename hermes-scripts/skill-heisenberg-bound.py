#!/usr/bin/env python3
"""skill-heisenberg-bound.py — Discrete uncertainty principle on skill usage signals.

Theory (3B1B Fourier series / uncertainty principle):
sigma_t * sigma_omega >= floor. Spiky usage -> small sigma_t, large sigma_omega.
Periodic usage -> small sigma_omega. Diffuse -> both large.
Regime flags authoring priority: diffuse = rewrite trigger text.
"""
from __future__ import annotations
import argparse, cmath, json, math, os, sqlite3, time
from pathlib import Path

_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_prof = os.environ.get('HERMES_PROFILE', 'fork')
_root = _base / 'profiles' / _prof if 'profiles' not in str(_base) else _base
CACHE = _root / 'cache'
OUT = CACHE / 'skill-heisenberg.json'
LIFECYCLE_DB = _base / 'memory-facts' / 'lifecycle.db'

def dft(x):
    N = len(x)
    return [sum(x[n] * cmath.exp(-2j * math.pi * k * n / N) for n in range(N))
            for k in range(N)]

def rms_width(weights, coords):
    E = sum(weights) or 1e-15
    mu = sum(c * w for c, w in zip(coords, weights)) / E
    var = sum((c - mu) ** 2 * w for c, w in zip(coords, weights)) / E
    return mu, max(var, 0.0) ** 0.5

def heisenberg(x):
    N = len(x)
    E = sum(v * v for v in x) or 1e-15
    t_weights = [v * v / E for v in x]
    _, st = rms_width(t_weights, range(N))
    X = dft(x)
    mags_sq = [abs(X[k]) ** 2 for k in range(N // 2 + 1)]
    Em = sum(mags_sq) or 1e-15
    f_weights = [m / Em for m in mags_sq]
    _, sw = rms_width(f_weights, range(len(mags_sq)))
    return {'sigma_t': round(st, 4), 'sigma_omega': round(sw, 4),
            'product': round(st * sw, 4)}

def classify(st, sw, median_st, median_sw):
    if st < median_st and sw > median_sw: return 'spiky'
    if sw < median_sw * 0.5: return 'periodic'
    if st > median_st and sw > median_sw: return 'diffuse'
    return 'mixed'

def _load_skill_bins():
    if not LIFECYCLE_DB.exists(): return {}
    N = 168  # 1 week of hourly bins
    try:
        conn = sqlite3.connect(LIFECYCLE_DB, timeout=5)
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        if 'anytime_eval_log' not in tables:
            conn.close()
            return {}
        rows = conn.execute(
            "SELECT skill_name, ts FROM anytime_eval_log ORDER BY ts"
        ).fetchall()
        conn.close()
        now = int(time.time()); cutoff = now - N * 3600
        bins: dict = {}
        for skill, ts in rows:
            if ts < cutoff: continue
            b = min(int((ts - cutoff) / 3600), N - 1)
            if skill not in bins: bins[skill] = [0.0] * N
            bins[skill][b] += 1.0
        return bins
    except Exception: return {}

def _atomic_write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(obj, indent=2) + '\n')
    os.replace(tmp, path)

def run(dry_run=False):
    bins = _load_skill_bins()
    if not bins:
        result = {'ts': int(time.time()), 'n_skills': 0, 'skills': []}
        if not dry_run: _atomic_write(OUT, result)
        return result
    results = []
    for skill, x in bins.items():
        h = heisenberg(x)
        results.append({'skill': skill, **h})
    sts = [r['sigma_t'] for r in results]
    sws = [r['sigma_omega'] for r in results]
    median_st = sorted(sts)[len(sts)//2] if sts else 1.0
    median_sw = sorted(sws)[len(sws)//2] if sws else 1.0
    for r in results:
        r['regime'] = classify(r['sigma_t'], r['sigma_omega'], median_st, median_sw)
    results.sort(key=lambda r: -r['product'])
    out = {'ts': int(time.time()), 'n_skills': len(results), 'skills': results[:20]}
    if not dry_run: _atomic_write(OUT, out)
    return out

def self_test():
    N = 16
    # Impulse at t=0: sigma_t small
    x_imp = [1.0] + [0.0] * (N - 1)
    h_imp = heisenberg(x_imp)
    assert h_imp['sigma_t'] < 1.0, f"Impulse sigma_t not small: {h_imp}"
    assert h_imp['product'] >= 0.0

    # Uniform: all energy at DC, sigma_omega near 0
    x_uni = [1.0] * N
    h_uni = heisenberg(x_uni)
    assert h_uni['sigma_omega'] < 1.0, f"Uniform sigma_omega not small: {h_uni}"
    assert h_uni['product'] >= 0.0

    # Impulse has larger sigma_omega than uniform
    assert h_imp['sigma_omega'] > h_uni['sigma_omega'], (
        f"Impulse should spread frequency more: {h_imp} vs {h_uni}")

    # Pure period-4 sine (N=16): sigma_omega < sigma_omega(impulse)
    x_sin = [math.sin(2 * math.pi * i / 4) for i in range(N)]
    h_sin = heisenberg(x_sin)
    assert h_sin['sigma_omega'] < h_imp['sigma_omega'], (
        f"Sine sigma_omega should be less than impulse: {h_sin}")

    # product >= 0 always
    for x in [x_imp, x_uni, x_sin, [0.0]*N]:
        h = heisenberg(x)
        assert h['product'] >= 0.0, f"product negative: {h}"

    # Return dict with correct keys
    for key in ('sigma_t', 'sigma_omega', 'product'):
        assert key in h_imp, f"Missing key: {key}"

    print("self-test: PASS")

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--self-test', action='store_true')
    p.add_argument('--dry-run', action='store_true')
    args = p.parse_args()
    if args.self_test: self_test(); return
    print(json.dumps(run(args.dry_run), indent=2))

if __name__ == '__main__': main()
