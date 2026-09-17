# Multilingual AI Agent Research: French / Russian / Ukrainian (2024)

Session: July 2026. Synthesizes content extracted from TALN 2024, CyberLeninka, and ACL Anthology UNLP workshop.

## 2026 refresh sweep (SerpApi, July 2026) — genuinely new since prior pass

### French (CORIA-TALN 2025, Marseille — fully open, talnarchives.atala.org)
- **Token pruning for late-interaction retrieval** ("Vers un élagage de tokens sans coût...",
  Zong & Piwowarski): preserves ColBERT-level retrieval performance using only 30% of tokens via
  regularized pruning. Relevant to Hermes' RAG-adjacent retrieval paths (QMD, Graphiti search) if
  token-count-per-retrieval-hit ever becomes a bottleneck.
- **AutoCluster** (Versmée, Remil, Kaytoue, Velcin): ReAct-style LLM clustering agent w/
  tool-calling, outperforms SOTA baselines across 26 clustering datasets. Domain-specific, not
  directly actionable for Hermes.

### Russian (CyberLeninka, fully open CC BY)
- **TEMA** (Teacher Exponential Moving Average fine-tuning, Sviridenko/Bobrova/Zaitsev/
  Dyuldin/Shifman, Intl. J. Open Information Technologies 2026): curbs catastrophic forgetting
  during domain adaptation. Qwen2-0.5B/1.5B + LoRA/4-bit; best plasticity-stability tradeoff on
  BLEU/ROUGE/BERTScore + MMLU 5-shot (medical corpus). Fine-tuning-specific — not applicable to
  Hermes' API-only usage, but relevant to the broader "catastrophic forgetting" literature that
  touches memory-maintenance research.
- **"Архитектура LLM агентов"** (Architecture of LLM Agents, Namiot & Ilyushin, MSU, Intl. J.
  Open Information Technologies 2025): survey covering workflows, orchestration, memory,
  tool-calling, MCP. No benchmark numbers — conceptual cross-reference, not a new technique.

### Ukrainian (UNLP 2026, 5th ed., Lviv, May 2026 — new proceedings volume since prior baseline)
- **DictSpec** (Syvokon, aclanthology.org/2026.unlp-1.15): dictionary-based speculative decoding
  for non-Latin-script languages. Up to 1.65x fewer verification steps (controlled emulation), up
  to 1.76x speedup (hybrid, live vLLM serving); <5MB memory overhead, no training required.
- **Lapa-12B** (Paniv et al., aclanthology.org/2026.unlp-1.14): data-efficient adaptation of
  multilingual LLMs to Ukrainian. Instruction-tuned Gemma-3-12B variant needs 1.5x fewer tokens
  than base model for same text; 33 BLEU on FLORES.
- Three UNLP 2026 shared-task papers on RAG pipeline design show incremental gains (e.g. Recall@1
  0.6957->0.7935 with reranking) — within already-known RAG territory, not a new technique class.

### Checked, no new findings beyond known baseline
LLM routing: no dedicated LLM-routing literature found in French, Russian, or Ukrainian this pass
(hits were non-LLM routing, e.g. telecom/network routing) — explicit negative result. Agent
memory topology (dedicated): nothing beyond the Namiot/Ilyushin survey above and the
already-known Focus Agent baseline (arXiv:2601.07190, 22.7% token reduction).

---

## TOP PICK FOR HERMES — Active Context Compression

### Focus Agent — Active Context Compression (arXiv:2601.07190)
- **Author:** Nikhil Verma
- **Submitted:** January 12, 2026 (cs.AI)
- **Architecture:** "Focus Agent" — inspired by *Physarum polycephalum* (slime mold) retraction behavior
- **Core idea:** Intra-trajectory compression — agent actively prunes its own context *during* a single task using two primitives:
  - `start_focus` — marks a checkpoint before exploration begins
  - `complete_focus` — agent summarizes what was attempted/learned, then system deletes the raw log and prepends the summary to a persistent "Knowledge" block at context top
  - Result: "sawtooth" context pattern (grows → collapses → grows → collapses) vs. standard "append-only" monotonic growth
- **Results on SWE-bench Lite (Claude Haiku 4.5, N=5 hard instances):**
  - 22.7% total token reduction (14.9M → 11.5M tokens), identical accuracy (3/5 = 60%)
  - Savings up to 57% on exploration-heavy tasks (matplotlib-26020, seaborn-2848, sympy-21171)
  - Average 6.0 compressions/task, 70.2 messages dropped/task
- **Critical implementation lesson:** Passive prompting → only 6% savings + accuracy degradation. **Aggressive prompting required:**
  - "ALWAYS call `start_focus` before ANY exploration"
  - "ALWAYS call `complete_focus` after 10-15 tool calls"
  - System injects periodic reminder after 15 tool calls without compression
