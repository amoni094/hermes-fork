---
name: arxiv
related_skills:
  - pdf
  - academic-literature-review
  - grounded-citations
  - arxiv-sweep-findings
  - domain-research-synthesis

provides: [web_search, web_extract]
description: >
  Use when searching arXiv papers by keyword, author, category, or ID. Not for querying Hermes sweep findings banks (use arxiv-sweep-findings / hermes-*-sweep-findings).
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Research, Arxiv, Papers, Academic, Science, API]
    related_skills: [pdf, academic-literature-review, grounded-citations, arxiv-sweep-findings, domain-research-synthesis]
triggers:
  - User asks to find, search, or fetch academic papers on arXiv
  - Task involves discovering papers by keyword, author, category (cs.AI, cs.CL, etc.), or arXiv ID
  - User says "find papers on", "latest arXiv on", "search arxiv for", or provides an arXiv ID
  - Systematic literature sweep over a date range or category
  - NOT general web research — specifically arXiv paper retrieval
  - NOT for the recurring Hermes agent research sweep (use hermes-research skill)
---

# arXiv Research

Search and retrieve academic papers from arXiv via their free REST API. No API key, no dependencies.

## KNOWN ISSUES (2026-08): keyword search is effectively broken

1. `export.arxiv.org/api/query?search_query=...` hangs indefinitely (IP-level CDN block).
2. The helper script `search_arxiv.py` falls back to Firecrawl, but returns **date-sorted results
   for today's submissions** — not topic-matched results for your query. Output looks plausible but
   is irrelevant noise.
3. `ai_research_search.py` has the same arXiv fallback problem. Semantic Scholar (S2) is
   frequently 429-rate-limited without an API key. OpenAlex keyword search returns citation-count-
   sorted results that are broad surveys, not the specific papers you want.

**What actually works:**
- `id_list=` fetching when you already have arXiv IDs (reliable, fast)
- `web_extract(urls=["https://arxiv.org/abs/ID"])` for abstract + metadata
- OpenAlex by exact title fragment or DOI
- HAL API for European/French sources (works reliably)
- Papers With Code API (currently returning empty — may be rate-limited)

**For keyword discovery, use these instead of the broken scripts:**
- web_search("site:arxiv.org TOPIC 2026") — Google-indexed, topic-matched
- web_extract(["https://arxiv.org/search/?query=TOPIC&searchtype=all&start=0"]) — HTML search UI
- Semantic Scholar with 5s delay between requests (1 req/sec unauthenticated)
- OpenAlex with exact title search: `?search=EXACT+TITLE+FRAGMENT`

Do NOT use raw curl with `search_query=` — it will time out. Use `id_list=` directly when you have IDs.

## Quick Reference

| Action | Command |
|--------|---------|
| **Unified search (arXiv + S2 + OpenAlex)** | `python3 ~/.hermes/skills/research/arxiv/scripts/ai_research_search.py "QUERY"` |
| **HAL (French/EU)** | `curl -s "https://api.archives-ouvertes.fr/search/?q=QUERY&rows=10&fl=title_s,authFullName_s,uri_s&wt=json"` |
| **OpenAIRE (EU-funded)** | `curl -s "https://api.openaire.eu/search/publications?keywords=QUERY&format=json&size=5"` |
| **DOAJ (multilingual OA journals)** | `curl -s "https://doaj.org/api/search/articles/QUERY"` |
| **Crossref (DOI metadata + references)** | `curl -s "https://api.crossref.org/works?query=QUERY&rows=5&mailto=you@email.com"` |
| **Crossref by DOI** | `curl -s "https://api.crossref.org/works/10.1145/XXXXX"` |
| **PubMed search** | `curl -s "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=QUERY&retmax=10&retmode=json"` |
| **PMC full text** | `curl -s "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pmc&id=PMCID&rettype=full&retmode=xml"` |
| **OpenCitations (citation graph)** | `curl -s "https://opencitations.net/index/coci/api/v1/citations/DOI"` |
| **AMiner (Chinese AI/CS graph)** | `curl -s "https://api.aminer.org/api/search/pub?query=QUERY&size=5"` |
| Search arXiv only | `python3 ~/.hermes/skills/research/arxiv/scripts/search_arxiv.py "QUERY"` |
| Get specific paper | `curl -s "https://export.arxiv.org/api/query?id_list=2402.03300"` |
| Read abstract (web) | `web_extract(urls=["https://arxiv.org/abs/2402.03300"])` |
| Read full paper (PDF) | `web_extract(urls=["https://arxiv.org/pdf/2402.03300"])` |

