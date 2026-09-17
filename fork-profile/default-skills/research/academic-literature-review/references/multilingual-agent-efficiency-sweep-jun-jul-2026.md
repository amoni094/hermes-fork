# Multilingual Agent Efficiency Sweep — June/July 2026

Delta sweep against known baselines (OScaR, MasRouter, SkillRL, ACON, CORIA-TALN 2025 AutoCluster, token pruning Zong/Piwowarski, Focus Agent, TEMA, Namiot/Ilyushin, DictSpec, Lapa-12B, GovTech RAG J1, Canvas-of-Thought, MRAgent, Δ-Mem, PPRO, TurboQuant).

## Quick-Reference Table

| arXiv / ID | Title | Lang track | Venue | Institution | Technique (1–2 sentences) | Quantified benefit | New vs. derivative |
|---|---|---|---|---|---|---|---|
| 2507.02259 | MemAgent | ZH | arXiv Jul 2026 | ByteDance Seed + Tsinghua AIR (SIA-Lab) | RL-trained memory agent reads text in segments, updates fixed-size memory buffer via overwrite strategy using extended DAPO algorithm for multi-conv generation | <5% degradation at 3.5M-token QA; 95%+ on 512K RULER | **Genuinely new** |
| 2508.07407 | Self-Evolving AI Agents Survey | ZH | IEEE Computational Intelligence Magazine | Multi-institution Chinese survey | Unified 4-component framework (System Inputs, Agent System, Environment, Optimizer) for self-evolving agents; classifies SkillRL as a skill-layer instantiation | Survey framework paper | Synthesis; derivative of English arXiv |
| TALN-2026/#15 | xLadder / "Oui à l'Échelle" | FR | CORIA-TALN 2026 | CNRS/LORIA | Extends Ladder Side-Tuning (LST) PEFT architecture by adding xLadder variant that deepens side network while shortening CoT; matches QLoRA scaling law slope at lower peak memory | Consumer-GPU fine-tuning viable; matches QLoRA perf on math tasks | **Genuinely new** |
| TALN-2026/#733466 | AutoBenchmark for Conversational Agents | FR | EvalLLM @ CORIA-TALN 2026 | French NLP community | Models agent execution space as weighted FSA transition graph, weights transitions with first-order Markov chain, hydrates sampled trajectories via real tool calls → automatic benchmark scenarios | 50 tasks / 6 tools (avg 5.7 calls); deployed on 10 agents, 60 tools | **Genuinely new** |
| TALN-2026/#30 | Sem-G-RAG | FR | CORIA-TALN 2026 | French NLP institutions | Integrates FrameNet semantic frames (Penman graph format) into RAG generation phase; entity-filtered semantic graphs don't degrade quality, opening optimization path | Entity-filtered graphs preserve quality; full FrameNet substitution degrades | **Original French-venue work** |
| TALN-2026/EvalLLM-Qwen | Parametric vs. Contextual Memory Conflict | FR | EvalLLM @ CORIA-TALN 2026 | De Bosschere, Lyonnais, Geliot | Quantifies conflict between LLM parametric memory and in-context RAG content using degradation metrics on Qwen3.5 family | Quantified unreliability when context overrides parametric beliefs | **New, direct RAG relevance** |
| CyberLeninka-Saratova | Coordination Process in LLM-Based MAS | RU | Экономика и качество систем связи 2026 | RTU MIREA (Saratova, Apukhtin) | Formal 4-tuple C=(T,M,U,S) coordination model; 2D architecture space parameterized by (centralization, adaptivity) unifies MARL, orchestration, decentralized evolutionary schemes | Theoretical framework — no benchmark numbers | **Original Russian formalism** |
| CyberLeninka-Malakhov | Goldfish Syndrome / 3-Tier Memory | RU | Экономика и качество систем связи 2026 | Povolzhsky State Univ. Telecomms, Samara | Argues context-only and RAG-only both fail for long-term agent memory; proposes Redis (hot) / ChromaDB (episodic vector) / files (cold) 3-tier with explicit write/retrieve control | Improved fact retention across sessions (qualitative) | Derivative engineering; independent documentation |
| IPSJ-KansaiBCSS11 | ANA+LLM Dynamic Network Construction | JP | IPSJ SIG Technical Report | Keio University | LLM auto-constructs Agent Network Architecture nodes using STRIPS-style Condition/Add/Delete lists; PageRank weights node priority; evaluated with GPT-4o | ~70% avg task success (window 66.7%, cup 71.4%, coffee 75.0%) | **Genuinely new** |
| IPSJ-2010057 | Dynamic Multi-Persona Policy Consensus | JP | IPSJ (DOI: 10.20729/...) Jun 29 2026 | Japanese (institution unspecified) | Multi-agent LLM with dynamic persona assignment (civil servant / researcher / citizen) for policy deliberation; personas shift based on emerging discussion state | Application result — no numeric efficiency metric | **Genuinely new JP application** |
| 2607.01224 | AutoMem | EN (surfaced ZH+KR) | arXiv Jul 1 2026 | Stanford (Wu, Zhu, Zhang, Wang, Yeung-Levy) | Dual-loop automated memory skill learning: outer loop uses meta-LLM to revise memory scaffold (prompts, file schemas, action vocabulary); inner loop fine-tunes dedicated memory specialist from agent's own good decisions. File-system ops promoted to first-class memory actions. | 2×–4× improvement on Crafter/MiniHack/NetHack; 32B open model approaches Claude Opus 4.5 / Gemini 3.1 Pro Thinking | **Genuinely new** |
| 2602.03315 | Memora | EN (surfaced KR) | Microsoft Research Feb 2026 | Microsoft | Harmonic memory representation decoupling content storage from retrieval indexing; multi-hop retrieval captures beyond semantic similarity | Long-horizon agent productivity improvement (no single metric) | New, surfaced by KR community |
| 2606.17929 | PreAct | EN (surfaced KR) | arXiv Jun 2026 | 19PINE-AI | Compiles successful agent runs into state-machine programs (conditions+transitions); replays directly on repeat without per-step LLM calls; screen-state verification triggers agent fallback on unexpected conditions | 8.5–13× speedup on repeated tasks | **Genuinely new technique** |
| 2604.24881 | Latent Agents | EN (surfaced KR) | ACL 2026 Main | Yi, Mueller, Lee | Two-stage fine-tuning distills multi-agent debate into single LLM; dynamic reward scheduling + length clipping for internalization; activation steering confirms agent-specific subspaces in activation space | Up to 93% fewer tokens, matches or exceeds explicit debate performance | Confirmed new |
| 2605.30785 | AdaCoM | EN (surfaced KR) | arXiv May 2026 | — | External manager LLM trained via RL to edit frozen agent's context (delete/rewrite/merge messages); preserves task constraints, removes noise; fidelity-reliability tradeoff: strong agents → preserve; weak → compress aggressively | Performance improvement on web search + deep research benchmarks | **Genuinely new** |
| KCC-2026-Tutorial | KVCache TensorMesh aiperf | KR | KCC 2026 Tutorial | tteon/Yitae Jeong (Korean community) | Tutorial operationalizing prefix caching for LLM serving: trace analysis → synthetic cluster construction → TensorMesh injection → aiperf profiling via cached_tokens and TTFT | Measured TTFT reduction via warm cached_tokens=1568 in live run | Engineering practice tutorial |

