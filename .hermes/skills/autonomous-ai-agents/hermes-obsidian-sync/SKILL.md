---
name: hermes-obsidian-sync
description: Curate recent Hermes session activity into an Obsidian vault with rewrite-oriented sync notes, daily-note rollups, and privacy-safe durable summaries.
---

# Hermes Obsidian Sync

Use this when a user wants Hermes chat activity synchronized into an Obsidian vault, especially from a scheduled cron job.

This is the canonical Obsidian synchronization skill for this workspace. If older rollup-oriented skills are nearby, prefer this one unless the user explicitly asks for legacy rollup behavior.

## Trigger

Use this skill when the task is to:
1. Review recent Hermes sessions and local sync hints.
2. Distill only durable/high-signal changes.
3. Rewrite a live-sync note cleanly instead of appending duplicate sections forever.
4. Update the current daily note with a short Hermes sync block.

## Core principles

- Prefer curated durable facts over transcript-like summaries.
- Keep the sync note rewrite-oriented: replace the note body with the current curated state rather than appending a fresh dated section every run.
- Capture stable changes only: workflow changes, configuration facts, verified results, note syncs, cron changes, maintenance actions, and stable follow-ups.
- Exclude secrets, raw transcripts, long logs, and transient noise.
- If there is genuinely nothing meaningful to add, keep the note stable and only refresh the timestamp when appropriate.
- A timestamp-only refresh counts as maintenance, not a new durable fact: preserve the daily note block if it is already current, and in silent-delivery cron modes you may return `[SILENT]` when no curated content changed.
- For cron-style delivery modes, return `[SILENT]` only when there is truly nothing new to report and the caller explicitly asked for silent suppression.
- Distinguish memory layers explicitly:
  - Obsidian sync notes are curated human-readable summaries.
  - `~/.hermes/memories/MEMORY.md` is agent-facing durable memory.
  - session history and local JSONL files are retrieval/telemetry sources, not canonical durable notes.
- When the same stable fact appears in multiple local memory surfaces, prefer one canonical home and summarize/link elsewhere instead of restating the full fact in every layer.

## Recommended workflow

1. Resolve the current local date/time first.
   - Treat that exact runtime result as the canonical source for both the daily-note filename and visible sync timestamps.
   - Do not mentally re-derive the hour, day name, or date string when writing the note; copy from the resolved runtime value so cron runs do not introduce avoidable timestamp or filename drift.
   - File tools do not expand shell substitutions; resolve the concrete daily-note path from the runtime date before reading or writing.
2. Browse recent sessions, then read the most relevant sessions from the last 24 hours (typically up to 5).
   - If recent results are crowded with earlier cron sync runs, treat those as note-maintenance context rather than primary source material.
   - Inspect at most one recent prior sync run when you need to preserve already-curated state, but prioritize substantive user/CLI sessions for genuinely new durable changes.
   - If a full prior sync session dump is huge or transcript-heavy, do not brute-read it just because it is recent; prefer the current live-sync note, today's daily note, and local file-event telemetry as the continuity baseline, and only drill into a narrowed session slice when you need a specific durable fact.
3. Check local high-signal hint files when present:
   - `~/.hermes/logs/hermes-memory-capture.jsonl`
   - `~/.hermes/logs/hermes-obsidian-file-events.jsonl`
   - `~/.hermes/state/obsidian-dirty-paths.json`
   - Prefer the newest tail of append-only JSONL logs first; for large files, inspect only the recent lines rather than trying to read the whole file at once.
   - If the JSONL logs are already large, first narrow with content search on the current date, recent session ids, or target note paths so you read only the relevant tail slice instead of brute-reading the file from line 1.
   - If a log read exceeds safety limits, use the reported `total_lines`/size hint and re-read a small tail window near the end rather than starting at line 1 again.
4. Read the current live-sync note and today's daily note before rewriting them, so repeated cron runs preserve already-curated durable state instead of replacing it with a narrower partial pass.
   - Do not treat a context-compaction summary, prior assistant report, or earlier-turn claim that a note was already read as satisfying this step; re-read the actual note files in the current turn before any rewrite or patch.
5. Extract only durable items that survived the session as actual state, configuration, or verified result.
   - For maintenance/cleanup sessions, record only the final verified baseline: consolidated cron ownership, config invariants now in force, low-risk skill pruning that actually happened, and any intentionally deferred prune candidates.
   - If a deletion happened, say whether it was absorbed into a canonical umbrella or pruned as a clear orphan; do not imply a broader cleanup than what was verified.
