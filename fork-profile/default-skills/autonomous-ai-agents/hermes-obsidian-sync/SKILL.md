---
name: hermes-obsidian-sync
related_skills:
  - obsidian
  - obsidian-research-ingestion
  - hermes-memory-surface-selection
  - hermes-session-hygiene
triggers:
  - Curating recent Hermes session activity into the Obsidian vault
  - User wants to sync Hermes notes or session summaries to Obsidian daily notes
  - Running the Hermes→Obsidian sync with rewrite-oriented output
  - Creating a session rollup or activity summary in the Obsidian vault
description: >
  Use when curating recent Hermes session activity into an Obsidian vault with rewrite-oriented sync notes, daily-note rollups, and privacy-safe durable summaries.
---

# Hermes Obsidian Sync

Use this when a user wants Hermes chat activity synchronized into an Obsidian vault, especially from a scheduled cron job.

This is the canonical Obsidian synchronization skill for this workspace. If older rollup-oriented skills are nearby, prefer this one unless the user explicitly asks for legacy rollup behavior.

## CRON FAST PATH (context-budget mode)

**Use this shortened path when loaded in a cron job to stay within 12K-token limits.
Skip all reference-file lookups and use the inline decision logic only.**

1. Resolve date/time: `date +"%Y-%m-%d %H:%M %Z"` and `date -u +"%Y-%m-%dT%H:%M:%SZ"`.
2. Discover daily-note path: `search_files(target='files', pattern='*YYYY-MM-DD*')`.
3. Read live-sync note + today's daily note (or note they don't exist).
4. Decision (inline, no reference files):
   - Both notes recent (<8h) and accurate → **Path A** (timestamp-only refresh, 2 patches).
   - Notes stale/drifted/missing → **Path B** (browse last 5 sessions, rewrite note).
   - No new content AND job has SILENT flag → **Path C** (return [SILENT]).
5. Patch frontmatter `last_synced` AND visible body `_Last synced_` (two separate patches).
6. Verify readback. Report one-line summary or [SILENT].

**Do NOT load reference files in cron mode. Inline logic above is complete.**

---

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
   - **Daily-note directory variance**: Different Obsidian vaults use different directory conventions (e.g. `10 Daily/`, `02 Daily Notes/`, `memory/`). When step 2 reads today's daily note and gets a "not found" error, **immediately** use `search_files(target='files', pattern='*<YYYY-MM-DD>*')` to discover existing daily-note paths by date pattern. Once found, use the discovered directory path going forward for all reads/writes in this sync run. See `references/daily-note-discovery-worked-example.md` for a concrete walkthrough.

2. Read the current live-sync note and today's daily note before any further decisions.
   - Do not treat a context-compaction summary, prior assistant report, or earlier-turn claim that a note was already read as satisfying this step; re-read the actual note files in the current turn before proceeding.
   - These are your continuity baseline.

3. **MANDATORY CHECKPOINT — Consult the decision tree** (`references/timestamp-only-maintenance-decision-tree.md`).
   - After reading the current notes (step 2), immediately consult this decision tree.
   - Do not skip to session browsing or log inspection without consulting it first.
   - **If the decision-tree reference file is missing, use this quick inline logic (which is the canonical form):**
     - Both notes recent (last sync < 8 hours ago) AND sections match current state? → **Path A (timestamp-only refresh)**
     - Notes stale, contain outdated sections, or missing sync metadata? → **Path B (full rewrite)**
     - No new durable items AND cron caller explicitly allows `[SILENT]` delivery? → **Path C (silent suppression)**
     - Otherwise? → **Path A** (default to timestamp refresh, then verify)
   - This gating decision determines whether the sync run should:
     - Do a **full rewrite** (new durable items found, or notes are stale/inaccurate)
     - Do a **timestamp-only refresh** (notes are current and accurate, no new durable items since last sync)
     - Return `[SILENT]` (no new content AND cron caller explicitly accepts silent suppression)
   - If the notes are already recent and accurate, session browsing becomes secondary verification only, not the primary decision source.

## Decision outcome → three execution paths

**After the decision tree, follow exactly one path:**

