# Multilingual AI Agent Research — Aug 12, 2026 Delta Sweep

Non-English-first / non-Anglophone-institution papers on AI agents, missed by main
English arXiv sweeps. Complements `agent-runtime-aug2026-sweep.md`. Each entry:
source URL, institution, key insight (≤2 sentences), Hermes relevance tier.

---

## 🇨🇳 CHINESE / ALIBABA-AFFILIATED

### ATP-Bench — Multimodal Agentic Tool Planning Benchmark
- **URL**: https://arxiv.org/abs/2603.29902
- **Institution**: Alibaba DAMO Academy / Qwen Applications
- **Key Insight**: 7,702-QA benchmark for when/where/which tool to invoke in multimodal interleaved generation. Proposes Multi-Agent MLLM-as-a-Judge (MAM) that evaluates tool-call quality without ground-truth references or re-execution.
- **Hermes Relevance**: ★★★★ MAM pattern → Hermes skill/tool quality assessment without ground truth; 25-intent taxonomy → classification framework for Hermes tool-dispatch.

### Layer-Wise Agentic Depth (Qwen/GLM/Minimax)
- **URL**: https://arxiv.org/abs/2605.27935
- **Institution**: Chinese authors (Zhenyu Cui, Xiangzhong Luo)
- **Key Insight**: Agentic reasoning recruits progressively deeper layers as trajectories unfold; Qwen shows a pronounced construction-refinement gap. Residual updates shift from feature accumulation to correction-dominant.
- **Hermes Relevance**: ★★★ Multi-turn agent loops push LLMs into a qualitatively different compute regime — later trajectory turns warrant routing to higher-capacity models.

### CodeSpec — Dual Executable Specifications for Code Agents
- **URL**: https://arxiv.org/abs/2607.26777
- **Institution**: Chinese authors (Peiding Wang et al.)
- **Key Insight**: Pairs sub-requirement semantics with repository architecture evidence to compile architecture + behavior specs enforcing design-implementation consistency throughout long-horizon feature development. Achieves 70.7% FeatureBench pass rate (DeepSeek-V4-Pro), outperforming Claude Code.
- **Hermes Relevance**: ★★★★ Use dual-spec pattern for Hermes sub-agent coding tasks; directly improves ISA/verification-before-completion workflows.

### Salience Induction — RAG Attack & Defense (Qwen/DeepSeek victims)
- **URL**: https://arxiv.org/abs/2607.17535
- **Institution**: Chinese authors (Xingfu Zhou et al.)
- **Key Insight**: Manipulating fact *position, emphasis, framing, proximity* (not content) redirects RAG agent reasoning with 83.3% ASR — no injected instructions needed, all retrieved facts remain true. Salience Normalization as input-side defense cuts ASR to 15.3%.
- **Hermes Relevance**: ★★★★★ **P1 for Hermes Hindsight/RAG**: truthfulness + instruction-filtering insufficient. Add salience normalization pre-processing to skill retrieval and tool-context injection.
- **Benchmark**: SalientWiki-MH (multi-hop)

### SCOPE — Edge MoE Agent (Qwen3-based, HRI 2026)
- **URL**: https://arxiv.org/abs/2606.02951
- **Institution**: HRI 2026; Qwen3/Moondream stack
- **Key Insight**: MoE models consistently match dense alternatives at comparable latency and memory footprint for edge agents; quantized Qwen3 substantially reduces tool-routing hallucinations. Perception, not planning, becomes the bottleneck once SLM capability crosses a threshold.
- **Hermes Relevance**: ★★★ Validates quantized MoE + Qwen3 as the efficiency path for Hermes on constrained hardware. 19 planner-perception combos on 536-task PTZ benchmark.

---

## 🇰🇷 KOREAN AI RESEARCH

### PICon — Persona Agent Consistency Evaluation (KAIST)
- **URL**: https://arxiv.org/abs/2603.25620
- **Institution**: KAIST (Korea Advanced Institute of Science and Technology), EdLab
- **Key Insight**: Applies interrogation methodology (logically chained multi-turn questioning) to probe persona agents across 3 dimensions: internal consistency, external consistency, retest consistency. All LLM-based persona agents fail the human baseline; contradictions and evasive responses emerge only under chained questioning.
- **Hermes Relevance**: ★★★★ Use PICon's three-dimensional probe as validation protocol for Hermes persona/role skills. Demo: https://kaist-edlab.github.io/picon/

### Zero-Replay Multi-Agent Trace Debugging
- **URL**: https://arxiv.org/abs/2606.14805
- **Institution**: Korean authors (Dong Ho Kang, Hyeonjeong Cha, Daein Weon); Knowledge-Based Systems
- **Key Insight**: Compiles multi-agent traces into event knowledge graphs (routing + memory + tool-use + uncertainty + latent evidence); a gradient-boosted predictor identifies high-effect counterfactual branches without replay. Branch Recall@5 rises from 0.73 → 0.93 across 37 trace families.
- **Hermes Relevance**: ★★★★★ **P1 for Hermes Hindsight observability**: event KG schema matches Hermes trace structure; zero-replay debugging at 0.93 recall would dramatically reduce debug overhead.

---

## 🇯🇵 JAPANESE AI RESEARCH

### RIKEN AIP Natural Language Understanding Team — ACL 2026
- **URL**: https://aip.riken.jp/labs/goalorient_tech/nat_lang_understand/
- **Institution**: RIKEN AIP (理化学研究所 革新知能統合研究センター), PI Kentaro Inui; JSAI Best Paper July 2026
- **Key Insight**: 21 ACL 2026 papers from this team. Design philosophy is "transparent, reliable, grounded AI" — mechanistic guarantees at multiple abstraction levels for different user types (end users, domain experts, engineers, scientists).
- **Hermes Relevance**: ★★ Multi-level abstraction stack for different user types → architecturally relevant to Hermes skill system design for different consumer profiles.