## Cross-Language Convergence Signals

| Technique | Tracks | Strength | Notes |
|---|---|---|---|
| Tiered / multi-level memory (hot/cold layers + explicit write gating) | ZH (MemAgent overwrite buffer), RU (Redis/ChromaDB/file 3-tier), JP (hot/cold Zenn), KR (Memora dual-layer) | **VERY STRONG** | Four independent communities converging on same architecture conclusion |
| Compilation/internalization of multi-agent behavior | KR (Latent Agents distillation), KR (PreAct state-machine compile), KR (subterranean agent weight-compiled) | **STRONG (KR-concentrated)** | Multiple papers via Korean community: externalize coordination → compile/internalize |
| Memory-as-learnable-skill | ZH+KR (AutoMem), JP (selective memory gating via Zenn), EN (AutoMem primary) | **MODERATE** | Independent articulation across Asian AI communities |
| LLM-driven dynamic agent network construction | JP (Keio ANA+LLM), RU (Saratova 4-tuple operator formalism), ZH (self-evolving survey topology dimension) | **MODERATE** | JP has concrete implementation; RU has theoretical formalism |

## Hermes Implementation Priority Ranking

1. **AutoMem (2607.01224)** — HIGHEST. Dual-loop automated memory optimization; 2×–4× gain. File-system-as-memory-action pattern directly implementable.
2. **PreAct (2606.17929)** — HIGH. 8.5–13× speedup on repeated tasks via state-machine replay. Apply to recurring Hermes workflows (CI checks, daily digests).
3. **AdaCoM (2605.30785)** — HIGH. External RL-trained context manager for frozen agents. No base-agent retraining required.
4. **MemAgent (2507.02259)** — HIGH for long-context tasks. Segmented read + fixed-size overwrite is a promptable workflow pattern.
5. **Latent Agents (2604.24881)** — MEDIUM. 93% token reduction if running repeated multi-agent debate patterns. Requires fine-tuning.
6. **xLadder / LST (FR TALN-2026/#15)** — MEDIUM for constrained-hardware fine-tuning. Lower peak GPU memory than QLoRA.
7. **Saratova 4-tuple coordination formalism (RU)** — LOW-MEDIUM. Vocabulary for evaluating Hermes MAS coordination architecture design.
8. **Sem-G-RAG (FR TALN-2026/#30)** — LOW-MEDIUM. FrameNet entity-filtered graph context is viable for experimentation.

## Source Database Notes (this sweep)

- **TALN 2026 (talnarchives.atala.org/TALN/TALN-2026/)**: ✅ Fully open, complete index + PDFs. Held June 29–July 3 2026, Nantes. EvalLLM workshop at same venue (talnarchives.atala.org/ateliers/2026/evalLLM/).
- **CyberLeninka (cyberleninka.ru)**: ✅ Open this sweep. Two relevant papers found via `site:cyberleninka.ru мультиагентная система LLM 2026` and `агент памяти LLM оптимизация 2026`.
- **mathnet.ru**: Searched — found LLM linguistic analysis only (verbal ellipsis in Trudy ISP RAS 2026), not relevant. No AI agent papers this sweep.
- **IPSJ (ipsj.ixsq.nii.ac.jp)**: ✅ Metadata/records open. ANA paper accessed as SIG Technical Report PDF (Kansai Branch BCSS-11 proceedings, open). Policy deliberation paper accessible via record page. Full IPSJ main conference papers paywalled.
- **PyTorchKR digest (discuss.pytorch.kr)**: ✅ OPEN, fully accessible. **KEY DISCOVERY: This is a high-signal Korean research curation channel.** Weekly AI/ML paper summaries in Korean, with detailed Korean-language explanations of English arXiv papers. The June 29–July 5 2026 digest (11092) surfaced AutoMem, Memora, PreAct, AdaCoM, MOSS, Latent Agents, SkillComposer. The June 1 week digest (sigco.tistory.com/692) surfaced Harness-1, AdaCoM, Latent Agents, MOSS, QKV variant attention, SISA attention. Both digests provide nuanced Korean-language interpretation not available elsewhere.
- **KCC 2026 (sub.kiise.or.kr/conference/2026/KCC/)**: Paper index accessible. Tutorial materials on GitHub (tteon/kcc2026-tutorial). Best paper was software engineering (bug reproduction test generation), not directly relevant.
- **RISS.kr**: Searched — no relevant LLM agent optimization papers in June–July 2026 window. GAP acknowledged.
- **Zenn.dev**: ✅ Open, Japanese practitioner community. Useful for engineering-practice consensus; not peer-reviewed research.
- **Qiita.com**: ✅ Open, Japanese developer community. Agent architecture articles surfaced (2026 MCP multi-agent design, March 2026 agent paradigm shift).

## GAPs

- Ukrainian track not swept (no search instructions for this session beyond baselines)
- RISS.kr: no relevant results for Jun–Jul 2026 window
- mathnet.ru: no AI agent papers found this sweep
- French HAL: bot-protected, no French-origin LLM agent papers beyond TALN 2026
- IPSJ full conference papers: subscription required (two-year embargo on SIG Technical Reports not in open-access set)

---

## Addendum — RAG Robustness + Multilingual RAG Delta Sweep (July 2026)

Scope: papers on RAG robustness to irrelevant/noisy context, multilingual RAG consistency,
and agent memory architecture taxonomy. Prompted by ret-robust (2310.01558) as a seed paper.
Full findings in references/rag-robustness-multilingual-memory-papers-2025-2026.md.

| arXiv / ID | Title | Track | Venue | Key Finding | New vs baseline |
|---|---|---|---|---|---|
| 2310.01558 | RetRobust (seed/origin) | EN | arXiv 2023 | NLI filter + 1K fine-tune; robust to irrelevant context | Baseline |
| 2606.13438 | CQC-RAG | EN | arXiv Jun 2026 | +4.76pp TriviaQA, +9.12pp MuSiQue via cross-query consistency | **Genuinely new** |
| 2506.00789 | RARE benchmark | EN | arXiv Jun 2025 | KG-driven 48K-question robustness benchmark; multi-hop worst | **Genuinely new** |
| 2601.06048 | Noise filtering inherently difficult | EN | arXiv Jan 2026 | Filtering can't fully solve noise — LLM must be intrinsically robust | **New** |
| 2504.00597 | mRAG Context Consistency | EN | MRL@EMNLP 2025 Best Paper | 48 langs; query-lang distractors exert slightly stronger negative effect | **Genuinely new** |
| 2603.04238 | Retrieval or Representation? | EN | ICLR 2026 Workshop | Representation/preprocessing > retrieval mechanism for multilingual gaps | **Genuinely new** |
| 2603.07670 | Memory for LLM Agents survey | EN | arXiv Mar 2026 | Write-manage-read loop; 3-axis taxonomy (temporal × substrate × control) | **New survey** |
| 2604.08224 | Externalization in LLM Agents | EN | arXiv Apr 2026 | Memory=state, Skills=procedure, Protocols=interaction, Harness=coordination | **New, validates Hermes architecture** |
| 2606.00610 | MemGraphRAG | EN | KDD 2026 | 3-layer Schema-Fact-Passage; ontology induction; conflict detection | **Genuinely new** |

### Non-English RAG Robustness Coverage (July 2026)
- Russian: GAP (CyberLeninka open; no independent Russian RAG robustness research — commentary only)
- French: COVERED from prior sweep (Qwen3.5 parametric-vs-contextual conflict paper at EvalLLM@TALN 2026 maps to this problem space)
- Korean/Japanese: GAP (EN monopolizes original RAG robustness research — topic-maturity gap, not access barrier)
- Cross-language convergence: WEAK. Non-English communities consume rather than produce independent RAG robustness findings.

### Priority Actions Added
- P1: Add CQC-RAG cross-query consistency step to Graphiti recall (prompt-only, API-compatible)
- P2: NLI pre-filter gate (RetRobust Method 1) before LLM generation in RAG pipelines (pip DeBERTa)
- P3: Representation-first principle for multilingual corpora (preprocessing > embedding model switch)
- P4: MemGraphRAG Schema-Fact-Passage pattern for Religion corpus conflict detection
