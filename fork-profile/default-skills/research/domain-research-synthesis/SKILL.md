---
name: domain-research-synthesis
depends_on: [firecrawl-research, grounded-citations]
provides: [domain-research-synthesis, tool-comparison, community-consensus, market-research]
triggers:
  - Research the best tools / libraries / frameworks for a practical domain (not academic papers)
  - Find popular GitHub repos for a domain — include stars, language, what it does
  - What does the community think about a strategy or approach (Reddit, forums, HN)
  - Combine GitHub stars, Reddit sentiment, and web sources into a structured report file
  - Research open-source or commercial tools with community consensus and locale-specific options
  - Melbourne property, PPOR, suburb comparison, school zones, infrastructure uplift
  - Algorithmic trading strategies, PEAD, momentum, factor investing — academic evidence with AU context
  - Consumer product research: jackets, gear, apparel, sleep products (pillows, mattresses), wellness/health products — with AU pricing, stockists, and spec comparison
  - Australian cruise and travel research: short-break availability, ship comparisons, AUD pricing, booking sources
  - NOT for academic paper surveys (use academic-literature-review); NOT for single arXiv paper lookup (use arxiv); NOT for news monitoring (use competitor-news-monitor); NOT for the recurring AI agent research sweep (use hermes-research); NOT for one-off product hunting by variant/country (use product-availability-search); NOT for cinema/movie recommendations (use gold-class or stay-in)
description: >
  Use when: Multi-source domain research: combine GitHub star rankings, web extraction, Reddit/forum community sentiment, and domain-specific knowledge into a structured report file. Covers research workflow, anti-bot fallbacks, output format discipline, and domain-knowledge banks (currently: ASX/Australian investing, algorithmic trading tools).
related_skills:
  - academic-literature-review
  - arxiv
  - arxiv-sweep-findings
  - external-signal-pipeline-recovery
  - firecrawl-research
  - agent-reach-discovery
  - grounded-citations
  - obsidian-research-ingestion
  - hermes-research
---

# Domain Research Synthesis

Use when the task is: find the best tools / community consensus / landscape for a
practical domain (not academic papers), combining GitHub, Reddit, web articles,
and domain knowledge. Deliverable is typically a structured file or report.


## Trigger conditions

- "Research open-source tools for X" (trading, ML, devops, etc.)
- "Find popular GitHub repos for Y — include stars, language, what it does"
- "What does r/algotrading / r/AusFinance think about Z strategies"
- "Include Australian / ASX-specific options"
- "Write findings to /tmp/X.txt"

Domain-specific triggers (route here, not to academic-literature-review):
- Melbourne PPOR / suburb comparison / school zones / SRL or NEL infrastructure uplift
- PEAD, price momentum, factor decay, momentum crashes, Kelly sizing, sector correlations
- AU bank AI benefit estimation / ABEF framework / stakeholder-free business case
- Technical trading strategies — Asian markets, cross-market evidence, RSI/MA/Bollinger
- NeSy / neurosymbolic AI frameworks — pip-installable, GitHub activity, local install
- AI agent research categories: reasoning/planning, tool-use, memory, multi-agent, evaluation, self-improvement, agentic-RAG — use hermes-research skill for the structured recurring sweep; use this skill for one-off domain landscape reports on these topics

## Core workflow

### Phase 0 — Plan the axes before searching

Identify the independent axes for the domain:
- **Tool categories** (e.g. backtesting / portfolio optimization / data / analytics)
- **Community sources** (subreddits, forums, Discord, Hacker News)
- **Locale** (global vs. country-specific variants)
- **Output schema** (what columns/fields the report needs)

Batch all Phase 1 searches in one turn — never serialize what can run in parallel.

### Phase 1 — Parallel discovery

Run 5–8 parallel `web_search` calls covering:
1. `"most popular open source [domain] GitHub stars 2024 2025"`
2. `"best [category1] tools GitHub" site:github.com OR site:libhunt.com`
3. `"best [category2] tools GitHub stars"`
4. `"site:reddit.com r/[community1] [strategy/tool] 2024 2025"`
5. `"site:reddit.com r/[community2] [topic]"`
6. `"[locale]-specific tools [domain]"` (e.g. ASX, Australian)
7. Curated list repos: `"awesome-[domain] GitHub"` or `"best-of-[domain]"`
8. X/Twitter practitioner signal: `"site:x.com [topic] [keyword]"` — Google indexes public tweets.
   Do NOT use browser_navigate on x.com (confirmed timeout). Use web_search site:x.com snippets;
   follow up with web_extract on a specific tweet URL if you need the full text.

