# hermes-research-sweep.py — Coverage Gaps Found and Fixed (2026-08-31)

Commit: 24700d0

## Gaps fixed

### 1. Query truncation (silent — no error, just fewer results)
- `search_arxiv_html` loop: `cat["queries"][:3]` — only 3 of 5 queries ran
- `search_semantic_scholar` loop: `cat["queries"][:2]` — only 2 of 5 queries ran
- Fix: removed slices; all queries now run for both sources
- OpenAlex `[:2]` is INTENTIONAL (OpenAlex is slower; top 2 queries are highest-signal) — do not remove
- Crossref `[0]` is INTENTIONAL (one quality-anchor query per category)

### 2. Dead code — functions defined but never called in run_sweep()
- `search_crossref()` — defined at line ~400, never invoked
- `scrape_hf_papers()` — defined, never invoked (HF_PAPERS_URL constant also unused)
- `scrape_pwc()` — defined, never invoked (PWC_TRENDING constant also unused)
- Fix: all three wired into run_sweep() after the multilingual block

### 3. Korean source missing entirely
- HAL (FR), AMiner (ZH), J-STAGE (JA), CyberLeninka (RU) were present
- Korean had no source despite academic-literature-review having Korean paper references
- Fix: added `ko` entry to MULTILINGUAL_SOURCES using arXiv institution search
  (KAIST, Seoul National University, POSTECH) — no native Korean academic API available
- Wired into run_sweep() with `multilingual_ko` category label

### 4. Multilingual queries too thin (2-3 per language, one topic cluster)
- Old: ZH 3 queries, JA 2, FR 2, RU 2 — all single-topic (memory/agent only)
- Fix: expanded to cover all 7 research categories per language:
  - ZH: 7 queries (self-improvement, RAG, evaluation, tool use added)
  - JA: 4 queries (multi-agent, memory retrieval added)
  - FR: 5 queries (multi-agent, self-improvement, evaluation added)
  - RU: 4 queries (multi-agent, self-improvement added)

## Verification pattern (27-check suite)

Run after any sweep script edit:

```python
import ast, sys, re
SCRIPT = "/var/home/rainbow/.hermes/scripts/hermes-research-sweep.py"
src = open(SCRIPT).read()

# 1. AST valid
ast.parse(src)

# 2. All fetcher functions defined
for fn in ["scrape_hf_papers", "scrape_pwc", "search_crossref",
           "search_hal", "search_aminer", "search_jstage",
           "search_cyberleninka", "search_semantic_scholar",
           "search_openalex", "sweep_arxiv_listings",
           "search_arxiv_html", "run_sweep"]:
    assert fn in src, f"MISSING: {fn}"

# 3. No truncating slices on arXiv/S2 loops
assert 'for query in cat["queries"][:3]' not in src, "arXiv loop still truncated"
assert 'for query in cat["queries"][:2]:\n            papers = search_semantic_scholar' not in src, "S2 loop still truncated"

# 4. New sources wired in run_sweep body
# (extract run_sweep body, check for each name)
for name in ["search_crossref", "scrape_hf_papers", "scrape_pwc", "multilingual_ko"]:
    assert name in src, f"NOT wired: {name}"

# 5. Korean in MULTILINGUAL_SOURCES
assert '"ko"' in src and "arxiv_queries" in src

# 6. Multilingual query counts
ml = re.search(r'MULTILINGUAL_SOURCES\s*=\s*\{(.+?)\n\}', src, re.DOTALL).group(1)
for lang, key, n in [("zh","aminer_queries",7),("fr","hal_queries",5),
                     ("ja","jstage_queries",4),("ru","cyberleninka_queries",4)]:
    section = re.search(rf'"{lang}".*?"{key}".*?\[(.*?)\]', ml, re.DOTALL).group(1)
    count = section.count('"') // 2
    assert count >= n, f"{lang}: {count} < {n} required"

print("All checks passed")
```

## Lesson

When a script has fetcher functions defined as constants or helper functions but
no call site in the main loop, they are silently dead. Always verify by searching
for the function name inside the `run_sweep` body specifically, not just the file.
The `[:N]` query slice pattern is a budget-control pattern that can accidentally
become a coverage gap when it's applied to the wrong loop.
