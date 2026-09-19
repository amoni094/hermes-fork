# ECHO: Prune to Act, Trace to Learn with Selective Turn Memory in Agentic RL
URL: https://arxiv.org/abs/2606.31650

ECHO: Prune to Act, Trace to Learn with Selective Turn Memory in Agentic RL

arXiv is now an independent nonprofit! Learn moreÃ

# ECHO: Prune to Act, Trace to Learn with Selective Turn Memory in Agentic RL

Zijun Xie1,2ââ  Binbin Zheng2,3ââ  Enlei Gong2â Jihua Liu2 Yuyang You1 Lingfeng Liu1 Jiayao Tang1 Guanqun Zhao2 Xiaoliang Fu Aoqi Hu2 Zeyu Chen2â¡ 1School of Mathematical Sciences, Peking University 2Baidu Inc. 3University of Science and Technology of China xiezijun@baidu.com GitHub:xiezijun714-lang/Echo

###### Abstract

Long-horizon language agents must repeatedly interact with tools, accumulate evidence, and make decisions under bounded context windows. Context-management methods make such rollouts feasible by simplifying past interactions through deletion, folding, or memory editing. However, when useful history is collapsed into compressed states, the reconstructed context may no longer reveal which earlier observations support a successful final answer. This creates a mismatch between bounded-context acting and outcome-based reinforcement learning: the policy acts on reconstructed context, while the learner lacks source-level provenance for assigning credit to the evidence that mattered. We propose ECHO, a selective turn-memory framework for traceable context reconstruction in agentic RL. ECHO compresses each completed environment turn into a compact source-indexed memory record, reconstructs bounded policy contexts by selecting useful records, and reuses the selected source indices to route positive outcome credit to the final trajectory segment, reused evidence turns, memory findings, and memory-selection actions. On BrowseComp-Plus, ECHO reaches 43.4% held-out accuracy, outperforming GRPO at 28.9% and the rolling-summary baseline SUPO at 36.1%, while using fewer turns and lower trajectory volume than SUPO. The trained policy also improves zero-shot generalization across multi-objective QA, code generation, and deep information-seeking benchmarks on both dense and MoE backbones.

Figure 1: Held-out accuracy, tool-use turns per rollout, and trajectory volume over training on BrowseComp-Plus with the Qwen3-32B-Instruct backbone for ECHO (purple), GRPO (orange), and SUPO (green). ECHO traces the upper-left frontier: rising accuracy without the turn and volume growth seen for SUPO.

## 1 Introduction

Large language models (LLMs) are increasingly deployed as multi-turn agents that interleave reasoning, tool invocation, and environment feedback (38; 20). Reinforcement learning (RL) from verifiable final outcomes has become a central recipe for improving such agents in search, coding, function calling, and deep-research settings (6; 18; 8; 46). As interaction horizons grow, however, history management becomes a bottleneck for both acting and learning. The policy must retain useful observations within a bounded context window, while the learner must decide which earlier decisions should receive credit from a sparse final outcome.

Context-manag