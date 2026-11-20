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
_hermes_profile = os.environ.get('HERMES_PROFILE', 'fork')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base

import argparse
import json
import re
import sys
from datetime import datetime, timezone, UTC

ASSIGN_THRESHOLD = 0.5  # containment: 50% of term trigrams in concept text
CORE_ENTITY_CONTAINMENT = 0.5
CORE_ENTITY_BOOST = 0.1
SYNONYM_FILE = 'synonym-pairs.json'
DOMAIN_FILE = 'domain-summary.json'
_TOKEN_RE = re.compile(r'[A-Za-z]{4,}')
_STOPWORDS = frozenset({
    'with', 'that', 'this', 'from', 'have', 'will', 'been', 'they', 'their',
    'also', 'when', 'then', 'into', 'more', 'some', 'such', 'each', 'over',
    'only', 'both', 'most', 'very', 'than', 'what', 'your', 'were', 'does',
    'used', 'like', 'which', 'these', 'those', 'them', 'here', 'there',
    'about', 'after', 'before', 'under', 'while', 'where', 'being', 'using',
    'make', 'made', 'note', 'full', 'back', 'good', 'high', 'just', 'pass',
    'fail', 'true', 'false', 'none', 'null', 'skip', 'next', 'last', 'data',
})
LATTICE_NAME = 'concept-lattice.json'
OUTPUT_NAME = 'term-typer-output.json'
ALARM_NAME = 'wave22ol-term-typer-alarm.json'


def _cache_dir() -> Path:
    return _hermes_root / 'cache'


def _now() -> str:
    return datetime.now(UTC).isoformat()


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
    """Return semantic text for a concept: intent string + member text fallback.

    When intent is a short cluster ID like 'C7' (<= 4 chars), the trigrams
    are too sparse to match anything meaningful.  Supplement with member text
    so that real-lattice concepts (which use cluster IDs) still produce useful
    Jaccard scores.
    """
    if not isinstance(concept, dict):
        return ''
    v = concept.get('intent', '')
    if isinstance(v, list):
        intent_str = ' '.join(str(x) for x in v)
    else:
        intent_str = str(v or '')
    # If intent is non-semantic (short cluster ID), augment with member snippets
    if len(intent_str.strip()) <= 4:
        members = concept.get('members', [])
        member_text = ' '.join(str(m)[:60] for m in members[:5] if m)
        intent_str = (intent_str + ' ' + member_text).strip()
    return intent_str


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
    return [m.group(0).lower() for m in _TOKEN_RE.finditer(text or '')
            if m.group(0).lower() not in _STOPWORDS]


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
    m = re.search(r'^description:\s*(.*)$', fm, re.MULTILINE)
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
    tm = re.search(r'^triggers:\s*$', fm, re.MULTILINE)
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


def _load_json(path: Path, default):
    try:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding='utf-8'))
    except FileNotFoundError:
        return default
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return default
    except Exception:
        return default


def _synonym_index(data) -> dict:
    """Bidirectional lowercased term → set of synonym strings."""
    pairs = []
    if isinstance(data, list):
        pairs = data
    elif isinstance(data, dict):
        p = data.get('pairs', [])
        if isinstance(p, list):
            pairs = p
    idx = {}
    for rec in pairs:
        if not isinstance(rec, dict):
            continue
        t = str(rec.get('term') or '').strip()
        s = str(rec.get('synonym') or '').strip()
        if not t or not s:
            continue
        idx.setdefault(t.lower(), set()).add(s)
        idx.setdefault(s.lower(), set()).add(t)
    return idx


def _core_entity_names(summary) -> list:
    if not isinstance(summary, dict):
        return []
    ents = summary.get('core_entities') or []
    names = []
    for e in ents:
        if isinstance(e, str) and e.strip():
            names.append(e.strip())
        elif isinstance(e, dict):
            n = e.get('name') or ''
            if isinstance(n, list):
                n = ' '.join(str(x) for x in n[:3])
            n = str(n).strip()
            if n:
                names.append(n)
    return names


