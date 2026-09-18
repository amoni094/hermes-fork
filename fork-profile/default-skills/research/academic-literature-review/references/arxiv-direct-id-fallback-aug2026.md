# arXiv Direct-ID Fallback Pattern (Aug 2026)

## Context
SerpAPI 429 rate-limits block `web_search` in high-volume research sweeps. This pattern emerged from the Aug 11 2026 agent KG/memory/skill sweep where SerpAPI hit 429 on ~6 consecutive queries but `web_extract` on arXiv remained fully available.

## Fallback Hierarchy (most → least yield)

### Tier 1: Direct arXiv ID batch extraction (HIGHEST YIELD when IDs known)
```python
# Batch up to 3 IDs per call
web_extract(urls=[
    "https://arxiv.org/abs/2608.05563",
    "https://arxiv.org/abs/2608.02636",
    "https://arxiv.org/abs/2607.21962",
])
```
Returns: full title, authors, submission history, venue (from comments), abstract. Complete and verified.

### Tier 2: arXiv search page (when IDs not yet known)
```python
# ≤4 content words — longer queries return 0 results
web_extract(urls=[
    "https://arxiv.org/search/?searchtype=all&query=agent+skill+trust+versioning&start=0&order=-announced_date_first"
])
```
Returns: titles + short abstracts + arXiv IDs for top 25–200 matches (varies). Use to discover IDs, then batch-extract with Tier 1.

Pitfall: multi-word compound queries ("skill uncertainty quantification versioning trust") → 0 results. Use ≤4 words max.

### Tier 3: arXiv listing walk (for very recent papers not yet indexed by search)
```python
# Papers from the last ~2 weeks by submission date
web_extract(urls=["https://arxiv.org/list/cs.AI/2026-08"])
web_extract(urls=["https://arxiv.org/list/cs.MA/2026-08"])
```
Returns: all submissions in a month. Highest recall for cutting-edge papers (pre-search-index). Noisy — scan abstracts for relevance.

### Tier 4: Known-paper forward traversal via Semantic Scholar
```python
web_extract(urls=["https://api.semanticscholar.org/graph/v1/paper/arXiv:2608.05563/citations"])
```
Finds papers that *cite* a known anchor paper. Good for finding responses/extensions.

## Blocked Multilingual Sources (Aug 2026)

These were all blocked in the Aug 11 2026 sweep:
- **HAL (France):** Anubis proof-of-work bot protection — JavaScript required, web_extract fails
- **Zhihu (China):** Anti-scraping "Internal Server Error" on direct article URLs
- **J-STAGE (Japan):** Accessible for search but full-text paywalled; metadata only
- **RISS/KISS (Korea):** Not directly accessible via web_extract

### Effective workaround
Chinese/Japanese/Korean/French researchers who publish in these venues also publish to arXiv simultaneously. Search arXiv with institution names:
- Chinese: "Tsinghua", "Peking University", "Zhejiang", "Alibaba", "ByteDance", "IAAR-Shanghai", "CAS"
- Korean: "KAIST", "POSTECH", "Seoul National University", "NAVER"
- Japanese: "NTT", "Fujitsu", "Waseda", "Tokyo Institute of Technology"
- French: "INRIA", "Sorbonne", "CentraleSupélec", "LIG"

This approach found: SkillComposer (Alibaba/Zhejiang), SEMA (Chinese Academy), Agentic-KGR, AutoWorldBuilder in the Aug 11 sweep — all Chinese-institution origin, all on arXiv with English abstracts.

## When to Switch Fallback Tiers

| Signal | Action |
|--------|--------|
| 2 consecutive web_search 429s | Switch to web_extract for rest of session |
| arXiv search returns 0 results | Shorten query to ≤4 words |
| arXiv search returns irrelevant results | Use Tier 3 listing walk instead |
| Need papers <2 weeks old | Tier 3 (listing) before Tier 2 (search) |
| Have anchor paper, need responses | Tier 4 (Semantic Scholar citations) |

## Session Budget Discipline with Direct-ID Pattern

When using Tier 1 (direct ID batch), a full 7-topic sweep requires ~20–30 web_extract calls:
- 5–8 calls: arXiv search pages (Tier 2) to discover candidate IDs per topic cluster
- 12–18 calls: direct ID batches (Tier 1) at 3 IDs/call to verify candidates
- 2–3 calls: listing walk (Tier 3) for very recent papers

This is approximately 2–3× more efficient than search-based approaches when SerpAPI is down, because each ID-batch call verifies 3 papers simultaneously vs. 1 search result page + separate verification.
