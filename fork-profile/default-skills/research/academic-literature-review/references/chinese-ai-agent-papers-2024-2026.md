# Chinese Institutional AI Agent Research — Paper Index (2024–2026)
*Compiled: July 2026 | Sweep by Hermes*

## 2026 refresh sweep (SerpApi, July 2026) — genuinely new since prior pass

### OScaR — Token Norm Imbalance fix for KV-cache quantization (arXiv:2605.19660)
Tsinghua, HKU, Edinburgh, UCAS, HK PolyU, Meituan LongCat team. Distinct from LLMLingua-2
(prompt-level compression) — this is numerical KV-cache quantization. Identifies "Token Norm
Imbalance" in channel-wise KV quantization; fixes via Hadamard channel rotation + omni-token
scaling. INT2 near-lossless (Qwen3-VL-8B OCRBench 856 vs 858 FP16); 3.0x decode speedup at 128K
context (92.9ms->30.9ms/token); 5x memory reduction, 4.1x throughput in batched serving.

### MasRouter — joint MAS-structure + role + model routing (arXiv:2502.11133, ACL 2025)
Tongji University + Ant Group (new institution beyond prior baseline). Cascaded controller
jointly decides collaboration mode + role allocation + per-role LLM routing, vs. routing LLM
choice alone. +3.51% avg accuracy over prior SOTA routers across 5 benchmarks; up to 52.07%
inference cost reduction. Relevant contrast to Hermes' current flat rule-based routing policy —
MasRouter routes *within* a multi-agent structure, closer to Hermes' delegate_task fan-out than
to single-model selection; worth revisiting if delegation patterns grow more complex.

### Skill-distillation-as-memory-replacement cluster (SkillRL / Skills-Coach / Skill-Pro / Skill1)
- **SkillRL** (arXiv:2602.08234): hierarchical "SkillBank" distilled from raw trajectories +
  adaptive retrieval + recursive co-evolution with RL policy. Outperforms baselines by >15.3% on
  ALFWorld/WebShop/7 search tasks; 7B model reportedly beats GPT-4o.
- **Skills-Coach** (arXiv:2604.27488, UCAS+ECNU+Southeast+Hainan+Tsinghua): training-free GRPO
  skill optimizer with 4 modules on new Skill-X benchmark (48 skills).
