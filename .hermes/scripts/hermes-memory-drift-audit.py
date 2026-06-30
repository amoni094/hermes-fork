#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import pathlib
import re
import sys
from difflib import SequenceMatcher

HERMES_MEMORY = pathlib.Path('/var/home/rainbow/.hermes/memories/MEMORY.md')
VAULT_ROOT = pathlib.Path('/var/home/rainbow/Documents/SecondBrain')
VAULT_MEMORY = VAULT_ROOT / 'MEMORY.md'
LIVE_SYNC = VAULT_ROOT / '04 Resources/Hermes Chat Live Sync.md'
AUDIT_NOTE = VAULT_ROOT / '04 Resources/Hermes Memory Drift Audit.md'
DAILY_NOTES_DIR = VAULT_ROOT / '01 Daily'

VAULT_MEMORY_MAX_LINES = 24
VAULT_MEMORY_MAX_BYTES = 1400
LIVE_SYNC_MAX_LINES = 90
LIVE_SYNC_MAX_BYTES = 6000
DAILY_SYNC_MAX_BULLETS = 5
DAILY_SYNC_MAX_LINES = 10
SIMILARITY_THRESHOLD = 0.78

MONITORED_NOTES: dict[pathlib.Path, dict[str, int]] = {
    AUDIT_NOTE: {'max_lines': 55, 'max_bytes': 1800},
    VAULT_ROOT / '04 Resources/Hermes Routing Policy.md': {'max_lines': 55, 'max_bytes': 1800},
    VAULT_ROOT / '04 Resources/Hermes Workflow Policy.md': {'max_lines': 70, 'max_bytes': 3200},
    VAULT_ROOT / '04 Resources/Hermes Approval Policy.md': {'max_lines': 65, 'max_bytes': 3400},
    VAULT_ROOT / '04 Resources/Hermes Maintenance and Session Retention.md': {'max_lines': 75, 'max_bytes': 3400},
}

STALE_REFERENCE_RULES: dict[pathlib.Path, list[tuple[str, str]]] = {
    VAULT_ROOT / '04 Resources/Hermes Maintenance and Session Retention.md': [
        ('~/.hermes/workspace/MEMORY.md', '~/.hermes/memories/MEMORY.md'),
    ],
}

HISTORICAL_REFERENCE_EXCLUSIONS: dict[str, str] = {
    '04 Resources/Hermes Memory Wiki/sources/': 'generated historical provenance; preserve plugin-owned source pages',
    '01 Daily/2026-05-27 Wednesday.md': 'historical daily note; preserve time-bound record',
    '01 Daily/2026-05-28 Thursday.md': 'historical daily note; preserve time-bound record',
}

IGNORE_PREFIXES = (
    '#',
    '##',
    'Canonical home:',
    'Curated vault index',
    'Pure index',
    '- Agent-facing durable memory lives in',
    '- This vault file should stay thin',
    '- Session transcripts and',
    '- Keep this file short',
    '- Prefer linking/summarizing',
)


def normalize(line: str) -> str:
    line = line.strip()
    line = re.sub(r'^[-*]\s*', '', line)
    line = line.replace('`', '')
    line = re.sub(r'\s+', ' ', line)
    return line.strip().lower()


def fact_lines(path: pathlib.Path) -> list[str]:
    lines: list[str] = []
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line == '§':
            continue
        if any(line.startswith(prefix) for prefix in IGNORE_PREFIXES):
            continue
        if ':' not in line and not line.startswith('- '):
            continue
        lines.append(raw.rstrip())
    return lines


def classify_overlap(hermes_lines: list[str], vault_lines: list[str]) -> tuple[list[tuple[str, str]], list[tuple[str, str, float]]]:
    hermes_map = {normalize(line): line for line in hermes_lines}
    vault_map = {normalize(line): line for line in vault_lines}
    exact = [(hermes_map[key], vault_map[key]) for key in sorted(set(hermes_map) & set(vault_map))]

    near: list[tuple[str, str, float]] = []
    exact_keys = set(hermes_map) & set(vault_map)
    for h_key, h_line in hermes_map.items():
        if h_key in exact_keys:
            continue
        best_score = 0.0
        best_line = None
        for v_key, v_line in vault_map.items():
            if v_key in exact_keys:
                continue
            score = SequenceMatcher(None, h_key, v_key).ratio()
            if score > best_score:
                best_score = score
                best_line = v_line
        if best_line and best_score >= SIMILARITY_THRESHOLD:
            near.append((h_line, best_line, best_score))
    near.sort(key=lambda item: item[2], reverse=True)
    return exact, near


