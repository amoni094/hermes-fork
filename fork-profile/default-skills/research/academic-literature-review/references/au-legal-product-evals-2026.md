# AU Legal AI Product Evals — Trust Deed Review & Marketing Compliance
## Session: August 2026 | Context: Product evals for AU trust deed validity + ACL s18/ASIC s12DA marketing review
## Scope: Building & testing evals for AU-specific legal document review tools

All arXiv IDs verified against live abstract pages. All AU legislation links verified against primary sources.
Fabricated citations explicitly excluded. This file covers: eval architecture for AU legal AI products,
trust deed validity criteria per state, ACL s18/ASIC s12DA eval design, code patterns, and practitioner guidance.

---

## 1. Quick Reference — Verified Papers

| ID | arXiv/URL | Title | Year | Relevance |
|----|-----------|-------|------|-----------|
| L1 | 2306.05685 | Judging LLM-as-a-Judge with MT-Bench | 2023 | LLM-as-judge biases — position, verbosity, self-enhancement |
| L2 | 2406.07791 | Judging the Judges: Position Bias Study | 2024 | Three bias metrics: repetition stability, position consistency, preference fairness |
| L3 | 2604.23178 | Judging the Judges: Bias Mitigation | 2026 | 9 debiasing strategies; biases evolve as models update |
| L4 | 2103.06268 | CUAD: Expert-Annotated Contract Review | 2021 | 510 contracts, 41 clause categories — clause extraction foundation |
| L5 | 2110.01799 | ContractNLI: Document-level NLI | 2021 | NDA entailment/contradiction — maps to ACL s18 contradiction detection |
| L6 | 2308.11462 | LegalBench: 162 Legal Reasoning Tasks | 2023 | 6 reasoning categories; methodology template for AU tasks |
| L7 | 2606.13184 | LAUKIN: AU/UK/IN Contract Dataset | 2026 | ONLY verified AU contract dataset; 65.11% best F1 — challenging |
| L8 | 2504.01840 | LRAGE: Legal RAG Evaluation Tool | 2025 | Purpose-built legal RAG eval; 5-component ablation; pip install lrage |
| L9 | JELS 2025 | Hallucination-Free? Stanford Legal RAG | 2025 | LexisNexis hallucinates 17-33% despite RAG; defines grounded/fabricated typology |
| L10 | 2606.21155 | Who Checks the Citations? Legal Hallucination | 2026 | Benchmarks methods for detecting fabricated legal citations |

---

## 2. LAUKIN — The Only Verified AU Contract Dataset ⭐

- **Full title:** "LAUKIN: A Multi-jurisdictional Common Law Contract Dataset"
- **Authors:** Amrita Singh, Aditya Joshi, Jiaojiao Jiang, Hye-young Paik, May Fong Cheong
- **Year:** June 2026 | **arXiv:** https://arxiv.org/abs/2606.13184 ✅ VERIFIED
- **License:** CC BY-NC-ND 4.0
- **Size:** 14,727 clause pairs from 204 contracts, 8 agreement types (AU-UK, UK-IN, IN-AU)
- **Labels:** Boolean legal equivalence (Equivalent / Not Equivalent)
- **Split:** 900 train / 600 dev / 1,500 test manually labelled; 11,727 unlabelled
- **Best result:** macro-F1 65.11% across 12 models and 4 techniques
- **Key finding:** Despite shared common law heritage, drafting conventions diverge significantly across AU/UK/IN
- **Gap:** No trust deed–specific AU dataset exists as of August 2026 — LAUKIN is the closest proxy

**How to use for trust deed product:**
- The boolean equivalence task is directly reusable: "Does this trust deed clause achieve the same legal effect as a standard template clause?"
- The 65.11% ceiling tells you current LLMs struggle with AU-specific legal semantics
- Use the AU-UK pairs for cross-jurisdictional clause understanding evals

---

## 3. LLM-as-Judge — Calibration Requirements for Legal Evals

**Foundational paper:** arXiv:2306.05685 (Zheng et al., NeurIPS 2023)
- Position bias: judge systematically prefers first/last response regardless of legal correctness
- Verbosity bias: longer legal opinions rated higher even when incorrect
- Self-enhancement: GPT-4 judge rates GPT-4 outputs higher — use a different model family for judging
- Sycophancy: judge agrees with stated human opinion — use blind evaluation

