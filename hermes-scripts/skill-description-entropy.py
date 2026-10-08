#!/usr/bin/env python3
"""skill-description-entropy.py — character-level entropy of skill descriptions.

H = -sum p(c) log2 p(c). H<2.5 uninformative; H<1.5 CRITICAL.

Source: Manning, Raghavan, Schutze — Introduction to Information Retrieval.
"""
from __future__ import annotations
import argparse
import json
import math
import os
import re
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path

import os
from pathlib import Path
_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base

LOW = 2.5
CRITICAL = 1.5


def _cache_dir() -> Path:
    override = os.environ.get('HERMES_CACHE_DIR', '').strip()
    p = Path(override) if override else (_hermes_root / 'cache')
    try:
        p.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return p


def _skills_root() -> Path:
    override = os.environ.get('HERMES_SKILLS_DIR', '').strip()
    return Path(override) if override else (_hermes_root / 'skills')


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


def parse_description(text: str) -> str:
    if not text.startswith('---'):
        return ''
    parts = text.split('---', 2)
    if len(parts) < 3:
        return ''
    fm = parts[1]
    desc = []
    in_desc = False
    for raw in fm.splitlines():
        line = raw.rstrip()
        if line.startswith('description:'):
            rest = line.split(':', 1)[1].strip().strip('"').strip("'")
            if rest:
                desc.append(rest)
                in_desc = False
            else:
                in_desc = True
            continue
        if in_desc:
            if line.startswith(' ') or line.startswith('\t') or line.startswith('- '):
                desc.append(line.strip().lstrip('- ').strip('"').strip("'"))
            else:
                in_desc = False
    return ' '.join(desc)


def char_entropy(s: str) -> float:
    if not s:
        return 0.0
    n = len(s)
    c = Counter(s)
    h = 0.0
    for k in c.values():
        p = k / n
        h -= p * math.log2(p)
    return h


def load_skills(skills_root: Path) -> list:
    out = []
    try:
        paths = list(skills_root.glob('*/SKILL.md')) + list(skills_root.glob('*/*/SKILL.md'))
    except Exception:
        paths = []
    for p in paths:
        try:
            text = p.read_text(errors='replace')
        except Exception:
            continue
        out.append({'name': p.parent.name, 'description': parse_description(text)})
    return out


def audit(skills: list) -> dict:
    alarms = []
    rows = []
    for s in skills:
        desc = s.get('description') or ''
        h = char_entropy(desc)
        level = 'ok'
        if h < CRITICAL:
            level = 'CRITICAL'
        elif h < LOW:
            level = 'LOW'
        rec = {'skill': s.get('name'), 'H': round(h, 4), 'n_chars': len(desc), 'level': level}
        rows.append(rec)
        if level != 'ok':
            alarms.append(rec)
    rows.sort(key=lambda r: r['H'])
    return {
        'ts': time.time(),
        'n_skills': len(skills),
        'low_threshold': LOW,
        'critical_threshold': CRITICAL,
        'n_alarm': len(alarms),
        'alarm': len(alarms) > 0,
        'alarms': alarms,
        'lowest': rows[:15],
    }


def run(cache: Path | None = None, skills_root: Path | None = None) -> dict:
    cache = cache or _cache_dir()
    skills_root = skills_root or _skills_root()
    result = audit(load_skills(skills_root))
    try:
        _atomic_write_json(cache / 'skill-description-entropy.json', result)
    except Exception:
        pass
    return result


def self_test() -> dict:
    failures = []
    try:
        assert char_entropy('aaaaaaa') < 1.5
        # english-ish
        s = 'Use when studying algebraic topology and persistent homology of filtrations.'
        assert char_entropy(s) > 2.5
        assert abs(char_entropy('')) == 0.0
    except Exception as e:
        failures.append(f'H: {e}')
    try:
        r = audit([
            {'name': 'const', 'description': 'aaaaaaaaaaaaaaaa'},
            {'name': 'ok', 'description': 'Use when applying geometric deep learning on manifolds and graphs.'},
        ])
        levels = {a['skill']: a['level'] for a in r['alarms']}
        assert levels.get('const') == 'CRITICAL'
        assert 'ok' not in levels
    except Exception as e:
        failures.append(f'alarm: {e}')
    try:
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            sk = d / 'skills' / 'rep'
            sk.mkdir(parents=True)
            (sk / 'SKILL.md').write_text('---\nname: rep\ndescription: xxxxxxxxxxxxxxxxxxxxx\n---\n')
            r = run(cache=d / 'cache', skills_root=d / 'skills')
            assert (d / 'cache' / 'skill-description-entropy.json').exists()
            json.dumps(r)
    except Exception as e:
        failures.append(f'io: {e}')
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
