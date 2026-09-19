---
name: firecrawl-research
related_skills:
  - academic-literature-review
  - domain-research-synthesis
  - competitor-news-monitor
  - blocked-page-recovery
  - defuddle
  - obsidian-research-ingestion
  - firecrawl-stealth-fallback

provides: [web_search, web_extract]
description: >
  Use when: Use the local Firecrawl self-host as the default crawl/scrape/research retrieval layer, with search mainly for discovery and Firecrawl for extraction.
version: 1.0.0
license: MIT
platforms: [linux, macos, windows]
metadata:
  tags: [firecrawl, research, crawling, scraping, extraction, local-first]
  hermes:
    related_skills: [academic-literature-review, domain-research-synthesis, competitor-news-monitor, blocked-page-recovery, defuddle, obsidian-research-ingestion, firecrawl-stealth-fallback]
triggers:
  - Task requires crawling a website or extracting clean text from one or more URLs
  - web_extract is insufficient (JavaScript-heavy, dynamic content, pagination, multi-page crawl)
  - User says "scrape", "crawl", "extract from website", or "get content from URL"
  - Research task requiring clean markdown from live web pages as input
  - Firecrawl local self-host is available at http://127.0.0.1:3002 — prefer it over web_extract for extraction
  - NOT for simple static-page article extraction where web_extract/defuddle is sufficient
  - NOT for arXiv PDFs — use arxiv skill + web_extract directly
---

# Firecrawl Research

Use this when the task involves crawling a site, scraping one or more pages, turning URLs into clean text, or building research from live web pages.


## Model Routing

Multi-source web synthesis (web_search + web_extract only, no execute_code/terminal): deepseek-v4-pro non-think dedicated session. Fallback: dedicated grok-4.6 session. ELIGIBLE when: (1) synthesis-dominant, (2) tools limited to web_search/web_extract/read_file. Non-think mode only.


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

## Pitfalls

- **Check `/` not `/v1/health`** — this self-host image returns 404 on `/v1/health`. Always probe `GET /` as the liveness check.
- **Stack-down vs target-blocked** — if `example.com` scrapes fine but Reuters returns 403, Firecrawl is healthy; the issue is site-specific. Do not restart the stack to fix a target-specific block.
- **Bypass scope** — when the user says "no anti-bot bypass", do not escalate to stealth browsers, CAPTCHA solvers, or proxy rotation. Use RSS/Atom, official APIs, or mark the article unavailable.
- **Claiming extraction without retrieving** — do not say a page was extracted unless Firecrawl actually returned content for that URL. Discovery hits are not extractions.
- **crawl4ai vs Firecrawl scope** — use Firecrawl for 1-10 pages; switch to crawl4ai for multi-page BFS/DFS crawls (10–1000 pages), schema extraction, or crash-resumable jobs.
- **podman compose PATH** — when making Firecrawl durable under systemd user services, use an explicit compose binary path (`/usr/bin/podman compose`) in the unit file; `podman compose` depends on a provider that may not be in the unit's PATH.
- **Stale web_extract failure** — after Hermes provider/env wiring changes, verify `web_extract` from a fresh Hermes process before concluding the Firecrawl integration is broken. A stale tool-bundle failure does not prove the fix failed.

## Local notes
- Local Firecrawl endpoint: `http://127.0.0.1:3002`
- Verified good endpoint: `GET /`
- Known bad health probe for this image: `GET /v1/health` returns 404
- See `references/local-firecrawl.md` for command snippets and `references/firecrawl-systemd-user-service.md` for a durable user-service pattern.

## MinerU2.5: Chinese SOTA vision PDF parser (arXiv 2509.22186, OpenDataLab/Shanghai AI Lab)

MinerU2.5 (OpenDataLab / Shanghai AI Lab) scores 90.67 on OmniDocBench — SOTA globally,
surpassing Gemini 2.5 Pro at 1.2B parameters. 18K+ GitHub stars.
GitHub: https://github.com/opendatalab/MinerU