**2024–2026 updates:**
- arXiv:2406.07791 — Three bias metrics: repetition stability, position consistency, preference fairness
- arXiv:2604.23178 — Biases EVOLVE as model training changes; a mitigation calibrated to 2023 behaviour may be counterproductive in 2026

**Legal-specific calibration rules:**
- Target κ ≥ 0.80 between LLM judge and human lawyer on golden set before production
- κ < 0.60 should block release
- For trust deed evals: judge must receive exact statutory text as context (Trustee Act, Property Law Act)
- For marketing review evals: judge must receive ACL s18 / ASIC Act s12DA statutory text + test cases

---

## 4. Stanford Hallucination Study — Benchmark for Legal RAG Claims

**Paper:** "Hallucination-Free? Assessing the Reliability of Leading AI Legal Research Tools"
- Authors: Varun Magesh, Faiz Surani, Matthew Dahl, Mirac Suzgun, Christopher Manning, Daniel Ho
- Published: Journal of Empirical Legal Studies, 2025
- URL: https://dho.stanford.edu/wp-content/uploads/Legal_RAG_Hallucinations.pdf
- First preregistered empirical evaluation of proprietary legal RAG tools

**Key findings:**
- LexisNexis Lexis+ AI: hallucinates 17-33% of the time despite RAG
- Westlaw AI-Assisted Research: hallucinates nearly twice as often as LexisNexis
- "Hallucination-free" claims are overstated — RAG reduces but does not eliminate hallucinations
- RAG-based legal AI at 65% (best) vs GPT-4 baseline — meaningful but partial improvement

**Hallucination typology (reusable for AU product):**
- **Grounded:** every material proposition supported by an applicable legal source
- **Ungrounded:** material proposition present but no citation
- **Misgrounded:** source cited does not support the proposition
- **Fabricated:** source cited does not exist

**Product design implication:** Your AU trust deed tool must never claim to be "hallucination-free." VLSB+C statement (December 2024) explicitly confirms this is impossible. Build the typology into your eval rubric.

---

## 5. Australian Trust Deed Validity — Eval Criteria

### 5.1 Three Certainties (all AU jurisdictions — common law)

Every valid trust deed must satisfy all three. Failure on any one = trust fails.

| Certainty | What AI must check | Failure examples |
|-----------|-------------------|------------------|
| **Intention** | Clear intent to create binding trust (not gift/loan/moral) | Precatory words: "I wish", "I hope" |
| **Subject matter** | Trust property specifically identified | "some of my assets", undefined property |
| **Objects** | Beneficiaries or class sufficiently certain | "worthy causes", "persons I like", empty class |

**Sources:**
- https://en.wikipedia.org/wiki/Australian_trust_law — overview of three certainties in AU context
- https://everglow.au/trust-deed-requirements/ — practitioner guide (2026)

### 5.2 Execution Requirements Per State (CRITICAL for state-specific evals)

Sourced from DBA Lawyers (29 July 2024): https://www.dbalawyers.com.au/smsf-compliance/executing-deeds-ensuring-validity-across-all-australian-jurisdictions/

| State | Legislation | Witness Required | Sealing | E-Execution |
|-------|------------|-----------------|---------|-------------|
| VIC | Instruments Act 1958 | **NO** | Yes (if expressed) | Uncertain — use wet ink |
| NSW | Conveyancing Act 1919 s 38 | **YES** | Yes (if expressed) | YES (s 38A) |
| QLD | Property Law Act 1974 s 46C-E | **NO** | NO | YES (s 46D) |
| WA | Property Law Act 1969 s 9 | YES | NO | NO |
| SA | Law of Property Act 1936 s 41 | YES | Yes (if expressed) | NO |
| TAS | Conveyancing and Law of Property Act 1884 s 63 | YES | Yes (if expressed) | NO |
| ACT | Civil Law (Property) Act 2006 s 219 | YES | Yes (if expressed) | NO |

**State-specific test cases required:**
```python
# These must each exist in your golden dataset
test_vic_witness_not_required()   # VIC deed without witness: VALID
test_nsw_witness_required()       # NSW deed without witness: INVALID
test_qld_no_sealing_needed()      # QLD deed without sealing: VALID
test_signed_sealed_delivered()    # VIC/NSW without "signed, sealed and delivered": INVALID
test_electronic_sa_invalid()      # SA electronic exec by individual: INVALID
```

