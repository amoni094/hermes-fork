#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import pathlib
import re
import sys
from difflib import SequenceMatcher

# OT utilities (shared; OT-11)
_OT_UTILS_PATH = pathlib.Path(__file__).parent / "ot_utils.py"
if _OT_UTILS_PATH.exists():
    import importlib.util as _ilu
    _spec = _ilu.spec_from_file_location("ot_utils", _OT_UTILS_PATH)
    _ot_utils = _ilu.module_from_spec(_spec)  # type: ignore[arg-type]
    _spec.loader.exec_module(_ot_utils)  # type: ignore[union-attr]
else:
    _ot_utils = None  # type: ignore[assignment]

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


def evaluate_mandatory_rule_leakage() -> list[str]:
    """
    Check whether mandatory system rules (safety, scope, routing) have leaked into
    the Hindsight retrieval path instead of living in MEMORY.md / config.yaml.

    Mandatory rules in probabilistic retrieval are unreliable — they may not surface
    when needed (Habr/RU practitioner finding, Aug 2026; corroborated by sweep 22
    'mandatory rules must NOT be in probabilistic retrieval' pattern).

    Strategy: query Hindsight for known mandatory-rule keywords and flag any hits
    that are exact duplicates of what already lives in MEMORY.md.
    This is a best-effort offline check; if Hindsight is down, skip silently.
    """
    import urllib.request
    import urllib.error
    import json

    HINDSIGHT_BASE = "http://127.0.0.1:9177"
    HINDSIGHT_BANK = "hermes-default"

    # Keywords that indicate a mandatory rule (should live in MEMORY.md, not Hindsight)
    MANDATORY_KEYWORDS = [
        "no autonomous loops",
        "never use local llm",
        "ollama uninstalled",
        "read-before-write",
        "escalation: default",
        "routing is cloud-only",
        "safety: no autonomous",
        "irreversible side effects",
    ]

    findings: list[str] = []

    # Load MEMORY.md content for cross-check
    try:
        memory_text = HERMES_MEMORY.read_text().lower()
    except Exception:
        return findings

    for keyword in MANDATORY_KEYWORDS:
        if keyword.lower() not in memory_text:
            continue  # Not a mandatory rule we track — skip
        try:
            payload = json.dumps({"query": keyword, "top_k": 5}).encode()
            req = urllib.request.Request(
                f"{HINDSIGHT_BASE}/v1/default/banks/{HINDSIGHT_BANK}/memories/recall",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read())
            results = data if isinstance(data, list) else data.get("results", [])
            for mem in results:
                text = mem.get("text", mem.get("content", "")).lower()
                if keyword.lower() in text:
                    findings.append(
                        f"Mandatory rule leaked into Hindsight retrieval path: "
                        f"keyword '{keyword}' found in memory id={mem.get('id', '?')[:16]}. "
                        f"Mandatory rules belong in MEMORY.md, not probabilistic retrieval."
                    )
                    break  # One flag per keyword is enough
        except (urllib.error.URLError, Exception):
            pass  # Hindsight unavailable — skip silently

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

    if not exact and not near and not overgrowth and not stale_refs and not rule_leakage:
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
    rule_leakage = evaluate_mandatory_rule_leakage()
    write_audit_note(exact, near, overgrowth, stale_refs + rule_leakage)

    post_write_overgrowth = evaluate_overgrowth()
    if post_write_overgrowth != overgrowth:
        overgrowth = post_write_overgrowth
        write_audit_note(exact, near, overgrowth, stale_refs + rule_leakage)

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
    return 1


