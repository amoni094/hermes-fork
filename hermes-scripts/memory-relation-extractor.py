#!/usr/bin/env python3
"""memory-relation-extractor.py — LLMs4OL Task C analog (Non-Taxonomic Relation Extraction).

Regex NRE over skill SKILL.md files. Nine relation types, confidence 0.7,
dedup on (subject, relation, object). Stdlib only.

Usage:
  python3 memory-relation-extractor.py
  python3 memory-relation-extractor.py --self-test
"""
from __future__ import annotations

import os
from pathlib import Path
_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base

import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone

CONFIDENCE = 0.7
STOPWORDS = {
    'the', 'and', 'for', 'with', 'from', 'into', 'that', 'this',
    'when', 'then', 'will', 'have', 'been', 'they', 'their', 'also',
}
RELATION_TYPES = (
    'uses', 'requires', 'supersedes', 'conflicts_with', 'extends',
    'implements', 'delegates_to', 'reads_from', 'writes_to',
)

# (regex, relation, subject_group, object_group)
_PATTERNS = (
    (re.compile(r'(\b[A-Za-z][\w.-]+)\.py\b.*?\b(uses|calls|invokes)\b.*?\b([A-Za-z][\w.-]+)'),
     'uses', 1, 3),
    (re.compile(r'\b([A-Za-z][\w-]+)\s+requires\s+([A-Za-z][\w-]+)'),
     'requires', 1, 2),
    (re.compile(r'\b([A-Za-z][\w-]+)\s+supersedes\s+([A-Za-z][\w-]+)'),
     'supersedes', 1, 2),
    (re.compile(r'\b([A-Za-z][\w-]+)\s+conflicts?\s+with\s+([A-Za-z][\w-]+)'),
     'conflicts_with', 1, 2),
    (re.compile(r'\b([A-Za-z][\w-]+)\s+extends\s+([A-Za-z][\w-]+)'),
     'extends', 1, 2),
    (re.compile(r'\b([A-Za-z][\w-]+)\s+implements\s+([A-Za-z][\w-]+)'),
     'implements', 1, 2),
    (re.compile(r'\b([A-Za-z][\w-]+)\s+delegates?\s+to\s+([A-Za-z][\w-]+)'),
     'delegates_to', 1, 2),
    (re.compile(r'\b([A-Za-z][\w-]+)\s+reads?\s+from\s+([A-Za-z][\w-]+)'),
     'reads_from', 1, 2),
    (re.compile(r'\b([A-Za-z][\w-]+)\s+writes?\s+to\s+([A-Za-z][\w-]+)'),
     'writes_to', 1, 2),
)


def _cache_dir() -> Path:
    override = os.environ.get('HERMES_CACHE_DIR', '').strip()
    p = Path(override) if override else (_hermes_root / 'cache')
    try:
        p.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return p


def _skills_dir() -> Path:
    override = os.environ.get('HERMES_SKILLS_DIR', '').strip()
    return Path(override) if override else (_hermes_root / 'skills')


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_write_json(path: Path, obj) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix('.tmp')
        tmp.write_text(json.dumps(obj, indent=2) + '\n', encoding='utf-8')
        os.replace(tmp, path)
    except Exception:
        try:
            tmp = path.with_suffix('.tmp')
            if tmp.exists():
                tmp.unlink()
        except Exception:
            pass


def _ok_token(tok: str) -> bool:
    if not tok or len(tok) < 3:
        return False
    return tok.lower() not in STOPWORDS


def extract_from_text(text: str, source: str = '') -> list[dict]:
    """Apply NRE patterns to each line. Returns raw triples (may contain dups)."""
    triples: list[dict] = []
    try:
        lines = (text or '').splitlines() or [text or '']
    except Exception:
        return triples
    for line in lines:
        if not line:
            continue
        for cre, rel, gi, gj in _PATTERNS:
            try:
                for m in cre.finditer(line):
                    subj = (m.group(gi) or '').strip()
                    obj = (m.group(gj) or '').strip()
                    if _ok_token(subj) and _ok_token(obj) and subj.lower() != obj.lower():
                        triples.append({
                            'subject': subj,
                            'relation': rel,
                            'object': obj,
                            'source': source,
                            'confidence': CONFIDENCE,
                        })
            except Exception:
                continue
    return triples


