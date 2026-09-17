---
name: law-firm-briefing-memo
version: 1.0.0
license: MIT
platforms: [linux, macos, windows]
triggers:
  - User needs to write a briefing memo to an external law firm
  - User needs to instruct external legal counsel on a matter
  - User needs to draft a matter brief, engagement scope, or instructions letter for a law firm
  - User needs to prepare for a regulatory or litigation matter briefing to external lawyers
  - Australian bank GC, deputy GC, or senior legal counsel needs to engage a law firm
description: >
  Use when an Australian bank (ADI) needs to write a briefing memo to an
  external law firm. Covers instructions letters, matter briefs, engagement
  scopes, regulatory matter briefings, and litigation instructions. Calibrated
  for APRA-regulated institutions with Australian common law conventions.
metadata:
  tags:
    - legal
    - memo
    - law-firm
    - external-counsel
    - briefing
    - australian-bank
    - regulatory
    - APRA
    - litigation
related_skills:
  - exec-memo-writing
  - legal-regulatory-research-writing
  - grounded-citations
  - docx
  - pdf
---

# Law Firm Briefing Memo

For Australian banks (ADIs) briefing external law firms. Covers the full range:
initial engagement / instructions letter, ongoing matter briefs, regulatory
matter handoffs, litigation scope letters, and standalone regulatory briefings.

Research basis: practitioner conventions from NSW Bar Association (verified templates), r/auslaw
community (verified threads), CLOC Core 12 framework, ALPMA, AU regulatory framework (APRA CPS 230
April 2026 update, FAR Act 2023, AML/CTF Act 2006 July 2026 reforms, Privacy Act 1988, ASCR 2026);
legal project management standards (CLOC, ACLA/ACLEA); academic literature (ComplianceNLP
arXiv:2604.23585; LegalGraphRAG arXiv:2605.28120); GitHub: anthropics/claude-for-legal design
patterns; multilingual research (French lettre de mission, German Mandatsbriefing, Japanese ringi
dual-purpose structure, Korean 법률자문계약서 conventions).

---

## When to use this skill

Use when:
- A bank in-house lawyer needs to instruct an external law firm on a new or ongoing matter
- GC or legal function needs to issue a matter brief covering scope, budget, and regulatory context
- A regulatory inquiry (APRA, ASIC, AUSTRAC, ACCC, OAIC) needs to be handed to external counsel
- Litigation is threatened or commenced and external counsel needs instruction
- Engagement scope needs to be varied and a formal scope-change letter is required
- External counsel needs a regulatory context brief (FAR accountability, CPS 230 obligations, etc.)

Do NOT use when:
- The audience is internal (use exec-memo-writing for internal briefs to GC/ELT)
- You need a formal legal advice memo (that is produced BY the law firm, not to it)
- The matter requires only a phone-call or email thread — very short informal instructions do not need a structured briefing memo

---

## Clarify before drafting

Ask (or infer from context) before writing:

| Question | Why it matters |
|---|---|
| Matter type? (regulatory/litigation/transactional/advisory) | Determines which structure variant to use |
| Which law firm and partner? | Salutation, engagement history, billing relationship |
| Is this a new engagement or ongoing matter update? | New = full instructions; ongoing = scope update/status brief |
| What is the regulatory trigger? (APRA, ASIC, AUSTRAC, OAIC, FAR…) | Determines which statutes/standards to name |
| What is the key ask — advice, review, attend, represent? | Shapes the BLUF and scope section |
| Fee cap, budget approval, matter code? | Required for law firm cost management |
| LPP status — is this communication itself privileged? | Opening privilege declaration may be needed |
| Confidentiality constraints — NDB, CPS 230 notification pending? | Determines what facts can be stated and when |
| Is the matter FAR-notifiable or APRA-disclosable? | May require mandatory notification wording |
| Which internal matter management system / matter code applies? | Required for legal ops / ELM cross-reference |

---

## Australian Regulatory Context (embedded — do not omit)

These apply to almost every matter for an APRA-regulated ADI. Know which apply before drafting.

### Regulatory bodies and frameworks

Paragraph numbers, notification clocks, and standard identifiers below are snapshots — **verify with current legislation** (legislation.gov.au + apra.gov.au live standards) before relying on them in a brief.

