# Rating-save escaping for local dashboard cards

Use this when a dashboard has inline per-card save/rate controls for music, movies, or similar recommendation items.

Problem pattern
- A card renderer builds inline handlers like `onclick="saveRating('music', '${itemId}', this)"`.
- Most items save correctly.
- Items whose ids or titles contain apostrophes or quotes fail intermittently because the rendered JavaScript string literal breaks in the browser.
- Example reproduction item: `Girlschool — C'mon Let's Go`.

Low-friction fix
- Keep the durable `item_id` URL-encoded for transport.
- When embedding it into inline JS, pass the encoded value through `JSON.stringify(...)` first and place it into the handler as a JavaScript string value.
- Better long-term alternatives: attach listeners with DOM methods or use `data-item-id` attributes and a delegated click handler.

Minimal safe pattern
```js
const itemId = encodeURIComponent(item.item_id);
const itemIdArg = JSON.stringify(itemId);
buttonHtml = `<button onclick='saveRating("music", ${itemIdArg}, this)'>Save rating</button>`;
```

Verification recipe
1. Compile or syntax-check the app after the patch.
2. Fetch the served HTML and confirm the save button now contains the `JSON.stringify`-escaped payload path rather than a raw nested quoted string.
3. Exercise the real save path for an item with an apostrophe/quote in the id/title.
4. Read the durable store back (for example SQLite) and confirm the exact item id and rating were persisted.

Concrete proof from this session
- App: `/var/home/rainbow/news_dashboard/app.py`
- Item: `Girlschool — C'mon Let's Go`
- Persisted result: rating `8/10` saved to `dashboard_state.sqlite3`
