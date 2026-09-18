# Research Master Synthesis — AI Agent Research Skills
**Consolidated:** August 2026  
**Sources:** research-skill-improvements-2025-2026.md · github-research-mining-2026.md · arxiv/SKILL.md  
**Adversarial pass applied inline.**

---

## (A) Agentic Search Tools

### Purpose-Built Paper Search Agents

| Tool | Origin | Claim | Adversarial Caveat |
|------|--------|-------|--------------------|
| **PaSa** | ByteDance, ACL 2025 | +37.78% recall@20, +39.90% recall@50 vs Google+GPT-4o. RL-trained crawler+selector loop (ReAct). | ⚠️ Evaluated only on ByteDance's own RealScholarQuery benchmark — high risk of overfitting/benchmark gaming. No third-party replication published as of Aug 2026. |
| **OpenScholar** | AI2, Nature 2025 | RAG-LM grounded on scientific corpora; verifiable citations. Best for synthesis tasks. | ⚠️ Corpus is primarily English open-access; coverage of paywalled venues (Elsevier, Wiley, ACM behind paywall) is limited by construction. |
| **SPAR** | Semantic Scholar 2025 | LLM agent over S2AG (200M+ papers, largest open scientific graph). | ⚠️ Semantic Scholar has 1–7 day indexing lag and has lower coverage of humanities and social sciences. |
| **STORM** | Stanford-oval | Wikipedia-style synthesis from web search; storm.genie.stanford.edu | ⚠️ Excellent for high-level overviews; systematically underweights edge cases, negative results, and minority viewpoints. Not suitable as sole synthesis tool for adversarial review. |
| **GPT-Researcher** | assafelovic OSS | Modular OSS deep research agent with pluggable backends. | ⚠️ Quality of results is highly dependent on backend search engine; not reproducible across configurations. |
| **deer-flow** | ByteDance OSS | Open deep research pipeline (same team as PaSa). | ⚠️ Tied to ByteDance infrastructure assumptions; limited documentation as of mid-2026. |

### arXiv Sidecar Tools (Zero-Extra-Effort Layer)

Accessible as sidebar toggles on any `arxiv.org/abs/` page:

| Sidecar | What it adds | Adversarial Caveat |
|---------|-------------|--------------------|
| **Connected Papers** | Visual citation/influence graph, good for field entry | ⚠️ Uses PageRank approximation. Papers < 2 weeks old are frequently missing. Not suitable for cutting-edge tracking. |
| **CatalyzeX** | Auto-links code implementations to papers | Generally reliable; faster than Papers With Code for quick code discovery. |
| **Litmaps** | Temporal citation map showing thread evolution | ⚠️ Limited to indexed literature; grey literature and preprints not well covered. |
| **scite.ai** | Smart citations: Supporting / Contrasting / Mentioning classification | ⚠️ Full classification requires a paid subscription. Free tier limited to ~5 citations per paper. Critical for adversarial review but gated behind paywall. |
| **alphaXiv** | Community discussion layer on arXiv | Low traffic for most papers outside top-cited ML work. |
| **ResearchRabbit** | Citation graph visualization, adjacent work discovery | ⚠️ Relies on Semantic Scholar index; same lag issues. |

### Practitioner Distillation Tools

| Tool | Best Use | Caveat |
|------|----------|--------|
| **NotebookLM** (Google) | Ingest and distill a corpus; shared team spaces | ⚠️ Agent synthesis mode (like STORM/NotebookLM) is excellent for overview, poor for edge cases and negative results. Do not use as sole evidence base. |
| **SciSpace / Typeset.io** | 280M+ papers, structured evidence search, PDF reading | Avoids raw Google crawl; good for structured data extraction. |
| **Consensus** | Scientific agreement scoring across peer-reviewed papers | ⚠️ "Consensus" framing can mask genuine scientific controversy; check scite.ai for contrasting citations. |
| **Sugaku** | Math-focused; surfaces diverse rather than similar papers | Useful for exploration over exploitation; small coverage outside mathematics. |

