#!/usr/bin/env python3
"""routing-hamming-audit.py — Jaccard distance over skill-description n-grams.

Near-duplicate triggers act like a degenerate codebook (min Hamming distance 0).
Flag pairs with Jaccard distance < 0.3.

Source: Lin, Error Control Coding.
"""
from __future__ import annotations
import argparse
import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path

import os
from pathlib import Path
_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base

THRESH = 0.3
TOKEN_RE = re.compile(r"[a-z0-9]+")


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


def ngrams(text: str) -> set:
    toks = TOKEN_RE.findall(text.lower())
    uni = set(toks)
    bi = {f'{toks[i]} {toks[i+1]}' for i in range(len(toks) - 1)}
    return uni | bi


def jaccard_distance(a: set, b: set) -> float:
    if not a and not b:
        return 0.0
    u = len(a | b)
    if u == 0:
        return 0.0
    return 1.0 - (len(a & b) / u)


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
        desc = parse_description(text)
        name = p.parent.name
        out.append({'name': name, 'description': desc, 'path': str(p)})
    return out


def audit(skills: list, thresh: float = THRESH) -> dict:
    grams = []
    for s in skills:
        grams.append((s['name'], ngrams(s.get('description') or '')))
    flags = []
    n = len(grams)
    for i in range(n):
        ni, gi = grams[i]
        if not gi:
            continue
        for j in range(i + 1, n):
            nj, gj = grams[j]
            if not gj:
                continue
            d = jaccard_distance(gi, gj)
            if d < thresh:
                sev = 'HIGH' if d < 0.15 else 'MED'
                flags.append({
                    'pair': [ni, nj],
                    'jaccard_distance': round(d, 6),
                    'severity': sev,
                })
    flags.sort(key=lambda x: x['jaccard_distance'])
    return {
        'ts': time.time(),
        'n_skills': n,
        'threshold': thresh,
        'n_flagged': len(flags),
        'alarm': len(flags) > 0,
        'pairs': flags[:200],
    }


def run(cache: Path | None = None, skills_root: Path | None = None) -> dict:
    cache = cache or _cache_dir()
    skills_root = skills_root or _skills_root()
    skills = load_skills(skills_root)
    result = audit(skills)
    try:
        _atomic_write_json(cache / 'routing-hamming-alarm.json', result)
    except Exception:
        pass
    return result


def self_test() -> dict:
    failures = []
    try:
        d = jaccard_distance(ngrams('hello world foo'), ngrams('hello world foo'))
        assert d == 0.0
        d2 = jaccard_distance(ngrams('alpha beta gamma'), ngrams('completely different tokens here'))
        assert d2 > 0.3
    except Exception as e:
        failures.append(f'distance: {e}')
    try:
        skills = [
            {'name': 'a', 'description': 'Use when routing among many skills. Full text beats description.'},
            {'name': 'b', 'description': 'Use when routing among many skills. Full text beats description.'},
            {'name': 'c', 'description': 'Use when studying symplectic geometry of cotangent bundles.'},
        ]
        r = audit(skills)
        pairs = {tuple(sorted(p['pair'])) for p in r['pairs']}
        assert ('a', 'b') in pairs
        assert ('a', 'c') not in pairs and ('b', 'c') not in pairs
        assert any(p['severity'] == 'HIGH' for p in r['pairs'] if set(p['pair']) == {'a', 'b'})
    except Exception as e:
        failures.append(f'flag: {e}')
    try:
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            sk = d / 'skills' / 'dup-one'
            sk.mkdir(parents=True)
            (sk / 'SKILL.md').write_text('---\nname: dup-one\ndescription: identical trigger phrase xyz\n---\n# x\n')
            sk2 = d / 'skills' / 'dup-two'
            sk2.mkdir(parents=True)
            (sk2 / 'SKILL.md').write_text('---\nname: dup-two\ndescription: identical trigger phrase xyz\n---\n# y\n')
            cache = d / 'cache'
            r = run(cache=cache, skills_root=d / 'skills')
            assert (cache / 'routing-hamming-alarm.json').exists()
            json.dumps(r)
    except Exception as e:
        failures.append(f'io: {e}')
    try:
        r = audit([])
        assert r['n_skills'] == 0
    except Exception as e:
        failures.append(f'empty: {e}')
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
