#!/usr/bin/env python3
"""memory-taxonomy-discover.py — LLMs4OL Task B analog.

Discovers missing is-a (subsumption) candidate edges between concept-lattice
nodes via FCA subset and intent trigram-Jaccard.

Usage:
  python3 memory-taxonomy-discover.py
  python3 memory-taxonomy-discover.py --self-test
"""
import os
from pathlib import Path
_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base

import argparse
import json
import sys
from datetime import datetime, timezone

JACCARD_THRESHOLD = 0.4
SUBSET_CONFIDENCE = 0.9
LATTICE_NAME = 'concept-lattice.json'
OUTPUT_NAME = 'taxonomy-candidates.json'
ALARM_NAME = 'wave22ol-taxonomy-alarm.json'


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
    """Return semantic text for a concept: intent string + member text fallback.

    When intent is a cluster ID like 'C7' (<= 4 chars), supplement with member
    text snippets to produce usable trigrams for Jaccard comparison.
    """
    if not isinstance(concept, dict):
        return ''
    v = concept.get('intent', '')
    if isinstance(v, list):
        intent_str = ' '.join(str(x) for x in v)
    else:
        intent_str = str(v or '')
    if len(intent_str.strip()) <= 4:
        members = concept.get('members', [])
        member_text = ' '.join(str(m)[:60] for m in members[:5] if m)
        intent_str = (intent_str + ' ' + member_text).strip()
    return intent_str


def _members(concept) -> set:
    if not isinstance(concept, dict):
        return set()
    m = concept.get('members', [])
    if not isinstance(m, list):
        return set()
    out = set()
    for x in m:
        try:
            out.add(str(x))
        except Exception:
            continue
    return out


def load_lattice(path: Path) -> dict:
    try:
        if not path.exists():
            return {'concepts': []}
        data = json.loads(path.read_text(encoding='utf-8'))
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


def has_cycle(candidates) -> bool:
    adj = {}
    for c in candidates or []:
        sub = c.get('sub')
        sup = c.get('super')
        if sub is None or sup is None:
            continue
        adj.setdefault(sub, []).append(sup)
    visited = set()
    in_stack = set()

    def dfs(node) -> bool:
        visited.add(node)
        in_stack.add(node)
        for nxt in adj.get(node, []):
            if nxt not in visited:
                if dfs(nxt):
                    return True
            elif nxt in in_stack:
                return True
        in_stack.discard(node)
        return False

    nodes = set(adj)
    for vs in adj.values():
        nodes.update(vs)
    for n in nodes:
        if n not in visited:
            if dfs(n):
                return True
    return False


def discover_taxonomy(concepts) -> dict:
    concepts = concepts or []
    raw = []
    n = len(concepts)
    for i in range(n):
        a = concepts[i]
        intent_a = _intent_text(a)
        mem_a = _members(a)
        for j in range(n):
            if i == j:
                continue
            b = concepts[j]
            intent_b = _intent_text(b)
            mem_b = _members(b)
            if mem_a and mem_a < mem_b:
                raw.append({
                    'sub': intent_a,
                    'super': intent_b,
                    'relation': 'is-a',
                    'confidence': float(SUBSET_CONFIDENCE),
                    'reason': 'subset',
                })
            jac = trigram_jaccard(intent_a, intent_b)
            if jac > 1.0:
                jac = 1.0
            if jac < 0.0:
                jac = 0.0
            if jac >= JACCARD_THRESHOLD:
                # Symmetric similarity: one directed edge (lexicographic) to
                # avoid trivial 2-cycles. Prefer subset direction when present.
                if intent_a <= intent_b:
                    raw.append({
                        'sub': intent_a,
                        'super': intent_b,
                        'relation': 'is-a',
                        'confidence': float(jac),
                        'reason': 'jaccard',
                    })
    # Deduplicate on (sub, super); keep highest confidence (subset 0.9 wins ties vs lower jaccard)
    best = {}
    for c in raw:
        key = (c['sub'], c['super'])
        prev = best.get(key)
        if prev is None or float(c['confidence']) > float(prev['confidence']):
            best[key] = c
    candidates = list(best.values())
    cyc = has_cycle(candidates)
    return {
        'ts': _now(),
        'candidates': candidates,
        'n_candidates': len(candidates),
        'cycle_detected': bool(cyc),
    }


def run() -> int:
    cache = _cache_dir()
    lattice = load_lattice(cache / LATTICE_NAME)
    concepts = lattice.get('concepts') or []
    result = discover_taxonomy(concepts)
    out_path = cache / OUTPUT_NAME
    alarm_path = cache / ALARM_NAME
    try:
        _atomic_write(out_path, result)
    except Exception:
        pass
    if result.get('n_candidates', 0) > 0:
        alarm = {
            'ts': result.get('ts') or _now(),
            'alarm': 'taxonomy_candidates',
            'n_candidates': result['n_candidates'],
            'cycle_detected': result.get('cycle_detected', False),
        }
        try:
            _atomic_write(alarm_path, alarm)
        except Exception:
            pass
    return 0


def self_test() -> int:
    lattice = {
        'concepts': [
            {'intent': 'memory retrieval', 'support': 2, 'members': ['alpha', 'beta']},
            {'intent': 'memory store', 'support': 3, 'members': ['alpha', 'beta', 'gamma']},
            {'intent': 'memory bandits', 'support': 1, 'members': ['delta']},
        ]
    }
    result = discover_taxonomy(lattice['concepts'])
    ok = result['n_candidates'] >= 1 and result['cycle_detected'] is False
    if ok:
        print('PASS')
        return 0
    print('FAIL')
    print(json.dumps(result, indent=2))
    return 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description='LLMs4OL Task B taxonomy discovery')
    ap.add_argument('--self-test', action='store_true')
    args = ap.parse_args(argv)
    if args.self_test:
        return self_test()
    return run()


if __name__ == '__main__':
    sys.exit(main())