This is the production alternative to RAGFlow's DeepDoc when higher accuracy is needed.
OmniDocBench (arXiv 2412.07626, CVPR 2025) is the global standard benchmark for document
parsing — Chinese-built and Chinese-dominated (MinerU2.5, PaddleOCR-VL both Chinese-origin).

Other strong Chinese-origin vision PDF tools in this space:
- **PaddleOCR-VL** (2510.14528, Baidu): 0.9B VLM, 109 languages, SOTA on OmniDocBench.
  GitHub: https://github.com/PaddlePaddle/PaddleOCR (41K+ stars)
- **Dolphin** (2505.14059, ByteDance, ACL 2025): Analyze-then-parse, parallel decoding.
  GitHub: https://github.com/ByteDance/Dolphin
- **MinerU-Diffusion** (2603.22458, OpenDataLab 2026): OCR as inverse rendering via
  diffusion decoding — a genuinely novel paradigm, not incremental improvement.

Decision table for vision PDF extraction in Hermes pipelines:

| Need | Tool | Notes |
|------|------|-------|
| General accuracy (SOTA) | MinerU2.5 | 90.67 OmniDocBench; pip install magic-pdf |
| 109-language multilingual | PaddleOCR-VL | Best for non-Latin scripts |
| Tables + structured layout | RAGFlow DeepDoc | Good table structure recognition |
| Parallel large batch | Dolphin (ByteDance) | Analyze-then-parse pattern |
| Firecrawl with JS rendering | Firecrawl scrape_url | For web-rendered docs |

## SemCAFE / CrediBench: entity-level and graph-level source credibility

### SemCAFE (arXiv 2504.08776, Uni Duisburg-Essen + Univ. Caen Normandie 🇩🇪🇫🇷)
Entity-level reliability scoring beyond domain-level signals:
- YAGO entity fingerprinting on 49K Ukraine-war articles
- +12% macro F1 vs. standard credibility filters
- Links source claims to named entities, scores the entity's credibility track record
  (not just the domain or publisher)

Hermes application: after SourceBench composite scoring (above), apply entity-fingerprinting
as a second pass for factual claims that involve specific named entities. If the source's
entity has a low trust score in a credibility graph, flag the claim specifically.

### CrediBench (arXiv 2509.23340, McGill/Mila + Oxford, KDD 2026)
Temporal web graph credibility — 40M+ node graph:
- Accuracy improvement: 56% → 85%
- MAE: 0.162 → 0.107
- Key innovation: temporal credibility signals — a source's reliability changes over time.
  A once-credible outlet that later published misinformation loses trust incrementally.
  CrediBench's temporal graph tracks this drift.

Hermes practical note: for news/research crawling, apply time-window credibility scoring —
a source's credibility from 3 years ago may not apply today. Add `source_vintage` check:
```python
def credibench_vintage_check(url: str, pub_date: str, source_domain: str) -> float:
    """Discount credibility for sources with recent reliability degradation."""
    import datetime
    pub_year = int(pub_date[:4]) if pub_date else 2020
    age_years = datetime.datetime.now().year - pub_year
    # Apply recency penalty for stale-domain sources (>2yr old low-quality domain signal)
    KNOWN_DEGRADED = {'naturalnews.com', 'zerohedge.com', 'infowars.com'}
    if source_domain in KNOWN_DEGRADED and age_years > 2:
        return 0.1  # strong penalty
    return 1.0  # no penalty — let SourceBench composite score stand
```

## CRAAP + SourceBench source credibility filter (upgraded from CRAAP to 8-metric framework)

### SourceBench 8-metric framework (arXiv 2602.16942, ICML 2026)
SourceBench evaluated 3,996 cited sources across 100 queries and found that standard
credibility signals are insufficient. The 8-metric framework covers:

Content quality metrics (check via LLM or regex heuristics):
  1. Content relevance — does the page actually address the query, or is it tangential?
  2. Factual accuracy — cross-check specific claims against known facts
  3. Objectivity — detect marketing CTAs, advocacy language, conflict-of-interest patterns

Page-level signals (extractable from headers/metadata):
  4. Freshness — publication/update date; prefer < 2 years for technical topics
  5. Authority/accountability — identifiable author, institution, or organizational byline
  6. Clarity — readable prose vs. SEO-stuffed keyword lists

