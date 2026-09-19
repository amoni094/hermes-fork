# LLM Agents Are Latent Context Managers:Eliciting Self-Managed Context via State Proprioception
URL: https://arxiv.org/abs/2606.30005

LLM Agents Are Latent Context Managers:Eliciting Self-Managed Context via State Proprioception

arXiv is now an independent nonprofit! Learn moreÃ

# LLM Agents Are Latent Context Managers: Eliciting Self-Managed Context via State Proprioception

Binyan Xu Affiliation: The Chinese University of Hong Kong Affiliation: LIGHTSPEED{binyxu, khzhang}@ie.cuhk.edu.hk, 729156675@qq.com*Work done during an internship at Tencent. â Corresponding author. Haitao Li Affiliation: LIGHTSPEED{binyxu, khzhang}@ie.cuhk.edu.hk, 729156675@qq.com*Work done during an internship at Tencent. â Corresponding author. Kehuan Zhang Affiliation: The Chinese University of Hong Kong

###### Abstract

Long-horizon tool agents are bottlenecked by how their context grows toward the limits of the context window. Recent systems make context management agent- or system-controlled, but they either learn compression policies that discard evidence or manage context in a layer the agent never sees. We argue that both miss a more basic gap: frontier language models are proprioceptively blind to their own context. From the prompt alone they cannot reliably infer block size, recency, or the remaining budget, all of which are needed for keep-or-archive decisions. We introduce VISTA (Visible Internal State for Tool Agents), a training-free, model-agnostic layer that represents working memory as typed addressable blocks, surfaces a runtime dashboard of token usage, recency, archive status, and remaining budget, and archives blocks as recoverable full-fidelity payloads. On LOCA-Bench, BrowseComp-Plus, and GAIA, the same untrained interface transfers across 1M-, 100K-, and 10K-scale trajectories. On LOCA-Bench it lifts Gemini-3-Flash from 22.7 to 50.7%, reaches 58.0% on BrowseComp-Plus, and remains competitive on GAIA. Gains grow with context pressure and transfer across backbones, while ablations confirm that the dashboard matters beyond archive and recovery tools.

Figure 1: Who manages context, and on what information. Fixed rules compact context the agent cannot see, and blind self-management guesses without state. VISTA surfaces per-block metadata, so the agent archives the large block losslessly.

## 1 Introduction

Language agents operate over stateful tasks such as filling spreadsheets from web and email evidence, modifying databases, preparing application materials, debugging code, and coordinating business workflows [45, 16, 33]. Their context is working memory. It accumulates tool evidence, stale observations, failed attempts, user constraints, hypotheses, file paths, and action contracts that must remain correct many steps later [22, 26, 31]. As the task runs, working memory grows until it crowds or overflows the context window, a pressure also studied in long reasoning systems that summarize or carry state across computation [11, 29, 2]. The agent must decide what to keep visible, what to set aside, and what to recover. How this growing context is managed determines whether long-horiz