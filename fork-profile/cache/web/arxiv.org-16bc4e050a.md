# Search-G1: Grounded Search Agents via Representation-Based Intrinsic Rewards
URL: https://arxiv.org/abs/2608.07531

Search-G1: Grounded Search Agents via Representation-Based Intrinsic Rewards

arXiv is now an independent nonprofit! Learn moreÃ

# Search-G1: Grounded Search Agents via Representation-Based Intrinsic Rewards

Ruoxi Cheng Affiliation: Fudan University Affiliation: Tencent Haoxuan Ma Affiliation: Nanjing University Hongyi Zhang Affiliation: Nanyang Technological University Junming Zhang Affiliation: Shanghai Jiao Tong University Ranjie Duan Affiliation: Tencent Qiaolin Xia Affiliation: Tencent Hao Wang Affiliation: Tencent Yu Lu Affiliation: Tencent Haibo Shi Affiliation: Tencent Xingjun Ma Affiliation: Fudan University

###### Abstract

Search-augmented language agents should retrieve external information only when necessary and ground their answers in retrieved evidence. Existing external rewards provide either sparse outcome supervision or richer feedback from process annotations and LLM judges. Outcome rewards scale readily but cannot distinguish grounded retrieval from redundant search, whereas richer signals require costly annotation or inference during training. Internal rewards based on policy-side signals such as entropy, likelihood, or information gain are graded and inexpensive to evaluate, yet mainly reflect model confidence rather than evidence grounding. We propose Search-G1, a representation-based intrinsic reward framework that measures the operational grounding of an agentâs answers through two intervention-calibrated readouts. A prompt-state readout predicts closed-book sufficiency, whose complement defines policy-relative retrieval necessity; an answer-commit readout estimates evidence reliance from answer-stage sensitivity to evidence deletion. Together, they provide additional credit to correct searched trajectories when retrieval is estimated necessary and the answer is evidence-sensitive, favor correct direct answers when closed-book knowledge suffices, and penalize repeated search. After calibration, reward scoring requires neither process annotations nor LLM-as-judge inference during policy optimization. Because reinforcement learning changes policy representations, Search-G1 periodically refits both readouts on trajectories from the latest checkpoint, allowing the reward to co-evolve with the policy. Experiments across multiple search-based question-answering benchmarks and two model scales show that Search-G1 improves the groundingâsearch-cost trade-off, producing shorter response-side trajectories at competitive task accuracy. Code is available at Rosy0912/Search-G1.

22footnotetext: Corresponding to vichwang@tencent.com; xingjunma@fudan.edu.cn. This work was conducted during Ruoxi Chengâs participation in the Tencent (Yuanbao AI Search) Rhino-Bird Research Elite Program (Industrial Supervisor: Hao Wang; Academic Supervisor: Xingjun Ma).

## 1 Introduction

Search agents augment large language models (LLMs) with an external retrieval loop. They issue queries, inspect documents, reason over evidence, and then commit an a