Extended signals (found to matter in SourceBench evaluation):
  7. Source type — academic paper > institutional report > quality journalism > blog > social
  8. Citation support — internal citations to primary sources vs. unsupported assertions

Key SourceBench finding: pages dominated by navigational artifacts ("Find a Doctor",
"Sign In") and commercial CTAs scored consistently low on authority/content quality —
these are flagged by detecting high ratio of UI-chrome text to informational content.

### Implementation

```python
import re, datetime

def sourcebench_score(url: str, content: str, query: str) -> dict:
    scores = {}

    # 1. Content relevance — query keyword coverage
    query_terms = set(query.lower().split())
    content_lower = content.lower()
    hits = sum(1 for t in query_terms if t in content_lower)
    scores['relevance'] = min(hits / max(len(query_terms), 1), 1.0)

    # 2. Freshness — look for date patterns
    date_patterns = [
        r'202[3-6][-/]\d{2}[-/]\d{2}',  # ISO date
        r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+202[3-6]',
    ]
    has_recent_date = any(re.search(p, content) for p in date_patterns)
    scores['freshness'] = 1.0 if has_recent_date else 0.4

    # 3. Authority — institution/author signals
    authority_signals = ['doi.org', 'arxiv.org', 'pubmed', 'reuters', 'bbc.com',
                         'gov.au', '.gov', 'university', 'research', 'professor']
    scores['authority'] = min(sum(1 for s in authority_signals if s in url + content_lower) * 0.2, 1.0)

    # 4. Objectivity — commercial/CTA density
    cta_patterns = ['buy now', 'sign up', 'subscribe', 'click here', 'limited time',
                    'find a doctor', 'contact us', 'get started']
    cta_density = sum(content_lower.count(p) for p in cta_patterns) / max(len(content.split()), 1)
    scores['objectivity'] = max(0.0, 1.0 - cta_density * 50)  # penalize heavily

    # 5. Source type bonus
    if any(x in url for x in ['arxiv.org', 'doi.org', 'pubmed', 'acm.org', 'nature.com']):
        scores['type_bonus'] = 1.0
    elif any(x in url for x in ['.gov', '.edu', 'reuters', 'ap.org', 'bbc']):
        scores['type_bonus'] = 0.8
    elif any(x in url for x in ['wikipedia', 'github.com']):
        scores['type_bonus'] = 0.6
    else:
        scores['type_bonus'] = 0.4

    # Composite — weighted
    composite = (scores['relevance'] * 0.3 + scores['authority'] * 0.25 +
                 scores['freshness'] * 0.2 + scores['objectivity'] * 0.15 +
                 scores['type_bonus'] * 0.1)
    scores['composite'] = round(composite, 3)
    return scores

# Usage: filter sources with composite < 0.5
```

This replaces the simpler 5-criteria CRAAP heuristic. Accept sources with composite >= 0.5,
flag for review at 0.35-0.50, reject below 0.35.

## CRAAP source credibility filter (OpenFang Researcher pattern)

Before feeding crawled content into Graphiti or Hindsight, apply CRAAP criteria to
filter low-quality sources. OpenFang's Researcher Hand applies this as a scoring pass
before any extracted fact is committed to the knowledge graph.

CRAAP = Currency, Relevance, Authority, Accuracy, Purpose.

Quick scoring heuristic (add to any post-crawl pipeline):

```python
def craap_score(url: str, content: str, query: str) -> float:
    """Return 0.0-1.0 credibility estimate. Below 0.4 = discard."""
    score = 0.0
    # Currency: prefer recent content
    if any(str(y) in content for y in range(2023, 2027)): score += 0.2
    # Relevance: query terms present
    hits = sum(1 for w in query.lower().split() if w in content.lower())
    score += min(hits / max(len(query.split()), 1), 1.0) * 0.2
    # Authority: domain signals
    trusted = [".gov", ".edu", ".org", "reuters", "arxiv", "github", "bbc"]
    if any(d in url for d in trusted): score += 0.2
    # Accuracy: no sensational signals
    red_flags = ["clickbait", "you won't believe", "100% guaranteed", "conspiracy"]
    if not any(r in content.lower() for r in red_flags): score += 0.2
    # Purpose: not a pure ad/marketing page
    ad_signals = ["buy now", "limited offer", "subscribe to unlock"]
    if not any(a in content.lower() for a in ad_signals): score += 0.2
    return score

# In a crawl pipeline:
results = firecrawl.batch_scrape(urls)
quality_results = [r for r in results if craap_score(r["url"], r["content"], query) >= 0.4]
```

