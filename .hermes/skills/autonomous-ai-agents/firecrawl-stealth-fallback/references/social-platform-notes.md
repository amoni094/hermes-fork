# Public social-profile extraction notes

Scope: public YouTube, X, Instagram, and Facebook pages where generic extraction often returns incomplete content or bot-gated shells.

## Practical fallback order
1. Try normal extractor / static fetch first.
2. If the page is JS-heavy or the static HTML lacks post links/text, use a real browser render.
3. Prefer platform-specific public extraction when available (example: YouTube via `yt-dlp`).
4. Keep browser-rendered HTML as a reusable intermediate artifact for downstream regex/JSON extraction.

## Durable lessons from this session
- A small local Chromium renderer is often enough for public social pages; you do not always need full MCP-driven browser orchestration.
- For Facebook public pages, rendered DOM can expose post/reel data that raw `urllib` misses.
- Facebook recent-post extraction worked by scanning rendered HTML for:
  - `"creation_time":<unix_ts>`
  - `"url":"...facebook.com/reel/..."` or `/posts/` or `/videos/`
  - `"text":"..."` payloads for message text
- Decode extracted JSON-string text with `json.loads(f'"{raw}"')` instead of `unicode_escape`; this avoids surrogate/encoding trouble when generating UTF-8 output.
- Deduplicate Facebook URLs before emitting summaries; rendered blobs can repeat the same reel/post multiple times.
- When rendered HTML is large, allow a larger capture budget/byte cap before concluding the content is absent.

## Platform notes
- YouTube: use `yt-dlp` first for recent public videos; it is more stable than generic scraping.
- X / Instagram: rendered metadata retrieval is feasible, but reliable recent-post extraction is still much less dependable without authenticated session reuse/cookies.
- Facebook: public pages/reels are currently the best fit for rendered-DOM fallback extraction in this environment.

## X/Twitter tweet extraction recipe (browser-free)

`browser_navigate` reliably times out on x.com (120s timeout, Chromium/JS rendering issues). Do not use it as the primary path for tweet content.

Proven fallback sequence for extracting full tweet body:
1. `web_search(query="<username> site:x.com <tweet_id>")` — returns snippet with the first ~200 chars of the tweet and the exact URL.
2. `web_extract(urls=["https://x.com/<user>/status/<id>"])` — returns near-complete tweet text including thread/reply content even without login, because x.com sends enough static HTML for the extractor.

This two-step sequence reliably recovers full tweet text (lists, threads, embedded links) without any browser session. The web_search snippet confirms the tweet exists and the URL is right before paying for the extract call.

Pitfalls:
- `browser_navigate` on x.com almost always times out in this environment; skip it.
- `web_extract` alone on a tweet URL sometimes returns only shell HTML; the search-first step is worth doing anyway to get the snippet as a fast sanity check.
- Quoted tweets and image-only tweets may have incomplete body; note this in the response if body seems short.

## Anti-bot tactics worth preserving
- Reuse a real browser engine rather than only Python HTTP clients for JS-heavy social sites.
- Keep request volume low and cache rendered HTML per URL.
- Prefer a fixed browser profile/session per target when cookies/storage help reveal public content.
- Fall back from raw HTTP to rendered browser; do not start every target with the heaviest path.
