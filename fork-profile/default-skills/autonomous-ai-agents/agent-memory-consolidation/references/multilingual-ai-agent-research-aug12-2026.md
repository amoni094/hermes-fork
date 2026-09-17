# Multilingual AI Agent Research Sweep — Aug 12, 2026
*New findings only; previous sweeps baseline excluded. Grouped by language/institution.*

---

## 🇨🇳 CHINESE-AFFILIATED RESEARCH

### 1. ATP-Bench — Qwen Applications (Alibaba)
- **Source**: https://arxiv.org/abs/2603.29902
- **Language/Institution**: English-primary but China-origin; Qwen Applications (Alibaba DAMO Academy)
- **Key Insight**: Introduces a 7,702-QA benchmark for *Agentic Tool Planning* in multimodal LLMs, where the model autonomously decides when, where, and which tools to invoke for interleaved text-image generation. Proposes a Multi-Agent MLLM-as-a-Judge (MAM) system that evaluates tool-call precision without requiring ground-truth references or re-execution.
- **English Summary**: 10 state-of-the-art MLLMs were tested on 25 visual-critical intents; all models showed significant gaps in coherent interleaved planning. The MAM judge identifies missed tool-use opportunities without ground-truth.
- **Hermes Relevance**: ★★★★ Direct analogue for Hermes tool-routing decisions. The MAM judge pattern (multi-agent evaluation of tool-call quality) could improve Hermes's skill-selection and tool-dispatch evaluation loops. The 25-intent taxonomy is a practical classification framework for agent tool invocation scenarios.

---

### 2. Do Agents Think Deeper? Layer-Wise Dynamics in Sequential Planning
- **Source**: https://arxiv.org/abs/2605.27935
- **Language/Institution**: English-primary; Chinese authors (Zhenyu Cui, Xiangzhong Luo)
- **Key Insight**: Mechanistic study of Qwen, GLM, and Minimax LLMs shows that agentic reasoning recruits progressively deeper layers across multi-turn trajectories, unlike static tasks—a construction-refinement gap where semantic direction forms early but deep layers stabilize outputs. Qwen shows a pronounced depth-utilization gap that grows with reasoning complexity.
- **English Summary**: Residual stream probes + causal layer-skipping across Deep Research, Code Generation, Tabular Processing trajectories; later turns show more long-range inter-layer dependencies and correction-dominant residual updates.
- **Hermes Relevance**: ★★★ Suggests that Hermes's multi-turn agent loops push LLMs into a qualitatively different compute regime. Understanding when deep-layer recruitment peaks could inform when to switch models (e.g., lighter model for early trajectory steps, heavier for recalibration turns).

---

### 3. CodeSpec — Dual Executable Specifications for Agentic Feature Development
- **Source**: https://arxiv.org/abs/2607.26777
- **Language/Institution**: English-primary; Chinese authors (Peiding Wang et al.)
- **Key Insight**: Proposes pairing sub-requirement semantics with repository architecture evidence to compile dual executable specifications—architecture spec (verifies chain completeness) + behavior spec (verifies design-implementation consistency)—for long-horizon code agent tasks. Achieves 70.7% pass rate on FeatureBench under DeepSeek-V4-Pro, outperforming Claude Code.
- **English Summary**: Free-form chain-of-thought reasoning for feature design yields incomplete functional chains; CodeSpec's evidence-grounded compilation reduces this by maintaining design-implementation invariants throughout 10+ step interactions.
- **Hermes Relevance**: ★★★★ Directly applicable to Hermes sub-agent coding tasks. The dual-spec pattern (architecture spec + behavior spec) is a concrete implementation of ISA/verification-before-completion workflows; the FeatureBench pass rates validate its superiority over current Claude Code baselines.

---

### 4. Salience Induction — Multi-Hop RAG Agent Attack & Defense
- **Source**: https://arxiv.org/abs/2607.17535
- **Language/Institution**: English-primary; Chinese authors (Xingfu Zhou et al.)
- **Key Insight**: Identifies a novel attack surface—the "salience channel"—where fact position, emphasis, framing, and semantic proximity redirect RAG agent reasoning even when all retrieved claims are factually true and no injected instructions exist. Under 30% edit budget, achieves 83.3% attack success rate across ReAct, Reflexion, and tool-calling agents including Qwen and DeepSeek.
- **English Summary**: Defines 6 Salience-Editing operator classes; proposes Salience Normalization as a lightweight input-side defense reducing ASR to 15.3%; introduces SalientWiki-MH benchmark for multi-hop evaluation.
- **Hermes Relevance**: ★★★★★ Critical for Hermes's Hindsight vector store and any RAG-augmented skill retrieval. Truthfulness + instruction-filtering alone are insufficient; Hermes should consider salience normalization as a pre-retrieval defense for tool-augmented contexts.