Also run parallel `web_extract` on 2–3 promising aggregator URLs found in the same turn.

### Phase 2 — Deep extraction

For the most useful pages (curated lists, comparison sites, community debate articles):
- `web_extract` the full page; read the cached file for truncated content
- For GitHub repo pages: star count is in the page text; extract name, stars, language, description
- For Reddit: use `web_search` to find real post IDs, then `web_extract` the actual thread URL
  for full comment content (see pitfalls — fabricated URLs return 500).
- **For recipe/procedure/how-to content: YouTube video pages are often the richest source.**
  Creators frequently write the full procedure (with exact amounts, timings, steps) in the
  video description. `web_extract` a YouTube URL yields the complete description text.
  Prefer known authoritative channels (e.g. James Hoffmann for coffee, community champions)
  over generic blog posts — the YT description is often the canonical written form of the recipe.

### Phase 3 — Community sentiment

Reddit and forum sentiment is extractable even when direct scraping is blocked:
- Use `web_search` with `site:reddit.com r/[subreddit] [topic]` — Google's snippet
  often contains the key opinion/advice from the top comment
- Search for `"r/[subreddit] community consensus [topic] site:reddit.com"` to surface
  threads where multiple upvoted comments state a clear view
- Look for summary/discussion articles: `"r/algotrading popular strategies summary"`
- Community debate articles (e.g. from biggo.com, medium.com) often quote verbatim
  community positions when a tool release sparks discussion

### Phase 4 — Synthesise and write

Write to the specified output file with:
1. Structured table: name | URL | stars | language | what it does | notes
2. Per-category prose section with context and caveats
3. Community consensus section — attribute to specific subreddit/community
4. Locale-specific section (if requested)
5. Domain knowledge section (tax, regulatory, practical context)
6. Honest caveats section: what the community says doesn't work

## Output format discipline

Use this structure for the output file:

```
SECTION 1: [Category 1] (e.g. Backtesting Frameworks)
  — Numbered entries, each with: URL, Stars, Language, What it does, Best for, Caveats
SECTION 2: [Category 2]
SECTION 3: Recommended starter stack for [locale/use-case]
SECTION 4: Community sentiment — per subreddit
SECTION 5: Domain-specific knowledge (tax, regulations, practical context)
SECTION 6: Quick reference table (all tools in one place)
SECTION 7: Honest community wisdom / what doesn't work
SECTION 9: Curated further reading
DISCLAIMER
```

Use ASCII box-drawing for section headers (`━━━`) to make the file scannable
as plain text. Prefix each section number and title clearly.

## Anti-bot & extraction fallbacks