| Body / Framework | Scope | Key provisions |
|---|---|---|
| **APRA** — Australian Prudential Regulation Authority | Prudential supervision of ADIs | CPS 230 (Op Risk), CPS 234 (Info Security), APS 330, **APS 220** (credit quality — not CPS 220) |
| **ASIC** — Australian Securities and Investments Commission | Market conduct, consumer protection, financial services | Corporations Act 2001, ASIC Act 2001 s12DA, RG 279 |
| **AUSTRAC** | AML/CTF compliance | AML/CTF Act 2006; SMR/TTR reporting obligations |
| **OAIC** — Office of the Australian Information Commissioner | Privacy, NDB scheme | Privacy Act 1988, NDB scheme (30-day assessment clock) |
| **ACCC** — Australian Competition & Consumer Commission | Competition, consumer law | Competition and Consumer Act 2010, ACL |
| **FAR** — Financial Accountability Regime | Senior officer accountability | FAR Act 2023; accountability statements; commenced 15 March 2024 for ADIs (verify current FAR entity thresholds) |
| **Banking Act 1959** | ADI licensing; **s62ZZO is Banking Act compulsory assistance**, not a generic "APRA directions" power | s29; s62ZZO (verify with current legislation) |
| **Banking Code of Practice** | Customer-facing conduct | ABA Banking Code 2019 as amended |

Do not conflate **CPS 220** (APRA *Risk Management* standard) with **APS 220** (ADI *Credit Quality*). They are different instruments.

### Privilege and confidentiality triggers for AU banks

- **Legal professional privilege (LPP)**: AU common law + Evidence Act 1995 (Cth/NSW/Vic). Communications with external counsel for dominant purpose of legal advice or litigation are privileged. When briefing external counsel, state LPP assertion explicitly if sensitive facts are included.
- **LPP waiver risk with AI tools**: Sharing privileged advice with third-party AI models risks waiver under the "inconsistency" test (Mann v Carnell [1999] HCA 66). Use confidentiality agreements with any AI vendor or use internal models only.
- **Banking Act s62ZZO (compulsory assistance)**: This is a *Banking Act 1959* power, not a generic APRA-directions heading and not an APRA Act information-gathering notice. APRA also has separate information-gathering powers under the APRA Act. Identify the actual instrument before asserting LPP. **Verify with current legislation.**
- **NDB notifications (Privacy Act 1988 Pt IIIC)**: 30-day assessment clock to determine if eligible data breach; notify OAIC + individuals once confirmed. Separate from CPS 230 72-hour clock.
- **CPS 230 notification — two separate clocks (July 2026)**:
  - Para 32 (material operational risk incident): notify APRA within **72 hours** of becoming aware of an incident likely to have material financial impact or material impact on critical operations.
  - Para 41 (critical operation disruption outside tolerance): notify APRA within **24 hours**. This is the shorter, more urgent clock — applies when a critical operation has actually breached its tolerance level. Determine which clock is running and brief external counsel accordingly.
- **CPS 234 notification (para 35, info security incidents)**: Material information security incidents — notify APRA within **72 hours**. Separate clock from CPS 230 para 32; both may run simultaneously for a cyber-incident. Do NOT confuse these three clocks.
- **FAR accountability mapping**: For FAR-notifiable matters, identify the accountable individual (AI) and their accountability statement obligations. Matters touching AI obligations must be reported to APRA under FAR.

---

## CPS 230 Material Service Provider Check (do this before drafting)

From APRA CPS 230 (skill snapshot: finalised April 2026, commenced 1 July 2026 — **verify with current legislation**): external law firms engaged on **material arrangements**
must be assessed under the Material Service Provider (MSP) framework. A legal service is a
material arrangement if it supports a critical operation of the ADI. Paragraph numbers below are snapshots, not timeless.

Before issuing instructions on a significant ongoing matter:
- [ ] Has Legal confirmed whether this engagement is a "material arrangement" under CPS 230?
- [ ] If yes: is the law firm on the MSP Register submitted to APRA (para 50)?
- [ ] If entering or materially changing a material arrangement for a critical operation: notify APRA within 20 business days (para 60(a)). For material offshoring arrangements: notify APRA prior to commencement (para 60(b)). Do not wait until the notice window closes before engaging Legal.
- [ ] CPS 230 para 41: if a disruption to a critical operation is reasonably expected to exceed tolerance levels, notify APRA within 24 hours — separate from the 72-hour operational risk incident notification (para 32). Both clocks may run on the same event.
- [ ] April 2026 amendments introduced "exempt service provider" categories — some legal services may qualify for limited contractual exemptions where "contractual compliance is not practicable"

Note: for one-off advisory matters or short-form engagements, the MSP framework likely does not apply. Confirm with Legal Ops before seeking exemption.

---

## eBrief Standards (post-2020 Australian Practice)

Per NSW Bar Association Electronic Briefing Guideline 2022 and r/auslaw practitioner consensus:

- **Standard format:** Single PDF with bookmarks per document. Not multiple emails with attachments.
- **Document naming:** Date + document type (e.g., "2026-03-15 APRA Notice s62"). Not "scan0001.pdf".
- **Document order:** Chronological order strongly preferred by barristers. Deviations must be explained.
- **Tabs/exhibit references:** Sequential tab numbers or exhibit labels; listed in an Index to Brief.
- **Factual chronology:** Separate Word document for substantial matters. Required on most matters.
- **Court/tribunal chronology:** Separate document for contested litigation.
- **Hardcopy:** Still used for major trials; spine labels required. For advisory matters, eBrief only.
- **Anti-patterns (r/auslaw consensus — what ruins a brief):**
  - Multiple emails with attachment chains ("FYI" / "Email 1 of 5")
  - Attachments within attachments
  - Draft documents indistinguishable from final documents in the bundle
  - Duplicate documents with slightly different filenames
  - No index, no numbering, no observations memo at all

