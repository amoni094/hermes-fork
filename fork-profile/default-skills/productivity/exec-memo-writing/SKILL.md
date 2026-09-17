---
name: exec-memo-writing
triggers:
  - User wants to write an executive memo, briefing note, or C-suite brief
  - User has a recommendation, update, or decision request for senior leadership
  - User asks to turn notes/analysis into a concise executive document
  - User needs a 1–2 page brief for a board, CEO, or executive team
description: "Use when writing exec memos or briefings (2-page max)."
version: 1.1.0
license: MIT
platforms: [linux, macos, windows]
metadata:
  tags: [memo, executive, briefing, writing, communication, C-suite, BLUF, Minto, plain-language]
related_skills:
  - docx
  - pdf
  - document-layout-design
  - grounded-citations
---

# Executive Memo Writing

Research basis: `research/exec-memo-writing.md` in hermes-config repo (amoni094/hermes-config).

## When to use
- Any document destined for C-suite, board, or senior leadership.
- Decisions that need sign-off, resources, or action.
- Status updates or risk flags requiring executive awareness.
- Any brief where "read and act in under 3 minutes" is the constraint.

## Core principles (non-negotiable)

1. **Two pages maximum.** If it doesn't fit in two pages, the thinking isn't done yet. Cut, don't append. Physical target: ~800–1,000 words for A4/Letter at standard margins (11–12pt body, 1-inch margins). Appendices are unlimited but must not contain decision-critical content.
2. **Lead with the ask or finding — always.** Executives scan; they anchor on the first strong claim. If the recommendation is buried, the memo fails.
3. **Every claim that can be quantified, must be.** "$4M revenue risk in H2" beats "significant financial exposure."
4. **Active voice, short sentences.** Target 15–20 words average. Cut nominalizations (utilization→use; implementation→rollout; consideration→review).
5. **Decision-forcing close.** End with a named choice or action — never leave the reader deciding whether to decide.

---

## When NOT to write a memo

A memo is the wrong tool when:
- The decision needs to happen in the next hour — call or meet instead; a memo will delay.
- The audience already knows 90% of the context and just needs a verbal check-in.
- The topic requires real-time dialogue, negotiation, or emotional calibration.
- It's a routine operational update that belongs in a dashboard or ticket system.

If any of these apply, note the constraint to the user and suggest the right channel.

## Clarify before drafting

Ask (yourself or the user) before writing:
- What decision or action is needed, and by when?
- Who is the reader — what do they already know, what register do they expect?
- What is the cultural/linguistic context? (see multilingual section)
- Is this a recommendation memo, situational update, options memo, or FYI?

If you can't answer these, ask before drafting.

For AI-generated memos: also ask — what is the relationship between the writer and the reader (direct report to CEO, peer-to-peer, external to board)? AI drafts tend to be transactionally correct but relationally flat. Without this context, the tone may be technically accurate but inappropriate for the relationship.

---

## Structure — Default (BLUF + Minto hybrid)

Use for most internal corporate memos in English-speaking contexts where recommendation-first is expected.

```
MEMO

TO:     [Name, Title]
FROM:   [Name, Title]
DATE:   [Date]
RE:     [Specific subject — one action-oriented line. Not a topic label: "Vendor X Contract Decision Required by 15 Sep" not "Vendor X Update."]
CC:     [If needed]

─────────────────────────────────────────────
SUMMARY / BLUF
─────────────────────────────────────────────
One paragraph, 3–5 sentences. Contains:
  - The single most important thing the reader must know or do.
  - The decision/action required and deadline if applicable.
  - The headline number or risk.

Example:
"Recommend we terminate Vendor X and transition to Vendor Y by 30 September.
Annual saving: $1.2M. Contract expires 31 October; 30-day notice required.
Approval needed by [date]."

─────────────────────────────────────────────
SITUATION / CONTEXT   (~¼ page)
─────────────────────────────────────────────
What is happening. 2–3 short paragraphs.
State the problem, trigger, or opportunity.
Include only context the reader does NOT already know.
Cite data source inline: "(Q2 Finance Report)" — no footnotes.

─────────────────────────────────────────────
ANALYSIS / KEY FINDINGS   (~½ page)
─────────────────────────────────────────────
Minto pyramid: 2–3 grouped arguments supporting the recommendation.
Each group = bold lead sentence + 2–3 supporting sentences.
MECE: mutually exclusive, collectively exhaustive — no overlap, no gaps.
Example: three arguments = "Cost savings justify the switch" + "Vendor Y's reliability record is stronger" + "Transition risk is manageable." Each stands alone; together they cover the decision space.
Bullets only for truly parallel items (≤5); otherwise prose.

SCQ option: if the memo was triggered by a discrete event (cost spike, new regulation, competitive move), use Situation → Complication → Question → Answer instead of pure deductive pyramid. More natural narrative arc; less mechanical than MECE groupings for event-triggered memos.

Uncertainty: if genuine, use scenario framing:
  Base case: [X] | Downside: [Y] | Upside: [Z]

─────────────────────────────────────────────
RECOMMENDATION / DECISION REQUEST   (~¼ page)
─────────────────────────────────────────────
Restate recommendation clearly. Name the decision.
Forced choice where possible:
  [ ] Option A: ...
  [ ] Option B: ...
  [ ] Approve as proposed
  [ ] Direct us to a different path: ___

Note: always include an escape valve. Offering only closed options to a senior executive who disagrees reads as limiting and may produce passive non-response instead of a redirect.

Immediate next steps: owner + date, max 3–4 lines.

─────────────────────────────────────────────
APPENDIX (optional — does not count toward 2 pages)
─────────────────────────────────────────────
Supporting data, methodology, detailed financials.
Referenced from body; not required for the decision.
```

