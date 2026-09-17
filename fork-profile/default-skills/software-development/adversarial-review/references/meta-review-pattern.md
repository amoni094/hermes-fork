## Meta-review pattern: auditing a critique/review document itself

When the artifact under review is *another review* (a critique doc, design review,
PR review write-up) rather than code or a spec, run the check across four named axes
instead of ad-hoc reading:

- **Strength** — is each finding backed by evidence/reasoning from the source
  material, or is it an assertion? Flag findings that read as opinion dressed as a
  defect.
- **Relevance** — does each finding actually engage with what the source document
  says, or does it critique a strawman / something the source never claimed? Requires
  having the source's own ground truth reconstructed (see
  `visual-document-review`'s one-at-a-time transcription mode when the source only
  exists as screenshots) — you cannot check relevance against a document you haven't
  actually read in full.
- **Cohesion** — do the review's own cross-references (§N / §N.M tokens, "responds to
  §X" citations) resolve to headings that actually exist in the review, and does the
  review avoid contradicting itself across sections (e.g., a section citing the same
  severity rating differently in two places)?
- **Nuance** — does the review present a balanced picture, or does it read as
  one-sided/alarmist? This axis catches a specific failure mode: **if the user asked
  for all "the proposal gets this right" praise to be stripped from an earlier draft,
  re-check whether the *remaining* document still reads as balanced once the praise is
  gone.** A review that used to interleave strengths and weaknesses can end up, after
  stripping, reading as 100% critique with zero acknowledgment that anything works —
  which is a legitimate nuance/tone finding even though the user's stripping request
  was correctly honored. Removing praise on request and having a balanced-sounding
  document are two different constraints; satisfying the first doesn't guarantee the
  second, and it's worth flagging (not silently re-adding praise) so the user can
  decide.

Report findings from this pattern the same way as any adversarial pass: severity-rated,
with the specific paragraph/section location, not just "the tone feels off."

**Severity-vocabulary discipline for critique deliverables.** Declare a *fixed* severity
key (e.g. exactly HIGH / MEDIUM / LOW, each defined once) at the top of the findings
table, and hold every row to it. Compound labels that leak in during drafting —
`MED-HIGH`, `LOW-MED`, `MED` alongside `MEDIUM` — are themselves a **cohesion defect**:
they don't map to the declared key and read as an undeclared fourth/fifth level. If you
genuinely need to signal that a finding sits at the top or bottom edge of its bucket, use
a parenthetical edge-annotation (`MEDIUM (upper)`, `LOW (upper)`) and *say so in the key*
that the parenthetical does not create a new level — do not invent a hyphenated label.
When you normalise these labels, apply the whole-artifact grep rule from the loop
discipline above: the same label appears in the table AND in every narrative section
header that references that finding.