Free precedent templates (NSW Bar Association):
- Observations to Counsel: nswbar.asn.au/uploads/word-documents/Observations_021118.docx
- Index to Brief: nswbar.asn.au/uploads/word-documents/Index_Brief_021118.docx
- Factual Chronology: nswbar.asn.au/uploads/word-documents/Factual_Chronology_021118.docx
- Court/Tribunal Chronology: nswbar.asn.au/uploads/word-documents/Court_Chronology_021118.docx
- Brief Checklist: nswbar.asn.au/uploads/word-documents/Checklist_Brief_021118.docx
- Electronic Briefing Guideline 2022: nswbar.asn.au/uploads/pdf-documents/Electronic_Briefing_Guideline_2022.pdf

---

## Output Marking Convention (from anthropics/claude-for-legal patterns)

Every briefing memo output from this skill should carry:
- At the top: `[DRAFT — ATTORNEY REVIEW REQUIRED BEFORE SENDING]`
- On any cited regulatory section: tag as `[verify: apra.gov.au]` or `[verify: legislation.gov.au]`
- On any inferred fact: `[confirm with matter owner]`
- At the bottom: a Reviewer Note listing sources used, flags, what to verify, and currency of cited standards

---

## Structure — Master Template

```
[BANK LETTERHEAD OR INTERNAL HEADER]

STRICTLY PRIVILEGED AND CONFIDENTIAL
LEGAL PROFESSIONAL PRIVILEGE CLAIMED

[DATE]

[Partner Name]
[Practice Group Lead / Managing Partner]
[Firm Name]
[Address]

Dear [Partner name],

RE: [MATTER — action-oriented, specific, one line]
    Matter Code: [INTERNAL CODE]
    [Law Firm File Reference if known]

─────────────────────────────────────────────
INSTRUCTIONS SUMMARY
─────────────────────────────────────────────
[One paragraph — what we want you to do, the key regulatory or legal issue,
the deadline or urgency driver, and the fee approval. Must be readable standalone.]

─────────────────────────────────────────────
BACKGROUND AND CONTEXT
─────────────────────────────────────────────
[2–4 paragraphs. Facts of the matter. Regulatory trigger if any.
Internal escalation path (who knows, who approved this instruction).
History of the matter if ongoing. What internal analysis has been done.]

─────────────────────────────────────────────
SCOPE OF INSTRUCTIONS
─────────────────────────────────────────────
[Numbered list of specific tasks being instructed.
Be precise — scope drift is the primary cost driver in external counsel engagements.
State what is IN scope AND what is OUT of scope.]

─────────────────────────────────────────────
REGULATORY AND LEGAL FRAMEWORK
─────────────────────────────────────────────
[Applicable statutes, standards, and regulatory guidance.
Include relevant APRA/ASIC/AUSTRAC/OAIC instruments.
State which regulatory body is (or may be) involved.]

─────────────────────────────────────────────
DELIVERABLES AND TIMELINE
─────────────────────────────────────────────
[What do we want back, in what form, by when.
Distinguish: interim update / draft advice / final advice / attendance at regulatory meeting / etc.]

─────────────────────────────────────────────
FEE ARRANGEMENT AND BILLING INSTRUCTIONS
─────────────────────────────────────────────
[Approved fee cap, matter code, billing contacts, billing frequency,
preferred format for invoices, GST treatment.]

─────────────────────────────────────────────
KEY CONTACTS
─────────────────────────────────────────────
[Internal matter owner. Internal approver. Legal ops contact.
Who to call for urgent escalation. Data room / document access instructions if applicable.]

─────────────────────────────────────────────
PRIVILEGE AND CONFIDENTIALITY
─────────────────────────────────────────────
[Confirm privilege claim. State any constraints on disclosure.
If NDB or CPS 230 clock is running, state the relevant notification deadline.]

─────────────────────────────────────────────
CONFLICTS AND INDEPENDENCE
─────────────────────────────────────────────
[Confirm no conflict of interest; confirm independence from counterparty.
Request written confirmation of conflict clearance before substantive work begins — ASCR 2026 Rule 11.
If firm has acted for any counterparty in the past 24 months: flag for GC review before engaging.]

─────────────────────────────────────────────
ENGAGEMENT TERMS
─────────────────────────────────────────────
[Reference to applicable Outside Counsel Guidelines / master legal services agreement.
ASCR (skill snapshot: 2026 Rule 13 — **verify with current legislation**): state when the engagement ends — "Engagement concludes upon delivery of
[deliverable] and resolution of any clarification questions arising within [X] business days."]

─────────────────────────────────────────────
DATA HANDLING (required if personal information involved)
─────────────────────────────────────────────
[Required if any customer data, employee data, or personal information is involved.]
Documents provided under this engagement may contain personal information within the meaning
of the Privacy Act 1988 (Cth). Handle all personal information in accordance with the
Australian Privacy Principles. Do not use or disclose personal information other than for
the purpose of this engagement. Destroy or return all personal information on completion
of this engagement per our data retention instructions.
[If work is to be performed in overseas offices: "Note that APP 8 (cross-border disclosure)
applies to any transfer of personal information offshore. Confirm your overseas office
data handling arrangements are APP-compatible before proceeding."]

─────────────────────────────────────────────
REVIEWER NOTE
─────────────────────────────────────────────
Standards cited: [list standards and their as-at date]
Flags: [anything not verified or confirmed by matter owner]
Verify before sending: [regulatory citations, matter code, fee cap, privilege status]
```

