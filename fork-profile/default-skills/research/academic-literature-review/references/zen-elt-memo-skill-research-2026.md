# zen / elt-memo AI Writing Skill — Research Supplement
Date: 2026-07-28
Context: Jesse Gleeson commissioned testing of two Hermes skills — zen (sentence-level
legal prose rewriting based on Weinzweig mantras + ASD-STE100) and elt-memo (messy legal
advice → two-page NAB-branded executive memo). This file records verified supplementary
sources NOT already in Jesse's research.odt baseline, plus key factual corrections found.

## FACTUAL CORRECTIONS (high priority — affects test scoring)

### CPS 230 Notification Window
CORRECT: 72 hours for a material operational risk incident under CPS 230 para 36.
WRONG: "24 hours" cited in a LinkedIn commentary post. CPS 230 itself has no 24-hour
window. CPS 234 (information security incidents) has its own separate notification clock.
Primary source: https://www.apra.gov.au/standards/cps-230
PDF: https://www.apra.gov.au/system/files/2023-07/Prudential+Standard+CPS+230+...

If a generated memo states "24 hours" for a CPS 230 notification, that is an extrinsic
fabrication. Score it accordingly.

### NAB Brand Red
CORRECT: #ed0000 (RGB 237,0,0)
WRONG: #ff0000 (RGB 255,0,0) — what the skill hardcodes
Source: pickcoloronline.com/brands/national-australia-bank/ citing nab.com.au
Also: brandfetch.com/nab.com.au for ongoing brand asset updates.
Fix the skill before any demo to ELT / Group Executive.

---

## SKILL & PROMPT OPTIMIZATION

### SkillOpt — Self-Evolving Agent Skills
Citation: Yang, Gong, Huang et al. (Microsoft/SJTU/Fudan/Tongji). arXiv:2605.23904. May 2026.
URL: https://arxiv.org/abs/2605.23904 | GitHub: https://github.com/microsoft/SkillOpt
Key finding: +23.5pp average gain over no-skill baseline across 6 benchmarks.
Mechanism: rollout → reflect → aggregate → select → update → evaluate loop with
validation-gated edit acceptance (an edit is only kept if it clears a held-out set).
Relevance: direct methodology for measuring whether a SKILL.md edit improved output
rather than just changed it. pip install skillopt.

### GEPA — Reflective Prompt Evolution
Citation: Agrawal et al. arXiv:2507.19457. Jul 2025 / Feb 2026.
URL: https://arxiv.org/abs/2507.19457
Key finding: reflective mutation step diagnoses WHY a prompt variant failed before
generating the next candidate. Outperforms RL-based methods on instruction-following.

### TextGrad — Automatic "Differentiation" via Text
Citation: Yuksekgonul et al. (Stanford). arXiv:2406.07496. Jun 2024.
URL: https://arxiv.org/abs/2406.07496 | GitHub: https://github.com/zou-group/textgrad
Key finding: backpropagates LLM textual feedback to improve prompt components.
+20% relative gain on LeetCode-Hard; +4pp on factual QA.
Warning: see TextReg below for overfitting failure mode.

### TextReg — Mitigating Prompt Distributional Overfitting
Citation: arXiv:2605.21318. May 2026.
URL: https://arxiv.org/abs/2605.21318
Key finding: +11.8% OOD accuracy vs TextGrad. TextGrad prompts optimized on one fixture
(e.g. CodeForge only) overfit and regress on held-out inputs. Run optimization against
multiple real advices, not just the CodeForge example.

### OPRO — Large Language Models as Optimizers
Citation: Yang, Wang et al. (Google DeepMind). arXiv:2309.03409. ICLR 2024.
URL: https://arxiv.org/abs/2309.03409
Foundational paper: LLM iteratively rewrites a prompt toward a higher score on a labeled
dataset. Theoretical foundation for any automated skill-editing loop.

### DSPy — "Is It Time To Treat Prompts As Code?"
Citation (applied): Lemos, Alves, Ferraz (U Minho). arXiv:2507.03620. Jul 2025.
URL: https://arxiv.org/abs/2507.03620 | Framework: https://github.com/stanfordnlp/dspy
Key finding: DSPy optimization raised prompt evaluation accuracy from 46.2% to 64.0%.
Applied to 5 use cases incl. hallucination detection and prompt quality evaluation.

### MIPRO — Multi-Stage Instruction and Demonstration Optimization (DSPy)
Citation: Opsahl-Ong et al. arXiv:2406.11695. Jun 2024.
URL: https://arxiv.org/abs/2406.11695
Extends DSPy to multi-stage pipelines (zen step → elt-memo step → format check step).
Outperformed baseline on 5 of 7 multi-stage programs with Llama-3-8B.

