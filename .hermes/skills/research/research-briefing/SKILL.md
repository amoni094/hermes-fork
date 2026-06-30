---
name: research-briefing
description: Broad current-events and trend briefing skill covering news synthesis, blindspot scanning, and live source coverage setup.
version: 1.0.0
license: MIT
platforms: [linux, macos, windows]
metadata:
  tags: [research, briefing, news, trends, live-search, blindspots, source-coverage]
---

# Research Briefing

Use this when the user wants a current, synthesized briefing rather than a raw search dump: latest developments, topic monitoring, trend scanning, or a "what am I missing?" pass across multiple domains.

## Core idea
A good briefing has three layers:
1. enough live source coverage to trust the run
2. narrow category query packs instead of one huge search
3. synthesis that highlights the dominant signal, not the top ranked noise

## When to use
- User wants the latest developments across one or more topics.
- User wants a live trend or current-events briefing.
- User wants blindspots or adjacent signals.
- User wants to improve source coverage for a research workflow.

## Workflow

### 1) Verify coverage before synthesis
- Identify what sources are actually available.
- Separate "the tool exists" from "the tool has enough live source coverage."
- If a source is missing, use a compact fallback instead of pretending it is covered.

### 2) Split into narrow query packs
- Build separate probes per topic/category.
- Keep categories distinct: politics, macro/finance, geopolitics, tech/AI, culture, autos, GitHub, etc.
- Avoid an omnibus query unless you explicitly want broad noise.

### 3) Add blindspot scanning
- Surface adjacent items that are popular or important but not centered in the main ranking.
- Treat blindspots as secondary signals, not the main conclusion.
- Use a second pass when the first pass is too narrow or too noisy.

### 4) Synthesize by topic
- State the main development first.
- Then give 2–4 supporting bullets.
- Call out weak or noisy buckets instead of padding them.
- Keep the output concise and readable.

### 5) Include setup improvements when needed
- If the workflow is source-limited, improve the search/extract/auth stack before blaming the briefing logic.
- Distinguish a general live-news workflow from source-specific signals such as GitHub trends or account-derived personalization.
- When the user wants recurring briefings, preserve their established output shape rather than inventing a new one each time.

## Practical rules
- Prefer the local Firecrawl instance for page retrieval and extraction when the task involves crawling, scraping, or turning URLs into clean text.
- Use search to discover candidate URLs, then use Firecrawl to fetch/extract them; do not rely on search snippets alone when full-page extraction is feasible.
- For one page or a small URL set, prefer Firecrawl scrape/extract-style calls; for site-wide or multi-page work, prefer Firecrawl crawl/map-style calls.
- Verify the local Firecrawl service first with `GET http://127.0.0.1:3002/`; do not rely on `/v1/health` because this self-host image does not expose that route.
- Keep fallback behavior honest: if Firecrawl is down or a target blocks extraction, fall back to `web_search`/`web_extract` and label the limitation plainly.
- Do not claim comprehensive coverage when the source mix is thin.
- Do not pad a briefing with irrelevant recent items.
- Do not merge blindspots into the main ranked story.
- Do not confuse search success with good coverage.
- Do not forget to label caveats plainly when a source path is missing.

## Verification
- Live sources were checked.
- Query packs were narrowed by topic.
- Briefing output is synthesized, not dumped raw.
- Blindspots or weak buckets are labeled honestly.

## Local service and appointment research
Use the same evidence discipline when the user wants a real-world provider shortlist (doctors, clinics, trades, venues) with a hard availability filter.

