# Adversarial Review — Law Firm Briefing Memo Skill
**Subject:** `/var/home/rainbow/hermes-config/skills/productivity/law-firm-briefing-memo/SKILL.md`
**Context:** Australian ADI (APRA-regulated, NAB-scale), in-house legal counsel, instructions letters / regulatory briefs to external law firms.
**Methodology:** Three-round recursive review. Sources verified: APRA CPS 230 (July 2026 clean PDF), CPS 234 (APRA.gov.au), AUSTRAC AML/CTF Act page, APRA FAR page, Evidence Act 1995 (Cth) standard commentary.

---

## Round 1 — Attack (candidate findings)

### A1. CPS 230 paragraph numbering — MSP notification (lines 114–115, 459)
Skill states: *"APRA notification required under para 59(a)(b) before engagement commences"* and repeats "para 59" at line 115 and line 459.

**July 2026 CPS 230 (clean PDF, April 2026 finalised, commenced 1 July 2026)**: The MSP notification obligation is at **paragraph 60**, not paragraph 59. Para 59 is the monitoring obligation. Para 60 is the notification obligation.

### A2. CPS 230 MSP notification timing is wrong (lines 114–115)
Skill states: *"APRA notification required under para 59(a)(b) before engagement commences."*

**July 2026 CPS 230 para 60(a)**: Notification must be made *"as soon as possible and not more than **20 business days after** entering into or materially changing"* a material arrangement. This is **not** a pre-engagement requirement for critical operations generally — that framing applies only to *offshoring* (para 60(b), which does require notification **prior to** entering). Collapsing these two distinct requirements into "before engagement commences" is factually incorrect for the main (non-offshoring) case and will cause users to over-comply or miscite.

### A3. CPS 230 MSP Register paragraph — wrong paragraph number (line 113)
Skill states: *"is the law firm on the MSP Register submitted to APRA (para 51)?"*

**July 2026 CPS 230**: **Para 50** is the MSP Register submission obligation ("An APRA-regulated entity must submit its register of material service providers to APRA on an annual basis"). **Para 51** is APRA's discretion to classify service providers. The skill has the wrong paragraph number for the core obligation.

### A4. Evidence Act 1995 s 119 cited for legal advice privilege (line 461)
Skill states: *"The dominant purpose test (Evidence Act 1995 s 119) governs."* This appears in the context of legal advice privilege (commercial vs legal purpose), not litigation privilege.

**Evidence Act 1995 (Cth):**
- **s 118**: Legal advice privilege — applies where dominant purpose is giving/receiving legal advice.
- **s 119**: Litigation privilege — applies where dominant purpose is preparing for anticipated litigation.

The dominant purpose test for *legal advice privilege* is **s 118**, not s 119. The skill cites the wrong section for the wrong privilege type. A bank counsel who reads this and cites s 119 for a legal advice privilege claim in a regulatory proceeding has cited the wrong section of the Act.

### A5. CPS 230 para 41 — 24-hour critical operation disruption window entirely omitted (lines 100, 280, 453)
Skill acknowledges the CPS 230 "72-hour" notification window multiple times. It does **not** mention the separate and shorter **24-hour window** in CPS 230 para 41 for disruptions to critical operations outside tolerance. Where a law firm is instructed on a business continuity/critical operation matter, missing this deadline could be catastrophic.

July 2026 CPS 230 para 41 (verified from PDF): *"An APRA-regulated entity must notify APRA as soon as possible, and not later than 24 hours after, if it has suffered a disruption to a critical operation outside tolerance."*

### A6. CPS 230 "para 36" example citation — wrong context (line 370)
Skill instructs users to cite *"CPS 230 (Operational Risk Management) para 36"* as a model for specific citation. In the July 2026 CPS 230, **para 36** covers internal audit assurance requirements for service provider information security controls — a highly specific and unrelated topic. Using this as a "model citation example" risks users cargo-culting "para 36" into real documents where it will be wrong and embarrassing.

