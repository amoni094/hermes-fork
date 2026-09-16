---
name: recent-news-briefing
description: Produce a concise recent-developments briefing across one or more topics, especially when a dedicated research skill is installed but source coverage is incomplete.
related_skills:
  - signal-oriented-research-briefing
  - competitor-news-monitor
  - rss-feeds
---

# Recent News Briefing

Use this when the user asks for the latest developments over the last N days across one or more domains (politics, business, geopolitics, tech, culture, autos, etc.), especially if you need to combine a specialized research skill with direct live-news fallback sources.

## Triggers
- User asks for "latest developments", "what happened in the last 30 days", or a cross-topic current-events briefing.
- A specialized research skill exists, but its active source coverage is incomplete or heavily skewed.
- You need to implement/verify a research workflow and also deliver an actual briefing in the same turn.

## Outcomes
- Verify whether the specialized research tool/skill is actually installed and working.
- Determine which live sources are truly active before trusting coverage.
- Supplement gaps with a lightweight, current fallback source.
- Deliver a concise topic-by-topic briefing with explicit caveats about source coverage.

## Workflow
1. Verify the research tool/skill first.
   - Confirm the skill is installed/listed.
   - If the skill has a diagnostic mode, run it and record active vs missing sources.
   - Separate "tool is implemented" from "tool has broad enough coverage for this briefing".

2. Run the specialized workflow on at least 1-2 representative topics.
   - This confirms the real output shape, quality, and source mix.
   - Note whether it falls back to deterministic behavior, limited sources, or missing planners/backends.

3. If coverage is limited, supplement with a live-news fallback.
   - Prefer a low-friction current source such as Google News RSS search.
   - Query per topic rather than one giant omnibus search.
   - Pull multiple recent items per topic and extract dates, titles, outlets, and links.
   - If Hermes `web_search` is part of the path, prefer a fallback-capable search stack instead of relying on one brittle backend. A good free-first chain is `searxng -> brave-free -> ddgs`, with the configured backend tried first and other available providers allowed to catch failures.
   - When implementing that fallback in Hermes itself, verify it with targeted tests that prove both success-path fallback and combined failure reporting, rather than only checking config values.

4. Normalize topic scope before synthesis.
   - If the user says "all the topics" from a research skill, distinguish between the skill's configured watchlist, its documented coverage domains, and the user's standing default topic bundle.
   - If a watchlist is empty but the user has durable topic preferences for recurring news updates, use that bundle rather than treating the empty watchlist as the answer.
   - Preserve any standing output contract the user already established, such as a main window (for example last 7 days), a separate last-24h trending section, a blind-spot section outside the usual categories, and a separate personalized section when local account/browser signal is available.

5. Add local personalization side-channels for recurring news updates when they are available and already approved.
   - For this workspace, run `/var/home/rainbow/.hermes/scripts/social_signals.py --limit 5 --json` and use it as a read-only personalization input.
   - Keep Reddit/X-derived signal out of the main public-news synthesis.
   - Render it under a distinct heading such as `## Personalised for you` or `## Personal signal from your Reddit/X`.
   - Use it for recommendation-style bullets: what looks unusually aligned with the user's recent interests, accounts, or subreddits.
   - Label it honestly as local-session/account-derived signal rather than broad public consensus.

6. Synthesize by topic, not by raw hit list.
   - Group into the user’s requested buckets.
   - State the dominant theme first, then 2-4 supporting developments.
   - Include a short "signals seen" or "examples" list so the synthesis is grounded.

6. Be explicit about confidence and blind spots.
   - If X/Twitter, YouTube, or general web search are unavailable, say so plainly.
   - Distinguish between strong signal topics and weaker ones.
   - Do not pretend a source-limited run is comprehensive.

6. If the user asked to "implement this" and "tell me the latest", report both:
   - implementation/verification status
   - the actual briefing

## Preferred output shape
- One short implementation status block
- One caveat block about active vs missing sources
- Topic-by-topic bullets with the main development first
- A short cross-topic summary at the end if helpful

## Pitfalls
- Do not treat successful installation as proof of adequate research coverage.
- Do not rely on a specialized skill’s brand promise; verify active sources at runtime.
- Do not dump raw evidence clusters when the task is a briefing.
- Do not merge tool-verification caveats into the substantive briefing so tightly that the answer becomes hard to scan.
- Do not claim "last 30 days" coverage without checking dates on fallback results.
- When the user references "all the topics" of a research skill, do not assume they mean the local watchlist database. First distinguish between: configured watchlist topics, the skill's source/topic categories, and example prompts baked into the skill docs.
- If the watchlist is empty, do not stop there when the user may be asking for a broad cross-topic briefing. State the watchlist status explicitly, then either infer a reasonable cross-topic set from the skill/docs or ask for topic scope if the interpretation materially changes the output.
- If direct Reddit/X verification is blocked or unavailable, say so plainly and use clearly-labeled proxy signals (news prominence, GitHub trending, search/news recency) rather than implying comprehensive social coverage.
- When the user has a standing news format, keep caveats compact and preserve the expected section order instead of letting source-diagnostic detail dominate the answer.

## Fallback pattern
When a recent-news research skill works but is source-limited:
- use the skill to confirm installation, diagnostics, and sample output
- then use a lightweight live-news feed per requested topic
- synthesize with explicit caveats about missing social/video/web coverage

## References
- references/google-news-rss-fallback.md — lightweight live-news fallback pattern for topic briefings
- references/default-cross-topic-news-shape.md — default section order and interpretation rules for recurring multi-topic news updates
