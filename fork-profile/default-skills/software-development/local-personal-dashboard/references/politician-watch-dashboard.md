# Politician watch dashboard pattern

Use this for local dashboards that need a searchable public-figure directory plus a narrower live-watch pane.

## Architecture split

1. Build the full directory from the most stable accessible roster source first.
   - In this session, current federal MP/senator coverage came from current Wikipedia membership tables.
   - Directory completeness and live-detail completeness are different goals; do not tie them together.

2. Add enrichment layers separately.
   - Wikidata: good for photos, official websites, X, Instagram when populated.
   - Official ministry/department pages: useful for portfolio and department drill-downs, but expect inconsistent markup or anti-bot behavior.
   - Monitored headline pages: useful for recent quotes, announcements, controversies, and mention scoring.

3. Keep the UI honest.
   - Search should cover the full directory even when enrichment is partial.
   - Missing live detail should render as explicit empty states, not silently disappear.
   - If last-24h mention ranking is only derived from a subset of accessible sources, label it as a monitored-source approximation.

## Good source pattern from this session

- Full roster:
  - `https://en.wikipedia.org/wiki/Members_of_the_Australian_House_of_Representatives,_2025%E2%80%932028`
  - `https://en.wikipedia.org/wiki/Members_of_the_Australian_Senate,_2025%E2%80%932028`
- Metadata enrichment:
  - Wikidata `wbgetentities` API by enwiki title
- Monitored-source ranking / quote inputs:
  - ABC politics page
  - PM media page
  - major party media/news pages
- Portfolio/department drill-down:
  - map known portfolio keywords to department/news sources

## Ranking rule

When the user asks for “top 10 most mentioned in the last 24h” but you only have open/public sources:
- compute ranking from the monitored accessible surfaces you actually queried
- state which surfaces those are
- call the result an approximation, not a complete media index

## Verification pattern

- verify refresh script output count (directory size + top-card count)
- verify search opens a detail view
- verify top-card click opens the same detail view shape
- verify empty states exist for partial profiles
- verify build/test/lint still pass after adding dashboard-specific test tooling

## Vite + Vitest note

If adding Vitest to an existing Vite React dashboard causes config-type friction, keep `vite.config.ts` build-only and move test config to a separate `vitest.config.ts`. This preserves build stability while keeping jsdom/test setup explicit.
