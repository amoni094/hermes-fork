# Federal legislation and social-summary patterns

Use this reference when a local dashboard needs a federal-politics legislation pane plus public-profile social summaries.

## Federal legislation tracker pattern

Goals
- Keep the pane federal-only when the user asks for federal politics.
- Keep the bill itself as the focal object.
- Preserve APH linkage even when direct APH scraping is brittle.
- Keep coverage explainable and avoid junk sources.

Recommended model
1. Maintain explicit seeded bill records in refresh code for the currently relevant federal themes.
   - Store: `theme`, `billId`, `title`, `aphHref`, `relatedPolicyIds`, a user-facing `status`, a concise `summary`, and a small `history` timeline.
2. Use resilient coverage feeds around the seeded bill.
   - Google News RSS for broad coverage.
   - Official/party query lanes for announcement surfaces.
3. Keep APH as the canonical visible link.
   - Show the APH bill page and bill reference prominently on the card.
   - Secondary monitoring/search links can stay available, but they should not visually outrank the APH link.
4. Filter unwanted domains explicitly.
   - If the user excludes YouTube, filter `youtube.com` and `youtu.be` from the legislation coverage lane before writing the generated artifact.
5. Tie each bill to the dashboard model.
   - Prefer bills that map to existing domestic-policy lanes via `relatedPolicyIds`.
   - If a bill is not tied to an existing lane, justify it as independently trending federal debate and say so in the status/summary.
6. Keep the UI compressed.
   - Main card: theme, bill title, bill ID, APH link, compact status, recent timeline.
   - Collapsed details: news coverage, official announcements, quotes for/against.

Good user-facing phrasing
- "Federal bills only. Each card prioritises the APH bill page and bill reference, with optional coverage and quote context tucked behind expandable details."

Avoid
- Leaving "direct APH fetch blocked" or similar acquisition complaints in the visible product copy once the seeded/fallback model is working.
- Mixing state and federal bills in the same pane after the user asked for federal only.
- Allowing a generic search result page to become the primary visible bill link when you already have a stable APH page URL.

## Production-gated diagnostics pattern

Use when the user wants a clean dashboard for regular use but still wants operational telemetry available during testing.

Recommended model
- Gate diagnostics with environment checks.
- In Vite/React, `if (import.meta.env.PROD) return null` is a simple pattern for hiding a diagnostics component in production.
- Keep non-prod wording explicit that the panel is diagnostic, not part of the normal product UI.

Verify
- Production build hides ingestion/source-health cards.
- Non-prod/dev build still renders them for testing.

## Social summary bullets from public profile metadata

Use when the existing social section only shows placeholder prose such as "surfaced from scraped official or public profiles".

Recommended model
1. Start from durable profile URLs.
   - Prefer canonical X/Instagram/Facebook/LinkedIn/TikTok profile links.
2. Fetch a small slice of the page and extract metadata.
   - `og:title`
   - `og:description`
   - `twitter:description`
   - fallback `<title>`
3. Build top-N summary bullets from that metadata.
   - Title
   - concise summary
   - link
   - source label/platform
4. Fall back honestly.
   - If no useful metadata is exposed, use a compact fallback like "Public X profile detected during refresh; open the link for the current social lane."
   - This is still better than vague scrape-process prose.

Caveat
- Platform pages vary widely; some profiles will still only yield generic metadata. The durable lesson is to prefer page-derived metadata when available, not to promise rich summaries for every platform/profile.
