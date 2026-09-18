# Neurosymbolic AI: Reference Index (July 2026)

## Canonical source
Full survey: /var/home/rainbow/Documents/neurosymbolic-ai-research-2026.md (26KB, 418 lines)
Library:     /var/home/rainbow/Documents/neurosymbolic/nesy.py (unified, self-testing)

## Installed packages (Python 3.14.6)
- z3-solver 5.0.0.0   — fully working; SMT solver for constraint checking
- pyreason 3.6.0       — installed; cannot import on Py3.14 (pkg_resources removed from setuptools)
                        GraphReasoner in nesy.py reimplements the same forward-chaining logic
- outlines 0.1.14      — installed (--no-deps); requires torch for neural backend (no GPU)
                        ConstrainedOutput.validate() in nesy.py is the CPU-only equivalent
- networkx 3.6.1       — fully working; graph inference substrate

## nesy.py API (import from /var/home/rainbow/Documents/neurosymbolic/nesy.py)
All 6 classes verified: `python3 /var/home/rainbow/Documents/neurosymbolic/nesy.py`

| Class | Basis | Key methods |
|-------|-------|-------------|
| `SymbolicVerifier` | Z3 SMT solver | `make_int/bool`, `check_integer_constraints`, `verify_postcondition` |
| `GraphReasoner` | networkx forward-chaining | `load_from_llm_output`, `risk_report` |
| `ConstrainedOutput` | Pydantic + PAL | `validate(data, Schema)`, `execute_pal(code)` |
| `CodingVerifier` | Forethought+Progent+SkillOpt | `run_pal`, `verify_spec`, `audit_dependencies`, `score_code_change` |
| `LLMVerifier` | LLM-as-a-Verifier 2607.05391 | `build_criterion_prompt`, `aggregate_scores`, `scope_critique_prompt`, `memharness_decompose` |
| `FSMAgent` | BioProAgent 2603.00876 | `design_verify_rectify()`, `read_verify_write()`, `compact_schema_prompt` |

### New NeSy papers (July 2026 sweep)

| arXiv | Name | Metric | nesy.py integration |
|-------|------|--------|---------------------|
| 2607.05391 | LLM-as-a-Verifier (Stanford/UCB) | SWE-Bench 78.2% SOTA | `LLMVerifier` class |
| 2607.06341 | Aria code agent verif (Claude Code) | 4257/4257 Iris lemmas | Pattern: harness → soundness gate |
| 2603.00876 | BioProAgent FSM (ACL 2026 Oral, PKU) | 95.6% vs 21.0%; 6× token reduction | `FSMAgent` class |
| 2605.16829 | CDC Constrained Diffusion for Code (UVA) | Training-free; beats baselines | Compatible with `ConstrainedOutput` |
| 2603.18495 | NeSyCR cross-domain code (CVPR 2026, SKK Univ) | +31.14% task success | Counterfactual check pattern |
| 2607.05810 | SCOPE subgoal critique (Vanderbilt) | 39.4% LiveCodeBench vs 36.6% Reflexion | `LLMVerifier.scope_critique_prompt` |
| 2604.07192 | Compact constraint headers (Tang) | 71% token reduction, no CSR loss | `FSMAgent.compact_schema_prompt` |
| 2605.10279 | DeepLog NeSy framework (KU Leuven IJCAI) | Beats LTN+DeepProbLog | pip: github.com/ML-KULeuven/deeplog |
| 2603.19715 | NeSy proof gen seL4 (OSDI 2026, NJU/ETH) | 77.6% seL4 theorems | Architecture reference |

## Key papers (see full survey for details)
- arXiv:2508.13678  IJCAI 2025 survey: NeSy for LLM Reasoning
- arXiv:2501.05435  Systematic review: 167/1428 papers; 28% address explainability (largest gap)
- arXiv:2502.03544  AlphaGeometry2: 84% IMO geometry solve rate
- arXiv:2607.04096  Forethought: ~30% accuracy gain, 3 OOM less compute than frontier
- arXiv:2606.30613  SPARK robotics: 43.7% vs 18.2% baseline
- arXiv:2606.20895  αNeSy-CTM: +30% clinical trial matching
- arXiv:2604.26521  iLTN: symbol grounding alone ≠ compositional generalization
- arXiv:2606.29799  CRISTAL: Bayes-optimal at 5 examples; frontier LLMs plateau at 40%
- DOI:10.1145/3591280 Scallop: Datalog NeSy (ACM PLDI 2023)

## Non-English research status
| Language | Status  | Key finding |
|----------|---------|-------------|
| Chinese  | HIT     | Robust Abductive Learning (Li Yufeng/Nanjing); KG+LLM bidirectional roadmap (Wu Xindong) |
| Japanese | HIT     | IPSJ 2024: Toulmin+KG debate partner; MUSUBIX Z3 for software requirements (Qiita) |
| Korean   | GAP     | No independent native-language NeSy research found — genuine gap |
| Russian  | PARTIAL | RAS/SPIIRAS 2023: ontology-oriented NeSy for collaborative decision support (RSF grant) |
| French   | HIT     | CORIA-TALN 2026: causal NeSy agent; Prevyo MR4AP (defense-funded) |
| German   | HIT     | UDE ClassicLogic benchmark; TIB/Leibniz ORKG HITL (4hr → 24min lit review) |

## Research gaps (arXiv:2501.05435)
Explainability 28%, Meta-cognition 5%, Symbol grounding ≠ compositionality (iLTN),
LLM hallucination in symbolic pipelines, Counterfactual reasoning, Korean NeSy gap.

## Graphiti knowledge graph
3 episodes ingested: NeSy survey, benchmark results, implementation status.
Search with: graphiti search "neurosymbolic" or hindsight_recall("neurosymbolic")
