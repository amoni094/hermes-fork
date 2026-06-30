---
name: recent-news-briefing
description: Produce a concise recent-developments briefing across one or more topics, especially when a dedicated research skill is installed but source coverage is incomplete.
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
- Preserve the tighter recurring-news digest pattern as a specialization under `research-briefing`, not a replacement for that broader umbrella skill.

## Workflow
1. Verify the research tool/skill first.
   - Confirm the skill is installed/listed.
   - If the skill has a diagnostic mode, run it and record active vs missing sources.
   - Separate "tool is implemented" from "tool has broad enough coverage for this briefing".

2. Run the specialized workflow on at least 1-2 representative topics.
   - This confirms the real output shape, quality, and source mix.
   - Note whether it falls back to deterministic behavior, limited sources, or missing planners/backends.

3. Add a WorldMonitor situational-awareness pass when the topic bundle includes geopolitics, conflict, infrastructure, macro stress, cyber, shipping, aviation, or weather-linked disruption.
   - If local WorldMonitor is running, use `/var/home/rainbow/.hermes/scripts/worldmonitor_news_signal.py --format text` first.
   - Treat its output as a compact source-freshness and domain-coverage check, not as the sole evidentiary basis for claims.
   - If local WorldMonitor is unavailable, fall back to `https://api.worldmonitor.app/api/health` or the public discovery/docs surfaces.
   - If WorldMonitor shows key domains as `EMPTY`, `WARN`, or `CRIT`, keep those caveats short and supplement with mainstream news/live search.

4. Use Firecrawl first for article retrieval; keep live-news search as fallback/discovery.
   - For this workspace, prefer the local Firecrawl self-host at `http://127.0.0.1:3002` whenever the task is crawl/scrape/research over real URLs.
   - Verify Firecrawl with `GET /` before a run; this image returns a JSON banner on `/` and does not expose `/v1/health`.
   - Use live search to discover candidate URLs per topic, then pass the selected URLs through Firecrawl for clean extraction before synthesis.
   - Query per topic rather than one giant omnibus search.
   - Pull multiple recent items per topic and extract dates, titles, outlets, and links.
   - If Hermes `web_search` is part of the path, prefer a fallback-capable search stack instead of relying on one brittle backend.
   - If Firecrawl is unavailable or a site blocks extraction, fall back to dated search hits/snippets plus any local signal scripts already approved in the workspace, and state that article-level synthesis is limited by extract backend configuration.
  - Distinguish service health from publisher blocking: if ordinary pages extract but Reuters or another outlet returns anti-bot errors, treat Firecrawl as healthy and label the affected outlet as snippet-backed unless you obtain article text through another verified path.
  - After restoring Firecrawl mid-session, re-run at least one simple known-good extraction plus one task-relevant extraction attempt before claiming the briefing is fully back to article-level grounding.

5. Normalize topic scope before synthesis.
   - If the user says "all the topics" from a research skill, distinguish between the skill's configured watchlist, its documented coverage domains, and the user's standing default topic bundle.
   - If a watchlist is empty but the user has durable topic preferences for recurring news updates, use that bundle rather than treating the empty watchlist as the answer.
   - Preserve any standing output contract the user already established, such as a main window (for example last 7 days), a separate last-24h trending section, a blind-spot section outside the usual categories, and a separate personalized section when local account/browser signal is available.

6. If the task is to build or upgrade the news summarizer itself, keep the architecture publisher-permitted and verifiable.
   - When the user forbids local models, make the design hosted-first: RSS/Atom and official APIs for ingestion, optional OpenAI-compatible hosted summarization, and no Ollama/local-model dependency.
   - Treat "no anti-bot bypass" as an architectural constraint, not a footnote: use only feeds, official APIs, newsletters, and plainly accessible pages; if article extraction encounters blocking/challenge text, return no article text and continue without escalation.
   - Prefer a registry-driven source config plus a seen-story cache so recurring runs can suppress already-covered items and emit an explicit "no new clusters" result on repeat runs.
   - Curate the checked-in registry around the user's standing topic bundle rather than broad generic coverage; keep only sources that are both reachable and useful for those recurring buckets.
   - Add timestamped Markdown + JSON bundle outputs for recurring delivery so runs are inspectable after the fact.
   - Render Markdown by requested topic sections first, with a fallback section such as `blind-spots-and-general`; preserve JSON as the stable machine-readable shape.
   - Default recurring briefings to a recency window (for example 7 days) and make the age cutoff explicit/overrideable, so stale feed archives do not flood a daily run.
   - Treat malformed or truncated publisher feeds as per-source failures, not whole-run failures: skip the bad source, continue the briefing, and surface the skipped source compactly in stderr/logs.
   - Tighten topic matching for short tokens and acronym-like topics (for example `ai`, `au`) to whole-word matching so substring collisions do not misclassify unrelated stories.
   - When clustering across mixed outlets, require stronger title similarity or shared topic hits before merging; otherwise you can accidentally join unrelated stories from broad feeds.
   - Verify the build in layers: offline fixture tests for parsing/clustering, a registry/cache CLI run, and (when hosted credentials are absent) a mocked hosted-summary test instead of pretending the external API path was live-verified.
   - If `python -m pytest` and `pytest` resolve to different environments, retry with the working pytest entrypoint and report which path produced the verified result.
   - Keep a session-specific reference note under `references/no-bypass-briefing-implementation-patterns.md` when you discover concrete feed-curation, topic-section, or failure-isolation patterns worth reusing.

7. Add local personalization side-channels for recurring news updates when they are available and already approved.

6. Add local personalization side-channels for recurring news updates when they are available and already approved.
   - In this workspace, run `/var/home/rainbow/.hermes/scripts/social_signals.py --limit 5 --json` and use it as a read-only personalization input.
   - Keep Reddit/X-derived signal out of the main public-news synthesis.
   - If one side-channel fails but another returns usable data, keep the successful side-channel and report the missing one explicitly rather than discarding the whole personalization block.
   - Render it under a distinct heading such as `## Personalised for you` or `## Personal signal from your Reddit/X`.

7. Synthesize by topic, not by raw hit list.
   - Group into the user’s requested buckets.
   - State the dominant theme first, then 2-4 supporting developments.
   - Include a short "signals seen" or "examples" list so the synthesis is grounded.

8. Be explicit about confidence and blind spots.
   - If X/Twitter, YouTube, or general web search are unavailable, say so plainly.
   - Distinguish between strong signal topics and weaker ones.
   - Do not pretend a source-limited run is comprehensive.

## Preferred output shape
- One short implementation/source-status block
- One caveat block about active vs missing sources
- Topic-by-topic bullets with the main development first
- A short cross-topic summary at the end if helpful

## Pitfalls
- Do not treat successful installation as proof of adequate research coverage.
- Do not rely on a specialized skill’s brand promise; verify active sources at runtime.
- Do not dump raw evidence clusters when the task is a briefing.
- Do not claim "last 30 days" coverage without checking dates on fallback results.
- Do not let WorldMonitor status replace source corroboration; it is an augmentation layer.

## References
- `firecrawl-research` — preferred retrieval-layer companion when the briefing needs article/page extraction through the local Firecrawl self-host.
- `/var/home/rainbow/.hermes/scripts/worldmonitor_news_signal.py` — compact WorldMonitor health summarizer for recurring news updates.
- `references/default-cross-topic-news-shape.md` — default section order and interpretation rules for recurring multi-topic news updates.
