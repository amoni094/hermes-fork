---
name: agent-reach-discovery
triggers:
  - User wants richer news or source coverage than generic web search snippets
  - User wants Reddit, X, Bilibili, Xiaohongshu, or community signal alongside news
  - Running Agent Reach as a sidecar for news, movie, or music discovery
  - Augmenting a news briefing or research pipeline with social/community sources
description: >
  Use when: Use locally installed Agent Reach as a sidecar for news, social/community, movie, and music discovery workflows in Hermes.
version: 1.0.1
license: MIT
platforms: [linux]
related_skills:
  - competitor-news-monitor
  - stay-in
  - gold-class
  - suggest-music
  - domain-research-synthesis
created_by: agent
metadata:
  tags: [research, news, movies, music, social, retrieval, hermes, agent-reach]
---

# Agent Reach discovery

Use this when Hermes needs broader internet reach for news, sentiment, community discussion, or recommendation discovery and a plain web search is not enough.

## When to use
- The user wants richer news/source coverage than generic web search snippets.
- The user wants Reddit/X/Bilibili/Xiaohongshu/community signal.
- The user wants movie or music discovery via reviews, discussion, buzz, or recommendation threads.
- Hermes `web_extract` is unavailable or weak and a sidecar retrieval path is needed.

## Local install verified here
- Wrapper command: `~/.local/bin/agent-reach`
- Venv: `~/.agent-reach-venv`
- Config/data dir: `~/.agent-reach/`
- Upstream auto-installed skill dir: `~/.agents/skills/agent-reach`

## Important local caveat
In this Hermes profile, Agent Reach is separate from Hermes web provider configuration. Do not treat Agent Reach as a fix for missing Hermes `web_extract` credentials; use it as a sidecar access layer.

## Safe verification workflow
1. Check version:
   - `~/.local/bin/agent-reach version`
2. Run safe install/status pass:
   - `~/.local/bin/agent-reach install --env=auto --safe`
3. Get machine-readable status:
   - `~/.local/bin/agent-reach doctor --json`
4. Prefer `doctor --json` over plain `doctor` during audits to reduce surprise side effects.

## What was available in this environment when verified
Working:
- GitHub
- Web via Jina Reader
- RSS
- YouTube via yt-dlp
- Bilibili basic search
- Exa semantic search via mcporter

Installed but still requiring manual auth/browser completion:
- Twitter/X via browser cookies
- Reddit via OpenCLI extension/browser state
- Xiaohongshu via OpenCLI extension/browser state
- LinkedIn first real use may still prompt for browser login even after mcporter is configured

Still off:
- Xueqiu
- Xiaoyuzhou transcription

## Local pitfalls discovered during verification
- OpenCLI package installation is automatable, but browser extension connection is still manual.
- On this Fedora Silverblue machine, Firefox runs from Flatpak and Agent Reach's browser-cookie import did not find the Firefox profile automatically in stock form.
- Local patch verified: `~/.agent-reach-venv/lib/python3.13/site-packages/agent_reach/cookie_extract.py` now probes `~/.var/app/org.mozilla.firefox/config/mozilla/firefox/*/cookies.sqlite` and `agent-reach configure --from-browser firefox` succeeds again.
- Local doctor patch verified: `~/.agent-reach-venv/lib/python3.13/site-packages/agent_reach/channels/twitter.py` now seeds `TWITTER_AUTH_TOKEN`/`TWITTER_CT0` from `~/.agent-reach/config.yaml`, so `doctor --json` reflects saved Twitter cookies instead of requiring per-shell exports.
- Local Xueqiu fallback patch verified: `~/.agent-reach-venv/lib/python3.13/site-packages/agent_reach/channels/xueqiu.py` now tries Firefox as well as Chrome when looking for `.xueqiu.com` cookies.
- Even with the Firefox fixes, cookie-backed channels should still be treated as installed-but-not-authenticated until the target site cookies actually exist in the browser profile.