---

## Structure variants by context

### Variant A: Crisis / Operational SitRep (SBAR)
Use when: incident, outage, regulatory breach, safety event, fast-moving situation, or healthcare-adjacent context.
Scope note: SBAR has limited diffusion into general business writing — use it only for genuine crisis/risk/safety contexts. For standard strategy or operational memos, use the default hybrid above.

```
SITUATION:      What is happening right now. One paragraph.
BACKGROUND:     Why it matters / how we got here. One paragraph.
ASSESSMENT:     Risk level, impact, trajectory. One paragraph.
RECOMMENDATION: What to do. Specific, timed, owned. 3–5 bullet lines.
```

### Variant B: FYI / Awareness Memo (no decision required)
Use when: updating stakeholders, no action required.
Structure: Context → Findings → Implications → Contact for questions.
Still keep BLUF: first sentence states what changed and why it matters.
Do NOT use this structure when you actually need a decision — it invites passivity.

### Variant C: Inductive / Context-first
Use when: East Asian, Southern European, or public-sector audiences where recommendation-first is culturally abrupt.
Structure: Situation → Background → Analysis → (softly framed) Recommendation.
Lead paragraph: shared context, not the ask.
Recommendation: "Based on this analysis, the team believes X is the strongest path" — not "Recommend X."

### Variant D: Sensitive / Political Topic (board conflict, regulatory failure, executive conduct)
Use when: the subject is politically charged and recommendation-first may close minds before the reader has accepted the framing.

Structure: Situation (neutral, factual) → Background (shared context, no loaded language) → Analysis (objective, evidence-only) → Softly framed recommendation or options.
Do NOT use the word "problem" — use "situation" or "challenge." Avoid assigning blame in the body; if accountability matters, name it in a separate section after the analysis.
Tone: measured, not alarmed. "This warrants attention" not "This is a crisis." Let the evidence carry the weight.
Close: offer options or invite direction rather than advocating strongly — preserves the reader's agency.

### Variant E: Options Memo (no single recommendation)
Use when: genuinely uncertain, or the political decision is above the writer's level.
Structure: Issue → Context → Option A (pros/cons) → Option B (pros/cons) → Option C (pros/cons) → Framing question.
Close: "Which direction would you like us to pursue? We can move immediately upon your guidance."

### Variant F: Product / Innovation Go-No-Go (PR/FAQ)
Use when: the memo's purpose is a go/no-go decision on a new product, feature, or initiative (Amazon-derived).
Structure:
  1. Press release paragraph (≤150 words): written as if the initiative succeeded — customer benefit, outcome, headline metric.
     Example opening: "Today [Company] launches [X], reducing customer onboarding time from 14 days to 2, saving $1.2M annually."
  2. FAQs (5–8 Q&A pairs): anticipated stakeholder questions, answered honestly — including hard ones (cost, risk, alternatives).
Key rule: write the FAQs first; the press release paragraph emerges from what the FAQs reveal. The press release IS the BLUF.
Page limit: up to 3 pages (FAQ structure inherently expands; this is expected and acceptable).
Do not use for operational, financial, or policy memos — purpose-built for product/initiative decisions only.

---

## Writing style rules

### Sentences
- 15–20 word average. Shorter for emphasis; longer only for nuance.
- One idea per sentence. Never compound two claims with "and."
- Active voice: "The board approved X" not "X was approved by the board."
- Passive only when: actor unknown, irrelevant, or politically awkward to name.

### Word choice
- Cut nominalizations: utilization→use, implementation→rollout, consideration→review, facilitation→help.
- Note: nominal style (noun-heavy writing, even grammatically active) reduces both readability AND reader interest. An executive bored by the writing will discount the content. Cut zombie nouns not just for clarity but for persuasion.
- Cut hedges: "might perhaps be worth considering" → "recommend."
- Cut filler: "In order to"→"To"; "Due to the fact that"→"Because"; "At this point in time"→"Now."
- Concrete over abstract: name the thing, not the category.

### Numbers
- Quantify everything quantifiable. Round to 3 significant figures ($4.2M not $4,187,423).
- Consistent units throughout (all $M or all $K, never mixed).
- Lead with the number: "$4.2M risk (Q2 Finance)" not "based on Q2 Finance, there is a $4.2M risk."

### Paragraphs
- First sentence = the paragraph's most important claim (inverted pyramid at paragraph level).
- Max 4–5 sentences, max 6 lines visually.
- One topic per paragraph — if covering two topics, split.