### ATO.gov.au (OFTEN anti-bot blocked)
- **ato.gov.au frequently blocks web_extract** — don't retry with web_extract; escalate then fall back.
- **Escalation path (try in order):**
  1. `web_search` — ATO pages often appear with useful snippet text; fastest, try first
  2. **Camofox stealth browser** — if CAMOFOX_URL is active (http://localhost:9377), ATO uses
     Cloudflare-style bot protection (not Kasada), so Camofox (Firefox + C++ fingerprint spoofing)
     has a good chance of rendering the page. Use `browser_navigate` + `browser_snapshot(full=true)`.
     Check `hermes config get CAMOFOX_URL` to confirm it's set.
  3. `moneysmart.gov.au` — ASIC consumer site, scrapable, accurate for core rules
  4. `budget.gov.au` / `pbo.gov.au` — Budget law and policy explainers, reliable and scrapable
  5. `austax.tools` — CGT reform detail, law-referenced, scrapable
  6. `superguide.com.au`, `heffron.com.au` — super/SMSF specialists, scrapable
  7. `thepropertyaccountant.com.au` — negative gearing, scrapable
- **Do NOT conclude a rule doesn't exist** just because ato.gov.au extraction failed.
  Cross-reference from the secondaries above and flag as "sourced from secondary, verify with ATO."

### Reddit (web_extract works on REAL URLs, not guessed ones)
- **Real Reddit URLs (actual post IDs, search pages, wiki pages) work fine with `web_extract`.**
  Real thread URL format: `reddit.com/r/SUBREDDIT/comments/POST_ID/slug/`
  Real search URL format: `reddit.com/r/SUBREDDIT/search/?q=QUERY&sort=top`
- **Fabricated or guessed Reddit URLs return 500** — do NOT invent Reddit URLs; always
  obtain the real post ID from `web_search` first, then extract the actual thread URL.
- Workflow: `web_search site:reddit.com r/[subreddit] [query]` → copy the real URL from
  results → `web_extract` that URL for full thread content including comments.
- Look for third-party articles that quote Reddit community discussions
  (e.g. biggo.com, medium.com) as an alternative when a specific thread isn't findable.

### GitHub repo pages (usually fine)
- `web_extract` works on most GitHub pages; star count appears in page text.
- For truncated pages, check the cached file: `read_file path="~/.hermes/cache/web/<hash>.md"`

### Australian/community sites
- Stockhead.com.au blocks scraping — use `web_search` snippet only.
- ASX official data site (asxonlinedata.com.au) is paywalled — note this.

## Domain knowledge bank: ASX / Australian Investing

Full detail: **references/asx-australian-investing-knowledge.md** (tax rates, CGT reform, Super, franking, ETFs, trader/investor classification)

Load: `skill_view(name='domain-research-synthesis', file_path='references/asx-australian-investing-knowledge.md')`

Key facts: ASX tickers use `.AX` suffix; CGT 50% discount for assets held >12 months (pre-1 Jul 2027); Super preservation age 60; Franked dividends carry franking credits offsetting tax; Trader classification has strict ATO tests (intent, frequency, volume).


## Domain knowledge bank: PPOR and Australian Property

Full detail in references:
- **references/melbourne-property-ppor-2026.md** — PPOR CGT exemption, rent vs buy analysis
- **references/melbourne-property-configuration-2026.md** — configuration details  
- **references/melbourne-suburb-profiles-2026.md** — suburb profiles

Key facts: PPOR CGT exemption S118-110 ITAA 1997; 6-year absence rule; Domain.com.au often blocks web_extract — use realestate.com.au or news sources instead.


## Domain knowledge bank: Algorithmic Trading Tools

Full detail: **references/algo-trading-tools-landscape-2026.md**

Key tools: Backtrader (Python, mature), VectorBT (vectorised, fast), Zipline-Reloaded (Quantopian fork), QuantConnect (cloud), Interactive Brokers API (live trading).


## Pitfalls

Full catalogue: **references/pitfalls-catalogue-2026.md**

Load: `skill_view(name='domain-research-synthesis', file_path='references/pitfalls-catalogue-2026.md')`

**Subagent + Reddit combination burns 900s timeout when web_search is down.** If a subagent
is tasked to use both reddit.py and web_search fallbacks, and web_search fails (provider config
error), the subagent will loop between both broken paths and consume its full timeout with no
output. Brief subagents to: (1) check if web_search works on first call; (2) if it fails with
a provider error, pivot immediately to web_extract on known-good Reddit search URLs or stick
exclusively to the reddit.py script. Never retry a tool whose error is a provider config issue.

**Pre-flight check before any Phase 1 search:** verify `web_search` provider is operational.
If you get `'web is configured to use \'serpapi\' but no registered provider has that name'`,
`web_search` is dead for this session — skip it entirely and go straight to `web_extract`
on known-good URLs (brand product pages, Sleep Foundation, Good Housekeeping, PubMed, etc.).
Do NOT retry `web_search` with different queries; the error is a provider configuration issue,
not a query issue. Subagents that hit this silently stall on retries — brief them to fallback
to direct URL extraction if `web_search` returns a provider-not-found error.

**SleepFoundation.org blocks `web_extract` (Internal Server Error)** — use Good Housekeeping,
Mattress Clarity, or Wired as alternatives for sleep product research. PubMed search pages
render but individual abstract pages require cookies; use the search results page to identify
PMIDs, then extract from Europe PMC (`europepmc.org/article/MED/<PMID>`) which has no cookie wall.

Top 5 recurring pitfalls:
1. **Parallelise Phase 1 aggressively** — batch 6–8 searches in one call; sequential wastes round-trips.
2. **arXiv REST API can return 0 bytes silently** — not a key issue; use HTML search page fallback.
3. **Reddit requires real post IDs** — fabricated Reddit URLs return 500; use web_search to get real thread URLs (with post IDs), then web_extract those. Search pages and wiki pages also work.
4. **Domain/realestate block direct extraction** — use news articles citing their data as proxy.
5. **Melbourne suburb median data conflicts** — always cite source + date. Use SQM Research, CoreLogic, Domain news as triangulation points.

### /tmp report volatility - regeneration pattern
Reports written to /tmp/ are volatile and lost on reboot. When asked to regenerate a prior report:
1. Check /tmp/BASENAME* - if present, use as base for incremental update.
2. If absent, load references/DOMAIN-*.md knowledge banks and synthesize from them.
3. Warn user: Previous report was in /tmp and has been lost - regenerated from knowledge bank.
Never silently return an empty document; explicitly report missing source data.


## Verification checklist

Before writing the output file:
- [ ] At least 8–10 tools covered with verified star counts
- [ ] At least 2 community sources (subreddits/forums) represented
- [ ] Locale-specific section included if requested
- [ ] Honest caveats/limitations included
- [ ] Quick reference table present
- [ ] Disclaimer ("not financial/legal advice") present on finance/legal topics
- [ ] Output file written with `write_file` (not echoed to terminal)

## Support files
- `references/pead-momentum-factor-research-2026.md` — Deep academic evidence on PEAD
  and price momentum factors: Bernard-Thomas 1989 quantified findings, size-cap decay
  table (micro through mega, gross and net after costs), Chan-Jegadeesh-Lakonishok 1996
  vs Chordia-Shivakumar 2006 vs Novy-Marx 2015 debate (are they the same factor?),
  momentum crashes magnitude/mechanism/forecastability (Daniel-Moskowitz 2016), decay
  evidence (McLean-Pontiff 2016, Lee/KAIST 2025, Nullberg 2017-2026 out-of-sample),
  regime dependency (Cooper-Gutierrez-Hameed 2004), Japan failure (Asness 2011), and
  complete citation verification status table. August 2026.
- `references/algo-trading-tools-landscape-2026.md` — verified tool landscape,
  star counts, community consensus (July 2026 research)
- `references/trading-strategies-academic-evidence-2026.md` — verified academic
  findings on momentum, mean reversion, portfolio construction, market timing,
  day trading profitability, and factor investing (July 2026, quantified results)
- `references/sector-correlation-pead-kelly-sizing-2026.md` — sector ETF correlations
  (XLK/XHB/ITA/XAR live data August 2026), mortgage lock-in academic evidence (FHFA
  WP24-03, Fed 2025, Philly Fed 2026), PEAD current status debate (Martineau 2022,
  Subrahmanyam 2025), Kelly criterion quantified reference (fractions table, Chopra-Ziemba
  ratio, factor crowding portfolio math), momentum crash drawdowns (2009 -35%/-80%,
  2020 -28%), and circuit breaker evidence (stops doubled Sharpe in momentum strategies)
- `references/melbourne-property-ppor-2026.md` — Melbourne property market
  snapshot (June 2026), PPOR CGT exemption value, rent-vs-buy framework,
  stamp duty payback, and leading indicators for market bottom
- `references/melbourne-suburb-profiles-2026.md` — Per-suburb profiles for
  PPOR research: Carnegie, Murrumbeena, Ormond, Glen Huntly, McKinnon,
  Bentleigh, Fairfield, Clifton Hill, Eltham, **Cheltenham** (added Aug 2026 with
  REIV August data, townhouse comparable sales, SRL terminus assessment). Covers
  median prices (Aug 2026 refresh), 5/10-yr growth, school zones, auction clearance
  by region, rental yields, budget fit, demographic profiles, SRL corridor note,
  and anti-bot source guide. Budget context: $1.2M (stretch). Last patched Aug 2026.
- `references/negative-gearing-cgt-reform-2026.md` — Enacted law (26 Jun 2026):
  negative gearing restriction (established dwellings, 1 Jul 2027), CGT discount
  replacement (indexation + 30% min tax), grandfathering rules, lock-in effect,
  PPOR exemption unchanged, market impact estimates (CBA/AMP/ANZ/Domain), key dates.
- `references/melbourne-suburb-growth-drivers-2026.md` — Evidence base for
  suburb-level price growth factors (rail uplift %, school zone premiums REIV
  table, gentrification signals and Melbourne wave pattern, 2017–19 downturn
  recovery suburb-by-suburb data, SRL East per-suburb assessment, McKinnon zone
  quantified premium, downturn resilience checklist). Research date July 2026.
- `references/melbourne-north-east-suburb-profiles-2026.md` — Per-suburb profiles
  for PPOR research in the NORTH (Reservoir, Macleod, Watsonia, Greensborough,
  Montmorency, Coburg, Preston, Thornbury) and EAST (Ringwood, Mitcham, Nunawading,
  Croydon, Blackburn, Box Hill South, Doncaster East). Covers median prices, 5-yr
  growth, clearance rates, school zones (EDSC, Balwyn HS, Ringwood SC, Brentwood
  SC zone correction), NEL infrastructure thesis, gentrification wave framework,
  price gap analysis, and recommended search parameters. July 2026 data.
- `references/abs-census-suburb-validation-methodology.md` — ABS Census 2021
  variable correlation analysis against house prices: education attainment (Bach+%)
  strongest predictor, Price-to-Income ratio table for 9 suburbs, Clifton Hill
  dwelling-mix paradox, commute/employment accessibility matrix, building approvals
  supply context (Victoria -44.2% YoY multi-unit, Jan 2026), regional population
  growth context (outer greenfield vs stable established suburbs), GDP.com.au as fast
  ABS aggregator, and RBA RDP 2011-03 key findings. Research date July 2026.
- `references/melbourne-property-configuration-2026.md` — Property configuration
  sweet spot for ~$1.1M Melbourne PPOR: bedrooms (4BR), bathrooms (main+ensuite),
  car spaces (double garage side-by-side), land (550-700m²), with resale rationale,
  suburb ranking at $1.1M, and commercial vs PPOR decision framework. July 2026.
- `references/neurosymbolic-ai-landscape-2026.md` — Verified NeSy framework landscape
  (July 2026): GitHub stars, pip-installability, last-commit activity, production vs
  research tier assessment, LLM+symbolic integration patterns, and local install guide
  for Fedora Linux / Python stack.
- `references/au-active-momentum-alternatives-execution-tax-2026.md` — Active momentum strategy
  for AU investor at 47% rate: SPIVA data (0/22 categories beat index over 15 years), factor ETF
  combined Sharpe evidence (Asness-Moskowitz-Pedersen 2013: ~double single factor), execution drift
  (PEAD slippage near earnings, Han-Zhou-Zhu stop-loss doubles Sharpe, Daniel-Moskowitz crash
  mechanics), backtest vs. live gap (~0–3% net live alpha at retail scale), 12-month hold tradeoff
  analysis, post-2027 reform impact on active strategies, ATO trader classification risk for PEAD,
  and SMSF vehicle quantification ($32k saving per $100k gain short-term vs personal account).
  August 2026.
- `references/equity-trading-strategy-research-2026.md` — Deep research knowledge bank
  for active equity momentum + PEAD strategies (August 2026): verified academic citations
  with DOIs for PEAD (Ball-Brown 1968 through Sadka 2006), momentum (Jegadeesh-Titman
  1993 through Lee 2025 arXiv), the PEAD-vs-momentum independence debate (CJL 1996 vs
  Chordia-Shivakumar 2006 vs Novy-Marx 2015), momentum crash mechanics and forecastability
  (Daniel-Moskowitz 2016), sector correlation data (tech/defense/homebuilders, verified
  August 2026), homebuilder lock-in thesis (FHFA WP24-03), Kelly criterion and factor-
  correlation position sizing, and full Australian CGT overlay including 2027 reform and
  SMSF comparison tables. Full strategy report: /tmp/slava-trading-strategy-report.md.
- AU investing tax knowledge is embedded directly in the Domain knowledge bank
  section above (inline for fast retrieval)
- `references/au-bank-ai-benefit-estimation-2026.md` — AU banking AI benefit
  estimation research (August 2026): NAB trust deed benchmark (45 min → 1 min,
  15K deeds/yr), CBA/Beyond Bank deployments, UK/APAC marketing compliance cases,
  DACH/French banking context, financial services AI ROI benchmark tables, APRA/ASIC
  regulatory obligations, and the full Alternative Benefit Estimation Framework (ABEF)
  — 5 methods for building a defensible business case without stakeholder engagement.
- `references/asian-technical-trading-strategy-research-2026.md` — Academic evidence sweep
  on technical trading strategies in China (A-share), Japan (Nikkei/TSE), and Korea
  (KOSPI/KSC). August 2026.
- `references/research-skill-improvements-2025-2026.md` in `academic-literature-review` skill —
  Full sweep: PaSa, OpenScholar, SPAR, OpenAlex, arXiv sidecars, Agentic RAG survey map,
  GitHub mining patterns (PaperFlow/PwC API/ToolMaker), multilingual corpora (CNKI/CiNii/
  SciELO/BASE/CORE), practitioner stack (NotebookLM/SciSpace/Consensus/scite.ai/STORM),
  benchmark list, and API reference table. August 2026.
- `references/github-research-mining-2026.md` (this skill) — GitHub code/repo mining
  for research: PaperFlow, PwC API, MSR field, awesome-list patterns, ToolMaker,
  RD-Agent, AIDE, search quality heuristics, and star-count pitfalls.
- `references/agent-memory-topology-research-2026-08.md` — AI agent memory topology,
  architecture & ontology sweep (August 2026). 23+ verified arXiv papers with IDs,
  quantified results, and Hermes implementation gap tiers A–D. Covers MemCon, TRUSTMEM,
  RecMem (-87% token cost), MEMTIER, MAGMA, MemGraphRAG (KDD 2026), Memory-R1/AgeMem
  RL-trained memory ops, SSGM governance, EverMemOS engram lifecycle. Community consensus
  and Chinese/Japanese source notes included.
- **`academic-literature-review` skill → `references/arxiv-api-fallback-and-pitfalls.md`** —
  arXiv API timeout fallback sequence + verified agent token-optimization / context-compression
  knowledge bank (20+ papers, August 2026): TokenPilot (61–87% cost), Tool Attention (95%
  tool token reduction), TSCG (44–50% schema savings), IntentKV (77.8% peak token reduction),
  AgentKVShift (2–3.5× prefill speedup), MemDecay (region-aware eviction lifetimes), Online
  KV Compaction (80% KV reduction via delayed compaction), Harness Effect (38% token / 41%
  cost from orchestration alone), SAGE (90% token reduction), Don't Break the Cache (41–80%
  API cost via caching discipline), Control Under Compression (≥75% safety floor). Load when
  researching AI agent efficiency, context compression, or KV cache for Hermes integration.

