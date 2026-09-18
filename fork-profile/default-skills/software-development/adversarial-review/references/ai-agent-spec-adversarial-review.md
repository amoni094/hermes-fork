# Worked pattern: adversarial review of an AI/agent system design spec

Applies when the artifact under review is a *design spec for an AI agent or AI-assisted
system* (evaluation methodology, autonomy/governance framework, agent rollout plan) rather
than code or a paper. Same recursive severity-tagged loop as the main skill, but the
attack-vector checklist and the fix-pass discipline are domain-specific.

## Attack-vector checklist for agent/system design specs

Check each of these explicitly — specs in this domain systematically omit them:

1. **Undefined risk taxonomy** — does the spec name a "critical"/"high-risk" category
   without ever enumerating what falls into it? If findings can't be mapped to a named
   category, the spec is untestable no matter how much process surrounds it.
2. **No named accountable human** — roles like "Risk Owner" or "Reviewer" without a named,
   currently-qualified individual on the hook for client/user-facing output. For regulated
   domains (legal, medical, financial) check the relevant professional-supervision guidance
   (e.g. Law Society / ABA generative-AI guidance for legal work) — a role placeholder is not
   the same as an accountable practitioner.
3. **No confidentiality/data-governance line** — no-training-on-user-data commitment,
   retention/deletion, residency, least-privilege access to any eval/reference dataset.
4. **No adversarial-input / prompt-injection defense** — if the agent ingests
   externally-sourced content (documents, emails, web pages, deeds, contracts), that content
   is an untrusted input channel (OWASP LLM01). A spec that only tests "hard legitimate
   cases" and never "content engineered to manipulate the agent" has a live security gap,
   not just a quality gap.
5. **No model/version change control** — silent vendor-side model swaps are a known failure
   mode. Check whether a model version change is required to trigger full regression +
   sign-off before promotion, the same as a code change would.
6. **Thresholds referenced but never given a column** — "metrics and tolerances are
   defined" is not itself a definition. If there's no field to hold an actual number and an
   owner to set it, the spec cannot be checked against reality. This is the most common gap:
   process described in prose, unimplementable because no schema exists for the numbers.
7. **No dataset representativeness / minimum-sample-size requirement** — before any
   confidence/autonomy claim is trusted, check for class-stratified coverage against the risk
   taxonomy, explicit negative/adversarial examples, and a minimum-N before promotion
   decisions are made on that class. Promoting on a handful of observations is noise.
8. **Pillars/sections drafted independently** — cross-check that a taxonomy or classification
   scheme introduced in one section is reused (not reinvented) in every other section that
   needs it (e.g. the same deed/case-class taxonomy used for both dataset stratification and
   autonomy gating).

Grounding sources worth pulling per pass: NIST AI RMF (govern/map/measure/manage), the
"earned autonomy" / progressive-supervision literature (staged autonomy levels, promotion
protocol requiring minimum sample size + sustained window, human-override-rate as an early
warning signal, rollback/circuit-breaker), OWASP LLM Top 10 for injection risk, and the
relevant professional-body AI-supervision guidance for the domain in question.

## Critical fix-pass discipline: don't fabricate judgment-call values

When the fix for a HIGH/MEDIUM finding is "add a numeric threshold" or "pick a structural
label," distinguish two kinds of fix:

- **Structural fix (do it yourself):** add the missing mechanism — a Target Metric column,
  an Accountable Owner field, a named control, a taxonomy. This is fully within scope for an
  adversarial review pass.
- **Judgment-call value (flag, don't invent):** the actual number (recall floor, override-rate
  ceiling, minimum sample size, MTTR target) or an organizational naming/structure decision
  (e.g. "is this a 5th pillar or a cross-cutting layer folded into the existing 4?") requires
  domain risk appetite or stakeholder ownership that the reviewing agent doesn't have standing
  to set. Add the column/mechanism, leave the value visibly open, and call it out explicitly
  in a Notes/Open-Items section rather than silently picking a plausible-looking number.

Silently inventing "reasonable" thresholds is worse than leaving them blank — a fabricated
90%/3%/500-operations set of numbers looks authoritative and will get rubber-stamped by a
reader who assumes the review did the risk-appetite work. Explicitly flagging "mechanism now
exists, value is owner's call" keeps the review honest and forces the real decision to
actually happen.

## Additional attack vectors for Hermes agent capability improvement specs

When reviewing skills, scripts, and config additions from an arXiv research sweep,
check these systematically — they are the recurring failure modes for this class:

1. **YAML duplicate top-level key** — appending a second `compression:` (or any top-level
   key) silently overwrites the first. PyYAML's `safe_load` keeps the last occurrence only.
   Check: `grep -n '^keyname:' config.yaml` must return exactly one hit. Verify the
   production block values survive with a direct attribute assertion after load.

2. **Config-as-documentation creating false enforcement signals** — `enabled: true` inside
   a purely documentary block implies runtime enforcement when no code reads that key.
   Check: every top-level config key must map to a parser in the Hermes runtime, or be
   renamed clearly (e.g. `reasoning_research:`) and stripped of `enabled:` switches.