def dedupe(triples: list[dict]) -> list[dict]:
    seen: set[tuple] = set()
    out: list[dict] = []
    for t in triples:
        key = (t.get('subject'), t.get('relation'), t.get('object'))
        if key in seen:
            continue
        seen.add(key)
        out.append(t)
    return out


def relation_counts(triples: list[dict]) -> dict:
    c = Counter(t.get('relation') for t in triples)
    return {r: int(c.get(r, 0)) for r in RELATION_TYPES}


def iter_skill_md(skills_root: Path | None = None) -> list[Path]:
    root = skills_root if skills_root is not None else _skills_dir()
    found: list[Path] = []
    try:
        if not root.exists() or not root.is_dir():
            return found
        for p in root.rglob('SKILL.md'):
            try:
                if p.is_file():
                    found.append(p)
            except Exception:
                continue
    except Exception:
        return found
    return found


def extract_from_skills(skills_root: Path | None = None) -> list[dict]:
    root = skills_root if skills_root is not None else _skills_dir()
    raw: list[dict] = []
    for path in iter_skill_md(root):
        try:
            text = path.read_text(encoding='utf-8', errors='replace')
        except Exception:
            continue
        try:
            rel = str(path.relative_to(root))
        except Exception:
            rel = path.name
        raw.extend(extract_from_text(text, source=rel))
    return dedupe(raw)


def build_output(triples: list[dict]) -> dict:
    triples = dedupe(triples)
    return {
        'ts': _now_iso(),
        'triples': triples,
        'n_triples': len(triples),
        'relation_counts': relation_counts(triples),
    }


def write_outputs(payload: dict, cache: Path | None = None) -> None:
    cache = cache or _cache_dir()
    _atomic_write_json(cache / 'relation-triples.json', payload)
    n = int(payload.get('n_triples') or 0)
    if n > 0:
        _atomic_write_json(cache / 'wave22ol-relation-alarm.json', {
            'ts': payload.get('ts') or _now_iso(),
            'kind': 'informational',
            'n_triples': n,
            'message': f'NRE extracted {n} relation triples (informational)',
        })


def run(skills_root: Path | None = None, cache: Path | None = None) -> dict:
    try:
        triples = extract_from_skills(skills_root)
        payload = build_output(triples)
        write_outputs(payload, cache=cache)
        return payload
    except Exception:
        payload = build_output([])
        try:
            write_outputs(payload, cache=cache)
        except Exception:
            pass
        return payload


def self_test() -> int:
    mock = (
        'memory-ransac-commit.py uses memory-sprt-commit; '
        'skill-router requires concept-lattice; '
        'memory-ttl supersedes memory-old'
    )
    triples = dedupe(extract_from_text(mock, source='self-test'))
    n = len(triples)
    rels = {t['relation'] for t in triples}
    ok = n >= 2
    # extra property checks (not required, fail closed if mock regressions)
    if 'uses' not in rels or 'requires' not in rels:
        ok = False
    if n != len({(t['subject'], t['relation'], t['object']) for t in triples}):
        ok = False
    dup = dedupe(triples + triples)
    if len(dup) != n:
        ok = False
    if ok:
        print('PASS')
        return 0
    print('FAIL n_triples=%s triples=%s' % (n, triples))
    return 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description='LLMs4OL Task C regex NRE')
    p.add_argument('--self-test', action='store_true')
    args = p.parse_args(argv)
    if args.self_test:
        return self_test()
    try:
        payload = run()
        print(json.dumps({'n_triples': payload.get('n_triples'), 'ts': payload.get('ts')}))
    except Exception:
        pass
    return 0


if __name__ == '__main__':
    sys.exit(main())
