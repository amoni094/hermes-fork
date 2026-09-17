# Hermes Research Sweep — Source & Query Configuration Reference

Last updated: 2026-09-04 (after Sweep 31 noise diagnosis, fixes applied for Sweep 32)

## Active Sources (as of Sweep 32)

| Source | Coverage | Queries/cycle | Notes |
|--------|----------|---------------|-------|
| arXiv listings | cs.AI/CL/MA/LG/IR/SE | 7 categories | Most reliable for recency |
| arXiv HTML search | cs.AI/CL/MA/LG/IR/SE | 7 categories x 5 queries | Was 3/cat pre-Sweep30 |
| Semantic Scholar | All CS | 5 queries/category | Was 2/cat pre-Sweep30 |
| OpenAlex | CS-only (C41008148 filter) | 5 queries/category | CS concept filter added Sweep32 |
| Crossref | CS-domain AND-filter | 5 queries/category | AND-boolean filter added Sweep32 |
| HuggingFace Papers | Trending community picks | Top 20 | Added Sweep30 |
| Papers With Code | Leaderboard trending | Top 20 | Added Sweep30 |
| HAL | French/EU academic | 5 French queries | EU-funded, all languages |
| AMiner | Chinese AI/CS graph | 7 queries | 48h+ lag for very recent papers |
| J-STAGE | Japanese journals | 4 queries | Low yield for agent queries |
| CyberLeninka | Russian OA | 4 queries (RU+EN) | Lower signal quality |
| Korean | arXiv institution search | KAIST/SNU/POSTECH | Small volume, high quality |

## Noise Pitfalls and Fixes

### OpenAlex CS filter

Problem: Without concept filter, OpenAlex returns medical/biology/public-health papers
at high volume (~40-50% of raw results by Sweep 31).

Root cause: OpenAlex indexes all academic disciplines; its default sort (cited_by_count)
favors high-citation medical journals over niche CS/AI work.

Fix applied (Sweep 32, 2026-09-04):

    filter=publication_year:2025|2026,concepts.id:C41008148

C41008148 is OpenAlex's concept ID for Computer Science. Verify via:
https://api.openalex.org/concepts/C41008148

If the ID ever stops working, find the current CS concept ID:
https://api.openalex.org/concepts?search=computer+science&per-page=1

### Crossref domain filter

Problem: Without constraint, Crossref returns physics/cosmology/medical journals
(~30% of raw results by Sweep 31). Crossref has NO subject/category filter parameter.

Fix applied (Sweep 32, 2026-09-04): bake CS terms into the query string:

    cs_query = f'({query}) AND (agent OR LLM OR "language model" OR "neural network")'

Do NOT use 'agent language model' as a plain suffix (prior attempt, Sweep 30).
The AND boolean with parenthesized alternatives is significantly more selective.

### History: noise accumulation timeline

| Sweep | Raw papers | Off-topic ratio | Notes |
|-------|-----------|-----------------|-------|
| 29 | ~300 | ~30% | Acceptable |
| 30 | 420 | ~50% | Crossref/Korean OpenAlex added, no domain filter |
| 31 | 420 | ~83% | Action item documented but not applied |
| 32 | TBD | TBD | CS filters applied — expect <20% off-topic |

## Structurally Blocked Sources

These sources are relevant but inaccessible from the sweep script:

- **Reddit** (r/LocalLLaMA, r/MachineLearning): 403/redirect; only Google snippet text
- **Zhihu, Juejin, V2EX** (Chinese practitioner): login-wall; no programmatic access
- **CNKI**: paywalled; workaround = arXiv institution search with Chinese university names

## Multilingual Query Coverage

| Language | Source | Queries | Quality |
|----------|--------|---------|--------|
| English | arXiv, SS, OpenAlex, HF, PWC, Crossref | 5/cat | Primary |
| French | HAL | 5 | Good — HAL covers EU-funded research |
| Chinese | AMiner | 7 | Good for institutional; practitioner blocked |
| Japanese | J-STAGE, arXiv | 4 | Low yield; J-STAGE best for NLP/robotics |
| Russian | CyberLeninka | 4 | Low signal; use for completeness only |
| Korean | arXiv institution | KAIST/SNU/POSTECH | Small but high quality |

## When to Check This File

- After a sweep with unexpectedly high noise ratio (>25% off-topic)
- Before adding a new source to the sweep script
- If OpenAlex or Crossref results look wrong (verify concept ID still valid)
- Sweep boundary log is in SKILL.md (the sweep table); this file is for source/config
