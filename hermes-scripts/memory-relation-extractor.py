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
_hermes_profile = os.environ.get('HERMES_PROFILE', 'fork')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base

import argparse
import json
import random
import re
import sys
from collections import Counter
from datetime import datetime, timezone, UTC

CONFIDENCE = 0.7
JACCARD_RELATED = 0.3
SUBSUMED_CONFIDENCE = 0.85
OVERLAP_CONCEPT_CAP = 500
OVERLAP_PAIR_SAMPLE = 500
LATTICE_NAME = 'concept-lattice.json'
TAXONOMY_NAME = 'taxonomy-candidates.json'
STOPWORDS = {
    'the', 'and', 'for', 'with', 'from', 'into', 'that', 'this',
    'when', 'then', 'will', 'have', 'been', 'they', 'their', 'also',
}
RELATION_TYPES = (
    'uses', 'requires', 'supersedes', 'conflicts_with', 'extends',
    'implements', 'delegates_to', 'reads_from', 'writes_to',
    'related_to', 'subsumed_by',
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
    return datetime.now(UTC).isoformat()


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
    out = {r: int(c.get(r, 0)) for r in RELATION_TYPES}
    for r, n in c.items():
        if r not in out:
            out[str(r)] = int(n)
    return out


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


def load_lattice(path: Path) -> dict:
    data = _load_json(path, {'concepts': []})
    if not isinstance(data, dict):
        return {'concepts': []}
    concepts = data.get('concepts', [])
    if not isinstance(concepts, list):
        concepts = []
    out = dict(data)
    out['concepts'] = concepts
    return out


def _intent_text(concept) -> str:
    if not isinstance(concept, dict):
        return ''
    v = concept.get('intent', '')
    if isinstance(v, list):
        intent_str = ' '.join(str(x) for x in v)
    else:
        intent_str = str(v or '')
    if len(intent_str.strip()) <= 4:
        members = concept.get('members', [])
        if isinstance(members, list):
            member_text = ' '.join(str(m)[:60] for m in members[:5] if m)
            intent_str = (intent_str + ' ' + member_text).strip()
    return intent_str


def _semantic_members(concept) -> set:
    """Member strings usable for Jaccard. Skip cluster IDs (<=4 chars)."""
    if not isinstance(concept, dict):
        return set()
    m = concept.get('members', [])
    if not isinstance(m, list):
        return set()
    out = set()
    for x in m:
        try:
            s = str(x).strip()
        except Exception:
            continue
        if len(s) > 4:
            out.add(s)
    return out


def member_jaccard(a: set, b: set) -> float:
    """|A ∩ B| / |A ∪ B|. Empty union → 0.0."""
    if not a or not b:
        return 0.0
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


def _isa_pairs(taxonomy) -> set:
    """Existing is-a (sub, super) from taxonomy-candidates.json."""
    pairs = set()
    items = []
    if isinstance(taxonomy, dict):
        cand = taxonomy.get('candidates') or taxonomy.get('edges') or []
        if isinstance(cand, list):
            items = cand
    elif isinstance(taxonomy, list):
        items = taxonomy
    for item in items:
        if not isinstance(item, dict):
            continue
        sub = item.get('sub') or item.get('child') or item.get('subject')
        sup = item.get('super') or item.get('parent') or item.get('object')
        if sub is None or sup is None:
            continue
        s, t = str(sub).strip(), str(sup).strip()
        if s and t:
            pairs.add((s, t))
    return pairs


def _pair_indices(n: int, rng: random.Random) -> list:
    """Unordered pairs (i < j). If n > 500 concepts, sample 500 random pairs."""
    if n <= 1:
        return []
    if n <= OVERLAP_CONCEPT_CAP:
        return [(i, j) for i in range(n) for j in range(i + 1, n)]
    seen = set()
    pairs = []
    attempts = 0
    limit = OVERLAP_PAIR_SAMPLE * 40
    while len(pairs) < OVERLAP_PAIR_SAMPLE and attempts < limit:
        attempts += 1
        i = rng.randrange(n)
        j = rng.randrange(n)
        if i == j:
            continue
        if i > j:
            i, j = j, i
        if (i, j) in seen:
            continue
        seen.add((i, j))
        pairs.append((i, j))
    return pairs


def extract_member_overlap(concepts: list, isa_pairs: set | None = None,
                           rng: random.Random | None = None) -> list[dict]:
    """Second NRE pass: Jaccard member-overlap → related_to / subsumed_by."""
    triples: list[dict] = []
    concepts = [c for c in (concepts or []) if isinstance(c, dict)]
    n = len(concepts)
    if n <= 1:
        return triples
    isa_pairs = isa_pairs or set()
    rng = rng or random.Random(22)
    member_sets = [_semantic_members(c) for c in concepts]
    intents = [_intent_text(c) for c in concepts]
    for i, j in _pair_indices(n, rng):
        a, b = member_sets[i], member_sets[j]
        if not a or not b:
            continue
        ia, ib = intents[i], intents[j]
        if not ia or not ib or ia == ib:
            continue
        jac = member_jaccard(a, b)
        jac = max(0.0, min(1.0, jac))
        if jac > JACCARD_RELATED:
            triples.append({
                'subject': ia,
                'relation': 'related_to',
                'object': ib,
                'source': 'member-overlap',
                'confidence': float(jac),
            })
        # strict subset → subsumed_by, skip if taxonomy already has is-a
        if a < b and (ia, ib) not in isa_pairs:
            triples.append({
                'subject': ia,
                'relation': 'subsumed_by',
                'object': ib,
                'source': 'member-overlap',
                'confidence': float(SUBSUMED_CONFIDENCE),
            })
        if b < a and (ib, ia) not in isa_pairs:
            triples.append({
                'subject': ib,
                'relation': 'subsumed_by',
                'object': ia,
                'source': 'member-overlap',
                'confidence': float(SUBSUMED_CONFIDENCE),
            })
    return triples


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
    _atomic_write_json(cache / 'wave22ol-relation-alarm.json', {
        'ts': payload.get('ts') or _now_iso(),
        'alarm': False,
        'kind': 'informational',
        'n_triples': n,
        'message': f'NRE extracted {n} relation triples (informational)',
    })


def run(skills_root: Path | None = None, cache: Path | None = None) -> dict:
    try:
        cache = cache or _cache_dir()
        triples = extract_from_skills(skills_root)
        lattice = load_lattice(cache / LATTICE_NAME)
        taxonomy = _load_json(cache / TAXONOMY_NAME, {})
        overlap = extract_member_overlap(
            lattice.get('concepts') or [],
            isa_pairs=_isa_pairs(taxonomy),
        )
        # Append overlap triples; do not drop regex NRE triples.
        payload = build_output(list(triples) + list(overlap))
        write_outputs(payload, cache=cache)
        return payload
    except FileNotFoundError:
        payload = build_output([])
        try:
            write_outputs(payload, cache=cache)
        except Exception:
            pass
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
    # member-overlap Jaccard is |∩|/|∪|, not |∩|/min
    a = {'alpha-skill', 'beta-skill', 'gamma-skill'}
    b = {'alpha-skill', 'beta-skill'}
    jac = member_jaccard(a, b)
    if abs(jac - (2 / 3)) > 1e-9:
        ok = False
    if member_jaccard(set(), a) != 0.0:
        ok = False
    concepts = [
        {'intent': 'group-a', 'members': ['alpha-skill', 'beta-skill', 'gamma-skill']},
        {'intent': 'group-b', 'members': ['alpha-skill', 'beta-skill']},
        {'intent': 'ids-only', 'members': ['C1', 'C2', 'ab']},
    ]
    ov = extract_member_overlap(concepts, isa_pairs=set(), rng=random.Random(0))
    rels = {(t['subject'], t['relation'], t['object']) for t in ov}
    if ('group-b', 'subsumed_by', 'group-a') not in rels:
        ok = False
    if any(t['subject'] == 'ids-only' or t['object'] == 'ids-only' for t in ov):
        ok = False
    # skip subsumed_by when taxonomy already has is-a
    ov2 = extract_member_overlap(
        concepts[:2], isa_pairs={('group-b', 'group-a')}, rng=random.Random(0)
    )
    if any(t['relation'] == 'subsumed_by' for t in ov2):
        ok = False
    missing = load_lattice(Path('/nonexistent/concept-lattice.json'))
    if missing.get('concepts') != []:
        ok = False
    if ok:
        print('PASS')
        return 0
    print(f'FAIL n_triples={n} triples={triples} overlap={ov} jac={jac}')
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