6. Rewrite the live-sync note with a stable structure:
   - frontmatter
   - last synced timestamp
   - scope
   - recent sessions
   - key durable themes
   - follow-ups
   - privacy notes
7. Ensure today’s daily note exists and contains a `## Hermes Chat Sync` section.
8. If today’s daily note does not exist yet, create a minimal note that contains the sync block only rather than skipping the daily-note update.
9. Update the daily note surgically: preserve any unrelated existing content and replace only the `## Hermes Chat Sync` block unless the file is empty or is clearly just a sync stub.
   - If the daily note already contains non-sync content, patch only the sync block in place.
   - Only rewrite the whole daily note when it is empty, missing, or obviously a sync-only stub.
   - If a patch misses because the sync block already drifted, re-read the live file and patch against the current block text instead of retrying the stale wording.
10. Keep the daily-note block concise: link `[[Hermes Chat Live Sync]]` and add 3–5 short bullets.
11. Read back the written files to verify the sync landed.
- If available, confirm dirty-path or file-event state reflects the writes.
- If the daily-note sync block includes its own visible timestamp line (for example `- Last synced: ...`), refresh that line too after final verification so the live-sync note and daily-note block do not drift by a minute or more.
- After a frontmatter timestamp edit, re-read the live-sync note and patch the visible body timestamp separately if it still shows the older time.

## Durable-item filter

Keep items like:
- service/config changes that remain in effect
- verified listeners, ports, endpoints, or runtime state
- installed integrations that were actually wired in
- cron or systemd changes
- note-maintenance conventions that should repeat next run
- stable caveats that affect future work
- for same-day iterative UX/config work, the final durable state plus at most one still-open caveat, rather than each intermediate tweak
- for same-day iterative preference-calibration or recommendation sessions, the final settled preference lane plus at most one durable caveat, rather than every rating round or suggestion batch
- when a session is dominated by pixel nudges, spacing tweaks, or other visual micro-adjustments after the core mechanism is already correct, summarize only the settled mechanism and the current final placement/state; never mirror the adjustment sequence from session history or JSONL hints
- when recommendation or preference sessions keep narrowing within the same broad lane during the same day (for example adventure → mystery-trashy → samurai → duel-driven), keep one settled current lane plus caveats instead of creating separate durable bullets for each sub-genre pivot

Do not keep:
- transient errors that were resolved and do not matter anymore
- environment/setup failures as durable negatives
- raw tool output or copied transcript chunks
- credentials or sensitive tokens

## Writing guidance

### Live-sync note
- Rewrite cleanly.
- Group related work into a few session/theme sections instead of many tiny bullets.
- Prefer “what changed and what remains true now” over “what happened minute-by-minute.”
- When a session is mostly repeated recommendation, taste-tuning, or other calibration loops, collapse it into the final stable preference or operating state instead of replaying the intermediate rounds.
- If the last 24 hours contain more than one still-current durable cluster (for example infrastructure recovery plus blocked-source policy work), keep both clusters in the rewrite. Do not let the newest narrower cluster crowd out earlier same-day state that is still part of the current operating picture.
- When a run contains both service-recovery work and source-policy/fallback work, keep them as separate recent-session themes rather than folding them into a single vague maintenance bullet.

### Daily note
- Keep the `## Hermes Chat Sync` block short and skimmable.
- Include one bullet for the link and 2–4 bullets for the most durable new items.
- Preserve all unrelated daily-note content above and below the sync block; rewrite the block, not the whole note.
- Avoid repeating the full live-sync note inside the daily note.
- Do not copy PR numbers, commit SHAs, test counts, or other verification minutiae into the daily note unless they changed an ongoing operating rule or durable workflow.
- Prefer daily-note bullets that express current state and memory-layer boundaries over session-specific accomplishment logs.

## Verification