def current_daily_note() -> pathlib.Path:
    today = dt.datetime.now().astimezone().date()
    return DAILY_NOTES_DIR / today.strftime('%Y-%m-%d %A.md')


def section_lines(path: pathlib.Path, heading: str) -> list[str]:
    lines = path.read_text().splitlines()
    in_section = False
    found_heading = False
    collected: list[str] = []
    for line in lines:
        if line.startswith('## '):
            if line.strip() == heading:
                in_section = True
                found_heading = True
                continue
            if in_section:
                break
        if in_section:
            collected.append(line)
    if found_heading:
        return collected
    return []


def evaluate_overgrowth() -> list[str]:
    findings: list[str] = []

    vault_text = VAULT_MEMORY.read_text()
    vault_lines = len(vault_text.splitlines())
    vault_bytes = len(vault_text.encode())
    if vault_lines > VAULT_MEMORY_MAX_LINES or vault_bytes > VAULT_MEMORY_MAX_BYTES:
        findings.append(
            f'Vault MEMORY.md is growing ({vault_lines} lines, {vault_bytes} bytes; target <= {VAULT_MEMORY_MAX_LINES} lines and <= {VAULT_MEMORY_MAX_BYTES} bytes).'
        )

    live_sync_text = LIVE_SYNC.read_text()
    live_sync_lines = len(live_sync_text.splitlines())
    live_sync_bytes = len(live_sync_text.encode())
    if live_sync_lines > LIVE_SYNC_MAX_LINES or live_sync_bytes > LIVE_SYNC_MAX_BYTES:
        findings.append(
            f'Hermes Chat Live Sync.md is growing ({live_sync_lines} lines, {live_sync_bytes} bytes; target <= {LIVE_SYNC_MAX_LINES} lines and <= {LIVE_SYNC_MAX_BYTES} bytes).'
        )

    daily_note = current_daily_note()
    sync_section = section_lines(daily_note, '## Hermes Chat Sync')
    bullet_count = sum(1 for line in sync_section if line.strip().startswith('- '))
    nonblank_count = sum(1 for line in sync_section if line.strip())
    if bullet_count > DAILY_SYNC_MAX_BULLETS or nonblank_count > DAILY_SYNC_MAX_LINES:
        findings.append(
            f"Today's daily-note Hermes Chat Sync block is growing ({bullet_count} bullets, {nonblank_count} nonblank lines; target <= {DAILY_SYNC_MAX_BULLETS} bullets and <= {DAILY_SYNC_MAX_LINES} nonblank lines)."
        )

    for note_path, limits in MONITORED_NOTES.items():
        text = note_path.read_text()
        note_lines = len(text.splitlines())
        note_bytes = len(text.encode())
        if note_lines > limits['max_lines'] or note_bytes > limits['max_bytes']:
            findings.append(
                f'{note_path.name} is growing ({note_lines} lines, {note_bytes} bytes; target <= {limits["max_lines"]} lines and <= {limits["max_bytes"]} bytes).'
            )

    return findings


def evaluate_stale_references() -> list[str]:
    findings: list[str] = []
    for note_path, replacements in STALE_REFERENCE_RULES.items():
        text = note_path.read_text()
        for stale, replacement in replacements:
            if stale in text:
                findings.append(f'{note_path.name} still references stale path `{stale}`; prefer `{replacement}`.')
    return findings


