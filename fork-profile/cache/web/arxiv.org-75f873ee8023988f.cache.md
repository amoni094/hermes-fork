# [2609.07471] MEMO: Multimodal Evidence Memory Organization for Long-Horizon LLM Agents
URL: https://arxiv.org/abs/2609.07471
Published: 2026-09-07

[2609.07471] MEMO: Multimodal Evidence Memory Organization for Long-Horizon LLM Agents
[Skip to main content](#content)
[](https://arxiv.org/IgnoreMe)
[
![archive](https://arxiv.org/static/base/1.0.1/images/arxiv-logo-primary-light.svg)
](https://arxiv.org/)
Search arXiv
Press Enter to search Â· [Advanced search](https://arxiv.org/search/advanced)
# Computer Science > Computation and Language
**arXiv:2609.07471** (cs)
[Submitted on 7 Sep 2026]
# Title:MEMO: Multimodal Evidence Memory Organization for Long-Horizon LLM Agents
Authors:[Xian Gao](https://arxiv.org/search/cs?searchtype=author&query=Gao,+X), [Jinpeng Wang](https://arxiv.org/search/cs?searchtype=author&query=Wang,+J), [Jiacheng Ruan](https://arxiv.org/search/cs?searchtype=author&query=Ruan,+J), [Guangyu Cao](https://arxiv.org/search/cs?searchtype=author&query=Cao,+G), [Ting Liu](https://arxiv.org/search/cs?searchtype=author&query=Liu,+T), [Yuzhuo Fu](https://arxiv.org/search/cs?searchtype=author&query=Fu,+Y)
View a PDF of the paper titled MEMO: Multimodal Evidence Memory Organization for Long-Horizon LLM Agents, by Xian Gao and 5 other authors
[View PDF](https://arxiv.org/pdf/2609.07471)
[HTML (experimental)](https://arxiv.org/html/2609.07471v1)
>
> Abstract:
> Long-running LLM agents rely on external memory to store and reuse information beyond a single context window, yet there is a fundamental tension between the continuous accumulation of interaction trajectories and the limited context capacity. The key challenge in agent memory is therefore not only to retrieve relevant records, but also to select necessary evidence under a given budget and organize it in an appropriate modality. Existing memory readout methods mainly use textual or visual forms. Text preserves high fidelity, but its linear token representation makes contents with different importance compete for the limited context at nearly uniform unit cost. Visual readout renders text into document-like images, which can use two-dimensional layouts to expose structure and emphasize key information, but it may lose fine-grained details during rendering and compression. To address this issue, we propose MEMO, a multimodal evidence memory organization method for LLM agents. MEMO first uses a trained evidence extractor to select relevant memory blocks and form evidence units with source information and presentation requirements. A trained query-conditioned memory manager assigns each unit to a textual, visual, or dual-channel carrier and selects a layout that matches the evidence structure. A deterministic memory construction module then generates the textual package and visual pages. The memory manager is trained with feedback from an offline reader that measures the utility of the guided memory plan, so that retention and presentation decisions align with downstream usage. We evaluate MEMO on four benchmarks, HotpotQA, 2WikiMultiHopQA, LoCoMo, and ALFWorld, with multiple reader backends. The results show that MEMO presents memory