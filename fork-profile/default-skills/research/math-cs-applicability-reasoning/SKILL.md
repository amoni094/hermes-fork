---
name: math-cs-applicability-reasoning
description: "Use when evaluating math/CS papers for Hermes with the 7-step chain. Not for non-Hermes or non-math/CS domains (use transfer-applicability-chain)."
# General version (any domain): transfer-applicability-chain
tags: [math, cs, research, applicability, reasoning, interpreter]
related_skills:
  - transfer-applicability-chain
  - hermes-math-research
  - hermes-cs-research
  - hermes-research
  - hermes-math-sweep-findings
  - hermes-cs-sweep-findings
  - spike
  - adversarial-review
  - trajectory-research-synthesis-to-skills
---

# Math/CS Paper Applicability Reasoning Framework

Hermes-specific instantiation of transfer-applicability-chain. Pre-fills all five slots
(COMPONENT_MAP, feasibility gates, known metrics, param defaults) for Hermes paper evaluation.
For non-Hermes or non-math/CS domains, use transfer-applicability-chain directly.

Evaluates whether a math or CS paper's contribution is applicable to Hermes architecture,
runtime, memory, skills, or config.

Callers:
  math-paper-interpreter.py: runs Steps 0–5 + _deterministic_verdict() automatically.
    Step 6 (asymmetric critic) is NOT automated in the script — manual step only.
    The script does NOT run the full 7-step chain; it runs a 6-step automated path.
    Text input: TITLE + ABSTRACT by default. Use --full-text for ar5iv HTML + PDF fallback.
    Abstract-only runs do NOT emit DEFER — the script runs Steps 0-5 on whatever it has.
    The skill's 'DEFER if abstract-only' rule applies to MANUAL use only, not the script.
    Step order in prompt (as of 2026-09-10): 0 -> 1 -> 3 -> 2 -> 4 -> 5 (disqualifier-first).
  cs-paper-interpreter.py: runs a SIMPLIFIED version only (feasibility gate + structural
    analogy check added to prompt; no Steps 0–5 chain; no _deterministic_verdict()).
    Do not apply this skill’s formula to cs-paper-interpreter output.
  Manual / agent-assisted: all 7 steps including Step 6.

Codebase inaccessibility fallback: if a gate requires checking the Hermes codebase
or config and that file is inaccessible, treat the gate as UNCERTAIN and apply the
conservative default: if the gate is a hard prerequisite (Step 3), return SKIP;
if it is a feasibility uncertainty (Step 5), score feasibility=1 with the assumption
named as uncertain and the verification test = "read [specific file] before implementing."
Access requirements: this chain requires the paper's FULL TEXT for Steps 0, 1, 2, and 3.
load-bearing assumptions, and primary contribution cannot be determined from abstracts alone.
If only the abstract is available, treat the result as DEFER until full text can be retrieved.

Disqualifier-first execution order (enforced in both script and manual):
  Step 0 -> Step 1 -> Step 3 -> Step 2 -> Step 4 -> Step 5 -> (Step 6 if non-SKIP)
Steps 0, 1, 3 are disqualifiers. Stop at the first SKIP trigger. Do NOT fill the
mapping table (Step 2) until Step 3 clears — filling it first causes post-hoc
rationalization (FM-8).

## Glossary