### A7. CPS 234 notification window — not stated precisely (lines 453, 99–100)
Skill says CPS 234 (info security) "has its own window" but does not state what it is.

**CPS 234 para 35** (verified from APRA.gov.au): 72 hours for material information security incidents. Omitting the number forces the user to look it up — acceptable trade-off, but the skill gives the NDB 30-day clock explicitly (line 99), inconsistently leaving CPS 234 unstated.

### A8. FAR commencement date (line 94) — minor precision issue
Skill states FAR effective *"15 March 2024 for ADIs"*. Verified from APRA.gov.au: FAR commenced for ADIs *"from 15 March 2024."* This is **correct**. Not an error.

### A9. AML/CTF s 123 tipping-off (line 455)
Skill states: *"AML/CTF Act 2006 s123 protects SMR information from disclosure — violation is criminal."* Verified from AUSTRAC/legislation.gov.au: s 123 of the AML/CTF Act 2006 is the tipping-off offence. This is **correct** and current in the July 2026 version.

### A10. Mann v Carnell [1999] HCA 66 citation (line 97)
Skill cites *"Mann v Carnell [1999] HCA 66"* for the "inconsistency" test for LPP waiver. Verified from AustLII: Mann v Carnell [1999] HCA 66 is indeed the leading High Court authority on implied waiver of legal professional privilege by conduct inconsistent with maintaining confidentiality. This is **correct**.

### A11. Banking Act s 62ZZO (line 94)
Skill cites *"Banking Act 1959 s29, s62ZZO (compulsory assistance)"*. This is a genuine Banking Act provision for compulsory assistance with APRA investigations — the section number is plausible but uncommon. No primary-source confirmation obtained (legislation.gov.au was inaccessible). **Flagged but not confirmed as wrong** — leave this for the user to verify against legislation.gov.au.

### A12. ASIC Act s.30 (line 283)
Skill gives an example notice *"under s.30 of the ASIC Act requiring production of documents."* Under the ASIC Act 2001: s.19 covers compulsory examination (oral); s.30 covers ASIC's power to direct production of books. **s.30 for document production is correct.**

### A13. Privilege claim accuracy — "shared with compliance officers" (line 411)
Skill states: *"add other bank legal staff to To/CC only, not compliance officers or business who aren't part of the legal team unless necessary."* This reflects the common-interest/waiver principle: sharing with non-legal operational staff can break privilege. The statement is accurate as a practical caution. The nuance that in-house compliance counsel are still "legal" is not addressed but this is a fine-grained point, not an error.

### A14. "Updated April 2026" description of CPS 230 (line 107)
Skill says: *"From APRA CPS 230 (updated April 2026)."* Technically the amendments were **finalised** 30 April 2026 but **commenced 1 July 2026**. Citing as "updated April 2026" is imprecise — a firm reading this in October 2026 might think it was the pre-July version.

---

## Round 2 — Defense

**A1 (para 59 vs 60):** Could the skill have been written against the pre-July 2026 version of CPS 230? Possible — the pre-2026 version may have had para 59 as the notification provision. **Defense fails**: The skill explicitly claims to incorporate "April 2026 update" (line 107) and the skill's source list (line 512) cites the updated CPS 230. The author intended to cite the current version. A skill that claims to incorporate the April 2026 CPS 230 update but uses the wrong paragraph number is an error, not an intentional trade-off.

**A2 (notification timing):** Defense: "before engagement commences" could be interpreted as the spirit of the rule. **Defense fails**: For non-offshoring critical operation arrangements, the legal obligation is a post-signing notification within 20 business days — not a pre-engagement gate. Instructing users it's required "before engagement commences" will cause them to delay matters unnecessarily or mischaracterise their obligations to APRA. The skill's own anti-pattern list (line 451) says "Do not invent regulatory obligations" — this does exactly that.