def run_memory_staleness() -> None:
    """Run memory-staleness.py as a subprocess and print its output if STALE sections found."""
    import subprocess
    staleness_script = pathlib.Path(__file__).parent / 'memory-staleness.py'
    if not staleness_script.exists():
        return
    try:
        result = subprocess.run(
            ['python3', str(staleness_script)],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0 and '✗ STALE' in result.stdout:
            print('\n--- memory-staleness.py report ---')
            print(result.stdout)
    except Exception as e:
        print(f'memory-staleness.py skipped: {e}')


if __name__ == '__main__':
    import argparse as _ap

    _parser = _ap.ArgumentParser(
        description="Hermes memory drift audit",
        formatter_class=_ap.RawDescriptionHelpFormatter,
    )
    _parser.add_argument(
        "--w1-drift", action="store_true", dest="w1_drift",
        help=(
            "OT-11: compute W1 distance between current and previous memory checkpoint. "
            "High value = memory vocabulary has shifted significantly."
        ),
    )
    _args, _remaining = _parser.parse_known_args()

    # === OT-11: --w1-drift ===
    if _args.w1_drift:
        if _ot_utils is None:
            print("[OT-11] ot_utils not available — cannot compute W1 drift.")
            sys.exit(1)

        # Current memory
        if not HERMES_MEMORY.exists():
            print(f"[OT-11] MEMORY.md not found at {HERMES_MEMORY}")
            sys.exit(1)
        current_text = HERMES_MEMORY.read_text(errors="replace")
        tf_current = _ot_utils.build_tf(current_text)

        # Previous checkpoint — look for a dated backup or snapshot
        # Convention: ~/.hermes/memories/MEMORY.md.prev or MEMORY-YYYY-MM-DD.md
        prev_candidates = [
            HERMES_MEMORY.parent / "MEMORY.md.prev",
            HERMES_MEMORY.parent / "MEMORY.md.bak",
        ]
        # Also look for yesterday's dated snapshot
        yesterday = (dt.datetime.now().astimezone().date() - dt.timedelta(days=1))
        prev_candidates.insert(
            0,
            HERMES_MEMORY.parent / f"MEMORY-{yesterday.isoformat()}.md",
        )
        prev_path = next((p for p in prev_candidates if p.exists()), None)

        if prev_path is None:
            # Fallback: use vault MEMORY.md as a proxy "previous" snapshot
            if VAULT_MEMORY.exists():
                prev_path = VAULT_MEMORY
                print(f"[OT-11] No checkpoint found; using vault MEMORY.md ({VAULT_MEMORY}) as proxy.")
            else:
                print("[OT-11] No previous memory checkpoint found. Cannot compute W1 drift.")
                sys.exit(1)
        else:
            print(f"[OT-11] Previous checkpoint: {prev_path}")

        prev_text = prev_path.read_text(errors="replace")
        tf_prev = _ot_utils.build_tf(prev_text)

        w1 = _ot_utils.w1_distance(tf_current, tf_prev)
        print(f"W1_drift = {w1:.6f}  (lower = stable; higher = significant memory vocabulary shift)")
        if w1 < 0.05:
            print("Interpretation: stable — memory vocabulary essentially unchanged.")
        elif w1 < 0.15:
            print("Interpretation: minor drift — small vocabulary additions/removals.")
        elif w1 < 0.30:
            print("Interpretation: moderate drift — review recent memory writes for consistency.")
        else:
            print("Interpretation: HIGH drift — memory vocabulary has shifted significantly; audit recommended.")
        sys.exit(0)

    run_memory_staleness()
    # AM-Sentry: passive memory poisoning scan (Sweep 21)
    import subprocess as _sp
    _sentry = pathlib.Path(__file__).parent / 'am-sentry.py'
    if _sentry.exists():
        try:
            _r = _sp.run(['python3', str(_sentry), '--since', '1'], capture_output=True, text=True, timeout=15)
            if _r.returncode == 1:
                print('\n--- AM-Sentry: HIGH-severity flags detected ---')
                print(_r.stdout)
            elif 'LOW' in _r.stdout:
                print('\n--- AM-Sentry: LOW flags (review advised) ---')
                print(_r.stdout)
        except Exception as _e:
            print(f'am-sentry.py skipped: {_e}')
    sys.exit(main())
