# AU Marketing Compliance + LLM Testing Tool Landscape
*Research date: August 2026. Verified links and arXiv IDs.*

---

## Australian Legal Framework — Verified URLs

### Primary Legislation
- **ACL s18 (misleading or deceptive conduct):** https://www.australiancontractlaw.info/legislation/acl/s18
- **ASIC Act 2001 s12DA (financial services):** https://www.legislation.gov.au/Details/C2024C00296
- **Australian Consumer Law full text:** https://www.legislation.gov.au/Details/C2011A00103

### ASIC Guidance (verified URLs)
- **RG 234** (advertising financial products and services) — **Updated June 2026:**
  https://download.asic.gov.au/media/cvcjdpy5/rg234-published-09-june-2026.pdf
  - ASIC news release: https://asic.gov.au/about-asic/news-centre/news-items/asic-updates-guidance-on-advertising-financial-products-and-services/
- **INFO 271** (how to avoid greenwashing — nine-question framework):
  https://asic.gov.au/regulatory-resources/financial-services/how-to-avoid-greenwashing-when-offering-or-promoting-sustainability-related-products/
- **ASIC greenwashing speech (regulator perspective):**
  https://www.asic.gov.au/about-asic/news-centre/speeches/greenwashing-a-view-from-the-regulator/

### ACCC Enforcement (2024-25)
- **2024-25 Compliance and Enforcement Priorities (factsheet PDF):**
  https://www.accc.gov.au/system/files/compliance-enforcement-2024-factsheet_0.pdf
- **Priority announcement (media release):**
  https://www.accc.gov.au/media-release/cost-of-living-and-digital-economy-shape-2024-25-compliance-and-enforcement-priorities
- **Greenwashing internet sweep results:**
  https://www.accc.gov.au/media-release/accc-greenwashing-internet-sweep-unearths-widespread-concerning-claims
- **Influencer/online review scrutiny (ongoing):**
  https://www.accc.gov.au/media-release/scrutiny-of-influencers-and-businesses-for-misleading-advertising-and-online-reviews-continues
- **PhotobookShop infringement notice (first paid-influencer penalty):**
  https://www.accc.gov.au/media-release/photobookshop-pays-penalties-for-influencer-reviews
- **False or misleading claims (consumer guidance):**
  https://www.accc.gov.au/consumers/advertising-and-promotions/false-or-misleading-claims
- **Clifford Chance analysis of 2024-25 priorities:**
  https://www.cliffordchance.com/content/dam/cliffordchance/briefings/2024/04/accc-compliance-and-enforcement-priorities-2024-25.pdf

### Key Enforcement Precedents
- **Mercer greenwashing case** (record fine; admitted ASIC Act s12DF(1) breach, 2021-2023 claims):
  https://www.lexology.com/pro/content/australian-court-imposes-record-greenwashing-fine
- **AU greenwashing penalties post-mid-2024** (>$42M total):
  https://carbonly.ai/blog/accc-greenwashing-penalties-australia

### Commercial Compliance Tools
- **Compliance.ai** (now Archer Evolv Compliance): https://www.compliance.ai/
- **Compliance.ai Developer API:** https://developer.compliance.ai/home
- **Clausematch:** https://www.clausematch.com/
- **Clausematch knowledge graph (open source):**
  https://www.corporatecomplianceinsights.com/clausematch-knowledge-graph/
- **ASIC Innovation Hub (Enhanced Regulatory Sandbox):**
  https://www.asic.gov.au/for-business-and-companies/innovation-hub/
- **ASIC informal assistance for fintechs/regtechs:**
  https://www.asic.gov.au/for-business-and-companies/innovation-hub/informal-assistance-for-fintechs-and-regtechs/

---

## Verified arXiv Papers — AU Marketing Compliance & Claim Verification

All IDs verified by fetching arxiv.org/abs/<id> directly.