### RSEA — Recursive Self-Evolving Agents via Held-Out Selection
Citation: arXiv:2606.28374. Jun 2026.
URL: https://arxiv.org/abs/2606.28374
Key finding: held-out selection prevents recursive auto-improvement from overfitting
its own evaluation criteria. Safety mechanism for any automated elt-memo improvement loop.

---

## FAITHFULNESS EVALUATION

### InFusE / DiverSumm — NLI Faithfulness for Diverse Summarisation
Citation: Zhang, Xu, Perez-Beltrachini (U Edinburgh). arXiv:2402.17630. EACL 2024.
URL: https://arxiv.org/abs/2402.17630 | GitHub: https://github.com/HJZnlp/infuse
Key finding: variable-size premise + simplified hypotheses outperforms FactCC/SummaC
on long-form and multi-document tasks. DiverSumm benchmark covers meeting + multi-doc.
Use for claim-level scoring of elt-memo output vs source advice.

### LLM-as-Judge for Long-Form Output Evaluation
Citation: arXiv:2606.01629. Jun 2026.
URL: https://arxiv.org/abs/2606.01629
Key finding: long-form evaluation failure modes differ from short factual QA. Studies
document-level assessment of organization, coverage, depth. Read before designing any
evaluation protocol that uses Claude to grade its own memos.

### Multi-Dimensional Evaluation of LLM Summarization
Citation: arXiv:2506.00549. Jun 2026.
URL: https://arxiv.org/html/2506.00549
Key finding: proposes per-axis scoring — faithfulness / detail level / coherence /
completeness — rather than a single quality score. Use to disaggregate failure modes
(e.g. "4/5 faithfulness, 2/5 appropriate detail") matching Jesse's three failure categories.

### Faithfulness vs Abstractiveness Tradeoff
Citation: Yuan et al. arXiv:2512.03503. Dec 2025.
URL: https://arxiv.org/pdf/2512.03503
Key finding: summary abstractiveness negatively correlates with faithfulness. GPT-5
scores much higher on faithfulness (4.42 vs 3.98). Empirical anchor for recommending
calibrated paraphrase over creative restatement in elt-memo.

### Domain-Conditional MI: Mitigating Hallucination in Abstractive Summarization
Citation: arXiv:2404.09480. Apr 2024.
URL: https://arxiv.org/abs/2404.09480
Key finding: models "fill gaps" from domain priors rather than input document.
Directly relevant when source advice is ambiguous (e.g. "arguably CPS 230" becomes
confident claim in the memo).

---

## SKILL AUTHORING & FORMAT

### Anthropic Claude Skill Authoring Docs
URL: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices
URL: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview
Guidance: ~500 lines max for SKILL.md body; details go in references/. elt-memo is
22KB — some content should be moved to references/ subdirectory.

### anthropics/skills — Upstream docx skill
URL: https://github.com/anthropics/skills/blob/main/skills/docx/SKILL.md
Active note: "Tables need dual widths: set columnWidths on the table AND width on every
cell, both in WidthType.DXA (PERCENTAGE breaks in Google Docs)." elt-memo must account
for this quirk in any table generation.

### Progressive Disclosure Architecture
URL: https://deepwiki.com/spences10/claude-skills-cli/2.1-progressive-disclosure-architecture
Three tiers: metadata (always in context), SKILL.md body (loads on trigger), references/
(loads on explicit request). Token cost increases at each tier.

### theosib/skill-writer
URL: https://github.com/theosib/skill-writer
Meta-skill for writing SKILL.md files across Claude/GPT/Gemini — applies instruction
clarity, token efficiency, positive framing. Could be used to refactor zen/elt-memo.

---

## DOCUMENT GENERATION & RENDERING

### OOXML Validator CLI
URL: https://github.com/mikeebowen/OOXML-Validator
Use: validate elt-memo .docx output against ECMA-376 schema before rendering. Catches
malformed XML that LibreOffice tolerates but Word rejects.

### pdf-visual-diff (moshensky)
URL: https://github.com/moshensky/pdf-visual-diff
Use: automate the mandatory visual check — pixel-diff rendered PDF against CodeForge
baseline. Integrates with Jest for CI. The missing automation link in elt-memo's pipeline.

### docx-templates (guigrpa)
URL: https://github.com/guigrpa/docx-templates
Use: design template in Word, mark fill-points with {tags}, inject data. Better branding
fidelity than generating from scratch in JS (real font embed, real border styles).

### Carbone.io
URL: https://carbone.io/ | https://github.com/carboneio/carbone
Use: {d.fieldName} markers in real Word/LibreOffice template + JSON data = generated
document. Manages LibreOffice workers for PDF conversion with auto-restart and retry.
Strongest production path to "start from real NAB .dotx and inject JSON".