### 5.3 Legislation URLs (Primary Sources)

- VIC Trustee Act 1958: https://www.legislation.vic.gov.au/in-force/acts/trustee-act-1958
- NSW Trustee Act 1925: https://legislation.nsw.gov.au/view/html/inforce/current/act-1925-014
- QLD Property Law Act 1974: https://www.legislation.qld.gov.au/view/html/inforce/current/act-1974-076
- VIC SRO trust deed duty: https://www.sro.vic.gov.au/buying-property/land-transfer-stamp-duty/companies-and-trusts/trust-deeds
- DBA Lawyers "six simple rules": https://www.dbalawyers.com.au/audit/six-simple-rules-to-execute-a-deed-that-satisfies-all-australian-jurisdictions/

---

## 6. ACL s18 / ASIC Act s12DA — Eval Criteria for Marketing Review

### 6.1 Statutory Text

**ACL s18 (Competition and Consumer Act 2010 Schedule 2):**
> "A person must not, in trade or commerce, engage in conduct that is misleading or deceptive or is likely to mislead or deceive."
- Applies to all goods and services
- No intent required — objective test
- Test: would a reasonable person in the target audience be misled?

**ASIC Act s12DA:**
> "A person must not, in trade or commerce, engage in conduct in relation to financial services that is misleading or deceptive or is likely to mislead or deceive."
- Applies specifically to financial services (investments, insurance, super, credit)
- Enforced by ASIC (not ACCC)
- Text: https://www5.austlii.edu.au/au/legis/cth/consol_act/asaica2001529/s12da.html

### 6.2 High-Risk Phrases (Eval Seed Set)

```python
# Regex patterns — any match triggers CRITICAL flag
AU_HIGH_RISK_MARKETING_PHRASES = [
    r"guaranteed\s+(return|income|profit|growth)",
    r"risk.free",
    r"100%\s+(safe|secure|protected|capital\s+protection)",
    r"ASIC.approved",       # ASIC doesn't "approve" products
    r"government.backed",
    r"no\s+(ongoing\s+)?(fees|charges|costs)",
    r"beat\s+inflation\s+guaranteed",
]
```

### 6.3 What Makes AI Marketing Review Legally Defensible

1. **Audit trail:** every flag must cite ACL s18 or ASIC Act s12DA + the exact text passage
2. **Human review gate:** AI output must be reviewed by a qualified legal practitioner before sign-off
3. **Explainability:** must explain WHY a claim is potentially misleading, not just flag it
4. **Calibrated FN rate:** document target false negative rate; FN (missed misleading claim) = legal liability
5. **Version locking:** log model version + prompt version + timestamp for every review
6. **Disclosure:** product cannot replace qualified legal advice; must be disclosed

**Source:** https://airiskaware.com/insights/asic-ai-obligations-australian-financial-services — ASIC AI obligations

---

## 7. VLSB+C / LSNSW Joint AI Statement (December 2024)

**URL:** https://lsbc.vic.gov.au/news-updates/news/statement-use-artificial-intelligence-australian-legal-practice
**PDF:** https://lsbc.vic.gov.au/sites/default/files/2024-12/Statement%20on%20the%20use%20of%20AI%20in%20Australian%20legal%20practice_2.pdf
**Issued by:** VLSB+C + LSNSW + LPBWA (Dec 6, 2024)

**Key product constraints — quote directly in product design:**

> "No tool based on current LLMs can be free of 'hallucinations', and lawyers using AI to prepare documents must be able and qualified to personally verify the information they contain."

| Obligation | Rule | Product Implication |
|-----------|------|---------------------|
| Competence & diligence | ASCR r 4.1.3 | Human review gate is mandatory; cannot be optional |
| No hallucinations relied upon | VLSB+C statement | Must flag uncertainty; cannot claim hallucination-free |
| Confidentiality | ASCR r 9.1 | Deed text is confidential — data processing agreement required before cloud API use |
| Honest costs | Uniform Law ss 172-173 | Document if AI reduces time vs traditional methods |
| Risk-based policy | VLSB+C guidance | AI-assisted review ≠ AI-only sign-off; distinguish these in product |

