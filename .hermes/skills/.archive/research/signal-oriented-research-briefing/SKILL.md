---
name: signal-oriented-research-briefing
description: Build and extend live research briefings with sharper query packs, popularity-adjacent blindspots, and source-specific trend verification.
related_skills:
  - recent-news-briefing
  - competitor-news-monitor
  - rss-feeds
---

# Signal-Oriented Research Briefing

Use this when a user wants a current-events or trend briefing that should not stop at the most obvious ranked hits, especially when the workflow mixes broad news sources with source-specific trend feeds like GitHub.

## When to use

Trigger this skill when any of the following are true:
1. The user asks for "latest developments" or a recent briefing across several domains.
2. Broad search results are too noisy and need narrower per-category query packs.
3. The user wants a "what am I missing?" or blindspot-style view.
4. A source-specific trend feed exists and should be verified separately from general web/news results.

## Core workflow

1. Split the topic into narrow category query packs.
   - Prefer focused probes per domain over one broad omnibus query.
   - Keep categories distinct: politics, macro/finance, geopolitics, tech/AI, culture, autos, etc.

2. Verify the strongest source per category.
   - Use grounded news/web sources for news-heavy categories.
   - Use source-native trend sources for domains like GitHub.
   - Do not overclaim weak buckets; mark them thin/noisy instead.

3. Add a blindspot pass.
   - A blindspot is not just another top result.
   - Surface high-engagement adjacent items that were not centered in the main ranking because they are less lexically aligned, differently framed, or weakly corroborated.
   - Present blindspots as secondary signals, never as the main conclusion.

4. Keep confidence labels implicit but honest.
   - Strong buckets: summarize directly.
   - Moderate buckets: summarize with narrower scope.
   - Weak buckets: say the run was noisy/thin and avoid invented trend claims.
   - If a broad "last 24h" omnibus query returns generic crime/sports/local-police noise, do not pad the briefing with irrelevant items just because they are recent. Prefer the freshest high-signal items from the user's actual categories.

5. When the system has a source-specific trend feature, verify it live.
   - Confirm logs/output indicate the trend path actually ran.
   - Confirm the result object/rendered output contains the expected trend or blindspot section.
   - For Git/GitHub coverage, do not rely on broad news search alone. Pull a source-native signal such as GitHub Trending and use that as the primary popularity check, then supplement with GitHub Blog / vendor / news coverage only for context.

## Blindspot implementation pattern

Use this pattern when extending a research/report pipeline:
1. Start from finalized evidence items, not raw retrieval noise.
2. Exclude items already represented in the main top-ranked set.
3. Score remaining items for popularity/engagement.
4. Boost items that are adjacent rather than central:
   - lower exact-query overlap
   - lower direct local relevance
   - high engagement despite weaker semantic alignment
5. Classify blindspots into readable subtypes when possible, for example:
   - adjacent-but-hot
   - cross-over-trend
   - niche-breakout
   - likely-overlooked
6. Store blindspots in a report artifact and render them in a dedicated section.
7. Allow empty output when the run is too thin.

## Blindspot expansion pass

When the first blindspot pass returns too little signal, add a second-pass expansion workflow:
1. Derive a compact core subject from the user topic.
2. Mine recurring non-topic nouns/entities from top candidates and finalized source items.
3. Build a small set of adjacent expansion queries from those terms.
4. Run the expansion only against a restrained source set that is good at surfacing popularity or trends.
5. Keep expansion results out of the main ranked clusters; use them only to enrich blindspot discovery.
6. Record the expansion queries and participating sources in artifacts so the run is auditable.

This is especially useful when a narrow main query is relevant but not broad enough to surface the most-discussed adjacent developments.

## Reporting guidance

Preferred output shape:
- brief implementation status if changes were made
- concise category-by-category developments
- explicit note where coverage is weak
- optional final `blindspots` section for popular adjacent signals
- for recurring news updates, add a separate `## Personalised for you` heading driven by local Reddit/X/browser history signal rather than mixing that material into the public-news buckets

## Authenticated personal-signal sources on local machines

