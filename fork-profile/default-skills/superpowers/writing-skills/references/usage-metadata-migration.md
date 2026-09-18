# Usage Metadata Migration Pattern

Use this when a skill-library cleanup pass reveals that `.usage.json` keys no longer line up with active skill names.

## When to use
- inventory counts disagree across live files, CLI listings, and usage metadata
- historical skill names were renamed, absorbed into umbrellas, or archived
- you need accurate ranking/pruning signals without losing historical usage

## Safe migration pattern
1. Build a replacement map first.
   - separate pure aliases from true replacements
   - allow unresolved historical keys to remain unresolved instead of forcing a bad mapping
2. Back up the raw `.usage.json` before any mutation.
3. Merge old entries into the replacement skill conservatively:
   - add `use_count`, `view_count`, and `patch_count`
   - keep earliest `created_at`
   - keep latest `last_used_at` / `last_viewed_at` / `last_patched_at`
   - preserve `pinned` if either side is pinned
4. Regenerate the authoritative inventory after migration.
5. Verify the stale-key count actually drops.
6. Keep a migration report in the repo so the merge history is explainable later.

## Rule
Do not mutate usage metadata blindly just because a stale key exists. A documented unresolved historical key is better than a fabricated replacement.

## Outputs worth keeping
- replacement map
- backup path
- migration report
- regenerated authoritative inventory