---

## (B) API Stack

### Core APIs — Quick Reference

| API | Endpoint Pattern | Rate Limit | Auth | Best For |
|-----|-----------------|------------|------|----------|
| **arXiv** | `export.arxiv.org/api/query?id_list=ID` | ~1 req/3s | None | Preprints; use `id_list=` only (search_query endpoint rate-limited as of 2026-08) |
| **Semantic Scholar** | `api.semanticscholar.org/graph/v1/paper/arXiv:ID?fields=...` | 1/s (100/s with key) | Optional (free) | Citation graph, influential citations, TLDR, recommendations |
| **OpenAlex** | `api.openalex.org/works?search=QUERY&filter=open_access.is_oa:true` | 10/s | None (polite pool: add `mailto=`) | Open-access bulk queries, institution analytics, DOI/ORCID graph |
| **Papers With Code** | `paperswithcode.com/api/v1/papers/?q=QUERY` | ~1/s | None | Benchmark tracking, code linking, leaderboard |
| **CORE** | `api.core.ac.uk/v3/search/works?q=QUERY` | 10/s | Free key at core.ac.uk | Open-access aggregator, 230M+ papers |
| **BASE** | `api.base-search.net/cgi-bin/BaseHttpSearchInterface.fcgi?...` | ~1/s | None | 300M+ multilingual documents |

### ⚠️ Known API Issue (2026-08)
`export.arxiv.org/api/query?search_query=...` hangs indefinitely due to IP-level CDN block. **Always use the helper script** (`python3 ~/.hermes/skills/research/arxiv/scripts/search_arxiv.py "QUERY"`) or use `id_list=` directly when IDs are known. Do NOT use raw curl with `search_query=`.

### OpenAlex vs Semantic Scholar Decision Table

| Need | Preferred API |
|------|--------------|
| Open-access PDF links | OpenAlex (better OA coverage) |
| TLDR/abstract summary | Semantic Scholar |
| Citation graph bulk download | OpenAlex (free JSONL snapshots) |
| Influential citations weighting | Semantic Scholar |
| Institution-level analytics | OpenAlex |
| Paper recommendations | Semantic Scholar |

**OpenAlex caveat:** Strong coverage for open-access (OA) works. Coverage is structurally weak for paywalled content from Elsevier, Wiley, and Springer Nature — these publishers do not participate in OpenAlex metadata sharing at the same depth as OA venues.

### Useful Semantic Scholar Fields
`title`, `authors`, `year`, `abstract`, `citationCount`, `referenceCount`, `influentialCitationCount`, `isOpenAccess`, `openAccessPdf`, `fieldsOfStudy`, `publicationVenue`, `externalIds` (contains arXiv ID, DOI, GitHub).

### Useful OpenAlex Fields
`title`, `authorships`, `publication_year`, `cited_by_count`, `open_access.oa_url`, `concepts`, `referenced_works`, `related_works`, `biblio.volume`, `primary_location.source.display_name`.

---

## (C) GitHub Mining

### Bridge Tools: Paper → Code

| Tool | Method | Notes |
|------|--------|-------|
| **PaperFlow** (papersflow.ai) | Enter arXiv ID/DOI → auto-extracts all GitHub repos in body, footnotes, appendices | No API; web UI only. Use `web_extract(["https://papersflow.ai/paper/arXiv:ID"])`. |
| **Papers With Code API** | `paperswithcode.com/api/v1/papers/arxiv:ID/repositories/` | Canonical bridge: paper → code → benchmark → leaderboard. |
| **Semantic Scholar externalIds** | Add `fields=externalIds,openAccessPdf` to any paper query | Returns GitHub links for some papers; coverage is partial. |

### Purpose-Built Research Engineering Tools

