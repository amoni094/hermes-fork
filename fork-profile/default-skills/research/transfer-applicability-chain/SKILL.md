---
name: transfer-applicability-chain
description: "Use when screening a finding for adoption in any target system — general five-slot chain. Not for Hermes math/CS paper evaluation (use math-cs-applicability-reasoning)."
version: 1.0.0
author: Hermes Agent
license: MIT
trust_level: trusted
related_skills:
  - math-cs-applicability-reasoning
  - adversarial-review
  - academic-literature-review
  - domain-research-synthesis
metadata:
  hermes:
    tags: [research, applicability, transfer, evaluation, relevance, reasoning]
---

# Transfer Applicability Chain

General-purpose structured chain for deciding whether an external finding (paper,
tool, pattern, framework, practice) is worth implementing in a target system.
Domain-agnostic — fill the five slots before running.

The Hermes/math-CS instantiation is math-cs-applicability-reasoning, which pre-fills
all slots for that domain and includes interpreter script integration, calibration
anchors, and worked examples. Use that skill directly for Hermes paper evaluation.

## When to Use

- Evaluating a research paper for adoption in any target system
- Deciding whether a new tool, library, framework, or pattern is worth integrating
- Assessing a design pattern, architecture change, or operational practice for fit
- Triage of a backlog of findings before committing implementation effort
- Any "should we do this?" that needs a structured, adversarially-resistant answer

Do NOT use for:
- Code review of already-decided changes (use adversarial-review)
- Pure literature survey with no implementation intent (use academic-literature-review)
- Hermes/math-CS paper evaluation (use math-cs-applicability-reasoning directly)

## Five Slots — Fill Before Running

Keep these visible throughout the chain. Do not invent entries mid-run.

  TARGET_SYSTEM:     What system? e.g. "Hermes context compressor", "our PG pipeline"

  OBJECT_TAXONOMY:   Closed list of named components findings can map to.
                     e.g. [router, scheduler, cache, summarizer, memory-store]

  FEASIBILITY_GATES: Hard no-go conditions. Any hit = SKIP.
                     e.g. requires GPU, requires training loop, requires
                     service unavailable at runtime.

  KNOWN_METRICS:     Measurable quantities a finding could improve.
                     Must be measurable before/after without human judgment.
                     e.g. [latency-ms, token-count, pass-rate, precision-at-k]

  PARAM_DEFAULTS:    Named tunable parameters + current values.
                     e.g. cache_ttl=3600, lambda=0.2, top_k=5
                     (Needed for Step 1 THEOREM exception and Step 4 check.)

## Step 0 — Neutral Claim

Write the finding's core contribution in ONE sentence using NO TARGET_SYSTEM
vocabulary. This prevents vocabulary anchoring (FM-1).

  Bad:  "Paper introduces a relevance scorer for Phase-1 pruning."
  Good: "Scoring items by information density before discarding reduces
         information loss compared to positional ordering."

Can't write a neutral claim? The finding is too vague to evaluate — SKIP.

## Step 1 — Abstraction Level Filter

Classify the finding. Most fail here.

  THEOREM:    Provable bound. Applicable ONLY if it directly tightens a named
              PARAM_DEFAULT with a specific numeric value or inequality.
              No PARAM_DEFAULT tightened -> SKIP immediately.

  ALGORITHM:  Pseudocode-runnable. SPIKE candidate if it maps onto OBJECT_TAXONOMY
              AND passes feasibility gates.

  HEURISTIC:  Design principle. SPIKE candidate if it directly informs a specific
              decision path in TARGET_SYSTEM.

  FRAMEWORK:  Conceptual. SKIP unless it resolves a live design ambiguity with a
              concrete, testable change. "Conceptual alignment" is not evidence.

  EMPIRICAL:  Benchmark result. OPTIMIZATION candidate if TARGET_SYSTEM has the
              same tunable PARAM_DEFAULT measured by the benchmark.

## Step 3 — Feasibility Gate (run BEFORE Step 2)

Check FEASIBILITY_GATES. Any box = SKIP.

  [ ] Requires resources/infrastructure not available at runtime
  [ ] Requires training or optimization loop (if inference-only system)
  [ ] Core assumption violated by TARGET_SYSTEM's operating constraints
  [ ] >200 LOC new code for marginal gain
  [ ] Requires external data/labels unavailable at runtime
  [ ] [add domain-specific gates]

Gates are hard stops. Partial applicability does not earn a pass.

## Step 2 — Structural Analogy (run AFTER Step 3 clears)

Map the finding's objects and operations onto OBJECT_TAXONOMY.

  - Use ONLY entries in OBJECT_TAXONOMY. Do not invent.
  - Name at least ONE load-bearing assumption that FAILS in TARGET_SYSTEM
    (the disanalogy). Surface differences don't count.
  - No OBJECT_TAXONOMY component maps -> SKIP.

  Weak: "finding uses matrices; system uses Python dicts"
  Strong: "finding assumes i.i.d. samples; our system's turns have sequential
    dependency — earlier turns constrain valid later turns, invalidating the
    independence assumption in the regret bound."