## How to use it in practice
### News / live topics
- Use Hermes `web_search` first for a broad scan.
- Use Agent Reach when you need community/native-platform coverage or Jina-style readable page fetches.
- Treat Agent Reach as an access layer, not a reasoning upgrade.

### Movies and music
- Use Agent Reach for discussion-layer discovery:
  - reviews
  - Reddit threads
  - YouTube reactions/explainers
  - social buzz
- Do not treat Agent Reach as canonical metadata. For release dates, credits, runtimes, discographies, and structured catalog facts, use dedicated metadata sources when available.

### Recommended command pattern
- Version/status:
  - `~/.local/bin/agent-reach version`
  - `~/.local/bin/agent-reach doctor --json`
- Safe re-check:
  - `~/.local/bin/agent-reach install --env=auto --safe`
- Optional channel install preview:
  - `~/.local/bin/agent-reach install --env=auto --dry-run --channels=twitter,reddit,xiaohongshu`

## Optional follow-up channels
Only install these when the user wants them and accepts the auth/config burden:
- Twitter/X
- Reddit
- Xiaohongshu
- LinkedIn
- Xueqiu
- Xiaoyuzhou
- Exa via mcporter

## Verification rules
- Do not claim a channel works because Agent Reach supports it in docs.
- Always verify with `doctor --json` after install or config changes.
- Distinguish `ok`, `warn`, and `off` in the final report.
- If a channel needs cookies/login/browser state, say so plainly.

## When direct Reddit/page access is blocked
1. Try the normal page path first.
2. If the page is blocked, use search results to recover only what is index-visible:
   - post title
   - post body snippet
   - any comment snippets shown in search descriptions or user-profile result previews
3. Be explicit that this is partial recovery, not full-thread access.
4. If the task depends on reading text inside attached images, ask the user for the screenshot or image directly; search snippets are not enough.
5. Still extract value: summarize the likely lessons/themes from the recovered snippets, but label confidence and missing coverage plainly.
6. Do not pretend you read the full comment tree when you only have snippet-level evidence.

## Handoff points
- For named-company news watching (recurring, cited): hand off to `competitor-news-monitor`
- For movie/TV home-viewing recommendations: hand off to `stay-in` (no cinema session required)
- For Gold Class / premium cinema session times: hand off to `gold-class` (within next 24h, specific venues)
- For music suggestions: hand off to `suggest-music`
- For structured domain research with file output: hand off to `domain-research-synthesis`
- For academic paper discovery on arXiv: hand off to `arxiv`
- For formal multi-source literature surveys: hand off to `academic-literature-review`

## News briefing format (when the user asks for a news update)

Use domain-sectioned plain-text output. On CLI there is no markdown rendering — use ALL CAPS section headers, not bold or #. Proven structure:

  DOMAIN NAME

  2-4 bullet points. Each: one crisp fact + why it matters.
  Sub-bullets for related detail where density justifies it.

  BLIND SPOTS TODAY

  Explicit list of what was not covered and why (channels unavailable,
  markets closed, no AU signal surfaced, etc.).

Domains to include when present: US/AU politics, geopolitics (Ukraine/Russia,
Iran/Middle East), AI/tech, markets/finance.
Always end with a BLIND SPOTS block — the user values knowing the gaps
as much as the signal itself.

Load this skill even for simple news requests: the channel status informs
which sources to weight and what belongs in the blind spots block.

## Parallel search batching for news sweeps

Batch all independent web_search calls in a single turn (one call per
domain cluster). Then batch web_extract calls on the best URLs from those
results. Avoids serial round-trips and keeps the session compact. Two-wave
pattern: search wave -> extract wave -> synthesize.

## Output expectations
Report:
- what Agent Reach adds beyond Hermes alone
- which channels are actually working on this machine now
- which channels are merely supported upstream but still off here
- whether the user’s goal is better served by fixing Hermes config first or by enabling additional Agent Reach channels
- when using a blocked-page fallback, exactly which parts came from full access vs search-snippet recovery