| Tool | GitHub | Function | Caveat |
|------|--------|----------|--------|
| **AIDE** (Weco AI) | github.com/WecoAI/aideml | ML engineering agent: arXiv + PwC integration, auto-debugging loop | Best for automated ML experiment iteration; not general-purpose. |
| **RD-Agent** (Microsoft) | github.com/microsoft/RD-Agent | Paper → code → experiment → evaluate; Kaggle automation | ⚠️ Only 38% of comparable systems release reproducibility artifacts (arXiv:2608.05179). |
| **AI Scientist v2** (SakanaAI) | github.com/SakanaAI/AI-Scientist | End-to-end: ideation → experiment → paper. 12k+ stars. | ⚠️ Same reproducibility gap issue (arXiv:2608.05179): only 38% of 24 audited systems release seeds/traces. |
| **ToolMaker** (AI4Science) | ai4s-research/awesome-ai-for-science | Converts papers with code into callable agent tools | Niche; best for agentic research pipelines. |
| **AutoResearchClaw** (aiming-lab) | aiming-lab GitHub | Pipeline: paper → sandbox → multi-agent review → LaTeX | Active 2025-2026; check for latest repo name. |
| **GPT-Researcher** | github.com/assafelovic/gpt-researcher | Modular OSS deep research agent, pluggable backends | Backend-dependent quality. |

### GitHub Search Quality Signals

| Signal | Good | Caution |
|--------|------|---------|
| Last commit | < 3 months | > 12 months |
| Stars | Context-dependent | ⚠️ High stars alone ≠ quality — star counts are stale; viral threads can add 5k stars in 24h |
| Issues | Open + maintainer responses | All closed OR silently ignored |
| README | Reproducibility steps, pinned deps | "See paper" with no code |
| CI badge | Green | Missing or broken |
| License | MIT / Apache | None (legally unresolvable); CC-BY-NC (blocks commercial use) |

### Search Patterns

```
# Awesome list entry points (curated, but verify recency)
"awesome {topic} papers 2025" OR "awesome {topic} survey"
"best-of-{topic} GitHub"
"survey {topic} papers GitHub"
```

**Filter:** Last commit < 6 months; issues open with responses; README has dated update sections.

### ⚠️ GitHub Pitfalls (Consolidated)
- **Awesome lists go stale fast** — a list last updated in 2022 may omit 60%+ of current relevant work. Filter by `pushed:>2025-01-01`.
- **"Has code" ≠ "code works"** — check Issues for "cannot reproduce" reports before trusting results.
- **Star inflation** — viral Twitter/X links can add 5k stars in 24h with no quality signal.
- **SOTA in a README is 6–18 months behind** — always verify against PwC leaderboard, which is updated continuously.
- **Non-English institution repos** — Chinese papers may be on Gitee, Japanese on NAVER Clova, not GitHub. Check platform-specific hosting.
- **Maintainer bias** — curated awesome lists (40k stars) measure curation effort, not individual tool quality, and maintainers frequently list their own work prominently.

---

## (D) Multilingual Sources

### Database Coverage

| Resource | Language | Access | Notes |
|----------|----------|--------|-------|
| CNKI / CNKI Overseas | Chinese (Simplified) | Partial free / MCP crawler | Largest Chinese academic DB; MCP: mcpmarket.com/server/cnki-crawler |
| CiNii Research | Japanese | Free | National academic bibliography (cir.nii.ac.jp) |
| J-STAGE | Japanese | Open access | Scientific journals (jstage.jst.go.jp) |
| Cyberleninka | Russian | Open access | Russian academic corpus (cyberleninka.ru) |
| Redalyc | Spanish/Portuguese | Open access | Latin American and Iberian journals |
| SciELO | Multi (ES/PT/FR) | Open access | Developing countries open science |
| BASE | Multi | Free API | 300M+ documents, Bielefeld (base-search.net) |
| CORE | Multi | Free API key | 230M+ open-access, aggregated |