## Unified Multi-Source Search

`ai_research_search.py` queries arXiv, Semantic Scholar, and OpenAlex in one call.
No API keys required. stdlib-only (no pip installs).

```bash
# Basic search — all three sources, 5 results each
python3 ~/.hermes/skills/research/arxiv/scripts/ai_research_search.py "LLM agents"

# Narrow by year, increase result count
python3 ~/.hermes/skills/research/arxiv/scripts/ai_research_search.py "RLHF reward model" --max 10 --year 2024

# Skip slow or rate-limited sources
python3 ~/.hermes/skills/research/arxiv/scripts/ai_research_search.py "attention mechanism" --no-arxiv
python3 ~/.hermes/skills/research/arxiv/scripts/ai_research_search.py "attention mechanism" --no-s2
```

Flags: `--max N` (results per source), `--year YYYY` (filter), `--no-arxiv`, `--no-s2`, `--no-openalex`

Source behaviour:
- arXiv: sorted by submission date (newest first); may time out on search_query endpoint (known CDN block — use search_arxiv.py with its Firecrawl fallback in that case)
- Semantic Scholar: relevance-ranked; free tier is 1 req/sec (HTTP 429 = rate limited, retry after a few seconds or get a free API key at semanticscholar.org/product/api)
- OpenAlex: open-access only, sorted by citation count; add `mailto=you@email.com` to URLs for the polite pool (10 req/sec)

## Searching Papers

The API returns Atom XML. Parse with `grep`/`sed` or pipe through `python3` for clean output.

### Basic search

```bash
curl -s "https://export.arxiv.org/api/query?search_query=all:GRPO+reinforcement+learning&max_results=5"
```

### Clean output (parse XML to readable format)

```bash
curl -s "https://export.arxiv.org/api/query?search_query=all:GRPO+reinforcement+learning&max_results=5&sortBy=submittedDate&sortOrder=descending" | python3 -c "
import sys, xml.etree.ElementTree as ET
ns = {'a': 'http://www.w3.org/2005/Atom'}
root = ET.parse(sys.stdin).getroot()
for i, entry in enumerate(root.findall('a:entry', ns)):
    title = entry.find('a:title', ns).text.strip().replace('\n', ' ')
    arxiv_id = entry.find('a:id', ns).text.strip().split('/abs/')[-1]
    published = entry.find('a:published', ns).text[:10]
    authors = ', '.join(a.find('a:name', ns).text for a in entry.findall('a:author', ns))
    summary = entry.find('a:summary', ns).text.strip()[:200]
    cats = ', '.join(c.get('term') for c in entry.findall('a:category', ns))
    print(f'{i+1}. [{arxiv_id}] {title}')
    print(f'   Authors: {authors}')
    print(f'   Published: {published} | Categories: {cats}')
    print(f'   Abstract: {summary}...')
    print(f'   PDF: https://arxiv.org/pdf/{arxiv_id}')
    print()
"
```

## Search Query Syntax

| Prefix | Searches | Example |
|--------|----------|---------|
| `all:` | All fields | `all:transformer+attention` |
| `ti:` | Title | `ti:large+language+models` |
| `au:` | Author | `au:vaswani` |
| `abs:` | Abstract | `abs:reinforcement+learning` |
| `cat:` | Category | `cat:cs.AI` |
| `co:` | Comment | `co:accepted+NeurIPS` |

### Boolean operators

```
# AND (default when using +)
search_query=all:transformer+attention

# OR
search_query=all:GPT+OR+all:BERT

# AND NOT
search_query=all:language+model+ANDNOT+all:vision

# Exact phrase
search_query=ti:"chain+of+thought"

# Combined
search_query=au:hinton+AND+cat:cs.LG
```

## Sort and Pagination

| Parameter | Options |
|-----------|---------|
| `sortBy` | `relevance`, `lastUpdatedDate`, `submittedDate` |
| `sortOrder` | `ascending`, `descending` |
| `start` | Result offset (0-based) |
| `max_results` | Number of results (default 10, max 30000) |

