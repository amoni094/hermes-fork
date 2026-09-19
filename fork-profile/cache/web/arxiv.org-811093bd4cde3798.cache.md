[Submitted on 10 Aug 2026]

# Title:Beyond the Capability Boundary: Zeroth-Order Optimization for Self-Evolving LLM Agents

[View PDF](/pdf/2608.09292) [HTML (experimental)](https://arxiv.org/html/2608.09292v1)

> Abstract:Self-evolving methods improve the capabilities of LLM agents by sampling trajectories from the underlying LLMs and learning from these trajectories. However, these methods struggle to learn beyond the inherent capability boundary of the agents, since the agents cannot sample correct trajectories on difficult examples for further improvements. In this paper, we propose a zeroth-order self-evolution framework that enables agents to learn beyond their capability boundary by perturbing LLM parameters to adapt to difficult examples without any trajectory annotations. Specifically, we perturb LoRA parameters of LLMs, run the agent, compute the losses under the perturbed and original parameters, and use the loss difference to estimate gradients and further update the LoRA parameters. We sample trajectories using the updated LLMs for supervised fine-tuning to break through the capability boundary of the agents, forming a closed self-evolution loop. We introduce a parallel perturbation inference mechanism and an adaptive lookup mechanism to reduce time consumption in zeroth-order optimization, with an answer perplexity loss that provides smooth and stable zeroth-order loss values. Experiments on multiple deep research benchmarks show that our method obtains substantially more successful trajectories and consistently outperforms strong baselines, especially on difficult examples. The code and released artifacts are available at [this https URL](https://github.com/hidk1911/ZOForLLMAgents).

| Subjects: | Machine Learning (cs.LG); Computation and Language (cs.CL) |
|---|---|
| Cite as: | [arXiv:2608.09292](https://arxiv.org/abs/2608.09292) [cs.LG] |
| | (or [arXiv:2608.09292v1](https://arxiv.org/abs/2608.09292v1) [cs.LG] for this version) |
| | [https://doi.org/10.48550/arXiv.2608.09292](https://doi.org/10.48550/arXiv.2608.09292) arXiv-issued DOI via DataCite (pending registration) |