### Cross-Lingual Retrieval Strategies

**Validated approach** from "Better to Ask in English" (ACM 2024) + XRAG (arXiv:2505.10089):
1. Formulate query in English first
2. Retrieve from English-language databases
3. For non-English corpora: translate the query to the target language and search natively
4. Synthesize across languages back in English

**LLM-native variant:** Prompt in target language → retrieve in English → synthesize in target language. Outperforms naive cross-lingual retrieval for most languages tested.

**⚠️ Critical caveat — Translation loss:** The "translate to English first" strategy loses domain-specific terminology in Chinese and Japanese academic writing. Technical concepts in materials science (Chinese), earthquake engineering (Japanese), and traditional medicine (Chinese/Korean) often have no accurate English translation equivalent. Translating queries erases precision; translating retrieved abstracts back can introduce semantic drift. For high-stakes non-English research, search natively in the source language and involve a domain expert for synthesis.

**Key references:**
- XRAG (arXiv:2505.10089): cross-lingual RAG, mono vs multilingual retrieval comparison
- CLIR survey (arXiv:2510.00908): advances in cross-lingual information retrieval

---

## (E) Practitioner Workflow

### Standard Research Workflow (Consolidated)

```
1. DISCOVER
   arXiv: python3 ~/.hermes/skills/research/arxiv/scripts/search_arxiv.py "TOPIC" --sort date --max 10
   OpenAlex: curl -s "https://api.openalex.org/works?search=QUERY&per-page=10"

2. ASSESS IMPACT
   curl -s "https://api.semanticscholar.org/graph/v1/paper/arXiv:ID?fields=citationCount,influentialCitationCount,tldr"

3. CHECK SIDECARS (on arxiv.org/abs/ID page)
   → Connected Papers (field entry, adjacency)       [⚠️ misses papers < 2 weeks old]
   → scite.ai (contrasting citations)               [⚠️ free tier limited]
   → CatalyzeX (code link)

4. READ
   Abstract: web_extract(urls=["https://arxiv.org/abs/ID"])
   Full paper: web_extract(urls=["https://arxiv.org/pdf/ID"])
   HTML (when available): web_extract(urls=["https://arxiv.org/html/ID"])

5. FIND CODE
   curl -s "https://paperswithcode.com/api/v1/papers/arxiv:ID/repositories/"
   OR: web_extract(["https://papersflow.ai/paper/arXiv:ID"])

6. TRACE CITATIONS
   References from paper: curl -s ".../graph/v1/paper/arXiv:ID/references?fields=title,citationCount&limit=20"
   Papers citing it: curl -s ".../graph/v1/paper/arXiv:ID/citations?fields=title,year&limit=10"

7. DISTILL
   → NotebookLM: ingest corpus, generate overview    [⚠️ misses edge cases, negative results]
   → SciSpace: structured evidence extraction
   → STORM: holistic synthesis                       [⚠️ same bias as NotebookLM]

8. ADVERSARIAL CHECK
   → scite.ai: find contrasting/refuting citations
   → Manually check citing papers for novelty claims
   → Verify code release + seeds (not just "code available")

9. NON-ENGLISH ANGLE
   → CNKI (Chinese), CiNii/J-STAGE (Japanese), Cyberleninka (Russian), SciELO (ES/PT)
   [⚠️ Do not rely solely on English-translated queries — see (D)]

10. TEMPORAL GAP CHECK
    → Hugging Face Papers (huggingface.co/papers): zero-lag daily paper drops
    → arXiv/S2 have 1–7 day indexing lag
```

### Benchmarks for Research Agent Evaluation

| Benchmark | Paper | Measures |
|-----------|-------|----------|
| RealScholarQuery | ByteDance/PaSa | Real-world academic query recall [⚠️ only used by PaSa team] |
| SAGE | arXiv:2602.05975 | Retrieval for deep research agents |
| AIRS-Bench / FIRE-Bench | — | Frontier research agent evaluation |
| DeepHalluBench | arXiv:2601.22984 | Hallucination in research trajectories |
| FML-bench | arXiv:2605.17373 | Agent search dynamics strategies |
| AutoScholarQuery | ByteDance | 35k fine-grained academic queries from top AI conferences |