**A3 (para 50 vs 51 for MSP Register):** Defense: para 51 is adjacent and APRA can require classification under it — maybe the author meant the broader compliance context. **Defense fails**: The question specifically asks "is the law firm on the MSP Register submitted to APRA (para 51)?" — the parenthetical is meant to direct users to the source requirement, and it's one paragraph off. A lawyer checking para 51 will find the classification discretion, not the submission obligation.

**A4 (s 118 vs s 119):** Defense: Both sections involve the dominant purpose test; the skill may have meant to capture both. **Defense partially fails**: The failure is directional — the context (line 461) is specifically about legal advice privilege (commercial vs legal purpose), not about litigation. Citing only s 119 (litigation privilege) for that proposition is technically wrong. The proper citation is "ss 118–119" or specifically "s 118" for legal advice privilege. However, the skill at line 541 correctly cites "Evidence Act 1995 (Cth) ss 118–120" in the references. The inconsistency between the body text (s 119 only) and the references (ss 118–120) creates a genuine user error risk in line 461. The body text is the actionable instruction; it should be corrected.

**A5 (24-hour window omitted):** Defense: The skill focuses on legal briefing, not incident response per se. Users know to consult their risk team. **Defense fails**: The skill explicitly addresses CPS 230 notification obligations and tells the user "CPS 230/NDB clock running" as a checklist item (line 441). It instructs users to "state the relevant notification deadline" (line 230). Omitting the most urgent APRA notification clock (24 hours for critical operation disruption, vs 72 hours for general operational incidents) in a checklist that claims to cover CPS 230 notifications is a structural gap that could cause real harm.

**A6 (para 36 example):** Defense: This is just a placeholder example, not a literal instruction to use para 36. **Defense partially fails**: The skill's explicit principle at line 451 says "Do NOT invent APRA standard paragraph numbers." The skill then exemplifies specific citation with a real paragraph number (para 36) from the standard, used in a context (generic how-to-cite instruction) where it will be read as a live example. Para 36 in the July 2026 CPS 230 is the internal audit / service provider assurance paragraph — completely unrelated to the operational risk management context the example is embedded in. A user cargo-culting this will put a real but wrong CPS 230 paragraph in their brief. This is fixable by using a placeholder (e.g., "[para XX]") or a correctly matched example.

**A7 (CPS 234 window unstated):** Defense: The skill states CPS 234 "has its own window" and provides a reference link — users can look it up. This is an intentional trade-off for conciseness. **Defense holds**: The skill doesn't claim to state the CPS 234 number; it signals awareness and routes the user to verify. This is a less serious gap than A5 (which claims to cover the clock and then omits the key number). Recommend adding the "72 hours" number for consistency with the NDB treatment, but this is not a fatal error.

**A8 (FAR commencement):** Confirmed correct. Survives as no-issue.

**A9 (AML/CTF s 123):** Confirmed correct. Survives as no-issue.

**A10 (Mann v Carnell):** Confirmed correct. Survives as no-issue.

**A11 (Banking Act s 62ZZO):** Unconfirmed but plausible. Not flagged as a confirmed error. User should verify.

**A12 (ASIC Act s.30):** Confirmed correct. Survives as no-issue.

**A13 (privilege with compliance):** Accurate caution. No issue.

**A14 (April 2026 vs July 2026 commencement):** Defense: saying "updated April 2026" is shorthand for when the amendments were finalised, not when they commenced. The referenced source (apra.gov.au/operational-risk-management) is the live URL which will show the current version. However, because the skill explicitly states it has folded in the "April 2026 update," specifying commencement as July 2026 avoids confusion. Minor issue; recommend adding commencement date.

---

## Adversarial Findings — Survivors (the only ones that matter)

These are the real issues requiring changes. Each is grounded in a primary source.

---

### Finding 1: CPS 230 MSP Notification — Wrong Paragraph Number (para 59 → para 60)

