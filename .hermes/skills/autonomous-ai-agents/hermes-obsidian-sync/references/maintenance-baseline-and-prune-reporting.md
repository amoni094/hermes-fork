# Maintenance baseline and prune reporting

Use this reference when the synced sessions are mostly Hermes housekeeping rather than feature work.

Keep the live-sync note focused on the verified end state:
- which cron jobs were consolidated or replaced
- which config invariants are now enforced
- which skills were actually deleted
- whether each deletion was `absorbed_into` a canonical umbrella or pruned as an orphan
- which zero-use or overlap candidates were intentionally left in place pending review

Reporting pattern:
1. State the new canonical owner for the maintenance area.
2. State the verified config/runtime baseline now in force.
3. List only low-risk deletions that actually occurred.
4. Name deferred candidates explicitly as deferred, not implicitly completed.
5. After maintenance edits, refresh the visible sync timestamps only after the final verified content lands.

Avoid:
- vague claims like "cleanup completed" when only a narrow subset was pruned
- presenting a review shortlist as if those skills were deleted
- recording every intermediate candidate considered during the session
