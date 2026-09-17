# Japanese & Korean AI Agent Research — Verified Paper Index 2024–2025
**Compiled:** 2026-07-04 via Hermes session  
**Topic:** Agent memory, RAG, LLM optimization, autonomous agents, context compression  
**Full synthesis saved to:** `/var/home/rainbow/japanese-korean-ai-agent-research-2024-2025.md`

## 2026 refresh sweep (SerpApi, July 2026) — genuinely new since prior pass

### Memory topology (new cluster — prior baseline had none dedicated to structure)
- **MRAgent** (arXiv:2606.06036, NUS, Jun 2026, surfaced via JP aib.vote): active memory
  *reconstruction* via a Cue-Tag-Content graph vs. static retrieve-then-reason. +23% on
  LoCoMo/LongMemEval; cuts token use & compute.
- **Δ-Mem** (arXiv:2605.12357, May 2026, surfaced via KR agent-hub.kr): frozen LLM backbone +
  tiny 8x8 online associative memory state, delta-rule updated, fed into attention as a low-rank
  correction. 1.10x avg score vs frozen backbone; 1.31x on MemoryAgentBench; 1.20x on LoCoMo.
- **PPRO** (arXiv:2607.00017, Baidu + U. Queensland, Jul 2026 — brand new, surfaced via KR
  alphaXiv translation): profile-guided personalized retrieval optimization — injects user
  profile into episodic/semantic memory retrieval ranking, trains query-rewriter via GRPO.
  +7 F1 over best baseline on LoCoMo (48.16 F1 w/ GPT-4o); 81.5% LLM-as-judge accuracy on
  LongMemEval-S. Relevant to Hermes' Hindsight+Graphiti stack, which does not currently do
  profile-conditioned retrieval ranking — worth revisiting if recall quality on personal-
  preference queries (memory/user profile) becomes an issue.

### Memory maintenance
- **AdMem** (arXiv:2606.06787, Jun 2026): unified store/organize/reuse memory framework
  targeting procedural-memory failure cases and online scalability gaps. Qualitative only.

### LLM routing
- **RouteBalance** (arXiv:2606.17949, Jun 2026, surfaced via a JP blog posted the day before this
  sweep): fuses model routing + serving-layer load balancing into one online assignment across
  concrete model instances, vs. optimizing routing and load-balancing in isolation. Not directly
  actionable for Hermes (single-provider-per-call routing, no instance-level load-balancer), but
  relevant if Hermes ever routes across multiple concurrent provider instances.

### Agent workflows / skill optimization
- **Lean4Agent** (arXiv:2606.06523, Jun 2026): formal specification/verification of agent
  workflow & trajectory vs. natural-language-only description. Framing paper, no headline metric.
- **Workflow-to-Skill** (arXiv:2606.06893, Jun 2026): auto-constructs reusable agent skills from
  heterogeneous traces via a routing-workflow-semantics-attachment decomposition. Conceptually
  close to Hermes' self-improve-agent skill-creation loop but automates trace-to-skill conversion
  rather than relying on an agent noticing "this should be a skill" — worth referencing if that
  skill's detection heuristics need sharpening.

### Non-technical / critical-studies finding
- **"기억의 공학적 합리성" (Engineering Rationality of Memory: A Critical Study on AI Agent Memory
  Design)** — Yoon Hana, Korean Association for Women's Communication, KCI journal (not arXiv).
  Humanities/critical lens on agent-memory design — not actionable, but flags that non-technical
  critique of agent memory exists in Korean discourse where English literature is almost
  entirely technical/benchmark-driven.

### Checked, no new findings beyond known baseline
Context compression/token optimization (ACON arXiv:2510.00615 resurfaced via a JP blog, already
inside known baseline window); self-improvement frameworks (Fujitsu EVE-Agent, Meta/UBC
DGM-Hyperagents — both already documented); CiNii direct search; RISS search (only the KCI item
above was new).

---

## Access Patterns (re-usable learnings)