Terms used as gates or conditions in this skill:

  DEFER -- evaluation result meaning: insufficient information to decide.
           Return DEFER and retrieve the paper's full text before re-running.
           DEFER is not a formula output; it overrides the chain at Steps 0 or 1
           when required inputs are unavailable.

  COMPONENT_MAP -- the closed object/operation taxonomy defined in Step 2 of this
           skill. Not a separate artifact; synonymous with the Step 2 table.

  FIELD PRIMER -- in the interpreter scripts: a short description of the math field
           (its objects, operations, typical results) injected into each haiku-4-5
           call. Scoped to "what this math IS"; contains no relevance framing.
           Not defined in this skill; defined in math-paper-interpreter.py.

  SPIKE document -- an external artifact (markdown file or issue) recording a
           spike result. Not defined in this skill. Required by FM-6 in document-
           based workflows; absent in pure in-session use.

  Primary contribution -- the result highlighted in the paper's abstract final
           sentence, contribution bullet list, or paper title, using the author's
           own framing. When ambiguous: use the contribution with the most
           experimental evaluation. (See also Step 1 ALGORITHM definition.)

  "Directly tightens" (THEOREM exception) -- the bound is expressible as a closed-
           form constraint on the named Hermes parameter AND produces a specific
           numeric value or inequality that changes the current Hermes default.
           "Inspires" or "suggests" are not "directly tightens."

  "New infra" (feasibility gate) -- requires code not currently in the Hermes
           codebase: a new module, new API integration, new external service, or
           new infrastructure component. Configuration changes and edits to
           existing scripts are not "new infra."

  structural_match -- set ONLY in Step 2A. True if at least one mapping row is
           fully non-NONE (object AND operation both matched). Never overridden
           by Step 2B. Disanalogy failure sets disanalogy_valid=false (a separate
           gate), not structural_match=false.

  disanalogy_valid -- set in Step 2B. True if the disanalogy passes the strength
           test (load-bearing assumption named AND specific Hermes property named).
           Checked independently from structural_match in the verdict formula.

  Negative lexicon -- words that are insufficient as sole evidence of applicability.
           Two distinct lists with different functions:

           (1) APPLICABILITY OVERSTATEMENT words — appearing in abstract/title alone
           is not evidence of Hermes applicability:
           "adversarial," "robust," "optimized," "generalizable," "interpretable,"
           "efficient," "scalable," "novel," "elegant," "powerful," "flexible,"
           "intelligent," "adaptive," "relevant," "memory" (the word alone; not a
           mapped component).
           Also banned as sole evidence: phrases "implies we should," "suggests Hermes
           should," "is applicable to," "this math is relevant to."
           These words may appear in the neutral claim but cannot substitute for a
           mapped object/operation pair in the analogy table.

           (2) VOCABULARY ANCHORING words — forbidden in Step 0's neutral claim
           (the full list is in Step 0's Forbidden words):
           agent, routing, memory, context, skill, pipeline, orchestration, compression,
           attention, coordination, planning, reasoning, tool, session, swarm, spike,
           dispatch, hindsight, compaction.
           Purpose: prevent using Hermes vocabulary to make a paper seem applicable.

  Authority-laundering ban -- citing a senior author, prestigious venue, or citation
           count as evidence of applicability is disallowed. Applicability is assessed
           from the paper's content alone.

  Hermes parameter defaults (for THEOREM exception "changes the current default"):
           - context window fill ratio: compression.threshold (verified 0.5 in config.yaml;
             NOT compaction_threshold — that key does not exist).
           - skill routing top-K: ABSENT from config.yaml; code default top_k=5 in
             hermes-semantic-skill-routing. Cannot be tightened by config edit alone.
           - memory retrieval precision@K: K=5 (hindsight default; verify in hindsight config).
           - swarm consensus quorum size: reasoning_research.consensus.initial_agents=2.
           - cron retry backoff multiplier: read from cron config; typically 2.0.
           If the config value is unknown: return DEFER, read the config, re-evaluate.

---

### Step 0 -- Neutral Claim (prevents vocabulary anchoring)

Write the paper's core contribution in one sentence using NO Hermes vocabulary.
Forbidden words: agent, routing, memory, context, skill, pipeline, orchestration,
compression, attention, coordination, planning, reasoning, tool, session, swarm,
spike, dispatch, hindsight, compaction.

Format: "[Algorithm/Method name] achieves [result] for [object] under [assumption]."
Example: "[Method] achieves O(sqrt(T)) regret for bounded prediction sequences
          under adversarial inputs."  (no Hermes words; pure math description)

If only the abstract is available (no full text): treat as DEFER.
Do not run Steps 1–5 from abstract alone.
If only the title is available: write "TITLE-ONLY" and treat the paper as DEFER.
If you cannot write a neutral claim from the full text: stop and re-read the contribution section.

If the paper has multiple contributions, write the neutral claim for the STRONGEST
SINGLE contribution only. If the math is incidental (e.g. OT geometry used to
motivate a training recipe, but the contribution is the recipe), the neutral claim
must reflect what the paper actually proves or proposes, not the supporting math.

---

### Step 1 -- Abstraction Level

Pick exactly ONE label:

  THEOREM -- existence result, information-theoretic bound, lower bound,
             impossibility result. The paper proves something is true or impossible.
             Gate: SKIP immediately.
             Exception: the bound DIRECTLY TIGHTENS a named, existing Hermes runtime
             parameter listed below. "Directly tightens" means the bound is expressible
             as a closed-form constraint on that parameter AND produces a specific
             numeric value or inequality that changes the current Hermes default.
             "Inspires" or "suggests" are not "directly tightens."
             The bound must be applicable as a config edit ONLY — no new code.
             If applying the bound requires building new code: the exception does NOT apply.
             The paper remains THEOREM → SKIP. Do NOT reclassify to ALGORITHM.
             (Reclassification to ALGORITHM is for papers whose primary contribution
             IS an algorithm — a bound requiring code is still primarily THEOREM.)
             In that case, reclassify as HEURISTIC (the bound is evidence for a tuning
             decision, not an implementable algorithm) and continue.
             Named Hermes parameters eligible for tightening (verified 2026-09-10
             against live ~/.hermes/config.yaml; re-verify before claiming a change):
               - context window fill ratio: compression.threshold (verified: 0.5)
               - compaction token trigger: compression.threshold_tokens (verified: 120000)
               - protected tail turns: compression.protect_last_n (verified: 32)
               - proactive prune budget: compression.proactive_prune_tokens (verified: 48000)
               - micro-compact cadence: compression.micro_compact_every_n_turns (verified: 3)
               - thinking budget short: adaptive_reasoning.budgets.short (verified: 300)
               - thinking budget long: adaptive_reasoning.budgets.long (verified: 3000)
               - consensus initial agents: reasoning_research.consensus.initial_agents (verified: 2)
             ABSENT keys (do NOT use as tightening targets):
               - compaction_threshold (old name — replaced by compression.threshold)
               - compaction_buffer_tokens (never existed in config)
               - skills.top_k (code default only; not a config key)
               - memory.reinject_every_n (not in config)
               - thinking.budget_tokens (not in config)
             If the config key is unknown or the file is inaccessible: return DEFER,
             read the config, re-evaluate. Do not guess from "typical" values.

  ALGORITHM -- concrete procedure that could be coded today from the paper alone,
               with explicit numbered steps or pseudocode.
               "Primary contribution" definition: the result highlighted in the paper's
               abstract final sentence, contribution bullet list, or paper title.
               If multiple contributions are claimed, use the one the authors call out
               as the main advance. When ambiguous, use the contribution with the most
               experimental evaluation.
               Formal complexity analysis is NOT required — prompt engineering
               recipes, sampling procedures, and search algorithms without Big-O
               analysis all qualify if they have explicit steps.
               Companion-algorithm rule: an algorithm in an appendix counts ONLY
               if it implements the paper's PRIMARY contribution. If the primary
               contribution is a theorem or empirical finding and the algorithm is
               a baseline, ablation helper, or enumeration, classify by the primary
               contribution instead.
               Existence-without-value: a proof that a parameter exists, without a
               usable numeric value or computing procedure, is THEOREM not ALGORITHM
               (Algorithmist arXiv:2603.22363). Quote the invariant the steps preserve.
               Asymptotic ranking without named constants is not implementable.
               SPIKE candidate.

  HEURISTIC -- empirical pattern, tuning recipe, or architectural trick supported
               by ablations. No formal proof required, but must be measurable.
               OPTIMIZATION candidate if Hermes has the same tunable parameter
               the heuristic acts on (checked again in verdict formula — must be
               named explicitly here, not deferred).
               Parameter existence verification: name the parameter AND verify it
               exists by name in ~/.hermes/config.yaml or the Hermes codebase.
               If you cannot locate it: parameter is "absent" (SPIKE path, not OPTIMIZATION).
               Tie-break vs EMPIRICAL: if the paper's primary contribution is a tuning
               rule or recipe (the "what to do" result), classify as HEURISTIC even if
               the evidence method is ablation studies. EMPIRICAL applies only when the
               primary contribution is measurement or comparison of existing methods.

  EMPIRICAL -- benchmark study, evaluation, ablation survey, or dataset paper.
               The paper's contribution is measurement or comparison, not a new
               algorithm or proof.
               Gate: SKIP immediately for the EMPIRICAL contribution.
               Exception: if the paper contains a secondary algorithm or heuristic
               contribution (a new method or tuning recipe proposed alongside the
               evaluation), evaluate that secondary contribution independently as
               ALGORITHM or HEURISTIC. Do not skip the method just because the paper
               is framed as a benchmark.

  FRAMEWORK -- conceptual architecture requiring substantial new infra to build.
               Gate: SKIP. Reclassify as ALGORITHM only if ALL of:
               (a) every component named in the paper's abstract or contribution
                   list has a named counterpart in the Hermes Step 2 object taxonomy.
                   This is an EXISTENCE CHECK only — name the Hermes component alone
                   (e.g. "paper's router → Hermes skill_dispatch_rules").
                   Do NOT create pairings or fill the Step 2 mapping table here.
                   That is FM-8's prohibited pre-Step-3 mapping. List only Hermes names.
               (b) the paper includes concrete pseudocode for each component.
               (c) implementation requires only configuration changes or edits to
                   existing Hermes scripts (total new code across all changes required
                   by the paper's full proposed system: <50 lines; no new modules,
                   APIs, or external services; count ALL edits together, not per-patch).
               If any condition fails: SKIP. Do not reclassify.

---

### Step 3 -- Feasibility Gate (run BEFORE Step 2 — hard filter, any box = SKIP)

This step runs before the mapping table to prevent post-hoc rationalization.

  [ ] Training loop: paper requires weight updates, fine-tuning, or gradients
  [ ] Tabular/enumerable states: paper requires discrete state space or tabular MDP
  [ ] Oracle reward: paper requires per-turn ground-truth reward signal
  [ ] Human feedback loop: paper requires real-time human preference annotation,
      RLHF, or human-in-the-loop reward at inference time
  [ ] Proprietary or licensed dataset: paper's method requires a specific dataset
      not publicly available or not available at Hermes runtime
  [ ] Measurement infrastructure: paper requires external sensors, random projection
      matrices, or hardware measurement apparatus at inference time
  [ ] Model internals: paper requires access to weights, activations, or attention maps
  [ ] Posterior sampling: paper requires sampling from a model's posterior distribution
  [ ] Logit/logprob access: paper requires access to token logits, logprobs,
      or probability distributions over the vocabulary at inference time
  [ ] Process reward / PRM: paper requires a trained process reward model or
      per-step reward signal during inference

  For each checked box: name the gate and quote the paper assumption that triggers it.
  One box checked = SKIP immediately. Do not proceed to Step 2.

  Note: Step 2 and Step 3 overlap intentionally. Step 3 catches runtime impossibility
  even when a structural mapping exists (e.g. a discrete-choice algorithm that requires
  posterior sampling to score options passes Step 2 but fails Step 3). Step 2 catches
  structural mismatch independently.

---

### Step 2 -- Structural Analogy (run AFTER Step 3 clears)

Two parts: mapping table (Part A) and mandatory disanalogy (Part B).
Both must be completed.

Part A -- Mapping Table:

  For each of the paper's key objects and operations, fill one row.
  Papers with multiple key objects: fill one row per object. At least ONE row must
  be fully non-NONE for structural_match = true. If NO row can be filled, SKIP.
  Use only the closed taxonomies below — do not invent entries.

  Object taxonomy:
    sequence of tokens/turns          -> matches: context window, session history
    probability distribution (disc)   -> matches: skill selection, model routing
                                         (discrete choice over a named finite set)
    probability distribution (cts)    -> NONE. Hermes operations are discrete;
                                         no operation in the closed taxonomy takes
                                         a continuous real-valued input in a
                                         mathematically meaningful sense. Do not
                                         invent an entry. If paper's core object is
                                         a continuous distribution: structural_match
                                         is likely false; confirm via NONE in this row.
    directed graph                    -> matches: skill dependency graph, knowledge graph
    metric/embedding space            -> matches: memory retrieval, semantic clustering
    set of scored/ranked candidates   -> matches: spike prioritization list, retrieved
                                         memory candidates (must involve explicit
                                         scoring, not generic item storage)
    bounded prediction sequence       -> matches: N subagent verdicts, N tool results,
                                         N memory retrievals aggregated per turn

    -- DOES NOT MATCH --
    tabular state space               -> Hermes has no discrete enumerable states
    weight matrix / gradient          -> Hermes has no training loop
    image, audio, video               -> not applicable unless explicit vision task
    continuous manifold               -> Hermes operations are discrete
    oracle reward signal              -> no per-turn ground-truth reward
    model weights / activations / attention maps -> no access to internals
    posterior samples from a model    -> not available at inference time

  Operation taxonomy:
    select / argmax / rank            -> matches: skill routing, memory retrieval ranking
    aggregate / combine / ensemble    -> matches: swarm consensus, multi-tool result merge
    compress / summarize              -> matches: context compaction, pre-compaction flush
    retrieve / search                 -> matches: hindsight search, skill index lookup
    schedule / allocate               -> matches: cron, tool call ordering
    write / persist                   -> matches: memory write, skill file update
                                         (algorithmic write — not human-authored edits)

  Surface vocabulary IS NOT evidence of a match.
  NEGATIVE LEXICON — these words create false matches; finding them alone is not a match:
    agent, memory, context, compression, attention, routing, skill, pipeline,
    coordination, planning, reasoning, tool, session, optimization, swarm, dispatch.
  A match requires filling a row with both object AND operation from the taxonomies above.

Part B -- Mandatory Disanalogy:

  Name at least ONE way the paper's core math DOES NOT transfer to Hermes.
  The disanalogy must name a specific load-bearing assumption that fails in Hermes.
  "Load-bearing" = if this assumption fails, the paper's core contribution does not apply.
  Incidental differences (notation, field name, implementation language) are not disanalogies.

  Strength test — a valid disanalogy must pass ALL THREE:
    (a) Names a LOAD-BEARING assumption from the paper.
        Load-bearing definition: if this assumption fails, does the paper's core
        result still hold? If yes, the assumption is not load-bearing — discard it.
        Self-test: "Would the authors claim their main result applies to Hermes
        even if this assumption were relaxed?" If yes, not load-bearing.
        Format: quote or close paraphrase the assumption from the paper.
    (b) Explains concretely why that load-bearing assumption fails in Hermes.
        Must name a specific Hermes property that violates the assumption.
        "Hermes doesn't support X" alone is insufficient — name the Hermes
        property that makes X impossible.
    (c) The assumption is SPECIFIC TO THIS PAPER — not a universal property of
        all mathematical papers. An assumption that every paper shares (e.g.
        "a mathematical model exists," "the algorithm has inputs and outputs,"
        "formal notation is used") does NOT pass (c). The assumption must be
        identifiable in this paper's specific text, not in all papers.

  Weak — fails (a): "it's from a different field"
  Weak — fails (a): "paper uses matrix notation; Hermes uses Python"
  Weak — fails (b): "paper uses Euclidean distance" (incidental; does not affect core result)
  Strong: "algorithm assumes i.i.d. samples [assumption]; Hermes session turns are
           correlated within a session [why it fails]"
  Strong: "proof requires bounded loss function [assumption]; LLM token outputs are
           unbounded strings with no natural norm [why it fails]"

  If you cannot write a disanalogy that passes both (a) and (b):
    set disanalogy_valid = false. This is a separate gate from structural_match.
    structural_match is unchanged (it was set in Part A).
    The verdict formula checks disanalogy_valid independently.
    Result = SKIP (via formula, not here).

---

### Step 4 -- Measurability

  Name ONE testable Hermes metric that would change if this paper is implemented.
  Must be an existing named output or log field — not invented or requiring new tooling.
  If you cannot name a specific existing field by name: SKIP (metric gate fails).

  Known existing Hermes metrics (non-exhaustive):
    - skill dispatch latency (ms) — logged in skill routing
    - context compaction ratio — logged by pre-compaction flush
    - hindsight recall precision@K — logged by hindsight search
    - swarm consensus convergence turns — logged in hermes-swarm-consensus
    - memory write frequency per session — logged in memory layer
    - tool call count per turn — logged in session trace
    - session token count at compaction — logged by context manager

  If none of these fit and you cannot name another existing field with confidence:
  result = SKIP. Do not invent a metric name.

---

### Step 5 -- Scores

  desirability:
    2 = materially improves a daily-use Hermes path if it worked
    1 = marginal improvement, narrow use case, or small expected metric gain
    0 = no clear value to Hermes

  Desirability inflation guard: desirability=2 requires ALL of:
    - name the specific Hermes path that improves (e.g. "skill routing on every turn")
    - name the metric that would move (the metric named in Step 4 — from
      known list or explicitly verified by name)
    - give an estimated delta grounded in the paper's SAME metric in the SAME
 task setting as Hermes. "Conservative inference from a related setting" is
 NOT acceptable for des=2 — different task domains introduce unverifiable transfer.
 If only a related-setting number is available: des=1, not des=2.
      "Would be useful" or "~10% improvement" with no paper anchor = desirability=1.

  feasibility:
    2 = all gates pass, existing metric named, no new infra needed
    1 = all gates pass, existing metric named, BUT one or two specific named
        assumptions are uncertain. For each uncertain assumption, must provide:
        (a) the assumption name (must be from the paper's text, not invented) AND
        (b) the verification test.
        A verification test must name: a specific Hermes component, config key,
        or executable action (e.g. "check hermes config for skills.top_k value"
        or "grep for sequential in hermes-swarm-consensus.py").
        "Verify assumption holds" or "check if this is true" are not valid tests.
        Example: "assumes sequential rounds — verify hermes-swarm-consensus is
        sequential before implementing."
        Three or more uncertain assumptions = feasibility=0 (too speculative, regardless
    of whether verification tests are provided).
    0 = any gate fails, OR metric cannot be named, OR uncertainty is unspecified,
        OR three or more uncertain assumptions (verification tests do not save this)

  feasibility=0 is scored only at Step 5. A gate failure at Step 3 returns SKIP directly.

---

## Verdict Formula (computed by _deterministic_verdict() — model's "result" ignored)

Prerequisites — any failure = SKIP:
  - abstraction IN {ALGORITHM, HEURISTIC}
    (THEOREM, EMPIRICAL, FRAMEWORK without reclassification = SKIP)
  - structural_match = true (set in Step 2A: at least one mapping row fully non-NONE)
  - disanalogy_valid = true (set in Step 2B: load-bearing assumption named AND
    specific Hermes property named; separate from structural_match)
  - all feasibility gates passed (Step 3)
  - metric named and existing (from known list or explicitly verified by name)

OPTIMIZATION:
  abstraction IN {ALGORITHM, HEURISTIC}
  AND structural_match = true (from Step 2A)
  AND disanalogy_valid = true (from Step 2B)
  AND feasibility = 2 (all gates pass, existing metric, no new infra)
  AND desirability >= 1
  AND if HEURISTIC: named tunable parameter exists in Hermes
      (if parameter absent -> SPIKE, not OPTIMIZATION)
  Note: ALGORITHM + feasibility=2 + des>=1 correctly yields OPTIMIZATION.
  A fully-feasible implementable algorithm with a named metric is OPTIMIZATION.
  SPIKE is for uncertain feasibility only; use it when one or two named assumptions
  are unverified (each with a verification test stated).

SPIKE:
  abstraction IN {ALGORITHM, HEURISTIC}
  AND structural_match = true (from Step 2A)
  AND disanalogy_valid = true (from Step 2B)
  AND (feasibility = 1 OR (HEURISTIC AND named parameter absent))
  AND desirability >= 1
  Note on HEURISTIC+absent path: if a HEURISTIC paper has no named Hermes parameter,
  it cannot reach OPTIMIZATION (which requires the parameter). SPIKE here means
  "worth a spike to determine whether a Hermes parameter for this heuristic exists."
  It is not a full endorsement — the spike must find the parameter or downgrade to SKIP.

SKIP: everything else (including desirability = 0 at any verdict level)

Script path: Steps 0–5 in disqualifier-first order + formula. Step 6 not automated.
Manual path: same order + Step 6.

---

## How to Use This Skill Manually

Follow the disqualifier-first order: 0 -> 1 -> 3 -> 2 -> 4 -> 5 -> 6.
Do NOT fill the mapping table (Step 2) before Step 3 clears.

1.  Read the abstract AND contribution section. Not just the title.
2.  Write the neutral claim (Step 0). If abstract-only (no full text): DEFER.
      If title-only: DEFER. If cannot write from full text: re-read contribution section.
3.  Pick abstraction level (Step 1, exactly one label):
      THEOREM with no named Hermes parameter to tighten: SKIP.
      THEOREM tightening a named parameter: reclassify as HEURISTIC, continue.
      EMPIRICAL: SKIP (unless secondary algorithm or heuristic contribution exists —
        then evaluate that contribution independently; the primary EMPIRICAL label is SKIP
        and the secondary contribution is evaluated on its own merit).
      FRAMEWORK: check all three reclassify conditions. Any fails: SKIP.
      ALGORITHM: confirm it is the primary contribution (not appendix baseline).
      HEURISTIC: identify and name the tunable parameter it acts on.
4.  Check feasibility gates (Step 3). First box checked: SKIP.
5.  Fill the mapping table (Step 2A). No valid row: SKIP.
6.  Write disanalogy (Step 2B). Fails strength test (a)+(b): set disanalogy_valid=false; formula produces SKIP.
7.  Name the metric (Step 4). Not on known list and uncertain: SKIP.
8.  Score desirability (apply inflation guard) and feasibility (Step 5).
9.  Apply verdict formula. For HEURISTIC: explicitly name the parameter.
10. If verdict is SPIKE or OPTIMIZATION: run Step 6 (asymmetric critic).

---

## Asymmetric Critic Pass (Step 6 — manual only; run for SPIKE and OPTIMIZATION)

The critic's ONLY job is to find reasons to downgrade. It cannot upgrade.
Run as a separate cold prompt or explicit second pass.
In-session: write "CRITIC:" as an explicitly-labeled separate block AFTER the
main chain output. IMPORTANT: a CRITIC: block in the same session still has access
to the same prior context and is subject to same-chain confirmation bias. It reduces
but does not eliminate the bias. For OPTIMIZATION verdicts in production use, a cold
prompt (new session, no prior chain context) is the recommended practice.
The CRITIC: block is an acceptable minimum for SPIKE verdicts or when a cold session
is impractical.

Ask: "Why does this NOT transfer to Hermes?"

Checklist:
  - Re-examine mapping rows: was any match borderline (ambiguous object/operation)?
    "Borderline" = the evaluator chose between two taxonomy entries and the choice
    was not obvious, or the paper's object is a loose fit to the taxonomy entry
    (e.g. "loss trajectory" mapped to "sequence of tokens/turns").
    Critic may re-score a borderline row as NONE. Clearly-passed rows are confirmed, not re-litigated.
  - Is the disanalogy actually load-bearing? Trivially-true = not a disanalogy.
  - Does the paper's benchmark context match Hermes's runtime context?
    (e.g. batch offline evaluation vs interactive per-turn agent)
  - Does implementing this require a tool, API, or capability Hermes doesn't have?
  - PRIMARY CONTRIBUTION TRANSFER TEST (apply to every SPIKE or OPTIMIZATION):
    Ask: "Does the paper's primary mathematical contribution — the formal guarantee,
    theorem, or bound — survive the disanalogy? Or does only the intuitive principle
    survive?"
    If only the intuitive principle survives (the formal guarantee breaks on the
    disanalogy), the mapping is borderline. Downgrade accordingly:
      OPTIMIZATION -> SPIKE
      SPIKE -> SKIP (if the intuitive principle is already implicit in existing Hermes
               behaviour and adds no new procedure)
    Intuitive principle = a generic heuristic (e.g. "rank by past performance",
    "prefer smaller representations") that requires no math to motivate.
    Formal guarantee = the bound, convergence proof, or optimality result the paper
    actually proves, which depends on specific assumptions that fail in Hermes.
    Test phrasing: "If I strip the math and keep only the intuitive principle, is
    this still worth implementing — or does Hermes already do something equivalent?"
    If yes to equivalent: SKIP. If yes to worth-implementing-without-math: SPIKE at best.

Downgrade triggers (each independent; combinator = worst result wins):
  - Mapping row re-scored as NONE:
      OPTIMIZATION -> SPIKE; SPIKE -> SKIP
  - Disanalogy fails strength test on re-examination:
      OPTIMIZATION -> SPIKE; SPIKE -> SKIP
  - Benchmark context mismatches Hermes runtime:
      OPTIMIZATION -> SPIKE (cannot reach SKIP from this trigger alone)
  - Missing tool or API required:
      any verdict -> SKIP

Combinator: SKIP beats SPIKE beats OPTIMIZATION. Apply all triggered downgrades,
take the worst result. Critic's final verdict is binding and cannot be appealed.

---

## Worked Examples

### Example A -- SPIKE (Hypothetical: online aggregation algorithm)

NOTE: This is a HYPOTHETICAL example. All paper details are invented for illustration.
Do not treat it as a real calibration anchor. No arXiv ID is assigned.

Suppose a paper proposes an online learning algorithm for aggregating N bounded
predictions with regret guarantees under adversarial inputs.

Step 0 neutral claim:
  "Algorithm X achieves O(sqrt(T)) regret for aggregating N bounded predictions
   under adversarial inputs across T rounds."
  (Neutral: no Hermes vocabulary; describes objects, operation, and guarantee.)

Step 1 abstraction:
  ALGORITHM (paper's Algorithm 1 in the body is the primary contribution;
             explicit pseudocode; not a pure existence proof).
  Companion-algorithm check: Is this a baseline/appendix algorithm? No — it is
  the contribution highlighted in the abstract. Proceed.

Step 3 feasibility gates (run before Step 2):
  Training loop: NO. Tabular states: NO. Oracle reward: NO. Human feedback: NO.
  Measurement infra: NO. Model internals: NO. Posterior: NO. Logit access: NO.
  Proprietary dataset: NO. PRM: NO.
  All gates pass. Proceed to Step 2.

Step 2A mapping:
  Object: bounded prediction sequence -> N subagent verdicts aggregated per turn
           (from taxonomy: "bounded prediction sequence -> N subagent verdicts")
  Operation: aggregate / combine -> swarm consensus (hermes-swarm-consensus skill)
  structural_match = true

Step 2B disanalogy:
  (a) Paper assumes T rounds known in advance [load-bearing: the O(sqrt(T)) regret
      bound requires T for the learning rate schedule].
      Self-test: "Would the authors claim O(sqrt(T)) applies without knowing T?"
      No — the bound explicitly depends on T. This is load-bearing.
  (b) Hermes swarm tasks are variable-length; T is not fixed in advance, which
      violates the algorithm's assumption that T is known for the learning rate schedule.
      Whether a conservative default T can substitute is UNVERIFIED (see feasibility=1).
  Strength test: passes (a) — specific load-bearing assumption quoted; (b) — specific
  Hermes property named (variable-length tasks). (c) — specific to this algorithm's
  O(sqrt(T)) regret bound, not a universal property of all papers. VALID disanalogy.
  Note: Part B names the violation; feasibility=1 captures that it may be workable.
  These are not contradictory: the assumption fails as stated, but a workaround may exist.

Step 4 metric: swarm consensus convergence turns (existing log field)

Step 5:
  desirability = 1 (consensus aggregation is useful if the algorithm reduces
                    convergence turns; delta unknown without running the paper's
                    code — cannot claim des=2 without paper-grounded estimate)
  feasibility = 1 (all gates pass, metric named; TWO uncertain assumptions:
                   (1) "T known in advance" — verify whether a default T can be
                   set conservatively without breaking the guarantee;
                   (2) adversarial benchmark context — verify swarm runs are
                   adversarial in the relevant sense.
                   Two uncertainties <= two-max, so feasibility=1 stands.
                   Each has a verification test. No new infrastructure required.)

Formula: ALGORITHM, structural_match=true, disanalogy_valid=true, feasibility=1, desirability=1
  -> SPIKE prerequisites met; feasibility=1 -> SPIKE (not OPTIMIZATION)

Step 6 critic:
  Re-examine mapping: "bounded prediction sequence -> N subagent verdicts" — is this
  borderline? A swarm verdict is bounded and sequential, matches the taxonomy entry.
  Confirmed, not re-scored.
  Disanalogy load-bearing? Yes — T-dependence is central to the algorithm.
  Benchmark context: paper evaluates in adversarial online learning setting;
  Hermes is interactive per-turn. Adversarial assumption may or may not hold.
  This is the second uncertainty already counted in feasibility=1 above.
  No downgrade triggered. SPIKE confirmed.

Final: SPIKE

---

### Example B -- SKIP (tabular RL convergence proof)

Step 0 neutral claim:
  "Q-learning converges to the optimal policy in tabular MDPs under infinite sampling."

Step 1 abstraction:
  THEOREM — the primary contribution is a convergence proof, not a deployable algorithm.
  No named Hermes parameter is tightened (Hermes has no tabular MDP or convergence
  parameter). Exception does not apply.
  Gate: SKIP immediately.

Final: SKIP (Steps 2–6 not run)
Note: structural_match and disanalogy_valid are not set — chain exits at Step 1.
The formula's SKIP prerequisite "abstraction IN {ALGORITHM, HEURISTIC}" fails first.

Note: FM-4 — Step 1 catches this, not Step 3. Step 3 (tabular states gate) would also
fire if Step 1 were misapplied, but Step 1 is the primary and earlier catch.

---

## Failure Modes and Catches

FM-1: Math is incidental, not the primary contribution
  Symptom: Abstract uses math to motivate a training recipe; the theorem isn't
           the contribution.
  Mechanism: Neutral claim (Step 0) names the training insight, not the math.
             Abstraction (Step 1) lands as HEURISTIC with no taxonomy binding.
             Usually caught at Step 2 (no valid object match).
  Caveat: Step 0 alone does not automatically catch this. Evaluator must verify
          the neutral claim references the paper's main theorem/algorithm section.
  Practical implication: If the neutral claim's math doesn't appear in the paper's
          contribution bullets, flag for manual review before continuing.

FM-2: THEOREM mistaken for ALGORITHM
  Symptom: "proves convergence" rated SPIKE because it sounds implementable.
  Mechanism: Step 1 THEOREM gate fires; SKIP immediately.
             Companion-algorithm note: classify by PRIMARY contribution. Theorem
             primary + appendix algorithm = THEOREM = SKIP.
  Practical implication: Read the "Contributions" section, not the abstract.

FM-3: Vocabulary match (shared words, no structural match)
  Symptom: "agent memory compression" in title -> SPIKE.
  Mechanism: Step 2A requires object+operation from closed taxonomies. Negative
             lexicon prevents shared words as evidence. No valid row = SKIP.
  Practical implication: Evaluator must quote the taxonomy entry used; invented
             entries are not accepted.

FM-4: Tabular MDP paper framed as "planning" or "optimization"
  Symptom: Q-learning paper for "agent optimization" treated as HEURISTIC.
  Mechanism: Step 1 (convergence proof = THEOREM -> SKIP) is the primary catch.
             Step 3 tabular-state gate is the secondary catch if Step 1 is misapplied.
  Practical implication: Check if the paper's result is a proof or empirical finding.

FM-5: Theoretical bound inflated to implementation claim
  Symptom: "this bound implies we should use smaller context windows."
  Mechanism: Step 1 THEOREM gate (must tighten a named parameter or SKIP).
             Step 4: bound alone is not an existing metric.
             Script: _deterministic_verdict() requires explicit metric string.
             Manual: Step 4 requires naming a known existing field.
  Practical implication: If you cannot name a specific Hermes log field the bound
          would move, do not assign OPTIMIZATION.

FM-6: Step 6 critic skipped (manual path)
  Symptom: OPTIMIZATION assigned without cold review.
  Mechanism: Step 6 is manual-only and discipline-dependent.
  Enforcement for document-based workflows: spike document requires a mandatory
             "Step 6 outcome:" field; if blank, treat as SPIKE until completed.
  Enforcement for in-session use: Step 6 cannot be enforced structurally. Use this
             heuristic: at the end of the chain, write "CRITIC: reasons this fails:"
             as a separate reasoning block before finalizing. If you cannot produce
             at least one plausible downgrade argument, treat result as SPIKE.
  Practical implication: Never finalize OPTIMIZATION in a single reasoning pass.

FM-7: Primer framing inflates evaluator confidence
  Symptom: Primer says "this math is relevant to Hermes context management";
           evaluator accepts surface vocabulary as structural match.
  Mechanism: SciFactCheck (arXiv:2606.21359) finds scientifically fine-tuned models
             produce more assertive, less calibrated claims. Primer framing as "what
             this math IS" (not "why it's relevant") reduces vocabulary anchoring.
  Practical implication: FIELD PRIMER in interpreter = description of math objects
             and operations only. No sentences about Hermes relevance.

FM-8: Post-hoc rationalization (mapping table filled before disqualifiers)
  Symptom: Evaluator reads title, forms SPIKE verdict, then fills mapping table
           to justify it.
  Mechanism: Disqualifier-first order: 0 -> 1 -> 3 -> 2 -> 4 -> 5.
             Step 2 mapping table is filled AFTER Step 3 clears. This is enforced
             in the manual procedure and in the script prompt ordering.
  Practical implication: Enforce step order strictly. If mapping table is filled
             before Step 3: for the script path, re-run the full interpreter; for manual
             use, discard the filled table and re-fill after Step 3 clears.

FM-9: Desirability inflation (anchor bias toward OPTIMIZATION)
  Symptom: Evaluator wants the paper to apply; assigns desirability=2 with an
           invented metric delta, converting SPIKE to OPTIMIZATION via feasibility=2.
  Mechanism: The real conversion lever is feasibility=2, not desirability=2.
             des=2 vs des=1 both reach OPTIMIZATION when feasibility=2.
             The actual guard is the feasibility gate — if feasibility=1 is correctly
             scored (one uncertain assumption), the result stays SPIKE regardless of des.
             The desirability inflation guard slows evaluators who want des=2 by requiring
             a paper-grounded delta, but cannot block OPTIMIZATION if feasibility=2 is
             legitimately scored.
  The real protection: score feasibility strictly. If ANY load-bearing assumption
             is uncertain, feasibility MUST be 1, not 2. Do not round up.
  Practical implication: When an evaluator assigns OPTIMIZATION, ask: "Is every
             gate genuinely passed and every assumption genuinely verified?" If not,
             downgrade feasibility to 1 -> SPIKE.

FM-10: Formal guarantee mistaken for transferable procedure
  Symptom: Paper's primary contribution is a formal bound (e.g. exponential recency
           dependence proven under specific measurement assumptions). Evaluator maps
           the intuitive principle ("rank by past progress") to Hermes and assigns
           SPIKE, without checking whether the formal guarantee survives.
  Mechanism: The formal guarantee requires measurement infrastructure unavailable
             in Hermes (e.g. bit-level Kolmogorov complexity, tabular state counts,
             exact posterior samples). Only the intuitive principle survives -- but
             the intuitive principle may already be implicit in existing Hermes
             behaviour (LRU, recency weighting).
  Catch: Step 6 PRIMARY CONTRIBUTION TRANSFER TEST. Ask: "Does the formal guarantee
             survive the disanalogy?" If no, ask: "Is the intuitive principle already
             implicit in Hermes?" If yes: downgrade to SKIP. If no: SPIKE at best.
  Practical implication: Every SPIKE or OPTIMIZATION verdict must pass the primary
             contribution transfer test in Step 6. A paper whose formal guarantee does
             not transfer and whose intuitive principle is already implemented should
             be SKIP, not SPIKE. Calibration anchor: arXiv:2605.14831 (Herrmann &
             Schmidhuber 2026) -- SPIKE (weak) because the intuitive principle adds
             new procedure (compaction ratio slope) even if the formal guarantee fails.
             Contrast with a case where Hermes already does LRU: that would be SKIP.

---

## Calibration Reference

WARNING: All arXiv IDs previously listed here were LLM-generated and verified wrong.
Every ID was checked against arxiv.org and resolves to a different paper.

Verified mismatches (do NOT use as calibration anchors):
  arXiv:2608.28754 -- actual: "Peer Oversight in Collective Decision Making"
  arXiv:2609.01131 -- actual: "Information-Theoretic Framework for AI-Native Communication"
  arXiv:2608.31166 -- actual: "Constant Individual Regret in General Games"
  arXiv:2609.02724 -- actual: "Almost Envy-Freeness for Additive Mixed Manna with Entitlements"

No verified calibration anchors exist as of Sep 8 2026.

Example A (the "Hypothetical: online aggregation algorithm") is a chain walkthrough only — its paper details are invented.

To add a real calibration anchor:
  1. Verify arXiv ID on arxiv.org — title must match description.
  2. Run paper through chain manually, recording all step outputs.
  3. Implement spike; measure metric movement.
  4. Record: verified ID + actual paper title + Hermes path + observed metric delta.

---

## Verified Calibration Anchors

These cases were run to completion (chain + spike implementation + critic) in session
20260908_183611_fed04a. They are verified real papers.

### Anchor 1 -- SPIKE (weak, formal guarantee does not transfer)

Paper: Herrmann & Schmidhuber (2026). "Interestingness as an Inductive Heuristic for
  Future Compression Progress." arXiv:2605.14831.
Verified: title matches arXiv record (Sep 2026).

Step 0 neutral claim:
  "A heuristic ranks tasks by expected rate of future description-length reduction,
   using past compression progress to predict discovery rate under three
   information-theoretic priors."

Step 1: ALGORITHM (explicit ranking procedure with formal analysis).

Step 3 gates: all pass.

Step 2A mapping:
  Object: set of scored/ranked candidates -> spike prioritization list
  Operation: select/argmax/rank -> skill routing ranking
  structural_match = true

Step 2B disanalogy:
  Paper assumes compression progress is observable as a discrete time-series of
  program lengths on standardised Turing machine paradigms. The formal guarantee
  (exponential recency dependence on breakthrough timing) requires bit-level
  Kolmogorov complexity measurements. Hermes context streams are natural-language;
  no stable notion of description length in bits exists between turns.

Step 5: feasibility=1, desirability=1. -> SPIKE

Step 6 critic outcome: DOWNGRADE SIGNAL TRIGGERED.
  Primary contribution transfer test: the paper's primary contribution IS the formal
  guarantee (exponential dependence on recency of last breakthrough, proven under
  three priors). This guarantee requires bit-level program length. Only the intuitive
  principle survives in Hermes: "rank by past progress rate." This is equivalent to
  generic LRU caching + recency weighting, which Hermes already approximates.
  Mapping re-scored as BORDERLINE (the "set of scored/ranked candidates" mapping
  was to spike prioritization, but the paper's actual procedure is over enumerable
  computational tasks, not LLM context segments).
  Final verdict: SPIKE (weak) -- kept because the compaction ratio slope IS a
  measurable proxy and the procedure can be approximated; but formal guarantee
  does not transfer. Implementation must be validated against baseline before
  claiming benefit.

Calibration lesson: When the formal guarantee is the paper's primary contribution
  and it requires measurement infrastructure (bit-level complexity) unavailable in
  Hermes, the mapping is borderline and critic should flag it. Only the intuitive
  principle survives -- ask whether Hermes already does it.

---

### Anchor 2 -- SPIKE (clean, formal mechanism partially transfers)

Paper: Vervaeke, Lillicrap & Richards (2012). "Relevance realization and the
  emerging framework in cognitive science."
  Journal of Logic and Computation 22(1):79-99.
  Full text: http://sites.utoronto.ca/jvcourses/jolc.pdf (verified)

Step 0 neutral claim:
  "Dynamically balanced opponent-process pairs (compression vs. particularization,
   exploitation vs. exploration, focusing vs. diversifying) enable a self-organizing
   system to select relevant information from an intractably large input space without
   a centralised relevance oracle."

