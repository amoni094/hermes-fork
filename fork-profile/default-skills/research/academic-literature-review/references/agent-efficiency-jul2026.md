# Agent Efficiency Research — July 2026 Delta Sweep
# English arXiv + multilingual (ZH/FR/RU/JP/KR)
# All papers verified via arXiv abs page or conference proceedings.
# For NeSy papers see: references/neurosymbolic-ai-research-2026.md
# For multilingual findings see: references/multilingual-agent-efficiency-sweep-jun-jul-2026.md
# Full master index: /var/home/rainbow/Documents/ai-agent-efficiency-research-2026.md

---

## Agent Memory

| arXiv | Title | Institution | Technique | Benefit | Hermes fit | Implemented |
|-------|-------|-------------|-----------|---------|-----------|-------------|
| 2607.01224 | AutoMem | Stanford | Two-loop: outer rewrites memory scaffold (prompts/schemas/vocab), inner trains memory specialist from own good decisions | 2-4× on Crafter/MiniHack/NetHack | HIGH — outer loop API-only | agent-memory-consolidation skill (AutoMem Pattern section) |
| 2607.09493 | Shared Selective Persistent Memory | — | 4-category selective persistence (task specs, data schemas, tool configs, output constraints); zero-token data refresh; RBAC sharing | 96% vs 79% task completion; 97× token reduction; 14× time reduction | HIGH | agent-memory-consolidation skill (4-Category Schema section) |
| 2607.05029 | FARMA/SENTINEL | Penn State | FARMA: poison reasoning traces via self-referential reinforcement (beats consensus). SENTINEL: 5 structural signals on reasoning provenance | SENTINEL 0% ASR vs 100% baseline | HIGH — defense | agent-memory-consolidation skill (Memory Security section) |
| 2607.06595 | GhostWriter/AM-Sentry | NM State | Two-phase injection+activation via tool-using agents; AM-Sentry: write-policy + retrieve-screen defense | ~98% injection rate baseline; AM-Sentry stops it | HIGH — defense | agent-memory-consolidation skill (Memory Security section) |
| 2605.30785 | AdaCoM | — | RL-trained external manager LLM edits frozen agent's context (delete/rewrite/merge); fidelity-reliability tradeoff: strong agent → preserve, weak → compress | Beats fixed-context baselines on web search | HIGH | hermes-context-hygiene skill (Pitfalls: fidelity tradeoff) |
| 2602.03315 | Memora | Microsoft | Harmonic dual-layer: abstraction + specificity, multi-hop retrieval | Long-horizon productivity gains | MEDIUM | Reference only |

## Multi-Agent Workflows

| arXiv | Title | Technique | Benefit | Hermes fit | Implemented |
|-------|-------|-----------|---------|-----------|-------------|
| 2607.11250 | MACE | Structured peer-selection POSG for capability inference between agents; value of exploration scales with agent diversity | Substantially improves coordination | HIGH — API wrapper | Reference; see autonomous-agent-loop-design |
| 2607.00269 | Mnemosyne/ATP | LLM proposals admitted only if they pass constraint set C; append-only log; local repair | <6% overhead; ~10× fewer repair ops; 0 invalid commits | HIGH | mnemosyne-atp-safety skill; verification-before-completion skill |
| 2606.17929 | PreAct | Compile successful agent runs to state machines; replay without LLM on repeat tasks | 8.5-13× speedup | VERY HIGH | preact-trajectory-compilation skill; autonomous-agent-loop-design skill |
| 2604.24881 | Latent Agents (ACL 2026) | Fine-tune multi-agent debate into single LLM; dynamic reward + length clipping | 93% token reduction vs explicit debate | MEDIUM (requires FT) | Reference only |

## LLM Routing

| arXiv | Title | Key Finding | Hermes fit | Implemented |
|-------|-------|-------------|-----------|-------------|
| 2601.07206 | LLMRouterBench (ACL 2026) | Commercial routers often ≤ simple baseline; main gap = model-recall failure (model reliably fails specific query types); large ensembles ≤ careful curation | HIGH | claude-routing-hierarchy skill (LLMRouterBench section) |
| 2603.04445 | Dynamic Routing Survey (Trinity/Huawei) | 3-dim taxonomy (when/what/how); well-designed routing outperforms best single model | HIGH — reference | claude-routing-hierarchy skill |

## Skill/Harness Optimization

| arXiv | Title | Technique | Benefit | Implemented |
|-------|-------|-----------|---------|-------------|
| 2607.05297 | MetaSkill-Evolve | Two-timescale: fast task-skill loop + slow meta-skill loop (improves improvement procedure itself). Five API-only pipeline agents. | +23.5pp OfficeQA, +16.1pp SealQA | self-improve-agent skill (MetaSkill-Evolve section) |
| 2607.08124 | TTHE (HKBU/Imperial) | Test-time harness evolution from unlabeled execution traces; no gold labels | Persistent improvement across SQL/code/tool-use | skillopt-continuous-improvement skill |
| 2607.12227 | Rethinking Harness Eval (UW/Allen) | Harness evolution ≠ consistent win over matched TTS baseline; benchmark overfitting real | HIGH — methodology | harness-first-agent-design skill (Harness Evolution Caveat) |
| 2607.14159 | MemoHarness (Notre Dame) | 6-dim harness decomposition (context/tools/orchestration/memory/decoding/output_handling) + dual-layer experience bank | Selective transfer to unseen suites | harness-first-agent-design skill; nesy.py LLMVerifier.memharness_decompose |

---

## Quick-Verdict Table (all verified)

| arXiv | Short name | Feasibility | Status |
|-------|-----------|-------------|--------|
| 2607.01224 | AutoMem | HIGH | Integrated in agent-memory-consolidation |
| 2607.09493 | Selective Persistent Memory | HIGH | Integrated |
| 2607.05029 | FARMA/SENTINEL | HIGH | Integrated |
| 2607.06595 | GhostWriter/AM-Sentry | HIGH | Integrated |
| 2605.30785 | AdaCoM | HIGH | Reference in context-hygiene |
| 2607.11250 | MACE | HIGH | Reference |
| 2607.00269 | Mnemosyne/ATP | HIGH | mnemosyne-atp-safety skill |
| 2606.17929 | PreAct | VERY HIGH | preact-trajectory-compilation skill |
| 2604.24881 | Latent Agents | MEDIUM | Reference |
| 2601.07206 | LLMRouterBench | HIGH | Routing skill |
| 2603.04445 | Dynamic Routing Survey | HIGH | Routing skill |
| 2607.05297 | MetaSkill-Evolve | HIGH | self-improve-agent skill |
| 2607.08124 | TTHE | HIGH | skillopt-continuous-improvement skill |
| 2607.12227 | Rethinking Harness Eval | HIGH | harness-first skill |
| 2607.14159 | MemoHarness | VERY HIGH | harness-first skill + nesy.py |
| 2607.05391 | LLM-as-a-Verifier | VERY HIGH | nesy.py LLMVerifier; verification skill |
| 2607.06341 | Aria code agent verif | VERY HIGH | Pattern in code review |
| 2603.00876 | BioProAgent FSM (95.6% vs 21.0%; 6× tokens) | HIGH | nesy.py FSMAgent; mnemosyne skill |
| 2607.05810 | SCOPE critique | HIGH | nesy.py LLMVerifier.scope_critique_prompt; code-review skill |
| 2604.07192 | Compact constraint headers | HIGH | nesy.py FSMAgent.compact_schema_prompt; context-hygiene |
| 2605.10279 | DeepLog (KU Leuven) | HIGH | pip candidate: github.com/ML-KULeuven/deeplog |
