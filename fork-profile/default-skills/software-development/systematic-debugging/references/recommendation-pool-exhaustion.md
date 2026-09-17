# Recommendation pool exhaustion in refreshable UIs

Use when a dashboard or recommendation panel seems to stop refreshing after repeated save/rate actions.

## Symptom pattern
- The refresh button appears dead or returns the same empty state.
- Saving/rating a card removes it, but no replacement appears.
- Health checks still pass, so the app looks "up" while the recommendation surface is effectively broken.

## Common root cause
The backend permanently excludes all previously rated/seen items. After enough interactions, the unseen pool is exhausted and the endpoint returns an empty recommendations array. The frontend is often fine; it just has nothing left to render.

## Minimal reproduction
1. Hit the refresh endpoint directly and record recommendation count.
2. Inspect saved ratings/seen-state volume.
3. Re-hit the same endpoint after enough saved interactions.
4. If the endpoint returns `[]`, reproduce the incremental refill path separately:
   - save/rate one visible item
   - request one replacement while excluding currently visible ids
   - confirm whether the replacement endpoint also returns empty

## What to verify
- Full refresh endpoint output, not just page load or `/healthz`
- Incremental refill path output after a save/rate action
- Whether exclusion logic is:
  - visible-only (good for avoiding duplicates in the current view)
  - permanent across all history (can exhaust the pool)
- Whether rated items can safely re-enter with a visible `user_rating` / seen chip

## Safe fix pattern
- Use unseen-first selection.
- If unseen items are exhausted, fall back to previously rated items instead of returning an empty list silently.
- Keep current visible ids excluded so the same screen does not duplicate cards.
- Surface fallback clearly in the note/copy so the user understands refresh is revisiting prior picks.
- If ratings influence ordering, preserve that signal during fallback rather than randomizing everything.

## Good verification sequence
1. Syntax/compile check the touched code.
2. Restart or reload the live service.
3. Confirm the refresh endpoint now returns non-empty recommendations.
4. Simulate one save/rate request and verify a replacement recommendation is returned.
5. Confirm revisited items expose prior rating state in the payload/UI.

## Reporting language
Prefer: "The UI was not the root cause; the backend exhausted the unseen recommendation pool and returned empty results."
Avoid: "The refresh button was broken" unless click handling or network dispatch actually failed.