## Context Interference in Multi-Turn Search (arXiv:2608.10743, Aug 2026)

"Mitigating Context Interference for Reliable and Efficient Search Agents"

Key finding: interference primarily arises from the LATEST retrieved documents, not accumulated
history. A distill-based context refiner after each retrieval step reduces hallucination and
unnecessary extra retrieval turns.

Hermes research pattern:
- After each web_extract/read_file result, extract relevant facts before the next search
- Use execute_code to batch-filter large result sets into summaries before reasoning on them
- When dispatching research subagents: instruct them to summarize each source before moving
  to the next, not collect all sources then summarize at the end

## Self-Ontology Query Expansion for Graphiti/Hindsight (arXiv:2608.11030, Sweep 12)

"Self-Knowledge RAG" — LLMs autonomously extract entity types and hierarchical relationships
from a query and use that structure for retrieval expansion. More effective than pre-built
domain ontologies because the expansion is query-specific, not schema-specific.

**Why it matters here:** Research queries are concept-rich but keyword-poor. A query like
"what do we know about agent memory pipelines?" misses Graphiti nodes labelled AMD, staging.md,
l1-extract, hindsight_retain, source_type — all of which are what the query is actually about.
The self-ontology step bridges this gap without any schema change to Graphiti or Hindsight.