---

## Structure Variants by Matter Type

### Variant A: Regulatory Investigation / Inquiry (most common for AU bank)

Use when: APRA, ASIC, AUSTRAC, OAIC, or ACCC has issued a notice, commenced an inquiry, or signalled supervisory concern.

Additional mandatory sections beyond master template:
- **Regulatory Notice or Trigger**: Attach or summarise the exact regulatory notice. State receipt date.
- **Response Deadline**: State the statutory or regulatory deadline for the bank's response.
- **FAR Accountable Individual**: Name the AI with accountability for this matter under FAR.
- **Privilege Segregation**: State whether the regulatory body has been told that legal advice privilege is claimed.
- **Parallel Obligations**: Flag any parallel notification obligations running simultaneously (CPS 230 72hr, NDB 30-day, FAR accountability notice, ASX disclosure if listed).
- **Prior Contact with Regulator**: Disclose any prior informal contact between the bank and the regulatory body.

BLUF tone for regulatory briefs: factual, controlled, no speculation. "ASIC has issued a notice under s.30 of the ASIC Act requiring production of documents by [date]. We instruct you to represent the bank in responding, advise on scope of production, and attend the ASIC meeting scheduled [date]."

### Variant B: Litigation / Threatened Litigation

Use when: claim received, LBA received, proceedings served, or internal decision to commence.

Additional mandatory sections:
- **Claim / Proceedings Summary**: Nature of claim, parties, relief sought, quantum.
- **Limitation Periods**: Flag any running limitation periods (Limitations Act timeframes by state).
- **Preservation Notice Status**: Has a litigation hold been issued internally? State yes/no.
- **Insurance**: Is this a matter potentially covered by D&O, PI, or banker's blanket bond? If yes, name insurer and whether notification has been made.
- **Without Prejudice Communications**: Disclose any prior settlement discussions.
- **Internal Witnesses**: Identify key witnesses and whether they will need independent legal advice.

BLUF tone for litigation: more urgent, specific about quantum and limitation risk. "The bank received a statement of claim on [date] claiming damages of $[X]. The applicable filing deadline falls on [date] — confirm the current court rules; do not assume a 28-day defence period. We instruct you to file a defence and advise on settlement strategy."

### Variant C: Transactional Matter (acquisition, disposal, significant contract)

Use when: M&A, asset acquisition, significant commercial contract, joint venture, or lending transaction.

Additional mandatory sections:
- **Transaction Overview**: Deal structure, parties, commercial rationale.
- **Conditions Precedent**: Key regulatory approvals required (FIRB, ACCC, APRA no-objection if applicable).
- **Exclusivity / Timing**: Exclusivity period, expected signing and completion dates.
- **Data Room Access**: Instructions for accessing due diligence materials.
- **Existing Precedents**: Reference any prior similar transactions where the same firm acted.

### Variant D: Ongoing Matter Update / Scope Change

Use when: updating instructions, changing scope, or issuing a variation to an existing matter brief.

Structure is abbreviated:
```
RE: [MATTER NAME] — Scope Variation / Updated Instructions
    Matter Code: [same code]

Dear [Partner],

Further to our instructions of [DATE], we write to [expand / reduce / vary] the scope as follows:

ADDITIONAL / VARIED INSTRUCTIONS:
[numbered delta list only — do not restate original scope]

REVISED FEE CAP:
[new cap or confirmation that existing cap is sufficient]

UPDATED DELIVERABLES AND TIMELINE:
[revised dates only]

Please confirm receipt and your capacity to act within revised scope.

Yours sincerely, ...
```

### Variant E: Standalone Regulatory Context Brief (for complex new matters)

Use when: firm is new to this regulatory area or the bank needs to ensure counsel understands the full AU regulatory overlay before giving advice.

