# Non-English Agent Research — Sweep 7 (Aug 12, 2026)

Part of the rolling non-English institutional source coverage for agent improvements.
This sweep specifically targeted sources NOT well-indexed on main arXiv English listings.

**Key pitfall confirmed this sweep:** `web_search` returned HTTP 429 (rate-limited) for the 
entire session. Workaround: use `web_extract` directly on target URLs — works reliably.

---

## Findings

### 1. CoffeeBench — Idle-Drift Pathology
**Source language:** Japanese (primary blog) + English (arXiv)  
**URL:** https://sakana.ai/coffee-bench/  
**arXiv:** 2606.16613  
**Venue:** ICML 2026 Workshop on Failure Modes in Agentic AI  
**Institution:** Sakana AI (Tokyo) × KPMG Azusa Audit Corp  

**Core technique:** Multi-agent economic simulation benchmark revealing the "idle-drift" 
failure mode: agent produces coherent reasoning but calls `wait_for_next_day()` instead 
of acting, for the entire duration of a 90-day simulation. Unique to long-horizon tasks; 
invisible in short evaluations. Claude Haiku 4.5 showed this in 3/3 runs; no other model did.

**Secondary finding:** High tool-call count ≠ performance. Kimi K2.6 matched top models in 
volume but called non-productive tools. Action type quality > action count.

**Hermes implementation:** Add idle-drift detector to agent loop harness. Track productive vs 
non-productive tool calls separately. If productive_calls == 0 for 5 turns AND reasoning tokens 
> 200/turn → inject recovery prompt. Full details: `agent-runtime-loop-patterns/references/noneng-agent-patterns-aug2026.md`.

---

### 2. Yandex Cloud Medical AI Agent — Deterministic Safety Gate Architecture
**Source language:** Russian  
**URL:** https://habr.com/ru/companies/yandex_cloud_and_infra/articles/1068692/  
**arXiv:** None (engineering blog)  
**Institution:** Yandex Cloud + ASPiRRe + ITMO University  
**Date:** August 12, 2026  

**Core technique:** LLM-scope minimization pattern for safety-critical agents. LLM handles 
exactly 2 roles: (a) extract structured data from free-text, (b) generate response from RAG. 
All risk/escalation decisions implemented in deterministic Python + YAML rules — never the LLM. 
Motivation: adversarial tests showed LLMs propagate injected false facts in 50–83% of cases.

**Hermes implementation:** Define `safety_gate.yaml` for computer_use and destructive file 
operations. Full details: `agent-runtime-loop-patterns/references/noneng-agent-patterns-aug2026.md`.

---

### 3. RUMBA — Russian Memory Evaluation Benchmark
**Source language:** Russian  
**URL:** https://habr.com/ru/companies/sberbank/articles/1060432/  
**arXiv:** Not cross-posted (blog-only as of Aug 2026)  
**Institution:** Sber AI  
**Date:** July 24, 2026  

**Core technique:** 3-axis compositional memory evaluation taxonomy (semantic_type × 
session_scope × temporality) with 17 semantic types including two not present in English 
benchmarks: DeleteInfo (does agent correctly forget on user request?) and AsstQuery (does 
agent remember its own prior outputs?). 85 multi-session dialogues, avg 191-day span, 
~340K chars/dialogue.

**Hermes implementation:** Use RUMBA taxonomy as design framework for memory eval harnesses. 
Full taxonomy + gap analysis: `llm-agent-memory-pipeline-research/references/rumba-memory-eval-taxonomy-aug2026.md`.

---

### 4. GigaCode CLI (Engineering blog, not novel research)
**Source language:** Russian  
**URL:** https://habr.com/ru/companies/sberbank/articles/1066152/  
**Institution:** Sber AI / SberTech  
**Date:** August 6, 2026  

Russian-language coding agent (IDE-integrated, Git-aware context injection). Engineering product 
update, not novel technique. Confirms Git-aware context injection pattern — already partially 
implemented in Hermes via `github-operations` skill. Not a new finding.

---

### 5. Sber LLM Data Lineage Agent (Engineering blog)
**Source language:** Russian  
**URL:** https://habr.com/ru/companies/sberbank/articles/1058618/  
**Institution:** Sber  
**Date:** July 28, 2026  

Agent that reads SQL/ETL code to auto-construct data lineage graphs. Addresses "stale 
documentation" problem. Interesting for repo audit use case but not an agent improvement 
technique per se. Low relevance to Hermes core.

---

## Source Access Matrix (Sweep 7)

| Source | Access method | Yield | Notes |
|--------|--------------|-------|-------|
| Sakana AI blog (sakana.ai) | web_extract ✅ | HIGH | Japanese primary; arXiv cross-posts available; full text |
| J-STAGE TJSAI (jstage.jst.go.jp) | web_extract ⚠️ | LOW | Article listing: metadata only; full text requires institutional login |
| CyberLeninka (cyberleninka.ru) | web_extract ⚠️ | LOW | JS-rendered search index doesn't extract; direct article URLs work better |
| Habr/Sber (habr.com/sberbank) | web_extract ✅ | HIGH | Russian corporate engineering blog; consistently full text |
| Habr/Yandex (habr.com/yandex) | web_extract ✅ | HIGH | Same; top articles from recent weeks load cleanly |
| Yandex Research (research.yandex.com) | web_extract ✅ | LOW | Publications list loads; content is primarily English arXiv papers |
| RISS (riss.kr) | web_extract ❌ | NONE | Korean institutional repo; requires login |
| KISS (kiss.kstudy.com) | web_extract ❌ | NONE | Korean academic; login-walled |
| NAVER AI blog | web_extract ❌ | NONE | No AI agent research content Aug 2026; product/infra posts only |
| Kakao tech (kakaoenterprise.github.io) | web_extract ❌ | NONE | No Aug 2026 content |
| DFKI (dfki.de) | web_extract ❌ | NONE | News section; no research blog; no Aug 2026 AI agent content |
| Inria (inria.fr) | web_extract ❌ | NONE | News section only; no research blog for Aug 2026 |
| web_search (all) | ❌ HTTP 429 | NONE | Rate-limited entire session — use web_extract directly |

## Methodology lessons

1. **web_search rate limit → web_extract fallback is the right move immediately**, not retrying search.
2. **Habr is the richest Russian-language source** for AI engineering content from major Russian labs (Sber, Yandex, SberDevices). Target it directly with known company blog paths.
3. **J-STAGE requires institutional login for full text** — metadata/abstract is accessible but insufficient for technique extraction. Don't budget deep time here.
4. **Korean sources remain blocked** (RISS, KISS) — no workaround found. Korean AI content appears on English arXiv (KAIST, NAVER papers) rather than domestic repos.
5. **European institutional blogs (DFKI, Inria)** don't maintain research blogs with Aug 2026 content — research appears on arXiv/conference proceedings only.
