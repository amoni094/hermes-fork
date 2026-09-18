# Install-status inventory and Firefox history pattern

## Install-status inventory pattern
When the user asks for an inventory of requested GitHub/git links that are or are not locally installed:

1. `session_search` to collect candidate repos the user asked to implement.
2. If broadening the source set, inspect direct sources too (e.g. Firefox `places.sqlite`) as a separate bucket.
3. Live local evidence to classify each item:
   - source clone present with matching git remote
   - binary/command installed but no source clone
   - plugin/integration present but not a standalone clone
   - not found locally
4. Report in buckets, not a flat list.
5. Keep provenance explicit — distinguish:
   - explicitly requested to implement
   - merely browsed/viewed in history
   - non-repo/profile/settings/login pages (exclude unless user asked for all GitHub activity)
6. Ambiguous cases (repo URL exists but repo 404s, binary present but source missing) go in a separate section.
7. A prior session saying something was "implemented" is not enough — verify against live filesystem and installed commands.

## Firefox-history specific pattern
- Prefer the live SQLite history DB over session recollection when the user asks what they viewed.
- Query by a concrete time window, then normalize URLs to repo roots before deduping.
- Exclude account/settings/login/oauth/password-reset pages unless the user wants all GitHub activity.
- If a history hit resolves to a repo-like URL but the page title says "Page not found", keep as browsed-item note, not as evidence the repo is valid.
- Do not merge "explicitly asked to implement" and "looked at in Firefox" into one flat list unless the user asked for that.