When a user asks to incorporate signals from their own Reddit or X accounts:
1. Get explicit approval before using account-backed local session data.
2. Prefer read-only verification first.
3. Distinguish between two access paths:
   - browser automation against a fresh/remote browser session
   - local-session reuse via the machine's real browser cookie store
4. On machines where Firefox is the live user browser, check whether a local cookie-backed probe is the more reliable path than browser automation.
5. Be source-specific in your conclusion:
   - X may be verifiable from a cookie-backed request to `/home`
   - Reddit may require a direct HTTP + cookie fallback if browser automation hits bot/security blocks
6. If the user did not ask for automation, prefer a manual local script/command first.
   - Do not default to cron or background scheduling just because the collection workflow is reusable.
   - Offer scheduling only as an explicit opt-in after the manual path is proven.
7. State clearly whether you verified a signed-in response, only found cookies, or were blocked.
8. In this workspace, use `/var/home/rainbow/.hermes/scripts/social_signals.py --limit 5 --json` as the default personalized social-signal collector for news briefings.
   - Treat its output as a side-channel for recommendation-style bullets.
   - Keep it under a separate heading such as `## Personalised for you` or `## Personal signal from your Reddit/X`.
   - Use it to suggest stories/accounts/themes the user is likely to care about next, based on recent followed-account and subreddit/feed signal.
   - Do not represent this section as broad consensus or objective top news.

Reference: `references/authenticated-social-signals-via-firefox-cookies.md` — local-first notes on Firefox cookie-store paths, collector usage, and how to report signed-in vs cookie-only vs blocked access clearly.

## Title-level media metadata pass

When the task is not a broad trend briefing but a title-by-title media research pass for films/TV:
1. Normalize the request before retrieval.
   - Deduplicate repeated titles first.
   - Convert fuzzy user phrases into canonical candidates: original vs remake, film vs TV, miniseries vs ongoing series, franchise vs specific installment.
   - Record explicit user disambiguations such as "original", "1997 version", or "season 1 only" and carry them into the final dataset.
2. Prefer title-specific probes over broad research queries.
   - Use narrow queries like `<title> film wikipedia`, `<title> tv series wikipedia`, or `<title> 2002 film wikipedia`.
   - For franchise requests, split the work into concrete child titles instead of keeping a single vague row.
3. If the search backend is sparse or inconsistent, retry with direct canonical-source fetches.
   - Go straight to likely Wikipedia canonical URLs or the Wikipedia REST summary endpoint for readback.
   - When fetching directly from Wikipedia over HTTP, send a browser-like User-Agent; some endpoints return 403 without one.
   - Treat search and extraction as separate layers: if web extract is unavailable, a direct page-summary fallback can still verify the title, year, type, and origin.
4. Return normalization decisions explicitly.
   - Call out removed duplicates, resolved ambiguities, and any remaining titles that still need user confirmation.

## Pitfalls

- Do not treat blindspots as primary ranked evidence.
- Do not force a blindspot section when the run is thin.
- Do not claim category coverage is strong when the source mix is weak or noisy.
- Do not assume broad free-source runs will be equally good for politics, music, and cars; query packs usually need to narrow by domain.
- Do not leave title-level ambiguity unresolved when the user clearly indicated a preferred version.
- Do not stop after an empty search result set if a direct canonical-source probe can verify the item.

## Pitfalls

- Do not treat blindspots as primary ranked evidence.
- Do not force a blindspot section when the run is thin.
- Do not claim category coverage is strong when the source mix is weak or noisy.
- Do not assume broad free-source runs will be equally good for politics, music, and cars; query packs usually need to narrow by domain.

## Verification checklist

- Trend path executed live, not just in code.
- Output contains the expected artifact/section.
- At least one example item can be quoted from real output.
- Weak buckets are clearly labeled instead of padded.

## References

- See `references/last30days-github-trends-and-blindspots.md` for a concrete pattern taken from a live `last30days` extension session.
- See `references/blindspot-expansion-pattern.md` for the dedicated second-pass query expansion pattern used when initial blindspot extraction is too sparse.