### Path A: Timestamp-Only Refresh
If the live-sync note and daily note are both current and accurate with no new durable items:
- Jump directly to **step 10** (read back verification).
- **Patch both timestamp locations in the same run** (they are independent text locations — missing one leaves drift):
  1. Patch the live-sync frontmatter `last_synced` field to current time.
  2. Patch the visible body line `_Last synced: ...._` separately to match the new time.
  - After patches, verify readback confirms both updated; if the visible line still shows the older time, patch it separately immediately.
  - **Always apply timestamp patches even if no new durable content appeared.** The timestamp signals "sync completed successfully at this time"; it is not conditional on finding new items. This is especially important when a prior cron attempt failed with an error (e.g. connection timeout, RuntimeError) — the successful timestamp refresh confirms the current run succeeded where the prior run did not.
- If today's daily note doesn't exist yet, create it with a minimal sync block (see `references/daily-note-bootstrap-logic.md`).
- If today's daily note already exists and is up-to-date, leave it unchanged unless it has its own visible timestamp line that needs refresh.
- **Report decision**: 
  - **Default**: Report "Timestamp refreshed to [TIME]; content unchanged." plus one sentence confirming the sync completed successfully (e.g. "No new durable changes since [date]"). This signals to downstream consumers that the sync ran and found no new work.
  - **[SILENT]**: Only return `[SILENT]` if the cron invocation explicitly sets a `SILENT:` flag or parameter in the job definition allowing silent delivery. Do not use [SILENT] based on inference alone — it requires explicit opt-in.

### Path B: Full Rewrite
If the decision tree found new durable items or notes are stale/drifted:
- Proceed to **step 4** below (session and log inspection).
- Rewrite the live-sync note content (step 6).
- Update or patch the daily note (step 9).
- Verify both files land correctly (step 11).

### Path C: Silent Suppression
If no new content AND cron caller explicitly accepts silent delivery:
- Return `[SILENT]` (no daily-note creation, no timestamp refresh, fully skipped).
- Only use this when instructed; otherwise prefer Path A (timestamp refresh).

4. **[Path B only]** If the decision tree indicates a **full rewrite** is needed, proceed with session and log inspection:
   - Check local high-signal hint files when present (caveat: **these often lag real-time activity** and may not reflect same-day cron runs or concurrent CLI work):
     - `~/.hermes/logs/hermes-memory-capture.jsonl`
     - `~/.hermes/logs/hermes-obsidian-file-events.jsonl`
     - `~/.hermes/state/obsidian-dirty-paths.json`
     - Prefer the newest tail of append-only JSONL logs first; for large files, inspect only the recent lines rather than trying to read the whole file at once.
     - If the JSONL logs are already large, first narrow with content search on the current date, recent session ids, or target note paths so you read only the relevant tail slice instead of brute-reading the file from line 1.
     - If a log read exceeds safety limits, use the reported `total_lines`/size hint and re-read a small tail window near the end rather than starting at line 1 again.
   - Browse recent sessions from the last 24 hours (typically up to 5). **For same-day sync work, `session_search` is the more reliable source than local hint files.**
     - **Note: When a prior cron sync already completed earlier today (e.g. morning run), look for new durable work that appeared after that sync's timestamp.** See `references/same-day-iterative-sync-pattern.md` for handling same-day chaining (when multiple syncs on the same calendar day make sense).
     - If recent results are crowded with earlier cron sync runs, treat those as note-maintenance context rather than primary source material.
     - Inspect at most one recent prior sync run when you need to preserve already-curated state, but prioritize substantive user/CLI sessions for genuinely new durable changes.
     - **Oversized session handling**: When `session_search(session_id=X)` returns output >100KB and is truncated, the tool response includes a temporary file path (e.g. `/tmp/hermes-results/toolu_....txt`) where the full output was saved. Use `read_file` on that temporary path. If the file is itself large (>1–2 MB), use `grep` with high-signal keywords (e.g. 'patch', 'skill', 'write_file', 'terminal', 'modified', feature names) to extract section boundaries before attempting a full read. See `references/large-session-dump-grep-recovery.md` for worked example and timing guidance.
     - If a full prior sync session dump is huge or transcript-heavy, do not brute-read it just because it is recent; prefer the current live-sync note, today's daily note, and local file-event telemetry as the continuity baseline, and only drill into a narrowed session slice when you need a specific durable fact.