---

## 🇵🇹 PORTUGUESE / IBERIAN AI

### GRPO + On-Policy Distillation for Long-Context Alignment (INESC-ID / IST Lisbon)
- **URL**: https://arxiv.org/abs/2605.12227
- **Institution**: INESC-ID, Instituto Superior Técnico Lisbon (Miguel Moura Ramos, Duarte M. Alves, André F. T. Martins)
- **Key Insight**: Combining GRPO with on-policy distillation (student learns from own rollouts + teacher provides dense token-level regularization) outperforms either approach alone for long-horizon alignment. Introduces LongBlocks synthetic multilingual dataset covering multi-hop reasoning, contextual grounding, long-form generation.
- **Hermes Relevance**: ★★★ GRPO+OPD recipe directly applicable to fine-tuning Hermes base model for long-horizon agentic trajectories. LongBlocks is a usable multilingual evaluation resource.

---

## 🌍 MULTI-INSTITUTION / CROSS-REGIONAL

### Innovation-Residual Audit Bounds for Autonomous Agents
- **URL**: https://arxiv.org/abs/2608.05490
- **Institution**: Johns Hopkins (Ahmed Hassoon, Mark Dredze)
- **Key Insight**: Errors below a threshold magnitude are indistinguishable from normal variation; this threshold falls slowly with data so *representation dimensionality* (not data volume) is the binding audit constraint. Per-operation scoring by surprise relative to longer reconstruction (not just preceding step) is required to localize multi-step errors.
- **Hermes Relevance**: ★★★ Defines theoretical bounds for Hermes Hindsight observability. Embedding dimensionality choices matter more than ingestion volume for audit resolution.

### Decentralized LLM Evaluation Trust + Chinese Judge Bias (QASC 2026)
- **URL**: https://arxiv.org/abs/2608.07762
- **Institution**: Multi-institution; Sarvam (India), GLM/Qwen/DeepSeek (China) as judges; QASC 2026
- **Key Insight**: Identity disclosure causes large score changes (GLM5.1: +7 pts, p=0.025) for geopolitically sensitive topics; blockchain commit-reveal protocol creates a tamper-evident audit trail separating blind evaluation from post-hoc claims. Chinese LLM judges show measurable identity-aware bias.
- **Hermes Relevance**: ★★★ Chinese model judges (GLM, Qwen, DeepSeek) carry systematic evaluation bias. Commit-reveal protocol is a practical template for bias-resistant Hermes skill quality assessment.

### LLM Invocation Trigger Theory — ECML PKDD 2026
- **URL**: https://arxiv.org/abs/2607.13048
- **Institution**: ECML PKDD 2026; author Zhaohui Wang
- **Key Insight**: Formalizes when-to-invoke-LLM as a risk-based sequential stopping problem; proves O(√T log T) regret for stationary streams and smooth-pasting optimality of threshold policies. Anomaly-score-driven risk functions dominate RouteLLM-style routers by ~1 order of magnitude on Pareto AUC.
- **Hermes Relevance**: ★★★★ Theoretical foundation for Hermes model routing. Threshold-based trigger policies have proven optimality; anomaly-score risk > classifier-based routing in empirical tests.

---

## ACCESS CONSTRAINTS DISCOVERED (Durable for future sweeps)

| Institution/Source | Access Status | Workaround |
|---|---|---|
| NAVER research.naver.com | Blocked at network level | Use arXiv author affiliation search ("NAVER" in author field) |
| CNKI (Chinese academic) | Requires institutional proxy | Search arXiv with Chinese institution name filter instead |
| J-STAGE (Japanese) | Requires Japanese browser locale for some content | Use web_extract on direct paper URLs; search with `site:jstage.jst.go.jp` |
| LG AI Research (EXAONE) | No 2026 arXiv preprints found | Search `EXAONE site:arxiv.org` periodically |
| HAL-Inria | Rate-limited during sweep | Use `hal.science` direct search + `web_extract` on HAL IDs |
| SerpApi (web_search) | 429 rate limit after ~4 calls/session | Fall back to direct arXiv ID extraction; batch extracts 5 IDs/call |

## TECHNIQUE: arXiv-ID Direct Extraction (Rate-Limit Fallback)

When `web_search` is 429-blocked, known arXiv IDs can still be extracted directly:
```python
# Batch up to 5 IDs per web_extract call
web_extract(urls=[
    "https://arxiv.org/abs/2603.29902",
    "https://arxiv.org/abs/2607.17535",
    "https://arxiv.org/abs/2605.27935",
    "https://arxiv.org/abs/2603.25620",
    "https://arxiv.org/abs/2607.13048"
])
```
Source IDs: use arXiv listing pages (`arxiv.org/list/cs.AI/current`) fetched in prior turns, or seed from known institution-filtered queries done early in the session before rate limits hit. The `arXiv category listing walk` technique from llm-agent-memory-pipeline-research SKILL.md recovers ~70% of recent papers.

## GAPS FOR FUTURE SWEEPS

- NAVER AI Lab / HyperCLOVA X 2026 agent papers (blocked)
- LG AI Research EXAONE 2026 publications
- Max Planck Institute for Intelligent Systems LLM papers
- TU Munich / Helmholtz AI 2026 papers
- MILA francophone HAL preprints (French-primary)
- Brazilian AI: USP, UNICAMP, Itaú AI Lab (no 2026 agent arXiv papers found)
- Samsung Research AI agent papers