---

## (F) Known Gaps / Adversarial Critiques

### Comprehensive Critique Table

| Claim / Tool | Adversarial Counter-evidence / Limitation |
|--------------|------------------------------------------|
| **PaSa +37-39% recall** | Self-evaluated on ByteDance's RealScholarQuery benchmark; no independent third-party replication as of Aug 2026. Benchmark gaming risk. |
| **OpenAlex "250M+ works, fully open"** | Coverage structurally limited for paywalled content (Elsevier, Wiley, Springer Nature). Strong for OA; weak for subscription-only literature. |
| **"Translate query to English first"** | Loses domain-specific terminology in Chinese/Japanese academic writing. Technical terms in materials science, traditional medicine, seismology may have no accurate English equivalent. Translating introduces semantic drift for domain-critical queries. |
| **scite.ai smart citations** | Full supporting/contrasting classification requires paid subscription. Free tier limited to ~5 citations per paper; cannot be relied on as a systematic adversarial review tool without institutional or personal subscription. |
| **GitHub awesome-list star counts** | Stars are stale (often from viral moments, not sustained quality). Maintainer bias: list curators frequently include their own work prominently. A 2021 "21k star" project may be less maintained than a 2024 "3k star" project. |
| **Connected Papers citation graph** | Uses PageRank approximation, not full citation data. Papers published < 2 weeks ago are systematically missing. Not suitable for tracking cutting-edge work. |
| **STORM / NotebookLM synthesis** | Excellent for high-level overviews and consensus positions. Systematically poor at surfacing edge cases, negative results, minority viewpoints, and contradictory evidence. Use scite.ai + manual citation checks for adversarial completeness. |
| **AI Scientist / AutoResearchClaw reproducibility** | Verification Gap survey (arXiv:2608.05179): only 38% of 24 audited AI-scientist systems release reproducibility artifacts (seeds/traces). Code release is common (83%) but executable reproduction is rare. Do not trust agent-generated results without artifact verification. |
| **Semantic Scholar indexing** | 1–7 day lag for new papers. Lower coverage in humanities, social sciences, and non-English literature. Use Hugging Face Papers (huggingface.co/papers) for zero-lag daily ML paper tracking. |
| **PaperFlow "auto-extracts all repos"** | Web UI only; no API. Extraction quality depends on PDF parsing quality; repos in supplementary materials or external links may be missed. |
| **SAGE / benchmark recall metrics generally** | Recall metrics assume a known gold standard corpus. In practice, the true set of "all relevant papers" is unknowable; benchmark recall overstates real-world retrieval completeness. |

### Structural Gaps in the Current Stack (Not Covered by Any Tool)
1. **Novelty verification** — no agent reliably verifies whether a claimed contribution is genuinely novel vs. prior art. Manual citation tracing required.
2. **Grey literature** — GitHub repos, preprints on non-arXiv servers, blog posts, and workshop papers are inconsistently indexed. No single API covers all.
3. **Contradictory evidence surfacing** — agents synthesize toward consensus by default. scite.ai (paywalled) is the only systematic tool for finding dissenting citations.
4. **Reproducibility verification** — "code available" ≠ "results reproduce." Only 38% of AI-scientist systems release seeds/traces (arXiv:2608.05179).
5. **Non-English cutting-edge research** — most agents are English-first. Chinese and Japanese ML/materials science research is systematically underrepresented in English-language academic search.

---

## (G) New arXiv Papers to Track (Found via Web Search, Aug 2026)

