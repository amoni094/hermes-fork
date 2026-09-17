# Web feed HTML fallback for blocked JSON/API endpoints

Use this when a web-facing data source has:
- a JSON endpoint that returns 4xx/5xx intermittently
- a rendered HTML page that still contains machine-readable attributes
- a downstream collector that should degrade gracefully instead of failing hard

Observed pattern:
- Public Reddit JSON endpoints may be blocked while the rendered community page still includes structured `<shreddit-post>` elements with attributes like `post-title`, `permalink`, `score`, and `comment-count`.
- A collector can preserve usefulness by trying the canonical JSON/API path first, then falling back to the rendered HTML path, and returning partial data plus a source-specific error rather than an all-or-nothing failure.

Practical steps:
1. Reproduce both the API route and the rendered page route.
2. Inspect the HTML for stable data-bearing attributes before falling back to brittle text scraping.
3. Prefer attributes and structured tags over visible text when available.
4. If one source branch fails and another succeeds, keep the successful branch and surface the failing branch explicitly.
5. Re-run the consumer after the fallback is added to verify the script returns real items instead of an empty report.
