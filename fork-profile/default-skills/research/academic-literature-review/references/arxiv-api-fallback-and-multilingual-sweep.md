# arXiv API Fallback & Multilingual Research Sweep — Field Notes
*August 2026 — from agent memory topology research session*

## arXiv Export API Reliability — Critical Environment Pitfall

The arXiv export API (`export.arxiv.org`) **consistently times out or returns 0 bytes** in this Hermes environment. Do NOT attempt `curl` to the API — it will waste round-trips.

### Working fallback sequence (fastest first)

1. `web_search("site:arxiv.org <topic> <year>")` — Google indexes arXiv fully; returns title, arXiv ID, and abstract snippet. **Best discovery path.**
2. `web_search("arxiv <YYMM> \"<topic>\" <year>")` — Month-prefix filter (2607 = July 2026, 2608 = Aug 2026) gives date-scoped sweeps without the API.
3. `web_extract(urls=["https://arxiv.org/abs/<ID>"])` — Abstract page works reliably even when export API is down.
4. `web_search("site:arxiv.org abstract \"<exact phrase>\"")` — Phrase search for high-precision discovery.
5. GitHub curated lists (`awesome-<topic>`, `<topic>-paper-list`) — Community-maintained, include dates and IDs, often more current than API indexes.
6. HuggingFace papers (`huggingface.co/papers?q=<topic>`) — Real-time tracking with community votes; reliable extraction.

**Never retry the export API** — 0-byte on first try = down for this session. Fall back immediately.

---

## Multilingual Research Sweep Patterns (2026)

From a successful agent memory topology sweep covering arXiv + GitHub + social + Chinese + Japanese sources.

### Chinese Academic Sources

**Effective proxies for CNKI (which blocks direct extraction):**
- `web_search("CNKI 知网 <topic in Chinese> <year>")` — returns Zhihu articles that cite CNKI papers with key findings
- `web_search("site:zhuanlan.zhihu.com <Chinese topic keywords> arXiv <year>")` — Zhihu tech posts summarize Chinese academic papers with arXiv IDs
- `web_search("<topic> 综述 arXiv <year> 北邮 OR 清华 OR 北大 OR 华为")` — Institution + 综述 (survey) narrows to academic output
- Key Chinese institutions active in LLM agent memory (2026): BUPT (北邮), Tsinghua, PKU, CUHK, XMU, Fudan, Renmin, SJTU/SAIF
- **Zhihu** (zhuanlan.zhihu.com) is the most reliable Chinese academic content proxy — scrapable, cites papers with IDs

**CNKI direct access**: Always blocked. Use Zhihu/CSDN/Baidu developer posts as proxies. Never spend more than 1 attempt on CNKI direct extraction.

### Japanese Sources (J-STAGE)

- **J-STAGE** does not index English-language AI/ML papers; Japanese-language LLM agent research is sparse vs. Chinese output
- IPSJ has a 2-year embargo on conference papers — 2024 papers not available until 2026 at earliest
- `web_search("J-STAGE LLM agent memory <topic> Japan 2026")` is the correct probe; expect sparse results
- Relevant Japanese community: LinkedIn tech posts, JSAI conference proceedings (some in English)
- **Conclusion for agent memory topology**: No J-STAGE papers identified; community signal comes from LinkedIn/tech blogs (privacy/governance theme)

### Social Media Extraction

- **Reddit**: Always blocks `web_extract`. Use `web_search("site:reddit.com r/<subreddit> <topic> <year>")` — Google snippets often contain enough of the top comment to extract sentiment
- **Hacker News**: Use `web_search("news.ycombinator.com <topic> <year>")` or `web_extract` on `hn.algolia.com` search — both work
- **Twitter/X**: Community consensus surfaces in blog aggregators (emergentmind.com, memorypapers.org, aimodels.fyi) which are scrapable and summarize HN/Twitter discussion

### GitHub Research List Strategy

Curated paper lists are the highest-signal discovery path for recent papers:
- Search pattern: `web_search("github awesome <topic> papers 2026")`
- Key repositories found for agent memory: 
  - `Shichun-Liu/Agent-Memory-Paper-List` (2.3k stars) — tracks FFD survey papers
  - `VoltAgent/awesome-ai-agent-papers` (1.7k stars) — weekly-updated 2026 agent papers with Memory & RAG section (57 papers)
  - `DEEP-PolyU/Awesome-GraphMemory` — graph-based memory taxonomy companion
  - `OpenDataBox/awesome-agent-memory` — companion to SIGMOD 2026 comparative study
- **Extraction tip**: GitHub README pages are reliably scrapable; use `web_extract` on the main page, then `read_file` on the cached file for the truncated middle section

### Community Blog Aggregators (reliable extraction, 2026)

These sites index arXiv papers with community votes/discussion and are scrapable:
- `emergentmind.com/topics/<topic>` — topical aggregation with paper snippets
- `aimodels.fyi/papers/arxiv/<topic>` — paper summaries with key findings
- `memorypapers.org/papers/<topic>` — memory-specific aggregator (new 2026)
- `huggingface.co/papers?q=<topic>` — real-time with votes, scrapable
- `scirate.com` — arXiv paper ratings, scrapable

---

## Parallel Search Batching — Verified Effective Pattern

From this session: batch 6–8 `web_search` calls in a single turn, then batch 3 `web_extract` calls on highest-value URLs. This is 2–3× faster than serializing.

**Effective batch for a June–August 2026 memory topology sweep:**
```
Batch 1 (web_search × 6):
  1. "arxiv 2026 agent memory topology architecture June July August cs.AI"
  2. "arxiv 2026 LLM agent memory management knowledge graph ontology June July August"  
  3. "site:arxiv.org 2026 agent memory hierarchy tiered episodic semantic forgetting"
  4. "arxiv 2607 2608 \"agent memory\" new paper language model graph topology"
  5. "CNKI 知网 2026 AI智能体记忆架构 knowledge graph memory agent Chinese"
  6. "github awesome agent memory papers 2026"

Batch 2 (web_extract × 3 on highest-value URLs):
  - arxiv.org/abs/<ID> for top 3 new papers found in batch 1
```

**Critical**: The first batch often surfaces 3–5 key papers + 2–3 GitHub lists. The second batch fills in quantified results from abstracts. After that, targeted follow-up searches for specific sub-topics.

---

## Date-Scoped arXiv Discovery (by ID prefix)

arXiv IDs encode year+month: `YYMM.NNNNN`
- 2606.* = June 2026
- 2607.* = July 2026  
- 2608.* = August 2026
- 2605.* = May 2026

Use in searches: `web_search("arxiv 2607 \"<exact phrase>\"")` — the 4-digit prefix acts as a date filter that Google respects.

For sweep coverage, run separate queries for each month prefix to catch papers that don't appear in topic-only searches.