- Separate clinic-level opening hours from provider/service-specific availability. "Open 7 days" for a medical centre is not proof that the podiatrist, physio, or other specialist works Sundays.
- Prefer service pages and practitioner profiles that explicitly name the condition/treatment fit: e.g. plantar fasciitis, orthotics, biomechanics, foot and ankle pain, flat feet.
- Use search to find candidate providers, then extract the provider page and the clinic contact/opening-hours page separately.
- Treat booking-directory snippets (HotDoc/Healthengine/etc.) as secondary evidence when dynamic pages do not extract cleanly. Useful for hints like weekend slots, but mark them as not fully confirmed unless the schedule is explicit.
- Rank by the user's hard constraint first (for example Sunday availability), then by distance, then by specialty fit.
- When the closest options fail the hard constraint, expand geographically and say that you expanded the radius.
- Be explicit about confidence: confirmed Sunday clinic + explicit provider fit is stronger than clinic-open-only + generic podiatry listing.
- If dynamic booking pages or bot checks block direct inspection, do not bluff booking availability. Report the strongest evidence found and label any remaining uncertainty.
- See `references/local-service-availability-research.md` for a compact evidence/ranking pattern.

## Evaluating external source stacks
Use this when the user asks whether a new retrieval/integration layer would improve news, recommendations, or research coverage.

- Compare the proposed stack against the current local stack before recommending installation.
- Separate access-layer gains from reasoning gains: better source reach can improve inputs without improving synthesis quality by itself.
- Distinguish discussion-layer value from structured-metadata value. Social/community sources can improve sentiment, buzz, and recommendations even when they do not improve canonical metadata lookup.
- Prefer a low-risk trial first: isolated venv or other reversible install path, plus dry-run/status commands before any real setup.
- Check for hidden side effects in verification commands. If an upstream `doctor` or `setup` command writes skills/config automatically, prefer the least side-effecting variant during evaluation.
- Report current gaps in the existing stack separately from the proposed tool's strengths. Sometimes the fastest win is fixing the current extract/search configuration rather than adding a second stack.
- When judging fit for recurring briefings, prioritize source coverage, auth burden, and reversibility over feature-list breadth.
- See `references/external-source-stack-evaluation.md` for a concrete comparison pattern and low-risk trial checklist.

## WorldMonitor augmentation
When a briefing touches geopolitics, conflict, infrastructure, macro stress, shipping, aviation, cyber, or weather-linked disruption:
- Use WorldMonitor as a secondary context layer, not a sole source of truth.
- Check `https://api.worldmonitor.app/api/health` first to confirm the relevant source stack is fresh enough to trust.
- Prefer the public discovery surfaces when you only need capability/source context: `https://worldmonitor.app/llms-full.txt`, `https://worldmonitor.app/.well-known/api-catalog`, and `https://worldmonitor.app/.well-known/agent-skills/index.json`.
- Treat premium/API-key-gated endpoints such as country briefs as optional enrichments; do not imply you used them unless you actually had working access.
- Expect some direct API calls to be bot-blocked from generic CLI clients; if so, fall back to the public docs/discovery/health surfaces and corroborating mainstream sources.
- For local experimentation, app-only dev (`npm ci && npm run dev -- --host 127.0.0.1`) is enough for UI/feed inspection; full local `/api/*` behavior requires the self-hosted Podman/Docker stack and seeders.
- For local verification, prefer `http://127.0.0.1:3000/api/health` over judging the app by `/` alone; the root can return a static 403 while the API is healthy enough to test.
- Use `/var/home/rainbow/.hermes/scripts/worldmonitor_news_signal.py --format text` to inject a compact WorldMonitor status block into the briefing workflow before synthesis.
- If a full seeder pass is slow, validate the stack with one or two targeted seeders first (for example earthquakes or weather alerts) and confirm that `/api/health` moves those checks from `EMPTY`/`STALE_SEED` to `OK`.
- See `references/worldmonitor-news-augmentation.md` for concrete usage notes.

## Fast-briefing fallback rules
When the user asks for a quick news update and the environment has thin extraction coverage:
- Try live search first across a few narrow topic buckets rather than blocking on full-page extraction.
- If a bucket returns stale, generic, or weakly-related results, immediately rerun that bucket with explicit date terms and trusted-source constraints instead of accepting noisy rankings.
- If URL extraction fails because the configured backend is search-only, fall back to search snippets and say so plainly.
- If high-value sources such as Reuters are bot-blocked in the browser, use corroborating search results from Reuters/AP/other mainstream sources instead of pretending you read the full article.
- Stamp the briefing with the current local time and clearly separate "24h signal", "7-day trend", and "weak/noisy buckets".
- When personalization is useful and local browser history is available, add a small separate "personalized signal" section rather than contaminating the main public-news ranking.
- If browser-history signal is mostly entertainment or general browsing rather than news consumption, say that plainly and keep it as lightweight context rather than forcing it into the main briefing.