```bash
# Latest 10 papers in cs.AI
curl -s "https://export.arxiv.org/api/query?search_query=cat:cs.AI&sortBy=submittedDate&sortOrder=descending&max_results=10"
```

## Fetching Specific Papers

```bash
# By arXiv ID
curl -s "https://export.arxiv.org/api/query?id_list=2402.03300"

# Multiple papers
curl -s "https://export.arxiv.org/api/query?id_list=2402.03300,2401.12345,2403.00001"
```

## BibTeX Generation

After fetching metadata for a paper, generate a BibTeX entry:

{% raw %}
```bash
curl -s "https://export.arxiv.org/api/query?id_list=1706.03762" | python3 -c "
import sys, xml.etree.ElementTree as ET
ns = {'a': 'http://www.w3.org/2005/Atom', 'arxiv': 'http://arxiv.org/schemas/atom'}
root = ET.parse(sys.stdin).getroot()
entry = root.find('a:entry', ns)
if entry is None: sys.exit('Paper not found')
title = entry.find('a:title', ns).text.strip().replace('\n', ' ')
authors = ' and '.join(a.find('a:name', ns).text for a in entry.findall('a:author', ns))
year = entry.find('a:published', ns).text[:4]
raw_id = entry.find('a:id', ns).text.strip().split('/abs/')[-1]
cat = entry.find('arxiv:primary_category', ns)
primary = cat.get('term') if cat is not None else 'cs.LG'
last_name = entry.find('a:author', ns).find('a:name', ns).text.split()[-1]
print(f'@article{{{last_name}{year}_{raw_id.replace(\".\", \"\")},')
print(f'  title     = {{{title}}},')
print(f'  author    = {{{authors}}},')
print(f'  year      = {{{year}}},')
print(f'  eprint    = {{{raw_id}}},')
print(f'  archivePrefix = {{arXiv}},')
print(f'  primaryClass  = {{{primary}}},')
print(f'  url       = {{https://arxiv.org/abs/{raw_id}}}')
print('}')
"
```
{% endraw %}

## Reading Paper Content

After finding a paper, read it:

```
# Abstract page (fast, metadata + abstract)
web_extract(urls=["https://arxiv.org/abs/2402.03300"])

# Full paper (PDF → markdown via Firecrawl)
web_extract(urls=["https://arxiv.org/pdf/2402.03300"])
```

For local PDF processing (scanned pages), use pytesseract/easyocr directly or `vision_analyze` on exported page images (`ocr-and-documents` skill is disabled). For text-layer PDFs, use the `pdf` skill.

## Key Open-Access AI Journals (no subscription required)

| Journal | URL | Notes |
|---------|-----|-------|
| JAIR | jair.org | Peer-reviewed, open access since 1993. AAAI-backed. |
| JMLR | jmlr.org | Journal of Machine Learning Research. Fully open, no APC. Top-tier. |
| Stanford HAI | hai.stanford.edu/research/publications | Human-centered AI. Annual AI Index Report (governance, policy, applied research). High signal for AI policy + societal impact context. Publications indexed in S2/OpenAlex. |
| AI Open | aiopen.elsevier.com | Elsevier open access, Chinese Academy focus. |
| Foundations & Trends in ML | nowpublishers.com/mal | Survey articles, some OA. |
| arXiv cs.AI/cs.LG/cs.CL | arxiv.org | Preprints — not peer-reviewed but the fastest signal. |

All are indexed in Semantic Scholar and OpenAlex. For paywalled venues (Nature MI, IEEE TPAMI, etc.), use OpenAlex `open_access.oa_url` field to find legal OA versions before hitting a paywall.

## Multilingual & Regional Sources

### Tier 1: Free API, no key required

| Source | Region | URL | API Endpoint | Notes |
|--------|--------|-----|--------------|-------|
| HAL | France/Europe | hal.science | `https://api.archives-ouvertes.fr/search/?q={query}&rows=10&wt=json` | Solr-based, returns JSON/BibTeX/CSV. 38K+ ML papers confirmed. French CS/AI community heavy user. Includes TEL thesis sub-archive. |
| OpenAIRE | Europe/Global | openaire.eu | `https://api.openaire.eu/search/publications?keywords={query}&format=json` | EU-funded research aggregator. 1M+ ML papers confirmed. Unique: EU funding metadata, provenance tracking. Covers content from DART-Europe (now defunct), NARCIS, institutional repos. |
| DOAJ | Multilingual | doaj.org | `https://doaj.org/api/` (v4, Elasticsearch syntax) | 20,000+ OA journals in 80+ languages, 10M+ articles. No key for searches (key only for publisher writes). Rate limit: 2 req/sec. Best for: discovering OA AI journals in non-English regions. |