**Pattern — apply before `hindsight_recall` or `mcp__graphiti__search_memory_facts`:**

1. **Entity extraction prompt** (one call, low token cost):
   Before calling recall/search, ask internally:
   "What are the key entities, concepts, and relationships in this query?
    List: (a) named entities, (b) concept types, (c) action verbs, (d) known system components."

2. **Expand the search terms:**
   Use the extracted terms as additional parallel queries alongside the original.
   Example — original: "agent memory pipelines"
   Expanded: ["AMD", "staging.md", "hindsight_retain", "l1-extract", "source_type",
               "Graphiti episodes", "l1-graphiti-write", "memory-facts"]

3. **Run parallel retrieval** with both original and expanded terms:
   ```python
   results_original = hindsight_recall(query="agent memory pipelines")
   results_expanded = hindsight_recall(query="AMD staging.md l1-extract Graphiti episodes")
   # Merge and deduplicate by content hash before reasoning
   ```

4. **When writing Graphiti episodes** (in l1-graphiti-write or hindsight_retain):
   Add extracted entity types as part of the episode text so Graphiti's own extraction
   can build richer node properties. Include: subject, type, relationship, context.
   Prefer: "[source_type=internal] Hermes l1-extract script (type=script, domain=memory-pipeline)
            filters cron_ sessions to prevent automation noise in staging.md"
   Over: "[source_type=internal] l1-extract now filters sessions"

