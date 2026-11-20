#!/usr/bin/env python3
"""Obstruction certificates for stale skill/memory cleanup (report-only)."""
from __future__ import annotations
import argparse, json, os, sqlite3, sys, tempfile, time, uuid
from datetime import datetime, timezone, UTC
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', 'fork')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base
CACHE = _hermes_root / 'cache'
SKILLS = _hermes_root / 'skills'

def _now() -> str:
    return datetime.now(UTC).isoformat()

def _atomic_write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(obj, indent=2) + '\n', encoding='utf-8')
    os.replace(str(tmp), str(path))

def _lifecycle_db() -> Path:
    return _hermes_root / 'memory-facts' / 'lifecycle.db'

def _temp_out(prefix: str) -> Path:
    return Path(tempfile.gettempdir()) / (f'{prefix}-{uuid.uuid4().hex}.json')

OUT_PATH = CACHE / 'obstruction-certificate-cache.json'


def certificates():
    now = time.time()
    stale = []
    if SKILLS.exists():
        try:
            for p in SKILLS.iterdir():
                if not p.is_dir() or p.name.startswith('.'):
                    continue
                md = p / 'SKILL.md'
                if not md.exists():
                    continue
                age_days = (now - md.stat().st_mtime) / 86400.0
                if age_days >= 90:
                    stale.append({'skill': p.name, 'age_days': round(age_days, 1), 'risk': 'low_if_unreferenced'})
        except OSError:
            pass
    mem_n = 0
    db = _lifecycle_db()
    if db.exists():
        try:
            conn = sqlite3.connect(f'file:{db}?mode=ro', uri=True)
            try:
                tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                if 'facts' in tables:
                    mem_n = conn.execute('SELECT COUNT(*) FROM facts').fetchone()[0]
            finally:
                conn.close()
        except Exception:
            mem_n = 0
    return {
        'ts': _now(),
        'stale_skill_count': len(stale),
        'stale_skills': stale[:40],
        'memory_candidates': mem_n,
        'destructive': False,
    }


def _self_test() -> int:
    r = certificates()
    assert 'stale_skill_count' in r
    tmp = _temp_out('occ')
    _atomic_write(tmp, r)
    try:
        tmp.unlink(missing_ok=True)
    except OSError:
        pass
    print('[obstruction-certificate-cache] --self-test PASS stale={}'.format(r['stale_skill_count']))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true')
    args = ap.parse_args()
    if args.self_test:
        try:
            sys.exit(_self_test())
        except Exception as exc:
            print(f'[obstruction-certificate-cache] --self-test FAIL: {exc}')
            sys.exit(1)
    try:
        r = certificates()
        _atomic_write(OUT_PATH, r)
        print(json.dumps({'stale_skill_count': r['stale_skill_count'], 'memory_candidates': r['memory_candidates']}))
    except Exception:
        pass


if __name__ == '__main__':
    main()