### Tier 2: Open access, OAI-PMH, niche regional coverage

| Source | Region | URL | Access | Notes |
|--------|--------|-----|--------|-------|
| Shodhganga | India | shodhganga.inflibnet.ac.in | OAI-PMH at `/oai/request`; full PDFs free, no login | 692K+ Indian PhD theses, CC BY-NC 4.0. DSpace-based. Unique: Indian CS/AI academic contributions absent from Western DBs. |
| RISS International | Korea | intl.riss.kr | No API; metadata free without login; full text with free registration | 21.4M records (7.5M articles, 2.6M theses). English search UI. 1.6M full-text Korean theses. Manual search source only (no pipeline API). |
| CyberLeninka | Russia | cyberleninka.ru | Web search free; no formal API | Russian OA journals. Partially accessible. Best for Russian-language AI commentary. |

### Tier 3: Paywalled or subscription — document for awareness only

| Source | Region | Status | Notes |
|--------|--------|--------|-------|
| CNKI | China | MCP crawler needed | Largest Chinese DB; requires crawler or institutional access |
| Wanfang Data | China | Subscription | 50M+ Chinese articles; EBSCO-integrated; no public API |
| DBpia | Korea | Subscription | 5.2M Korean papers, no API |
| Dar Almandumah | Arabic | Subscription | Primary Arabic academic DB; theses + journals from Arab world universities |
| Al Manhal | MENA/Asia | Subscription | Arabic + English; unique MENA/Africa/Asia content |
| Dimensions | Global | Web free / API subscription | 130M+ publications; DSL API requires institutional license; OpenAlex is the free proxy |

### Dead or bot-blocked — do not use
- DART-Europe: permanently shut down Feb 2025
- NARCIS: Anubis bot-blocked (use OpenAIRE to cover Dutch/EU content instead)
- KISS: subscription-only, no API

## Common Categories

| Category | Field |
|----------|-------|
| `cs.AI` | Artificial Intelligence |
| `cs.CL` | Computation and Language (NLP) |
| `cs.CV` | Computer Vision |
| `cs.LG` | Machine Learning |
| `cs.CR` | Cryptography and Security |
| `stat.ML` | Machine Learning (Statistics) |
| `math.OC` | Optimization and Control |
| `physics.comp-ph` | Computational Physics |

Full list: https://arxiv.org/category_taxonomy

## Helper Script

The `scripts/search_arxiv.py` script handles XML parsing and provides clean output:

```bash
python scripts/search_arxiv.py "GRPO reinforcement learning"
python scripts/search_arxiv.py "transformer attention" --max 10 --sort date
python scripts/search_arxiv.py --author "Yann LeCun" --max 5
python scripts/search_arxiv.py --category cs.AI --sort date
python scripts/search_arxiv.py --id 2402.03300
python scripts/search_arxiv.py --id 2402.03300,2401.12345
```

No dependencies — uses only Python stdlib.

---

## Crossref (DOI Metadata + Reference Lists)

Crossref holds metadata for ~180M research outputs with DOIs. Free, no key needed (add mailto= for polite pool). Best for: resolving DOIs, getting reference lists from published papers, publisher/venue metadata.

```bash
# Search by keyword
curl -s "https://api.crossref.org/works?query=large+language+models&rows=5&mailto=you@email.com" | python3 -m json.tool

# Fetch specific paper by DOI
curl -s "https://api.crossref.org/works/10.1145/3442381.3450048" | python3 -m json.tool

# Get references FROM a paper (I4OC open citations)
curl -s "https://api.crossref.org/works/10.1145/3442381.3450048" | python3 -c "import sys,json; d=json.load(sys.stdin)['message']; [print(r.get('DOI',''),r.get('article-title','')) for r in d.get('reference',[])]"
```

Useful fields: `title`, `author`, `published`, `DOI`, `URL`, `is-referenced-by-count`, `reference` (list of what the paper cites), `container-title` (journal/conference).

