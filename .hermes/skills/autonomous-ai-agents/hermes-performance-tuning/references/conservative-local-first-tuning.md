# Conservative local-first Hermes tuning

Use this pattern when Hermes is functional but feels slower and heavier than expected, and the goal is to improve responsiveness without a major capability downgrade.

## Observed pattern this reference captures
- Main model migrated to `anthropic/claude-sonnet-4-6`, so remote inference via Anthropic is the primary path.
- Local auxiliary work used `qwen3:8b`, which is materially heavier than `llama3.2:3b` on CPU/RAM.
- Logs showed repeated compression activity and large-context turns.
- Resume/context behavior was still fairly verbose for CLI continuity.

## Conservative change set
1. Migrate Hermes config if outdated.
2. Keep the main model unchanged.
3. Move these auxiliary tasks from a heavier local model to a lighter local model:
   - compression
   - title_generation
   - triage_specifier
   - profile_describer
   - curator
4. Raise `compression.threshold` modestly (`0.5 -> 0.6`).
5. Make resume behavior more compact:
   - `display.resume_display = compact`
   - `display.resume_exchanges = 6`

## Why this helps
- Auxiliary local jobs can create steady CPU/RAM pressure even when the main model is remote.
- Compression frequency matters twice: it burns local auxiliary compute and can add latency before the main turn proceeds.
- Compact resume lowers default transcript injection on resumed sessions.

## Tradeoff framing
- This is a light optimization pass, not a maximal one.
- Expect some improvement in local resource use and session snappiness.
- Do not oversell token savings: a higher compression threshold slightly increases average prompt size, but often lowers local summarization churn enough to be worthwhile.

## Good verification checklist
- Confirm config migrated successfully.
- Confirm the new auxiliary model values were written.
- Confirm the lighter model exists locally and has enough context for the auxiliary role.
- Keep the previous config backup path when making edits so rollback is trivial.
