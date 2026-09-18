# Research Source Access Status — Sep 2026

Verified access status for sources used in Hermes research sweeps.
Authority document: supersedes individual sweep notes about source blockage.

## Confirmed Working (REST API, no auth)

| Source | Endpoint | Notes |
|--------|----------|-------|
| HAL (French/EU) | api.archives-ouvertes.fr/search/?q=QUERY&rows=N&wt=json | REST API confirmed working Sep 2026. The web UI at hal.science is Anubis PoW bot-blocked; the API is not. sweep script already uses API correctly. Returns non-arXiv OA papers. |
| AMiner (Chinese) | api.aminer.org/api/search/pub?query=QUERY | Free, no key. Best for Chinese institutional AI output. 48h+ lag on very recent papers. |
| OpenAlex | api.openalex.org/works?search=QUERY&filter=publication_year:2025|2026 | Free, open, citation-ranked. Pass mailto= param for better rate limits. |
| Crossref | api.crossref.org/works?query=QUERY&mailto=research@hermes.local | High quality DOI-backed results. Add cs filter in query to suppress noise. |
| Semantic Scholar | api.semanticscholar.org/graph/v1/paper/search | Unauthenticated: 1 req/sec. Free API key available at semanticscholar.org/product/api for higher limits. |
| CyberLeninka | cyberleninka.ru/api/1/search?q=QUERY | Russian/Eastern European OA. Returns survey/review articles mostly. Low signal-to-noise for agent/LLM topics. |
| arXiv search HTML | arxiv.org/search/?searchtype=all&query=QUERY&order=-submitted_date | Most reliable. Use order=-submitted_date (not -announced_date_first) for delta sweeps past a known ID threshold. |
| arXiv listing | arxiv.org/list/cs.AI/recent | Highest yield for very recent papers before search engines index them. |

## NOT Yet in Sweep Script (gap)

| Source | Endpoint | Value |
|--------|----------|-------|
| OpenAIRE | api.openaire.eu/search/publications?keywords=QUERY&format=json | Covers EU-funded + Dutch/French/German content. Free, no auth. Would supplement HAL for non-French EU papers. Low priority addition. |

## Confirmed Blocked / Inaccessible

| Source | Block type | Workaround |
|--------|------------|------------|
| HAL web UI (hal.science/search) | Anubis proof-of-work JS challenge | Use REST API instead (confirmed working) |
| CNKI / Wanfang | Institutional paywall, no bypass | Search arXiv with Chinese institution names (Tsinghua/PKU/Fudan/USTC). AMiner covers some. |
| CCKS / NLPCC proceedings | Springer paywall, no preprints found | No reliable workaround for conference-only papers. |
| DBpia (Korean KIISE) | Subscription required | Abstract/metadata only. Search arXiv with KAIST/POSTECH/SNU affiliation. |
| IPSJ main proceedings (Japan) | 2-year OA embargo | Use J-STAGE for IPSJ SIG Technical Reports (embargo-free). |
| J-STAGE (from execute_code) | "private/internal network" block | Use via terminal/curl or browser. J-STAGE API at api.jstage.jst.go.jp/articles/_search works via urllib in sweep script. |
| Reddit r/LocalLLaMA, r/MachineLearning | Anti-bot 403/redirect | web_search snippets only. For specific high-value threads, use browser_navigate directly to the thread URL. |
| Zhihu, Juejin, V2EX | Login-walled or bot-blocked | No reliable programmatic access. Monitor via web_search keyword hits. |
| scite.ai | Paywalled | No free tier for dissenting citation search. Gap: can't find papers that CONTRADICT our referenced papers. |

## Unresolvable Research Gaps (Hermes-relevant, Sep 2026)

These were identified but the underlying paper/source could not be read:

### GN-IVO (KAIST AI Lab)
- Topic: Model-based planning via imagination + value optimization. Faster adaptation
  without retraining. Tier B relevance for Hermes planning/reflection.
- Problem: No arXiv ID confirmed. Found via KAIST institutional sweep. May exist only
  as a conference paper or internal preprint.
- Action: Search arXiv periodically for "GN-IVO" or "KAIST imagination planning".

### Zhihu claim: 37% OOD failure rate in active-forgetting memory systems
- Topic: OOD robustness failure mode specific to active-forgetting architectures.
  Directly relevant to Hermes l1-promote.py dedup/forgetting logic.
- Problem: Surfaced on Zhihu (login-walled) with no arXiv source. Could be practitioner
  folklore or unpublished internal finding. Explicitly flagged as unverifiable.
- Action: If a paper with this claim surfaces on arXiv, triage immediately as HIGH.
  In the meantime, treat the 37% figure as unverified but plausible risk signal.

## Historical Note on HAL

Early sweep notes (Aug 2026, agent-runtime-aug2026-sweep2.md) state "HAL Anubis-blocked".
This referred to the HAL *web search UI*, not the HAL REST API. The sweep script
has always used the REST API endpoint and was never actually blocked. The historical
notes are technically accurate for the web UI but were misread as a total HAL blockage.
This file is the authoritative reference — trust it over individual sweep notes.
