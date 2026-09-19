# Computer Science > Artificial Intelligence

 [Submitted on 15 Aug 2026 ([v1](https://arxiv.org/abs/2608.15071v1)), last revised 30 Aug 2026 (this version, v2)]

# Title:Evo-Harness: Context-to-Harness Skill Compilation for Self-Evolving Agents

[View PDF](/pdf/2608.15071) [HTML (experimental)](https://arxiv.org/html/2608.15071v2)

> Abstract:Learning from experience is critical for developing capable, self-improving large language model (LLM) agents. Existing methods typically extract knowledge from accumulated trajectories via reflection, memory, rules, or skills. However, agents in realistic environments continuously encounter novel tasks, often offering only a one-shot opportunity to improve. These executions yield rich but highly noisy contexts, entangling broadly useful lessons with task-specific artifacts. Critically, prior works rarely validate their effectiveness on complex real-world tasks or isolate the underlying drivers of improvement. To address these gaps, we formulate online harness learning, where a frozen agent improves by continually updating a structured harness across sequential tasks. This formulation enables a systematic study of key self-improvement factors through our proposed Evo-Harness. At its core, context-to-harness skill compilation distills noisy, single-shot executions into reusable skill harnesses for cross-domain and topic-level adaptation. To demonstrate the efficacy of one-shot skill compilation, we evaluate across five realistic benchmarks (TerminalBench2, SWE-bench, CL-Bench, -bench, WebArena-Infinity). Our extensive analysis demonstrates the effectiveness of Evo-Harness and provides a principled understanding of how LLM agents can effectively learn on the fly. Our code is available at [this https URL](https://github.com/A-EVO-Lab/a-evolve/tree/release/evo-harness).

| Comments: | EMNLP 2026 Main |
|---|---|
| Subjects: | Artificial Intelligence (cs.AI); Computation and Language (cs.CL) |
| Cite as: | [arXiv:2608.15071](https://arxiv.org/abs/2608.15071) [cs.AI] |
| | (or [arXiv:2608.15071v2](https://arxiv.org/abs/2608.15071v2) [cs.AI] for this version) |
| | [https://doi.org/10.48550/arXiv.2608.15071](https://doi.org/10.48550/arXiv.2608.15071) |

## Submission history

 From: Tianxin Wei [[view email](/show-email/6a9098ed/2608.15071)]
**[[v1]](/abs/2608.15071v1)** Sat, 15 Aug 2026 06:43:56 UTC (600 KB)
**[v2]** Sun, 30 Aug 2026 19:47:36 UTC (600 KB)

# Bibliographic and Citation Tools

# Code, Data and Media Associated with this Article

# Recommenders and Search Tools

# arXivLabs: experimental projects with community collaborators

arXivLabs is a framework that allows collaborators to develop and share new arXiv features directly on our website.

Both individuals and organizations that work with arXivLabs have embraced and accepted our values of openness, community, excellence, and user data privacy. arXiv is committed to these values and only works with partners that adhere to them.

Have an idea for a project that will add value for arXiv's community? [**Learn more about arXivLabs**](https://info.arxiv.org/labs/index.html).