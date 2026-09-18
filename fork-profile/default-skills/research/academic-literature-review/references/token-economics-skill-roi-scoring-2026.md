# Token Economics, Skill ROI & Multi-Signal Scoring — Research Bank
*Research date: July 2026. Multi-language sweep (EN, NL, PT-BR).*

---

## 1. LLM Token Count as Proxy for Cognitive Complexity

**Core finding:** Raw token count is a *poor* proxy for reasoning quality. The research community has moved toward layer-depth signals and perplexity-based measures.

### Key papers

| Source | Description |
|--------|-------------|
| [Think Deep, Not Just Long: Measuring LLM Reasoning Effort via Deep-Thinking Tokens (arXiv 2602.13517)](https://arxiv.org/abs/2602.13517) | Google/ICML 2026. Introduces *Deep-Thinking Ratio* (DTR) — proportion of tokens whose hidden-state distributions don't converge until deeper layers. Raw token count ≠ reasoning quality; DTR shows robust positive correlation with accuracy on AIME, HMMT, GPQA-diamond. arXiv PDF: https://arxiv.org/pdf/2602.13517 |
| [ICML 2026 poster page](https://icml.cc/virtual/2026/poster/64256) | Accepted ICML 2026. Evaluated on GPT-OSS, DeepSeek-R1, Qwen3. |
| [HuggingFace paper page](https://huggingface.co/papers/2602.13517) | Community discussion thread. |
| [Measuring In-Context Computation Complexity via Hidden State Prediction (Medium)](https://medium.com/@lukasbierling/measuring-in-context-computation-complexity-of-token-generation-4501b5511513) | PHi loss (hidden state prediction error) as per-token reasoning complexity proxy. Aug 2025. |
| [Language Complexity as Zero-Shot LLM Performance Proxy (arXiv 2502.11578)](https://arxiv.org/html/2502.11578) | LIX readability metric and dependency parse depth as noisy zero-shot proxies for LLM task difficulty. Feb 2025. |
| [Why Some Puzzles Are Hard for LLMs: Cognitive Load Framework](https://ytcs.github.io/machine-learning/2025/06/08/llm-cognitive-load.html) | Cognitive Load Theory as better predictor of LLM difficulty than raw move count / token count. Token usage declines at high complexity (threshold effect). |
| [CogniLoad Benchmark (OpenReview)](https://openreview.net/forum?id=0Sex2H5Jnn) | Synthetic benchmark grounded in CLT — separates intrinsic task complexity, distractor interference, and task length. Directly useful for designing complexity signal experiments. |
| [Cognitive Load-Aware Inference (CLAI) Framework (arXiv 2507.00653)](https://arxiv.org/html/2507.00653v1) | Applies Cognitive Load Theory to optimize LLM token economy. Connects token budgeting with cognitive complexity measurement. |
| [Cognitive Load Limits in LLMs (arXiv 2509.19517)](https://arxiv.org/abs/2509.19517) | Formal theory of computational cognitive load in LLMs; reasoning fragility under load. |
| [The LLM Already Knows: Estimating Difficulty (Papers with Code)](https://paperswithcode.co/paper/2509.12886) | Hidden representations + Markov chains to estimate input difficulty — potential proxy for email/message cognitive complexity. |
| [Context Rot: Input Tokens vs LLM Performance (Chroma)](https://www.trychroma.com/research/context-rot) | Controls task complexity while varying input length — shows non-linear degradation; separates length from complexity. |
| [Measuring and Interpreting Token Usage (CodeSignal)](https://codesignal.com/learn/courses/behavioral-benchmarking-of-llms/lessons/measuring-and-interpreting-token-usage-in-llms) | Practical: completion token count as signal of response complexity. High completion tokens → more complex/detailed task. |

### Perplexity as complexity proxy

| Source | Description |
|--------|-------------|
| [Understanding Perplexity for LLM Evaluation (Medium)](https://medium.com/@adilmaqsood501/understanding-perplexity-the-key-metric-for-evaluating-large-language-models-llms-453ade06ba4f) | Perplexity inversely related to text predictability — higher perplexity → harder/more complex text. |
| [Confidence Score vs Perplexity (arXiv 2510.08596)](https://arxiv.org/html/2510.08596v1) | Proposes Confidence Score (CS) as less-biased alternative to perplexity for generation quality. Runs on gpt-4o-mini; does so 19% of the time on creative prompts. |
| [Kolmogorov Complexity + Perplexity Ratio Score (arXiv 2603.21567)](https://arxiv.org/abs/2603.21567) | Binoculars perplexity-ratio score as a Kolmogorov-complexity analog. Theoretical grounding for perplexity as complexity proxy. |

---

## 2. Alternatives to Token Count: Complexity Metrics

### 2a. Function Point Analysis (FPA)

| Source | Description |
|--------|-------------|
| [Story Points vs. Function Points (ProjectManagement.com)](https://www.projectmanagement.com/blog-post/80189/story-points-vs--function-points--fp---evaluating-the-systemic-risk-of-using-team-relative--semiquantitative-sizing-) | Compares FP (objective, standardized, technology-agnostic, ISO-approved) vs. story points (relative, team-dependent). |
| [Software Measurement Compass (LinkedIn/Saxena)](https://www.linkedin.com/pulse/software-measurement-compass-can-function-points-story-saxena-tjxqc) | FPA vs. story points vs. AI metrics — practitioner perspective. |
| [FPT-FPA: Tree-Based Function Point Analysis (Academia.edu)](https://www.academia.edu/66889159/Function_Point_Tree_Based_Function_Point_Analysis_Improving_Reproducibility_Whilst_Maintaining_Accuracy_in_Function_Point_Counting) | Improved reproducibility in FP counting via tree structure. |
| [Evaluation of Functional Size Measurement Methods (ResearchGate)](https://www.researchgate.net/publication/282921299_An_evaluation_of_functional_size_measurement_methods) | Academic comparison of FSM methods including IFPUG FPA. |
| [FPA Thesis — Leiden LIACS (PDF)](https://theses.liacs.nl/pdf/2022-2023-HuY.pdf) | 2023 thesis on FPA with automated counting approaches. |

### 2b. Cognitive Complexity Metrics (Halstead / McCabe / SonarQube)

| Source | Description |
|--------|-------------|
| [Halstead Complexity Measures — Wikipedia](https://en.wikipedia.org/wiki/Halstead_complexity_measures) | Operators/operands → volume, difficulty, effort. Originally for code; adaptable framework. |
| [Cognitive Complexity measure as understandability predictor (ScienceDirect)](https://www.sciencedirect.com/science/article/pii/S0164121222002370) | Empirical evaluation: SonarQube Cognitive Complexity (2018) correlates with code understandability similarly to McCabe. |
| [Complementarity in Software Complexity Metrics (ScienceDirect 2025)](https://www.sciencedirect.com/science/article/pii/S0164121225003486) | McCabe cyclomatic, Halstead, and Cognitive Complexity are complementary — each captures a different dimension. |
| [Cognitive Complexity: Theory & Applications (EmergentMind)](https://www.emergentmind.com/topics/cognitive-complexity) | Information-theoretic metrics, algorithmic abstractions, structural analyses across multiple domains. |
| [Cognitive Complexity Overview and Evaluation (ResearchGate)](https://www.researchgate.net/publication/326562432_Cognitive_complexity_an_overview_and_evaluation) | Survey of CC issues in open source projects. |
| [Demystifying Code Complexity (TIOBE)](https://www.tiobe.com/knowledge/article/demystifying-code-complexity/) | Comparative walkthrough: McCabe, NPath, cognitive complexity, Halstead as complementary lenses. |

### 2c. Task Complexity via Cognitive Load Theory

| Source | Description |
|--------|-------------|
| [CLT Approach to Defining Task Complexity (Springer 2023)](https://link.springer.com/article/10.1007/s10648-023-09782-w) | Complexity as *element interactivity* — number of interacting information elements. Direct framework for knowledge work complexity. |
| [Same — ResearchGate](https://www.researchgate.net/publication/371238692_A_Cognitive_Load_Theory_Approach_to_Defining_and_Measuring_Task_Complexity_Through_Element_Interactivity) | Open access version. |
| [Evaluating cognitive complexity in practice-based learning (TandF 2026)](https://www.tandfonline.com/doi/full/10.1080/0144929X.2026.2676751) | Multidimensional framework for cognitive complexity; empirically relates to knowledge gain across 5 learning modules. |
| [Quantifying Task Complexity via Generalized Information Entropy (OpenReview)](https://openreview.net/forum?id=vcKVhY7AZqK) | Information entropy as task complexity measure; proves sub-additivity. Theoretical grounding. |
| [Cognitive Task Analysis and Workload Classification (ScienceDirect)](https://www.sciencedirect.com/science/article/pii/S2215016121000285) | CTAWC — standardized process to decompose cognitive tasks and identify workload sources. |

### 2d. Prioritization/Scoring Frameworks (RICE, WSJF — as lightweight complexity proxies)

| Source | Description |
|--------|-------------|
| [17 Prioritization Frameworks Guide (bool.dev)](https://bool.dev/blog/detail/prioritization-frameworks) | RICE, WSJF, Weighted Scoring, Risk-Based — practical overview with use-case mapping. |
| [Product Prioritization Guide 2026 (ProductLift)](https://www.productlift.dev/blog/product-prioritization-framework/) | Weighted scoring, WSJF, Kano — framework selection criteria. |

---

## 3. Skill ROI Measurement in L&D

### Kirkpatrick / Phillips model family

| Source | Description |
|--------|-------------|
| [Kirkpatrick + Phillips ROI Model Overview (Learnifier)](https://www.learnifier.com/blog/how-to-measure-learning-impact-kirkpatrick-model) | 5-level model: Reaction → Learning → Behavior → Results → Financial ROI. The dominant framework. |
| [Phillips ROI Model: 5 Levels (Whatfix)](https://whatfix.com/blog/phillips-roi-model/) | Detailed walkthrough of Phillips extension. |
| [From Kirkpatrick to Predictive Analytics (WorldTeachPathways)](https://www.worldteachpathways.com/news/measure-training-program-effectiveness) | Beyond Kirkpatrick — predictive analytics for training ROI. |
| [Training Evaluation Methods (Mindstamp)](https://mindstamp.com/blog/training-evaluation-methods) | 7 methods; Phillips ROI as 5th level beyond Kirkpatrick. |
| [Kirkpatrick-based ROI (Liberateglobal)](https://www.liberateglobal.com/blogs/determining-the-training-roi-using-kirkpatricks-model-of-training-evaluation) | Structured walkthrough of each level with practical metrics. |

### Practical L&D ROI guides

| Source | Description |
|--------|-------------|
| [L&D ROI Measurement Guide 2026 (InfluenceFlow)](https://influenceflow.io/resources/learning-and-development-roi-measurement-a-comprehensive-2026-guide-to-proving-training-value/) | 2026 guide; compares online vs. in-person training ROI using the same framework. |
| [How to Measure L&D ROI: 7 Proven Methods (Intellum)](https://www.intellum.com/resources/blog/roi-of-learning-and-development) | Baseline → training → reassessment; tracks skill lift and time-to-proficiency. |
| [L&D Metrics that Prove ROI (Acorn)](https://acorn.works/blog/learning-and-development-metrics) | Capability maps + competency frameworks as foundation. Can't use metrics in isolation. |
| [Training ROI Framework for L&D (Illumeo)](https://www.illumeo.com/training-roi-a-framework-for-ld-professionals/) | Pre/post assessments, performance appraisals, supervisor feedback. |
| [Measuring ROI in L&D (Access Group)](https://www.theaccessgroup.com/en-gb/digital-learning/resources/measuring-roi-in-learning-and-development/) | UK perspective; skill application and behavior change as ROI evidence. |
| [L&D ROI — Corporate Finance Institute](https://corporatefinanceinstitute.com/resources/team-development/measuring-the-roi-of-your-learning-and-development-program/) | Quantifiable metrics + stakeholder demonstration. |
| [ROI L&D — Pluralsight](https://www.pluralsight.com/resources/blog/business-and-leadership/roi-learning-and-development) | Tech-skills focus: new hire engagement, training hour reduction, skill acquisition speed. |
| [Training ROI: Maximize (FrontlineOn)](https://frontlineon.com/blog/maximize-training-roi/) | Kirkpatrick 4 levels with Phillips Level 5 extension — practical formula. |

---

## 4. Knowledge Management ROI (Saint-Onge, Milton, APQC)

### Nick Milton

| Source | Description |
|--------|-------------|
| [The KM ROI Question (nickmilton.com, 2023)](http://www.nickmilton.com/2023/05/the-km-roi-question-problem-or.html) | KM ROI is hard to predict upfront; demonstrate via pilot projects instead. |
| [Nick Milton: KM Thought Leader #94 (Medium/Garfield)](https://stangarfield.medium.com/knowledge-management-thought-leader-94-nick-milton-93b4fd72292c) | Profile: lessons learned, knowledge capture programs, Knoco consulting. |
| [KM's Not Dead, But ROI Should Be (Medium/Garfield)](https://stangarfield.medium.com/kms-not-dead-but-talking-about-its-roi-should-be-adf7e26b6d0c) | References Milton's BP Group KM ROI measurement methodology and practical steps. |
| [Nick Milton on LinkedIn: KM ROI](https://www.linkedin.com/posts/nickmilton_the-km-roi-question-a-problem-or-an-activity-7061711176270766080-FUOl) | ISO30414 Human Capital Reporting as KM metrics framework. |
| [Lucidea: Nick Milton KM Thought Leader profile](https://lucidea.com/blog/km-thought-leader-nick-milton/) | Overview of Milton's consulting focus areas. |

### Hubert Saint-Onge

| Source | Description |
|--------|-------------|
| [Hubert Saint-Onge: Profiles in Knowledge (Medium)](https://stangarfield.medium.com/hubert-saint-onge-profiles-in-knowledge-e10ee646e3cf) | Knowledge Assets Framework — integrates business plans, people management, technology, organizational infrastructure. Intellectual capital as intangible asset management. |
| [Saint-Onge Conversation (ResearchGate)](https://www.researchgate.net/publication/241707146_A_conversation_with_Hubert_Saint-Onge) | KM strategy as framework for managing intangible organizational assets. |
| [Saint-Onge Smart Community Seminar (Waterloo)](https://infranet.uwaterloo.ca/index.php?MenuItemID=125) | Knowledge Assets Framework for strategic integration of business plans with people management systems. |
| [Intellectual Capital Express Exec (PDF/vdoc.pub)](https://vdoc.pub/documents/intellectual-capital-express-exec-7tn8tkup1ci0) | Broader intellectual capital framework (with Saint-Onge contributions). |

### APQC

| Source | Description |
|--------|-------------|
| [APQC KM Strategic Framework (interactive)](https://www.apqc.org/expertise/knowledge-management/interactive-km-framework) | APQC's canonical KM framework with measurement components. The de facto industry standard. |
| [APQC KM Maturity Model (APQC blog)](https://www.apqc.org/blog/knowledge-management-maturity-model-resources-examples-and-tools) | 5-level KM maturity: Initial → Aware → Defined → Managed → Optimized. Measurement at each level. |
| [APQC KM Framework — ResearchGate figure](https://www.researchgate.net/figure/The-APQC-Knowledge-management-framework-APQC-1996-Bukowitz-and-Williams-1999_fig2_34002564) | Visual: 1996 framework with enablers (strategy, culture, measurement, technology). |
| [KM Frameworks: 6 Types & 5 Models (Slite)](https://slite.com/learn/knowledge-management-frameworks) | SECI, APQC, 90-10 rule — accessible comparison. |
| [InfoToday 2002: 114 KM Indices](https://www.infotoday.com/it2002/KnowledgeNets.htm) | 9 KM principles → 114 key indices for measuring organizational KM potential. |
| [KM ROI: 2026 Walkthrough (aiproductivity.ai)](https://aiproductivity.ai/guides/knowledge-management-roi/) | Core KM ROI Metrics Framework: time savings, error reduction, headcount efficiency. |
| [How to Measure KM Success: KPIs, Dashboards, ROI (KMInsider)](https://kminsider.com/blog/measure-knowledge-management-success-kpis-roi/) | Practical KPIs + executive dashboard guidance. |
| [KM ROI detailed (KMInsider)](https://kminsider.com/blog/knowledge-management-roi/) | Core KM ROI metrics with real benchmarks. |

---

## 5. Talent Intelligence Platforms: Skill Scoring Methodologies

### Overview / Comparison

| Source | Description |
|--------|-------------|
| [AI Talent Intelligence 2026 Buyer's Guide (Knowlee)](https://www.knowlee.ai/blog/ai-talent-intelligence) | **Best overview.** Compares Eightfold, Beamery (Ray), Gloat (Loomra), Phenom + Included. Covers 9-box, predictive turnover, career paths, skill scoring. |
| [8 Best Talent Intelligence Platforms (HRTechSaaS)](https://hrtechsaas.com/blog/best-talent-intelligence-platforms/) | Eightfold, Gloat, Beamery, Findem: skills inference accuracy varies dramatically across vendors. |
| [Talent Intelligence Platforms 2026 Buyer's Guide (Truffle)](https://www.hiretruffle.com/blog/talent-intelligence-platforms) | Comparison: Eightfold, Beamery, Phenom, Gloat. |
| [Best TI Platforms for Enterprise (BestRecruitingTools)](https://bestrecruitingtools.com/blog/best-talent-intelligence-platforms-enterprise-2026) | Enterprise comparison: Eightfold, Beamery, SeekOut, Gloat, Phenom, Visier, LinkedIn Talent Insights. |

### Eightfold AI

| Source | Description |
|--------|-------------|
| [Eightfold Skills Intelligence page](https://eightfold.ai/solutions/skills-intelligence/) | Deep-learning model trained on 1B+ career trajectories. Infers adjacent skills and potential. Skills-based matching beyond job title. |
| [Eightfold AI Deep Dive (DigiDai 2025)](https://digidai.github.io/2025/07/05/eightfold-ai-deep-dive/) | Talent Graph construction from resume + performance + project history. |
| [Eightfold AI Review 2026 (AIMadeFor)](https://www.aimadefor.com/blog/eightfold-ai-review-hr/) | Per-employee skills graph → lateral moves, stretch assignments, promotion paths. |
| [Eightfold AI — Overview (youraifinder)](https://youraifinder.com/tool/eightfold-ai) | Next-gen platform: deep learning on hundreds of millions of career trajectories. |

### Beamery

| Source | Description |
|--------|-------------|
| [Beamery Skills Data Platform](https://beamery.com/skills-platform/) | Knowledge graph methodology — skills data → actionable HR insights. |
| [Beamery Skills Intelligence Platform](https://beamery.com/platform/data-platform/skills-intelligence/) | "Skills-first" approach to hiring, development, and planning. |
| [How We Manage Skills @ Beamery — Part I (Medium 2022)](https://medium.com/hacking-talent/skills-beamery-part-1-representing-skills-for-today-and-the-unknown-of-tomorrow-d87e114771a3) | **Technical deep dive.** Beamery Knowledge Graph (BKG). Skills as first-class citizens. Supply (talent skills) vs. demand (job skills). |
| [How We Manage Skills @ Beamery — Part II (Medium 2022)](https://medium.com/hacking-talent/skills-beamery-part-2-disaggregating-a-skill-72fa4f4d1cfa) | Skill provenance > skill entity. Disaggregation framework. |
| [Beamery Dynamic Work Architecture — Skills (Support)](https://support.beamery.com/hc/en-us/articles/22734283218961-Dynamic-Work-Architecture-Understanding-Skills) | Core attributes of skills in the BKG. |
| [Beamery AI Talent Match FAQ](https://support.beamery.com/hc/en-us/articles/9867879374353-Beamery-AI-Talent-Match-FAQ) | Adjacent skills inference via Skills API. Intersectionality-based match score. |
| [Beamery Customized Skills Framework](https://info.beamery.com/skills-framework) | Company-specific skills insights methodology. |

### Gloat

| Source | Description |
|--------|-------------|
| [Gloat Workforce Graph](https://gloat.com/platform/workforce-graph/) | AI-driven skill mapping. Identifies hidden talent. Skills inferred from project assignments, role moves, learning completions. |
| [Gloat Talent Marketplace](https://gloat.com/platform/the-talent-marketplace/) | AI-guided learning + career recommendations based on current skills and aspirations. |
| [Gloat Workforce Insights](https://resources.gloat.com/workforce-insights/) | Skills utilization + productivity metrics dashboard. |
| [Gloat on Josh Bersin (2023)](https://joshbersin.com/2023/07/building-a-skills-based-organization-the-exciting-but-sober-reality/) | Analyst view: Gloat's "workforce agility" positioning and skill graph strategy. |
| [Gloat Skills Graph (ooligo.com)](https://ooligo.com/en/tools/gloat/) | Platform value compounds with usage — every action enriches skills graph for future matching. |

---

## 6. Rank Aggregation Methods

| Source | Description |
|--------|-------------|
| [Borda Count as Initial Threshold for Kemeny (ResearchGate)](https://www.researchgate.net/publication/354605887_The_Borda_Count_as_an_Initial_Threshold_for_Kemeny_Ranking_Aggregation) | **Key paper.** 104 algorithms compared. Borda as warm-start for Branch-and-Bound Kemeny — improves execution time. |
| [Same — Atlantis Press (full proceedings)](https://www.atlantis-press.com/proceedings/ifsa-eusflat-agop-21/125960346) | IFSA-EUSFLAT-AGOP 2021 proceedings version. |
| [Towards Foundation Models for Consensus Rank Aggregation (arXiv 2603.15218)](https://arxiv.org/abs/2603.15218) | **2026 SOTA.** Foundation model for Kemeny-optimal consensus ranking. Addresses NP-hardness with learned approximation. Applications: recommendation, search, job recruitment. |
| [Same — HTML version](https://arxiv.org/html/2603.15218v1) | Readable HTML. Condorcet criterion, Condorcet paradox handling. |
| [Rank Aggregation Using Scoring Rules (Springer/Theory & Decision 2025)](https://link.springer.com/article/10.1007/s11238-025-10120-5) | Distinguishes ranking-by-score, ranking-by-winner, ranking-by-loser. Covers Plurality, Veto, Borda. |
| [Rank Aggregation via Scoring Rules — slides (Dominik Peters)](https://www.dominik-peters.de/slides/ranking-by-scoring-slides.pdf) | Presentation slides. Borda, plurality, veto scoring systems. |
| [Analysis of Rank Aggregation Algorithms (arXiv 1402.5259)](https://arxiv.org/pdf/1402.5259) | Implements Borda + Kemeny DP + heuristics; performance comparison. |
| [Kemeny Method — Wikipedia](https://en.wikipedia.org/wiki/Kemeny_method) | Canonical reference: maximizes pairwise agreement = minimizes Kendall tau distance. Also known as VoteFair popularity ranking, maximum likelihood method. |
| [Kemeny Optimal Aggregation — Overview (FlyRiver)](https://www.flyriver.com/kemeny-optimal-aggregation) | Accessible explanation of Kemeny's rule. |
| [Kemeny Ranking Aggregation meets the GPU (Springer)](https://link.springer.com/article/10.1007/s11227-023-05058-w) | GPU-accelerated Kemeny for scale. |
| [Kemeny-Young GitHub solver](https://github.com/juanromerohb/kemeny-young) | Web app and solver for Kemeny-Young method. Minimizes Kendall tau distance. |
| [Schulze Method — Wikipedia](https://en.wikipedia.org/wiki/Schulze_method) | Beat-path method. Condorcet-consistent. Handles cyclic preferences via widest-path computation. |
| [Schulze Method Calculator (MetricGate)](https://metricgate.com/docs/schulze-method-ranking/) | Practical widest-path algorithm explanation + calculator. |
| [New Method for Schulze Winner Set (arXiv 2606.02213)](https://arxiv.org/abs/2606.02213) | 2026 paper: new efficient algorithm eliminating weaker candidates via all-pairs comparisons. |
| [Condorcet Matrix Analysis (MetricGate)](https://metricgate.com/docs/condorcet-matrix-analysis/) | When no Condorcet winner exists: Copeland, Schulze, ranked pairs, minimax comparisons. |
| [Effective Signal Reconstruction from Multiple Ranked Lists (Springer)](https://link.springer.com/article/10.1007/s10618-023-00991-z) | Convex optimization for combining ranked signals. Connection between score recovery and rank aggregation. |

---

## 7. Shapley Value for Multi-Factor Scoring Attribution

| Source | Description |
|--------|-------------|
| [Shapley Value — Wikipedia](https://en.wikipedia.org/wiki/Shapley_value) | Canonical: Efficiency, Symmetry, Dummy, Additivity axioms. Fair attribution guarantees. |
| [Interpretable ML Book — Chapter 17: Shapley Values (Christoph Molnar)](https://christophm.github.io/interpretable-ml-book/shapley.html) | **Best practitioner reference.** Properties, computation, feature importance application. Open access. |
| [Shapley Value for ML Models (Towards Data Science)](https://towardsdatascience.com/the-shapley-value-for-ml-models-f1100bff78d1/) | Dummy/Symmetry/Monotonicity properties; practical for scoring models. |
| [Algorithms to Estimate Shapley Value Attributions (Nature MI 2023)](https://www.nature.com/articles/s42256-023-00657-x) | Comprehensive review: Monte Carlo, regression-based, model-specific estimation. |
| [Shapley Value Overview (Springer 2024)](https://link.springer.com/article/10.1007/s43684-023-00060-8) | Comprehensive overview of Shapley-based attribution + cooperative game theory connection. |
| [ShaRP: Shapley for Rankings and Preferences (arXiv 2401.16744)](https://arxiv.org/abs/2401.16744) | **Directly applicable.** Shapley values for *rankings*, not just scores. Rank-aware QoIs (rank, top-k, pairwise preference). Published VLDB 2025. |
| [ShaRP — VLDB 2025 (ACM DL)](https://dl.acm.org/doi/10.14778/3749646.3749682) | Peer-reviewed published version. |
| [ShaRP — HTML v4](https://arxiv.org/html/2401.16744v4) | Score-based and learned rankers. Explains feature contributions to rank position and top-k inclusion. |
| [RankSHAP: Shapley for Learning-to-Rank (arXiv 2405.01848)](https://arxiv.org/html/2405.01848v2) | Listwise Shapley attribution for ranking models specifically. |
| [Shapley Value Attribution (EmergentMind)](https://www.emergentmind.com/topics/shapley-value-attribution) | Topic overview: Monte Carlo, regression, model-specific estimation. |
| [SageMaker Clarify: Shapley Values (AWS docs)](https://docs.aws.amazon.com/sagemaker/latest/dg/clarify-shapley-values.html) | Production implementation reference. Per-prediction + global attribution. |
| [Shapley Value Attribution: Fair Credit (GrowthMethod)](https://growthmethod.com/shapley-value-attribution/) | Accessible explanation: weighted average of marginal contributions across all coalitions. |
| [Cooperative Game Theory: Core and Shapley (Frontiers in Applied Mathematics)](https://www.frontiersin.org/journals/applied-mathematics-and-statistics/articles/10.3389/fams.2024.1332352/full) | Theoretical foundations. Core + Shapley compared. |

---

## 8. Ensemble / Stacking for Multi-Signal Combination

| Source | Description |
|--------|-------------|
| [Ensemble Learning — Wikipedia](https://en.wikipedia.org/wiki/Ensemble_learning) | Canonical: bagging, boosting, stacking/blending. |
| [Stacking Ensemble Method (Towards Data Science)](https://towardsdatascience.com/the-stacking-ensemble-method-984f5134463a/) | Meta-learner combining base models — applicable to combining token count, seniority, org benefit signals. |
| [Stacking Ensemble with Python (MachineLearningMastery)](https://machinelearningmastery.com/stacking-ensemble-machine-learning-with-python/) | Practical implementation guide with sklearn. |
| [H2O Stacked Ensembles (H2O docs)](https://docs.h2o.ai/h2o/latest-stable/h2o-docs/data-science/stacked-ensembles.html) | Production: finds optimal combination via metalearner automatically. |
| [Ensembles: Accuracy-Energy Trade-offs in Recommender Systems (arXiv 2604.07869)](https://arxiv.org/html/2604.07869) | Hybrid aggregation, averaging, weighting, stacking, boosting, rank fusion in recommender systems. Apr 2026. |

---

## 9. Skill Gap Analysis Methodologies

| Source | Description |
|--------|-------------|
| [PGA vs SGA vs CGA — PeopleManager Community](https://community.peoplemanager.online/bridging-the-gaps-are-you-measuring-what-truly-matters-in-workforce-development/) | Distinguishes Performance Gap Assessment (PGA), Skill Gap Analysis (SGA), and Competency Gap Analysis (CGA) — not interchangeable. |
| [AI Impact on Workers' Skills (ResearchGate)](https://www.researchgate.net/publication/368721087_The_impact_of_artificial_intelligence_on_workers'_skills_Upskilling_and_reskilling_in_organisations) | Validates skill gap identification methodology; upskilling/reskilling in AI-affected organizations. |
| [WorkforceAI Methodology](https://workforceai.ai/workforce-methodology) | Competitor benchmarking, skills gap analysis, critical-role mapping with AI. |

---

## 10. Human Capital & Skill Valuation Economics

| Source | Description |
|--------|-------------|
| [Skills and Human Capital in the Labor Market (NBER w32908)](https://www.nber.org/papers/w32908) | Comprehensive synthesis: returns to human capital (micro + macro), higher-order skills (social, decision-making). Sep 2024. |
| [NBER w32908 PDF](https://www.nber.org/system/files/working_papers/w32908/w32908.pdf) | Direct PDF. Returns to schooling; cognitive skills; college quality. |
| [Human Capital Depreciation + Returns to Experience (NBER w27925 PDF)](https://www.nber.org/system/files/working_papers/w27925/w27925.pdf) | Skill depreciation rates from non-formal employment — important for time-decay of skill value in scoring models. |
| [Human Capital — Investopedia](https://www.investopedia.com/terms/h/humancapital.asp) | Baseline ROI formula: total profits / total investment in human capital. |

---

## 11. Dutch-Language Resources

| Source | Description |
|--------|-------------|
| [Kennismanagement — Wikipedia NL](https://nl.wikipedia.org/wiki/Kennismanagement) | Dutch overview of knowledge management as multidisciplinary organizational discipline. |
| [Competentie management (Bapas.nl)](https://bapas.nl/organisatie-ontwikkeling/competentie-management/) | Dutch: systematic competency development, deployment, and alignment to organizational goals. |
| [Competenties meten — WUR Wageningen (PDF)](https://edepot.wur.nl/118423) | Dutch academic paper: valid competency-based measurement methodology. |
| [Competenties in de praktijk (Managementboek.nl/Jongbloed)](https://www.jongbloed.nl/trefwoord/competenties) | Dutch: STAR method, assessment, competency development, certification books. |
| [Competenties Rijk (P-Direkt NL)](https://www.p-direkt.nl/informatie-rijkspersoneel-2020/mijn-werk/loopbaan-en-ontwikkeling/ontwikkelvragen/competenties) | Dutch Government competency guide — ~40 competencies for civil servants. |

---

## 12. Portuguese-Language Resources

| Source | Description |
|--------|-------------|
| [ROI em Treinamento Corporativo: Guia Completo (Eagles Flight BR)](https://br.eaglesflight.com/roi-em-treinamento-corporativo-guia-completo-para-medir-e-maximizar-retorno/) | PT-BR: Complete guide to measuring and maximizing training ROI. Practical vs. theoretical assessment. |
| [Gestão por competências: métodos e técnicas (ENAP PDF)](https://repositorio.enap.gov.br/jspui/bitstream/1/7478/1/8728-Texto+do+Artigo-30278-1-10-20221124.pdf) | PT-BR: Competency mapping methods; CHA framework (Conhecimento, Habilidade, Atitude). |
| [Mapeamento de competências humanas (FEBAB/RBBD PDF)](https://rbbd.febab.org.br/rbbd/article/download/1603/1345) | PT-BR: Mapping human competencies and knowledge in organizations. |
| [Desenho de modelo de competências (Universidade de Évora PDF)](http://dspace.uevora.pt/rdpc/bitstream/10174/24162/1/Mestrado-Gestão_Recursos_Humanos-Ana_Teresa_Pena_Severino-Desenho_de_um_modelo_de_competências....pdf) | PT (Portugal): Boyatzis competency model adapted for HR; intrinsic characteristics → performance. |
| [Framework de Competências Auditoria Interna (IIA Global PT-BR PDF)](https://www.theiia.org/globalassets/site/content/guidance/recommended/supplemental/practice-guides/global-practice-guide-internal-auditing-competency-framework/gpg_internal_auditing_competency_framework_portuguese-brazil.pdf) | PT-BR: IIA competency framework — 4 groupings, 28 subcategories, 4 proficiency levels. |

---

## Key Synthesis Notes for Future Research

1. **Token count as complexity proxy is established as *problematic* in the literature** — the DTR paper (arXiv 2602.13517) is the sharpest citation for this claim. Better proxies: DTR, PHi loss, perplexity, element interactivity (CLT).

2. **For ranking multiple scoring signals**: Kemeny-Young is theoretically optimal but NP-hard; Borda is the polynomial-time practical approximation; Schulze handles cyclic preferences. The 2026 foundation-model approach (arXiv 2603.15218) is the latest SOTA for learned approximation.

3. **For attributing fair credit to multiple features in a score**: ShaRP (arXiv 2401.16744, VLDB 2025) is the directly applicable framework — Shapley values specifically for *rankings*, not just point predictions.

4. **Talent platform skill scoring**: All three major platforms (Beamery, Eightfold, Gloat) use graph-based inference, not raw resume parsing. Beamery treats skill *provenance* as more important than the skill entity itself — a key differentiator.

5. **KM ROI is notoriously hard to predict upfront** (Nick Milton's core claim) — the practical path is demonstrating value through pilot projects, not upfront ROI predictions.
