# Obsidian Chat Live Sync

Use this pattern when syncing recent Hermes/Hermes chat activity into the vault as a durable, human-readable summary.

## Goal

Keep a current summary of recent chats without turning Obsidian into a transcript dump.

## Canonical Shape

- One rolling summary note, rewritten in place.
- One short mirror section in the current daily note.
- Optional recurring local cron job for refresh.

## Recommended Workflow

1. Browse recent sessions from the local session DB.
2. Read only the most relevant sessions from the target window.
3. Extract durable/high-signal items only:
   - workflow changes
   - verified configuration facts
   - cron changes
   - maintenance actions
   - reusable lessons
   - stable follow-ups
4. Rewrite the canonical summary note with:
   - frontmatter
   - last synced timestamp
   - scope
   - recent sessions
   - key durable themes
   - follow-ups
   - privacy notes
5. Update the current daily note with a small sync section linking back to the canonical note.
6. Read back the written files to verify the sync landed.

## Good Defaults

- Keep the canonical note under `04 Resources/`.
- Keep the daily-note section tiny: timestamp, link, 3-5 bullets.
- If nothing meaningful changed, keep the note stable instead of manufacturing new detail.

## Pitfalls

- Do not paste raw transcripts or long tool output into the vault.
- Do not append duplicate sections forever when a rewrite would do.
- Do not promote unverified claims from a session into durable notes.
- Do not let the daily note become the only durable location; keep the canonical summary separate.

## Automation Pattern

For recurring sync:

- use a local cron job
- rewrite the canonical note each run
- refresh the current daily note section
- keep delivery local
- verify by reading the files after writing

## Workspace Example

In this workspace, the pattern writes:

- `Documents/SecondBrain/04 Resources/Hermes Chat Live Sync.md`
- `Documents/SecondBrain/01 Daily/<YYYY-MM-DD Day>.md`

and can be scheduled as an hourly local cron sync.
