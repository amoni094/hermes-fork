# Cognitive Bias Correction & ML/AI Skill Scoring Reference Bank (July 2026)

Covers: optimism bias correction, Bayesian/Monte Carlo estimation, multi-armed bandit skill recommendation, learning curve theory (Wright's Law), knowledge graph-based skill recommendation, LLM skill extraction, ONA for skill impact by seniority/centrality.

---

## 1. Optimism Bias Correction & Planning Fallacy

### Foundational Theory

| Source | URL | Notes |
|--------|-----|-------|
| Reference Class Forecasting — Wikipedia | https://en.wikipedia.org/wiki/Reference_class_forecasting | Core: Kahneman/Tversky "outside view". Starting point for RCF. |
| Planning Fallacy — Wikipedia | https://en.wikipedia.org/wiki/Planning_fallacy | Canonical definition, links to mitigation strategies. |
| Lovallo & Kahneman (2003) "Delusions of Success" — HBR | https://hbr.org/2003/07/delusions-of-success-how-optimism-undermines-executives-decisions | Seminal HBR article. Anchoring + competitor neglect → systematic over-optimism. |
| Delusions of Success (free PDF via UC Davis) | https://faculty.econ.ucdavis.edu/faculty/nehring/teaching/econ106/readings/Lovallo-Kahneman-Optimism-HBR+July+2003.pdf | Full paper, free access. |
| Delusions of Success — Semantic Scholar | https://www.semanticscholar.org/paper/Delusions-of-success.-How-optimism-undermines-Lovallo-Kahneman/d1705ed0ac5c8eb5b86d7704a2ceab52e91eecf4 | Citation network for follow-on work. |

### RCF in Practice / Flyvbjerg

| Source | URL | Notes |
|--------|-----|-------|
| RCF: Promises, Problems — Tandfonline (2025) | https://www.tandfonline.com/doi/full/10.1080/09537287.2025.2578708 | Critical review for megaprojects; surfaces hybrid approaches. |
| Reducing Risks via RCF — ScienceDirect (2023) | https://www.sciencedirect.com/science/article/pii/S2666721523000248 | Comprehensive literature review. Uplift factor methodology. |
| Kahneman's Legacy in Project Mgmt — ScienceDirect (2025) | https://www.sciencedirect.com/science/article/pii/S0263786325000249 | Applies outside view to time/cost estimation improvement. |
| From Nobel Prize to PM — PMI | https://www.pmi.org/learning/library/nobel-project-management-reference-class-forecasting-8068 | Step-by-step RCF application methodology. |
| RCF for Hong Kong Roadworks (Flyvbjerg) — arXiv PDF | https://arxiv.org/pdf/1710.09419 | Concrete uplift factor tables. Adaptable for business case estimation. |
| How Big Things Get Done — Flyvbjerg (Penguin) | https://www.penguinrandomhouse.com/books/672118/how-big-things-get-done-by-bent-flyvbjerg-and-dan-gardner/ | 2023 book. "Think slow, act fast", "Find your Lego" heuristics. |
| Top Ten Behavioral Biases in PM — arXiv PDF | https://arxiv.org/pdf/2202.00125 | Flyvbjerg's taxonomy: optimism bias + strategic misrepresentation + planning fallacy, each requiring different correction. |
| Biases in Project Estimating — ICEAA (2025 PDF) | https://www.iceaaonline.com/wp-content/uploads/2025/06/PBP02-Glauser-Biases-in-Project-Estimating-paper.pdf | Mitigation strategies for anchoring, sunk cost, optimism bias. |

### RICE/WSJF Improvement

| Source | URL | Notes |
|--------|-----|-------|
| AI-Enhanced RICE Scoring — MindBacklog (2026) | https://mindbacklog.com/blog/the-ultimate-guide-to-feature-prioritization-12-frameworks-compared/ | Calibrates confidence from evidence volume/quality. |
| RICE vs WSJF — CenterCode | https://www.centercode.com/blog/rice-vs-wsjf-prioritization-framework | Comparison; WSJF's Cost of Delay is better for time-sensitive skill value. |
| Monte Carlo for Product Prioritization — Medium | https://medium.com/@aahammer/lets-try-quantitative-product-priorization-decisions-with-monte-carlo-simulation-1d0af9d7b338 | Replace point-estimate RICE with probability distributions + Monte Carlo. |

---

## 2. Bayesian Priors & Monte Carlo Uncertainty

| Source | URL | Notes |
|--------|-----|-------|
| Monte Carlo + Bayesian Networks for Project Completion — PMC | https://pmc.ncbi.nlm.nih.gov/articles/PMC6950629/ | Full text. Integrates BN (risk dependency) with MC (uncertainty). |
| Monte Carlo for Risk Prioritization — Springer (2024) | https://link.springer.com/chapter/10.1007/978-3-031-57996-7_78 | Avoids probability-impact matrix. Applicable to skill/feature scoring. |
| Bayesian Methods + Monte Carlo — IntechOpen (2022) | https://www.intechopen.com/chapters/84891 | Foundational: combining Bayesian priors with MC sampling. |
| Bayesian Monte Carlo — Rasmussen & Ghahramani (Cambridge PDF) | https://mlg.eng.cam.ac.uk/zoubin/papers/RasGha03.pdf | Classic ML paper. Sample-efficient alternative to plain MCMC. |
| Software Effort Estimation with Bayesian Updating — Springer (2021) | https://link.springer.com/article/10.1007/s10664-021-10103-4 | Empirical study applying Bayesian updating to correct estimation bias. |
| Monte Carlo in Project Management — ProjectWizards (2026) | https://www.projectwizards.net/en/blog/2026/07/monte-carlo-simulation-project-management | "80% confident by October 15" framing. Communicating probabilistic estimates. |
| Monte Carlo in Agile — Devoteam | https://www.devoteam.com/expert-view/embracing-uncertainty-with-monte-carlo-simulations-in-agile/ | Agile-specific. Replace story point estimates with distribution-based forecasts. |

---

## 3. Multi-Armed Bandit for Skill Recommendation

| Source | URL | Notes |
|--------|-----|-------|
| Bandit-Based Educational Recommender: Thompson Sampling — arXiv (2026) | https://arxiv.org/abs/2602.04347 | **Most directly relevant.** Contextual Thompson Sampling for skill gain optimization in educational recommender. |
| Active Learning-Based MAB for Recommendation — Springer (2025) | https://link.springer.com/article/10.1007/s10115-025-02502-6 | MAB + active learning; adapts to evolving skill needs. |
| MAB in Recommendation Systems Survey — ScienceDirect | https://www.sciencedirect.com/science/article/pii/S0957417422001543 | Design, evaluation, best practices for MAB recommenders. Cold-start handling. |
| Multi-Armed Bandits Meet LLMs — arXiv (2025) | https://arxiv.org/html/2505.13355v1 | LLM semantics + bandit exploration policy for skill ranking. |
| MAB in the Wild — ACM (2025) | https://dl.acm.org/doi/10.1145/3705328.3748005 | Production challenges: implementation gotchas in live systems. |
| Mab2Rec: Bandit-Based Recommender Library — Fidelity | https://fidelity.github.io/mab2rec/ | Open-source library. Directly usable in skill recommendation pipelines. |
| Deep Bayesian Bandits for Recommendations — ACM | https://dl.acm.org/doi/fullHtml/10.1145/3383313.3412214 | Bayesian deep bandit. Uncertainty quantification + exploration for cold-start. |
| Multi-Armed Bandits for Front Page Recommendation — ACM | https://dl.acm.org/doi/10.1145/3774935.3807907 | Production case study of MAB for recommendation strategy selection. |

---

## 4. Learning Curve Theory (Wright's Law / Experience Curve)

| Source | URL | Notes |
|--------|-----|-------|
| Experience Curve Effect — Wikipedia | https://en.wikipedia.org/wiki/Experience_curve_effect | Wright's Law: 20% cost reduction per doubling cumulative output. Foundation for skill value modeling. |
| Learning Curves — Encyclopedia of OR (Springer) | https://link.springer.com/rwe/10.1007/1-4020-0611-X_526 | Power law of practice, Wright's cumulative average model, individual vs org learning. |
| Learning Curve Analysis — Encyclopedia of Prod. Mgmt (Springer) | https://link.springer.com/rwe/10.1007/1-4020-0612-8_504 | Analysis for manufacturing and skill development estimation. |
| Learning Curves — Mind Tools | https://www.mindtools.com/avhnogk/learning-curves/ | Practitioner guide: how experience curves apply to organizational learning. |
| Learning Curve Calculator (Wright's Model) | https://mytimecalculator.com/learning-curve-calculator | Interactive: Wright, Power Law, Cost, and Experience models. |

---

## 5. Knowledge Graph-Based Skill Recommendation

| Source | URL | Notes |
|--------|-----|-------|
| JobEdKG: Uncertain KG for Job/Skill Recommendation — ScienceDirect (2024) | https://www.sciencedirect.com/science/article/pii/S0952197623019632 | KG built over job descriptions + education. Recommends courses + predicts future skill needs. Uncertainty-aware. |
| KG-Integrated Recommendation for Career Planning — Springer (2026) | https://link.springer.com/article/10.1007/s44163-026-00996-9 | KG construction + collaborative filtering for personalized career recommendations. |
| Personalized Job Recommendation via KG + GNN — ResearchGate (2024) | https://www.researchgate.net/publication/379685228_Personalized_Context-Oriented_Job_Recommendation_System_Based_On_Knowledge_Graph | Context-oriented job/skill recommendation. GNN over knowledge graph. |
| 融合知识图谱的推荐系统研究进展 (ZJU Journal, 2023) 🇨🇳 | https://www.zjujournals.com/eng/article/2023/1008-973X/202308006/Table1.html | Survey: comparison table of KG recommendation algorithms. |
| 利用知识图谱的推荐系统研究综述 (CEA Journal) 🇨🇳 | http://cea.ceaj.org/CN/10.3778/j.issn.1002-8331.2209-0033 | Chinese survey: KG recommenders for data sparsity and cold-start. |
| ESCO Ontology — European Commission | https://ec.europa.eu/esco/lod/static/model.html | EU standard skills/occupations taxonomy in RDF. Reference for skill graph construction. |
| EmployChain ESCO Skill Recommender — CINECA HPC | https://www.hpc.cineca.it/poc/employchain_esco-building-a-skill-recommender-system-for-the-job-matching-app-employchain-by-integrating-the-esco-ontology/ | Practical: KG + ESCO for skill-based job matching. |
| Career Path Prediction via Resume RL — arXiv/CEUR (2023) | https://ceur-ws.org/Vol-3490/RecSysHR2023-paper_1.pdf | Textual job descriptions rather than career history. Closer to email/comms extraction use case. |
| RecruiterGCN: Cold-Start Job Rec via Heterogeneous Graphs — HAL | https://hal.science/hal-04250416/document | GCN for cold-start recommendations. Beats state-of-art on top-N. |
| LLM KG Retrieval for Recommender Systems — ACL (2025) | https://aclanthology.org/2025.acl-long.1317/ | RAG + KG for LLM-based recommenders. Addresses hallucinations + stale knowledge. |
| From "Strings" to "Things" for Personal KGs — arXiv (2607.00003) | https://arxiv.org/abs/2607.00003 | LLM triple extraction for personal KGs used in recommendation systems. Direct match to "personal brain" architecture. |

---

## 6. LLM-Based Skill Extraction & Ranking

| Source | URL | Notes |
|--------|-----|-------|
| Skill-LLM: Repurposing LLMs for Skill Extraction — arXiv (2024) | https://arxiv.org/html/2410.12052v1 | Fine-tunes general LLMs for skill extraction. Adaptable to email/Teams content. |
| Rethinking Skill Extraction with LLMs — ACL NLP4HR (2024) | https://aclanthology.org/2024.nlp4hr-1.3/ | In-context learning across 6 datasets. Few-shot beats annotation-heavy supervised. |
| SkillGPT: LLM for Skill Extraction & Standardization — arXiv (2023) | https://arxiv.org/abs/2304.11060 | LLaMA-based. Summarization + vector similarity search for ESCO standardization. Open-source. |
| LLMs as Zero-Shot ESCO Skills Matchers — arXiv PDF (2023) | https://arxiv.org/pdf/2307.03539 | End-to-end zero-shot ESCO extraction. Strong performance without fine-tuning. |
| LLM-Supervised Multilingual Skill Extraction — Springer (2025) | https://link.springer.com/chapter/10.1007/978-3-031-97144-0_9 | Lightweight sentence encoder trained via LLM supervision. Handles implicit skills. |
| SkiLLMo: ESCO Skill Extraction via Transformers — ACM (2025) | https://dl.acm.org/doi/10.1145/3672608.3707960 | Extraction + standardization pipeline. Benchmarked against ESCO. |
| LLM-Powered KGs for Enterprise Intelligence — arXiv (2025) | https://arxiv.org/abs/2503.07993 | **Exact personal brain architecture.** Unifies emails, calendars, chats, docs into user-centric KG via LLM entity extraction. |
| KLLMs4Rec: KG-Enhanced LLM Sentiment for Recommendation — ScienceDirect | https://www.sciencedirect.com/science/article/pii/S0957417425010528 | KG enrichment + LLM sentiment analysis for personalized recommendation. |
| Skills Extraction with LLMs — Autonomy Data Unit (2023) | https://adu.autonomy.work/posts/2023_11_14_skills-extraction-w-llms/ | Practitioner benchmarks; comparison of SkillSpan and transformer approaches. |
| MindScope: Cognitive Bias in LLMs — Volcengine (华东师范) 🇨🇳 | https://developer.volcengine.com/articles/7430708452860624922 | Multi-agent LLM benchmark for detecting cognitive biases in LLM decision-making. |

---

## 7. Organizational Network Analysis (ONA) for Skill Impact

| Source | URL | Notes |
|--------|-----|-------|
| ONA — Wikipedia | https://en.wikipedia.org/wiki/Organizational_network_analysis | Foundational. Degree, betweenness, closeness centrality and how they map to influence/expertise. |
| Expertise & Specialization in Orgs: SNA — Tandfonline (2024) | https://www.tandfonline.com/doi/full/10.1080/1359432X.2024.2387874 | **Key paper.** N=344: in-degree centrality (advice requests) ↔ skill expertise. Halo effect across skill bundles. |
| Social Network Centrality → Knowledge Sharing — Springer | https://link.springer.com/article/10.1007/s12927-019-0009-2 | Closeness centrality → within-team sharing; betweenness → cross-team knowledge brokerage. |
| ONA for Workforce Inclusion — PMC (2025) | https://pmc.ncbi.nlm.nih.gov/articles/PMC12709551/ | Scoping review: centrality as indicator of influence, connectivity, gender comparison. |
| Antecedents of Betweenness Centrality Changes — ScienceDirect | https://www.sciencedirect.com/science/article/pii/S0040162516301457 | Exploration strategy (broad skill acquisition) predicts higher betweenness. Validates skill learning → network influence thesis. |
| ONA Measuring Organizational Agility — Worklytics | https://www.worklytics.co/blog/measuring-organizational-agility-via-ona | Practitioner: email/meeting metadata → ONA graphs. Relevant to email-based ONA construction. |
| Rob Cross: What is ONA? | https://www.robcross.org/what-is-organizational-network-analysis/ | Leading ONA academic practitioner. Survey vs passive ONA (email metadata). |
| Deloitte ONA for Workforce Performance | https://www.deloitte.com/us/en/services/consulting/blogs/human-capital/harnessing-organization-network-analysis.html | Enterprise-scale ONA case studies. |
| ONA: Introduction with Python — Towards Data Science | https://towardsdatascience.com/an-introduction-to-organizational-network-analysis-cfa91a0e2fda/ | Technical intro with Python examples for betweenness/degree centrality computation. |

---

## 8. Japanese Language Resources 🇯🇵

| Source | URL | Notes |
|--------|-----|-------|
| 認知バイアスの一覧 — Wikipedia | https://ja.wikipedia.org/wiki/認知バイアスの一覧 | Full list with Japanese terminology. |
| 認知バイアス (HR/企業向け) — HRプロ | https://www.hrpro.co.jp/series_detail.php?t_no=3900 | HR-focused article on cognitive biases in business decisions. |
| データのバイアス理解と複数データ源からの推論 — 総務省統計局 (慶應 星野崇宏) | https://www.stat.go.jp/info/kenkyu/sss/pdf/161227_shiryou3.pdf | **Academic PDF.** Keio University. Bayesian bias correction: 100% error → 22.7% after correction. |
| ベイズ推定スケーリング則 — 九州大学 | https://www.kyushu-u.ac.jp/ja/researches/view/852/ | Research on scaling laws for Bayesian estimation. Sample quality vs. quantity effects on posteriors. |

---

## 9. Chinese Language Resources 🇨🇳

| Source | URL | Notes |
|--------|-----|-------|
| AAAI 2024 知識図譜論文総結 — 腾訊云 | https://cloud.tencent.com/developer/article/2466804 | 22 AAAI 2024 KG papers including temporal KG, multi-modal KG. |
| 融合知识图谱的推荐系统研究进展 — 浙大学报 | https://www.zjujournals.com/eng/article/2023/1008-973X/202308006/Table1.html | ZJU survey. Comparison table of KG recommendation algorithms. |
| 利用知识图谱的推荐系统研究综述 — CEA Journal | http://cea.ceaj.org/CN/10.3778/j.issn.1002-8331.2209-0033 | Survey on KG recommenders for data sparsity and cold-start. |
| 推荐系统EE问题概述 (探索-利用) — 腾讯云 | https://cloud.tencent.com/developer/article/1164110 | Exploration-exploitation in recommenders including LinUCB, Thompson Sampling. |
| 核上下文多臂赌博机推荐算法 — 智能系统学报 | https://tis.hrbeu.edu.cn/oa/DArticle.aspx?type=view&id=202105039 | Kernel-based contextual MAB for personalized recommendation (extends LinUCB). |
| MindScope: LLM认知偏差多Agent — 火山引擎 (华东师范+复旦) | https://developer.volcengine.com/articles/7430708452860624922 | Benchmark for cognitive bias in LLMs. Relevant for auditing bias in LLM-driven scoring. |

---

## Synthesis Table: Problem → Approach → Key Links

| Problem | Recommended Approach | Key Reference |
|---------|---------------------|---------------|
| Confidence field is gut-feel (RICE) | RCF uplift factor from historical project distributions | Flyvbjerg arXiv PDF, RCF ScienceDirect (2023) |
| WSJF scores are point estimates | Monte Carlo distribution over each input variable | Monte Carlo Agile (Devoteam), Medium (aahammer) |
| Optimism bias in effort estimates | Bayesian posterior update using class distribution priors | Bayesian Updating for SEE (Springer), Keio Univ PDF |
| Skill recommendation is static | Contextual Thompson Sampling bandit (skill gain as reward) | arXiv 2602.04347 |
| Skill value doesn't decay/grow over time | Wright's Law experience curve for value growth with repetitions | Wikipedia Experience Curve, Mind Tools |
| Skill graph construction from emails/comms | LLM entity extraction → activity-centric KG | arXiv 2503.07993, Skill-LLM (arXiv 2410.12052) |
| Seniority weighting for skill impact | ONA centrality (betweenness/degree) as seniority-independent influence proxy | Tandfonline (2024) Expertise SNA, Rob Cross ONA |
| Cold-start skill recommendation | Uncertain KG (JobEdKG) + MAB exploration | JobEdKG (ScienceDirect), RecruiterGCN (HAL) |
| Skill taxonomy standardization | ESCO ontology + SkillGPT/Skill-LLM extraction | ESCO (EU), arXiv 2304.11060, arXiv 2410.12052 |