- **Caveat:** One task (pylint-7080) showed +110% token increase — iterative refinement tasks benefit less than explore-then-implement tasks
- **Hermes implementation path:** Implement as a skill that wraps the agent loop. Force compression checkpoints every 10–15 tool calls. Knowledge block = structured YAML at top of context, not free text.
- **Related work:** MemGPT (OS-inspired memory hierarchy), Reflexion (episodic buffer), StreamingLLM (attention sinks), LLMLingua (separate compression model — requires extra infra, unlike Focus which is prompt-only)

---

## FRENCH — TALN 2024 (talnarchives.atala.org)

Conference: JEP-TALN-RECITAL 2024, Toulouse, July 8–12, 2024. Open access, all PDFs direct download.

### LOCOST — State-Space Models for Long Document Summarization
- **Authors:** Florian Le Bronnec (Sorbonne/Paris-Dauphine), Song Duong (Criteo AI Lab), et al.
- **Paper:** talnarchives.atala.org/TALN/TALN-2024/7014.pdf. Also in EACL 2024.
- **Method:** Encoder-decoder on state-space models (SSMs) for long-context text generation
- **Complexity:** O(L log L) vs O(L²) for standard attention
- **Quantified benefits:** 93–96% of sparse-Transformer quality; up to **50% memory savings during training**, **87% during inference**; handles inputs exceeding **600K tokens** at inference time
- **Hermes relevance:** SSM-based context layer could replace attention for long-session summarization/compression. Suggests Mamba/S4 as compute-efficient backend for the context compressor module.

### WikiFactDiff — Atomic Factual Knowledge Updates in LLMs
- **Authors:** Hichem Ammar Khodja, Frédéric Béchet, Quentin Brabant, Alexis Nasr, Gwénolé Lecorvé
- **Paper:** talnarchives.atala.org/TALN/TALN-2024/1281.pdf
- **Method:** Large realistic dataset for temporal knowledge updating — one fact at a time, without full retraining
- **Hermes relevance:** Pattern for incremental memory updates in an agent knowledge base; relevant to long-term memory refresh strategies

### Small Models Are Good — Zero-Shot Classification
- **Authors:** Pierre Lepagnol, Thomas Gerald, Sahar Ghannay, Christophe Servan, Sophie Rosset
- **Paper:** talnarchives.atala.org/TALN/TALN-2024/0636.pdf
- **Key finding:** Small models with proper prompting can match larger ones in zero-shot classification
- **Hermes relevance:** Validates model routing — Haiku-class models may suffice for classification sub-tasks in agent pipelines, avoiding Sonnet-class costs

### Translation Memory Augmentation (parallel to RAG)
- **Authors:** Maxime Bouthors, Josep Crego, François Yvon
- **Paper:** talnarchives.atala.org/TALN/TALN-2024/4837.pdf
- **Method:** Optimizing which prior translation examples to retrieve (analogous to RAG example selection)
- **Hermes relevance:** Example selection patterns transferable to RAG chunk selection strategies

---

## RUSSIAN — CyberLeninka (cyberleninka.ru)

Open access. Full text extractable via `web_extract`. eLibrary.ru requires login — skip it.

### RAG Accuracy Study (Borodulin 2024)
- **Author:** Боровулин И.В. / Borodulin I.V., Omsk State Technical University
- **Source:** Вестник науки (Journal of Science), 2024
- **URL:** cyberleninka.ru/article/n/uvelichenie-tochnosti-bolshih-yazykovyh-modeley-s-pomoschyu-rasshirennoy-poiskovoy-generatsii
- **Method:** GPT-3 with/without RAG on Q&A across multiple knowledge domains
- **Results (accuracy improvement with RAG):**
  | Domain | Δ accuracy |
  |--------|-----------|
  | Financial news | +35% |
  | Current events | +30% |
  | Scientific discoveries | +25% |
  | Medical/health | +26% |
  | Technology | +25% |
  | Geographic data | +15% |
  | Culture | +15% |
  | Historical facts | +10% |
- **Key insight:** RAG helps even for "stable" domains (historical facts +10%) — not just dynamic knowledge. Validates RAG investment broadly.
- **Assessment:** Applied practitioner level; confirms known methodology rather than advancing it. Useful empirical baseline for Russian-language applied AI research.

### LLM Knowledge Management Taxonomy (Zelenkov 2024)
- **Author:** Ю.А. Зеленков / Yu.A. Zelenkov, Graduate School of Business, HSE University Moscow
- **Source:** Российский журнал менеджмента / Russian Management Journal 22(3): 573–601, 2024
- **DOI:** 10.21638/spbu18.2024.309
- **URL:** cyberleninka.ru/article/n/upravlenie-znaniyami-organizatsii-i-bolshie-yazykovye-modeli
- **Method:** PRISMA systematic review of 75 papers (2020–2024) on LLMs in organizational knowledge management
- **Four-area taxonomy:**
  1. LLM implementation challenges (hallucination, staleness, cost, enterprise integration)
  2. Impact of LLMs on knowledge management efficiency
  3. LLMs in knowledge usage processes (retrieval, Q&A, search)
  4. LLMs in knowledge creation processes (documentation, synthesis, interpretation)