Step 1: HEURISTIC (empirical patterns from ML mechanisms -- weight decay, TD-learning,
  competing cost functions -- supported by existing evidence; no formal optimality proof).
  Named tunable parameter: lambda (compression-vs-particularization tradeoff),
  mapped to compression.rr_scorer_lambda in Hermes config (added by integration patch
  in session 20260908_183611_fed04a).

Step 3 gates: training loop BORDERLINE (weight decay is cited as the mechanism, but
  the structural principle is more general and instantiable without gradients at
  inference time). Gate treated as pass under heuristic reading. Remaining gates pass.

Step 2A mapping:
  Object: set of scored/ranked candidates -> context segment retention scoring
           during pre-compaction flush
  Operation: compress/summarize -> context compaction (Phase-1 tool-result demotion)
  Named tunable parameter: rr_scorer_lambda (in config after patch)
  structural_match = true

Step 2B disanalogy:
  Paper's mechanism is self-organizing: metabolic cost is real (felt, constrains
  behaviour). The opponent processes reach equilibrium without a central oracle
  because cost and benefit are both genuine feedback signals. Hermes has no metabolic
  cost feedback -- context length cost is imposed as a hard external threshold, not
  felt by the system. The emergent self-organisation property, which is the key
  innovation, does not transfer.

