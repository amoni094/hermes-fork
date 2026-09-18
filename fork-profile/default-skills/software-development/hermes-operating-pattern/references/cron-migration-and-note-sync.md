# Hermes cron migration and note sync

Session-derived durable lesson for the Hermes operating pattern.

## What changed in this run

- Hermes cron jobs replaced the older `siegward-*` naming in the live scheduler for the Hermes maintenance/research cadence.
- Obsidian policy notes were updated to point at the Hermes job names and IDs.
- The live cron registry was verified after creation with `cronjob action=list`.
- Some historical/archive notes still contain `siegward-*` references; that is acceptable unless the user explicitly asks for a full historical rename.

## Practical verification pattern

1. Create or update the Hermes cron jobs.
2. Read back the cron registry and confirm the job IDs, schedules, delivery mode, and enabled state.
3. Update the notes that describe the active workflow to use the Hermes names.
4. Re-read the edited notes and search for stale references in the active policy surface.
5. Leave historical notes alone unless they are part of the user’s requested scope.

## Useful wording

- Prefer “Hermes cron” or “Hermes cron job” for the live scheduler.
- Keep the specific job name and job ID together when the note is describing an active schedule.
- Use “historical/archive notes” when explaining why older names remain in past-dated material.