Apply before: Graphiti add_memory, Hindsight hindsight_retain, or any knowledge graph ingestion.
Skip for: trusted first-party sources (official docs, your own repo, known curated feeds).

## DeepDoc: vision-based PDF/table extraction (RAGFlow pattern)

For crawled PDFs or documents with complex tables, RAGFlow's `DeepDoc` parser is far
superior to naive pdf-to-text. It runs a vision pipeline:
  layout detector (10-class: Text, Title, Figure, Table, Header, Footer, Reference, Equation)
  → Table Structure Recognition (TSR, 5-class cells)
  → OCR with confidence-scored rotation at 4 angles
  → output: text chunks with PDF page + bounding-box coordinates

DeepDoc parsers are importable standalone without the full RAGFlow stack:
```python
# pip install ragflow-sdk  OR  git clone + from deepdoc.parser import PdfParser
from deepdoc.parser import PdfParser

parser = PdfParser()
chunks = parser(pdf_path)  # returns list of (text, page_num, bbox) tuples
# Each chunk has coordinates → preserves document structure as chunk metadata
```

Table cells are re-serialized as natural-language sentences for embedding rather than
raw cell text — this dramatically improves table retrieval quality.

When to use DeepDoc vs default extraction:
- Annual reports, academic papers, legal docs with complex tables → DeepDoc
- Simple web pages, plain-text articles → Firecrawl default
- Scanned PDFs → DeepDoc (OCR pipeline handles rotation artifacts)

## EraRAG: LSH-based incremental index update — 10x faster than full re-index (arXiv 2506.20963)

EraRAG (Fangyuan Zhang, Di Jiang/WeBank AI, Yixiang Fang/HKU — University of Hong Kong):
GitHub: https://github.com/EverM0re/EraRAG-Official

Standard GraphRAG/ChromaDB pipelines re-index the entire corpus on any document change.
EraRAG's hyperplane-based LSH partitioning enables localized insertions without disrupting
existing topology: **update time reduction up to 10x** on large-scale benchmarks.

LSH change detection algorithm:
1. On ingest, assign each document chunk to an LSH bucket (hyperplane partition)
2. On update, compute new chunk's LSH hash
3. If hash falls within an existing bucket → append to that cluster (O(log n))
4. If hash is in a NEW bucket → create new cluster without touching existing ones
5. Only re-embed and re-graph documents in affected buckets

Implementation for Hermes Firecrawl pipeline:
```python
import hashlib, json

def lsh_bucket_key(text: str, n_planes: int = 8) -> str:
    """Simple simhash-style LSH bucket key for change detection."""
    # Use multiple hash planes for locality-sensitive bucketing
    h = int(hashlib.sha256(text.encode()).hexdigest(), 16)
    # Project onto n_planes hyperplanes using bit extraction
    planes = [(h >> i) & 1 for i in range(n_planes)]
    return ''.join(map(str, planes))

class DeltaCrawler:
    def __init__(self, state_file: str = "crawl_state.json"):
        self.state_file = state_file
        try:
            self.state = json.load(open(state_file))
        except FileNotFoundError:
            self.state = {"url_hashes": {}, "lsh_buckets": {}}

    def needs_reindex(self, url: str, content: str) -> bool:
        """True if content has changed since last crawl."""
        new_hash = hashlib.sha256(content.encode()).hexdigest()
        old_hash = self.state["url_hashes"].get(url)
        if new_hash == old_hash:
            return False  # unchanged — skip
        # Check if LSH bucket changed (implies topology change)
        new_bucket = lsh_bucket_key(content)
        old_bucket = self.state["lsh_buckets"].get(url)
        self.state["url_hashes"][url] = new_hash
        self.state["lsh_buckets"][url] = new_bucket
        return True  # changed

    def save(self):
        json.dump(self.state, open(self.state_file, 'w'), indent=2)
```

