# Blindspot and screen-section patterns

## Working file targets
- `~/.hermes/skills/research/last30days/scripts/lib/pipeline.py`
- `~/.hermes/skills/research/last30days/scripts/lib/render.py`

In this environment those paths resolved to the same underlying development tree under `/tmp/last30days-skill/...`, so path resolution should be checked before duplicate editing.

## Blindspot expansion pattern
Use a second-pass blindspot expansion only when the initial blindspot list is thin.

Recommended behavior:
- Build extra queries from topic-adjacent compound terms/entities first.
- Fall back to single tokens only after phrase candidates are exhausted.
- Reject generic engagement/time words such as:
  - weekly, popular, popularity, viral, trending, trend, hot
  - stars, starred, latest, best, top, news, update, updates
  - day, days, week, weeks, month, months, release, releases, review, reviews
- Split phrases on whitespace, hyphens, underscores, and slashes before filtering.
- Merge expansion results into blindspot extraction only, not the main candidate ranking.

Observed good outcome:
- ugly expansions like `weekly-popular` and `7-day` disappeared
- better expansions surfaced topic-adjacent entities/phrases instead

## Artifact pattern
Use `report.artifacts` for all new side-channel outputs.

Examples:
- `blindspot_expansion`
- `blindspots`
- `well_rated_screen_releases`

Keep payloads JSON-serializable and stable enough to inspect in `--emit json` tests.

## Well-rated movies/TV section pattern
Use a dedicated collector gated by screen-entertainment topic words.

Collection pattern that worked:
- query SearXNG directly for IMDb and Metacritic results
- extract title, snippet, URL, and rating clues from snippets/titles
- accept entries with either:
  - Metascore >= 75
  - IMDb >= 7.0
- merge duplicate titles across IMDb and Metacritic
- render a dedicated `## Well-Rated New Movies/TV` section

Useful cleanup rules:
- strip ` - IMDb`
- strip ` Reviews - Metacritic` and ` Review - Metacritic`
- strip dangling `(TV Series ...)`, `(Movie ...)`, and year suffix clutter when forming normalized titles

## Verification pattern
Run both forms:
1. JSON verification
   - confirm artifact key exists
   - inspect representative items and scores
2. Rendered verification
   - confirm the `##` section appears in the report
   - confirm labels, URLs, and evidence lines are readable

Example checks from a working session:
- blindspot JSON contained `blindspot_expansion.queries`
- rendered report contained `## Blindspots`
- screen JSON contained `well_rated_screen_releases.items`
- rendered report contained `## Well-Rated New Movies/TV`
