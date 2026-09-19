# [2609.05339] Does Your Agent's Memory Survive a Model Upgrade? A Controlled Study of Memory Portability
URL: https://arxiv.org/abs/2609.05339
Published: 2026-09-04

[2609.05339] Does Your Agent's Memory Survive a Model Upgrade? A Controlled Study of Memory Portability
[Skip to main content](#content)
[](https://arxiv.org/IgnoreMe)
[
![archive](https://arxiv.org/static/base/1.0.1/images/arxiv-logo-primary-light.svg)
](https://arxiv.org/)
Search arXiv
Press Enter to search Â· [Advanced search](https://arxiv.org/search/advanced)
# Computer Science > Artificial Intelligence
**arXiv:2609.05339** (cs)
[Submitted on 4 Sep 2026]
# Title:Does Your Agent's Memory Survive a Model Upgrade? A Controlled Study of Memory Portability
Authors:[Ankit Goyal](https://arxiv.org/search/cs?searchtype=author&query=Goyal,+A), [Jaideep Ray](https://arxiv.org/search/cs?searchtype=author&query=Ray,+J)
View a PDF of the paper titled Does Your Agent's Memory Survive a Model Upgrade? A Controlled Study of Memory Portability, by Ankit Goyal and 1 other authors
[View PDF](https://arxiv.org/pdf/2609.05339)
[HTML (experimental)](https://arxiv.org/html/2609.05339v1)
>
> Abstract:
> Model upgrades are routine; memory migrations are not. An agent can keep the same memory store and still forget: a new model may interpret old notes differently, mixed embedding versions may break retrieval, and repair may fail without the original evidence. We compare memory as the same history is preserved verbatim for long-context reading (LC-RAW), divided into chunks for retrieval-augmented generation (RAG), compressed by a model into natural-language notes (NOTES), or normalized into a fixed-schema knowledge graph (KG-fixed). The study uses 48 synthetic histories with randomized answer codes, exact scoring, and two open-weight models with sub 10 billion parameters.
> Our measurements show that fixed-schema structures transfer reliably, with KG-fixed accuracy changing by only
> +
> 0.0004
> Â±
> 0.0020
> following a writer swap. Conversely, compressed NOTES exhibit high model coupling, with accuracy shifting asymmetrically by
> +
> 9.91
> or
> â
> 13.28
> percentage points depending on the specific migration direction. In RAG systems, partial embedding migrations using a 50/50 mixed index capture only a 4.96-point accuracy improvement, forfeiting the majority of the 11.90-point gain achieved through full re-embedding. Diagnostic decomposition attributes 80% (
> 0.467
> Â±
> 0.014
> ) of the NOTES accuracy deficit to information lost during initial construction, whereas retrieval failures drive 81% (
> 0.364
> Â±
> 0.012
> ) of the RAG deficit. Finally, store-only repair of NOTES fails to reach a 90% performance recovery target in all 48 test cases, whereas retaining the raw source history enables successful recovery in 34 of 48 cases for one tested direction. These findings highlight the necessity of direction-specific migration testing, strict embedding space isolation, and the retention of source histories for memory repair.
|Comments:|18 pages, 3 figures, 7 tables, under review|
|Subjects:|Artificial Intelligence (cs.AI); Computation and Language (cs.CL); Informa