---

## OpenCitations (Open Citation Graph)

Free, no key. 1B+ citation links from open publisher data. Complements S2/OpenAlex for citation traversal.

```bash
# Papers citing a DOI
curl -s "https://opencitations.net/index/coci/api/v1/citations/10.1145/3442381.3450048"

# Papers cited by a DOI
curl -s "https://opencitations.net/index/coci/api/v1/references/10.1145/3442381.3450048"
```

---

## PubMed / PMC (Biomedical + AI in Medicine)

Free E-utilities API, no key needed (key raises rate limit). 36.6M biomedical citations. Relevant for: AI in healthcare, medical NLP, clinical AI papers.

```bash
# Search PubMed
curl -s "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=large+language+model+clinical&retmax=10&retmode=json" | python3 -m json.tool

# Fetch abstract by PMID
curl -s "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=37979023&rettype=abstract&retmode=text"

# Get full text (PMC open access only)
curl -s "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pmc&id=PMC10579063&rettype=full&retmode=xml"
```

---

## AMiner (Chinese AI/CS Academic Graph)

Built by Tsinghua University. Free API. ~300M papers with expertise graphs, author profiling, institution rankings. Best for: finding Chinese institutional AI output, author expertise maps, AI-in-China landscape.

```bash
# Search papers
curl -s "https://api.aminer.org/api/search/pub?query=reinforcement+learning+agents&size=5" | python3 -m json.tool

# Author search
curl -s "https://api.aminer.org/api/search/person?query=Andrew+Ng&size=3" | python3 -m json.tool
```

---

## Domain-Specific Preprint Servers

Beyond arXiv — useful when the research crosses into adjacent fields:

| Server | Domain | URL | API |
|--------|--------|-----|-----|
| bioRxiv | Biology, bioinformatics, computational biology | biorxiv.org | Yes — `api.biorxiv.org/details/biorxiv/QUERY` |
| medRxiv | Clinical medicine, health AI, epidemiology | medrxiv.org | Same API as bioRxiv |
| SSRN | Economics, law, AI policy/governance, social science | ssrn.com | No API; browse free |
| OSF Preprints | Psychology, social/behavioral AI, HCI, education | osf.io/preprints | Yes — OSF API v2 |

```bash
# bioRxiv/medRxiv API (same endpoint, change server param)
curl -s "https://api.biorxiv.org/details/biorxiv/AI+health/0/5/json" | python3 -m json.tool
curl -s "https://api.biorxiv.org/details/medrxiv/large+language+model/0/5/json" | python3 -m json.tool
```

---

## OpenAlex (Preferred for Open-Access Bulk Queries)

OpenAlex is increasingly preferred over Semantic Scholar for open-access programmatic research. 250M+ works, fully open, no rate limit with a free API key, full DOI/ORCID/institution graph.

```bash
# Search papers (JSON, no key needed for basic use)
curl -s "https://api.openalex.org/works?search=QUERY&filter=open_access.is_oa:true&per-page=10" | python3 -m json.tool

# Fetch by DOI
curl -s "https://api.openalex.org/works/https://doi.org/10.1145/3442381.3450048" | python3 -m json.tool

# By arXiv ID
curl -s "https://api.openalex.org/works/https://arxiv.org/abs/2402.03300" | python3 -m json.tool

# Author lookup with institution affiliation
curl -s "https://api.openalex.org/authors?search=Yann+LeCun&select=display_name,cited_by_count,works_count,last_known_institutions" | python3 -m json.tool

# Citation chain: papers citing a work
curl -s "https://api.openalex.org/works?filter=cites:W2741809807&per-page=10&select=title,publication_year,cited_by_count" | python3 -m json.tool
```

### OpenAlex useful fields
`title`, `authorships`, `publication_year`, `cited_by_count`, `open_access.oa_url`,
`concepts` (topic tags), `referenced_works`, `related_works`, `biblio.volume`,
`primary_location.source.display_name` (journal/conference name)

### When to use OpenAlex vs Semantic Scholar
| Need | Use |
|------|-----|
| Open-access PDF links | OpenAlex (better OA coverage) |
| TLDR/abstract summary | Semantic Scholar |
| Citation graph bulk download | OpenAlex (free JSONL snapshots) |
| Influential citations | Semantic Scholar |
| Institution-level analytics | OpenAlex |
| Paper recommendations | Semantic Scholar |