### Headers
- Navigation, not decoration. Headers scanned alone should convey the memo's logic.
- Verb-led headers are stronger: "Revenue risk exceeds threshold" > "Revenue Risk."
- Max 4 headers in a 2-page memo.

### Bold and emphasis
- Bold the decision, key number, and deadline. "Bold scan" in 10 seconds should convey the memo.
- Use sparingly — if everything is bold, nothing is.
- No italics for emphasis; use word order and sentence structure instead.

### AI-era front-loading rule
Executives increasingly receive AI pre-summaries of documents. The first 50 words of your memo will likely become the AI summary. Write as if those 50 words ARE the memo — if they don't capture the essence, rewrite the opening.

---

## Quality checklist (run before sending)

**Structure:**
- [ ] BLUF in first paragraph — clear ask, key number, deadline
- [ ] Fits in two pages (no exceptions without explicit sign-off)
- [ ] Ends with a named decision or forced choice
- [ ] Appendix used for detail, not padding the main body

**Writing:**
- [ ] Average sentence ≤20 words
- [ ] No unchecked nominalizations (utilization, implementation, consideration, facilitation)
- [ ] Active voice dominant (<20% passive)
- [ ] Every claim quantified or sourced inline
- [ ] No weasel hedges ("might," "could potentially," "somewhat")

**Formatting:**
- [ ] Bold on decision, key number, deadline
- [ ] Bullets only for truly parallel items (≤5)
- [ ] Paragraphs ≤5 sentences, ≤6 lines
- [ ] White space between paragraphs — no dense blocks

**AI-generation specific checks:**
- [ ] No generic filler: "It is important to note that..." / "In conclusion..." / "Furthermore..." — cut all of these
- [ ] Every number is specific to THIS situation (not a generic example left in)
- [ ] Passive voice frequency: count passive sentences; if >20%, rewrite the worst offenders
- [ ] Word count ≤1,000 words (proxy for 2 pages at standard formatting)
- [ ] RE: line contains an action verb or decision stake — not a topic label
- [ ] Does the opening sentence arrest a scanner? (Concrete or counter-intuitive hook)
- [ ] Is the key number concrete and memorable?
- [ ] Is the recommendation phrased confidently, not hedged?
- [ ] Relational tone check (AI gap): is the tone appropriate to the specific relationship — not just technically correct? For board/sensitive/political memos, does the memo acknowledge the relationship context before the ask?

---

## Multilingual delivery

| Language | Structure | Tone | Key adjustments |
|---|---|---|---|
| English (AU/UK/US) | BLUF-first | Direct, professional | Default — use hybrid above |
| French | Context → conclusion | Formal, nuanced | Formal salutation; soften recommendation; vous form |
| German | Full context → conclusion | Formal, precise | Expand Situation; conclusions after evidence; Sie form |
| Japanese/Korean | Inductive (Variant C) | Deferential | Never lead with recommendation; "the team believes" framing |
| Chinese (Mandarin) | Inductive or parallel | Formal, collective | Collective framing: "We propose" not "I recommend" |
| Spanish (LatAm) | Relationship context first | Warm-professional | Brief relational opening before business |
| Arabic | Formal greeting, then context | Deferential to seniority | Formal honorifics; context before action |

---

## Workflow

1. Clarify before drafting (see questions above).
2. Write the BLUF paragraph first. If you can't write it, you don't know what the memo is for.
3. Outline 2–3 supporting arguments. Are they MECE?
4. Draft body following chosen structure variant.
5. Cut to 2 pages — cut from the bottom up.
6. Run quality checklist.
7. Read aloud — if you stumble, the sentence is too long.
8. Bold-scan test — read only bolded text. Does it tell the story?
9. Deliver in the appropriate channel/format: use `docx` or `pdf` skill for formal document output; for email, use the memo header as the email body (RE: line = subject); for async platforms (Slack, Teams), bold the BLUF and attach the full memo as a file.
10. For AI-generated memos: skip the "read aloud" step; instead run a word-count check (≤1,000 words) and a passive-voice frequency check (flag if >20% of sentences are passive).

---

## Pitfalls

- **Burying the lede**: Starting with background before recommendation. Executives stop reading before they reach it.
- **Bullet overload**: Using bullets to avoid writing real sentences. Bullets hide reasoning gaps; prose forces coherence.
- **Vague quantification**: "Significant risk" without a number. Makes the memo unactionable.
- **Missing the ask**: Ending without a clear decision request. The executive reads it, nods, and does nothing.
- **Two-page trap on the wrong two pages**: Two pages of context with recommendation crammed at the end. Invert.
- **False precision**: "$4,187,423 at risk" in a strategic memo signals the writer is too close to the spreadsheet.
- **Passive + hedging combo**: "It is believed there may be some risk..." — damages credibility.
- **Wrong variant for cultural context**: Minto-pyramid for a Japanese board reads as arrogant.
- **Ignoring AI pre-summarisation**: Weak opening → AI summary misleads the executive before they open the document.
- **Appendix creep**: Putting decision-critical content in the appendix. If they need it to decide, it goes in the body.
