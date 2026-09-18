# Neurosymbolic AI Landscape — Verified Data (July 2026)

Research date: July 17, 2026. Sources: GitHub (direct), PyPI, arxiv.org,
LAMDA-NeSy, scallop-lang.org. Full report: /tmp/neurosymbolic-implementation.md

---

## Production-Ready Frameworks (pip-installable, actively maintained)

| Framework | GitHub | Stars | Last Commit | pip install | Notes |
|-----------|--------|-------|-------------|-------------|-------|
| Outlines | dottxt-ai/outlines | ⭐14,500 | Jul 9 2026 (daily) | `pip install outlines` | Grammar-constrained LLM generation; 3.1k dependents; used in vLLM/Ollama |
| SymbolicAI | ExtensityAI/symbolicai | ⭐1,700 | Jun 24 2026 | `pip install symbolicai` | NeSy LLM orchestration + Lean4 formal verification; 95 releases |
| SynaLinks | SynaLinks/synalinks | ⭐446 | Jul 10 2026 (daily) | `pip install synalinks` | Keras-inspired NeSy LM; graph RAG, in-context RL, Text2SQL |
| PyReason | lab-v2/pyreason | ⭐344 | May 13 2026 | `pip install pyreason` | Graph temporal logic; v3.6.0; NumPy/Numba parallel inference |
| Scallop | scallop-lang/scallop | ⭐500 | Jun 26 2026 | Build from source (Rust nightly) | Differentiable Datalog; MIT; PLDI 2023 |

## Research/Academic Frameworks (pip-installable but slower cadence)

| Framework | GitHub | Stars | Last Commit | pip install | Notes |
|-----------|--------|-------|-------------|-------------|-------|
| DeepProbLog | ML-KULeuven/deepproblog | ⭐349 | Aug 9 2024 | `pip install deepproblog` | Probabilistic Prolog + PyTorch; needs SWI-Prolog <9.0 for approx inference |
| LTNtorch | tommasocarraro/LTNtorch | ~200 | Oct 2024 | `pip install LTNtorch` | FOL as training loss (PyTorch); good tutorials |
| LTN (TF2) | logictensornetworks/logictensornetworks | ⭐368 | Nov 13 2024 | `pip install ltn` | TensorFlow 2 version; original LTN implementation |
| mOWL | bio-ontology-research-group/mowl | ⭐92 | Jul 9 2026 | `pip install mowl-borg` | ML with OWL ontologies; knowledge graph + DL reasoning |
| ABLKit | — | — | — | `pip install ablkit` | Abductive Learning framework |

## Research Prototypes (NOT pip-installable / unmaintained)

| Framework | Notes |
|-----------|-------|
| DreamCoder (liqing-ustc/dreamcoder) | Wake-sleep program synthesis; OCaml+Python; 2020 paper; complex setup; not maintained |
| DeepCoder (Microsoft Research) | 2017; symbolic-guided program synthesis; no active repo |
| NeuroLogic Decoding (qbetterk/Constrained_Generation) | NAACL 2021; code available but not packaged |
| DeepDistilling (pauljblazek/deepdistilling) | ⭐101; Nature ComputSci 2024; no pip; research only |

## LLM + Symbolic Integration Patterns (ranked by practicality)

1. **Grammar-constrained decoding** (Outlines): symbolic grammar masks logits at inference time.
   Most production-ready. `pip install outlines`. Works with any local model.

2. **PAL / Program-Aided LMs**: LLM writes Python → Python interpreter executes → answer.
   No library needed. Any LLM API + subprocess. One-file implementation.

3. **Text2SQL / Text2Cypher**: LLM generates structured query → DB executes.
   Most-deployed NeSy in enterprise. SynaLinks has built-in support.

4. **Symbolic feedback loop**: LLM generates code → pytest/mypy/Z3 runs → result fed back.
   Standard agentic coding pattern. Composable with any coding agent.

5. **LLM → Z3 constraints**: `pip install z3-solver`. LLM generates SMT constraints;
   Z3 verifies/finds solution. Good for spec verification tasks.

6. **RAG as symbolic memory**: vector DB (Qdrant/Chroma) + knowledge graph (Graphiti) =
   symbolic retrieval layer for LLM reasoning.

7. **Wolfram Alpha integration**: Wolfram Agent One API (gpt.wolfram.com) = cloud-based
   symbolic math/knowledge engine callable from LLM agents.

## Curated Lists / Awesome Resources

- LAMDA-NeSy/Awesome-LLM-Reasoning-with-NeSy — ⭐318, LLMs+NeSy papers, Jun 2025
- filipeoliveiraa/awesome-neuro-symbolic-ai — General NeSy curated list (CodeSandbox mirror)
- Brandonio-c/NeuroAI-Cognition-Hub — Cognition-focused NeSy links
- thuwzy/Neural-Symbolic-and-Probabilistic-Logic-Papers — ⭐137, papers list

## Key Research Papers (LLM + NeSy era)

| Paper | Year | Key Idea |
|-------|------|----------|
| DeepProbLog | NeurIPS 2018 | Neural predicates in ProbLog |
| DreamCoder (Ellis et al.) | PLDI 2021 | Wake-sleep program induction + library learning |
| PAL | ICML 2023 | Program-Aided LMs with Python interpreter |
| Scallop (Li et al.) | PLDI 2023 | Differentiable Datalog |
| NeuroLogic Decoding | NAACL 2021 | Constrained text gen with predicate logic |
| NeuroLogic A*esque | NAACL 2022 | Better constraint satisfaction during gen |
| NeSy AI in 2024 (survey) | arXiv Jan 2025 | Systematic review (arxiv:2501.05435) |
| LLM-SYM | 2025 | Symbolic fine-tuning for LLM theorem proving |

## Local Install Notes (Fedora Silverblue / Python)

- All `pip install` frameworks above work in a standard Python venv / toolbox container
- Scallop requires `rustup default nightly` + `git clone` + `make install-scli`
- DeepProbLog approximate inference requires SWI-Prolog <9.0:
  In toolbox: `sudo dnf install swi-prolog` (check version; Fedora ships 9.x — may need RPM)
- All others: zero system dependencies beyond PyTorch / TensorFlow

## Quick-Win Patterns (5-30 min to working demo)

```python
# 1. Outlines — grammar-constrained code analysis (15 min)
pip install outlines transformers
# Force LLM to produce valid Pydantic schema output — no hallucinated fields

# 2. PyReason — graph logic over code deps (30 min)
pip install pyreason networkx
# Load dependency graph → define logical rules → run inference to find at-risk modules

# 3. Z3 constraint verification (5 min)
pip install z3-solver
# Have LLM generate constraints → Z3 verifies / finds counterexample
```

## Gartner Positioning (2025-2026)

- Broad NeSy AI adoption: 2-5 year horizon (Gartner)
- Production NOW: Text2SQL, constrained generation, code verification loops, document review
- Research stage: End-to-end differentiable NeSy (DeepProbLog, LTN training workflows)
- The "NeSy" label is increasingly applied to agentic LLM + tool-use patterns that
  have been in production since 2023 (Outlines, PAL, pytest feedback loops)