---

## arXiv Sidecars (Attached to Every arxiv.org Abstract Page)

Before doing a full literature pass, check these tools — they add significant value with zero extra effort:

| Sidecar | What it adds |
|---------|-------------|
| **Connected Papers** (connectedpapers.com) | Visual citation/influence graph — find adjacent work you wouldn't have searched for |
| **CatalyzeX** (catalyzex.com) | Auto-links code implementations to papers — faster than Papers With Code |
| **Litmaps** (litmaps.co) | Temporal citation map — shows how a research thread evolved |
| **scite.ai** | Smart citations: marks each citation as Supporting / Contrasting / Mentioning — critical for adversarial review |
| **alphaXiv** (alphaxiv.org) | Community discussion layer on arXiv papers |
| **Semantic Scholar** link | One-click to full citation graph from any arXiv page |

All are accessible as sidebar toggles at the bottom of any arxiv.org/abs/ page.

---

## Papers With Code (Code + Benchmarks Bridge)

```bash
# Search papers with linked code
curl -s "https://paperswithcode.com/api/v1/papers/?q=QUERY" | python3 -m json.tool

# Get methods for a task
curl -s "https://paperswithcode.com/api/v1/tasks/?q=object+detection" | python3 -m json.tool

# Find repos for a paper by arXiv ID
curl -s "https://paperswithcode.com/api/v1/papers/arxiv:2402.03300/repositories/" | python3 -m json.tool
```

Use PaperFlow (papersflow.ai) as an alternative: enter an arXiv ID and it auto-extracts all GitHub repos mentioned in the paper.

---

## Multilingual Academic Sources

| Source | Language | Access | Notes |
|--------|----------|--------|-------|
| CNKI (oversea.cnki.net) | Chinese | Partial free / MCP crawler | Largest Chinese academic DB; MCP: mcpmarket.com/server/cnki-crawler |
| CiNii Research (cir.nii.ac.jp) | Japanese | Free | National academic bibliography |
| J-STAGE (jstage.jst.go.jp) | Japanese | Open access | Scientific journals |
| Cyberleninka (cyberleninka.ru) | Russian | Open access | Russian academic corpus |
| Redalyc (redalyc.org) | Spanish/Portuguese | Open access | Latin American/Iberian journals |
| SciELO (scielo.org) | Multi | Open access | Developing countries open science |
| BASE (base-search.net) | Multi | Free API | 300M+ documents, Bielefeld |
| CORE (core.ac.uk) | Multi | Free API | 230M+ open access papers |

### Cross-lingual search strategy (validated in literature)
Best approach from "Better to Ask in English" (ACM 2024) and XRAG (arXiv:2505.10089):
1. Formulate query in English first
2. Retrieve from English-language databases
3. For non-English corpora, translate the query to the target language and search natively
4. Synthesize across languages in English

```bash
# BASE API — multilingual open access
curl -s "https://api.base-search.net/cgi-bin/BaseHttpSearchInterface.fcgi?func=PerformSearch&query=QUERY&hits=20&format=json"

# CORE API — open access aggregator
curl -s "https://api.core.ac.uk/v3/search/works?q=QUERY" -H "Authorization: Bearer YOUR_API_KEY"
```

---

## Semantic Scholar (Citations, Related Papers, Author Profiles)

arXiv doesn't provide citation data or recommendations. Use the **Semantic Scholar API** for that — free, no key needed for basic use (1 req/sec), returns JSON.

### Get paper details + citations

```bash
# By arXiv ID
curl -s "https://api.semanticscholar.org/graph/v1/paper/arXiv:2402.03300?fields=title,authors,citationCount,referenceCount,influentialCitationCount,year,abstract" | python3 -m json.tool

# By Semantic Scholar paper ID or DOI
curl -s "https://api.semanticscholar.org/graph/v1/paper/DOI:10.1234/example?fields=title,citationCount"
```

### Get citations OF a paper (who cited it)

```bash
curl -s "https://api.semanticscholar.org/graph/v1/paper/arXiv:2402.03300/citations?fields=title,authors,year,citationCount&limit=10" | python3 -m json.tool
```

### Get references FROM a paper (what it cites)

