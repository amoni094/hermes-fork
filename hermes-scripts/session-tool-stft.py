#!/usr/bin/env python3
"""session-tool-stft.py — STFT on in-session tool call sequence (Fourier series).

Theory (3B1B Fourier): DFT on windows of W tool calls detects recurring patterns.
Phase break = window where dominant frequency shifts (task-type transition).
Distinct from skill-fourier-schedule (hourly bins of skill use).
"""
from __future__ import annotations
import argparse, cmath, json, math, os, time
from pathlib import Path
import itertools

_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_prof = os.environ.get('HERMES_PROFILE', 'fork')
_root = _base / 'profiles' / _prof if 'profiles' not in str(_base) else _base
CACHE = _root / 'cache'
OUT = CACHE / 'session-tool-stft.json'
SESSIONS_DIR = _root / 'sessions'
W, H = 8, 2

def dft(x):
    N = len(x)
    return [sum(x[n] * cmath.exp(-2j * math.pi * k * n / N) for n in range(N))
            for k in range(N)]

def encode(tools):
    vocab = {t: i for i, t in enumerate(sorted(set(tools)))}
    return [float(vocab[t]) for t in tools], vocab

def dominant_period(x):
    N = len(x)
    if N < 4: return None
    X = dft(x)
    # Find max magnitude at k>0
    best = max(range(1, N // 2 + 1), key=lambda k: abs(X[k]))
    mag = abs(X[best])
    dc_mag = abs(X[0])
    is_flat = (mag < dc_mag * 0.01) or (mag < 1e-9)
    return {'period': round(N / best, 3), 'mag': round(mag, 4), 'k': best,
            'dc_mag': round(dc_mag, 4), 'is_flat': is_flat}

def stft(x, W=W, H=H):
    out = []
    for i in range(0, max(1, len(x) - W + 1), H):
        win = x[i:i + W]
        p = dominant_period(win)
        if p:
            out.append({'start': i, **p})
    return out

def phase_breaks(frames, min_dk=1):
    return [b['start'] for a, b in itertools.pairwise(frames)
            if abs(a['k'] - b['k']) >= min_dk]

def parseval_check(x):
    N = len(x)
    X = dft(x)
    lhs = sum(abs(c)**2 for c in X)
    rhs = N * sum(v**2 for v in x)
    return abs(lhs - rhs) < max(1e-6 * rhs, 1e-6)

def _load_session_tools():
    tools = []
    for f in sorted(SESSIONS_DIR.glob('*.jsonl'), key=lambda f: f.stat().st_mtime, reverse=True)[:1]:
        try:
            for line in f.read_text('utf-8', errors='replace').splitlines():
                if not line.strip():
                    continue
                try:
                    m = json.loads(line)
                except Exception:
                    continue
                if not isinstance(m, dict):
                    continue
                if m.get('role') == 'tool':
                    name = m.get('tool_name') or m.get('name')
                    if name:
                        tools.append(name)
                tcs = m.get('tool_calls')
                if isinstance(tcs, list):
                    for tc in tcs:
                        if isinstance(tc, dict):
                            tools.append(tc.get('name') or tc.get('tool_name') or 'unknown')
                content = m.get('content', '')
                if isinstance(content, list):
                    for c in content:
                        if isinstance(c, dict) and c.get('type') == 'tool_use':
                            tools.append(c.get('name', 'unknown'))
                        elif isinstance(c, dict) and c.get('tool_name'):
                            tools.append(c.get('tool_name'))
                elif isinstance(content, str) and 'tool_calls' in content:
                    try:
                        nested = json.loads(content)
                        if isinstance(nested, dict):
                            for tc in nested.get('tool_calls') or []:
                                if isinstance(tc, dict):
                                    tools.append(tc.get('name') or tc.get('tool_name') or 'unknown')
                    except Exception:
                        pass
        except Exception:
            pass
    return tools

def _atomic_write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(obj, indent=2) + '\n')
    os.replace(tmp, path)

def run(dry_run=False):
    tools = _load_session_tools()
    if len(tools) < 4:
        result = {'ts': int(time.time()), 'n_tools': len(tools), 'error': 'insufficient tool calls'}
        if not dry_run: _atomic_write(OUT, result)
        return result
    x, vocab = encode(tools)
    frames = stft(x)
    breaks = phase_breaks(frames)
    overall = dominant_period(x)
    result = {'ts': int(time.time()), 'n_tools': len(tools), 'vocab_size': len(vocab),
              'overall': overall, 'n_frames': len(frames), 'phase_breaks': breaks}
    if not dry_run: _atomic_write(OUT, result)
    return result

def self_test():
    # Period-3 signal: [0,1,2]*8 -> dominant period ~3
    x_p3 = [float(i % 3) for i in range(24)]
    p = dominant_period(x_p3)
    assert p is not None and abs(p['period'] - 3.0) < 1.0, f"Period not ~3: {p}"
    assert p['k'] > 0

    # Constant [0]*16: DC dominates, is_flat=True
    x_const = [0.0] * 16
    # All zero: X[k]=0 for all k. Handle gracefully.
    p_const = dominant_period(x_const)
    # All magnitudes are 0 or equal; is_flat should be True
    assert p_const is None or p_const['is_flat'], f"Constant should be flat: {p_const}"

    # Phase break: concat period-3 then period-2
    x_mix = [float(i % 3) for i in range(16)] + [float(i % 2) for i in range(12)]
    frames = stft(x_mix, W=8, H=2)
    breaks = phase_breaks(frames, min_dk=1)
    assert len(breaks) > 0, "No phase breaks detected in mixed signal"

    # Parseval holds
    x_test = [1.0, 2.0, 3.0, 2.0, 1.0, 0.0, -1.0, 0.0]
    assert parseval_check(x_test), "Parseval violated"

    # stft returns list of dicts with 'start' key
    frames2 = stft([float(i % 4) for i in range(16)])
    for f in frames2:
        assert 'start' in f and 'k' in f and 'period' in f

    # phase_breaks returns list of ints
    if len(frames2) >= 2:
        pb = phase_breaks(frames2)
        assert isinstance(pb, list)

    print("self-test: PASS")

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--self-test', action='store_true')
    p.add_argument('--dry-run', action='store_true')
    args = p.parse_args()
    if args.self_test: self_test(); return
    print(json.dumps(run(args.dry_run), indent=2))

if __name__ == '__main__': main()