---

### 5. Uncertainty-Aware LLM Invocation Triggers (ECML PKDD 2026)
- **Source**: https://arxiv.org/abs/2607.13048
- **Language/Institution**: English-primary, European venue (ECML PKDD); author Zhaohui Wang (likely Chinese affiliation)
- **Key Insight**: Formalizes the "when to invoke LLM" problem as a risk-based sequential stopping problem, proving six theoretical results including O(√(T log T)) regret for stationary streams and a calibration-to-miss-rate transfer inequality. Anomaly-score-driven risk functions dominate alternatives by ~1 order of magnitude on Pareto AUC.
- **English Summary**: Unifies event-triggered, SPRT, CUSUM, and contextual bandit triggers under a single framework; empirically outperforms RouteLLM-style routers on turbofan degradation data with real LLM calls (92.9% grounding score on 1600 diagnoses).
- **Hermes Relevance**: ★★★★ Directly relevant to Hermes's model routing and when to escalate from lightweight to heavyweight models. The smooth-pasting optimality proof provides theoretical backing for threshold-based routing decisions.

---

## 🇰🇷 KOREAN AI RESEARCH

### 6. PICon — Persona Agent Consistency Evaluation (KAIST)
- **Source**: https://arxiv.org/abs/2603.25620
- **Language/Institution**: English-primary; KAIST (Korea Advanced Institute of Science and Technology), Edward Choi lab
- **Key Insight**: Applies interrogation methodology to evaluate persona agent consistency through logically chained multi-turn questioning across three dimensions: internal (self-contradiction-free), external (real-world fact alignment), and retest (stability under repetition). Even "highly consistent" systems fail the human baseline across all three dimensions under chained questioning.
- **English Summary**: 7 persona agent groups vs. 63 real human participants; LLM-based agents show evasive responses and logical contradictions not visible under single-turn evaluation. Framework available at https://kaist-edlab.github.io/picon/
- **Hermes Relevance**: ★★★★ Hermes's persona/role-playing mode could adopt PICon's three-dimensional consistency testing as a validation step in persona skill creation. The chained-questioning probe technique maps directly onto adversarial review of Hermes skill definitions.

---

### 7. Knowledge-Based Zero-Replay Debugging of Multi-Agent Traces (Korean)
- **Source**: https://arxiv.org/abs/2606.14805
- **Language/Institution**: English-primary; Korean authors (Dong Ho Kang, Hyeonjeong Cha, Daein Weon); submitted to Knowledge-Based Systems
- **Key Insight**: Frames multi-agent trace debugging as a zero-replay problem—predict which events a counterfactual replay oracle would mark high-effect without paying the replay cost. Compiles traces into event knowledge graphs over routing, memory, tool-use, uncertainty, and latent evidence; a gradient-boosted predictor raises Branch Recall@5 from 0.73 to 0.93 on held-out trace families.
- **English Summary**: 37 trace families tested; identifies when graph centrality suffices vs. when learned latent features are necessary; creates an auditable cost-efficiency frontier for AI-reliability debugging.
- **Hermes Relevance**: ★★★★★ Directly applicable to Hermes agent debugging and the Hindsight observability stack. The event KG schema (routing + memory + tool-use + uncertainty) matches Hermes's trace structure; zero-replay prediction at Branch Recall@5 = 0.93 would dramatically reduce debug overhead.

---

## 🇯🇵 JAPANESE AI RESEARCH