Before finishing:
- Read back the live-sync note.
- Read back the daily note.
- Treat readback of the written note files as the primary verification source.
- Use dirty-path or file-event state only as supporting evidence; those local tracking files can lag behind the actual note rewrite during the same run.
- If available, confirm dirty-path or file-event state reflects the writes.
- If the live-sync note exposes a visible `_Last synced_` line, refresh it to the actual completed sync time after the final verification pass so it matches the frontmatter timestamp.
- When refreshing that timestamp, patch both locations deliberately; do not assume a frontmatter-only edit also updated the visible body line.
- After any timestamp patch, re-read the live-sync note before finishing; if the visible body line still shows the older time, patch it separately immediately rather than trusting the first successful edit.
- If the daily note already contains the correct thin sync bullets and only the live-sync timestamp changed, keep the daily note stable unless its own visible timestamp line also needs the same refresh.
- Report only the curated result, not the raw verification logs.
- If you inspect duplication or drift, classify each source before editing or summarizing it:
  - canonical durable memory
  - curated vault note
  - transcript/session history
  - operational telemetry/log
  This prevents accidentally treating JSONL capture files or session transcripts as first-class durable memory.

## When the task is memory cleanup rather than routine sync

If the user asks you to reduce duplication or fix drift between Hermes memory and Obsidian, make the source-of-truth boundaries explicit in the files themselves instead of only describing them in chat.

Recommended cleanup pattern:
- In `~/.hermes/memories/MEMORY.md`, add or preserve a short statement that it is the canonical home for agent-facing durable facts.
- In vault `MEMORY.md`, keep only a thin human-facing index plus a short `Source of truth` section that points back to `~/.hermes/memories/MEMORY.md`.
- Remove repeated operational facts from the vault index when they already live in Hermes durable memory.
- In the live-sync note, add one sentence in the scope/intro clarifying that it is a curated human-readable rollup, not the canonical durable-memory store.
- Treat `~/.hermes/logs/*.jsonl` and `~/.hermes/state/*.json` as telemetry/retrieval aids, not durable notes.
- Check scheduled sync jobs for stale or missing skill references and update them to the current umbrella skill instead of leaving disabled legacy names in place.
- When this layered setup is already in place, add a lightweight drift audit that compares Hermes durable memory against vault `MEMORY.md`, checks for near-duplicate phrasing and note overgrowth, writes a compact rewrite-oriented audit note in the vault, and stays silent unless attention is needed.

This class of task is complete only when the files and any affected cron job definitions have been updated and then read back for verification.

## Pitfalls

- Do not rewrite from session/log hints alone when the current live-sync note or daily note already contains validated durable state from an earlier run; read the existing note surfaces first and preserve the durable parts.
- Do not replace a populated daily note wholesale just to refresh the sync section; patch the `## Hermes Chat Sync` block in place unless the note is genuinely just a sync stub.
- If a run is timestamp-only maintenance, keep the daily note untouched unless its own visible timestamp line is stale; the live-sync note can carry the freshness signal.
- Do not append a new large dated section to the live-sync note every run; rewrite it.
- Do not treat every recent session as durable; many are transient or superseded.
- Do not overfit to one session’s wording when the lasting lesson is a broader operational state.
- Do not dump local logs into Obsidian; extract only the durable signal.
- Do not let both `~/.hermes/memories/MEMORY.md` and vault `MEMORY.md` grow into competing canonical sources for the same stable operational facts; decide which layer owns the fact and keep the other layer thinner.
- Do not hardcode the drift audit to a single dated daily note path; resolve the current daily note dynamically.
- Do not make the daily-note size threshold stricter than the sync policy itself; if the skill says 3–5 bullets, the audit threshold should allow 5.

## Support files

- `references/live-sync-note-template.md` — compact template and section checklist for the rewritten sync note.
- `references/memory-layering-and-drift-checks.md` — source-of-truth map for Hermes memory vs Obsidian vs session/log layers, plus duplication/drift review prompts.
- `references/memory-drift-audit-pattern.md` — lightweight silent-audit pattern for catching reintroduced overlap between Hermes durable memory and vault `MEMORY.md`, plus near-duplicate, overgrowth, and audit-note patterns.
- `references/timestamp-refresh-and-partial-read-pitfalls.md` — notes on keeping frontmatter and visible timestamps aligned and re-reading full files before overwrite.
- `references/daily-note-bootstrap-and-timestamp-sync.md` — how to bootstrap a missing daily note and keep the sync timestamp aligned after final verification.
- `references/mixed-cluster-sync-pattern.md` — how to keep multiple still-current durable clusters separate in one sync rewrite without collapsing them into a vague maintenance bullet.
- `references/maintenance-baseline-and-prune-reporting.md` — how to summarize maintenance-only sessions as a verified end-state baseline without overstating what was pruned.