| Paper | Authors | Year | arXiv ID | Relevance |
|-------|---------|------|----------|-----------|
| FEVER: Fact Extraction and VERification | Thorne, Vlachos, Christodoulopoulos, Mittal | 2018 | [1803.05355](https://arxiv.org/abs/1803.05355) | Foundation benchmark for claim verification; adapt for AU marketing claims |
| "Liar, Liar Pants on Fire": LIAR Dataset | William Yang Wang | 2017 | [1705.00648](https://arxiv.org/abs/1705.00648) | 12,836 labelled veracity claims; annotation methodology directly adaptable |
| Detecting Greenwashing: NLP Literature Survey | Calamai, Balalau, Le Guenedal, Suchanek | 2025 (updated 2026) | [2502.07541](https://arxiv.org/abs/2502.07541) | Recommends regulatory records as ground truth; ASIC/ACCC enforcement aligns |
| ComplianceNLP: KG-Augmented RAG for Regulatory Gap Detection | Guo, Wu, Yiu | 2026 | [2604.23585](https://arxiv.org/abs/2604.23585) | 87.7 F1 gap detection; 3.1x analyst efficiency; ACL 2026 Industry |

---

## Verified arXiv Papers — LLM Testing & Legal AI

| Paper | Authors | Year | arXiv ID | Relevance |
|-------|---------|------|----------|-----------|
| Beyond Accuracy: Behavioral Testing of NLP Models with CheckList | Ribeiro, Wu, Guestrin, Singh | 2020 | [2005.04118](https://arxiv.org/abs/2005.04118) | ACL 2020 Best Paper; MFT/INV/DIR test types for compliance NLP |
| Large Legal Fictions: Profiling Legal Hallucinations in LLMs | Dahl, Magesh, Suzgun, Ho | 2024 | [2401.01301](https://arxiv.org/abs/2401.01301) | 58-88% hallucination rate; mandates citation gating for legal AI |
| A Survey on Hallucination in LLMs: Principles, Taxonomy, Challenges | Huang, Yu, Ma, et al. | 2023-2024 | [2311.05232](https://arxiv.org/abs/2311.05232) | ACM TOIS; hallucination taxonomy; detection methods |
| Measure and Improve Robustness in NLP Models: A Survey | X. Wang, H. Wang, Yang | 2022 | [2112.08313](https://arxiv.org/abs/2112.08313) | NAACL 2022; metamorphic testing grounding; robustness measurement framework |

---

## GitHub Repositories — LLM Evaluation Tools (Star Counts: August 2026)

| Repo | URL | Stars | Description |
|------|-----|-------|-------------|
| confident-ai/deepeval | https://github.com/confident-ai/deepeval | ⭐ 17.4k | LLM eval framework; pytest-native; hallucination, faithfulness, relevancy metrics |
| explodinggradients/ragas | https://github.com/explodinggradients/ragas | ⭐ 15.1k | RAG eval; Faithfulness, ContextRecall, AnswerRelevance; test set generation |
| truera/trulens | https://github.com/truera/trulens | ⭐ 3.5k | LLM eval and tracking; RAG triad; Snowflake Cortex integration |
| promptfoo/promptfoo | https://github.com/promptfoo/promptfoo | ⭐ 23.9k | Prompt/agent/RAG testing + red-teaming; YAML config; CI/CD; used by OpenAI/Anthropic |
| langfuse/langfuse | https://github.com/langfuse/langfuse | ⭐ 32.6k | Open-source LLM observability; self-hostable; full trace + eval + audit trail |
| EleutherAI/lm-evaluation-harness | https://github.com/EleutherAI/lm-evaluation-harness | ⭐ 13.5k | 60+ LLM benchmarks; pluggable custom tasks; foundation for AU compliance benchmarks |
| marcotcr/checklist | https://github.com/marcotcr/checklist | ⭐ 2.1k | Behavioral testing (MFT/INV/DIR) for NLP; CheckList paper implementation |
| boxed/mutmut | https://github.com/boxed/mutmut | ~800 | Python mutation testing; restartable; pytest integration |
| stryker-mutator/stryker-js | https://github.com/stryker-mutator/stryker-js | ~2.5k | JavaScript/TypeScript mutation testing; CI/CD integration |
| HypothesisWorks/hypothesis | https://github.com/HypothesisWorks/hypothesis | ~7.5k | Property-based testing for Python; edge case discovery, automatic shrinking |

### Fact Verification / FEVER Repos
- **awslabs/fever** (AWS Labs, FEVER baseline): https://github.com/awslabs/fever
- **fever/feverous** (HuggingFace dataset, 87k claims, structured+unstructured): https://huggingface.co/datasets/fever/feverous
- **liar dataset** (HuggingFace): https://huggingface.co/datasets/liar

---

## AU Marketing Compliance Test Set Construction — Workflow

```
1. Scrape ACCC media releases (accc.gov.au/media-release/*)
   → Extract: claim_text, date, product/service, outcome
   → Label: misleading=True, acl_section, penalty

2. Scrape ASIC enforcement decisions
   → Extract financial product marketing claims
   → Label: misleading=True, asic_act_section, severity

3. Manually sample compliant marketing (from ASIC-approved PDS documents)
   → Label: misleading=False (hard negatives)

4. Build test set with temporal cutoff (train: pre-2023, test: 2024+)

5. Evaluate precision/recall:
   - Tier 1 (requires review): target recall ≥ 0.90
   - Tier 2 (likely violation, mandatory sign-off): target precision ≥ 0.80
```

---

## Python+TypeScript Testing Stack Recommendation

```
Backend (Python):
  pytest + hypothesis          → property-based + unit tests
  deepeval                     → LLM eval metrics (hallucination, faithfulness)
  ragas                        → RAG pipeline evaluation
  trulens                      → continuous production monitoring
  mutmut                       → mutation testing of classifier logic

Frontend (TypeScript):
  promptfoo                    → prompt regression + red-team scans
  fast-check                   → property-based API contract tests
  stryker-js                   → mutation testing of frontend logic

Observability:
  langfuse (self-hosted)       → full trace + audit trail for every verdict
  lm-evaluation-harness        → custom AU compliance benchmark suite
```

## CI/CD Gates for Legal AI

1. **Pre-commit:** mutmut on changed Python; stryker on changed TypeScript
2. **PR gate:** pytest + deepeval hallucination/faithfulness metrics (no regression vs baseline)
3. **Pre-deploy:** promptfoo red-team (injection, jailbreak, confidentiality probes)
4. **Post-deploy:** langfuse continuous eval with human review queue for low-confidence verdicts
