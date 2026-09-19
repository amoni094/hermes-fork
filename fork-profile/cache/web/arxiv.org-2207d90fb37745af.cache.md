# Computer Science > Artificial Intelligence

 [Submitted on 10 Sep 2026]

# Title:Grounding Agent Memory: Environment-Probing Curation for Enterprise Agents

[View PDF](/pdf/2609.11060) [HTML (experimental)](https://arxiv.org/html/2609.11060v1)

> Abstract:Persistent memory is entering production-oriented agent platforms to help long-horizon agents accumulate experience across sessions. Yet a post-task curator agent restricted to completed trajectories can preserve errors, overgeneralize partial evidence, or retain stale knowledge. We introduce environment-probing curation, a deployment-compatible extension that gives an existing asynchronous curator agent least-privilege, read-only world tools to check, scope, and refresh candidate memories. It requires no model retraining and leaves the task agent, retriever, memory representation, and production write authority unchanged. In a production-like GitHub Copilot (GHCP) harness built on its SDK, we compare stateless execution, full in-context learning, GHCP + Mem, and GHCP + Mem (w/ Env Probing) on CLBench database exploration and 90 adapted APEX management-consulting tasks. On CLBench, probing raises pass rate from 39% to 73% and pass-discounted reward from 8.60 to 22.60 while reducing queries from 8.8 to 4.7 per question and task-agent cost from \$3.38 to \$1.68. Across six APEX worlds, all 18 memory-versus-baseline mean reward comparisons are positive and task-agent tool calls fall by 16--75%; probing gives the best task-agent reward gain per dollar in five worlds. Probing also attains higher mean reward than GHCP + Mem on both Sonnet 4.6 and Opus 4.7 without schema drift. Environment probing therefore turns existing agent-memory curation into an environment-informed, auditable process while preserving a compact task-time interface.

| Subjects: | Artificial Intelligence (cs.AI); Software Engineering (cs.SE) |
|---|---|
| Cite as: | [arXiv:2609.11060](https://arxiv.org/abs/2609.11060) [cs.AI] |
| | (or [arXiv:2609.11060v1](https://arxiv.org/abs/2609.11060v1) [cs.AI] for this version) |
| | [https://doi.org/10.48550/arXiv.2609.11060](https://doi.org/10.48550/arXiv.2609.11060) |

## Submission history

 From: Susheel Suresh [[view email](/show-email/3ce55db3/2609.11060)]
**[v1]** Thu, 10 Sep 2026 04:06:16 UTC (100 KB)

# Bibliographic and Citation Tools

# Code, Data and Media Associated with this Article

# Recommenders and Search Tools

# arXivLabs: experimental projects with community collaborators

arXivLabs is a framework that allows collaborators to develop and share new arXiv features directly on our website.

Both individuals and organizations that work with arXivLabs have embraced and accepted our values of openness, community, excellence, and user data privacy. arXiv is committed to these values and only works with partners that adhere to them.

Have an idea for a project that will add value for arXiv's community? [**Learn more about arXivLabs**](https://info.arxiv.org/labs/index.html).