**Pitfall:** Don't expand so broadly that the retrieval returns noise. Cap expansion at 6–8
additional terms. If the expanded query returns more than 30 results, filter to top-5 by
relevance score before merging with the original result set.
## Reference files

- `references/au-consumer-product-research-notes.md` — AU consumer product research methodology:
  output format for product reports (Telegram-friendly), AU sleep product brand & extraction
  notes, pillow science reference (cervical alignment PMID citations, cooling material grades,
  combo sleeper pick hierarchy and AU ranked list Sep 2026).
- `references/coffee-brewing-recipes.md` — V60/pour-over recipe domain knowledge: Kasuya 4:6,
  Hoffmann Better 1-Cup, Winton 5-Pour, Osmotic Flow; ZP6 dial-in reference; fast-flow paper
  impact; temperature guide for medium-light roast; research workflow for recipe queries.
- `references/au-cruise-market-2026.md` — Australian short cruise market knowledge bank (Sep 2026): P&O shutdown, Carnival/RC ship roster, Sydney/Brisbane schedule patterns, CruiseTimetables search workflow, live booking sources, gratuities note, Quantum of the Seas BNE schedule, premium-line absence from short-break market.
- `references/winter-jacket-research-2026.md` — Winter jacket domain knowledge bank: down construction taxonomy (sewn-through vs box-wall vs shell/liner), windproof vs wind-resistant distinction, wax cotton + wool category, AU stockist table, spec relaxation framework. August 2026.
- `references/au-marketing-compliance-llm-testing-landscape-2026.md` — AU Marketing Compliance + LLM Testing Tool Landscape
- `references/report-regeneration-and-multilang-sweep-workflow.md` — Report Regeneration & Multilingual Academic Sweep Workflow
- `references/sme-lending-origination-delay-research-2026.md` — SME Loan Origination Delay — Research Knowledge Bank
- `references/technical-trading-strategies-multilang-2026.md` — Technical Trading Strategies — Cross-Market Evidence & Multilingual Sweep
- `references/vervaeke-meaning-crisis-critiques-2026.md` — Vervaeke 'Awakening from the Meaning Crisis' — Critique Knowledge Bank

### Multilingual sweep: parallel 3-cluster dispatch
For international academic coverage, dispatch three clusters in the same turn:
- Cluster 1 (CJK): arXiv (CN affiliation filter), J-STAGE (Japan), CyberLeninka (Russia)
- Cluster 2 (Latin): SciELO (Brazil/Spain/Portugal), Dialnet (Spanish social science)
- Cluster 3 (EU): BASE (300M+ EU docs), CORE (UK/EU open access)
Trigger: any topic where English-only sources miss regional evidence (Asian markets, property, compliance).

## Pipeline position

This skill sits in the middle of the research pipeline:
`arxiv` (discovery) → `domain-research-synthesis` (you are here) → `arxiv-sweep-findings` (skill patches)

When synthesis produces findings targeted at the Hermes skill library, pass them to `arxiv-sweep-findings`.
Note: curator-managed target skills require `hermes curator adopt <skill>` before patches can apply.