**Practical eval implication:** Your INVALID recall metric (≥ 0.95) and your hallucination rate metric (RAGAS Faithfulness ≥ 0.95) are not just product quality metrics — they are the means by which lawyers can "personally verify" outputs. Document these metrics in your product documentation so lawyers can make an informed judgment about verification burden.

---

## 8. AustLII — Case Law Access for Eval Dataset Building

**URL:** https://www.austlii.edu.au/
**Classic interface:** https://classic.austlii.edu.au/

Use AustLII to source adversarial/edge-case test deeds:
- Search: `"certainty of objects" "trust deed"` — find cases where courts found trust deeds invalid
- Trust deed invalidity cases → real-world adversarial test cases for the model
- ASIC enforcement actions: `site:austlii.edu.au ASIC misleading` → real examples of ACL s18 violations
- LawCite (within AustLII) — checks whether a case your AI cited is still good law

**Key databases:**
- https://www.austlii.edu.au/au/cases/vic/ — Victorian case law
- https://www.austlii.edu.au/au/cases/nsw/ — NSW case law
- https://www.austlii.edu.au/au/cases/qld/ — Queensland case law
- https://www.austlii.edu.au/au/legis/cth/consol_act/asaica2001529/ — ASIC Act 2001

---

## 9. Eval Frameworks — Verified GitHub Repos

| Repo | Stars | Use |
|------|-------|-----|
| https://github.com/confident-ai/deepeval | ~15,000 (May 2026) | pytest-native; G-Eval + hallucination; CI/CD; Python + TypeScript |
| https://github.com/explodinggradients/ragas | ~10,000+ | RAG eval; Faithfulness = hallucination proxy for legal RAG |
| https://github.com/EleutherAI/lm-evaluation-harness | ~13,000 | Broad LLM benchmarking; YAML task config |
| https://github.com/openai/evals | ~14,000+ | OpenAI's eval framework; YAML + JSON config |
| https://github.com/promptfoo/promptfoo | ~23,700 | Prompt regression testing; YAML; CI GitHub Action |
| https://github.com/truera/trulens | ~3,000+ | RAG triad + production monitoring |
| https://github.com/The-Atticus-Project/cuad | ~800 | CUAD dataset + baseline models |
| https://github.com/stanfordnlp/contract-nli | ~300 | ContractNLI: document-level NLI for contracts |
| https://github.com/harveyai/biglaw-bench | small | BigLaw Bench rubric examples |
| https://github.com/harveyai/harvey-labs | small | Harvey LAB: agentic legal task eval |
| https://github.com/hoorangyee/LRAGE | small | LRAGE: Legal RAG eval; 5-component ablation |
| https://github.com/maastrichtlawtech/awesome-legal-nlp | ~334 | Curated legal NLP papers/datasets/models |
| https://github.com/HypothesisWorks/hypothesis | ~7,000+ | Property-based testing for legal edge cases |

---

## 10. Eval Code Patterns — Key Decisions

### Critical Metric Thresholds (AU Trust Deed Product)

```python
QUALITY_GATES = {
    # Safety-critical — must pass before release
    "invalid_deed_recall": 0.95,        # Must catch 95%+ of invalid deeds
    "hallucination_rate_max": 0.05,     # RAGAS Faithfulness >= 0.95
    "llm_judge_kappa_min": 0.80,        # LLM judge vs human lawyer agreement
    "overall_accuracy_min": 0.90,       # Blended accuracy on golden set
    
    # Per-jurisdiction — must pass per state, not just overall
    "jurisdiction_breakdown_required": True,  # Don't hide per-state failures in averages
    
    # Confusion matrix — asymmetric risk
    "false_negative_weight": 5,         # Missing an INVALID deed is 5x worse than false positive
}
```

### INVALID Recall Priority

Missing an invalid trust deed (FN) is more dangerous than flagging a valid deed (FP):
- FN risk: client relies on invalid trust; ATO issues; assets not protected
- FP risk: client re-engages solicitor for second opinion (inconvenient but not catastrophic)

Always track INVALID recall separately — do not let it be diluted in overall accuracy.

### Hypothesis PBT for Legal Invariants

