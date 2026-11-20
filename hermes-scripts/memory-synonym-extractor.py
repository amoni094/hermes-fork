#!/usr/bin/env python3
"""memory-synonym-extractor.py — NVIDIA auto-ontology synonym pass (stdlib).

Extracts *explicit* aliases/abbreviations from SKILL.md files (not inferred):
  a) parenthetical abbreviations: word (ABBR) / word (Abbr), 2-6 letters/digits
  b) alias phrases: also known as / also called / abbreviated as / short for / a.k.a.
  c) backtick code-name aliases adjacent to a spelled-out name within 10 tokens

Writes cache/synonym-pairs.json and cache/wave22ol-synonym-alarm.json.
Missing concept-lattice.json is ignored (empty concepts). Stdlib only.
"""
from __future__ import annotations

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

MIN_LEN = 2
MAX_LEN = 40
LATTICE_NAME = 'concept-lattice.json'
OUTPUT_NAME = 'synonym-pairs.json'
ALARM_NAME = 'wave22ol-synonym-alarm.json'

STOPWORDS = frozenset({
    'the', 'and', 'for', 'with', 'from', 'into', 'that', 'this', 'when', 'then',
    'will', 'have', 'been', 'they', 'their', 'also', 'than', 'what', 'your',
    'were', 'does', 'used', 'like', 'which', 'these', 'those', 'them', 'here',
    'there', 'about', 'after', 'before', 'under', 'while', 'where', 'being',
    'using', 'make', 'made', 'note', 'full', 'back', 'good', 'high', 'just',
    'pass', 'fail', 'true', 'false', 'none', 'null', 'skip', 'next', 'last',
    'data', 'text', 'type', 'file', 'base', 'only', 'both', 'most', 'very',
    'each', 'over', 'some', 'such', 'more',
    # 2-letter English / country tokens that match paren-abbrev (IT, US, OR, IF)
    'it', 'us', 'or', 'if', 'to', 'in', 'on', 'at', 'by', 'an', 'as', 'be',
    'we', 'no', 'so', 'do', 'of', 'is', 'am', 'me', 'my', 'he', 'she',
})
ABBREV_STOP = frozenset({
    'IT', 'US', 'OR', 'IF', 'TO', 'IN', 'ON', 'AT', 'BY', 'AN', 'AS', 'BE',
    'WE', 'NO', 'SO', 'DO', 'OF', 'IS', 'AM', 'ME', 'MY', 'ID', 'OK', 'HE',
})

# word (ABBR) — ABBR is 2-6 uppercase letters/digits
_PAREN_UPPER = re.compile(
    r'\b([A-Za-z][A-Za-z0-9_-]{0,38})\s*\(([A-Z][A-Z0-9]{1,5})\)'
)
# word (Abbr) — title-case 2-6
_PAREN_TITLE = re.compile(
    r'\b([A-Za-z][A-Za-z0-9_-]{0,38})\s*\(([A-Z][a-z][A-Za-z0-9]{0,2})\)'
)
# Extra alias tokens must be Title Case so "also known as HA runs locally"
# captures HA, not the rest of the sentence. No '.' in the token class.
_ALIAS_SPAN = (
    r'[A-Za-z][A-Za-z0-9_-]{0,38}'
    r'(?:\s+[A-Z][A-Za-z0-9_-]{0,38}){0,2}'
)
_ALIAS_PHRASE = re.compile(
    r'\b([A-Za-z][A-Za-z0-9_-]{0,38})\s*(?:,\s*)?'
    r'(?i:also known as|also called|abbreviated as|a\.k\.a\.|aka)\s+'
    r'(' + _ALIAS_SPAN + r')'
)
_SHORT_FOR = re.compile(
    r'\b([A-Za-z][A-Za-z0-9_-]{0,38})\s+(?i:is\s+)?(?i:short for)\s+'
    r'(' + _ALIAS_SPAN + r')'
)
_BACKTICK = re.compile(r'`([^`\n]{2,40})`')
_IDENT = re.compile(r'^[A-Za-z][A-Za-z0-9_-]{1,39}$')
_TOKEN = re.compile(r"[A-Za-z][A-Za-z0-9_-]*")


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


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _atomic_write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(obj, indent=2) + '\n', encoding='utf-8')
    os.replace(tmp, path)


def _load_json(path: Path, default):
    try:
        if not path.exists():
            return default
        data = json.loads(path.read_text(encoding='utf-8'))
        return data
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


def _ok_term(s: str) -> bool:
    t = (s or '').strip()
    if len(t) < MIN_LEN or len(t) > MAX_LEN:
        return False
    if len(t.split()) > 3:
        return False
    if t.lower() in STOPWORDS:
        return False
    if t.upper() in ABBREV_STOP and len(t) <= 3:
        return False
    if not re.search(r'[A-Za-z]', t):
        return False
    return True


