# arXiv API Fallback & Research Sweep Pitfalls

**Documented:** August 2026 — from agent context compression multilingual research sweep.

## arXiv REST API Network Timeout (Critical)

The arXiv REST API (`export.arxiv.org/api/query`) can be **completely unreachable** in
some network environments — curl returns 0 bytes with no error. Complex boolean queries
(`AND`, `OR` combined with field prefixes `ti:`, `abs:`) also frequently return empty XML
even when the API is reachable. This is NOT an API key issue.

**Reliable fallback sequence when the API returns nothing:**

1. `web_search` with query: `arXiv 2026 "topic phrase" abstract institution`
   — Google indexes arXiv abstracts; snippets often contain quantified findings + arXiv IDs.
2. `web_extract(urls=["https://arxiv.org/abs/PAPER_ID"])` on known arXiv IDs
   — abstract pages are reliably scrapable: full metadata + abstract text.
3. `web_extract(urls=["https://arxiv.org/html/PAPER_ID"])` — full HTML (when available).
4. Semantic Scholar HTTP API: `https://api.semanticscholar.org/graph/v1/paper/search?query=...&fields=title,authors,year,externalIds`
5. Papers-with-Code search for very recent papers.
6. For Chinese institution papers: QQ Tech / Zhihu / 微信公众号 snippets (web_search with
   Chinese institution names: 中国科学院, 上交, 清华, 北大 + topic keywords).

**Never conclude "no papers found" because the API timed out.**

## Preferred arXiv API Query Style (when API is reachable)

- Use `all:term1+term2` (simple AND) rather than complex boolean expressions
- Avoid `ti:`, `abs:` field prefixes in combination with `ANDNOT` / `OR` in shell curl
  calls — URL encoding interactions cause silent failures
- `sortBy=submittedDate&sortOrder=descending&max_results=15` is a reliable default
- Always filter results to `DATE >= 2025-06` after parsing; the API does not date-filter
  reliably on all query forms

## Community Sentiment Sources (agent/ML research sweeps)

- **r/LocalLLaMA, r/MachineLearning**: web_extract is blocked; use `web_search` with
  `site:reddit.com r/LocalLLaMA [topic]` — snippets contain upvoted positions
- **Hacker News**: `site:news.ycombinator.com [topic]` via web_search; or direct
  `web_extract("https://hn.algolia.com/?q=topic")` for structured results
- **Chinese tech press**: QQ Tech (`news.qq.com`), 微信公众号 summaries often contain
  verbatim excerpts from Chinese institution papers; search `"arXiv 2026" 综述 [topic]`

## Output Format for Implementability Assessment

For each paper in a sweep targeting a specific system, include:

```
| Field | Value |
|-------|-------|
| arXiv ID | [NNNN.NNNNN](https://arxiv.org/abs/...) |
| Date | YYYY-MM-DD |
| Institution | [Name] |
| Code | URL or "None" |

**Quantified benefit:** [exact numbers from abstract]
**Hermes implementability:** ✅/⚠️/❌ [rationale: API-only / needs fine-tuning / server-side]
**Gap vs. current stack:** [what's new vs. what's already deployed]
```

The "Hermes implementability" flag is critical for research sweeps targeting Hermes v0.20+:
- ✅ = API-only, no fine-tuning, prompt-level or harness-level change
- ⚠️ = Partial (some aspects API-implementable, others require server/backend)
- ⚠️ SERVER = Requires inference backend control (vLLM, llama.cpp, etc.)
- ❌ = Requires fine-tuning or training

## Agent Token Optimization Research — Key Sources (August 2026)

Verified high-signal papers from August 2026 sweep (all confirmed via arxiv.org abstract extraction):

### Context Compression
- **TokenPilot** arXiv:2606.17016 (Zhejiang/Alibaba, Jun 2026) — 61–87% cost reduction; cache-invalidation trap: compaction that alters prefix hashes cancels its own benefit
- **GenericAgent** arXiv:2604.17091 (Fudan, Apr 2026) — 6× fewer tokens; hierarchical on-demand memory + self-evolving SOPs; code at github.com/lsdefine/GenericAgent
- **ACM Five-Primitives** arXiv:2607.21503 (Jul 2026) — quadratic→linear cost via validated compaction; 92% LongMemEval

### Prompt Caching
- **Don't Break the Cache** arXiv:2601.06007 (Jan 2026) — 41–80% cost savings; dynamic tool outputs must go *after* cache boundary; full-context caching can paradoxically *increase* latency
- **Auditing Prompt Caching** arXiv:2502.07776 (Stanford, 2025) — TTFT timing = cache-drift detection signal

### Tool Schema Compression
- **TSCG** arXiv:2605.26165 (May 2026) — 44–50% schema savings; binary enablement at 8k context (near-zero → +20.5pp EM)
- **Tool Attention** arXiv:2604.21816 (Infrrd.ai, Apr 2026) — 95% tool token reduction via ISO embedding gating + lazy loading; code at github.com/asadani/tool-attention
- **Notation Matters** arXiv:2605.29676 (May 2026) — TRON 27% savings; TOON fragile in multi-turn (avoid)
- **Control Under Compression** arXiv:2608.01056 (Aug 2026) — ≥75% control context must be retained; below 50% causes tool-execution/parsing failures

### Selective Context Injection
- **SAGE** arXiv:2604.15583 (MIT, Apr 2026) — 90% token reduction via attention heatmap; training-free; uses lightweight LLM as relevance scorer
- **Structured Distillation** arXiv:2603.13017 (Mar 2026) — 11× compression, 96% recall; four-field schema: exchange_core / specific_context / thematic_room / artifacts_touched
- **Less Context Better Agents** arXiv:2606.10209 (Microsoft, Jun 2026) — last-5 tool-pairs + summarization: 91.6% completion at 63% fewer tokens

### KV Cache Reuse
- **IntentKV** arXiv:2606.09916 (Jun 2026) — 77.8% worst-case peak token reduction; cross-turn intent QueryMemory (intent scoring is API-implementable even if KV eviction is server-side)
- **AgentKVShift** arXiv:2607.21604 (UC San Diego, May 2026) — 2–3.5× prefill speedup; structured memory reuse with probe-guided residual correction
- **MemDecay** arXiv:2607.10582 (Jul 2026) — system token half-life 148–189 steps vs. scratchpad 14–16 steps (10× difference); region-aware eviction priority
- **Online KV Compaction** arXiv:2608.00902 (Aug 2026) — 80% KV reduction; delay compaction to *start* of next turn (use incoming query as proxy), not end of current turn
- **CompressKV** arXiv:2606.24467 (TU Darmstadt, Jun 2026) — 97% perf at 3% KV cache; server-side

### Per-Turn Cost Measurement
- **Agent Spend Analysis** arXiv:2604.22750 (Michigan/MIT/Stanford, Apr 2026) — agents 1000× more expensive than code chat; accuracy peaks at intermediate token count (not maximum); model cost-prediction correlation ≤0.39
- **Harness Effect** arXiv:2607.06906 (Writer, Jul 2026) — 38% token reduction / 41% cost reduction from orchestration layer alone (same models); quality per dollar +82%; 6 mechanism families
- **Token Economics Survey** arXiv:2605.09104 (Zhejiang, May 2026) — differentiable token budgets; 4-level taxonomy (micro/meso/macro/security)