## Step 4 — Measurability

Name ONE metric from KNOWN_METRICS that would change if this finding is implemented.
Must be measurable without human judgment.
No such metric -> downgrade verdict one level (SPIKE->OPTIMIZATION, OPTIMIZATION->SKIP).

## Step 5 — Scores and Verdict

  Desirability (D, 0-2):
    2 = materially improves a high-frequency path if it works
    1 = improves a low-frequency path or marginal improvement on high-frequency
    0 = no clear value

  Feasibility (F, 0-2):
    2 = fits existing interfaces, <100 LOC, testable
    1 = some new structure, 100-200 LOC, testable
    0 = new infra required or untestable

  Verdict (deterministic — model opinion does not override):
    D=2, F>=1 -> SPIKE
    D=2, F=0  -> OPTIMIZATION
    D=1, F=2  -> OPTIMIZATION
    D=1, F<=1 -> SKIP
    D=0       -> SKIP

## Step 6 — Asymmetric Critic (SPIKE and OPTIMIZATION only)

  Author view:     "Would the authors claim this applies to TARGET_SYSTEM?"
  Maintainer view: "What is the single strongest reason NOT to implement this?"

New disanalogy found -> re-evaluate from Step 2.
New feasibility failure -> SKIP.

## Step 7 — Implementation Check (SPIKE only)

All four must pass, else downgrade to OPTIMIZATION:
  [ ] Specific file/function/config key in TARGET_SYSTEM to modify
  [ ] Change testable by a named KNOWN_METRIC
  [ ] No load-bearing assumption violated in TARGET_SYSTEM
  [ ] Disanalogy from Step 2 does not break the core mechanism

## Common Failure Modes

  FM-1 VOCABULARY ANCHOR: TARGET_SYSTEM words inflating apparent relevance.
       Catch: re-run Step 0 without that vocabulary.

  FM-2 FRAMEWORK INFLATION: Conceptual framework mistaken for an algorithm.
       Catch: Step 1 FRAMEWORK -> SKIP unless a concrete testable change is named.

  FM-3 PARTIAL MAP: Peripheral detail mapped, not the core mechanism.
       Catch: Step 2 requires the CORE mechanism maps.

  FM-4 FEASIBILITY OPTIMISM: "We could build that infrastructure."
       Catch: Gates apply to what exists NOW.

  FM-5 METRIC INFLATION: Benefit claimed that can't be measured.
       Catch: Step 4 requires a named KNOWN_METRIC.

  FM-6 DISANALOGY DISMISSAL: "The disanalogy is minor."
       Catch: Any load-bearing assumption disanalogy is never minor.

  FM-7 STEP-ORDER VIOLATION: Step 2 run before Step 3.
       Catch: Always feasibility-gate before structural analogy. Doing Step 2
       first anchors you to a mapping before checking runnability.

## Domain Instantiations

  Hermes/math-CS papers:
    Use math-cs-applicability-reasoning directly. Pre-fills:
      OBJECT_TAXONOMY = Hermes COMPONENT_MAP (closed, ~20 components)
      FEASIBILITY_GATES = no-GPU, no-training-loop, no-new-infra >200 LOC
      KNOWN_METRICS = compaction ratio, tool SLO pass rate, memory decay score
      PARAM_DEFAULTS = lambda=0.2, rdm_lambda=0.05, threshold_tokens=120000, ...
    Also: interpreter scripts, calibration anchors, worked examples.

  Other domains:
    Define your five slots at session start, run this skill as written.
    If the domain recurs across sessions, save a thin wrapper skill that
    fills the slots and calls this chain. See math-cs-applicability-reasoning
    as the reference example of a properly instantiated wrapper.

## Quick-Run Checklist

  Before first finding:
    [ ] TARGET_SYSTEM defined
    [ ] OBJECT_TAXONOMY listed (closed, finite)
    [ ] FEASIBILITY_GATES listed
    [ ] KNOWN_METRICS listed
    [ ] PARAM_DEFAULTS listed (if THEOREMs in scope)

  Per finding:
    [ ] Step 0: neutral claim (no TARGET_SYSTEM vocab)
    [ ] Step 1: abstraction level classified
    [ ] Step 3: feasibility checked (before Step 2)
    [ ] Step 2: analogy + disanalogy named using only OBJECT_TAXONOMY
    [ ] Step 4: metric named from KNOWN_METRICS (or verdict downgraded)
    [ ] Step 5: D/F scored, formula applied
    [ ] Step 6 (SPIKE/OPT): asymmetric critic run
    [ ] Step 7 (SPIKE only): all four implementation checks passed