def _pair(term: str, synonym: str, source_file: str, pattern_type: str):
    term = (term or '').strip().strip('`').strip().strip('.,;:)')
    synonym = (synonym or '').strip().strip('`').strip().strip('.,;:)')
    if not _ok_term(term) or not _ok_term(synonym):
        return None
    if term.lower() == synonym.lower():
        return None
    return {
        'term': term,
        'synonym': synonym,
        'source_file': source_file,
        'pattern_type': pattern_type,
    }


def extract_paren(text: str, source: str) -> list:
    out = []
    for rx, ptype in ((_PAREN_UPPER, 'paren_abbrev'), (_PAREN_TITLE, 'paren_abbrev')):
        try:
            for m in rx.finditer(text or ''):
                # skip markdown links ](url)
                start = m.start()
                if start > 0 and (text[start - 1] in (']', '!')):
                    continue
                abbr = m.group(2)
                if abbr.upper() in ABBREV_STOP:
                    continue
                rec = _pair(m.group(1), abbr, source, ptype)
                if rec:
                    out.append(rec)
        except Exception:
            continue
    return out


def extract_alias_phrases(text: str, source: str) -> list:
    out = []
    for rx, ptype in ((_ALIAS_PHRASE, 'alias_phrase'), (_SHORT_FOR, 'alias_phrase')):
        try:
            for m in rx.finditer(text or ''):
                rec = _pair(m.group(1), m.group(2), source, ptype)
                if rec:
                    out.append(rec)
        except Exception:
            continue
    return out


def _collapse(s: str) -> str:
    return re.sub(r'[^a-z0-9]+', '', (s or '').lower())


def extract_backtick_aliases(text: str, source: str) -> list:
    """Backtick identifier ↔ spelled-out name within 10 tokens."""
    out = []
    text = text or ''
    try:
        tokens = list(_TOKEN.finditer(text))
    except Exception:
        return out
    if not tokens:
        return out
    # map char offset -> token index
    def nearest_idx(pos: int) -> int:
        best = 0
        for i, tm in enumerate(tokens):
            if tm.start() <= pos:
                best = i
            else:
                break
        return best

    try:
        bts = list(_BACKTICK.finditer(text))
    except Exception:
        return out
    for m in bts:
        ident = (m.group(1) or '').strip()
        # Identifiers only (skill names, snake/kebab) — skip math/prose backticks.
        if not ident or not _IDENT.match(ident):
            continue
        collapsed = _collapse(ident)
        if len(collapsed) < MIN_LEN:
            continue
        idx = nearest_idx(m.start())
        lo = max(0, idx - 10)
        hi = min(len(tokens), idx + 11)
        window = tokens[lo:hi]
        words = [tm.group(0) for tm in window]
        # try concatenating 2-8 consecutive window tokens
        n = len(words)
        found = None
        for i in range(n):
            acc = ''
            parts = []
            for j in range(i, min(n, i + 8)):
                parts.append(words[j])
                acc = _collapse(''.join(parts))
                if acc == collapsed and len(parts) >= 2:
                    found = ' '.join(parts)
                    break
            if found:
                break
        if found:
            rec = _pair(found, ident, source, 'code_name')
            if rec:
                out.append(rec)
    return out


def extract_from_text(text: str, source: str = '') -> list:
    recs = []
    recs.extend(extract_paren(text, source))
    recs.extend(extract_alias_phrases(text, source))
    recs.extend(extract_backtick_aliases(text, source))
    return recs


def dedupe(pairs: list) -> list:
    seen = set()
    out = []
    for p in pairs or []:
        try:
            key = ((p.get('term') or '').lower(), (p.get('synonym') or '').lower())
        except Exception:
            continue
        if not key[0] or not key[1] or key in seen:
            continue
        seen.add(key)
        out.append(p)
    return out


def iter_skill_md(skills_root: Path | None = None) -> list:
    root = skills_root if skills_root is not None else _skills_dir()
    found = []
    try:
        if not root.exists() or not root.is_dir():
            return found
        for p in root.rglob('SKILL.md'):
            try:
                if p.is_file():
                    found.append(p)
            except Exception:
                continue
    except FileNotFoundError:
        return found
    except Exception:
        return found
    return found


def extract_from_skills(skills_root: Path | None = None) -> list:
    root = skills_root if skills_root is not None else _skills_dir()
    raw = []
    for path in iter_skill_md(root):
        try:
            text = path.read_text(encoding='utf-8', errors='replace')
        except FileNotFoundError:
            continue
        except Exception:
            continue
        try:
            rel = str(path.relative_to(root))
        except Exception:
            rel = path.name
        raw.extend(extract_from_text(text, source=rel))
    return dedupe(raw)


