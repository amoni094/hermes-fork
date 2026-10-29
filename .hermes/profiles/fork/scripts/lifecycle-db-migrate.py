#!/usr/bin/env python3
"""lifecycle-db-migrate: Sync lifecycle.db schema from root to fork profile. Idempotent.

Run before memory-ttl-purge (daily 03:30) to ensure fork profile DB always has all root tables.
"""
import os, sqlite3
from pathlib import Path

_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_profile = os.environ.get('HERMES_PROFILE', '')
_FORK_ROOT = (_base / 'profiles' / _profile) if _profile and 'profiles' not in str(_base) else _base
_hermes_root = _base if 'profiles' not in str(_base) else _base.parent.parent

ROOT_DB = _hermes_root / 'memory-facts' / 'lifecycle.db'
FORK_DB = _FORK_ROOT / 'memory-facts' / 'lifecycle.db'


def main():
    if not ROOT_DB.exists():
        print(f'[lifecycle-db-migrate] root DB not found: {ROOT_DB}')
        return 1
    FORK_DB.parent.mkdir(parents=True, exist_ok=True)
    src = sqlite3.connect(str(ROOT_DB))
    dst = sqlite3.connect(str(FORK_DB))
    added_tables, added_indexes = [], []
    try:
        src_t = dict(src.execute(
            "SELECT name, sql FROM sqlite_master WHERE type='table' AND sql IS NOT NULL"
        ).fetchall())
        dst_t = {r[0] for r in dst.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        for name, sql in src_t.items():
            if name not in dst_t:
                dst.execute(sql)
                added_tables.append(name)
        src_i = src.execute(
            "SELECT name, sql FROM sqlite_master WHERE type='index' AND sql IS NOT NULL"
        ).fetchall()
        dst_i = {r[0] for r in dst.execute(
            "SELECT name FROM sqlite_master WHERE type='index'"
        ).fetchall()}
        for name, sql in src_i:
            if name not in dst_i:
                try:
                    dst.execute(sql)
                    added_indexes.append(name)
                except sqlite3.OperationalError:
                    pass
        dst.commit()
        if added_tables:
            print(f'[lifecycle-db-migrate] added tables: {added_tables}')
        if added_indexes:
            print(f'[lifecycle-db-migrate] added indexes: {added_indexes}')
        if not added_tables and not added_indexes:
            print('[lifecycle-db-migrate] schema in sync')
        return 0
    finally:
        src.close()
        dst.close()


if __name__ == '__main__':
    raise SystemExit(main())
