---
name: hermes-skillspector-guard-maintenance
description: Fix and verify the local skillspector_guard cron/script when it times out by reusing unchanged cached reports instead of rescanning unchanged flagged skills every run.
created_by: agent
---

# Hermes Skillspector Guard Maintenance

Use when the local `skillspector-guard` cron job or `skillspector_guard.py --enforce` script starts timing out.

## Symptom
- Cron job `skillspector-guard` shows `error: Script timed out after 120s`.
- Direct run of `python ~/.hermes/scripts/skillspector_guard.py --enforce` hangs or times out.

## Root cause pattern
The guard script may only reuse cached scan reports for unchanged skills when they are baseline-approved or allowlisted. That causes unchanged flagged/non-approved skills to be rescanned on every run, which grows linearly with the skill count and can push the script past the cron timeout.

## Fix workflow
1. Read `~/.hermes/scripts/skillspector_guard.py`.
2. Find the `can_reuse_cache` logic in the main loop.
3. If cache reuse is gated on `previous_approved` or allowlisted hashes in addition to unchanged file hash + existing report, remove that extra gate.
4. The conservative target behavior is:
   - if `refresh_baseline` is false,
   - and cached result exists,
   - and cached hash matches current hash,
   - and cached report file exists,
   - then reuse cache.
5. Re-run the script directly:
   - `python ~/.hermes/scripts/skillspector_guard.py --enforce`
6. Verify it exits 0 and still performs real enforcement when needed.
7. Re-run the cron job and verify `last_status: ok`.

## Example patch shape
Old behavior:
- unchanged cached result reused only if baseline-approved OR allowlisted

Desired behavior:
- unchanged cached result reused for any unchanged skill with an existing cached report

## Verification
- Direct script run finishes within normal time.
- Cron `skillspector-guard` returns `execution_success: true`.
- `~/.hermes/skills-security/last-summary.json` is updated.
- If a genuinely new risky skill exists, quarantine still happens.

## Pitfalls
- Do not disable enforcement just to make the timeout disappear.
- Do not remove quarantine logic.
- Do not invalidate cache reuse for unchanged flagged skills; that is the main performance bug.
- Keep the change minimal so enforcement semantics remain intact.
