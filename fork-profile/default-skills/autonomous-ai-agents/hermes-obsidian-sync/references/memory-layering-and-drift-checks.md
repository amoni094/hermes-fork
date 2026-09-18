# Memory layering and drift checks

Use this reference when reviewing how Hermes local memory and an Obsidian second brain interact.

## Default source-of-truth map

- `~/.hermes/memories/MEMORY.md`
  - Agent-facing durable facts and stable user/workflow preferences.
- Session DB / `session_search`
  - Transcript recall and past conversational context.
- `~/.hermes/logs/*.jsonl`
  - Operational telemetry and capture traces.
- `~/.hermes/state/*.json`
  - Runtime state/supporting indicators.
- Obsidian live-sync note
  - Curated human-readable rollup of what matters now.
- Obsidian daily note mirror
  - Short pointer + a few durable bullets, not a second full summary.

## Review questions

1. Which file is the canonical home for this fact?
2. Is the same stable fact repeated in both Hermes durable memory and the vault?
3. Is a JSONL/event/state file being treated like durable knowledge instead of telemetry?
4. Is the daily note repeating the live-sync note instead of pointing to it?
5. Are there stale skill or cron references to missing sync/memory skills that should be updated?

## Common duplication patterns

- Stable environment facts copied into both `~/.hermes/memories/MEMORY.md` and vault `MEMORY.md`.
- Live-sync content expanded again inside the daily note.
- Operational logs summarized into notes without filtering for durable state.
- Multiple docs/skills all describing the same sync workflow with slightly different wording.

## Preferred response

- Choose one canonical home per memory type.
- Keep telemetry/logs out of curated notes except as evidence during review.
- Keep the daily note thin and link back to the live-sync note.
- When duplication exists, recommend trimming or linking instead of mirroring the same text everywhere.
- If verification sources disagree, trust direct filesystem readback of the note before dirty-path/event lag indicators.