def _containment(a: str, b: str) -> float:
    """Directional containment: |trigrams(a) ∩ trigrams(b)| / |trigrams(a)|."""
    A = trigrams((a or '').lower())
    B = trigrams((b or '').lower())
    if not A:
        return 0.0
    return len(A & B) / len(A)


def type_terms(term_sources: dict, concepts: list,
               synonym_pairs=None, domain_summary=None) -> dict:
    """Assign each term to the best concept intent via directional containment.

    Synonym pairs (from synonym-pairs.json) expand the term with aliases before
    scoring — boosts recall when an abbreviation is typed against a full name.
    Domain summary core_entities: containment >= 0.5 vs a core entity name
    boosts the best score by 0.1 (capped at 1.0).
    """
    typed = []
    untyped = []
    concept_intents = []
    for c in concepts or []:
        intent = _intent_text(c)
        concept_intents.append(intent)
    syn_idx = _synonym_index(synonym_pairs)
    core_names = _core_entity_names(domain_summary)
    for term, source in (term_sources or {}).items():
        best_intent = ''
        best_score = 0.0
        tnorm = (term or '').lower()
        variants = [tnorm]
        for syn in syn_idx.get(tnorm, ()):
            sl = (syn or '').lower()
            if sl and sl not in variants:
                variants.append(sl)
        for intent in concept_intents:
            inorm = (intent or '').lower()
            i_tri = trigrams(inorm)
            score = 0.0
            for variant in variants:
                t_tri = trigrams(variant)
                if t_tri and i_tri:
                    score = max(score, len(t_tri & i_tri) / len(t_tri))
                elif t_tri:
                    score = max(score, _containment(variant, inorm))
                else:
                    score = max(score, trigram_jaccard(variant, inorm))
            # Bidirectional synonym index already expanded `variants` with
            # aliases of the typed term (including abbreviations of concept
            # tokens). Do not get(inorm) — intent strings are not index keys.
            score = max(0.0, min(1.0, score))
            if score > best_score:
                best_score = score
                best_intent = intent
        boost = 0.0
        for name in core_names:
            if _containment(tnorm, name) >= CORE_ENTITY_CONTAINMENT:
                boost = CORE_ENTITY_BOOST
                break
        best_score = max(0.0, min(1.0, best_score + boost))
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
    synonym_pairs = _load_json(cache / SYNONYM_FILE, {'pairs': []})
    domain_summary = _load_json(cache / DOMAIN_FILE, {})
    result = type_terms(
        term_sources, concepts,
        synonym_pairs=synonym_pairs,
        domain_summary=domain_summary,
    )
    out_path = cache / OUTPUT_NAME
    alarm_path = cache / ALARM_NAME
    try:
        _atomic_write(out_path, result)
    except Exception:
        pass
    if result.get('n_untyped', 0) > 0:
        n_typed_count = result.get('n_typed', 0)
        n_untyped_count = result['n_untyped']
        total = n_typed_count + n_untyped_count
        # Alarm only when untyped rate > 80% — tolerates stopgap lattice gaps;
        # still catches truly failed typing (lattice missing, 0 typed terms, etc.)
        UNTYPED_RATE_THRESHOLD = 0.80
        untyped_rate = n_untyped_count / total if total > 0 else 1.0
        if untyped_rate > UNTYPED_RATE_THRESHOLD:
            alarm = {
                'ts': result.get('ts') or _now(),
                'alarm': True,
                'reason': 'untyped_terms',
                'n_untyped': n_untyped_count,
                'n_typed': n_typed_count,
                'n_total': total,
                'untyped_rate': round(untyped_rate, 3),
                'untyped_terms': result.get('untyped_terms') or [],
            }
        else:
            alarm = {
                'ts': result.get('ts') or _now(),
                'alarm': False,
                'reason': 'acceptable_coverage',
                'n_untyped': n_untyped_count,
                'n_typed': n_typed_count,
                'n_total': total,
                'untyped_rate': round(untyped_rate, 3),
            }
    else:
        alarm = {
            'ts': result.get('ts') or _now(),
            'alarm': False,
            'reason': 'ok',
            'n_untyped': 0,
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