### 8. RIKEN AIP Natural Language Understanding Team — ACL 2026 Papers
- **Source**: https://aip.riken.jp/labs/goalorient_tech/nat_lang_understand/
- **Language/Institution**: Japanese institution (理化学研究所 革新知能統合研究センター); PI Kentaro Inui; JSAI 40th Anniversary Best Paper Award (July 2026)
- **Key Insight**: 21 papers accepted at ACL 2026, including work on interpretable/trustworthy NLP and new model architectures combining language understanding with mechanistic guarantees at multiple abstraction levels. Focus on "transparent, reliable, and grounded" AI systems rather than black-box improvement—an ergonomic research philosophy.
- **English Summary**: Team focuses on mechanistic guarantees for end users, domain experts, engineers, and scientists; close collaboration with educational AI industry partners. FY2025 research poster available in Japanese (PDF, includes NLP2025 award winners).
- **Hermes Relevance**: ★★ The interpretability-first design philosophy and multi-level abstraction stack for different user types is architecturally relevant to Hermes's skill system design. Worth monitoring ACL 2026 proceedings for specific agent-related papers from this team.

---

### 9. SCOPE — Edge LLM Agent with MoE Tool Routing (HRI 2026)
- **Source**: https://arxiv.org/abs/2606.02951
- **Language/Institution**: Accepted at HRI 2026 (Edinburgh); Qwen3/Moondream stack; edge-deployment focus
- **Key Insight**: Shows that Mixture-of-Experts models consistently match or exceed dense alternatives in both planning and perception at comparable latency and memory footprint for real-time edge deployment. Stronger SLMs (via Qwen3) substantially reduce tool-routing hallucinations; perception becomes the dominant bottleneck once SLM capability crosses a threshold.
- **English Summary**: 19 planner-perception combinations evaluated on 536-task PTZ camera control benchmark (QA, multi-step commands, spatial reasoning); MoE + quantization is the validated design point for edge agents.
- **Hermes Relevance**: ★★★ Validates MoE-based tool routing as a practical architecture (not just theoretical). For Hermes running on constrained hardware, quantized MoE planners with Qwen3-family SLMs are the validated efficient inference path.

---

## 🇵🇹 PORTUGUESE/IBERIAN AI RESEARCH

### 10. Long-Context Reasoning via On-Policy Optimization + Distillation (INESC-ID / Instituto Superior Técnico)
- **Source**: https://arxiv.org/abs/2605.12227
- **Language/Institution**: Portuguese-affiliated; Miguel Moura Ramos, Duarte M. Alves, André F. T. Martins (INESC-ID / IST Lisbon, Instituto de Telecomunicações)
- **Key Insight**: Combining GRPO (Group Relative Policy Optimization) with on-policy distillation—where the student learns from its own rollouts while a stronger teacher provides dense token-level regularization—outperforms either approach alone for long-context alignment. Introduces LongBlocks, a synthetic multilingual dataset spanning multi-hop reasoning, contextual grounding, and long-form generation.
- **English Summary**: Ablations isolate roles of cold-start initialization, teacher anchoring, and data mixing; the combined GRPO+OPD recipe is more stable than pure GRPO or pure OPD while preserving short-context capabilities.
- **Hermes Relevance**: ★★★ The GRPO+OPD recipe is applicable to fine-tuning Hermes's base model for long-horizon agentic trajectories. LongBlocks multilingual dataset (with multi-hop reasoning) is a directly usable resource for evaluating Hermes cross-language skill transfer.

---

## 🌍 MULTI-INSTITUTION / CROSS-REGIONAL

### 11. Innovation-Residual Auditing of Autonomous Analysis Agents
- **Source**: https://arxiv.org/abs/2608.05490
- **Language/Institution**: Ahmed Hassoon & Mark Dredze (Johns Hopkins); Aug 6, 2026
- **Key Insight**: Establishes a mathematical limit on what any agent audit can report: errors below a certain magnitude are indistinguishable from normal variation, and this limit falls so slowly with more training data that the representation dimensionality (not data volume) is the binding constraint. Provides FDR-controlling procedures for flagging operations that don't require a correctly-specified model.
- **English Summary**: Per-operation scoring by surprise relative to longer reconstruction (not just the immediately preceding step) is necessary to localize multi-step errors; single-step scoring hides inherited errors.
- **Hermes Relevance**: ★★★ Defines theoretical bounds for Hermes's Hindsight observability. The key finding—that representation dimension matters more than data volume for audit resolution—should inform Hermes's vector store embedding dimensionality choices.

---

