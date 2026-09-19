# Computer Science > Artificial Intelligence

 [Submitted on 16 Aug 2026]

# Title:HyMem: Hierarchical Context Management for Long-Horizon Agents via Information Isolation

[View PDF](/pdf/2608.15703) [HTML (experimental)](https://arxiv.org/html/2608.15703v1)

> Abstract:Large language model (LLM) agents often perform poorly on complex, long-horizon tasks because their context becomes increasingly cluttered over time. As interactions accumulate, detailed execution traces and intermediate outputs dominate the context, making it difficult for the model to retain and use high-level planning information. Most existing methods address this issue through compression or retrieval applied to a single, flat context, which does not clearly separate different types of context information and often leads to degraded reasoning. To address this challenge, we propose HyMem, a hierarchical framework that explicitly separates the agent's context into distinct functional layers. HyMem organizes context by function to separate high-level planning from execution and complex analysis. Its isolated reasoning module handles complex subtasks without adding intermediate reasoning traces to the persistent planning context, while its memory management module preserves task progress across context refreshes through structured summaries. These components reduce redundant context accumulation, retain task-critical information, and support coherent long-horizon reasoning within a limited context window. Experiments on GAIA and Browsecomp-plus show that, with DeepSeek-V4, HyMem achieves average Pass@1 scores of 66.7% and 61.3%, outperforming the strongest baseline by 6.1 and 4.7 percentage points, respectively. Further analysis indicates that HyMem effectively controls the growth of the reasoning context, allowing the model to maintain focus and accuracy across complex, long-horizon tasks.

| Subjects: | Artificial Intelligence (cs.AI) |
|---|---|
| Cite as: | [arXiv:2608.15703](https://arxiv.org/abs/2608.15703) [cs.AI] |
| | (or [arXiv:2608.15703v1](https://arxiv.org/abs/2608.15703v1) [cs.AI] for this version) |
| | [https://doi.org/10.48550/arXiv.2608.15703](https://doi.org/10.48550/arXiv.2608.15703) |

## Submission history

 From: Hongming Zhang [[view email](/show-email/3db98bf2/2608.15703)]
**[v1]** Sun, 16 Aug 2026 12:15:01 UTC (1,412 KB)

# Bibliographic and Citation Tools

# Code, Data and Media Associated with this Article

# Recommenders and Search Tools

# arXivLabs: experimental projects with community collaborators

arXivLabs is a framework that allows collaborators to develop and share new arXiv features directly on our website.

Both individuals and organizations that work with arXivLabs have embraced and accepted our values of openness, community, excellence, and user data privacy. arXiv is committed to these values and only works with partners that adhere to them.

Have an idea for a project that will add value for arXiv's community? [**Learn more about arXivLabs**](https://info.arxiv.org/labs/index.html).