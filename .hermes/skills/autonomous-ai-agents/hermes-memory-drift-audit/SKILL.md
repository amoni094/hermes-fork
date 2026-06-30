---
name: hermes-memory-drift-audit
description: Audit Hermes durable memory, Obsidian sync notes, and compact policy notes for duplication, stale references, and overgrowth.
---

# Hermes Memory Drift Audit

Use this when the user wants to inspect or maintain the boundary between Hermes local memory and the Obsidian second brain.

## Trigger

Use this skill when the task is to:
1. Explain how Hermes local memory is layered.
2. Check for duplication or drift between `~/.hermes/memories/MEMORY.md` and vault `MEMORY.md`.
3. Keep rewrite-oriented sync notes compact.
4. Detect stale path references after memory-layout migrations.
5. Schedule or verify a recurring audit.

## Current local layering

- Canonical agent-facing durable facts live in `~/.hermes/memories/MEMORY.md`.
- Vault `Documents/SecondBrain/MEMORY.md` is a thin human-facing index, not a second canonical memory store.
- `Documents/SecondBrain/04 Resources/Hermes Chat Live Sync.md` is a curated rollup.
- The current daily note should contain only a short `## Hermes Chat Sync` mirror.
- `~/.hermes/logs/*.jsonl` and `~/.hermes/state/*.json` are telemetry/retrieval aids, not durable memory.

## Audit workflow

1. Read these files first:
   - `~/.hermes/memories/MEMORY.md`
   - `/var/home/rainbow/Documents/SecondBrain/MEMORY.md`
   - `/var/home/rainbow/Documents/SecondBrain/04 Resources/Hermes Chat Live Sync.md`
   - today’s daily note under `/var/home/rainbow/Documents/SecondBrain/01 Daily/`
2. If the scripted audit exists, read `/var/home/rainbow/.hermes/scripts/hermes-memory-drift-audit.py` before changing policy.
3. Check for:
   - exact duplicated durable facts
   - near-duplicate durable facts
   - overgrown live-sync or daily-note sync sections
   - stale note references to old memory paths
4. Prefer making source-of-truth boundaries explicit in the files themselves, not just in chat.
5. Re-run the script directly with:
   - `python3 /var/home/rainbow/.hermes/scripts/hermes-memory-drift-audit.py`
6. Read back the generated audit note:
   - `/var/home/rainbow/Documents/SecondBrain/04 Resources/Hermes Memory Drift Audit.md`
7. If a cron job exists for the audit, verify it still points at the script and stays quiet when clean.
8. Treat a missing current-day daily note as a quiet bootstrap/no-op condition, not an audit failure by itself.
   - The sync workflow may not have created today’s note yet.
   - Flag only when the missing note contradicts an explicit expectation set by the surrounding workflow.
9. After changing the script or policy, verify both paths:
   - run the script directly
   - run the cron job manually and confirm `last_status: ok`

## Current local thresholds

These are tuned to the current vault shape and should be revisited only when the note design changes materially:

- Near-duplicate threshold: `0.78`
- Vault `MEMORY.md`: `<= 24` lines and `<= 1400` bytes
- Live sync note: `<= 90` lines and `<= 6000` bytes
- Daily-note Hermes sync block: `<= 5` bullets and `<= 10` nonblank lines
- Compact monitored notes:
  - `Hermes Memory Drift Audit.md`: `<= 55` lines and `<= 1800` bytes
  - `Hermes Routing Policy.md`: `<= 55` lines and `<= 1800` bytes
  - `Hermes Workflow Policy.md`: `<= 70` lines and `<= 3200` bytes
  - `Hermes Approval Policy.md`: `<= 65` lines and `<= 3400` bytes
  - `Hermes Maintenance and Session Retention.md`: `<= 75` lines and `<= 3400` bytes

## Known local stale-reference rule

Flag and replace this in curated notes unless the note is explicitly documenting legacy history:

- stale: `~/.hermes/workspace/MEMORY.md`
- preferred: `~/.hermes/memories/MEMORY.md`

## Historical exclusions

Do not treat these as live drift unless the user explicitly asks to rewrite historical material:

- `Documents/SecondBrain/04 Resources/Hermes Memory Wiki/sources/`
  - generated provenance/source pages; plugin-owned history should be preserved
- `Documents/SecondBrain/01 Daily/2026-05-27 Wednesday.md`
- `Documents/SecondBrain/01 Daily/2026-05-28 Thursday.md`
  - time-bound historical daily notes; preserve the record of what paths were current then

Current local classification: legacy workspace-memory references should be absent from live curated operational notes, but may remain in historical/generated notes as archive evidence.

## Verification standard

A memory-layering cleanup is not complete until:
- the edited notes were read back,
- the audit script was run for real,
- the audit note was regenerated,
- the script performed its post-write self-check on the generated audit note,
- and the final run outcome was verified from real command output.

## Pitfalls

- Do not let vault `MEMORY.md` become a second full durable-facts store.
- Do not append transcript-like detail into the live-sync note.
- Do not let the daily-note sync section become a duplicate of the live-sync note.
- Do not treat telemetry logs as canonical memory.
- Do not fail the audit just because today’s daily note is absent before the sync job has had a chance to create it.
- If the audit note itself is monitored, the script must check note size again after writing it; otherwise self-generated overgrowth can be missed on the first pass.
