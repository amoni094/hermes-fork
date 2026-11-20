#!/usr/bin/env python3
"""memory-domain-summary.py — NVIDIA auto-ontology domain summary injection.

Derives DomainSummary {domains, core_entities, business_rules} from
concept-lattice.json + skill category directories + SKILL.md rule lines.

Writes cache/domain-summary.json and cache/wave22ol-domain-summary-alarm.json.
Missing concept-lattice.json → empty core_entities, exit 0. Stdlib only.
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

LATTICE_NAME = 'concept-lattice.json'
OUTPUT_NAME = 'domain-summary.json'
ALARM_NAME = 'wave22ol-domain-summary-alarm.json'
RULE_CAP = 20
RULE_MAX_CHARS = 120
CORE_K = 5
_RULE_WORDS = re.compile(r'\b(must|never|always|required|forbidden)\b', re.IGNORECASE)


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


def _intent_name(concept) -> str:
    if not isinstance(concept, dict):
        return ''
    v = concept.get('intent', '')
    if isinstance(v, list):
        parts = [str(x).strip() for x in v if str(x).strip()]
        return parts[0] if parts else ''
    return str(v or '').strip()


def _intent_full(concept) -> str:
    if not isinstance(concept, dict):
        return ''
    v = concept.get('intent', '')
    if isinstance(v, list):
        return ' '.join(str(x) for x in v)
    return str(v or '')


def _n_members(concept) -> int:
    if not isinstance(concept, dict):
        return 0
    m = concept.get('members', [])
    if not isinstance(m, list):
        return 0
    return len(m)


def collect_domains(skills_root: Path) -> list:
    names = []
    try:
        if not skills_root.exists() or not skills_root.is_dir():
            return names
        for d in sorted(skills_root.iterdir()):
            try:
                if d.is_dir() and not d.name.startswith('.'):
                    names.append(d.name)
            except Exception:
                continue
    except FileNotFoundError:
        return []
    except Exception:
        return []
    # unique, stable
    seen = set()
    out = []
    for n in names:
        if n.lower() not in seen:
            seen.add(n.lower())
            out.append(n)
    return out


def collect_core_entities(concepts: list) -> list:
    ranked = []
    for c in concepts or []:
        name = _intent_name(c)
        if not name:
            continue
        ranked.append({
            'name': name[:40],
            'intent': _intent_full(c),
            'n_members': _n_members(c),
        })
    ranked.sort(key=lambda x: (-int(x['n_members']), x['name']))
    # dedupe by name, keep most populated
    seen = set()
    out = []
    for e in ranked:
        k = e['name'].lower()
        if k in seen:
            continue
        seen.add(k)
        out.append(e)
        if len(out) >= CORE_K:
            break
    return out


def collect_business_rules(skills_root: Path) -> list:
    rules = []
    seen = set()
    try:
        if not skills_root.exists() or not skills_root.is_dir():
            return rules
        paths = []
        try:
            paths = [p for p in skills_root.rglob('SKILL.md') if p.is_file()]
        except FileNotFoundError:
            return rules
        except Exception:
            return rules
        for path in paths:
            if len(rules) >= RULE_CAP:
                break
            try:
                text = path.read_text(encoding='utf-8', errors='replace')
            except FileNotFoundError:
                continue
            except Exception:
                continue
            for line in text.splitlines():
                s = line.strip()
                if not s.startswith('- '):
                    continue
                body = s[2:].strip()
                if not _RULE_WORDS.search(body):
                    continue
                truncated = body[:RULE_MAX_CHARS]
                key = truncated.lower()
                if key in seen:
                    continue
                seen.add(key)
                rules.append(truncated)
                if len(rules) >= RULE_CAP:
                    break
    except FileNotFoundError:
        return rules
    except Exception:
        return rules
    return rules[:RULE_CAP]


def _core_names(summary) -> list:
    ents = []
    if isinstance(summary, dict):
        ents = summary.get('core_entities') or []
    elif isinstance(summary, list):
        ents = summary
    names = []
    for e in ents:
        if isinstance(e, str):
            names.append(e.lower())
        elif isinstance(e, dict):
            names.append(str(e.get('name') or '').lower())
    return names


def build_summary(concepts, skills_root: Path) -> dict:
    return {
        'ts': _now(),
        'domains': collect_domains(skills_root),
        'core_entities': collect_core_entities(concepts),
        'business_rules': collect_business_rules(skills_root),
    }


def write_outputs(payload: dict, prev, cache: Path | None = None) -> None:
    cache = cache or _cache_dir()
    _atomic_write(cache / OUTPUT_NAME, payload)
    old_names = _core_names(prev)
    new_names = _core_names(payload)
    old_set, new_set = set(old_names), set(new_names)
    if not old_names:
        added, removed = [], []
        changed = False
    else:
        added = sorted(new_set - old_set)
        removed = sorted(old_set - new_set)
        changed = bool(added or removed)
    alarm = {
        'ts': payload.get('ts') or _now(),
        'alarm': changed,
        'core_entities_changed': changed,
        'added': added,
        'removed': removed,
        'new_items': added,
    }
    _atomic_write(cache / ALARM_NAME, alarm)


def run(skills_root: Path | None = None, cache: Path | None = None) -> dict:
    cache = cache or _cache_dir()
    skills_root = skills_root if skills_root is not None else _skills_dir()
    try:
        lattice = load_lattice(cache / LATTICE_NAME)
        concepts = lattice.get('concepts') or []
        prev = _load_json(cache / OUTPUT_NAME, {})
        payload = build_summary(concepts, skills_root)
        write_outputs(payload, prev, cache=cache)
        return payload
    except FileNotFoundError:
        payload = build_summary([], skills_root)
        try:
            write_outputs(payload, {}, cache=cache)
        except Exception:
            pass
        return payload
    except Exception:
        payload = {
            'ts': _now(),
            'domains': [],
            'core_entities': [],
            'business_rules': [],
        }
        try:
            write_outputs(payload, {}, cache=cache)
        except Exception:
            pass
        return payload


def self_test() -> int:
    import tempfile
    concepts = [
        {'intent': ['alpha', 'beta'], 'members': list('123456')},
        {'intent': ['gamma'], 'members': list('12')},
        {'intent': ['delta'], 'members': list('1234')},
        {'intent': ['epsilon'], 'members': list('123')},
        {'intent': ['zeta'], 'members': list('12345')},
        {'intent': ['eta'], 'members': ['x']},
    ]
    core = collect_core_entities(concepts)
    ok = len(core) == 5 and core[0]['name'] == 'alpha'
    # 20-rule cap + 120 truncation
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        skill = root / 'cat' / 's' 
        skill.mkdir(parents=True)
        lines = []
        for i in range(30):
            lines.append('- must always required never forbidden rule number {} {}'.format(i, 'x' * 200))
        (skill / 'SKILL.md').write_text('\n'.join(lines), encoding='utf-8')
        rules = collect_business_rules(root)
        if len(rules) != 20:
            ok = False
        if any(len(r) > 120 for r in rules):
            ok = False
        domains = collect_domains(root)
        if 'cat' not in domains:
            ok = False
        missing = load_lattice(Path('/nonexistent/concept-lattice.json'))
        if missing.get('concepts') != []:
            ok = False
    if ok:
        print('PASS')
        return 0
    print(f'FAIL core={core}')
    return 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description='Domain summary for ontology injection')
    ap.add_argument('--self-test', action='store_true')
    args = ap.parse_args(argv)
    if args.self_test:
        return self_test()
    try:
        payload = run()
        print(json.dumps({
            'n_domains': len(payload.get('domains') or []),
            'n_core_entities': len(payload.get('core_entities') or []),
            'n_business_rules': len(payload.get('business_rules') or []),
            'ts': payload.get('ts'),
        }))
    except Exception:
        pass
    return 0


if __name__ == '__main__':
    sys.exit(main())