```bash
curl -s "https://api.semanticscholar.org/graph/v1/paper/arXiv:2402.03300/references?fields=title,authors,year,citationCount&limit=10" | python3 -m json.tool
```

### Search papers (alternative to arXiv search, returns JSON)

```bash
curl -s "https://api.semanticscholar.org/graph/v1/paper/search?query=GRPO+reinforcement+learning&limit=5&fields=title,authors,year,citationCount,externalIds" | python3 -m json.tool
```

### Get paper recommendations

```bash
curl -s -X POST "https://api.semanticscholar.org/recommendations/v1/papers/" \
  -H "Content-Type: application/json" \
  -d '{"positivePaperIds": ["arXiv:2402.03300"], "negativePaperIds": []}' | python3 -m json.tool
```

### Author profile

```bash
curl -s "https://api.semanticscholar.org/graph/v1/author/search?query=Yann+LeCun&fields=name,hIndex,citationCount,paperCount" | python3 -m json.tool
```

### Useful Semantic Scholar fields

`title`, `authors`, `year`, `abstract`, `citationCount`, `referenceCount`, `influentialCitationCount`, `isOpenAccess`, `openAccessPdf`, `fieldsOfStudy`, `publicationVenue`, `externalIds` (contains arXiv ID, DOI, etc.)

---

## Complete Research Workflow

0. **Unified discovery (start here)**: `python3 ~/.hermes/skills/research/arxiv/scripts/ai_research_search.py "your topic" --max 5`
   Hits arXiv + Semantic Scholar + OpenAlex in one shot. Then drill into specific papers below.
1. **arXiv only (date-sorted, with Firecrawl fallback)**: `python3 ~/.hermes/skills/research/arxiv/scripts/search_arxiv.py "your topic" --sort date --max 10`
2. **OpenAlex direct**: `curl -s "https://api.openalex.org/works?search=QUERY&per-page=10"`
3. **Assess impact**: `curl -s "https://api.semanticscholar.org/graph/v1/paper/arXiv:ID?fields=citationCount,influentialCitationCount,tldr"`
4. **Check sidecars**: Open arxiv.org/abs/ID, toggle Connected Papers + scite.ai in sidebar
5. **Read abstract**: `web_extract(urls=["https://arxiv.org/abs/ID"])`
6. **Read full paper**: `web_extract(urls=["https://arxiv.org/pdf/ID"])` or HTML: `web_extract(urls=["https://arxiv.org/html/ID"])`
7. **Find code**: `curl -s "https://paperswithcode.com/api/v1/papers/arxiv:ID/repositories/"`
8. **Find related work**: `curl -s "https://api.semanticscholar.org/graph/v1/paper/arXiv:ID/references?fields=title,citationCount&limit=20"`
9. **Get recommendations**: POST to Semantic Scholar recommendations endpoint
10. **Track authors**: `curl -s "https://api.semanticscholar.org/graph/v1/author/search?query=NAME"`
11. **Non-English angle**: Check CNKI/CiNii/SciELO for the same topic in target language
12. **Adversarial check**: Use scite.ai to find contrasting citations before finalising synthesis

### Agentic Academic Search Tools (2025-2026)
For complex multi-hop queries across many papers, consider these purpose-built tools:
- **Asta Find Papers** (asta.allen.ai): Built by AI2 (Allen Institute — same org as Semantic Scholar). Free, unlimited, no login required. 108M abstracts + 12M full texts. Returns results with Perfectly Relevant / Relevant / Somewhat Relevant scores plus evidence passages. Can also generate structured multi-section reports with inline citations. Best for: relevance-scored discovery with evidence grounding. Agentic: can be told to "work harder" for a deeper pass.
- **PaSa** (pasa-agent.ai / github.com/bytedance/pasa): RL-trained paper search agent. Outperforms Google+GPT-4o by 37-39% recall. Best for: comprehensive retrieval on a focused research question.
- **OpenScholar**: RAG-LM grounded on scientific corpora. Best for: citation-grounded synthesis.
- **STORM** (storm.genie.stanford.edu): Synthesis pipeline for holistic topic overviews.
- **Consensus** (consensus.app): Scientific agreement scoring across peer-reviewed literature.
- **Undermind** (undermind.ai): Agentic deep-semantic search with citation trailing. Guides you through question refinement before searching. 5 free searches/month, S2-backed. Best for: thorough single-question deep dives.
- **The-literature.com**: Free, no login, PubMed-only. Generates a narrative synthesis with references. Zero friction for clinical/biomedical AI questions.
- **scite.ai**: Smart citations — find supporting vs contrasting evidence for any claim.