| Paper | arXiv ID / URL | Relevance |
|-------|---------------|-----------|
| AI for Auto-Research: A Survey (Roadmap & User Guide) | arxiv.org/html/2605.18661 | L0–L4 autonomy taxonomy; covers end-to-end research agents including AI Scientist lineage |
| AI4Research: A Survey of Artificial Intelligence for Scientific Research | arxiv.org/html/2507.01903 | Covers PaSa, OpenScholar, and broader AI4research landscape; most comprehensive survey as of 2026 |
| Reinforcement Learning Foundations for Deep Research Agents | arxiv.org/html/2509.06733 | RL training for search agents; covers PaSa two-agent Crawler/Selector loop in technical depth |
| A Survey of AI Scientists and the Verification Gap | arXiv:2608.05179 | Critical: only 38% reproducibility rate across 24 AI-scientist systems; benchmark for claims audit |
| LLM Deep Search Agents Survey | arXiv:2508.05668 | SFT vs RL training comparison for search agents; open challenges survey |
| AutoResearch Survey | arXiv:2605.23204 | L0–L4 autonomy levels; "Vibe Research" (L1–L2) practical today |
| BLAZE | arXiv:2608.02775 | Socialized scientific intelligence: persistent KG + collective reasoning |
| XRAG | arXiv:2505.10089 | Cross-lingual RAG; mono vs multilingual retrieval comparison |
| ResearchAgent (Baek et al., 2025) | researchgate.net/publication/392503464 | Iterative research idea generation over scientific literature |

**Note:** PaSa primary arXiv ID not confirmed in search results (referenced as ByteDance/ACL 2025 in source files); verify via `python3 ~/.hermes/skills/research/arxiv/scripts/search_arxiv.py "PaSa paper search agent bytedance"`.

---

## Appendix: Consolidated API Cheatsheet

```bash
# arXiv — fetch by ID (do NOT use search_query= endpoint — rate-limited 2026-08)
curl -s "https://export.arxiv.org/api/query?id_list=2402.03300"

# Semantic Scholar — paper details
curl -s "https://api.semanticscholar.org/graph/v1/paper/arXiv:2402.03300?fields=title,authors,citationCount,influentialCitationCount,tldr,externalIds"

# Semantic Scholar — citations of a paper
curl -s "https://api.semanticscholar.org/graph/v1/paper/arXiv:2402.03300/citations?fields=title,authors,year,citationCount&limit=10"

# Semantic Scholar — paper search (JSON, fallback to arXiv script for keyword search)
curl -s "https://api.semanticscholar.org/graph/v1/paper/search?query=QUERY&limit=5&fields=title,authors,year,citationCount,externalIds"

# OpenAlex — open-access search
curl -s "https://api.openalex.org/works?search=QUERY&filter=open_access.is_oa:true&per-page=10"

# OpenAlex — citation chain (papers citing a work by OpenAlex ID)
curl -s "https://api.openalex.org/works?filter=cites:W2741809807&per-page=10&select=title,publication_year,cited_by_count"

# Papers With Code — repos for a paper
curl -s "https://paperswithcode.com/api/v1/papers/arxiv:2402.03300/repositories/"

# GitHub — repository search
curl -s "https://api.github.com/search/repositories?q=QUERY+topic:machine-learning&sort=updated&order=desc&per_page=10" \
  -H "Accept: application/vnd.github.v3+json"

# CORE — open access search (get key at core.ac.uk/api-keys)
curl -s "https://api.core.ac.uk/v3/search/works?q=QUERY" -H "Authorization: Bearer YOUR_KEY"

# BASE — multilingual open access
curl -s "https://api.base-search.net/cgi-bin/BaseHttpSearchInterface.fcgi?func=PerformSearch&query=QUERY&hits=20&format=json"
```

---

*Consolidated from three source files. All adversarial caveats are inline per the criteria provided. No claims are made without source attribution or critique.*  
**File:** `~/.hermes/skills/research/academic-literature-review/references/research-master-synthesis-2026.md`