### IPSJ Digital Library (ipsj.ixsq.nii.ac.jp)
- SIG Technical Reports and most symposium papers have a **~2-year embargo** from publication date
- Record pages (metadata) are always accessible; PDF download links visible but paywalled until embargo lifts
- Transactions (e.g., Transactions on Digital Practices = TDP) are often open-access — test PDF URL directly with web_extract
- Pattern for record URL: `https://ipsj.ixsq.nii.ac.jp/records/{id}` → metadata page
- Pattern for PDF URL: `https://ipsj.ixsq.nii.ac.jp/record/{id}/files/IPSJ-{code}.pdf` → may be open

### KIISE / DBpia (Korean)
- KIISE conference index: `http://sub.kiise.or.kr/conference/{year}/KSC/paper_index.asp?SHOW_PAGESIZE=20` — **fully public**, all paper titles + presenter names
- DBpia full text: subscription required; abstract + authors always visible
- DBpia node URL: `https://www.dbpia.co.kr/journal/articleDetail?nodeId=NODE{id}`
- UCI format: `I410-151-{yy}-{nn}-{nnnnnnnnn}`

### RISS (riss.kr — Korean government aggregator)
- Free text search; record detail pages accessible; full text requires institutional login
- Abstract (Korean) visible on record page — extract and translate in-context
- Cached detail pages available in `/var/home/rainbow/.hermes/cache/web/www.riss.kr-*.md`

### KoreaScience (koreascience.or.kr — KISS/KIPS journals)
- Partial open access for some journals — worth a direct web_extract attempt
- DOI format: `JAKO{year}{sequence}` (e.g., JAKO202430459949411)
- Direct URL: `https://koreascience.or.kr/article/{DOI}.pub`

---

## Verified Papers — Quick Index

