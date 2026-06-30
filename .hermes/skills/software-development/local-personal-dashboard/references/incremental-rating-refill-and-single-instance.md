# Incremental rating refill and single-instance localhost pattern

Use this pattern for lightweight local dashboards that show a fixed-size shortlist with inline save/rate controls.

## Problem shape
- User wants exactly one local server instance on a fixed port.
- User wants saving a rating to affect only the saved card, not re-randomize the entire visible list.
- Recommendation ids may contain apostrophes or other quote-sensitive characters.

## Backend pattern
- Keep `/healthz` cheap and always available.
- In `main()`, probe `http://127.0.0.1:<port>/healthz` before binding.
- If the probe returns `{ok: true}`, print a clear "already running" message and exit 0 instead of attempting a second bind.
- For recommendation routes, accept:
  - `limit` for small refill requests
  - repeated `exclude_id` query params for currently visible cards
- Exclude both rated/saved ids and caller-supplied `exclude_id` values from the candidate set.
- Keep the underlying recommendation pool larger than the visible pane size so refill-after-save can still return one fresh item.

## Frontend pattern
- Put a stable `data-item-id` on each rendered recommendation card.
- On save:
  1. POST the rating.
  2. Collect the currently visible card ids.
  3. Request exactly one replacement from the pane endpoint with `limit=1` plus the visible `exclude_id` values.
  4. Remove only the saved card.
  5. Append the replacement if one exists.
  6. Renumber the surviving cards in place.
- Do not call the full pane reload function after a save when the user wants the rest of the shortlist preserved.

## Quote-safe save wiring
- Do not interpolate raw titles/ids into inline JS string literals.
- Safe option: `const itemIdArg = JSON.stringify(encodeURIComponent(item.item_id))` and pass that to the handler.
- Alternative: bind events through DOM APIs and read ids from `data-*` attributes.

## Verification recipe
- Compile/syntax-check the app.
- Start the server and confirm `/healthz` returns ok.
- Launch the app a second time and verify it exits 0 with an "already running" message.
- Hit the recommendation endpoint with `limit=1` and one `exclude_id`; confirm the response returns at most one item and does not echo the excluded id.
- Exercise a quote-sensitive item id/title through the real save path and confirm the durable store updated.
- Confirm the recommendation pool still has enough unseen items to refill the pane after exclusions.

## Example session signal
- A save action refreshed the whole list, but the user wanted only the saved item to disappear and one new item to appear while the other entries stayed stable.
- A duplicate dashboard launch previously failed with `Address already in use`; fix the startup path so second launch becomes a clean no-op rather than an error path.
