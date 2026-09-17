# Hermes Research Sweep Script Design Patterns

Reusable engineering lessons for hermes-research-sweep.py and any similar
multi-source academic sweep script. Drawn from the Sep 2026 consolidation
and efficiency pass.

## Category Consolidation

When a sweep script has grown to 50+ categories:

1. Identify merge candidates by comparing `arxiv_cats` lists across categories.
   Categories with identical arxiv_cats AND overlapping conceptual space are
   safe to merge. Categories with distinct search spaces stay separate.
2. Merge rule: union all arxiv_cats, keep up to 5 unique query strings across
   all merged categories (dedup by exact string). Drop queries that are strict
   subsets of broader ones.
3. Measure wall-clock improvement: categories * (queries * per-query-latency)
   + listing fetches * (cats-with-new-arxiv-codes * listing-latency).
   The listing fetch cost dominates for large sweeps.
4. Verify with: AST parse + importlib module load + assert len(CATEGORIES) == N
   + assert all(len(c['queries']) == 5 for c in CATEGORIES.values())

Sep 2026 result: 98 -> 51 categories, 41 -> ~28 unique arXiv listing codes,
~50% wall-clock reduction, 0 unique queries lost.

## Off-Topic Pre-Filter

Apply a compiled regex to (title + source) BEFORE adding to the seen cache
or writing to output. This keeps the seen cache small and triage load low.

Filter design principles:
- Compile once at module load: `_OFFTOPIC = re.compile(r'\b(...)\b', re.I)`
- Target domain clusters, not individual words: medical (cancer/tumor/RNA...),
  physics (quark/boson/superconductor...), climate (atmospheric/precipitation...),
  humanities (archaeology/medieval...), sport (athletic/olympic...).
- DO NOT filter on: learning, neural, network, model, agent, optimization,
  graph, matrix, distribution, random, stochastic, algorithm -- too broad.
- Apply pre-filter in the dedup loop, NOT in the per-source fetch functions.
  This keeps source functions generic and reusable.
- Log the filtered_count in the sweep summary for monitoring filter drift.

Filter placement in the dedup loop:
```python
for p in all_papers:
    pid = p["id"]
    title = p.get("title", "") or ""
    if _OFFTOPIC.search(title):
        filtered_count += 1
        continue
    if pid and pid not in seen_this_run:
        seen_this_run.add(pid)
        unique_papers.append(p)
```

## Direct Listing Pre-Flight

For sweeps targeting agent/AI research, add explicit listing fetches for the
core CS categories (cs.AI, cs.CL, cs.MA, cs.LG, cs.SE) BEFORE the per-category
loop. This guarantees core agent papers are captured even if none of the
category queries match them.

Implementation: iterate over CORE_ARXIV_CATS, call `sweep_arxiv_listings(cat)`
for each (deduplicate against fetched_arxiv_cats to avoid double-fetching).
Do this before the per-category loop; the per-category loop will skip already-
fetched listing pages.

Core cats for Hermes agent research:
  ['cs.AI', 'cs.CL', 'cs.MA', 'cs.LG', 'cs.SE']

## Source Coverage Decisions

- **arXiv listings + search**: primary, low latency, high volume
- **Semantic Scholar**: best for citation-ranked results, unauthenticated ok
- **OpenAlex**: best for non-arXiv venues (NeurIPS/ICML proceedings)
- **Crossref**: LOW value for cs.AI corpus -- mostly finds published versions
  of papers already in arXiv. Drop if sweep latency is a concern.
  Only real value: very new proceedings before arXiv preprint appears.
- **Multilingual sources** (HAL, IPSJ, Cyberleninka): keep for French/Japanese/
  Russian coverage; expect low hit rate for agent-specific queries.

## Seen Cache Sizing

MAX_SEEN controls how many arXiv IDs are held in the dedup cache across runs.
When the cache exceeds MAX_SEEN, old entries are evicted and previously-seen
papers can re-appear in output. Monitor: if triage shows many duplicates from
previous sweeps, increase MAX_SEEN or switch to a persistent SQLite-backed cache.

## Verification Script (run after every structural change)

```python
import ast, importlib.util, re
path = 'hermes-research-sweep.py'
src = open(path).read()
ast.parse(src)  # fails fast on syntax error
spec = importlib.util.spec_from_file_location('sweep', path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
assert len(mod.CATEGORIES) == EXPECTED_COUNT
assert all(len(c['queries']) == 5 for c in mod.CATEGORIES.values())
assert all('arxiv_cats' in c for c in mod.CATEGORIES.values())
print('PASS')
```
