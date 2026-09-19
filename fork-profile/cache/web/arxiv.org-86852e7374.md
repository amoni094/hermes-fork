# Misinformation Propagation in Benign Multi-Agent Systems
URL: https://arxiv.org/abs/2606.16710

Misinformation Propagation in Benign Multi-Agent Systems

arXiv is now an independent nonprofit! Learn moreÃ

# Misinformation Propagation in Benign Multi-Agent Systems

Jonas Becker1,2,*, Jan Philip Wahle1, Terry Ruas1, â , Bela Gipp1, â  1University of GÃ¶ttingen, Germany; 2LKA NRW, Germany â Shared last authorship *Correspondence: jonas.becker@uni-goettingen.de

###### Abstract

Multi-agent systems, in which multiple large language model agents solve problems through turn-based interaction, are increasingly deployed in high-stakes settings such as medical diagnosis, legal analysis, and forensic decision-making. Their reliability can be at risk when single agents reason from incorrect or misleading context, e.g., from tool calls, since errors may propagate through agent interactions. This work studies this risk by injecting intent-based misinformation into benign single-agent and multi-agent systems across reasoning, knowledge, and alignment tasks. We find that misinformation can degrade single-agent performance and persists across multi-agent debate, with agents often retaining answers introduced by misinformed peers. Nevertheless, multi-agent debate reduces the resulting performance degradation compared to single-agent prompting, especially when most agents are not exposed to misinformation. Robustness depends on group composition and decision protocol. Consensus can be more stable than voting under peer pressure, while majorities can often steer misinformed agents back toward correct answers. Our results show that misinformation robustness in multi-agent systems depends on the underlying model and also on how agents exchange information and aggregate decisions.

Misinformation Propagation in Benign Multi-Agent Systems

Jonas Becker1,2,*, Jan Philip Wahle1, Terry Ruas1, â , Bela Gipp1, â  1University of GÃ¶ttingen, Germany; 2LKA NRW, Germany â Shared last authorship *Correspondence: jonas.becker@uni-goettingen.de

## 1 Introduction

Multi-agent systems (MAS) based on large language models (LLMs) can solve complex problems through debate and task decomposition (rasal2024llmharmonymultiagentcommunication; li2024survey; SAPKOTA2026103599). Collaborative structures have been proposed as a way to improve reasoning quality (wang-etal-2024-rethinking-bounds; 10.5555/3692070.3692537), enable task specialization (borghoff2025organizational), and increase robustness compared to single-agent systems (ju2025disagreementselicitrobustnessinvestigating; staufer20262025aiagentindex). MAS often rely on agent-user interactions and on multiple agents exchanging intermediate reasoning steps, challenging each other, and collectively arriving at a final decision.

Figure 1: Overall accuracy by dataset and model comparing the single-agent and multi-agent system with and without misinformation in the context.

The reliability of MAS becomes uncertain when some agents operate under incorrect information. Inaccurate knowledge may arise from several sources, such as retrieval