This variant prepends a regulatory primer before the instructions:
- Opens with a "Regulatory Context" section (3–5 paragraphs) explaining the relevant APRA/ASIC/FAR framework as it applies to the bank
- States what the bank's internal risk appetite / policies say about this area (without disclosing privileged internal advice)
- Then flows into standard Instructions / Scope / Deliverables

---

## Writing Style Rules (AU Legal Professional Context)

### Formality register
- External counsel briefings are formal but direct. Not stuffy British formality; not casual email tone.
- Use "we instruct you to" not "we would appreciate if you could."
- Name the deadline: "by [DATE]" not "in due course" or "as soon as practicable."
- Use firm names in full on first reference, then shortened: "Allens Linklaters" → "Allens."

### AU legal profession conventions
- Salutation: "Dear [Partner first name]," (common law AU convention; not "Dear Sir/Madam" unless unknown recipient)
- Closing: "Yours sincerely," (not "Kind regards" for formal instruction letters)
- Heading: all-caps or bold; one line; action-oriented (e.g., "RE: ASIC NOTICE — RESPONSIBLE LENDING REVIEW")
- Privilege header: "STRICTLY PRIVILEGED AND CONFIDENTIAL / LEGAL PROFESSIONAL PRIVILEGE CLAIMED" above the salutation; standard AU practice
- Date: "21 August 2026" (day-month-year; not US format)
- Currency: AUD or $ with no ambiguity; do not use "$" where USD/NZD context could apply

### Precision over hedging
- State what you know; flag what is uncertain. Do not hedge everything.
- "The amount claimed is $2.4M" not "we believe the amount may be approximately $2.4M."
- If genuinely uncertain: "Quantum has not been disclosed; we estimate exposure at $X based on [reason]."

### AU regulatory citation style
- APRA standards: "CPS 230 (Operational Risk Management) para [XX] — [section heading]" not just "CPS 230." Do not cargo-cult a paragraph number without verifying it is the right one — cite the section heading if uncertain and add [verify: apra.gov.au] tag.
- Legislation: "Corporations Act 2001 (Cth) s 912A(1)(a)" with jurisdiction identifier.
- ASIC regulatory guides: "RG 279 (Financial Accountability Regime)" with publication date if quoting.
- APRA enforcement orders / notices: cite full title as it appears on the APRA notice.
- Do NOT invent standard numbers or section numbers — verify before citing.

### Sentence discipline
- 15–20 words average. Long sentences for background; short for scope and deliverables.
- Active voice: "We instruct you to file the defence" not "It is requested that a defence be filed."
- One instruction per numbered item — do not bundle two tasks into one numbered point.
- MECE scope list: no gaps, no overlaps between numbered instructions.

### Numbers
- Quantify the exposure, the fee cap, the deadline. A memo with vague quantification is not actionable.
- "$4.2M" not "$4,187,423" in running text; exact figure acceptable in a schedule.
- GST-exclusive for fee caps unless stated otherwise; note if GST is included.

---

## AU Law Firm Specific Notes (Big-6 firms)

The following AU firms are commonly instructed by major banks. Engagement conventions vary:

| Firm | Practice area strengths for banks | Billing conventions |
|---|---|---|
| Allens | APRA regulatory, M&A, capital markets | Matter-based budget letters standard |
| King & Wood Mallesons (KWM) | Banking & finance, regulatory, disputes | Monthly WIP reports; matter code required |
| MinterEllison | Litigation, insurance, consumer law, regulatory | Preferred panel firm for many AU banks |
| Gilbert + Tobin (G+T) | M&A, competition, financial services regulation | Known for clear scope letters; secondments common |
| Herbert Smith Freehills (HSF) | APRA/ASIC regulatory, litigation | Global alignment; AU-specific billing team |
| Clayton Utz | Insurance, disputes, government advisory | Common for major litigation matters |
| Ashurst | Structured finance, capital markets, regulatory | Preferred for ISDA/derivative documentation |

Panel arrangements: most major AU banks (CBA, NAB, ANZ, Westpac) maintain a legal panel. Confirm whether the firm is on-panel before issuing instructions; off-panel engagements require separate approval.

---

## Legal Privilege Checklist (run before sending)