## Third-party skill ecosystem vetting
When evaluating external skill repos (awesome-claude-skills, Trail of Bits, Anthropic-Cybersecurity-Skills, etc.) for bulk installation or selective integration:

- **Separate index claims from reality.** Repository READMEs and index entries are often stale. Path mismatch (claimed `/skills/ai-security`, actual `/domains/ai/`), deleted subdirs, and 404s are common. Always verify by:
  - Cloning/browsing the actual repo structure.
  - Testing raw URLs against confirmed paths before committing to installation.
  - Checking commit history for recent activity in the target directory (dormant = risky).

- **Tier-rank candidates before batch install.** Use the concrete evaluation framework in `references/skill-vetting-framework.md` to sort into Tier 1 (install now), Tier 2 (solid value but lower priority), Tier 3 (review before deciding). This prevents skill bloat and conflicting defaults.

- **Validate skill author credibility.** Trail of Bits (5.9k stars, 123 commits, maintained), Anthropic-Cybersecurity-Skills (23.2k stars, 2026 framework alignment) are production-ready. Single-author repos with <50 stars and <5 commits are exploratory — install with low risk expectations.

- **Check for skill conflicts.** Cross-reference candidate skill names, domains, and trigger phrases against your existing library. Duplicated coverage in different repos is common; prefer the most recently maintained version.

- **Verify installation mechanics.** Different repos use different discovery paths:
  - `.claude/skills/name/` (Claude Code native)
  - `skills/name/` (agentskills.io standard)
  - `plugins/name/` (CLI/plugin-native)
  - Hermes-native skills live under `~/.hermes/skills/`.
  Always test the install command in isolation before batch operations.

- **Document installed source.** When you install from an external repo, keep a record of: source repo URL, commit SHA, installation date, and intended trigger. This makes updates, rollback, and conflict resolution traceable.

- **Known-good sources (as of 2026-06-30):**
  - **Trail of Bits** (`trailofbits/skills`): codeql, semgrep, agentic-actions-auditor, fp-check. Production-ready, peer-reviewed, actively maintained.
  - **Anthropic-Cybersecurity-Skills** (`mukul975/Anthropic-Cybersecurity-Skills`): 817 skills across 29 security domains, mapped to MITRE ATT&CK v19.1, NIST CSF 2.0, ATLAS, D3FEND, AI RMF, and F3. Curated domain selection beats wholesale import.
  - **OWASP Security** (`agamm/claude-code-owasp`): OWASP Top 10:2025, ASVS 5.0, Agentic AI Security 2026 (ASI01–ASI06). Install via degit to preserve reference files.

- **Pitfalls that block vetting:**
  - Index file path is wrong (repo was reorganized, link is stale).
  - Skill frontmatter references non-existent tools or dependencies.
  - Skill content is generated text (verbose, lacks practitioner detail, rationalizations).
  - Trigger phrases are too broad (loads on every code review, not specialized).
  - No verification section or clear success criteria.

See `references/skill-vetting-framework.md` for a step-by-step checklist and concrete Tier 1/2/3 assignments.

## Notes
More specific workflows that fit under this umbrella include recent-news briefings, signal-oriented briefings, live research source-coverage setup, and third-party skill library vetting.
Treat this as the canonical umbrella when multiple current-events or trend-briefing skills overlap.
When the task is explicitly a recurring 24h/7d digest, `recent-news-briefing` is the narrower specialization to pair with this skill rather than replace it.
When the task specifically needs URL retrieval, crawling, or page extraction, load `firecrawl-research` first and treat it as the retrieval-layer companion to this skill.
