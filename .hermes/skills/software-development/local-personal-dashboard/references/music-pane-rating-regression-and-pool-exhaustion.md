# Music pane rating regression and pool exhaustion

Use this pattern when a recommendation pane starts showing fewer than the target number of cards after many saves, and some remaining cards refuse to save ratings.

## Symptom pair
- Recommendation count shrinks below the intended steady-state size because rated/seen items are excluded and the remaining curated pool is too shallow.
- Save buttons fail only for some items, especially titles or IDs containing apostrophes/quotes such as `Burnin' for You` or `It's My Life`.

These two symptoms often appear together late in a feedback loop rollout: the pane looks partly alive, but the remaining unrated quote-bearing items expose the escaping bug.

## Root-cause checklist
1. Count the durable ratings already stored for that pane.
2. Count the total unique candidate items in the curated pool.
3. Compare the two counts; if `remaining candidates < target visible count`, the pool itself is exhausted.
4. Inspect the rendered save-button wiring for quote-sensitive IDs.
   - Inline `onclick='save(...)'` handlers are the main risk.
   - Even `JSON.stringify`-escaped payloads are more brittle than listener attachment via DOM methods or delegated events.

## Preferred fix
- Replace inline `onclick` save wiring with one of:
  - event delegation on the pane/container/body plus `data-kind` / `data-item-id` attributes
  - direct `addEventListener` attachment after rendering
- Keep `item_id` in `data-*` attributes and pass it to the save function without URI-encoding gymnastics unless the transport specifically needs encoding.
- Expand the curated candidate pool enough that, after excluding all previously rated items, the pane can still return the target steady-state count.

## Verification recipe
1. Hit the recommendation endpoint and confirm it returns the full target count again.
2. Exercise the real save endpoint with at least two quote-bearing IDs.
3. Read the durable store back and confirm both ratings persisted.
4. Hit the recommendation endpoint again and confirm the pane still returns the full target count after those new saves.

## Concrete example
- Stored music ratings had grown to 17 while the curated music candidate pool only had 21 unique songs, leaving 4 unrated songs and causing the music pane to shrink to 3 visible cards.
- Two of the remaining songs contained apostrophes, and the inline save-button wiring failed on them.
- Fix: switch to delegated click handling with `data-item-id`, then deepen the curated pool.