- [ ] Privilege claim header included ("STRICTLY PRIVILEGED AND CONFIDENTIAL / LEGAL PROFESSIONAL PRIVILEGE CLAIMED")
- [ ] Dominant purpose of communication is legal advice or litigation — confirm before including sensitive operational facts
- [ ] No third parties copied who would break privilege (privilege is shared between client and lawyer only; add other bank legal staff to To/CC only, not compliance officers or business who aren't part of the legal team unless necessary)
- [ ] If forwarding to internal stakeholders later, remind recipients that LPP status does not extend beyond the legal team without legal sign-off
- [ ] Confirm the law firm has a confidentiality agreement in place covering AI tools they use — sharing privileged advice with the firm's AI platform without a data processing agreement risks waiver (Stirling & Rose, 2024; Mann v Carnell [1999] HCA 66)

---

## Quality Checklist (run before sending)

**Structure:**
- [ ] Privilege header present
- [ ] Matter code / law firm file reference stated
- [ ] BLUF (Instructions Summary) paragraph standalone-readable
- [ ] Scope list is numbered, MECE, and unambiguous
- [ ] All regulatory statutes and standards cited correctly (verify section numbers)
- [ ] Fee cap stated (GST treatment clear)
- [ ] Deliverables are named outputs with due dates, not vague intentions
- [ ] Key contacts named (including urgency escalation path)
- [ ] Privilege and confidentiality section present
- [ ] FAR accountable individual named for regulatory matters

**Writing:**
- [ ] Active voice dominant
- [ ] No vague timeframes ("as soon as practicable" → name the date)
- [ ] Currency unambiguous (AUD)
- [ ] Regulatory citations verified (not invented)
- [ ] Date in Australian format (DD Month YYYY)
- [ ] Closing: "Yours sincerely,"

**AU legal specific:**
- [ ] If matter is regulatory: response deadline to regulator stated
- [ ] If CPS 230/NDB clock running: relevant notification deadline stated explicitly
- [ ] If FAR-notifiable: accountable individual named and FAR obligation stated
- [ ] LPP waiver risk assessed if external AI tools are involved at firm side

---

## Pitfalls

- **Scope drift without a written brief**: The most costly failure mode in external counsel engagements. Verbal instructions expand silently. Always reduce scope to writing before work commences; use Variant D (scope change letter) to vary it formally.

- **Invented regulatory citation numbers**: Do NOT invent APRA standard paragraph numbers, ASIC regulatory guide sections, or Act section numbers. Verify against primary sources (APRA.gov.au, ASIC.gov.au, legislation.gov.au) before including. A wrong citation in a brief to a law firm is embarrassing and may mislead advice.

- **Confusing CPS 230 and CPS 234 notification windows**: These are separate:
  - CPS 230 para 32: operational risk incident (material financial/operational impact) = notify APRA "as soon as possible and not later than 72 hours"
  - CPS 230 para 41: disruption to critical operation (exceeds tolerance levels) = notify APRA "as soon as possible and not later than 24 hours"
  - CPS 234 para 35: information security incident = 72 hours
  - Privacy Act NDB scheme: 30-day assessment window after becoming aware of potential eligible data breach
  These clocks are independent and may run simultaneously on the same event. The brief must state which clock(s) apply and their current position.

- **AML/CTF tipping-off is a criminal offence**: When briefing on AML/CTF matters, include explicit tipping-off instructions. AML/CTF Act 2006 s123 protects SMR information from disclosure — violation is criminal. The brief must state: "Do not disclose the existence of any suspicious matter report or related investigation to any person other than [named Bank legal contacts]." Post-July 2026 reforms: some law firm services are now "designated services" — check whether the instructed firm's own AML/CTF obligations conflict with matter instructions.

- **FAR matters: external counsel must NOT contact APRA independently**: Instruct external counsel on FAR matters that all regulatory contact must be coordinated through the bank. FAR@apra.gov.au is the APRA contact point — bank legal approves any contact before it occurs. Accountable individuals facing personal FAR liability may need independent legal advice — flag this in the brief.

- **CPS 230 MSP check omitted**: For significant ongoing matters, confirm before issuing whether the law firm engagement is a "material arrangement" under CPS 230. If yes, and it involves a critical operation: notify APRA within 20 business days of entering or materially changing the arrangement (para 60(a)). For material offshoring: notify APRA prior to commencement (para 60(b)). Submit the firm to the MSP Register annually (para 50). Substantive work should not commence on a new material arrangement before the notification obligation is understood.

- **Privilege header without substance**: Marking a document "Privileged" does not create privilege. AU evidence law recognises two heads of privilege in this context: s118 (legal advice privilege — communication made for the dominant purpose of obtaining legal advice) and s119 (litigation privilege — document prepared for the dominant purpose of existing or reasonably apprehended litigation). Both require a "dominant purpose" assessment. If the dominant purpose is commercial rather than legal, privilege does not attach regardless of the header. Key risk: briefing memos that include operational risk facts, financial exposures, or business strategy alongside legal instructions may fail the dominant purpose test. Get in-house legal sign-off before including sensitive operational facts. For communications privilege, Mann v Carnell [1999] HCA 66 remains the leading AU authority on implied waiver.

- **Copying compliance officers or business stakeholders without thought**: Adding non-lawyers to the email loop may break LPP. Confirm with in-house counsel before copying.

- **Fee cap stated in GST-exclusive terms when firm invoices GST-inclusive**: Always specify whether the cap is "exclusive of GST and disbursements" to avoid disputes on first invoice.

- **Omitting the FAR accountable individual**: For regulatory matters involving an APRA-regulated ADI, the FAR accountable individual should be named in the brief. The firm needs the governance chain to advise correctly on notification obligations.

- **Using email format for formal instructions**: Formal instruction letters for significant matters should be issued as PDF or DOCX on letterhead, not as a plain email. Use the docx or pdf skill for formal document output.

- **Wrong firm on panel**: Confirm the firm is on the bank's legal panel before issuing. Off-panel instructions require GC or Deputy GC sign-off at most major AU banks.

- **Stating facts that are subject to pending regulatory disclosure**: If a CPS 230 or FAR notification is pending but not yet made, do not include those facts in an external brief without legal sign-off on what can be disclosed and to whom.

- **Skipping conflict check in writing**: ASCR (skill snapshot: 2026 Rule 11 — **verify with current legislation**) — always request written confirmation of conflict check clearance before substantive work begins. Verbal confirmation is not enough. If firm acted for a counterparty in the past 24 months, escalate to GC before proceeding.

- **No document index or eBrief structure**: r/auslaw practitioners uniformly report that unstructured document dumps (multiple emails, unnamed files, no index) are the most common brief failure mode. Any brief with more than 5 documents requires a numbered index and chronological ordering.

- **ASCR Rule 8 / Rule 9 omitted**: Rule 11 (conflicts) and Rule 13 (end of engagement) are not enough. Rule 8 requires lawful, clear client instructions — the briefing memo is how the ADI exercises that right. Rule 9 requires confidentiality handling in the brief itself: "Do not disclose to any third party, including any regulator, without prior written consent."
  <!-- why: prevents a brief that looks complete on conflicts/termination but leaves the solicitor without lawful-instruction and confidentiality terms -->

- **Instructions cannot direct professional judgment**: Legal Profession Uniform Law — instruct scope and facts only. Do not word instructions as directing the outcome of counsel's independent assessment.
  <!-- why: prevents an LPUL/professional-independence breach when a bank tries to script the advice conclusion -->

- **Compulsory production: notify bank legal first**: If counsel receives a compulsory request from APRA, ASIC, AUSTRAC, or another regulator for matter documents, they must notify the named Bank legal contact immediately and not respond until authorised. Do not treat **Banking Act s62ZZO** as interchangeable with APRA Act information-gathering powers — identify the instrument. **Verify with current legislation.** [legislation.gov.au]
  <!-- why: prevents counsel answering a regulator before the ADI has asserted LPP and coordinated FAR/APRA contact -->

- **Wrong prudential standard for the matter type**: CPS 230/234 are not the only APRA overlays. CPS 511 (remuneration/clawback) applies to exec-pay matters; APS 220 (credit quality) applies to loan enforcement/recovery. FAR enhanced entities (skill snapshot: total assets >$20 billion — **verify with current legislation**; thresholds change) have extra notification (accountability maps, statements, material changes).
  <!-- why: prevents briefing a recovery or rem matter as a generic CPS 230 operational-risk file -->

- **Direct-briefing eligibility**: An in-house lawyer with a current practising certificate can directly brief a barrister (NSW Bar). Do not assume a panel solicitor must always sit in the middle.
  <!-- why: prevents unnecessary panel-firm delay on an urgent counsel brief when in-house holds a practising certificate -->

- **Observations that omit client expectations**: Barristers want what the client has been told to expect, any killer evidence/weakness, and current settlement thinking — not just a document dump. See `references/research-community.md`.
  <!-- why: prevents an eBrief that is chronologically perfect but leaves counsel guessing the client's instructions -->

---

## Workflow

1. Clarify matter type, firm, regulatory context, key ask (use clarify questions above).
2. Run CPS 230 MSP check before committing to engage.
3. Choose structure variant (A–E).
4. Write Instructions Summary (BLUF) first — if you cannot write it clearly, you do not have enough facts yet.
5. Draft scope list: numbered, MECE, no bundled tasks.
6. Verify all regulatory citations against primary sources (apra.gov.au, legislation.gov.au, asic.gov.au).
7. For matters with documents: prepare numbered index + chronological eBrief (single PDF with bookmarks).
8. Run privilege checklist.
9. Run quality checklist.
10. Mark output: `[DRAFT — ATTORNEY REVIEW REQUIRED BEFORE SENDING]` + Reviewer Note at bottom.
11. Deliver as DOCX or PDF on letterhead for significant matters (use docx / pdf skill).
12. For email-based shorter instructions (Variant D), confirm partner read receipt.

---

## Completion contract

This skill is complete ONLY when:
1. The briefing memo has been drafted and meets the quality checklist
2. Regulatory citations have been verified (not just stated)
3. The privilege checklist has been run
4. For formal matters: the document has been formatted for delivery (docx/pdf skill) or explicitly noted as suitable for email delivery
5. The user has confirmed the firm is on-panel or off-panel approval is in place

---

## Reference sources

### Local research dumps (read on demand; do not cargo-cult stale paragraph numbers)
- `references/research-en.md` — CLOC/LPM structure, ASCR 8/9/13, FAR enhanced-entity overlay, Privacy APP 8, AML designated-services. Some CPS 230 para numbers in this dump are pre-July 2026 — prefer the skill body (para 50/60/41).
- `references/research-multilang.md` — comparative briefing forms; AU takeaway is LPUL professional independence (instructions ≠ directed outcome).
- `references/research-community.md` — NSW Bar toolkit, r/auslaw eBrief anti-patterns, direct briefing with practising certificate.
- `references/adversarial-review.md` — CPS 230 para 59→60 / 51→50, Evidence Act s118 vs s119, para 41 24-hour clock. Survivors already applied in this skill; keep as the audit trail.

### Primary AU regulatory (always verify against live versions)
- APRA CPS 230 (Operational Risk Management, updated April 2026): apra.gov.au/operational-risk-management
- APRA CPS 234 (Information Security): apra.gov.au/standards/cps-234
- APRA **CPS 220** (Risk Management) — distinct from **APS 220** (Credit Quality): apra.gov.au. Do not cite CPS 220 for loan-enforcement/credit-quality matters. Verify with current legislation.
- FAR Act 2023 + APRA/ASIC implementation (updated July 2024): apra.gov.au/financial-accountability-regime
- ASIC RG 279 (Financial Accountability Regime): asic.gov.au
- Privacy Act 1988 (Cth) NDB scheme: oaic.gov.au/privacy/notifiable-data-breaches
- AML/CTF Act 2006 (July 2026 reforms): austrac.gov.au
- Banking Act 1959 (Cth): legislation.gov.au
- Law Council — Australian Solicitors' Conduct Rules 2026: lawcouncil.au/policy-agenda/regulation-of-the-profession-and-ethics/australian-solicitors-conduct-rules
- Law Council — National Legal Profession AML/CTF Guidance (June 2026): lawcouncil.au/resources/policies-and-guidelines/national-legal-profession-anti-money-laundering---counter-terrorism-financing-guidance

### AU practitioner resources (verified accessible August 2026)
- NSW Bar Association — Briefing a Barrister toolkit: nswbar.asn.au/using-barristers/briefing-a-barrister
- NSW Bar — Observations to Counsel template: nswbar.asn.au/uploads/word-documents/Observations_021118.docx
- NSW Bar — Index to Brief template: nswbar.asn.au/uploads/word-documents/Index_Brief_021118.docx
- NSW Bar — Factual Chronology template: nswbar.asn.au/uploads/word-documents/Factual_Chronology_021118.docx
- NSW Bar — Brief Checklist: nswbar.asn.au/uploads/word-documents/Checklist_Brief_021118.docx
- NSW Bar — Electronic Briefing Guideline 2022: nswbar.asn.au/uploads/pdf-documents/Electronic_Briefing_Guideline_2022.pdf
- ALPMA (Australian Legal Practice Management Association): alpma.com.au
- ACLA (Association of Corporate Lawyers Australia): acla.com.au
- CLOC Core 12 — Firm & Vendor Management: cloc.org/cloc-core-12/firm-and-vendor-management/
- CLOC — Collaborative Counsel (2021): cloc.org/blog/core-12/collaborative-counsel-8-practical-ways-to-work-better-together/

### Legal project management
- CLOC Core 12 framework: cloc.org/cloc-core-12/
- VLSB+C / LSNSW Joint AI Statement (Dec 2024): lsbc.vic.gov.au (AI in legal practice)

### Privilege and confidentiality
- Mann v Carnell [1999] HCA 66 (LPP waiver — AU leading case)
- Evidence Act 1995 (Cth) ss 118–120 (lawyer–client privilege)
- Stirling & Rose (2024): AI tools and LPP waiver risk in AU: stirlingandrose.com/2024/03/21/client-privilege-at-risk-sharing-legal-advice-with-ai-models/

### Community sources (verified)
- r/auslaw — How to write a professional brief: reddit.com/r/auslaw/comments/yz9xey/
- r/auslaw — Do you read the observations to your brief: reddit.com/r/auslaw/comments/171yzaf/
- r/auslaw — When to brief counsel: reddit.com/r/auslaw/comments/3pcjen/

### GitHub reference implementations
- anthropics/claude-for-legal: github.com/anthropics/claude-for-legal (design patterns: Reviewer Note, source tagging, [DRAFT] marking)
- openmagi/korean-legal-doc-drafter: github.com/openmagi/korean-legal-doc-drafter (Korean legal doc architecture patterns)
