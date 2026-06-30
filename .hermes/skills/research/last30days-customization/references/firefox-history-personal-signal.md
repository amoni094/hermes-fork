# Firefox history personal-signal pattern

Use this when a news/research briefing should include a personalized section based on what the user has recently been browsing.

## Validated pattern
- Keep browsing-history extraction separate from public-source retrieval.
- Write the result to a dedicated artifact such as `browsing_history_signal`.
- Render it as a separate section, e.g. `## Personal signal` or `## From your browsing/history`.
- Include YouTube URLs/titles when they are visible in Firefox history.
- Label the section honestly: this is browser-history-derived signal, not direct private account/API watch history.

## Firefox path note for this environment class
On Fedora Silverblue with Flatpak Firefox, the profile root is under:
- `~/.var/app/org.mozilla.firefox/config/mozilla/firefox/`

Useful databases:
- `places.sqlite` — browsing history
- `cookies.sqlite` — cookie verification when source setup needs browser-backed auth

## Safe extraction pattern
- Do not query Firefox SQLite databases in place when the browser may have them open.
- Copy `places.sqlite` to a temporary file first, then open the temp copy with sqlite3.
- Pull a recent-visit sample ordered by `last_visit_date desc`.
- Pull a YouTube-focused slice with URL filters like `%youtube.com/%` and `%youtu.be/%`.
- Optionally aggregate repeated domains/themes before rendering.

## Verification signals from the session that established this pattern
- Firefox history was readable from `places.sqlite`.
- The profile contained thousands of history rows.
- YouTube URLs were present in significant volume.
- Recent rows included current GitHub and Gmail activity, confirming the history view was live and current.

## Rendering guidance
- Keep the section concise and high-signal.
- Emphasize repeated themes, not raw URL dumps.
- Use it to bias or contextualize the main briefing, not replace the 7-day / 24h / blindspot public-source structure.

## Pitfalls
- Do not imply you have direct YouTube account-history API access when you only read browser history.
- Do not bury browsing-history themes inside the main topical ranking; keep them visibly separate.
- Do not assume `~/.mozilla/firefox/` on Flatpak systems.
