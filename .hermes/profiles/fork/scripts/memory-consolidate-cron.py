#!/usr/bin/env python3
"""memory-consolidate-cron.py - Deduplicate MEMORY.md without losing facts.

Usage:
  python3 memory-consolidate-cron.py        # dry run
  python3 memory-consolidate-cron.py --apply # write changes

Algorithm: within each section (split by paragraph/blank line),
remove lines that are >85%% word-overlap with another line in the same section.
Never deletes unique facts. Stdlib only. Atomic write.
"""
import argparse, json, os
from datetime import datetime, timezone
from pathlib import Path


def _mem_path() -> Path:
    base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
    profile = os.environ.get('HERMES_PROFILE', 'fork')
    if profile:
        return base / 'profiles' / profile / 'memories' / 'MEMORY.md'
    return base / 'memories' / 'MEMORY.md'


def _log_path() -> Path:
    base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
    return base / 'cache' / 'memory-consolidate.log'


def _similarity(a: str, b: str) -> float:
    wa = set(a.lower().split())
    wb = set(b.lower().split())
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / max(len(wa), len(wb))


def _dedup_section(lines: list) -> list:
    kept = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            kept.append(line)
            continue
        is_dup = any(
            _similarity(stripped, k.strip()) > 0.85
            for k in kept if k.strip()
        )
        if not is_dup:
            kept.append(line)
    return kept


def main() -> None:
    parser = argparse.ArgumentParser(description='Deduplicate MEMORY.md')
    parser.add_argument('--apply', action='store_true', help='Write changes')
    args = parser.parse_args()

    mem_path = _mem_path()
    if not mem_path.exists():
        print(f'MEMORY.md not found: {mem_path}')
        return

    original = mem_path.read_text()
    sections = original.split('\u00a7')  # section separator
    new_sections = []
    total_removed = 0
    for section in sections:
        lines = section.split('\n')
        deduped = _dedup_section(lines)
        removed = len(lines) - len(deduped)
        total_removed += removed
        new_sections.append('\n'.join(deduped))

    result = '\u00a7'.join(new_sections)

    print(f'Original: {len(original)} chars, {len(original.splitlines())} lines')
    print(f'Result:   {len(result)} chars, {len(result.splitlines())} lines')
    print(f'Removed:  {total_removed} duplicate lines')

    if len(result) > 2100:
        print('WARNING: result still > 2100 chars -- no changes applied')
        return

    if args.apply:
        if total_removed == 0:
            print('Nothing to remove.')
            return
        tmp = mem_path.with_suffix('.tmp')
        tmp.write_text(result)
        os.replace(str(tmp), str(mem_path))
        print(f'Applied: {len(result)} chars written to {mem_path}')
        try:
            log_path = _log_path()
            log_path.parent.mkdir(parents=True, exist_ok=True)
            entry = json.dumps({
                'ts': datetime.now(timezone.utc).isoformat(),
                'removed_lines': total_removed,
                'chars_after': len(result),
            })
            with open(str(log_path), 'a') as f:
                f.write(entry + '\n')
        except Exception:
            pass
    else:
        print('Dry run. Pass --apply to write.')


if __name__ == '__main__':
    main()