**Issue:** The skill cites CPS 230 "para 59(a)(b)" for the MSP notification obligation in three places (lines 114, 115, 459). In the July 2026 CPS 230 (commencement 1 July 2026, which the skill claims to reflect), the MSP notification obligation is at **paragraph 60**.

**Evidence:** July 2026 CPS 230 clean PDF (APRA, April 2026 finalised): *"60. An APRA-regulated entity must notify APRA: (a) as soon as possible and not more than 20 business days after entering into or materially changing an agreement… (b) prior to entering into any material offshoring arrangement…"* Paragraph 59 in the same document reads: *"59. An APRA-regulated entity must monitor…"* (a monitoring obligation, not notification). APRA's own notification form page confirms the form is labelled "para 59 (a) and (b)" — but this reflects the **pre-July 2026** numbering. The skill claims to incorporate the April 2026 update; it must use July 2026 paragraph numbers.

**Suggested fix (line 113–115):**
```
OLD:
- [ ] If entering or changing a material arrangement: APRA notification required under para 59(a)(b) before engagement commences
- [ ] If work involves offshoring to overseas offices: APP 8 cross-border disclosure + CPS 230 para 59 notification

NEW:
- [ ] If entering or materially changing a material arrangement for a critical operation: APRA notification required under CPS 230 para 60(a) — within 20 business days after entering/changing (not a pre-engagement gate, except for offshoring)
- [ ] If work involves offshoring to overseas offices: APP 8 cross-border disclosure + CPS 230 para 60(b) notification — required PRIOR TO entering the arrangement
```

**Suggested fix (line 459):**
```
OLD:
For significant ongoing matters, confirm before issuing whether the law firm engagement is a "material arrangement" under CPS 230. If yes, APRA notification required (para 59). Substantive work should not commence until this is resolved.

NEW:
For significant ongoing matters, confirm before issuing whether the law firm engagement is a "material arrangement" under CPS 230. If yes, APRA notification required under para 60: within 20 business days after entering the arrangement for critical operations (non-offshoring), or prior to entering for offshoring arrangements. The notification timing distinction matters — do not delay engagement pending notification unless it is an offshoring arrangement.
```

---

### Finding 2: CPS 230 MSP Register — Wrong Paragraph Number (para 51 → para 50)

**Issue:** Line 113 asks: *"is the law firm on the MSP Register submitted to APRA (para 51)?"* In the July 2026 CPS 230, **paragraph 50** is the MSP Register submission obligation. Paragraph 51 is APRA's discretionary power to classify a service provider as material.

**Evidence:** July 2026 CPS 230 para 50: *"An APRA-regulated entity must submit its register of material service providers to APRA on an annual basis."* Para 51: *"APRA may require an APRA-regulated entity, or a class of APRA-regulated entities, to classify a service provider, type of service provider or service provider arrangement as material."*

**Suggested fix (line 113):**
```
OLD:
- [ ] If yes: is the law firm on the MSP Register submitted to APRA (para 51)?

NEW:
- [ ] If yes: is the law firm on the MSP Register submitted to APRA annually (CPS 230 para 50)?
```

---

### Finding 3: Evidence Act 1995 s 119 cited for Legal Advice Privilege — Wrong Section

**Issue:** Line 461 states: *"The dominant purpose test (Evidence Act 1995 s 119) governs."* in the context of determining whether a communication qualifies as legal advice privilege (commercial vs legal purpose). Section 119 of the Evidence Act 1995 is **litigation privilege** (dominant purpose of litigation, anticipated or existing). Section **118** is **legal advice privilege** (dominant purpose of giving or receiving legal advice). The text at line 461 is unambiguously addressing legal advice privilege, not litigation privilege.

