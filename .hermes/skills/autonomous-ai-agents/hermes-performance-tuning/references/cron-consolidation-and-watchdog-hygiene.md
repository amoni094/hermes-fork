# Cron consolidation and watchdog hygiene

Use this note when Hermes maintenance work includes too many overlapping cron jobs or a watchdog is noisy enough to look like platform drift.

## Audit pattern
1. List the live cron inventory first.
2. Group jobs by:
   - schedule cadence
   - agent vs no-agent mode
   - quiet-on-success vs chatty delivery
   - backing script/prompt surface
   - operational purpose
3. Read the backing scripts before merging jobs that only look similar from their names.
4. Merge only when the jobs share all of these:
   - same broad cadence expectations
   - same delivery style (usually silent/no-agent watchdogs)
   - same operational surface (for example general Hermes platform health)
5. Keep separate when a job is:
   - service-specific (`firecrawl-watchdog`-style)
   - policy/enforcement oriented (`skillspector-guard`-style)
   - a user-facing sync/curation job
   - a distinct risk gate or mutation gate

## Good consolidation target
Two quiet platform-health watchdogs running at the same cadence, each checking different pieces of Hermes config/runtime state, are good merge candidates. Fold them into one script with sectioned output and silence on success.

## Not a merge target
Do not merge a general platform watchdog with:
- a service-health restart loop
- a policy guard/enforcer
- a user-facing sync job
- a task-specific mutation or approval gate

## Transient failure rule
If a watchdog script fails because a date-specific note or file does not exist yet, then later passes unchanged, treat it as timing/schedule hygiene rather than a broken integration.

Preferred fixes:
- reschedule the job later in the day
- make the missing artifact a quiet no-op when absence is expected
- attach the check to the workflow that creates the artifact instead of a freestanding early cron tick

Do not encode the original one-off failure as a durable claim that the tool or script is broken.