Step 5: feasibility=1 (training loop gate borderline; parameter exists after patch),
  desirability=2 (context compaction is a daily-use path; integration achieved
  25% less information loss in spike experiment on real 185-message session vs
  positional baseline; paper-grounded mechanism, same task domain).
  -> SPIKE (feasibility=1 holds despite des=2; des=2 cannot push to OPTIMIZATION
     when feasibility=1)

Step 6 critic outcome: NO DOWNGRADE.
  Primary contribution transfer test: paper's primary contribution is the structural
  principle (opponent-process pairs), not a formal optimality bound. The principle
  survives the disanalogy in degraded form: a fixed-formula approximation
  (retention_score = pp - lambda * cp) implements the Cognitive Scope pair without
  self-organisation. This is NOT equivalent to existing Hermes behaviour (the current
  Phase-1 prune is purely positional -- no information-density signal at all).
  Integration patch implemented; spike measured 25% reduction in information loss
  on real session data. Verdict confirmed: SPIKE (pending 20-session measurement
  protocol before OPTIMIZATION upgrade).

Calibration lesson: When the paper's primary contribution is a structural principle
  (not a formal bound), the primary contribution transfer test outcome is different.
  The principle survives in degraded form if it is NOT already implicit in Hermes
  behaviour. Here, positional-only pruning has no information-density signal, so the
  RR principle adds genuine new structure. SPIKE confirmed; promote to OPTIMIZATION
  after measurement protocol (3+ sessions, pp-loss delta positive, token reclaim
  regression <= 15%).