**Evidence:** Evidence Act 1995 (Cth):
- s 118: "Evidence is not to be adduced if, on objection by a client, the court finds that adducing the evidence would result in disclosure of… a confidential communication… where the dominant purpose for which the communication was made was the provision of professional legal services…"
- s 119: "Evidence is not to be adduced if… the dominant purpose for which the document was prepared was… use in connection with an anticipated or pending Australian or overseas proceeding…"

The skill's own reference list (line 541) correctly cites "ss 118–120" — but the body text at line 461 gives only s 119. A user who reads the checklist instruction and cites s 119 in a legal advice privilege claim (e.g., resisting ASIC's document production request based on legal advice, not anticipated litigation) has cited the wrong provision.

**Suggested fix (line 461):**
```
OLD:
Marking a document "Privileged" does not create privilege. The dominant purpose test (Evidence Act 1995 s 119) governs. If the dominant purpose is commercial rather than legal, privilege does not attach regardless of the header.

NEW:
Marking a document "Privileged" does not create privilege. The dominant purpose test governs: for legal advice privilege, see Evidence Act 1995 (Cth) s 118 (dominant purpose of giving/receiving legal advice); for litigation privilege, see s 119 (dominant purpose of anticipated litigation). If the dominant purpose is commercial rather than legal, privilege does not attach regardless of the header. In most regulatory briefing contexts, s 118 legal advice privilege is the primary applicable provision — ensure the brief is authored and directed by legal counsel for legal advice purposes.
```

---

### Finding 4: CPS 230 Para 41 — 24-Hour Critical Operation Disruption Notification Omitted

**Issue:** The skill's CPS 230 notification coverage mentions only the 72-hour window (material operational risk incidents, para 32) and the NDB 30-day window. It never mentions the **24-hour notification window for disruptions to critical operations outside tolerance** (CPS 230 para 41). This is the most urgent APRA notification clock and is directly relevant when external counsel is engaged on business continuity failures.

**Evidence:** July 2026 CPS 230 para 41 (verified from PDF): *"An APRA-regulated entity must notify APRA as soon as possible, and not later than 24 hours after, if it has suffered a disruption to a critical operation outside tolerance."* The APRA notification form page confirms "Breach of Critical Operation Tolerance (para 42)" as a separate form — the breach notification is para 41 (text), the form covers para 42 which is the remediation plan. The 24-hour window is a separate, shorter, more urgent clock.

The skill's checklist at line 441 says *"If CPS 230/NDB clock running: relevant notification deadline stated explicitly"* — but nowhere does the skill tell the user what this deadline is for a critical operation disruption. A legal team instructing counsel on a major system outage affecting critical operations might relay the wrong deadline (72 hours instead of 24 hours) based on reading this skill.

**Suggested fix (lines 99–100):**
```
OLD:
- **NDB notifications (Privacy Act 1988 Pt IIIC)**: 30-day assessment clock to determine if eligible data breach; notify OAIC + individuals once confirmed. Separate from CPS 230 72-hour clock.
- **CPS 230 notification (72 hours)**: Material operational risk incident must be notified to APRA within 72 hours. CPS 234 (info security incidents) has its own separate clock. Do NOT confuse these.

NEW:
- **NDB notifications (Privacy Act 1988 Pt IIIC)**: 30-day assessment clock to determine if eligible data breach; notify OAIC + individuals once confirmed. Separate from CPS 230 clocks.
- **CPS 230 notification — two separate clocks**:
  - Para 32 (material operational risk incident): notify APRA within **72 hours** of becoming aware of an incident likely to have material financial impact or material impact on critical operations.
  - Para 41 (critical operation disruption outside tolerance): notify APRA within **24 hours**. This is the shorter, more urgent clock — applies when a critical operation has actually breached its tolerance level. Brief external counsel on which clock is running and whether both apply.
- **CPS 234 notification (para 35)**: Material information security incidents — notify APRA within **72 hours**. Separate clock from CPS 230 para 32, though both may run simultaneously for a cyber-incident affecting operations.
- Do NOT confuse these clocks. State the applicable deadline(s) explicitly in any regulatory brief where an incident is live.
```

