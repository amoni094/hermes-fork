---
name: firecrawl-research
description: Use the local Firecrawl self-host as the default crawl/scrape/research retrieval layer, with search mainly for discovery and Firecrawl for extraction.
version: 1.0.0
license: MIT
platforms: [linux, macos, windows]
metadata:
  tags: [firecrawl, research, crawling, scraping, extraction, local-first]
---

# Firecrawl Research

Use this when the task involves crawling a site, scraping one or more pages, turning URLs into clean text, or building research from live web pages.

## Core rule
- In this workspace, default to the local Firecrawl self-host at `http://127.0.0.1:3002` when applicable.
- Use search mainly to discover candidate URLs.
- Use Firecrawl to retrieve and extract the actual page content.

## When to use
- The user asks to crawl a site.
- The user asks to scrape one or more URLs.
- The user wants a research summary grounded in web pages rather than search snippets.
- The user provides URLs and wants them turned into markdown/text.

## Workflow
1. Verify Firecrawl is up.
   - Check `GET http://127.0.0.1:3002/`.
   - Expect the API banner JSON.
   - Do not rely on `/v1/health`; this self-host image does not expose that route.
   - If the root endpoint is down, check whether the self-host stack is merely stopped before assuming Firecrawl is misconfigured.

2. Decide discovery vs retrieval.
   - If the user already gave URLs, go straight to Firecrawl retrieval.
   - If the user gave a topic but not URLs, use search first to find candidate pages.
   - Keep search narrow and topic-specific.

3. Pick the Firecrawl mode.
   - For one page or a short URL list, use scrape/extract-style retrieval.
   - For site exploration or multi-page discovery, use crawl/map-style retrieval.
   - Prefer the smallest retrieval scope that answers the question.

4. Extract before synthesizing.
   - Base the answer on retrieved page content, not just result snippets.
   - Capture title, URL, date if available, and the main claims.
   - When comparing sources, keep source attribution explicit.

5. Fall back honestly when needed.
   - If Firecrawl is down, blocked, or unsuitable for the target, fall back to `web_search`/`web_extract`.
   - State clearly when the answer is based on fallback search/extract rather than Firecrawl retrieval.

## Practical rules
- Prefer local-first retrieval over hosted services when Firecrawl can do the job.
- Do not claim a page was extracted unless you actually retrieved it.
- Do not treat discovery hits as equivalent to page extraction.
- For news/research, use multiple URLs when one source is too thin or biased.
- For broad sites, avoid over-crawling when a few key pages are enough.
- Distinguish **stack-down** from **target-specific blocking**: if `example.com` scrapes successfully but Reuters or another site returns 401/anti-bot failures, the Firecrawl service is healthy and the issue is site-specific.
- When the user explicitly wants **no anti-bot bypass**, do not escalate to stealth browsers, CAPTCHA workarounds, proxy rotation, or header-fakery. Prefer RSS/Atom feeds, official APIs, publisher-provided newsletters, and normal extract/search access; if the target article is blocked, mark it unavailable and continue with accessible sources.
- For no-bypass news summarizers, structure the pipeline as: source registry -> feed/API ingestion -> optional normal extraction for accessible URLs -> clustering/ranking -> citation-backed summary. Blocked article bodies are a coverage gap, not a reason to add bypass code.
- When making Firecrawl durable under systemd user services, prefer an explicit compose binary path if `podman compose` depends on a provider that may not be present in the unit PATH.

## Verification
- Firecrawl root endpoint responded before use.
- URLs used in the answer were actually retrieved, not just discovered.
- Fallbacks were labeled if Firecrawl was unavailable.
- Final synthesis cited the key source pages.
- If Hermes provider/env wiring changed in the same maintenance pass, verify `web_extract` from a fresh Hermes process before treating the integration as fixed.
- Do not use a stale failure from the current conversation's already-loaded tool bundle as proof that Firecrawl wiring is still broken.

## Local notes
- Local Firecrawl endpoint: `http://127.0.0.1:3002`
- Verified good endpoint: `GET /`
- Known bad health probe for this image: `GET /v1/health` returns 404
- See `references/local-firecrawl.md` for command snippets and `references/firecrawl-systemd-user-service.md` for a durable user-service pattern.

## Related skills
- `research-briefing`
- `recent-news-briefing`
- `hermes-web-provider-configuration`