Promotion criteria (for reference):
  Run: python ~/.hermes/scripts/rr_compaction_spike.py --json on 20 sessions.
  Promote if: pp-loss delta positive on 3+ sessions AND token reclaim regression <= 15%.
  Config to enable: compression.use_rr_scorer: true, compression.rr_scorer_lambda: 0.2
  Note: constructor default is 0.5; live config.yaml is 0.2. Use 0.2 as the reference value.

---

## Research Basis

Verified from Sep 8 2026 subagent sweep (Grok-4.6, 253s) unless noted.
Practical implications reflect the abstract's stated content.

Structured frameworks:
  arXiv:2504.17192 PaperCoder -- three-stage pipeline (planning/analysis/generation);
    applicability decided at analysis, not from abstract.
    Practical implication: title+abstract interpreters miss the analysis stage;
    Steps 0–3 are a partial structural analog of the analysis stage (not identical).
  arXiv:2603.22363 Algorithmist -- proof-first synthesis; implementation must preserve
    a named invariant. Existence proofs without usable parameters are not algorithms.
    Practical implication: STEP 1 ALGORITHM requires quoting the invariant the steps
    preserve; existence-only → THEOREM. Asymptotic ranking without named constants is
    not implementable (theory-practice gap: Fibonacci-heap Dijkstra, AKS primality).
  arXiv:2509.06917 Paper2Agent -- paper + codebase converted to MCP with iterative tests;
    transfer = "can paper's tools answer a new query", not topical similarity.
    Practical implication: structural function match beats keyword match.
    Note: "COMPONENT_MAP proximity" (RA-RFT, below) refers to surface-level
    keyword similarity between paper terms and taxonomy entries — not a defined
    Hermes similarity metric.
  arXiv:2504.00255 SciReplicate-Bench -- reproduction score = executable fidelity.
    Practical implication: checklist of implementable units beats holistic "looks useful."
  arXiv:2604.10793 Bajraktari & Vogelsang "Enhancing Understandability and Transparency
    of Research Software: Tracing Research to Code" -- if you cannot name the target
    file/function, you are still at bound level, not implementation.
    Practical implication: Step 4 metric requirement operationalizes this.
  arXiv:2608.13428 AIRL/RAIL -- 9-level readiness scale; chief expert can only confirm
    or lower, never raise.
    Practical implication: Step 6 asymmetric critic cannot upgrade a verdict.
  arXiv:2006.12497 TRL4ML -- NASA-style TRL for ML; "principle shown" != "integrated."
    Practical implication: SPIKE != OPTIMIZATION; integration TRL assessed separately.
  arXiv:2609.04871 AutoLR -- multi-expert adversarial council, evidence-weighted trial
    allocation, deterministic controller owns metrics; LLMs propose, controller decides.
    Practical implication: _deterministic_verdict() owns the verdict; model proposes fields.
  arXiv:2604.02617 AutoVerifier -- (Subject, Predicate, Object) triples + cross-source
    verification; finds overclaims without relying on domain expert judgment.
    Practical implication: overclaim detection is feasible at scale; Step 3 uses
    a binary gate structure (different from triples) as a lower-cost analog.
  arXiv:2604.21304 PaperMind -- four task families including critical assessment;
    isolated Q&A overrates paper understanding.
    Practical implication: title+abstract alone insufficient; Step 0 requires reading
    the contribution section.
  arXiv:2508.19202 KRUX/SciReas -- bottleneck is retrieving task-relevant knowledge,
    not reasoning capacity; injecting system constraints in-context helps more than CoT.
    Practical implication: HERMES SYSTEM FACTS block injected per interpreter call;
    missing system constraints are a likely failure source.
  arXiv:2606.28363 meta-pipe -- 12 overclaim linguistic patterns + evidence grades +
    mandatory human gates.
    Practical implication: negative lexicon and authority-laundering ban operationalize
    overclaim detection.