### LibreOffice Dev Blog — Validating ODF and OOXML (Jan 2026)
URL: https://dev.blog.documentfoundation.org/2026/01/22/validating-odf-and-ooxml-files/
OOXML validation toolchain LibreOffice uses internally.

---

## AUSTRALIAN REGULATORY CONTEXT

### APRA AI Governance Letter — April 2026
URL: https://www.apra.gov.au/news-and-publications/apra-letter-industry-artificial-intelligence-ai
Issued 30 April 2026. Requires: AI inventory with named owners, human sign-off for
high-risk AI decisions, governance framework across lifecycle. Supervisory guidance,
not a new prudential standard. An elt-memo/zen deployment at NAB is plausibly an AI
use case that belongs on this inventory.

### FAR / ASIC RG 279 (Jul 2024)
URL: https://www.apra.gov.au/financial-accountability-regime-information-for-accountable-entities
URL: https://download.asic.gov.au/media/prbd2fyg/rg279-published-11-july-2024.pdf
FAR replaced BEAR for ADIs from 15 March 2024. Accountability statements, maps, and
enhanced notification obligations. Reference for what a real FAR analysis looks like.

### LPP Waiver via AI Models — Stirling & Rose (Mar 2024)
URL: https://stirlingandrose.com/2024/03/21/client-privilege-at-risk-sharing-legal-advice-with-ai-models/
Directly applies Mann v Carnell to feeding privileged advice to an AI model in Australia.
Confirmed: sharing with external AI risks LPP waiver under the "inconsistency" test even
without subjective intent. Mitigation: confidentiality agreement with provider, or
internal model. Covers AU, SG, UK, US.

### NSW SC GEN 23 — Generative AI Practice Note (eff. 3 Feb 2025)
Source: confirmed via lawsociety.com.au AI hub and multiple confirmed sources.
Prohibits AI-generated content for affidavits, witness statements, expert reports without
court approval. Carve-out for grammar/formatting tools may cover zen; does not cover
elt-memo. Check for revised version (review submissions closed 18 Dec 2025).

### NDB Scheme (OAIC)
URL: https://www.oaic.gov.au/privacy/notifiable-data-breaches
30 days to assess a suspected eligible data breach; notify OAIC + individuals ASAP once
confirmed. Separate clock from APRA CPS 230/234. Both may run simultaneously in
CodeForge scenario if customer personal information fragments were involved.

---

## MULTILINGUAL FINDINGS

### French (CONFIRMED HIT)
Roy et al. HAL-04678366. EvalLLM workshop (TALN 2024 satellite). Aug 2024.
URL: https://hal.science/hal-04678366
Full-paper research on automatic LLM summarization of judicial investigation texts.
Exact task match: legal document → structured summary. French judicial corpus.

### French (CONFIRMED HIT)
HAL-05441298. 2025. URL: https://hal.science/hal-05441298
Low-supervision terminology extraction from legal documents — prerequisite for
faithful legal summarization (preserving domain-specific terms vs paraphrasing).

### German (CONFIRMED HIT)
Rios, Stodden, Fan. DEplain. arXiv:2305.18939. KONVENS 2023 / ACL 2023.
URL: https://arxiv.org/abs/2305.18939
German parallel plain-language corpus. Document-level simplification harder than
sentence-level — maps to elt-memo's challenge.

### German (CONFIRMED HIT)
CourtPressGER. Nagl et al. arXiv:2512.09434. Dec 2025.
URL: https://arxiv.org/abs/2512.09434
German court decision → press release dataset. Exact structural analog to elt-memo.

### German (CONFIRMED HIT)
Decher, Dembach (Fraunhofer FKIE). KONVENS 2025.
URL: https://aclanthology.org/2025.konvens-2.16
Domain-specific terminology is the primary driver of summary degradation. Models
over-simplify (losing precision) or under-simplify (losing comprehension).

### Korean (CONFIRMED HIT — dataset)
AI-Hub Korean Legislative Bill Review Report Dataset.
URL: https://aihub.or.kr/aihubdata/data/view.do?aihubDataSe=realm&dataSetSn=71794
Public dataset of structured bill review summaries — usable as neutral test set.

### Japanese — CONFIRMED GAP
No peer-reviewed Japanese-language work on legal document summarization or executive
memo generation. Japanese legal NLP focuses on case law retrieval and statute
interpretation. Topic-maturity gap, not an access barrier.

### Chinese — CONFIRMED GAP
Chinese legal NLP covers case retrieval, statutory QA, and judgment prediction (CAIL
benchmark). No equivalent of the common-law "legal advice → executive memo" task.
Structural gap: the corporate advisory memo format is specific to common-law jurisdictions.
