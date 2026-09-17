# Skill Document Adversarial Review — Attack Vector Class

> Offloaded from SKILL.md body (size > 600 lines). Load on demand via skill_view. Paper metrics and dated incident notes are not timeless — re-verify before citing as current.

## Skill Document Adversarial Review — Attack Vector Class (Sep 2026)

A skill SKILL.md is neither code nor prose — it is a procedural specification with
terminology, formula gates, worked examples, and cross-references that must all be
mutually consistent. Standard code review and prose review both miss a distinct class
of failure. Apply these additional attack vectors when reviewing a skill document:

**Terminology defined vs. referenced check (HIGH):**
Search for every term used as a gate or condition in the verdict formula or decision
tree. For each term, verify it is DEFINED somewhere in the skill (Glossary, inline, or
in the step where it is set). A term that appears only in usage — never in a definition
— is an unfollowable instruction gate. Common failure: a section gets dropped in a
rewrite; the term survives in downstream references.
Detection: list all formula gate tokens → grep for each in the document → if only
call-sites found (no definition), it's a dangling reference.
Concrete case (Sep 2026): `negative_lexicon` referenced as a constraint in two steps
but the Negative Lexicon section itself was dropped in a prior rewrite. The skill
parsed cleanly (no YAML errors) but the constraint was unenforciable.

**Dual-variable collapse bug (HIGH):**
When two logically distinct predicates (different conditions, set at different steps)
are stored in the same named variable, a step that writes the variable for one purpose
silently overwrites the other. Verdict formulas that read the variable get the LAST
write's value regardless of the earlier condition's outcome.
Correct pattern: give each distinct gate its OWN named variable.
Concrete case (Sep 2026): `structural_match` was set to `true` in Step 2A (at least
one mapping row non-NONE) AND also set to `false` in Step 2B (disanalogy fails). The
two conditions are independent — a paper can have a valid mapping but fail the
disanalogy test. Collapsing both into `structural_match` let a failed disanalogy silently
clear a valid mapping result. Fix: introduced `disanalogy_valid` as a separate gate;
updated the formula to check both independently.

**Worked-example consistency check (HIGH):**
For every worked example in the skill, trace it manually through the current verdict
formula using only the values stated in the example. Verify:
  (a) The formula produces the stated verdict
  (b) All new field names introduced since the example was written appear in the example
  (c) All formula clauses (AND conditions) are addressed — none left implicit
Self-consistency bug: Example A stated `match=true, disanalogy valid` (old terminology)
after `disanalogy_valid` was introduced as a named field. The example passed the old
formula path but did not demonstrate the new gate explicitly — a reader following the
example would not know to set `disanalogy_valid`.

**Feasibility threshold justification (MEDIUM):**
Numeric thresholds in skill gates should be justified, not arbitrary. An exact number
without rationale ("exactly ONE uncertain assumption") is a policy choice masquerading
as a procedure. When tightening or loosening a threshold, state the reasoning.
Concrete case (Sep 2026): `feasibility=1` required "one uncertain assumption" exactly.
Changed to "one OR TWO" after noting that two minor uncertainties should not hard-SKIP
a paper — each with a verification test. The original "one" was never justified.
Fix pattern: add a rationale clause or examples that show the boundary.

**Calibration section authenticity check (CRITICAL for skills with research bases):**
Any arXiv ID or calibration anchor in a skill's Research Basis or Calibration section
that was LLM-generated (not user-supplied) must be verified by fetching the abstract
and confirming title + topic match the stated description. LLM-generated IDs frequently
resolve to REAL papers on entirely DIFFERENT topics — they pass URL validation while
being factually wrong.
Detection: for each ID in the skill, call `web_extract(["https://arxiv.org/abs/<ID>"])`
and verify the title and topic against the skill's description of it.
Concrete case (Sep 2026): four IDs in a research basis section all resolved to real
papers but wrong topics (e.g. "OFTRL aggregation" → "Constant Individual Regret in
General Games"; "memory retrieval ranking" → "Almost Envy-Freeness for Additive Mixed
Manna"). All four passed URL resolution and format checks.
Fix: remove unverified IDs to a "known mismatches" block with warning; keep only
verified-correct IDs as calibration anchors. Fewer honest anchors beat many false ones.

**Disanalogy strength-test completeness (MEDIUM):**
A disanalogy predicate defined at one gate in a skill but used at multiple locations
(formula, manual procedure, examples) must be checked for consistency at ALL locations.
Fixes applied to the formula definition do not automatically propagate to the manual
procedure or worked examples — each location must be updated separately and then
cross-checked. After any disanalogy gate change, grep the whole skill for every
usage of the gate term and verify each one uses the updated definition.

**Step ordering physical vs. logical consistency (LOW):**
If a skill documents an execution order that differs from document reading order (e.g.
"run Steps 0,1,3,2,4,5"), verify the physical order of sections in the document matches
the stated execution order. A reader following the document top-to-bottom should
naturally execute the correct order. Mismatch creates confusion without being a
correctness error — the failure mode is slow execution, not wrong results.