Analogical reasoning:
  arXiv:2310.01714 Analogical Prompting -- self-generate exemplars before solving
    (not before judging); beats 0-shot CoT.
    Practical implication: mapping table (Step 2A) makes analogy explicit before verdict,
    serving a similar anchoring function — but this is not the paper's proposed method.
  arXiv:2310.00996 ARN -- GPT-4 below random on far analogies zero-shot; disanalogy
    scoring essential.
    Practical implication: Step 2B mandatory disanalogy is non-optional; models
    systematically miss failed mappings.
  arXiv:2603.29997 YARN -- decompose, abstract at chosen grain, then structure-map;
    wrong abstraction grain (too concrete or too abstract) causes incorrect mapping.
    Practical implication: Step 1 abstraction level must be set before Step 2.
  arXiv:2511.20344 Curious Case of Analogies -- structural alignment failures: relational
    info encoded but not applied to new entities.
    Practical implication: structural mapping is the bottleneck; adding more field context
    alone doesn't fix application failures.
  arXiv:2503.03666 concept vectors -- correct internal concept != correct output;
    structured slots help surface the alignment.
    Practical implication: free-prose verdict unreliable; JSON with required fields forces
    explicit mapping.
  arXiv:2606.13680 RA-RFT -- retrieve by expected reasoning benefit, not semantic
    similarity; semantic-near papers are often the wrong analog.
    Practical implication: COMPONENT_MAP proximity is the wrong similarity measure.
  arXiv:2503.14891 MetaLadder -- recall analogical meta-problems before solving;
    reported improvement vs CoT on math tasks (specific delta unverified from abstract).
    Practical implication: calibration examples serve as meta-problem anchors.
  arXiv:2605.11258 AR for scientific creativity -- cross-domain analogies from shared
    relational structure; diversity +90–173% vs mode-collapsed generation.
    Practical implication: object/operation taxonomy in Step 2 is a relational scaffold.