- **Key insight:** Distinguishes GenAI (new paradigm for unstructured creative/interpretive tasks) from classical ML (structured routine tasks). GenAI addresses the KM problems classical ML cannot.
- **Hermes relevance:** The four-area taxonomy is a useful scaffold for designing Hermes memory architecture — map each Hermes memory surface (session_search, Graphiti, qmd, durable memory) to one of the four areas.
- **Assessment:** HSE University is top-tier Russian institution. High-quality systematic review. Most rigorous Russian-language paper in this survey.

---

## UKRAINIAN — ACL Anthology UNLP Workshop + UA-LLM Project

### UNLP 2024 Shared Task on Fine-Tuning LLMs for Ukrainian
- **Authors:** Oleksiy Syvokon (Microsoft), Mariana Romanyshyn (Grammarly), Roman Kyslyi (KPI)
- **Source:** ACL Anthology: aclanthology.org/2024.unlp-1.9.pdf — Third UNLP Workshop @ LREC-COLING 2024, May 25, 2024
- **Task:** First shared task on fine-tuning open-weight LLMs for Ukrainian language
- **Models used:** Llama 2, Mistral 7B, Phi-2, Gemma, Aya 101 — open weights only
- **Constraint:** Must fit in 16GB GPU VRAM (no CPU offloading)
- **RAG explicitly encouraged** as complementary to fine-tuning
- **Evaluation:** ZNO (Ukrainian standardized exam) multiple-choice + human-rated open-ended generation
- **Key finding:** Multilingual base models underperform on Ukrainian without dedicated adaptation; fine-tuning + RAG together outperform either alone
- **Assessment:** Diaspora-driven research (Microsoft + Grammarly contributors). Demonstrates PEFT/LoRA under resource constraints.

### UA-LLM Project (uallm.org — NLPForUA)
Active 2024–2025 work on Ukrainian LLM infrastructure:
- **ZNO-Eval** (arXiv:2501.06715) — benchmark for LLM reasoning in Ukrainian using standardized exam questions
- **PEFT reasoning models** (arXiv:2503.13988) — LLaMA + Gemma with chain-of-thought for Ukrainian exam tasks; strong gains for compact models
- **DUMY dataset** — open step-by-step reasoning dataset for Ukrainian (March 2025)
- **UA-Code-Bench** — 500 competitive programming problems in Ukrainian; evaluates 13 LLMs
- **UA-LLM v1.0** — 20B parameter Ukrainian model in training (Q3 2025 target)
- **Key paper:** "UA-LLM: Advancing context-based question answering in Ukrainian through large language models" — Syromiatnikov & Ruvinskaya, Radio Electronics, Computer Science, Control, 2024
  - Semantic Scholar: b9194cf73bfa63aabe69532af6a58cee9e541872 (Semantic Scholar blocked scraping; access via UA-LLM website)

---

## Repository Access Quick Reference

| Repository | Language | Access | Method |
|---|---|---|---|
| talnarchives.atala.org | French | ✅ Open | Direct web_extract on PDF URLs |
| hal.science | French | ❌ Bot blocked | web_search site:hal.science for discovery only |
| cyberleninka.ru | Russian | ✅ Open | web_extract on article URLs; site: search works |
| eLibrary.ru | Russian | ❌ Login required | Skip; use CyberLeninka |
| aclanthology.org UNLP | Ukrainian | ✅ Open | Direct PDF extraction |
| uallm.org | Ukrainian | ✅ Open | Site indexes papers, links to arXiv |
| ela.kpi.ua | Ukrainian | ❌ No search | Skip |
| nbuv.gov.ua | Ukrainian | ❌ Not useful | Public interface doesn't return AI results |
| gi.de | German | ❌ Institutional | Skip; search arXiv for German-affiliated work instead |
| arxiv.org | German | ✅ Open | Use affiliation terms: "DFKI" OR "Fraunhofer" OR "Technische Universität" |

## Effective Non-English Query Terms

**Russian (CyberLeninka):**
- LLMs: `большие языковые модели`
- Memory management: `управление памятью`
- Agent: `агент`
- Multi-agent: `мультиагентная система`
- RAG: `расширенная поисковая генерация` or just `RAG`
- Optimization: `оптимизация`
- Context: `контекст`

**Ukrainian (UNLP/arXiv):**
- Language model: `мовна модель`
- AI agent: `штучний інтелект агент`
- Memory management: `управління памяттю`
- Optimization: `оптимізація`
- (Most Ukrainian AI research is in English; these terms useful for nbuv.gov.ua fallback)

**French (TALN/HAL):**
- Agent AI: `agent IA`
- Memory management: `gestion mémoire`
- Context compression: `compression contexte`
- Language model: `modèle de langage`
- Retrieval augmented generation: `génération augmentée par récupération`