5. Extract only durable items that survived the session as actual state, configuration, or verified result.
   - For maintenance/cleanup sessions, record only the final verified baseline: consolidated cron ownership, config invariants now in force, low-risk skill pruning that actually happened, and any intentionally deferred prune candidates.
   - If a deletion happened, say whether it was absorbed into a canonical umbrella or pruned as a clear orphan; do not imply a broader cleanup than what was verified.
6. Rewrite the live-sync note with a stable structure:
   - frontmatter (including `last_synced: <ISO timestamp>`)
   - visible body `_Last synced: <local date/time>_` line
   - scope
   - recent sessions
   - key durable themes
   - follow-ups
   - privacy notes
   
   **CRITICAL for Path B rewrites**: The frontmatter `last_synced` field and the visible body `_Last synced_` line are independent text locations. When rewriting the note, patch BOTH separately in the same run (not with a single edit). Patching only one leaves them drifted on disk and creates confusion on the next sync run. After patches, verify readback confirms both updated; if one still shows the older time, patch it immediately.
7. Ensure today's daily note exists and contains a `## Hermes Chat Sync` section.
8. If today's daily note does not exist yet, create a minimal note that contains the sync block only, even if that run found no new durable items. The daily note acts as a visibility signal that "Hermes ran today" — an empty or missing daily note makes it ambiguous whether no durable changes occurred or whether the sync ran but made no update. Always create it; populate it with at least the link and a note like "No new durable changes since prior sync" if no items warrant reporting. (Exception: If the caller explicitly asked for silent suppression AND no new content appeared, you may return [SILENT] instead of creating an empty-looking stub.)
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
- When bootstrapping a new daily note during a timestamp-only maintenance run (no new content found, but daily note doesn't exist yet), create the minimal sync block with the link and a concise bullet like "No new durable changes since prior sync" — this counts as successful verification. The newly-created daily note signals that "Hermes ran today," and its creation itself is the durable output of the maintenance run, not a durable change to Hermes work.
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

- **Frontmatter vs. visible body timestamps are separate edits**: The live-sync note contains two independent timestamp locations: (1) frontmatter `last_synced: <ISO timestamp>` and (2) visible body `_Last synced: <local date/time>_`. When rewriting the note (Path B full rewrite), you must patch BOTH in the same run using **separate patch calls** — they are not synchronized by a single edit. Patching only the frontmatter or only the visible line leaves them drifted on disk. After any timestamp refresh, verify readback confirms both updated; if one still shows the older time, patch it immediately rather than leaving it for the next run. This is especially critical for cron syncs: downstream consumers read the visible body line for human-friendly status; the frontmatter is metadata. Drift between them signals "sync may not have completed" to the next run.
- **Reference files are optional detail, not blocking dependencies**: The skill lists 23 support files (`references/*.md`) that provide worked examples and detailed decision matrices. These are enhancements for learning and verification, NOT required for operation. The canonical decision tree is **embedded inline in step 3** (`Quick inline logic` block). For cron jobs where reference files don't exist (or for speed), use the inline logic directly: (1) Both notes recent (last sync < 8 hours) and accurate? → **Path A**; (2) Notes stale, drifted, or missing sync metadata? → **Path B**; (3) No new content AND cron caller explicitly allows `[SILENT]` delivery? → **Path C**; (4) Otherwise? → **Path A** with verification. The reference files accelerate decision-making on edge cases (same-day iterative syncs, large session dumps, timezone offsets) but are not prerequisites. Do not treat their absence as a blocker.
- **Large session-dump files: grep-first recovery when read fails.** When you attempt to read a large session result (>100KB) via read_file and the tool returns empty output or timeout, do NOT retry the same read with offset/limit parameters. Instead: use `grep` or `grep -i` on the file path to extract high-signal keywords (e.g. "write_file", "patch", "commit", "skill", key feature names). This is faster and avoids the read failure. If grep succeeds, you have the section boundaries; pivot to structured data sources (SQLite for sessions, hermes-obsidian-file-events.jsonl for file traces, obsidian-dirty-paths.json for state). Only re-read specific line ranges if a grep match gives you concrete line anchors. Brute-reading from line 1 a second time will hit the same failure mode.
- Do not rewrite from session/log hints alone when the current live-sync note or daily note already contains validated durable state from an earlier run; read the existing note surfaces first and preserve the durable parts.
- Do not replace a populated daily note wholesale just to refresh the sync section; patch the `## Hermes Chat Sync` block in place unless the note is genuinely just a sync stub.
- **Timestamp-only refresh requires TWO separate patches**: frontmatter `last_synced` and visible body `_Last synced_` line are independent text locations. Patching only one leaves them drifted and creates confusion on the next sync run when you re-read the note and see mismatched timestamps. Always patch both in the same run and verify readback before finishing. If the second patch was missed, detect it during readback and patch it immediately rather than leaving it for the next run.
- If a run is timestamp-only maintenance on an already-created daily note, keep the daily note untouched unless its own visible timestamp line is stale; the live-sync note can carry the freshness signal. However, if the daily note is newly created during a timestamp-only maintenance run (no new content), still create it with the sync block to act as the "ran today" visibility signal — leave its visible timestamp as-is (no need to refresh a newly-created note). On the NEXT sync run same-day, if still no new content, leave the daily note unchanged (no need to re-patch its timestamp just because the live-sync note refreshed).
- **Daily notes often don't have visible timestamp lines.** The live-sync note typically exposes `_Last synced: ..._` in the body, but daily note sync blocks often just have bullets (link + 2-4 short items). Do not add a timestamp line to the daily note just because the live-sync note has one; they serve different purposes (live-sync = curated repository, daily note = quick reference). Leave the daily note without a visible timestamp unless it originally had one.
- Do not append a new large dated section to the live-sync note every run; rewrite it.
- Do not treat every recent session as durable; many are transient or superseded.
- Do not overfit to one session's wording when the lasting lesson is a broader operational state.
- Do not dump local logs into Obsidian; extract only the durable signal.
- Do not let both `~/.hermes/memories/MEMORY.md` and vault `MEMORY.md` grow into competing canonical sources for the same stable operational facts; decide which layer owns the fact and keep the other layer thinner.
- Do not hardcode the drift audit to a single dated daily note path; resolve the current daily note dynamically.
- Do not make the daily-note size threshold stricter than the sync policy itself; if the skill says 3–5 bullets, the audit threshold should allow 5.
- **Vault directory structure varies widely**: Do not assume daily notes live at a hardcoded path like `10 Daily/YYYY-MM-DD.md`. When the initial read for today's daily note fails, use `search_files(pattern='YYYY-MM-DD.md')` to discover the correct directory, then use that discovered path for all subsequent reads/writes in the sync run. Vaults commonly use `02 Daily Notes/`, `memory/`, `10 Daily/`, or variants. The discovered path becomes the source of truth for the current run.
- **[SILENT] threshold vs default reporting**: Path A (timestamp-only maintenance) defaults to a brief report confirming the sync ran. Suppress with `[SILENT]` only when the cron job's definition explicitly sets a `SILENT:` flag or policy — not based on inference about "nothing changed." This prevents ambiguity: downstream consumers distinguish "sync ran, no new content" (brief report) from "sync did not run or was skipped" ([SILENT]). For recurring cron jobs with no new durable work most days, a 1-line summary is the right signal density.

## Durable item triage — three-lens pattern (from references/durable-item-triage-patterns.md)

When the decision tree indicates new durable items *may* exist, scan 3–5 recent sessions through three lenses:

**Lens 1 — Configuration & Deployment**: config YAML/JSON changes that remain in effect, git commits pushed to a tracked branch (capture SHA + scope), active cron jobs, API endpoints/services started, package installs that are now in the environment. *Only changes that lasted from the session into now.*

**Lens 2 — Verified Fixes & Outcomes**: bugs fixed and confirmed resolved, security patches validated (`hermes doctor`), test results, skill patches confirmed (file size stable, syntax ok). *Only outcomes confirmed before the session ended — "I'll fix this next turn" does not count.*

**Lens 3 — Workflow & Process Changes**: new/updated cron jobs, scripts, automation workflows; decision trees or patterns that stabilized; new skill/reference documentation added; integration points wired in; process changes affecting how the system runs going forward.

**High-signal durable indicators**: git commit SHAs, `hermes doctor` resolved output, `hermes cron list` confirming new job, `skill_manage` patch confirmation, config before/after verification.
**Low-signal transient work** (usually skip): multiple recommendation rounds without final choice picked, test/spike branches without merge, back-and-forth debugging with no root cause found, config testing that was reverted.

**Filtering**: if decision tree says "probably timestamp-only", skim 3–5 sessions for all three lenses — any concrete hit (config pushed, fix verified, workflow stabilized) moves you to full-rewrite.

## Support files

**Reference files provide worked examples and edge-case guidance — they are optional enhancements, not blocking dependencies.** The canonical decision logic is embedded inline in step 3. Use reference files when you encounter same-day iterative syncs, oversized session results, timezone edge cases, or need verification of a borderline decision.

- `references/decision-tree-quick-reference.md` — fast 3-question decision logic for determining which path (A/B/C

## Feature Watch Publish Step (Denuto Pattern)

Source: Denuto `feature_watch/handlers/publish_obsidian.py`.

Writing normalized research findings to Obsidian vault. This is the publish step
of the Feature Watch pipeline — see `hermes-research-ops` for the full pipeline.

```python
from pathlib import Path
import json
import time

def publish_to_obsidian(
    findings: list[dict],
    vault_path: str = "~/Documents/SecondBrain/research/",
    mode: str = "daily",
) -> str:
    """Write findings to Obsidian vault. Returns path to created note."""
    vault = Path(vault_path).expanduser()
    vault.mkdir(parents=True, exist_ok=True)

    date_str = time.strftime("%Y-%m-%d")
    note_path = vault / f"feature-watch-{mode}-{date_str}.md"

    # Build markdown note
    sections = ["# Feature Watch Report", f"Date: {date_str}", f"Mode: {mode}", ""]

    new_findings = [f for f in findings if f.get("novelty") == "new"]
    extended = [f for f in findings if f.get("novelty") == "extended"]

    if new_findings:
        sections.append("## New Findings")
        for f in new_findings:
            sections.append(f"- **{f.get('feature', 'Unknown')}** ({f.get('vendor', 'Unknown')})")
            if f.get("description"):
                sections.append(f"  {f['description']}")

    if extended:
        sections.append("\n## Extended/Updated Findings")
        for f in extended:
            sections.append(f"- **{f.get('feature', 'Unknown')}** ({f.get('vendor', 'Unknown')})")

    sections.append(f"\n*Total: {len(findings)} findings, {len(new_findings)} new, {len(extended)} extended*")

    note_path.write_text("\n".join(sections), encoding="utf-8")
    return str(note_path)
```

### Notes Path Convention

Research notes go to: `~/Documents/SecondBrain/research/feature-watch-{mode}-{date}.md`

For incremental updates (append to existing daily note vs. create new):
- If note for today already exists and it's the same mode → append new findings
- Otherwise → create new note

See also: `hermes-research-ops` for the full seed → submit → poll → normalize → publish pipeline.
- `references/decision-tree-quick-reference.md` — fast 3-question decision logic for determining which path (A/B/C) to take; includes quick heuristics for session search and verification checklist.
- `references/live-sync-note-template.md` — compact template and section checklist for the rewritten sync note.
- `references/daily-note-discovery-worked-example.md` — concrete walkthrough of vault directory discovery when daily-note paths vary (e.g., `10 Daily/` vs `02 Daily Notes/` vs `memory/`); shows when and how to use `search_files` to discover the canonical directory, and why hardcoding paths breaks across different vaults.
- `references/timestamp-only-maintenance-decision-tree.md` — decision matrix for determining whether a sync run requires full rewrite vs. timestamp refresh only; includes efficiency notes and the pitfall of confusing "no new sessions" with "no new durable items."
- `references/timestamp-only-maintenance-worked-example.md` — concrete walk-through of a real timestamp-only maintenance sync (July 2, 2026, 16:08 AEST): how to recognize the decision-tree outcome, patch both timestamps, verify readback, and keep the daily note stable.
- `references/timestamp-only-maintenance-no-daily-timestamp.md` — focused worked example of timestamp-only maintenance when the daily note has no visible timestamp line (July 18, 2026, 18:47 AEST): why the live-sync and daily note timestamps move independently, and the pitfall of adding a timestamp to a daily note that never had one.
- `references/large-session-dump-grep-recovery.md` — when session_search returns >100KB, use grep-first recovery to extract high-signal keywords before attempting read_file; includes worked example and timing comparison showing why grep beats brute-reading from line 1.
- `references/durable-item-triage-patterns.md` — three-lens (Configuration & Deployment, Verified Fixes, Workflow Changes) triage pattern for separating durable state changes from transient work when reviewing recent sessions; includes recognition shortcuts, high-signal indicators, and session-to-sync-note mapping.
- `references/full-rewrite-same-day-sync-worked-example.md` — concrete walk-through of a full-rewrite sync (July 2, 2026, 19:11 AEST) that found new durable items after an earlier same-day sync: how to distinguish signal from noise, add new session sections, update themes and follow-ups, and verify both files land correctly.
- `references/single-item-rewrite-same-day-sync.md` — concrete walk-through of a focused single-item rewrite (July 4, 2026, 18:24 AEST): when one clean fix appears after a recent sync, how to add a session section and bump the daily-note cluster count without over-extending. Illustrates surgical rewrite pattern.
- `references/cron-sync-high-signal-sessions-pattern.md` — recognition patterns for multi-cluster operational sessions (config+port, infrastructure+integration, etc.) that warrant full rewrite; decision table and writing guidance for cron contexts.
- `references/memory-layering-and-drift-checks.md` — source-of-truth map for Hermes memory vs Obsidian vs session/log layers, plus duplication/drift review prompts.
- `references/memory-drift-audit-pattern.md` — lightweight silent-audit pattern for catching reintroduced overlap between Hermes durable memory and vault `MEMORY.md`, plus near-duplicate, overgrowth, and audit-note patterns.
- `references/timestamp-refresh-and-partial-read-pitfalls.md` — notes on keeping frontmatter and visible timestamps aligned and re-reading full files before overwrite.
- `references/daily-note-bootstrap-and-timestamp-sync.md` — how to bootstrap a missing daily note and keep the sync timestamp aligned after final verification.
- `references/daily-note-bootstrap-logic.md` — clarity on when to create a minimal daily note vs. when silent suppression is appropriate; explains the visibility signal principle and patterns for zero-changes runs.
- `references/mixed-cluster-sync-pattern.md` — how to keep multiple still-current durable clusters separate in one sync rewrite without collapsing them into a vague maintenance bullet.
- `references/maintenance-baseline-and-prune-reporting.md` — how to summarize maintenance-only sessions as a verified end-state baseline without overstating what was pruned.
- `references/cron-job-session-hygiene-pattern.md` — when a cron job's session retention policy is durable and notable (two-tier cleanup, separate hygiene script, etc.), how to report it in sync notes with verification and design rationale.
- `references/same-day-iterative-sync-pattern.md` — handling cron sync runs that detect new durable work within the same calendar day (e.g., morning sync finds nothing, afternoon work occurs, evening sync discovers it). Covers the decision tree for partial rewrites vs. timestamp-only refresh when chaining multiple syncs same-day.
- `references/cron-sync-full-rewrite-pattern.md` — when a **scheduled cron job** (not user-triggered) fires on its regular schedule, use the decision tree to determine whether new durable work from the prior 24 hours warrants a full rewrite or only timestamp-only maintenance. Includes a worked example (July 9, 2026) and pitfalls around confusing \"cron job\" with \"no changes\" or \"no rewrite needed.\"
- `references/timestamp-only-with-daily-bootstrap-july22-2026.md` — concrete walk-through of timestamp-only maintenance when today's daily note doesn't exist: decision tree application, both timestamp patches, daily-note bootstrap as visibility signal, and reporting boundary (brief summary by default, [SILENT] only with explicit opt-in).
- `references/timestamp-only-with-daily-bootstrap-july31-2026.md` — second worked example (July 31, 2026) showing the same pattern applied in a later cron run: validates pattern consistency across weeks of recurring syncs, demonstrates timestamp resolution from runtime `date` output, and clarifies the distinction between \"no new content found\" and \"cron explicitly requests silent delivery.\"
- `references/timestamp-timezone-pattern-july2026.md` — timezone conversion pattern for vault notes: when frontmatter uses UTC and visible body uses local timezone (AEST), why both patches must happen together, how to extract UTC from runtime `date` output without arithmetic, and the pitfall of manual hour offset calculation across DST transitions.