Abstraction level:
  arXiv:2507.00432 math reasoning transfer -- math benchmark skill does not transfer to
    planning/coding/science for most SFT-tuned reasoners.
    Practical implication: a "reasoning" model does not substitute for the chain;
    math skill != system judgment skill.

Feasibility:
  arXiv:2606.04769 description-code inconsistency -- abstract claims and real interfaces
    often diverge.
    Practical implication: Step 3 gates check runtime constraints independently of
    abstract capability claims.

False-positive mitigation:
  arXiv:2606.21359 SciFactCheck -- scientifically fine-tuned models are more assertive
    and less calibrated (this is about model fine-tuning, not primer content).
    Practical implication: FIELD PRIMER scoped to "what this math IS"; do not add
    relevance framing.
  arXiv:2408.10365 error injection -- plant wrong applicability claims; test if reviewer
    detects them.
    Practical implication: motivates building a calibration set with known
    SKIPs/SPIKEs for interpreter QA. No such verified set exists yet (Sep 2026).

---

## Embedded in Interpreter Scripts (2026-09-08)

math-paper-interpreter.py (cumulative changes):
  - 6-step evaluation chain in prompt (Steps 0–5 in disqualifier-first order)
  - Step 3 runs before Step 2 in prompt to prevent post-hoc rationalization
  - Output fields: neutral_claim, abstraction_level, object_operation, structural_match,
   disanalogy, disanalogy_valid, feasibility_violations (list of triggered gate names),
   feasibility (score 0/1/2; feasibility_violations informs feasibility scoring but
   both are emitted: violations = which gates triggered; score = resulting 0/1/2),
   desirability, target, reasoning
  - _deterministic_verdict() owns verdict; model's "result" field ignored
  - FIELD PRIMER scoped to "what this math IS" (no relevance framing)
  - max_tokens: 2000 (Steps 0–5 inline reasoning + JSON; raised from 1200)
  - --full-text: ar5iv HTML (https://ar5iv.labs.arxiv.org/html/ARXIV_ID), PDF fallback
    via pdftotext then pypdf; first 4000 chars to LLM instead of 1500-char abstract
  - Step 2 closed object taxonomy + 3-part disanalogy (quote, Hermes property, paper-specific)
  - Two calibration few-shots (tabular RL SKIP; Herrmann/Schmidhuber 2605.14831 SPIKE)
  - JSON extraction handles reasoning+JSON hybrid output
  - HEURISTIC parameter check in verdict function

cs-paper-interpreter.py:
  - Feasibility gate + structural analogy check added to prompt
  - Simpler pipe-delimited output format (not full JSON schema)

_deterministic_verdict() logic (Steps 0–5 + formula only; Step 6 not automated):
  abstraction check -> disqualifier gates -> structural_match -> disanalogy strength ->
  metric check -> HEURISTIC parameter check -> score thresholds -> verdict

HERMES SYSTEM FACTS block injected per call (KRUX finding):
  Provides Hermes runtime constraints to haiku-4-5 in working memory.
  Contents defined in the interpreter script, not this skill file.
