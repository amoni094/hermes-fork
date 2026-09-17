# Legal-Tech Product Name Verification Reference

Compiled July 2026 from adversarial review of an AI legal knowledge management
system analysis document. Use this as a quick-check lookup when writing competitive
landscapes, build-or-buy analyses, or market surveys touching legal tech.

## Verified product names (as of July 2026)

### LexisNexis
- Correct: **Lexis+ AI** (AU: lexisnexis.com/en-au/products/lexis-plus-ai)
- Fabricated: "Lexis+ Protus" — does not exist
- Notes: Lexis+ AI is the primary AU enterprise product; includes conversational
  search, legal drafting assistance, AI-powered research. Enterprise data residency
  available for AU deployments.

### Thomson Reuters
- Correct: **Westlaw Edge** (legacy), **Westlaw Advantage** (current agentic AI research),
  **CoCounsel Legal** (rebuilt 2026, integrates Practical Law + org's own knowledge)
- Fabricated: "Westlaw Precision" — does not exist
- Notes: CoCounsel Legal is the closest to an internal KM layer; still primarily
  research-assistance rather than passive capture. Westlaw Advantage is the agentic
  multi-step research product (as of Jan 2026, available to law schools).

### iManage
- Correct: **iManage Knowledge Unlocked, powered by RAVN**
  (kmworld.com/Articles/ReadArticle.aspx?ArticleID=141504)
- Fabricated: "iManage RAVN/Insight", "iManage RAVN Knowledge" (missing "Unlocked")
- Notes: Used by Linklaters (from 2019, MatterExplorer), Walder Wyss (from 2020).
  Provides DMS-integrated AI extraction, automatic tagging, 7 search modes.
  Won LegalTech Breakthrough "Knowledge Management Platform of the Year".
  Does NOT provide three-tier personal/team/department architecture or
  conversational delivery layer out of the box.

### Harvey
- Correct: **Harvey** (harvey.ai) — generative AI legal assistant
- Notes: Matter-assistance focused, not a systematic KM system.

### EvenUp
- Correct: **EvenUp** — AI for plaintiff personal injury
- Notes: Highly specialised; NOT a general legal KM competitor.

### Luminance
- Correct: **Luminance** — legal AI for document analysis / due diligence
- Notes: Strong in due diligence; weaker in ongoing KM.

### Practical Law (Thomson Reuters)
- Correct: **Practical Law** — external curated legal guidance content
- Notes: External knowledge product, not an internal capture system.

---

## Verified academic datasets / papers for legal NLP

### CUAD (Contract Understanding Atticus Dataset)
- ArXiv: **2103.06268** — Hendrycks et al. 2021
- Title: "CUAD: An Expert-Annotated NLP Dataset for Legal Contract Review"
- Verified: Yes — real, widely cited. 510 commercial contracts, 41 clause types.
- Accuracy context: ~85–95% for well-defined standard clause types in standard
  commercial contracts; lower for non-standard drafting.

### ContractNLI
- ArXiv: **2110.01799** — Koreeda & Manning, EMNLP 2021
- Title: "ContractNLI: A Dataset for Document-level Natural Language Inference for Contracts"
- Verified: Yes — real (CC BY 4.0 license). 607 annotated contracts,
  document-level NLI with span-level evidence identification.

### NOT a legal NLP paper
- ArXiv: **2003.02609** — Theile et al. 2020
- Title: "UAV Coverage Path Planning under Varying Power Constraints using Deep
  Reinforcement Learning" — robotics paper, NOT legal NLP
- Fabrication risk: ID looks plausible; always fetch abstract page to confirm domain.

---

## Verification pattern

```python
# Always verify before citing any arXiv ID
from hermes_tools import web_extract
result = web_extract([f"https://arxiv.org/abs/{arxiv_id}"])
# Check: result[0]["title"] matches expected topic domain
# Check: result[0]["content"] contains expected author names and abstract keywords
```

For product names:
```
web_search(f'"{exact_product_name}" site:{vendor_domain}')
# If no results for exact name but results for a similar name -> fabrication signal
# Replace with the name the vendor's own site uses
```
