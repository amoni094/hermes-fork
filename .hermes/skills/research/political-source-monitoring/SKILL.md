---
name: political-source-monitoring
description: Build and maintain political/media monitoring pipelines with resilient outlet coverage, conservative entity matching, and social-profile enrichment.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [media-monitoring, news, political-data, entity-matching, scraping]
    related_skills: [media-catalog-seed-data, systematic-debugging, verification-before-completion]
---

# Political Source Monitoring

Use this skill when maintaining a dashboard, feed collector, or generated dataset that tracks politicians through news outlets, official media pages, and public social links.

## When to use

- a monitored-source list must cover a specific outlet set
- direct scraping is uneven across publishers
- politician mention matching is too sparse or too noisy
- social-profile coverage is incomplete
- generated dashboard data needs source-health evidence

## Core approach

1. Prefer direct outlet pages when the page structure is stable enough to extract recent headline anchors.
2. Use Google News RSS as a resilience layer for outlets that are brittle, JS-heavy, paywalled, or inconsistent in their markup.
3. Record harvested source labels into the generated payload so coverage is auditable after each refresh.
4. Match politicians conservatively:
   - strongest: full-name match
   - next: given-name + surname token match
   - optional: explicit alias map for high-profile roles
   - avoid weak surname-only matching
5. Weight headline evidence above summary/body evidence, but use summary/body to recover valid mentions that the headline alone misses.
6. Enrich politician social links from both structured sources and linked official/public pages.
7. When politician-specific news hits are sparse, surface discovered social-profile links as fallback public-facing announcement items instead of leaving cards empty.

## Recommended source strategy

### Direct pages
Use direct extraction for outlets/pages where recent content can be found reliably via anchors and stable URL patterns.
Examples:
- official government media pages
- party news pages
- stable publisher politics/category pages

### Google News RSS fallback
Use Google News RSS query mode when any of these are true:
- the outlet is paywalled
- the outlet relies on heavy client-side rendering
- the politics landing page is inconsistent or sparse
- direct scraping returns too few usable anchors

Good candidates include:
- Reuters
- AFR / Financial Review
- The Australian
- Nine News when direct politics extraction is weak
- a generic Google News politics query for breadth

## Mention scoring pattern

Use a weighted score across fields rather than headline-only matching.

Recommended baseline:
- headline/title score × 2
- summary/body score × 1

Suggested confidence rules:
- full-name exact phrase in title/body = strongest hit
- given-name + surname tokens together = medium hit
- explicit alias hit = weaker than full name, but strong enough for key leaders when combined with title weighting
- surname-only = reject by default

Only count items above a threshold that still preserves precision.
If expanding recall, raise aliases or add body weighting before enabling surname-only logic.

## Alias policy

Maintain a small explicit alias map for high-profile office holders or leaders whose role titles often replace their names in headlines.
Examples:
- Prime Minister
- Opposition Leader
- Treasurer
- Foreign Minister
- Defence Minister
- Greens leader
- Nationals leader

Do not generate broad freeform aliases for every politician unless another strong signal exists. Over-broad aliasing creates false positives quickly.

## Social-profile enrichment

Start with structured profile fields when available, then enrich from linked public pages.

Priority order:
1. canonical structured source (e.g. Wikidata or maintained directory fields)
2. official website
3. official/public profile page
4. Wikipedia page as a last public discovery surface

Useful platforms to collect when found:
- X / Twitter
- Instagram
- Facebook
- YouTube
- LinkedIn
- TikTok

Normalize URLs before storing:
- collapse twitter.com to x.com if desired by the dataset
- strip share/intent/reel/story paths that are not canonical profiles
- remove trailing slashes and query strings when appropriate

## Generated-data hygiene

After each refresh, include machine-checkable evidence in the output payload:
- refreshedAt
- mentionMethod summary
- monitoredSources list
- source-health notes for auxiliary collectors

This makes it easy to verify requested outlet coverage from generated artifacts instead of re-reading scraper code.

## Verification checklist

After changing the monitoring logic:
1. run a syntax/compile check on the scraper
2. run the refresh command end-to-end
3. inspect the generated payload for monitoredSources coverage
4. inspect a few key politician cards for mention-score changes
5. run tests
6. run the build

## Pitfalls

- relying on headline-only matching when summaries already contain clear names
- enabling surname-only matching and flooding results with false positives
- assuming source coverage from code alone instead of writing monitored source labels into generated output
- treating missing politician news hits as a reason to leave cards empty when public social-profile links can provide useful fallback context
- using direct scraping for outlets that are better handled by Google News RSS

## Session-learned pattern

A strong practical setup for Australian political monitoring was:
- direct pages for ABC News, SBS News, The Guardian, The Conversation, 7 News, official government media, and party news
- Google News RSS for Reuters, AFR, The Australian, Nine News, and a generic Google News breadth query
- weighted headline + summary matching
- explicit alias map for major leaders only
- monitoredSources persisted into the generated payload for post-refresh verification
