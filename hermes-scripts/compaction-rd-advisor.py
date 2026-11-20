#!/usr/bin/env python3
"""compaction-rd-advisor.py — Pareto pick from eval R-D curve.

Reads cache/eval-compaction-results.json (also cache/scratch/).
Recommends the non-dominated policy with lowest D, then highest rate.
Oracle-summary arms are excluded (cheat: needles injected into summary).

Usage:
  python3 compaction-rd-advisor.py
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone, UTC
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', 'fork')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base
CACHE = _hermes_root / 'cache'
OUT = CACHE / 'compaction-rd-advice.json'


def _atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    os.replace(tmp, path)


def _load_eval() -> dict:
    for p in (
        CACHE / 'eval-compaction-results.json',
        CACHE / 'scratch' / 'eval-compaction-results.json',
        _hermes_base / 'cache' / 'eval-compaction-results.json',
    ):
        try:
            obj = json.loads(p.read_text(encoding='utf-8'))
            if isinstance(obj, dict):
                obj['_source'] = str(p)
                return obj
        except (OSError, json.JSONDecodeError):
            continue
    return {}


def _points(curve) -> list:
    pts = []
    if not isinstance(curve, list):
        return pts
    for item in curve:
        if not isinstance(item, dict):
            continue
        if item.get('oracle_summary') is True:
            continue
        name = item.get('policy') or item.get('name')
        if not name:
            continue
        d = item.get('D', item.get('distortion'))
        rate = item.get('rate')
        try:
            d = float(d)
            rate = float(rate)
        except (TypeError, ValueError):
            continue
        pts.append({'policy': str(name), 'D': d, 'rate': rate})
    return pts


def _pareto(pts: list) -> list:
    nd = []
    for a in pts:
        dominated = False
        for b in pts:
            if b is a:
                continue
            le_d = b['D'] <= a['D']
            ge_r = b['rate'] >= a['rate']
            strict = (b['D'] < a['D']) or (b['rate'] > a['rate'])
            if le_d and ge_r and strict:
                dominated = True
                break
        if not dominated:
            nd.append(a)
    return nd


def advise() -> dict:
    src = _load_eval()
    pts = _points(src.get('rd_curve'))
    nd = _pareto(pts)
    # lowest D, then highest rate
    nd.sort(key=lambda p: (p['D'], -p['rate']))
    ts = datetime.now(UTC).isoformat()
    if not nd:
        out = {
            'recommended': None,
            'D': None,
            'rate': None,
            'aggressiveness': None,
            'rationale': 'no rd_curve points (non-oracle) in eval-compaction-results.json',
            'ts': ts,
            'n_points': 0,
            'source': src.get('_source'),
        }
        return out
    pick = nd[0]
    rate = pick['rate']
    out = {
        'recommended': pick['policy'],
        'D': pick['D'],
        'rate': rate,
        'aggressiveness': round(1.0 - rate, 6),
        'rationale': (
            f'Pareto-dominant among {len(pts)} non-oracle arms '
            f'({len(nd)} non-dominated): lowest D then highest rate. '
            f"Picked {pick['policy']} D={pick['D']:.6f} rate={pick['rate']:.6f}."
        ),
        'ts': ts,
        'n_points': len(pts),
        'n_nondominated': len(nd),
        'source': src.get('_source'),
    }
    return out


def main() -> int:
    out = advise()
    try:
        _atomic_write(OUT, out)
        out['output'] = str(OUT)
    except OSError as exc:
        out['write_error'] = str(exc)
    print(json.dumps(out))
    rec = out.get('recommended')
    print(f"rd-advisor: recommended={rec} D={out.get('D')} rate={out.get('rate')}", file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