### 12. Who Verifies the Benchmark? Decentralized LLM Evaluation Trust (QASC 2026)
- **Source**: https://arxiv.org/abs/2608.07762
- **Language/Institution**: Multi-institution; Sarvam M (Indian), GLM (Chinese), Qwen3 (Chinese), DeepSeek (Chinese) included as judges; QASC 2026
- **Key Insight**: Identity disclosure causes large score changes (GLM5.1: +7 points, p=0.025) for geopolitically sensitive topics in LLM-as-judge evaluation, while blockchain commit-reveal protocol creates a tamper-evident audit trail separating blind evaluation from post-hoc claims. Chinese LLM judges (GLM, Qwen, DeepSeek) show measurable identity-aware bias.
- **English Summary**: Tests 7 verifier models × 3 primary models on 58 questions; reveals that Chinese models' benchmark scores and evaluations carry systematic bias that standard academic reassessment doesn't correct.
- **Hermes Relevance**: ★★★ Relevant to Hermes's LLM-as-judge skill evaluation patterns. The commit-reveal protocol is a practical template for bias-resistant skill quality assessment; Chinese model judges should be used with awareness of identity-bias inflation.

---

## 📊 COVERAGE NOTES & GAPS

### Successfully Covered (New as of Aug 12, 2026):
- ✅ Qwen/Alibaba: ATP-Bench (tool planning benchmark), SCOPE MoE routing
- ✅ Chinese mechanistic interpretability: Layer-wise agentic depth study
- ✅ Chinese code agents: CodeSpec dual-spec framework
- ✅ Chinese security: Salience Induction RAG attack + defense
- ✅ Korean: KAIST PICon consistency evaluation, Korean multi-agent trace debugging
- ✅ Japanese: RIKEN AIP ACL 2026 outputs (interpretability-first)
- ✅ Portuguese (INESC-ID/IST): LongBlocks multilingual + GRPO+OPD recipe
- ✅ European venue (ECML PKDD): LLM invocation trigger theory

### Genuine Gaps (Not Found / Access Blocked):
- ❌ **NAVER AI Lab / HyperCLOVA X** 2026 papers: naver.com blocked, no fresh arXiv results accessible
- ❌ **LG AI Research (EXAONE)**: No accessible 2026 preprints found in this sweep
- ❌ **Max Planck Institute for Intelligent Systems**: No LLM agent papers found in accessible indices
- ❌ **TU Munich / Helmholtz AI**: No targeted agent papers found
- ❌ **MILA francophone preprints**: HAL-Inria agent papers not accessible (rate limits)
- ❌ **CNKI / Zhihu academic**: Not accessible from this environment
- ❌ **J-STAGE CS papers on agent systems**: Not queried (J-STAGE requires Japanese browser session)
- ❌ **Brazilian AI (USP, UNICAMP, Itaú AI Lab)**: No 2026 agent papers found in arXiv sweep; INESC-ID (Lisbon) covered as proxy for Lusophone research

### Access Constraints:
- SerpApi rate-limited (429) during this session—limited web search to ~4 calls
- ArXiv search endpoints blocked for query-string URLs; individual paper IDs worked fine
- NAVER Research blocked at network level
- CNKI/CNKI-China not accessible without institutional proxy

---

## 🔑 TOP ACTIONABLE INSIGHTS FOR HERMES

| Priority | Finding | Action |
|----------|---------|--------|
| P1 | Salience Induction (2607.17535) — truthfulness alone doesn't protect RAG agents | Add salience normalization pre-processing to Hermes skill retrieval |
| P1 | Zero-Replay Trace Debugging (2606.14805) — event KG enables 0.93 Branch Recall@5 | Model Hindsight observability layer on event KG schema |
| P2 | ATP-Bench MAM judge (2603.29902) — multi-agent tool-call evaluation without ground truth | Adopt MAM pattern for Hermes skill/tool quality assessment |
| P2 | CodeSpec dual spec (2607.26777) — architecture + behavior specs for agent feature dev | Use for Hermes sub-agent coding task scaffolding |
| P3 | KAIST PICon (2603.25620) — chained interrogation reveals consistency gaps | Use as validation protocol for Hermes persona/role skills |
| P3 | GRPO+OPD recipe (2605.12227) — stable long-context fine-tuning | Reference for any Hermes base model fine-tuning efforts |
| P4 | Layer-wise depth study (2605.27935) — agents recruit deeper layers over turns | Informs when to route to larger models in multi-turn sessions |
| P4 | MoE routing validated (2606.02951) — quantized MoE matches dense at lower cost | Validates Hermes efficiency path on constrained hardware |