def _pairs_list(obj) -> list:
    if isinstance(obj, list):
        return [x for x in obj if isinstance(x, dict)]
    if isinstance(obj, dict):
        p = obj.get('pairs', [])
        if isinstance(p, list):
            return [x for x in p if isinstance(x, dict)]
    return []


def diff_pairs(old, new) -> tuple:
    """Return (new_pairs, changed_pairs) vs previous run. Keys are lowercased."""
    def k(p):
        return ((p.get('term') or '').lower(), (p.get('synonym') or '').lower())
    old_map = {k(p): p for p in _pairs_list(old)}
    new_items = []
    changed = []
    for p in _pairs_list(new):
        key = k(p)
        prev = old_map.get(key)
        if prev is None:
            new_items.append(p)
        else:
            if (prev.get('source_file') != p.get('source_file')
                    or prev.get('pattern_type') != p.get('pattern_type')):
                changed.append(p)
    return new_items, changed


def build_output(pairs: list) -> dict:
    pairs = dedupe(pairs)
    return {
        'ts': _now(),
        'pairs': pairs,
        'n_pairs': len(pairs),
    }


def write_outputs(payload: dict, prev, cache: Path | None = None) -> None:
    cache = cache or _cache_dir()
    _atomic_write(cache / OUTPUT_NAME, payload)
    new_items, changed = diff_pairs(prev, payload)
    alarm = {
        'ts': payload.get('ts') or _now(),
        'alarm': bool(new_items or changed),
        'n_new': len(new_items),
        'n_changed': len(changed),
        'n_pairs': int(payload.get('n_pairs') or 0),
        'new_pairs': new_items,
        'changed_pairs': changed,
    }
    _atomic_write(cache / ALARM_NAME, alarm)


def run(skills_root: Path | None = None, cache: Path | None = None) -> dict:
    cache = cache or _cache_dir()
    try:
        # lattice optional — empty concepts if missing
        load_lattice(cache / LATTICE_NAME)
        prev = _load_json(cache / OUTPUT_NAME, {'pairs': []})
        pairs = extract_from_skills(skills_root)
        payload = build_output(pairs)
        write_outputs(payload, prev, cache=cache)
        return payload
    except FileNotFoundError:
        payload = build_output([])
        try:
            write_outputs(payload, {'pairs': []}, cache=cache)
        except Exception:
            pass
        return payload
    except Exception:
        payload = build_output([])
        try:
            write_outputs(payload, {'pairs': []}, cache=cache)
        except Exception:
            pass
        return payload


def self_test() -> int:
    mock = (
        'Hermes Agent also known as HA runs locally. '
        'NRE is short for extraction. '
        'Bandit (UCB) and Formal Concept Analysis (FCA) are used. '
        'The `memory-term-typer` memory term typer script types terms. '
        'Skip the (IT) and (US) and (OR) and (IF) abbreviations. '
        'the (AND) should drop. '
    )
    recs = dedupe(extract_from_text(mock, source='self-test'))
    types = {r['pattern_type'] for r in recs}
    keys = {(r['term'].lower(), r['synonym'].lower()) for r in recs}
    ok = True
    # paren FCA
    if not any(k[1] == 'fca' for k in keys):
        ok = False
    # stopword abbrev must not appear
    for stop in ('it', 'us', 'or', 'if'):
        if any(k[1] == stop for k in keys):
            ok = False
    # alias phrase: "Agent also known as HA" — HA only, not rest of sentence
    if not any(r['synonym'].lower() == 'ha' or r['term'].lower() == 'ha' for r in recs):
        ok = False
    if any('runs locally' in (r.get('synonym') or '').lower() for r in recs):
        ok = False
    # code name
    if 'code_name' not in types:
        ok = False
    # dedupe key is lowercased
    dedupe(recs + [{'term': 'FCA', 'synonym': 'fca', 'source_file': 'x', 'pattern_type': 't'}])
    # FCA/fca vs existing fca pair: term Formal... synonym FCA; extra pair FCA/fca different key
    # empty / missing
    assert extract_from_text('', '') == []
    assert dedupe([]) == []
    # FileNotFound lattice
    missing = load_lattice(Path('/nonexistent/concept-lattice.json'))
    if missing.get('concepts') != []:
        ok = False
    if ok:
        print(f'PASS n={len(recs)} types={sorted(types)}')
        return 0
    print(f'FAIL recs={recs}')
    return 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description='Explicit synonym extraction from SKILL.md')
    ap.add_argument('--self-test', action='store_true')
    args = ap.parse_args(argv)
    if args.self_test:
        return self_test()
    try:
        payload = run()
        print(json.dumps({'n_pairs': payload.get('n_pairs'), 'ts': payload.get('ts')}))
    except Exception:
        pass
    return 0


if __name__ == '__main__':
    sys.exit(main())