Use alongside CocoIndex etag/last-modified tracking (below). EraRAG's LSH is the
topology-aware layer; CocoIndex's etag/SHA-256 is the content-hash layer. Together:
skip-if-etag-unchanged → skip-if-SHA256-unchanged → LSH-bucket-aware partial re-index.

## Incremental delta-crawl pattern (CocoIndex principle)

Avoid re-crawling unchanged pages. CocoIndex's core design uses content-fingerprinting +
change detection to process only what has changed since the last run.

Apply the same principle to Firecrawl and crawl4ai workflows:

### HTTP-level delta detection (for web crawls)
```python
import hashlib, json, os, time

cache_file = "~/.hermes/cache/crawl-state.json"
state = json.load(open(os.path.expanduser(cache_file))) if os.path.exists(os.path.expanduser(cache_file)) else {}

def should_recrawl(url: str, response_headers: dict) -> bool:
    etag = response_headers.get("etag")
    last_modified = response_headers.get("last-modified")
    cached = state.get(url, {})
    
    if etag and etag == cached.get("etag"):
        return False  # unchanged
    if last_modified and last_modified == cached.get("last_modified"):
        return False  # unchanged
    return True

def update_state(url: str, headers: dict, content_hash: str):
    state[url] = {
        "etag": headers.get("etag"),
        "last_modified": headers.get("last-modified"),
        "content_hash": content_hash,
        "crawled_at": time.time()
    }
    json.dump(state, open(os.path.expanduser(cache_file), "w"), indent=2)
```

### Content-hash delta detection (for file/corpus crawls)
When crawling a local corpus or file system, hash each document before processing:
```python
def content_changed(path: str, state: dict) -> bool:
    h = hashlib.sha256(open(path, "rb").read()).hexdigest()
    if state.get(path) == h:
        return False
    state[path] = h
    return True
```

### When to use delta-crawl
- Recurring cron-based crawl jobs (news, documentation sites)
- Re-indexing a local corpus (~/Religion texts, documents)
- Any crawl that runs more than once on the same URL set

### Conversation-to-knowledge pipeline (CocoIndex pattern)
After crawling a set of pages or processing conversation transcripts, extract structured
facts as entities into the graph rather than just storing raw text:

```python
# Post-crawl: extract entities from each page
for page in crawled_pages:
    entities = llm_extract(
        text=page.content,
        prompt="Extract: people, organizations, topics, decisions, key claims as JSON"
    )
    mcp_graphiti_add_memory(
        name=f"crawl:{page.url}",
        episode_body=page.content,
        group_id="hermes"
    )
# Graphiti handles entity dedup + relationship graph automatically
```

This is the same pipeline CocoIndex calls `conversation_to_knowledge` — also applicable
to any structured text extraction task.

## CDP attach to user's existing Chrome (MediaCrawler pattern)

For auth-required targets, heavily rate-limited APIs, or platforms with JS-based request signing, attach to the user's **real, already-logged-in Chrome** via CDP. Full setup, Playwright snippets, agent-browser CLI, JS-signing trick, session caching, and Fedora Silverblue/Kasada notes are in the `firecrawl-stealth-fallback` skill — load it when you need this path.

Quick decision table:

| Situation | Use |
|---|---|
| Public page, no auth needed | Firecrawl or web_extract |
| Cloudflare / bot check, no auth | firecrawl-stealth-fallback |
| Login required OR JS-signed API | CDP-attach (see firecrawl-stealth-fallback) |
| Kasada-protected site | CDP-attach — only reliable option |
| Multi-page deep crawl, no auth | crawl4ai |

## Crawl4AI: complementary tool for deep crawls and structured extraction

Use crawl4ai when Firecrawl is the wrong tool for the job:

