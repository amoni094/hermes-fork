#!/usr/bin/env python3
"""memory-term-typer.py — LLMs4OL Task A analog.

Reads concept-lattice.json, extracts terms from skill SKILL.md files and
memory stores, infers which concept-lattice TYPE each term belongs to using
trigram Jaccard similarity against existing lattice concept intents.

Usage:
  python3 memory-term-typer.py
  python3 memory-term-typer.py --self-test
"""
import os
from pathlib import Path
_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base

import argparse
import json
import re
import sys
from datetime import datetime, timezone

ASSIGN_THRESHOLD = 0.15
_TOKEN_RE = re.compile(r'[A-Za-z]{4,}')
LATTICE_NAME = 'concept-lattice.json'
OUTPUT_NAME = 'term-typer-output.json'
ALARM_NAME = 'wave22ol-term-typer-alarm.json'


def _cache_dir() -> Path:
    return _hermes_root / 'cache'


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(obj, indent=2), encoding='utf-8')
    os.replace(tmp, path)


def trigrams(s):
    s = s or ''
    n = len(s)
    if n < 3:
        return set()
    return set(s[i:i + 3] for i in range(n - 2))


def trigram_jaccard(a, b):
    A = trigrams(a)
    B = trigrams(b)
    union = A | B
    if not union:
        return 0.0
    return len(A & B) / len(union)


def _intent_text(concept) -> str:
    if not isinstance(concept, dict):
        return ''
    v = concept.get('intent', '')
    if isinstance(v, list):
        return ' '.join(str(x) for x in v)
    return str(v or '')


def load_lattice(path: Path) -> dict:
    try:
        if not path.exists():
            return {'concepts': []}
        raw = path.read_text(encoding='utf-8')
        data = json.loads(raw)
        if not isinstance(data, dict):
            return {'concepts': []}
        concepts = data.get('concepts', [])
        if not isinstance(concepts, list):
            concepts = []
        out = dict(data)
        out['concepts'] = concepts
        return out
    except json.JSONDecodeError:
        return {'concepts': []}
    except Exception:
        return {'concepts': []}


def tokens_from_text(text: str) -> list:
    return [m.group(0).lower() for m in _TOKEN_RE.finditer(text or '')]


def _parse_skill_md(text: str) -> list:
    """Description first line + trigger lines from SKILL.md."""
    chunks = []
    if not text:
        return chunks
    fm = ''
    if text.startswith('---'):
        rest = text[3:]
        end = rest.find('\n---')
        if end != -1:
            fm = rest[:end]
    if not fm:
        for line in text.splitlines():
            if line.strip():
                chunks.append(line.strip())
                break
        return chunks
    m = re.search(r'^description:\s*(.*)$', fm, re.M)
    if m:
        val = m.group(1).strip().strip('"').strip("'")
        if val in ('>', '|'):
            for ln in fm[m.end():].splitlines():
                s = ln.strip().strip('"').strip("'")
                if s:
                    chunks.append(s)
                    break
        else:
            chunks.append(val.split('\n')[0])
    tm = re.search(r'^triggers:\s*$', fm, re.M)
    if tm:
        for ln in fm[tm.end():].splitlines():
            if not ln.strip():
                continue
            stripped = ln.lstrip()
            indented = len(ln) > len(stripped)
            if indented or stripped.startswith('-'):
                item = stripped
                if item.startswith('-'):
                    item = item[1:].strip()
                item = item.strip('"').strip("'")
                if item:
                    chunks.append(item)
            else:
                break
    return chunks


def collect_terms(skills_dir: Path, memories_dir: Path) -> dict:
    """Return {term: source} unique, first source wins."""
    found = {}

    def add(term, source):
        if term and term not in found:
            found[term] = source

    try:
        if skills_dir.is_dir():
            for p in skills_dir.rglob('SKILL.md'):
                try:
                    text = p.read_text(encoding='utf-8', errors='replace')
                except Exception:
                    continue
                name = p.parent.name
                for chunk in _parse_skill_md(text):
                    for tok in tokens_from_text(chunk):
                        add(tok, 'skill:' + name)
    except Exception:
        pass
    try:
        if memories_dir.is_dir():
            for p in memories_dir.rglob('*'):
                try:
                    if not p.is_file():
                        continue
                    if p.suffix.lower() not in ('.md', '.txt', '.jsonl', '.json'):
                        continue
                    if p.stat().st_size > 2_000_000:
                        continue
                    text = p.read_text(encoding='utf-8', errors='replace')
                except Exception:
                    continue
                for line in text[:4000].splitlines()[:5]:
                    for tok in tokens_from_text(line):
                        add(tok, 'memory:' + p.name)
    except Exception:
        pass
    return found


def type_terms(term_sources: dict, concepts: list) -> dict:
    """Assign each term to the best concept intent via trigram Jaccard."""
    typed = []
    untyped = []
    concept_intents = []
    for c in concepts or []:
        intent = _intent_text(c)
        concept_intents.append(intent)
    for term, source in (term_sources or {}).items():
        best_intent = ''
        best_score = 0.0
        tnorm = (term or '').lower()
        for intent in concept_intents:
            score = trigram_jaccard(tnorm, (intent or '').lower())
            if score > 1.0:
                score = 1.0
            if score < 0.0:
                score = 0.0
            if score > best_score:
                best_score = score
                best_intent = intent
        if best_score >= ASSIGN_THRESHOLD and best_intent:
            typed.append({
                'term': term,
                'assigned_type': best_intent,
                'score': float(best_score),
                'source': source,
            })
        else:
            untyped.append(term)
    return {
        'ts': _now(),
        'typed_terms': typed,
        'untyped_terms': untyped,
        'n_typed': len(typed),
        'n_untyped': len(untyped),
    }


def run() -> int:
    cache = _cache_dir()
    lattice = load_lattice(cache / LATTICE_NAME)
    concepts = lattice.get('concepts') or []
    skills_dir = _hermes_root / 'skills'
    memories_dir = _hermes_root / 'memories'
    term_sources = collect_terms(skills_dir, memories_dir)
    result = type_terms(term_sources, concepts)
    out_path = cache / OUTPUT_NAME
    alarm_path = cache / ALARM_NAME
    try:
        _atomic_write(out_path, result)
    except Exception:
        pass
    if result.get('n_untyped', 0) > 0:
        alarm = {
            'ts': result.get('ts') or _now(),
            'alarm': 'untyped_terms',
            'n_untyped': result['n_untyped'],
            'untyped_terms': result.get('untyped_terms') or [],
        }
        try:
            _atomic_write(alarm_path, alarm)
        except Exception:
            pass
    return 0


def self_test() -> int:
    lattice = {
        'concepts': [
            {'intent': 'memory retrieval', 'support': 2, 'members': ['a']},
            {'intent': 'routing bandits', 'support': 2, 'members': ['b']},
        ]
    }
    terms = {
        'memory': 'test',
        'routing': 'test',
        'zzzzzzzzz': 'test',
    }
    result = type_terms(terms, lattice['concepts'])
    ok = result['n_typed'] >= 2 and result['n_untyped'] >= 1
    if ok:
        print('PASS')
        return 0
    print('FAIL')
    print(json.dumps(result, indent=2))
    return 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description='LLMs4OL Task A term typer')
    ap.add_argument('--self-test', action='store_true')
    args = ap.parse_args(argv)
    if args.self_test:
        return self_test()
    return run()


if __name__ == '__main__':
    sys.exit(main())