3. **Paper metric attribution transferred out of class** — benchmark gains measured on
   a specific model+dataset (e.g. Gemini-Flash on LOCA-Bench, N=10 7B agents, Qwen-8B)
   are cited as if they apply to a Claude Sonnet prompt-only harness. Check: every numeric
   claim must include `(paper: [model]/[dataset]; not reproduced here)`. Gains from
   fine-tuned or latent-space methods are not transferable to prompt-only implementations.

4. **False paper attribution for thresholds** — thresholds documented as "from paper X"
   when the paper used a learned classifier (LightGBM, SVM) not a lexical heuristic.
   Check: any threshold labeled "from paper" must be traceable to a specific experiment
   in that paper using the same method. Lexical proxies are "uncalibrated; not from paper".

5. **Script CLI shape assumed in tests** — verification tests written against assumed
   argument names fail when the real argparser differs. This produces false PASS results
   that mask real failures. Check: run `python3 script.py subcmd --help` for every
   subcommand before writing functional test cases. Build tests from help output, not
   from code assumptions.

6. **Loop threshold inconsistency across files** — skill says 3x, config says 2x, script
   implements 2x. Any safety threshold that appears in multiple files must be a single
   constant. Check: grep all files for the threshold value and confirm they agree.

7. **Unimplemented tools advertised as available** — skill or config describes
   `recall_by_id`, `seek_transcript`, `offload_span` or similar tools as if they exist
   and can be called. Check: every tool named in a skill must exist as a registered
   Hermes tool or a real Python function in a loaded script. Mark non-existent tools
   `NOT_IMPLEMENTED — future work`.

9. **Cross-cycle rule conflicts — trajectory confidence vs abort policy** — new techniques
   added in later cycles commonly conflict with existing rules without cross-referencing them.
   The specific recurring pattern: a trajectory-confidence gate that triggers abstention or abort
   contradicts a standing "no mid-trajectory abort" invariant. Check: any new gate that produces
   an abort/abstain outcome must be checked against ALL existing abort rules; either scoped away
   from the existing rule ("replan, not abort") or explicitly superseding it with a rationale.

10. **Freshness class collapse in extended sessions** — a new technique that introduces its own
    half-life table overrides the existing Cycle 1 half-life table silently. Check: grep ALL
    sections for half-life values and verify they agree. A freshness class that narrows from 7d
    to 24h without explicit reconciliation is a correctness bug.

11. **Inverted direction on optimism-bias corrections** — when documenting a self-modeling
    overclaim correction, "lower bound" and "upper bound" are easily inverted. Models
    OVERCLAIM, so verbal self-prediction is an OPTIMISTIC UPPER BOUND (not a lower bound).
    The correction is a downward subtraction. Check any text near "lower bound"/"upper bound"
    in self-modeling or calibration sections.

12. **Verify-gated fail-closed trapping agents in infinite loops** — "non-empty open_questions
    → not complete" triggers perpetual incompleteness when open questions are annotated
    uncertainties (not missing constraint evidence). Fail-closed must be scoped to: stated
    constraint has no tool-grounded evidence. Unresolvable unknowns must be flagged and
    delivered under the existing max-revision-cycle cap.

13. **Confidence signal confusion across sections** — when a skill grows across multiple
    research cycles, different sections introduce different confidence signals (FOK, JOL,
    trajectory_confidence, U/IU/EU, source_reliability, freshness, pre-call score) without a
    routing table. Check: each signal must map to exactly one decision class. Add an explicit
    "which score for which decision" routing table at the top of any multi-cycle skill block.

8. **L0/L1 task exemptions missing from safety gates** — confidence gates, tool-forcing
   rules, and retry policies designed for L2/L3 tasks erroneously apply to L0/L1 where
   they suppress correct short answers. Check: every gate must have an explicit
   complexity-level exemption for L0/L1 tasks.

## Deliverable shape when the artifact is a spreadsheet

When the reviewed artifact is itself a spreadsheet/methodology doc (not code), the most
useful revision deliverable is a multi-sheet workbook (built with openpyxl), not just prose:

- **Read Me** — one-paragraph orientation + a table of what's in each other sheet.
- **Critique Log** — every finding: # / severity / area / issue / fix applied / status.
  Severity-tag with fill color (High/Medium/Low) for scannability.
- **[Methodology] v2** — the actual corrected spec, one row per control, with two columns
  added to *every* row regardless of whether the original had them: Target Metric/Threshold
  and Accountable Owner. Highlight new-in-this-pass rows distinctly (e.g. green fill) so the
  diff against the original is visually obvious without a redline tool.
- **Notes** — the judgment-call items deliberately not resolved (see discipline above), plus
  any LOW-severity cleanup left open.

This structure makes the review's own rigor auditable: a reader can trace every High/Medium
finding to a specific fixed row, and can immediately spot which values still need a human
risk-appetite decision instead of being invented.
