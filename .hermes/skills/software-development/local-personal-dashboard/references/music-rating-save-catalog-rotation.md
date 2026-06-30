# Music rating save vs catalog rotation

Problem class:
- A dashboard pane shows visible music recommendation cards from a dynamic pool.
- First save works, but changing the rating on the same visible item later returns HTTP 400 `unknown item`.
- The visible card is legitimate; the failure happens because the backend only accepts items still present in the current regenerated catalog.

Reproduction shape:
1. Fetch `/api/music` and choose one returned item.
2. POST `/api/rate` with `kind=music`, that `item_id`, and a valid rating.
3. Let the pane refresh or let the backend regenerate the live catalog.
4. POST another valid rating for the same `item_id`.
5. Pre-fix symptom: HTTP 400 `{"error": "unknown item"}` even though the item was just shown/saved.

Root cause:
- Save logic resolves `item_id` only against the current candidate catalog.
- Dynamic panes can rotate after save/refill, so a card that was valid on render is no longer present in the next live pool.
- The backend rejects a rerate instead of using durable knowledge about the item.

Fix pattern:
- Frontend: include stable card metadata in the save request body.
  - Minimum practical fields for music: `title`, `artist`, `seed_artist`, `media_type`.
  - Render these onto the card as `data-*` attributes and POST them with `item_id`, `kind`, and `rating`.
- Backend: resolve rating saves in this order:
  1. current live catalog
  2. existing durable rating row for that `item_id`
  3. client-supplied metadata from the rendered card
- Keep validation on rating range and supported kind, but do not equate "not in current pool" with "invalid item" for a visible card.

Verification pattern:
- Live API check:
  - Save one visible music item.
  - Save a changed rating for that same item after refresh/rotation.
  - Confirm repeated valid ratings no longer return HTTP 400.
- Regression test:
  - Save a music item into a temporary DB.
  - Simulate catalog rotation/unavailability.
  - Save a new rating for the same `item_id` using metadata.
  - Assert the durable row updates instead of raising `unknown item`.

Implementation notes:
- This bug class is adjacent to quote-sensitive handler bugs but distinct from them.
- If the UI previously had inline `onclick` issues, fix those too, but do not stop there; a delegated listener can still hit backend catalog-rotation failures.
- Useful user-facing fallback: when any save still fails, surface the backend error text instead of a generic `HTTP 400` so the distinction is visible during debugging.