```python
from hypothesis import given, settings
from hypothesis import strategies as st

@given(beneficiary_class=st.just(""))
def test_empty_beneficiary_always_invalid(beneficiary_class):
    """PROPERTY: Empty beneficiary class → always INVALID (certainty of objects fails)."""
    deed = make_deed(beneficiary_class=beneficiary_class)
    result = reviewer.classify(deed)
    assert result["valid"] is False
```

**Use Hypothesis for:** empty/null fields, jurisdiction boundary cases, execution variant combinations across all 7 states, string injection attacks on deed text parser.

### Golden Dataset Schema (per case)

```json
{
  "id": "td-vic-0042",
  "version": "3",
  "deed_text": "...",
  "valid": false,
  "jurisdiction": "VIC",
  "failure_reasons": ["Missing certainty of objects: 'persons the trustee likes' too vague"],
  "expected": {
    "certainty_of_intention": true,
    "certainty_of_subject_matter": true,
    "certainty_of_objects": false,
    "execution_valid": true
  },
  "annotator": "lawyer_a",
  "adjudicator": null,
  "annotation_date": "2026-06-15",
  "annotation_guide_version": "2.1",
  "notes": "Borderline — 'persons the trustee likes' per Re Denley [1969] is insufficient"
}
```

---

## 11. Inter-Rater Reliability Protocol

Target Cohen's κ ≥ 0.80 before treating any label as ground truth.

```python
from sklearn.metrics import cohen_kappa_score

kappa = cohen_kappa_score(lawyer_1_labels, lawyer_2_labels)
# < 0.60 → redesign annotation guide
# 0.60–0.80 → acceptable but improve
# > 0.80 → release quality
```

**Adjudication protocol:** When two annotators disagree → third senior lawyer adjudicates (blind, reads both prior labels) → adjudicator decision is final → document reasoning for institutional knowledge.

---

## 12. BigLaw Bench — Scoring Design to Copy

**URL:** https://www.harvey.ai/blog/introducing-biglaw-bench
**GitHub rubric examples:** https://github.com/harveyai/biglaw-bench

**Key design principle:** Rubrics use SIGNED scoring — positive points for affirmative requirements AND negative points for hallucinations. Net score = (positive points earned − negative penalties) / total positive points = "% of lawyer-quality work product completed."

This is better than accuracy alone because it penalises confident-but-wrong outputs more than uncertain ones. Adopt for trust deed evals: define positive rubric items (identifies three certainties, identifies correct jurisdiction, identifies execution method) and negative items (hallucinated statutory reference, asserted non-existent witness requirement).

---

## 13. LRAGE — Install & Use

**arXiv:** https://arxiv.org/abs/2504.01840 (April 2025) ✅ VERIFIED
**GitHub:** https://github.com/hoorangyee/LRAGE

```bash
pip install lrage  # includes pre-compiled Pile-of-law BM25 indices
```

**Five components LRAGE ablates independently:**
1. Retrieval corpus (what law is in the index)
2. Retrieval algorithm (BM25, dense, hybrid)
3. Reranker (cross-encoder, none)
4. LLM backbone (GPT-4o, Claude, Llama)
5. Evaluation metrics (task accuracy, faithfulness, etc.)

**Key finding from LRAGE authors:** Retrieval corpus quality matters MORE than LLM backbone quality. A better model with poor document retrieval underperforms a weaker model with good retrieval. For AU trust deed RAG: invest in the corpus (correct, current AU legislation and case law) before tuning the LLM.

---

## 14. Confirmed Gaps (August 2026)

1. **No AU trust deed–specific benchmark dataset exists.** LAUKIN is the only AU contract dataset but covers general commercial contracts, not trust deeds.
2. **No AU-specific accuracy threshold has been published** for trust deed review AI. ASCR Rule 4 (competence) is the operative test.
3. **No published benchmark for ACL s18 / ASIC s12DA marketing review detection.** ContractNLI (contradiction detection on NDAs) is the closest methodology to adapt.
4. **LAUKIN best F1 of 65.11%** establishes that AU legal NLP is genuinely hard — do not set user-facing accuracy expectations based on US-law benchmark numbers.
5. **Electronic execution is ambiguous in VIC** (Electronic Transactions (Victoria) Act 2000 s 9 — "as reliable as appropriate" test has no published safe harbour). Conservative approach (wet ink) is the defensible recommendation; AI review tools should flag e-signed VIC deeds as REQUIRES_LEGAL_REVIEW, not VALID.