| ID | Title (EN) | Authors | Venue | Date | Access | Key finding |
|----|-----------|---------|-------|------|--------|-------------|
| J1 | GovTech RAG: Development of RAG System for Government DX | Kawashima, Shiramatsu (NIT), Mizumoto (Hylable) | IPSJ TDP Vol.6 No.1 pp.12–22 | Jan 2025 | ✅ Open PDF | Temporal metadata pre-extraction; +40pp accuracy for novices; segment length × query type interaction |
| J2 | Preliminary Investigation on Personality Effects on LLM Software Engineering Agents | Tomoi, Ishimoto, Kondo (Kyushu U); Ubayashi (Waseda); Kamei (Kyushu U) | IPSJ SES 2024 pp.123–129 | Sep 2024 | 🔒 Embargo to 2026-09-10 | Big-5 personality prompting affects MetaGPT code quality; extroversion correlates positively |
| J3 | Cross-Lingual Code Knowledge Transfer via Continual Pre-Training | Sato, Soma, Kuramitsu (Japan Women's U) | IPSJ NL 2024-NL-261 No.13 pp.1–7 | Aug 2024 | 🔒 Embargo to 2026-08-27 | **Negative result**: English code knowledge does NOT transfer to Japanese via continual pre-training |
| J4 | LangMem: Long-Term Memory Overview and Usage | — | Mamezou Developer Site | Feb 26 2025 | ✅ Open | Three-tier memory (in-context/external store/parametric); async Memory Manager API |
| J5 | MemOS: Memory Operating System for LLMs | — | Zenn (annalaguna) | 2025 | ✅ Open | MemCube unified abstraction over parametric/context/KV cache memory; OS-metaphor scheduling |
| J6 | Canvas-of-Thought: Expanding Reasoning Canvas via Structural Reification | — | arXiv 2602.10494v1 | 2025 | ✅ Open | DOM-tree variable-state reasoning; named intermediate results; replaces flat scratchpad |
| K1 | Improving Multi-Hop QA with Hierarchical Multi-Agent RAG | Kim Se-hyeon (Soongsil U); Yoon Ji-won (Sookmyung W U) | KIISE KSC 2025 pp.1257–1259 | Dec 2025 | 🔒 DBpia | Manager-worker dynamic routing; per-worker generate-reflect-revise self-correction loop |
| K2 | RAG-Based Interview Question Quality Improvement | Jung Seung-won | KIISE KSC 2024 #424 (19A-P5.3-07) | Dec 2024 | 🔒 KIISE member | Domain RAG for HR; quality evaluation methodology |
| K3 | Framework for Self-Improving LLM Agents via Retrieval of Past Experiences | — | RISS 2024–2025 | 2024–2025 | 🔒 Institutional | Task-level RAG over agent's own history; failure experiences trigger re-retrieval with adjusted queries |
| K4 | KG-RAG for Korean Regulatory Documents | — | RISS 2024–2025 | 2024–2025 | 🔒 Institutional | KG construction from legislative text; citation-chain traversal; reduces hallucinated legal citations |
| K5 | Survey on Latest Research Trends in RAG Technology | — | J. Korea Information Processing Society | 2024 | ✅ Partial (KoreaScience) | Architecture, optimization, evaluation, industrial deployment; Korean practitioner synthesis |
| K6 | TurboQuant: Efficient KV Cache Compression | KAIST (Prof. Han In-soo), Google Research, DeepMind, NYU | arXiv (TBD) / news | Mar 24 2025 | ✅ News confirmed | 6× KV compression; 8× throughput; PolarQuant (polar-coord keys) + QJL (1-bit JL value compression); no fine-tuning; evaluated on LongBench, NIAH, ZeroSCROLLS, RULER, L-Eval |

---

## Novel Contributions vs. English arXiv Literature

These findings were NOT present in the prior English-language arXiv pass as of July 2026:

1. **Temporal metadata pre-extraction for RAG** (J1) — LLM pre-pass to extract date/version facts as metadata before embedding. Validated at production scale (Aichi Prefecture).

2. **PolarQuant polar-coordinate key transformation** (K6) — Quantizing attention keys in polar (magnitude + angle) rather than Cartesian space. Enables asymmetric bit allocation. Geometrically novel vs. H2O, SnapKV, KIVI.

3. **Per-agent Big-5 personality prompting** (J2) — Empirical study of psychological personality traits on MetaGPT multi-agent coordination. Bridges org-psychology + LLM agents.

4. **MemCube unified memory abstraction** (J5/MemOS) — Single API over parametric weights, context window, and KV cache. More architectural than Mem0 or LangMem which address one tier.

5. **Per-worker generate-reflect-revise loop** (K1) — Self-correction at the individual worker-agent level (not top-level system reflection). More granular than Self-RAG and standard reflection architectures.

6. **Negative cross-lingual code transfer result** (J3) — Sequential continual pre-training in Japanese does not transfer English code knowledge. Informs multilingual LLM development methodology.

---

## Search Term Banks

### Japanese (use with site:ipsj.ixsq.nii.ac.jp or general web_search)
| Japanese | English |
|----------|---------|
| エージェントメモリ管理 | agent memory management |
| RAG検索拡張生成 | RAG / retrieval-augmented generation |
| マルチエージェント協調 | multi-agent coordination |
| LLMトークン最適化 | LLM token optimization |
| コンテキスト圧縮 | context compression |
| 自律エージェント | autonomous agent |
| 自己改善 | self-improvement |
| 長期記憶 | long-term memory |
| 記憶管理 | memory management |
| 大規模言語モデル | large language model (LLM) |

### Korean (use with site:riss.kr or general web_search)
| Korean | English |
|--------|---------|
| AI 에이전트 메모리 관리 | AI agent memory management |
| RAG 검색 증강 생성 | RAG / retrieval-augmented generation |
| LLM 토큰 최적화 | LLM token optimization |
| 컨텍스트 압축 | context compression |
| 자율 에이전트 | autonomous agent |
| 자기 개선 | self-improvement |
| 계층적 다중 에이전트 | hierarchical multi-agent |
| 지식 그래프 | knowledge graph |
| 대규모언어모델 | large language model (LLM) |
| 자기 보정 루프 | self-correction loop |

---

## Practitioner Community Sources (Japan)

Beyond peer-reviewed venues, the Japanese practitioner community synthesises cutting-edge ML research quickly:

| Site | Type | Notable for |
|------|------|-------------|
| zenn.dev | Dev blog platform | Early LangMem/MemOS writeups; often more technically detailed than English Medium posts |
| qiita.com | Dev blog platform | LLM implementation how-tos; search `#LLM` tag |
| developer.mamezou-tech.com | Company dev blog | Systematic framework overviews (LangMem, LangGraph); Mamezou is a large Japanese SI firm |
| alphaXiv | arXiv commentary | Japanese authors discussing arXiv papers; good for finding relevant papers by topic context |
