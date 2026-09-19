[![Cornell University](/static/browse/0.3.4/images/icons/cu/cornell-reduced-white-SMALL.svg)](https://www.cornell.edu/)

We gratefully acknowledge support from the Simons Foundation, [member institutions](https://info.arxiv.org/about/ourmembers.html), and all contributors.[Donate](https://info.arxiv.org/about/donate.html)

[![arXiv logo](/static/browse/0.3.4/images/arxiv-logomark-small-white.svg)](https://arxiv.org/)

[![Cornell University Logo](/static/browse/0.3.4/images/icons/cu/cornell-reduced-white-SMALL.svg)](https://www.cornell.edu/)

# Computer Science > Artificial Intelligence

 [Submitted on 22 Mar 2026]

# Title:AdaRubric: Task-Adaptive Rubrics for LLM Agent Evaluation

[View PDF](/pdf/2603.21362)[HTML (experimental)](https://arxiv.org/html/2603.21362v1)

> Abstract:LLM-as-Judge evaluation fails agent tasks because a fixed rubric cannot capture what matters for this task: code debugging demands Correctness and Error Handling; web navigation demands Goal Alignment and Action Efficiency. We present ADARUBRIC, which closes this gap by generating task-specific evaluation rubrics on the fly from task descriptions, scoring trajectories step-by-step with confidence-weighted per-dimension feedback, and filtering preference pairs with the novel DimensionAwareFilter - a provably necessary condition for preventing high-scoring dimensions from masking dimension-level failures. On WebArena and ToolBench, ADARUBRIC achieves Pearson r=0.79 human correlation (+0.16 over the best static baseline) with deployment-grade reliability (Krippendorff's $\alpha$=0.83). DPO agents trained on ADARUBRIC preference pairs gain +6.8 to +8.5 pp task success over Prometheus across three benchmarks; gains transfer to SWE-bench code repair (+4.9 pp) and accelerate PPO convergence by +6.6 pp at 5K steps - both without any rubric engineering. Code: [this https URL](https://github.com/alphadl/AdaRubrics).

| Subjects: | Artificial Intelligence (cs.AI); Computation and Language (cs.CL) |
|---|---|
| Cite as: | [arXiv:2603.21362](https://arxiv.org/abs/2603.21362) [cs.AI] |
| | (or [arXiv:2603.21362v1](https://arxiv.org/abs/2603.21362v1) [cs.AI] for this version) |
| | [https://doi.org/10.48550/arXiv.2603.21362](https://doi.org/10.48550/arXiv.2603.21362) arXiv-issued DOI via DataCite (pending registration) |

## Submission history

 From: Liang Ding [[view email](/show-email/1ffbc889/2603.21362)]
**[v1]** Sun, 22 Mar 2026 18:47:34 UTC (43 KB)

Full-text links:

## Access Paper:

- [View PDF](/pdf/2603.21362)
- [HTML (experimental)](https://arxiv.org/html/2603.21362v1)
- [TeX Source ](/src/2603.21362)
[![license icon](https://arxiv.org/icons/licenses/zero-1.0.png)view license](http://creativecommons.org/publicdomain/zero/1.0/)

 Current browse context:
cs.AI

[< prev](/prevnext?id=2603.21362&function=prev&context=cs.AI)[next >](/prevnext?id=2603.21362&function=next&context=cs.AI)

[new](/list/cs.AI/new)[recent](/list/cs.AI/recent)[2026-03](/list/cs.AI/2026-03)

 Change to browse by:
[cs](/abs/2603.21362?context=cs)[cs.CL](/abs/2603.21362?context=cs.CL)

### References & Citations

- [NASA ADS](https://ui.adsabs.harvard.edu/abs/arXiv:2603.21362)
- [Google Scholar](https://scholar.google.com/scholar_lookup?arxiv_id=2603.21362)
- [Semantic Scholar](https://api.semanticscholar.org/arXiv:2603.21362)

export BibTeX citation

### Bookmark

[![BibSonomy logo](/static/browse/0.3.4/images/icons/social/bibsonomy.png)](http://www.bibsonomy.org/BibtexHandler?requTask=upload&url=https://arxiv.org/abs/2603.21362&description=AdaRubric: Task-Adaptive Rubrics for LLM Agent Evaluation)[![Reddit logo](/static/browse/0.3.4/images/icons/social/reddit.png)](https://reddit.com/submit?url=https://arxiv.org/abs/2603.21362&title=AdaRubric: Task-Adaptive Rubrics for LLM Agent Evaluation)

# Bibliographic and Citation Tools

Bibliographic Explorer*([What is the Explorer?](https://info.arxiv.org/labs/showcase.html#arxiv-bibliographic-explorer))*

Connected Papers*([What is Connected Papers?](https://www.connectedpapers.com/about))*

Litmaps*([What is Litmaps?](https://www.litmaps.co/))*

scite Smart Citations*([What are Smart Citations?](https://www.scite.ai/))*

# Code, Data and Media Associated with this Article

alphaXiv*([What is alphaXiv?](https://alphaxiv.org/))*

CatalyzeX Code Finder for Papers*([What is CatalyzeX?](https://www.catalyzex.com))*

DagsHub*([What is DagsHub?](https://dagshub.com/))*

Gotit.pub*([What is GotitPub?](http://gotit.pub/faq))*

Hugging Face*([What is Huggingface?](https://huggingface.co/huggingface))*

Papers with Code*([What is Papers with Code?](https://paperswithcode.com/))*

ScienceCast*([What is ScienceCast?](https://sciencecast.org/welcome))*

# Demos

Replicate*([What is Replicate?](https://replicate.com/docs/arxiv/about))*

Hugging Face Spaces*([What is Spaces?](https://huggingface.co/docs/hub/spaces))*

TXYZ.AI*([What is TXYZ.AI?](https://txyz.ai))*

# Recommenders and Search Tools

Influence Flower*([What are Influence Flowers?](https://influencemap.cmlab.dev/))*

CORE Recommender*([What is CORE?](https://core.ac.uk/services/recommender))*

# arXivLabs: experimental projects with community collaborators

arXivLabs is a framework that allows collaborators to develop and share new arXiv features directly on our website.

Both individuals and organizations that work with arXivLabs have embraced and accepted our values of openness, community, excellence, and user data privacy. arXiv is committed to these values and only works with partners that adhere to them.

Have an idea for a project that will add value for arXiv's community? [**Learn more about arXivLabs**](https://info.arxiv.org/labs/index.html).

[Which authors of this paper are endorsers?](/auth/show-endorsers/2603.21362) | Disable MathJax ([What is MathJax?](https://info.arxiv.org/help/mathjax.html))