- Architectural angle: skill distillation *replaces* raw-trajectory memory (reduces token
  footprint) rather than optimizing memory retrieval. Distinct paradigm from Hermes' current
  skill model (hand-authored SKILL.md + curator patches) — not adopted (requires an RL training
  loop Hermes doesn't have), but flags the direction skill-optimization research is heading.

### Renmin University gist-token failure-mode taxonomy (arXiv:2412.17483, Renmin U Gaoling AI + Tencent AI Lab)
Newly surfaced this sweep (published Dec 2024). Catalogues 3 KV-cache/gist-token compression
failure modes: boundary effect, incidental-info loss, mid-sequence drift. Fine-grained KV-cache +
self-autoencoding + segment-wise token-importance estimation raises exact-recall accuracy
40.6%->62.0% at 4x compression. Complements (not replaces) existing LLMLingua-2/budget-hint
guidance — useful vocabulary for diagnosing *why* a compression pass degraded output.

### Checked, no new findings beyond known baseline
Agent memory *topology* specifically (structural/graph-based memory architecture) — searches
surfaced only re-hashes of memory-compression/KV-cache work above. Also flagged: an unconfirmed
Zhihu-only claim of 37% OOD failure rate in active-forgetting memory systems — no arXiv source
found to verify; noted as a risk signal, not a citable finding.

## Source Access Notes

| Source | Access | Notes |
|--------|--------|-------|
| arXiv (English, Chinese-authored) | ✅ Full text | Primary channel — all major papers |
| Chinese Journal of Computers (cjc.ict.ac.cn) | ✅ Open PDF | cjc.ict.ac.cn/EN |
| CCKS-IJCKG proceedings | ⚠️ Titles only | Paper list at sigkg.cn; full text Springer-paywalled |
| NLPCC proceedings | ⚠️ Titles only | Springer-paywalled |
| CNKI / Wanfang | ❌ Paywalled | No bypass; skip entirely |
| Shanghai AI Lab (shlab.org.cn) | ✅ Summary pages | News posts link to arXiv |
| GitHub (THUNLP, TsinghuaC3I, InternScience, antgroup) | ✅ Full | Repos with code + READMEs |

**Key finding:** Chinese-language-only papers are the rare exception. Virtually all significant Chinese institutional ML/NLP work has a parallel arXiv preprint.

---

## Quick-Reference Table

| arXiv ID | Short Name | Institution | Venue | Topic |
|----------|-----------|-------------|-------|-------|
| 2505.21471 | ExtAgents | Tsinghua THUNLP-MT + Alibaba DAMO | ACL 2026 | Multi-agent context extension |
| 2512.13564 | Agent Memory Taxonomy (FFD) | NUS, Renmin U, Fudan, PKU | Dec 2025 preprint | Memory forms-functions-dynamics |
| 2602.07848 | MARTI/MARS² | Tsinghua C3I | 2026 preprint | Multi-agent RL tree search |
| 2409.05591 | MemoRAG | Beihang/PKU-adjacent | 2024 preprint | Global memory RAG |
| 2510.11967 | Context-Folding | ByteDance | 2025 preprint | Context compression ~10× |
| 2510.00615 | ACON | Microsoft Research Asia (Chinese team) | ICML 2026 | Failure-driven context compression |
| 2507.21046 | Self-Evolving Survey (What/When/How) | Princeton, Tsinghua, CMU, SJTU | TMLR Jan 2026 | Self-evolving agent taxonomy |
| 2508.07407 | Self-Evolving Survey (4-component) | HIT, UK collaborators | Aug 2025 preprint | Self-evolving agent feedback loop |
| 2410.09342 | LLM×MapReduce V1 | Tsinghua THUNLP | ACL 2025 | Divide-and-conquer long-seq |
| 2504.05732 | LLM×MapReduce V2 | Tsinghua THUNLP | Apr 2025 preprint | Entropy-driven convolutional scaling |
| 2510.10890 | LLM×MapReduce V3 | Tsinghua THUNLP | EMNLP 2025 Demo | MCP-based modular survey agent |
| 2505.16938 | InternAgent | Shanghai AI Lab | May 2025 preprint | Closed-loop autonomous science |
| 2506.01939 | High-Entropy Token 80/20 | Alibaba Qwen + Tsinghua LeapLab | NeurIPS 2025 | Token entropy for RLVR |
| 2508.01186 | Agent Workflow Survey | Chinese university consortium | IEEE ICAIBD 2025 | Agent workflow taxonomy |
| 2505.19591 | Evolving Orchestration | Chinese university consortium | ACL Findings 2025 | Dynamic multi-agent orchestration |
| ICLR 2025 | OmniKV | AntGroup (Alibaba) + HIT | ICLR 2025 | KV cache optimization, 75% memory reduction |
| CJC Vol.49 No.2 2026 | BUPT RAG Survey | BUPT + CAS (Software/ICT institutes) | Chinese J. Computers Feb 2026 | 6-category RAG optimization |
| 2412.17483 | Gist Token Compression Failure Modes | Renmin University (Gaoling) + Tencent AI Lab | Dec 2024 preprint | KV-cache/recurrent gist-token compression, 3 failure modes |
| 2605.19660 | OScaR | Tsinghua, HKU, Edinburgh, UCAS, HK PolyU, Meituan LongCat | May 2026 preprint | INT2 KV-cache quantization via Token Norm Imbalance fix |
| 2502.11133 | MasRouter | Tongji University + Ant Group | ACL 2025 | Joint MAS collaboration-mode + role + LLM routing |
| 2602.08234 | SkillRL | Multi-author incl. UCSB | Feb 2026 preprint | Recursive skill-library RL (SkillBank) replacing raw-trajectory memory |
| 2604.27488 | Skills-Coach | UCAS + ECNU + Southeast U + Hainan U + Tsinghua | Apr 2026 preprint | Training-free GRPO skill optimizer, Skill-X benchmark (48 skills) |
| 2602.01869 | Skill-Pro | — | 2026 preprint | Reusable procedural skill learning from experience, no fine-tuning |
| 2605.06130 | Skill1 | — | 2026 preprint | Unified evolution of skill-augmented agents |
| 2601.14192 | Toward Efficient Agents (survey) | Mixed-author | 2026 preprint | Agent efficiency survey (memory/tool-learning/planning); critiques A-MEM forgetting-curve memory |

---

## Per-Paper Detail

### ExtAgents (arXiv:2505.21471)
- **Full title:** "Scaling External Knowledge Input Beyond Context Windows of LLMs via Multi-Agent Collaboration"
- **Authors:** THUNLP-MT (Zhiyuan Liu, Maosong Sun group) + Alibaba DAMO Academy
- **Venue:** ACL 2026
- **Core idea:** Distribute knowledge chunks across multiple agent instances; each agent summarizes its portion; master agent synthesizes with knowledge synchronization prompts. Handles corpora 10–100× any single model's context window.
- **Code:** github.com/THUNLP-MT/ExtAgents
- **Prompt templates (bilingual EN/ZH):** In paper — knowledge sync on first/subsequent iterations, ranking, knowledge-accumulating reasoning with/without termination
- **Feasibility for Hermes:** Medium — requires multi-agent dispatch; templates directly reusable

### Agent Memory Taxonomy — FFD Framework (arXiv:2512.13564)
- **Title:** Memory in the Age of AI Agents (approximate)
- **Authors:** NUS, Renmin University, Fudan, PKU — Dec 2025
- **Core contribution:** Forms-Functions-Dynamics framework
  - Forms: parametric, in-context, external/retrieval, in-cache
  - Functions: storage, retrieval, updating, forgetting
  - Dynamics: accumulation, consolidation, decay
- **Key insight:** Explicit *forgetting* and *decay* as design primitives, not just storage/retrieval
- **Feasibility for Hermes:** High — suggests adding TTL/staleness scoring to Graphiti facts

### MARTI/MARS² (arXiv:2602.07848)
- **Title:** Multi-Agent Reinforced Training and Inference with Self-Search Scaling
- **Authors:** TsinghuaC3I
- **Core idea:** RL-integrated tree search; centralized interaction + distributed policy training
- **Code:** github.com/TsinghuaC3I/MARTI

### MemoRAG (arXiv:2409.05591)
- **Core idea:** Two-memory architecture: lightweight global "clue" LM scans full document to formulate retrieval queries; standard retrieval memory for precise chunk recall
- **Why notable:** Solves "question requires global context to even formulate right retrieval query" problem
- **Feasibility for Hermes:** Medium — needs lightweight model as global scanner

### Context-Folding (arXiv:2510.11967)
- **Institution:** ByteDance
- **Core idea:** Context compression achieving ~10× efficiency gains
- **Feasibility for Hermes:** High — training-free compression

### ACON (arXiv:2510.00615)
- **Full title:** "ACON: Optimizing Context Compression for Long-horizon LLM Agents"
- **Authors:** Microsoft Research Asia (Chinese team)
- **Venue:** ICML 2026
- **Core idea:** Iterative refinement of compression guidelines from failure analysis; no fine-tuning; smaller distilled compressor
- **Results:** 26–54% peak token reduction; 46% task success improvement on smaller models
- **Benchmarks:** AppWorld, OfficeBench, Multi-objective QA
- **Code:** github.com/microsoft/acon
- **Feasibility for Hermes:** Very High — works with any LLM API; failure-analysis loop is a skill pattern

### Self-Evolving Agent Survey — What/When/How (arXiv:2507.21046)
- **Authors:** Huan-ang Gao (Princeton), Jiayi Geng, Wenyue Hua et al. — 27 authors, Princeton/Tsinghua/CMU/NUS/UIUC
- **Venue:** TMLR Jan 2026 (v4)
- **Framework:** What (models/memory/tools/arch), When (intra-test vs. inter-test time), How (scalar vs. textual feedback, single vs. multi-agent)
- **Key gap:** Inter-test-time evolution (persisting improvements across sessions) is understudied
- **Hermes relevance:** Skills + memory already implement inter-test-time evolution. Survey's "textual feedback as evolutionary signal" = skill patching on failure

### Self-Evolving Survey — 4-Component (arXiv:2508.07407)
- **Authors:** Jinyuan Fang, Yanwen Peng, Guibin Zhang, Zhaochun Ren (HIT) et al.
- **Framework:** System Inputs → Agent System → Environment → Optimisers feedback loop
- **Domain coverage:** Biomedicine, programming, finance evolution strategies
- **Key gap:** Safety/ethics during self-modification
- **GitHub:** github.com/EvoAgentX/Awesome-Self-Evolving-Agents

### LLM×MapReduce Series (Tsinghua THUNLP — Zhiyuan Liu, Maosong Sun group)

**V1 (arXiv:2410.09342) — ACL 2025**
- Divide-and-conquer: split → process chunks independently → aggregate
- Structured Information Protocol (inter-chunk dependencies) + In-context Confidence Calibration (inter-chunk conflicts)

**V2 (arXiv:2504.05732)**
- Entropy-driven convolutional test-time scaling
- Stacked "convolutional" layers progressively integrate local→global representations
- Powers SurveyGO online system

**V3 (arXiv:2510.10890) — EMNLP 2025 Demo**
- MCP-based modular architecture — each function (skeleton init, digest construction, refinement) is an independent MCP module
- Human-in-the-loop alignment; adaptive planning
- **Hermes relevance:** THUNLP independently chose MCP as the right architecture for composable survey generation — validation of Hermes's MCP-first approach

**Code:** github.com/thunlp/LLMxMapReduce

### InternAgent (arXiv:2505.16938)
- **Authors:** InternAgent Team — Bo Zhang, Wangli Ouyang, Bowen Zhou, Lei Bai + 21 others — Shanghai AI Lab
- **Core contribution:** Closed-loop autonomous scientific research across 12 task types
  - Loop: hypothesis → literature → experiment design → code gen → execution → result analysis → refinement
  - Human expert feedback integration at any stage
- **Results:** Reaction yield 27.6%→35.4% in 12h; enhancer activity 0.65→0.79 in 4h; 2D segmentation 78.8%→81.0% in 30h
- **Code:** github.com/Alpha-Innovator/InternAgent (formerly NovelSeek)
- **Hermes relevance:** Blueprint for a Hermes self-improvement loop: run task → measure → patch skill → re-run

### High-Entropy Token 80/20 Rule (arXiv:2506.01939)
- **Authors:** Shenzhi Wang, Le Yu + 16 others — Alibaba Qwen Team + Tsinghua LeapLab
- **Venue:** NeurIPS 2025
- **Core finding:** Only ~20% of CoT tokens are high-entropy "forking tokens" (genuine decision points). RLVR works by adjusting these, not the 80% filler.
- **Results:** Restricting policy gradient to forking tokens: Qwen3-32B +11.04 AIME'25 / +7.71 AIME'24 vs. full-gradient; Qwen3-14B +4.79/+5.21
- **Compression implication:** Entropy-aware compression should preserve high-entropy tokens specifically, not just length-prune

### OmniKV (ICLR 2025)
- **Authors:** Jitai Hao, Yuke Zhu, Tian Wang, Jun Yu, Xin Xin, Bo Zheng, Zhaochun Ren, Sheng Guo
- **Affil:** AntGroup (Alibaba subsidiary) + Harbin Institute of Technology (HIT)
- **Core technique:** Inter-layer attention similarity → identify "filter" layer whose attention pattern generalizes; other layers reuse that token selection. No token dropping — full KV retained, computation is selective.
- **Results:** 1.68× inference speedup; up to 75% KV cache memory reduction; zero performance loss
- **Code:** github.com/antgroup/OmniKV
- **Feasibility for Hermes:** Medium — requires vLLM/llama.cpp integration; not applicable to cloud APIs

### BUPT + CAS RAG Survey (Chinese Journal of Computers Vol.49 No.2, Feb 2026)
- **Title:** 大语言模型检索增强生成优化技术研究综述
- **Authors:** Yuan Le, Liu Shaohua et al. — BUPT + Institute of Software CAS + ICT CAS
- **DOI:** 10.11897/SP.J.1016.2026.00383
- **Access:** Open PDF at cjc.ict.ac.cn/EN
- **Six-category framework:**
  1. Pre-retrieval: query rewriting, expansion, decomposition
  2. Retriever: dense/sparse hybrid, cross-encoder reranking
  3. Retrieval Strategy: active/adaptive retrieval, iterative MCTS-based retrieval
  4. Index: hierarchical chunking, Meta-Chunking (arXiv:2410.12788), KG indexing
  5. Post-retrieval: RECOMP compression, reranking, noise filtering
  6. LLM Enhancement: FiD, attention tuning, context window management
- **Key call-out:** Meta-Chunking (2410.12788) — adaptive chunk sizing based on "logical perception" of sentence relationships
- **Agentic RAG examples cited:** DeerFlow (ByteDance), OpenAI DeepResearch, Google DeepResearch

### Agent Workflow Survey (arXiv:2508.01186)
- **Authors:** Chaojia Yu, Zihan Cheng et al. — Chinese university consortium
- **Venue:** IEEE ICAIBD 2025
- **Key taxonomy:** Static workflow (fixed DAG) vs. dynamic workflow (runtime-determined) — trend is dynamic
- **Covers:** 20+ systems across functional capabilities and architectural features

---

## July 2026 Delta Sweep — New Findings Beyond Baseline Above

Ran as an incremental sweep (see SKILL.md "Alternate output mode: incremental delta sweep against a known baseline") against the baseline in this same file. 5 of 6 topic axes yielded genuinely new material; agent memory *topology* specifically did not.

### Gist Token Compression Failure Modes (arXiv:2412.17483v1)
- **Authors:** Renmin University of China (Gaoling School of AI) + Tencent AI Lab
- **New institution** not previously in this file's Institutional Key Contacts.
- **Core idea:** Systematic comparison of gist-token context compression across 2 axes — storage location (recurrent/working-memory vs. KV-cache) × granularity (coarse per-segment vs. fine-grained multi-tag per-segment). Fine-grained KV-cache wins. Identifies 3 concrete failure modes: **boundary effect** (accuracy dips at the start of each new segment), **incidental-info loss** (facts phrased around an off-topic entity get dropped preferentially), **mid-sequence drift** (exact-recall accuracy decays the further into a token sequence you need to reproduce, e.g. 32-digit recall: 77.3%→52.5%→38.2% at 4/8/32 digits).
- **Fixes proposed:** fine-grained self-autoencoding (weak 1-layer decoder forces the gist token to be reconstructable) + segment-wise token-importance estimation (weight learning by how much a token's prediction depends on long-range vs. local context).
- **Quantified benefit:** Exact-recall accuracy 40.6%→62.0% (autoencoding) at 4× compression; complex-reasoning accuracy 41.3%→47.8% (boundary-effect fix).
- **Delta vs. baseline:** This is a distinct technique from LLMLingua-2 (prompt-level extractive compression) — targets KV-cache/recurrent gist-token architectures and is the first paper in this index to catalogue *why* compression fails task-by-task rather than just reporting an aggregate score.

### OScaR — KV-Cache Token Norm Imbalance fix (arXiv:2605.19660)
- **Institutions:** Tsinghua, HKU, University of Edinburgh, UCAS, HK PolyU, Meituan LongCat team
- **Core idea:** Identifies "Token Norm Imbalance" (TNI) as the real bottleneck in INT2 (2-bit) channel-wise KV-cache quantization — a few low-norm "attention sink" tokens get crushed by sharing a quantization scale with normal-norm tokens. Fixes with a 2-step pipeline: Hadamard channel rotation (spreads channel-level outliers evenly) then omni-token scaling (normalizes every token's L2 norm) — order matters, doing scaling first creates new outliers ("Scaling-Induced Outlier Artifact").
- **Quantified benefit:** Near-lossless at INT2 across text/multimodal/omni models (e.g. Qwen3-VL-8B OCRBench 856 vs. 858 FP16 baseline); 3.0× decode speedup at 128K context (92.9ms→30.9ms/token on H20 GPU); 5× memory reduction and 4.1× throughput in batched serving (48 concurrent conversations).
- **Delta vs. baseline:** Distinct axis from OmniKV (already in baseline — attention-similarity layer filtering, no token dropping) — OScaR is numerical quantization of the KV values themselves, a different mechanism on the same general KV-cache-efficiency topic. Not a re-report; judged novel on technique, not institution (Tsinghua/AntGroup-adjacent names already appear in baseline).

### MasRouter — joint MAS routing (arXiv:2502.11133, ACL 2025)
- **Institutions:** Tongji University + Ant Group (new institution: Tongji; Ant Group already known via OmniKV but this is a materially different technique)
- **Core idea:** Cascaded controller that jointly decides (1) collaboration mode — single-agent vs. multi-agent debate vs. workflow, (2) role allocation, and (3) per-role LLM routing — in one pipeline, vs. prior LLM routers that only pick the model for a single agent.
- **Quantified benefit:** +3.51% average accuracy over prior SOTA routing methods across 5 benchmarks; up to 52.07% inference cost reduction.
- **Delta vs. baseline:** No prior LLM-routing paper existed in this index at all — this is a new topic axis, not an extension of an existing one.

### Skill-library-as-memory-replacement cluster (SkillRL, Skills-Coach, Skill-Pro, Skill1)
- **SkillRL (arXiv:2602.08234):** multi-author team incl. UCSB. Hierarchical "SkillBank" distilled from raw interaction trajectories (rather than storing raw trajectories as memory) + adaptive retrieval + recursive co-evolution of skill library with RL policy. Result: outperforms strong baselines by >15.3% on ALFWorld/WebShop/7 search-augmented tasks; claims a 7B model can beat GPT-4o with skill accumulation. Code: github.com/aiming-lab/SkillRL.
- **Skills-Coach (arXiv:2604.27488):** UCAS + East China Normal University + Southeast University + Hainan University + Tsinghua. Training-free GRPO-based skill optimizer with 4 modules (diverse task generation, lightweight prompt/code optimization, comparative execution, traceable evaluation); introduces Skill-X benchmark (48 diverse skills). Reports "significant" gains across categories, no single headline percentage in the abstract — flagged as a vaguer quantification than SkillRL.
- **Skill-Pro (arXiv:2602.01869)** and **Skill1 (arXiv:2605.06130):** same technique family (reusable procedural skill learning from experience, without parameter updates) — noted as existing but not deep-dived this sweep; worth checking in a future pass if this cluster keeps growing.
- **Delta vs. baseline:** This is architecturally distinct from the memory-taxonomy (FFD) and MemoRAG entries already in the baseline — those treat memory as retrieval over stored experience; this cluster treats *distilled skills* as a compact replacement for storing raw trajectories at all, explicitly reducing token footprint as a side effect of the abstraction. New topic axis for "skill/tool optimization" specifically (as opposed to general agent memory).

### Toward Efficient Agents survey (arXiv:2601.14192) — pointer only, not a new empirical result
- Structures agent efficiency into memory / tool-learning / planning and explicitly critiques A-MEM's forgetting-curve memory management: reduces memory size/retrieval time but causes a "substantial drop in task performance." Useful as independent corroboration of the OOD-forgetting risk noted in the delta sweep, but contributes no new benchmark of its own — cite as a survey pointer, not as a standalone finding.

### Agent memory topology — checked, no new findings beyond known baseline
Searches for a distinct "memory topology" (graph-structured or hierarchical memory *architecture*, as opposed to memory *maintenance*/compression) turned up only re-hashes of the KV-cache/compression papers already covered above and in the existing FFD taxonomy entry. No new topology-specific paper emerged in the July 2026 delta sweep — report this explicitly in future sweeps rather than stretching a compression paper to cover the topology axis.

---

## Chinese-Language Search Terms for Future Sweeps

| Chinese | Pinyin | English |
|---------|--------|---------|
| 大语言模型 | dà yǔyán móxíng | LLM |
| 多智能体 | duō zhìnéngtǐ | Multi-agent |
| 检索增强生成 | jiǎnsuǒ zēngqiáng shēngchéng | RAG |
| 智能体记忆 | zhìnéngtǐ jìyì | Agent memory |
| 自进化 / 自我进化 | zì jìnhuà | Self-evolving |
| 上下文压缩 | shàngxiàwén yāsuō | Context compression |
| 知识图谱 | zhīshí túpǔ | Knowledge graph |
| 综述 | zōngshù | Survey / review |
| 智能体工作流 | zhìnéngtǐ gōngzuòliú | Agent workflow |
| Token优化 | — | Token optimization |
| 记忆维护 / 记忆遗忘 | jìyì wéihù / jìyì yíwàng | Memory maintenance / forgetting |
| 多智能体路由 / LLM路由 | — | Multi-agent / LLM routing |
| 技能优化 / 工具优化 | jìnéng yōuhuà / gōngjù yōuhuà | Skill / tool optimization |

## Institutional Key Contacts

| Institution | Lab/Group | Notable Work |
|-------------|-----------|--------------|
| Tsinghua THUNLP-MT | Zhiyuan Liu, Maosong Sun | ExtAgents, LLM×MapReduce series |
| Tsinghua C3I | — | MARTI/MARS² |
| Tsinghua LeapLab | — | High-entropy token NeurIPS 2025 |
| Tsinghua (general) | — | OScaR (KV-cache quantization, w/ HKU/Meituan LongCat) |
| Shanghai AI Lab | InternAgent Team | InternAgent, Intern-series |
| Peking University | — | Agent memory taxonomy (with Fudan/NUS/Renmin) |
| Fudan | — | Agent memory taxonomy |
| BUPT | Yuan Le, Liu Shaohua | Chinese Journal RAG survey 2026 |
| CAS Software Institute | — | RAG survey co-author |
| CAS ICT | — | RAG survey co-author |
| UCAS (Univ. of Chinese Academy of Sciences) | — | Skills-Coach (self-evolving skill optimizer) |
| AntGroup (Alibaba) | Zhaochun Ren group | OmniKV |
| HIT (Harbin IT) | Zhaochun Ren | OmniKV, self-evolving survey |
| Alibaba Qwen Team | — | High-entropy token paper |
| ByteDance | — | Context-Folding, DeerFlow |
| Microsoft Research Asia | — | ACON |
| NUS | — | Agent memory taxonomy |
| Renmin University | Gaoling School of AI | Agent memory taxonomy; gist-token compression failure modes (with Tencent AI Lab) |
| Tencent AI Lab | — | Gist-token compression failure modes (with Renmin U) |
| Tongji University | — | MasRouter (with Ant Group) |
| Meituan (LongCat team) | — | OScaR (with Tsinghua/HKU) |
| HKU / HK PolyU / U. Edinburgh | — | OScaR co-authors |