| Situation | Use |
|---|---|
| Single page or short URL list, no bot protection | Firecrawl scrape |
| Single page, heavy bot protection | firecrawl-stealth-fallback |
| Multi-page site crawl, 10–1000s of pages | crawl4ai |
| Structured schema extraction (CSS/XPath/regex selectors) | crawl4ai |
| Deep BFS/DFS/BestFirst crawl with URL scoring | crawl4ai |
| Long-running crawl that needs crash recovery + resume | crawl4ai |
| LLM-ready Markdown with citations, tables, code preserved | crawl4ai |
| Downloading binary files (PDF, CSV) discovered during crawl | crawl4ai |

### Install (one-time, per-venv)
```bash
pip install -U crawl4ai
crawl4ai-setup       # installs Playwright + Chromium
crawl4ai-doctor      # verify
```

### CLI quick reference
```bash
# Single page -> markdown
crwl https://example.com -o markdown

# Deep crawl BFS, max 10 pages
crwl https://docs.example.com --deep-crawl bfs --max-pages 10

# LLM extraction with a question
crwl https://example.com/products -q "Extract all product prices"
```

### Python quick reference
```python
import asyncio
from crawl4ai import AsyncWebCrawler

async def main():
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url="https://example.com")
        print(result.markdown)

asyncio.run(main())
```

### Extraction strategies
- `JsonCssExtractionStrategy` — CSS selector → structured JSON
- `JsonXPathExtractionStrategy` — XPath selector → structured JSON
- `RegexExtractionStrategy` — regex patterns → structured JSON
- `CosineStrategy` — semantic similarity pruning
- `PruningContentFilter` — noise removal with `preserve_classes`/`preserve_tags` whitelist

### Deep crawl options
- Strategy: `bfs` (default), `dfs`, `best_first` (scored)
- `resume_state` + `on_state_change` callbacks for crash recovery on long runs
- `prefetch=True` for 5-10x faster URL discovery

### Pitfalls
- crawl4ai uses Playwright/Chromium under the hood; keep browser install current with `crawl4ai-setup`.
- For bot-protected targets, combine with proxy/session config or escalate to firecrawl-stealth-fallback.
- `arun_many` for parallel URL lists; don't loop `arun` in sequence for large batches.
- v0.9.0+ Docker server is secure-by-default: auth on, loopback-only bind unless token provided.

## Firecrawl User Systemd Durability Pattern (from firecrawl-systemd-user-service.md)

**Symptom:** `web_extract` or Firecrawl-backed retrieval fails with `connection refused` on 127.0.0.1:3002 after reboots/logouts. Containers are stopped; manual `podman-compose up -d` restores service.

**Fix:** Create a user systemd service unit:
```ini
[Unit]
Description=Firecrawl self-host stack (Podman Compose)
After=network-online.target
Wants=network-online.target
[Service]
Type=oneshot
WorkingDirectory=/var/home/rainbow/firecrawl-selfhost
RemainAfterExit=yes
ExecStart=/var/home/rainbow/.local/bin/podman-compose up -d
ExecStop=/var/home/rainbow/.local/bin/podman-compose down
TimeoutStartSec=180
TimeoutStopSec=120
[Install]
WantedBy=default.target
```
**Activation:** `systemctl --user daemon-reload && systemctl --user enable --now firecrawl.service`

**Pitfall:** Do NOT assume `podman compose` works in a user systemd unit just because it works interactively. The unit PATH may not expose the compose provider. If you see `looking up compose provider failed` or `podman-compose: executable file not found`, use the **explicit full binary path** in `ExecStart`/`ExecStop`.

**Verification:**
```bash
systemctl --user is-active firecrawl.service
curl -sS http://127.0.0.1:3002/
podman ps --format '{{.Names}}|{{.Status}}' | grep '^firecrawl_'
```

## Related skills
- `firecrawl-stealth-fallback` — CDP-attach details, Kasada bypass, stealth escalation workflow (in autonomous-ai-agents/ category)
- `academic-literature-review` — feeds this skill for URL extraction during paper sweeps
- `domain-research-synthesis` — uses Firecrawl as extraction backend
- `competitor-news-monitor` — uses Firecrawl for feed/page ingestion
- `obsidian-research-ingestion` — depends on this skill for URL extraction
- `hermes-web-provider-configuration` — provider-level configuration
