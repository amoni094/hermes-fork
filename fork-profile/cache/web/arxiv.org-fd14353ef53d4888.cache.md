# Certifying Collective Reasoning in Multi-Agent Systems via Koopman Spectral Analysis
URL: https://arxiv.org/abs/2608.05956

Certifying Collective Reasoning in Multi-Agent Systems via Koopman Spectral Analysis

arXiv is now an independent nonprofit! Learn moreÃ

# Certifying Collective Reasoning in Multi-Agent Systems via Koopman Spectral Analysis

Nuzhat Khan Indrakshi Dey Thanks: N.ËKhan is with Universiti Teknologi Malaysia, Johor Bahru, Malaysia; I.ËDey is with Department of Computing and Mathematics, South East Technological University, Waterford, Ireland (e-mail: khan.nuzhat@utm.my; indrakshi.dey@setu.ie). Thanks: Manuscript submitted to IEEE Transactions on Emerging Topics in Computational Intelligence and is under review.

###### Abstract

Orchestrated collectives of large language model (LLM) agents that debate and vote are an emerging form of computational intelligence: the intelligent behaviour resides in the interaction, not in any single agent. They improve task accuracy, yet remain black boxes at the system level: there is no principled test of convergence, no bound on the rounds needed, and no faithful account of what drove a decision. This paper develops a novel framework based on Koopman operator theory and validates its theoretical guarantees on multi-agent consensus dynamics. Treating the collective as one nonlinear dynamical system on a communication graph, we read its essential behaviour off the spectrum of its Koopman transfer operator, an exact linear representation of the nonlinear dynamics estimated from interaction traces. The spectrum yields three machine-checkable certificates: the sub-dominant eigenvalue $\lambda_{2}$ fixes the intrinsic timescale of reasoning and yields a convergence deadline computable before the debate runs; its eigenvector names the coherent factions the collective reasons in, and $|\lambda_{2}|$ certifies when that explanation is valid; and the leading spectral coordinates form a compressed, auditable message basis. On an attention-consensus model, the deadline tracks observed convergence with logâlog correlation $0.93$ and bounds it in 96% of 24 configurations; attribution is exact whenever the spectrum certifies metastability; eight of 32 coordinates preserve the decision at 99.7% fidelity; and a certificate learned from 15 debates held on 60/60 held-out debates. The study runs in minutes on a CPU, making spectral certification a practical layer for trustworthy collective reasoning.

###### Index Terms:

Collective intelligence, multi-agent systems, large language models, Koopman operator, dynamic mode decomposition, social reasoning, explainable artificial intelligence, consensus dynamics, trustworthy AI, semantic communications.

## I Introduction

An emerging class of intelligent systems locates its intelligence not in a single model but in a society of models. Orchestrated large language model (LLM) agents that debate one another [1], criticise and defend candidate solutions [2], or coordinate through structured conversation [3] now routinely outperform their individual members on mathematical, coding, and questi