### Vetting a new AI search tool
Use the U of Toronto checklist (zenodo.org/records/15319378) to evaluate any new tool. Key questions: what dataset does it search? Is retrieval deterministic (keyword/Boolean) or probabilistic (semantic)? Are citations faithful to the primary source or hallucinated? What's visible vs paywalled in the free tier?

## Rate Limits

| API | Rate | Auth |
|-----|------|------|
| arXiv | ~1 req / 3 seconds | None needed |
| Semantic Scholar | 1 req / second | None (100/sec with API key — semanticscholar.org/product/api) |
| OpenAlex | 10 req / second | None (higher with polite pool: add `mailto=you@email.com` to URL) |
| Papers With Code | ~1 req / second | None |
| CORE | 10 req / second | Free API key at core.ac.uk/api-keys |
| BASE | ~1 req / second | None |

## Notes

- arXiv returns Atom XML — use the helper script or parsing snippet for clean output
- Semantic Scholar returns JSON — pipe through `python3 -m json.tool` for readability
- arXiv IDs: old format (`hep-th/0601001`) vs new (`2402.03300`)
- PDF: `https://arxiv.org/pdf/{id}` — Abstract: `https://arxiv.org/abs/{id}`
- HTML (when available): `https://arxiv.org/html/{id}`
- For local PDF processing, see the `pdf` skill (text-layer); for scanned pages use pytesseract/`vision_analyze` (`ocr-and-documents` is disabled)

## ID Versioning

- `arxiv.org/abs/1706.03762` always resolves to the **latest** version
- `arxiv.org/abs/1706.03762v1` points to a **specific** immutable version
- When generating citations, preserve the version suffix you actually read to prevent citation drift (a later version may substantially change content)
- The API `<id>` field returns the versioned URL (e.g., `http://arxiv.org/abs/1706.03762v7`)

## Withdrawn Papers

Papers can be withdrawn after submission. When this happens:
- The `<summary>` field contains a withdrawal notice (look for "withdrawn" or "retracted")
- Metadata fields may be incomplete
- Always check the summary before treating a result as a valid paper

## Pitfalls

- **export.arxiv.org search_query hangs** — CDN IP-block on keyword search. Use `id_list=` when you have IDs, or fall back to `web_extract(["https://arxiv.org/search/?query=..."])` for keyword discovery.
- **search_arxiv.py Firecrawl fallback returns date-sorted noise** — the Firecrawl fallback returns today's submissions, not topic-matched results. Output looks plausible but is irrelevant. Use `ai_research_search.py` or OpenAlex instead.
- **Semantic Scholar 429 rate-limit** — free tier is 1 req/sec. Add 5s delay between calls or register for a free API key at semanticscholar.org/product/api.
- **DART-Europe is permanently shut down** (Feb 2025). NARCIS is Anubis bot-blocked. Use OpenAIRE for Dutch/EU coverage instead.
- **arXiv ID versioning** — `arxiv.org/abs/1706.03762` resolves to the latest version; `…v1` is immutable. Preserve the version suffix you actually read to prevent citation drift.
- **Retracted/withdrawn papers** — the `<summary>` field contains a withdrawal notice. Always check before treating a result as a valid source.
- **Papers With Code API** — currently returning empty results (may be rate-limited); do not rely on it as a primary discovery source.
- **GDELT Doc API v2** — returns HTTP 200 with empty body silently when rate-limited (1 req/5s). Cannot distinguish from "no results". Do not use; prefer geopolitics RSS instead.

## Research Pipeline Handoff

When a sweep produces findings for the skill corpus:
1. `arxiv` (search + collect papers) → `domain-research-synthesis` (multi-source synthesis)
2. `domain-research-synthesis` → `arxiv-sweep-findings` (structured findings + skill patches)
3. `arxiv-sweep-findings` → `self-improve-agent` or direct `skill_manage(action='patch')` per finding
4. Curator-managed skills require `hermes curator adopt <skill>` before patches can apply.

See `academic-literature-review` for the full end-to-end pipeline with fallback chain.
