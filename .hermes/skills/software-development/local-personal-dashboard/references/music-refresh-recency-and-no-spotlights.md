# Music refresh ranking and spotlight removal

Use this pattern when a local dashboard's music pane must stay fresh after many ratings while staying aligned to the user's explicit content-shape preferences.

## Problem shape
- The pane excludes already rated tracks, so the original shortlist can run dry.
- A simple fallback can refill the pane, but may drift into the wrong card type (for example artist-only spotlight entries) if the user really wants song recommendations.
- The user may want ranking driven by multiple time horizons, not a flat all-time score.

## Durable approach
1. Build a deeper candidate catalog than the initial curated shortlist.
   - Start with the normal curated neighbor-song candidates.
   - Expand with local seed tracks.
   - Optionally keep artist-only refresh entries in the underlying catalog for future experimentation, but do not emit them if the user has prohibited them.
2. Add a persistent refresh cache for exhaustion recovery.
   - Keep a small local cache file of auto-refreshed song candidates so the pane can recover after many ratings without rewriting the curated seed data.
   - Trigger a refresh when any of these are true: the cache is older than 24 hours, the user has added 10 new music ratings since the last refresh, or the unseen song pool has fallen below the dashboard's minimum target.
   - Use real song-level refill items from a lightweight external catalog/search source when available; store stable `item_id`, `artist`, `song`, `seed_artist`, `reason`, and `source_type` fields so the refreshed items behave like normal candidates.
   - Set and expose an explicit minimum unseen-song target (for example 20) in the API payload so pool-health checks can verify the contract directly.
3. Score each candidate with a blended preference model:
   - lifetime / overall historical taste
   - last 30 days of ratings
   - most recent ratings, weighted strongest
   - a small boost for auto-refreshed real songs so the refill pool can actually surface after exhaustion
4. Keep the ranking explainable.
   - Expose the scoring ingredients in the item reason text so live API verification can confirm the signals are actually flowing through.
5. Treat ratings as seen/heard state by default.
   - Exclude every rated item from the live recommendation surface.
   - Re-run the refresh-threshold check after each saved music rating so the pool replenishes automatically after every 10 new ratings.
   - Do not repopulate with previously rated items just to keep the pane full.
6. Treat explicit UX bans literally.
   - If the user says no artist spotlights, skip `song == 'Artist Spotlight'` candidates before scoring/selection and verify the live API payload contains none.

## Verification pattern
- Syntax-check the dashboard module after the edit.
- Restart the running dashboard service.
- Force one refresh in code if you need to validate the refill path immediately, then fetch the live music API, not just helper output.
- Check:
  - `pool_target` matches the intended minimum unseen-song contract
  - `unseen_song_pool` is at or above that target when refill succeeds
  - target item count still returns when enough unseen songs exist
  - no overlap with rated music in SQLite
  - banned card types (for example `Artist Spotlight`) are absent from the live payload
  - refresh metadata reports whether a refill happened and why (for example daily refresh, 10 new ratings, or pool below minimum)

## Why this matters
A partial fix that only downranks the wrong card type is not enough when the user explicitly banned it. This is a product requirement, not a ranking preference.