def write_audit_note(exact: list[tuple[str, str]], near: list[tuple[str, str, float]], overgrowth: list[str], stale_refs: list[str]) -> None:
    now = dt.datetime.now().astimezone()
    timestamp = now.strftime('%Y-%m-%d %H:%M %Z')
    status = 'clean' if not exact and not near and not overgrowth and not stale_refs else 'attention'

    lines = [
        '---',
        'title: Hermes Memory Drift Audit',
        f'date: {now.strftime("%Y-%m-%d")}',
        f'status: {status}',
        f'last_checked: {timestamp}',
        '---',
        '',
        '# Hermes Memory Drift Audit',
        '',
        f'- Checked: {timestamp}',
        '- Canonical: `~/.hermes/memories/MEMORY.md`',
        '- Vault index: `Documents/SecondBrain/MEMORY.md`',
        '- Sync checks: live sync, today\'s sync block, compact policy notes',
        f'- Thresholds: dup>={SIMILARITY_THRESHOLD:.2f}; daily<={DAILY_SYNC_MAX_BULLETS} bullets/{DAILY_SYNC_MAX_LINES} lines; live sync<={LIVE_SYNC_MAX_LINES} lines/{LIVE_SYNC_MAX_BYTES} bytes',
        '- Historical exclusions: Memory Wiki `sources/`; daily notes `2026-05-27` and `2026-05-28`',
        '',
        '## Status',
        '',
    ]

    if not exact and not near and not overgrowth and not stale_refs:
        lines.extend([
            '- No exact overlaps detected between Hermes durable memory and vault MEMORY.md.',
            f'- No near-duplicate durable facts detected above similarity threshold {SIMILARITY_THRESHOLD:.2f}.',
            '- No note overgrowth alerts triggered.',
            '- No stale curated-note path references detected in the monitored set.',
        ])
    else:
        if exact:
            lines.append('- Exact durable-fact overlap detected:')
            for _, vault_line in exact:
                lines.append(f'  - {vault_line}')
        if near:
            lines.append('- Near-duplicate durable facts detected:')
            for hermes_line, vault_line, score in near[:8]:
                lines.append(f'  - {score:.2f}: Hermes="{hermes_line}" | Vault="{vault_line}"')
        if overgrowth:
            lines.append('- Note overgrowth alerts:')
            for finding in overgrowth:
                lines.append(f'  - {finding}')
        if stale_refs:
            lines.append('- Stale-path or sync-reference alerts:')
            for finding in stale_refs:
                lines.append(f'  - {finding}')

    lines.extend([
        '',
        '## Notes',
        '',
        '- Monitored compact notes: audit, routing, workflow, approval, maintenance/session-retention.',
        '- Legacy workspace-memory refs are allowed only in excluded historical/generated material.',
        '- Policy: keep stable facts in `~/.hermes/memories/MEMORY.md`; keep vault `MEMORY.md` thin; keep daily sync short and broader rollup in `[[Hermes Chat Live Sync]]`.',
        '',
    ])

    AUDIT_NOTE.write_text('\n'.join(lines) + '\n')


def main() -> int:
    daily_note = current_daily_note()
    required = [HERMES_MEMORY, VAULT_MEMORY, LIVE_SYNC, *MONITORED_NOTES.keys(), *STALE_REFERENCE_RULES.keys()]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        print('Hermes memory drift audit error: missing files: ' + ', '.join(sorted(set(missing))))
        return 1
    if not daily_note.exists():
        return 0

    hermes_lines = fact_lines(HERMES_MEMORY)
    vault_lines = fact_lines(VAULT_MEMORY)
    exact, near = classify_overlap(hermes_lines, vault_lines)
    overgrowth = evaluate_overgrowth()
    stale_refs = evaluate_stale_references()
    write_audit_note(exact, near, overgrowth, stale_refs)

    post_write_overgrowth = evaluate_overgrowth()
    if post_write_overgrowth != overgrowth:
        overgrowth = post_write_overgrowth
        write_audit_note(exact, near, overgrowth, stale_refs)

    if not exact and not near and not overgrowth and not stale_refs:
        return 0

    print('Hermes memory drift audit: attention needed')
    if exact:
        print('- Exact overlaps:')
        for _, vault_line in exact:
            print(f'  - {vault_line}')
    if near:
        print('- Near-duplicates:')
        for hermes_line, vault_line, score in near[:8]:
            print(f'  - {score:.2f}: Hermes="{hermes_line}" | Vault="{vault_line}"')
    if overgrowth:
        print('- Overgrowth alerts:')
        for finding in overgrowth:
            print(f'  - {finding}')
    if stale_refs:
        print('- Stale-path alerts:')
        for finding in stale_refs:
            print(f'  - {finding}')
    print(f'- Audit note updated: {AUDIT_NOTE}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