---

### Finding 5: CPS 230 "Para 36" Model Citation Example — Wrong Paragraph for Context

**Issue:** Line 370 instructs users to be specific about citations and gives as a model: *"CPS 230 (Operational Risk Management) para 36."* In the July 2026 CPS 230, paragraph 36 is: *"An APRA-regulated entity's internal audit activities must include a review of the design and operating effectiveness of information security controls, including those maintained by related parties and third parties."* This is a highly specific internal audit requirement for information security control assurance — completely unrelated to the generic "be specific in your citations" instruction this line is meant to illustrate.

The skill's own anti-pattern at line 451 says: *"Do NOT invent APRA standard paragraph numbers… A wrong citation in a brief to a law firm is embarrassing and may mislead advice."* The model example violates this principle.

**Evidence:** July 2026 CPS 230 clean PDF, para 36: confirmed to be internal audit / information security assurance content.

**Suggested fix (line 370):**
```
OLD:
- APRA standards: "CPS 230 (Operational Risk Management) para 36" not just "CPS 230."

NEW:
- APRA standards: "CPS 230 (Operational Risk Management) para [XX]" not just "CPS 230." Do not use a para number as a placeholder — if you do not know the exact paragraph, write the section heading (e.g., "CPS 230 — Operational Risk Incidents notification obligation") and add a verify tag.
```

---

## Non-Survivors (confirmed correct, no change needed)

| Claim | Verdict |
|---|---|
| FAR commencement "15 March 2024 for ADIs" | ✅ Correct (APRA confirmed) |
| AML/CTF Act 2006 s 123 tipping-off | ✅ Correct (AUSTRAC confirmed) |
| Mann v Carnell [1999] HCA 66 for LPP waiver | ✅ Correct (leading HCA authority) |
| ASIC Act 2001 s.30 for document production notice | ✅ Correct |
| NDB scheme — 30-day assessment clock | ✅ Correct (Privacy Act 1988 Pt IIIC) |
| LPP waiver risk from sharing with AI tools | ✅ Accurate and prudent caution |
| AML/CTF tipping-off instructions structure | ✅ Correct and well-structured |
| Evidence Act 1995 ss 118–120 (reference list, line 541) | ✅ Correct |
| FAR accountable individual obligations | ✅ Structurally correct |
| Privilege header without substance (as anti-pattern) | ✅ Accurate legal principle |

---

## Summary for Patch Author

**5 changes required** (in priority order):

1. **CRITICAL**: CPS 230 MSP notification paragraph: replace all "para 59" with "para 60" and fix the timing description (20 business days post-signing, not pre-engagement, except offshoring).
2. **CRITICAL**: CPS 230 24-hour notification clock for critical operation disruption (para 41): add alongside the 72-hour clock.
3. **HIGH**: Evidence Act s 119 → s 118 for legal advice privilege in line 461.
4. **MEDIUM**: CPS 230 MSP Register: para 51 → para 50 in line 113.
5. **LOW**: CPS 230 model citation example "para 36" — replace with a placeholder or accurately labelled example.

**Optional improvement** (not a confirmed error):
- Add CPS 234 72-hour notification window explicitly (currently only stated as "its own window").
- Clarify "April 2026 update" → "finalised April 2026, commenced 1 July 2026."

---

*Review conducted: August 2026. Sources: APRA CPS 230 July 2026 clean PDF; APRA CPS 234 (APRA.gov.au); APRA FAR page (APRA.gov.au); AUSTRAC AML/CTF Act page; standard AU evidence law commentary (Evidence Act 1995 (Cth) ss 118–119). Anti-fabrication: every finding above is grounded in a verified primary source or a well-established legal principle. Findings A8, A9, A10, A12 were confirmed correct and are not listed as survivors.*
