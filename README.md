<p align="center">
  <img src="assets/banner.png" alt="Hermes Agent" width="100%">
</p>

# hermes-fork ☤

> **This is a personal fork of [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent).** It tracks upstream and layers a dense set of research-driven extensions on top. Not an official Nous Research product — one person's daily driver. For the supported version use the upstream repo.

<p align="center">
  <a href="https://hermes-agent.nousresearch.com/docs/"><img src="https://img.shields.io/badge/Docs-hermes--agent.nousresearch.com-FFD700?style=for-the-badge" alt="Documentation"></a>
  <a href="https://discord.gg/NousResearch"><img src="https://img.shields.io/badge/Discord-5865F2?style=for-the-badge&logo=discord&logoColor=white" alt="Discord"></a>
  <a href="https://github.com/NousResearch/hermes-agent/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License: MIT"></a>
  <a href="https://nousresearch.com"><img src="https://img.shields.io/badge/Built%20by-Nous%20Research-blueviolet?style=for-the-badge" alt="Built by Nous Research"></a>
</p>

**227 commits ahead of upstream. 421 fork-only scripts. 25 active plugins. 145 core agent file changes.**

---

## What this fork adds over upstream

The fork's additions fall into nine areas. All extensions are additive — scripts, plugins, and configuration layered on top of upstream code. Nothing in the core agent loop is replaced; these things run alongside it, mostly as background scheduled jobs. Plugins are fail-open (they observe and report but don't crash the agent if they fail) unless otherwise noted.

---

### 1. Memory system

Upstream Hermes stores memories as plain text entries that the agent manually writes and reads. This fork adds ~65 background scripts that treat memory as a managed dataset — automatically deciding what to keep, what to discard, how to index it, and whether a new fact is worth saving at all. None of this runs during your conversation; it all runs as overnight or hourly scheduled jobs.

**How long should a memory be kept?**

Memories you haven't touched in a long time probably aren't useful anymore. These scripts calculate when to evict them:

- `memory-ttl-purge.py` — deletes memories that haven't been accessed within a configurable time window, with a floor so nothing important gets purged too aggressively
- `memory-ttl-floor-merge.py` — blends time-based expiry with how recently you actually used a memory, so frequently-touched old memories survive longer
- `memory-staleness.py` — scores each memory on how stale it is based on access history, separate from pure age
- `memory-mixing-ttl.py` — estimates how "connected" a memory is to others in the graph; isolated memories decay faster
- `memory-hitting-time.py` — identifies memories that are rarely reached during retrieval and flags them for earlier expiry
- `memory-conductance-ttl.py` — uses the memory graph's structure to decide retention: memories that act as bridges between clusters get longer lifetimes
- `memory-access-decay.py` — applies a smooth exponential fade to memory relevance scores based on time since last access

**Is this memory taking up too much space for what it contributes?**

These scripts check whether the memory system is encoding things efficiently — whether facts are being stored in a compressed, non-redundant way:

- `memory-jl-distortion.py` — checks that the numerical embeddings used to represent memories haven't drifted too far from the original text meaning (using a projection distance test)
- `memory-eckart-young.py` — checks whether the full set of memory embeddings can be compressed to fewer dimensions without losing much, and flags memory collections that have bloated beyond their information content
- `memory-lp-dct-gate.py` — applies a frequency-domain energy test to text segments: if most of the signal is in a few components, the text is compressible; low-energy segments get deprioritised
- `memory-bits-back.py` — estimates how much hidden redundancy exists in the memory encoding and whether the latent representation is earning its space
- `memory-kraft-code.py` — checks that the memory encoding satisfies a fundamental property of valid compression schemes (the Kraft inequality); violations suggest inconsistent encoding
- `memory-haar-mra.py` — analyses temporal patterns in memory over time at multiple resolution levels, like a multi-scale zoom on when memories were created and accessed
- `memory-rough-signature.py` — creates a compact mathematical fingerprint of a sequence of memory accesses; used to detect unusual patterns in how memories are being used over time

**Is retrieval returning the right things?**

When the agent looks something up, these scripts govern how results are ranked, deduplicated, and gated:

- `memory-adaptive-rank.py` — adjusts the ranking of memories in real time based on which ones have proven useful in past retrievals, learning from the agent's own retrieval history
- `memory-query-router.py` — decides which retrieval backend (session search, knowledge graph, long-term store) to query for a given type of question
- `memory-signature-rerank.py` — reranks retrieval results using the rough path signature of recent memory sequences, so context from recent activity influences what floats to the top
- `memory-redundancy-gate.py` — before saving a new memory, checks whether something nearly identical already exists; blocks the duplicate if so
- `memory-dkw-ue.py` — adds a statistical confidence band around retrieval scores, so the agent knows when a retrieval result is reliable vs. borderline
- `memory-sprt-commit.py` — uses sequential hypothesis testing to decide when there's enough evidence to commit a new fact to long-term memory, rather than committing everything immediately
- `memory-ransac-commit.py` — before committing a fact, checks it against existing memories and rejects it if it looks like an outlier inconsistent with what the agent already knows (a robustness filter borrowed from computer vision)

**How are memories related to each other?**

These scripts treat the memory store as a graph — nodes are facts, edges are relationships — and maintain that graph's health:

- `memory-ontology-topology.py` — analyses the shape of the memory knowledge graph (how connected it is, whether it has natural clusters, whether it has isolated dead-end nodes)
- `memory-taxonomy-discover.py` — automatically discovers category groupings from memory clusters, so related facts get labelled and grouped without manual tagging
- `memory-coupling-merge.py` — finds memory nodes that are so tightly related they're essentially the same thing, and merges them
- `memory-relation-extractor.py` — reads free-text memories and extracts structured relationships from them (e.g. "X is a type of Y", "X causes Y"), building typed edges in the graph
- `memory-bethe-free-energy.py` — measures the internal consistency of the memory graph by computing a physics-inspired energy score; high energy means the graph has contradictions or over-counted facts
- `memory-doob-decompose.py` — decomposes the history of a memory's value score into a predictable trend and a noise component, to separate systematic drift from random fluctuation
- `memory-portmanteau.py` — runs a statistical test for autocorrelation in memory access patterns; if you tend to access the same memories in bursts, this detects that structure

**Is the memory system drifting or developing anomalies?**

- `memory-auto-improvement.py` — a nightly pass that runs multiple health checks in sequence and flags memories that consistently fail them for review or deletion
- `memory-gelman-shrink.py` — estimates how consistent memory scores are across multiple measurement approaches; large disagreement suggests the scoring is unreliable
- `memory-kalman-latent.py` — applies a Kalman filter (like GPS smoothing) to track the underlying "true" relevance of a memory over time, filtering out noise from individual access events
- `memory-wave18-adversarial.py` / `memory-wave18-invariants.py` — an adversarial test suite for memory: tries to find ways to confuse the memory system (e.g. by injecting contradictory facts) and checks that invariants hold

**Long-term structured memory (L1 stack)**

Separate from conversational memory, this pipeline extracts the most important facts and elevates them to a structured, queryable knowledge store:

- `l1-extract.py` / `l1-promote.py` — scans session history and existing memories to identify facts worth keeping long-term, then moves them into the L1 store
- `l1-graphiti-write.py` / `l1-graphiti-reconcile.py` — writes promoted facts to a knowledge graph (Graphiti) and reconciles conflicts when two sessions produce contradictory facts about the same thing
- `l1-gmemory-consolidation.py` — periodically merges and de-duplicates nodes in the knowledge graph as it grows
- `l1-hypermem-promote.py` — identifies facts that are referenced by many other facts and promotes them to a hypergraph tier for faster lookup
- `l1-tracegrant.py` — tracks the provenance of every promoted fact: where it came from, which session, which tool call, so you can trace any memory back to its source
- `unified-recall.py` — a single recall interface that searches across all three tiers (L1 structured store, Graphiti knowledge graph, and session search) and merges the results
- `dual-backend-memory-fuser.py` — when two memory backends return results for the same query, this script fuses and deduplicates them into a single ranked list
- `hindsight-reembed.py` / `hindsight-watchdog.py` — periodically re-generates the vector embeddings for hindsight memories as the embedding model changes, and monitors the hindsight pipeline for stalls

---

### 2. Skill routing

Upstream Hermes picks which skill to load using keyword matching (BM25 — essentially a search engine similarity score). This works fine for 20–30 skills but degrades as the library grows, because many skills have similar descriptions and the best skill for a query isn't always the most lexically similar one. This fork adds ~60 scripts implementing a learning layer on top of BM25 that tracks which skills actually produce good outcomes and adjusts routing weights accordingly.

The core idea: treat skill selection as a multi-arm bandit problem. Each skill is an "arm"; each time a skill is routed, we observe an outcome (did it help?); over time, the router learns which skills are genuinely useful for which types of queries.

**Learning which skill to pick**

- `routing-linucb.py` — the main routing bandit. Uses contextual features (query type, session history, recent skill performance) to select skills. Updates weights based on observed outcomes after each use.
- `routing-kl-ucb.py` — an alternative bandit algorithm that's more aggressive about exploring underused skills to find hidden gems in the library
- `routing-tsallis-inf.py` — a bandit variant designed for adversarial conditions, where the best skill changes over time or the signal is noisy
- `routing-exp3-adversarial.py` / `routing-exp4-contextual.py` — two more bandit variants: EXP3 handles fully adversarial settings; EXP4 incorporates contextual side-information about the query
- `routing-ips-offpolicy.py` — estimates how well the current routing policy would have performed historically, correcting for the fact that we only observed outcomes for skills we actually picked (not all alternatives)
- `routing-pac-bayes-bound.py` — computes a theoretical guarantee on how well the routing policy generalises to new queries; useful for knowing when the router has learned enough to trust
- `routing-rademacher-bound.py` — a complementary bound on the complexity of the routing model; penalises overly complicated policies that might overfit to recent sessions
- `routing-weight-updater.py` — the central dispatcher that applies weight updates from all bandit algorithms to the shared routing table

**Is routing working correctly?**

These scripts act as health monitors for the routing layer — checking that the learned policy isn't diverging, gaming itself, or getting stuck:

- `routing-azuma-concentration.py` — a statistical check that the observed routing rewards are within expected bounds; large deviations suggest the reward signal is broken
- `routing-mcdiarmid-bm25.py` — checks whether the underlying BM25 similarity scores have shifted significantly (e.g. because the skill index was rebuilt), which would invalidate cached routing weights
- `routing-fano-bound.py` — a theoretical lower bound on how much information the routing decision carries; if it falls too low, the router is essentially random
- `routing-mutual-information.py` — directly measures how much the query features and the skill selection are correlated; low mutual information means the router isn't using context effectively
- `routing-convergence-guard.py` — detects when the routing policy has stopped converging (the weights keep oscillating), and raises an alarm
- `routing-switching-detector.py` — detects when the best skill for a class of queries has permanently changed (a regime shift), so old weights can be reset rather than averaged
- `routing-alarm-bridge.py` / `wave21a-alarm-bridge.py` / `wave21c-alarm-bridge.py` — collect alarms from all routing monitors and forward them to the central alarm log

**How do skills relate to each other?**

- `routing-skill-markov.py` — models skill usage as a Markov chain: given the skill used last turn, what skill is likely to be useful next? Improves multi-turn coherence.
- `routing-skill-percolation.py` — analyses the skill graph for percolation thresholds: at what point does removing a few highly-connected skills fragment the whole library?
- `routing-graph-bandit-update.py` — propagates routing weight updates through the skill graph, so improving one skill's weight also nudges related skills
- `routing-graph-independence.py` — tests whether the skill similarity graph has independent components (clusters of unrelated skills), which helps partition the routing problem
- `routing-boolean-influence.py` — identifies which query features most strongly influence routing decisions, helping diagnose why a particular skill keeps winning or losing
- `routing-mobius-audit.py` — audits the co-occurrence patterns of skills across sessions, checking whether the routing policy is inadvertently always pairing the same skills
- `routing-hamming-audit.py` — compares routing decisions across similar queries and flags cases where tiny query differences lead to wildly different skill selections (instability)
- `routing-token-setcover.py` — finds the minimum set of skills that collectively covers all query types in the recent session history; useful for pruning the index
- `routing-precision-recall.py` — tracks routing precision (how often the selected skill was actually useful) and recall (how often the right skill was selected at all) over time

**Are individual skills healthy?**

- `skill-monitor.py` — tracks each skill's performance over time using a changepoint detection algorithm; automatically excludes skills that have recently been degrading from the routing pool
- `skill-lift-tracker.py` — measures whether routing a skill to a query actually improves the outcome compared to not using a skill at all ("lift"); skills with negative lift get downweighted
- `skill-variance-regularization.py` — smooths out skills whose performance estimates are very noisy (high variance), preventing them from dominating the routing policy based on a lucky run
- `skill-disagreement-allocation.py` — identifies skills where different measurement approaches disagree on quality, and allocates more evaluation budget to resolve the disagreement
- `skill-imbalance-reweight.py` — corrects for the fact that some skills get routed far more often than others; ensures underused skills still get enough exposure to be evaluated fairly
- `skill_confidence_calibration.py` — checks whether the router's confidence estimates match actual accuracy (a well-calibrated router that says "80% confident" should be right ~80% of the time)
- `skill-hierarchical-routing.py` — first picks a skill category, then picks the best skill within that category; reduces the search space and speeds up routing for large skill libraries
- `bps-skill-selector.py` — budget-aware selection: picks the best skill that fits within the remaining context budget for the current turn
- `kl-skill-prior.py` — maintains a prior belief about each skill's utility based on its description, and updates it with observed outcomes; stops new skills from being ignored before they're proven
- `occam-skill-ranker.py` — penalises skills with long, complex descriptions relative to their observed utility (simpler explanations preferred)
- `soft-bellman-skill-router.py` — a probabilistic routing approach that sometimes picks a non-optimal skill to maintain exploration; prevents the router from locking in prematurely
- `skill-admissibility.py` / `skill-dependency-verifier.py` / `skill-integrity-check.py` — structural health checks on the skill library: are skill dependencies declared? Are there circular references? Are description frontmatter fields valid?

**Index and observability**

- `skill-router-index.py` — builds and updates the routing index across all 255 skills; runs weekly with `--build` to regenerate embeddings and BM25 scores
- `skill-routing-table.py` / `skill-routing-bounds.py` — manages the in-memory routing weight table and computes theoretical performance bounds
- `skill-access-logger` plugin — logs every skill access event (which skill, what query fingerprint, what outcome) for offline analysis
- `skill-routing-nudge` plugin — during a conversation turn, if the router's confidence in its skill selection drops below a threshold, inserts a brief nudge to the agent to reconsider
- `skill-latency-logger` plugin — tracks how long each skill takes to load and use; identifies slow skills that add latency to responses

---

### 3. Compaction evaluation pipeline

When a conversation gets too long, Hermes compresses ("compacts") earlier context to free up space. Upstream does this with a simple heuristic — it summarises and drops old turns. The problem: there's no way to know if the compaction was good or bad. Did the agent lose important facts? Did it hallucinate new ones during summarisation? This fork adds a measurement pipeline that scores every compaction on multiple axes and raises alarms when quality falls below thresholds.

**What gets measured, and why**

The main question is: does the compressed version faithfully represent the original? Two failure modes to guard against:
- **Coverage failure** — the compression lost information that was actually needed
- **Fabrication failure** — the compression introduced facts that weren't in the original

**JEV scoring** (`jev-compaction` plugin)

JEV (Joint Evaluation Voting) is the primary compaction quality gate. Before compaction runs, it marks segments of the context by importance. After compaction, it checks whether the high-importance segments survived. If the compaction would throw away too much important content, it's blocked.

- `pre-compact-annotate.py` — before the compaction runs, walks the context and labels each segment with an importance weight based on how much information it carries
- `jev_compaction.py` / `jev_verify_fn.py` — the scorer itself: computes a weighted coverage score and decides whether to allow or block the compaction
- `jev-scores-staleness-check.py` — alerts if the JEV scores haven't been updated recently, which would mean the gate is running on stale data

**Information-theory quality metrics**

These scripts apply mathematical measures from information theory to give a precise, model-free assessment of how much information was preserved or lost:

- `compaction-aep-typical-set.py` — checks whether the compressed content looks like a "typical" compression of the original, in the information-theoretic sense; atypical compressions are suspicious
- `compaction-chain-rule-mi.py` — measures how much information the compressed version shares with the original, turn by turn; a sharp drop in mutual information indicates a lossy compression
- `compaction-rd-converse.py` — computes the theoretical minimum distortion achievable at the current compression ratio; if the actual distortion exceeds this, the compaction algorithm is doing worse than it has to
- `rd-compaction-advisor.py` — uses the rate-distortion tradeoff to recommend how deep the compaction should go for the current context, balancing compression ratio against information loss
- `eval-compaction-distortion-gate.py` — a hard gate: if measured distortion exceeds a threshold, the compaction is rejected and the context is left uncompressed
- `eval-compaction-data-bridge.py` — pipes compaction quality scores from all the above scripts into a shared log file for the nightly evaluation pipeline to consume
- `statecomp-compression-router.py` — checks each context span's "readiness" for compression before including it in a compaction batch; spans that are still actively referenced get excluded

**ROUGE scorer** (no external dependencies)

ROUGE is a standard metric from the summarisation research literature — it checks word-level overlap between the original and compressed text. If the compressed version is missing words that appeared in the original, that's a coverage problem. If the compressed version contains words that weren't in the original, that's a fabrication problem.

- `score-compaction-rouge.py` — computes two scores: ROUGE-1 (single-word overlap) and ROUGE-L (longest matching sequence). Both coverage and fabrication alarms are raised when scores fall below thresholds. For very long contexts (over 10,000 words), it samples from the beginning and end to keep the computation fast. Runs nightly and appends results to a log file.

**Compaction gate** (`compaction-gate` plugin)

An independent gate based on minimum description length: compaction is only allowed if the compressed version is genuinely shorter in an information-theoretic sense by at least a configurable threshold. Prevents compaction from running when it would produce a result almost as long as the original.

---

### 4. Loop control and anytime algorithms

The agent loop runs many background processes — evaluation jobs, compaction, skill routing updates — that need to be managed without destabilising the agent or wasting compute. This section covers the control infrastructure: how the loop self-regulates, how it detects when something has changed, and how it decides when "good enough" is good enough and stops early.

**Self-tuning control**

A PID controller (the same feedback mechanism used in thermostats and autopilots) watches a quality metric over time and adjusts agent parameters to keep it stable:

- `loop-pid.py` — the main PID controller. Watches a rolling quality score (compaction distortion, skill routing accuracy, or eval scores) and automatically adjusts compaction depth or other parameters to bring the metric back to target when it drifts
- `loop-pid-cron-step.py` / `loop-pid-iss-wrapper.py` / `loop-pid-synthetic-step.py` — a scheduled version that runs the PID step as a cron job; a stability wrapper that guarantees the controller doesn't amplify disturbances; and a synthetic test harness to validate the controller before connecting it to real data
- `pid-circle-criterion.py` — a formal stability check on the PID loop: verifies that the controller will actually converge rather than oscillate or diverge
- `pid-passivity-index.py` — a complementary stability metric that measures how "energy absorbing" the control loop is; negative passivity means the loop could become unstable

**Detecting when things change**

CUSUM (Cumulative Sum) is a statistical algorithm for detecting changes in a data stream — it's sensitive to small persistent shifts that would be invisible in any single measurement:

- `loop-cusum-changepoint.py` — the main changepoint detector. Watches quality metrics and flags when a genuine shift has occurred (e.g. a skill has degraded, a model has changed, compaction quality has dropped). Includes a bug fix for a freeze condition in the original implementation where the detector would stop updating after the internal buffer filled.
- `cusum-h-calibrator.py` — calibrates the detection threshold automatically from historical data, so the detector is neither too sensitive (many false alarms) nor too slow (misses real changes)
- `cusum-gain-freeze.py` — suppresses false alarms that occur specifically when the gain (sensitivity) of the detector itself is changed, since that change triggers an apparent shift in the signal
- `conformal-changepoint-detector.py` — an alternative changepoint detector based on conformal prediction, which provides statistical guarantees on the false alarm rate
- `rolling-conformal-predictor.py` — computes rolling confidence intervals on quality metrics using conformal prediction; flags turns where the metric falls outside expected bounds

**Knowing when to stop early**

The "anytime" framework (from AI planning research) produces the best available result at any point, improving quality if given more time but always ready to return something useful immediately:

- `anytime-eval-feeder.py` — submits evaluation jobs to a queue and tracks which are most time-sensitive; prioritises jobs that need results before the next scheduled decision point
- `anytime-nspi-evaluator.py` — scores the quality of agent outputs on a normalised scale (Normalised Score Per Instruction); used to decide when a result is good enough to stop iterating
- `anytime-skill-evaluator.py` — builds a quality-vs-time profile for each skill (how much does quality improve if we let the skill run longer?); used to allocate time budgets
- `anytime-quality-monitor.py` — watches the overall session quality trend and raises an alarm if quality is declining rather than improving over time
- `loop-rollout-horizon.py` — decides how far ahead to plan (how many turns of reasoning to simulate) based on the anytime quality profiles; stops planning when further lookahead yields diminishing returns
- `loop-model-comparison.py` — runs side-by-side comparisons of different models over rolling time windows and reports which is performing better for the current type of work

---

### 5. Safety, alignment, and governance

A collection of hardening measures that run alongside the agent's normal operation. The goal is to catch cases where the agent is about to do something harmful, ineffective, or inconsistent with its stated principles — and either block it, log it, or raise an alarm.

**Making tool use safer**

The upstream approval system already asks for confirmation before running risky commands. The fork tightens it further:

- `tools/threat_patterns.py` — the list of patterns the approval system uses to flag risky tool calls. The fork removed 48 patterns that were triggering false positives on completely legitimate operations (e.g. reading files, running tests) and added 4 new patterns that target actual prompt injection vectors that the original list missed.
- `tools/approval.py` — the grant allowlist (operations pre-approved without prompting) was incorrectly restored in an upstream merge. The fork re-tightens it and fixes a path in the multi-step tool chain scanner that could be bypassed by chaining certain tool calls together.
- `tool-auth-gate` plugin — randomly samples tool calls that involve external services and verifies that the authentication tokens being used are what they're supposed to be; not a comprehensive check on every call, but catches drift and misconfiguration
- `tool-result-audit` plugin — when a tool returns content from an external source (web pages, files, API responses), this plugin scans the result for prompt injection patterns before the agent sees it
- `browser_act_guard.py` — monitors browser tool activity and blocks actions that look like the browser session is being hijacked or used outside its intended scope
- `browser_orphan_watchdog.sh` — periodically checks for browser processes that were spawned by the agent but have been abandoned (session ended, browser didn't clean up) and kills them
- `mcp-privilege-audit.py` — audits connected MCP (Model Context Protocol) servers to verify they're not claiming more permissions than they were granted

**Governance and behavioural consistency**

These scripts check that the agent is behaving consistently with its own stated principles and plans:

- `governance-hard-block` plugin — the most aggressive safety plugin: checks every tool call against a set of policy rules before dispatch. If a rule is violated, the tool call is blocked (not just logged). Fail-closed on blocking rules.
- `governance-conflict-detector.py` — checks for contradictions in the governance rules themselves (e.g. two rules that give opposite instructions for the same situation)
- `governance-conflict-epistemic.py` — a variant that also flags cases where the right action is genuinely ambiguous given the current rules, rather than just outright contradictory
- `governance-falsifiability-lint.py` — checks that every governance rule is falsifiable — i.e. that there exist situations that would violate it. Rules that can never be violated are useless (they don't actually constrain anything).
- `soares-halt-liveness.py` — a liveness check inspired by MIRI's corrigibility work: verifies that the agent can always be stopped cleanly and that there are no decision loops that would prevent halting
- `ltl-promotion-invariant.py` — checks that memory promotion (elevating facts to long-term store) satisfies temporal logic invariants: once something is promoted, certain properties about it must remain true in future states
- `plan-enforcement-gate.py` / `plan-commitment.py` — when the agent commits to a multi-step plan, these scripts track whether subsequent actions are consistent with that plan and flag deviations
- `iss-justification-gate.py` — checks that every significant agent decision comes with a justification that's input-to-state stable: the justification can't switch from "I'm doing X because of Y" to "I'm doing X because of Z" mid-task without an explicit reason

**COBRA guard** (`cobra-guard` plugin)

COBRA tracks the outcome of every significant agent decision and builds a history. If the same type of decision has failed multiple times in a row, the guard blocks the agent from making that decision again without escalating — preventing it from repeating known-bad patterns.

- `cobra-outcome-logger.py` — records decision outcomes to the COBRA history
- `cobra-skip-guard.py` — checks whether the current decision matches a blocked pattern and enforces the skip

**Adversarial robustness testing**

Periodically probes the agent's behaviour with adversarial inputs to find weaknesses before they're exploited in real use:

- `adversarial-robustness-tester.py` — runs a battery of adversarial prompts against the agent (prompt injection attempts, instruction confusion, role-play jailbreaks) and logs failures
- `adversarial_quarantine_review.py` — when a session is flagged as potentially adversarial, this script reviews the transcript and decides whether to quarantine it for manual inspection
- `adversarial-allocation-auditor.py` — checks that the adversarial test suite is covering all decision types proportionally; flags gaps where certain operations have never been tested adversarially

**Statistical gates for alignment claims**

These scripts apply sequential hypothesis testing (a statistical method that decides "have we seen enough evidence to be confident?") to alignment-related claims:

- `shadow-gate-sprt.py` — runs a parallel "shadow" version of the agent and uses sequential testing to check whether the main agent's behaviour has drifted away from the shadow. Runs the full test nightly.
- `shadow-gate-nightly.py` — the nightly batch pass that runs the shadow gate across the previous day's sessions
- `sprt-falsifiability-handshake.py` — before running a statistical test, verifies that the claim being tested is actually falsifiable (a test on an unfalsifiable claim is meaningless)
- `sprt-inner-outer-alignment.py` — checks for inner/outer alignment gaps: does the agent's behaviour during evaluation match its behaviour when not being evaluated?
- `sprt-measurement-tamper.py` — checks whether the measurement process itself is being gamed; flags sessions where the agent's behaviour changes suspiciously when it's being observed
- `sprt-truncation-gate.py` — prevents statistical tests from running on incomplete evidence (truncated session logs), which would produce unreliable results

---

### 6. Uncertainty estimation and evaluation

Before the agent stores a memory or routes to a skill, it's worth asking: how confident is it in that decision? Upstream has no built-in uncertainty awareness — it treats all outputs as equally reliable. This fork adds a layer of uncertainty estimation that gates certain operations on confidence, and a broader evaluation scaffold for measuring agent quality statistically.

**How confident is the agent in this output?**

Uncertainty estimation (UE) assigns a confidence score to model outputs. The fork uses it to gate memory commits, flag potentially hallucinated tool results, and avoid routing to skills when the routing confidence is low.

- `ue-blackbox-scorer.py` — estimates uncertainty from the outside: uses multiple sampling runs and measures how much the outputs disagree with each other. Works with any model, doesn't need access to internal probability scores.
- `ue-calibration-bridge.py` — takes raw uncertainty scores and calibrates them against historical accuracy, so "80% confident" actually means the agent is right about 80% of the time
- `ue-memory-gate.py` — before saving a fact to long-term memory, checks the uncertainty score. High-uncertainty facts (e.g. from a tool call that produced inconsistent results) are held back or flagged for review rather than committed as ground truth.
- `ue-perplexity-proxy.py` — for models that don't expose token probabilities, uses the model's own perplexity estimate (how "surprised" it is by its output) as a rough uncertainty proxy
- `ue-semantic-density.py` — measures how information-dense a piece of text is; sparse, repetitive outputs are often lower-quality and are assigned higher uncertainty
- `ue-semantic-graph.py` — builds a graph of concepts mentioned in a response and checks whether they're internally consistent; outputs with many disconnected or contradictory concepts get higher uncertainty scores
- `uncertainty-calibration-monitor.py` — tracks whether the calibration of uncertainty estimates is drifting over time (e.g. after a model change), and alerts when recalibration is needed
- `reasoning-ue-integrator.py` — integrates uncertainty scores from individual steps in a reasoning chain, so a chain where every intermediate step is uncertain gets flagged even if the final answer looks confident

**Statistical evaluation**

For measuring whether changes to the agent (new routing weights, new compaction settings, etc.) actually improve things:

- `block-bootstrap-sprt.py` — a statistically rigorous comparison tool: runs block bootstrap resampling combined with sequential hypothesis testing to determine whether two agent configurations are genuinely different, accounting for the autocorrelation in conversation-level metrics
- `eval-routing-linucb-features.py` — feeds evaluation outcomes back into the routing bandit as contextual features, closing the loop between evaluation and routing
- `hallucination-detector.py` — specifically for tool outputs: when a tool returns factual content (web search results, database queries), this checks whether the agent's summary of that content introduced facts that weren't in the original
- `step-level-prm-scorer.py` — scores each intermediate step in a multi-step reasoning chain rather than just the final output; catches errors that look fine in the final answer but arose from a bad intermediate step
- `step-level-trajectory-auditor.py` — audits full session trajectories step by step, checking for compounding errors, unnecessary tool calls, and goal drift over long conversations
- `circuit-trajectory-scorer.py` — checks whether the sequence of tool calls in a session matches expected "circuit" patterns for the declared task type; deviations from expected patterns are flagged

---

### 7. Cost and compute governance

Running a capable AI agent can get expensive fast — especially when it spawns subagents, runs many tool calls, or uses expensive models for simple tasks. This section covers the fork's cost controls: how it decides which model to use, when to spawn additional agents, and how to stay within budget without sacrificing quality.

**Picking the right model for the task**

Not every task needs the most expensive model. These scripts route tasks to the cheapest model that can handle them:

- `dcr-compute-router.py` / `dcr-reconcile.py` — a dual compute router: one route for high-complexity tasks, one for simple ones. After routing decisions are made, a reconciliation pass checks whether the routing assignments were actually correct based on outcome.
- `cost-cutoff-task-router.py` — if a task's estimated cost exceeds a threshold, automatically downroutes it to a cheaper model
- `pareto-phase-router.py` — finds the point on the quality-vs-cost frontier that maximises quality within a cost budget; not just "cheapest model" but "best value"
- `triple-objective-frontier-router.py` — extends the Pareto router to three dimensions: quality, cost, and response latency. Useful when latency matters as much as cost (e.g. interactive sessions vs. background jobs).
- `real-options-deployment-gate.py` — treats model upgrades as real options (a finance concept): wait to upgrade until you've accumulated enough evidence that the new model is worth the cost increase, rather than upgrading immediately on release

**Keeping spending within bounds**

- `token-budget-controller.py` — enforces a hard token budget per session; when the budget is close to exhausted, it restricts the agent to lighter operations and prevents spawning new subagents
- `cascade-error-budget-allocator.py` — when a tool call fails and needs to be retried, allocates the retry budget across the tool cascade proportionally to each tool's historical failure rate
- `relay-routing-capacity-allocator.py` — when routing tasks through a chain of models (e.g. a lightweight model for classification, a heavier one for generation), allocates capacity based on predicted demand
- `feedback-budget-optimizer.py` — optimises how much compute to spend on the evaluation feedback loop (how often to run quality checks, how many samples to use) given the remaining session budget
- `cost-aware-escalation.py` / `cost-aware-eval-framework.py` — before escalating a task to a more expensive model or running a full evaluation pass, checks whether the expected quality improvement justifies the cost

**Scaling up and down**

- `llm-autoscaler.py` — dynamically adjusts how many parallel subagents to run based on the current task queue depth and the remaining cost budget; scales up when there's work to parallelize and budget to spend, scales down when either runs low
- `spawning-utility-estimator.py` — before spawning a subagent, estimates whether the expected quality improvement from parallelisation actually justifies the overhead cost of spawning it; prevents reflexive fan-out
- `campaign-scorer.py` — when the fork is running model A/B experiments (comparing two routing configurations or model choices), this aggregates the per-session scores into campaign-level statistics and declares a winner when enough data has accumulated

---

### 8. Data versioning (Dolt-inspired)

Dolt is a database that works like Git — you can branch, merge, and diff your data the same way you do with code. The fork borrows two of Dolt's core ideas and implements them on top of SQLite (without needing the Dolt binary):

**Three-way merge for structured data** (`dolt-merge.py`)

The agent's job configuration (`jobs.json`) can be written by multiple cron processes simultaneously. Without a proper merge strategy, concurrent writes corrupt the file. This script implements the same merge algorithm Git uses for code, applied to rows of structured data:

- Each record is identified by a unique key (like a primary key in a database)
- If two processes both changed different records, their changes are automatically combined — no conflict
- If two processes both changed the same field on the same record, that's flagged as a conflict and must be resolved explicitly — no silent last-write-wins behaviour
- Conflicts record exactly what the original value was, what each side changed it to, and can be resolved by picking either side
- Used for safe concurrent updates to `jobs.json` from multiple cron workers

**Change history and blame** (`lifecycle-changelog.py`)

Adds Git-style history tracking to the agent's SQLite database — without touching any existing tables:

- Every change to any tracked record gets a commit entry: what changed, when, and from which process
- `get_history()` — returns the full change log for any record
- `time_travel()` — reconstructs what a record looked like at any point in the past by replaying the change history up to a given commit
- `blame()` — identifies which commit last changed a specific field on a specific record; like `git blame` but for database rows
- Read operations use a read-only database connection, so querying history never accidentally triggers a write

---

### 9. System maintenance and infrastructure

Practical plumbing that keeps the fork running reliably day-to-day on a Fedora Silverblue (immutable Linux) system.

**Automated system updates** (`daily-silverblue-update.sh`)

The upstream system update script had no per-step timeouts, so a single slow mirror or a large Flatpak update would cause the entire job to time out after 3+ hours, triggering false failure alerts. The fork adds:

- Individual timeouts for each update step: package manager (20 minutes), firmware updates (5 minutes), each Git repository sync (1 minute each)
- Flatpak app store metadata errors are now treated as non-fatal — a slow mirror failing to update its metadata doesn't block the whole update
- A login-trigger variant for update steps that require an active desktop session (some firmware tools won't run headless)

**Cron job management**

Over 100 scheduled jobs run on this installation, covering everything from nightly memory health checks to hourly compaction quality scores to weekly skill index rebuilds. Supporting infrastructure:

- `cron-sandbox-runner.py` — wraps every cron script in an openshell security sandbox that restricts which files the script can read and write; scripts that try to access paths outside their declared scope are blocked
- `cron-admission-control.py` — when the system is under load, drops low-priority scheduled jobs rather than letting them queue up; prevents a backlog of deferred jobs from all running at once when the system recovers
- The skill index weekly rebuild was silently broken (it was running but not actually regenerating the index because a required flag was missing); fixed
- The environment variable `HERMES_NO_SANDBOX=1` (which would bypass the security sandbox) is explicitly blocked in the cron wrapper; attempts to set it are logged and ignored

**Security monitoring**

- `firewall-port-audit.sh` — periodically checks the system firewall rules against a known-good baseline and alerts on unexpected open ports
- `sysctl-verify.sh` — checks kernel security settings (network hardening, memory protection flags) against expected values after every system update
- `mcp-auth-drift-check.py` — checks whether the authentication configuration for connected MCP servers has changed since it was last reviewed; flags new permissions that weren't explicitly approved
- `secure-message.py` — utility for signing and verifying messages between agent components, used by the cron sandbox to verify that scripts haven't been tampered with

**Sandbox policy**

`openshell-policy.yaml` defines which files each cron script is allowed to read or write. The fork maintains a clean separation: files are either read-only or read-write, never listed in both categories. Attempts to bypass the sandbox are logged to a separate audit file and the script is terminated.

---

## Plugin summary

Plugins hook into the agent's event stream and run automatically on every matching event. All plugins listed here are fail-open — if a plugin crashes or times out, the agent continues normally rather than blocking.

| Plugin | When it runs | What it does |
|---|---|---|
| `jev-compaction` | Before context compression | Scores the importance of each context segment; blocks compression if too much high-importance content would be lost |
| `compaction-gate` | Before context compression | Blocks compression if the information saving doesn't meet a minimum threshold — prevents compressing when it's not worth it |
| `jev-turn-evaluator` | After every model response | Runs the response through a secondary model to score quality; feeds scores into the routing bandit; blocks policy updates until a minimum number of scored turns has accumulated |
| `governance-hard-block` | Before every tool call | Checks the tool call against a policy rulebook; blocks calls that violate any rule (the only fail-closed plugin) |
| `cobra-guard` | After every tool call | Records the outcome; if the same type of decision has failed repeatedly, blocks future attempts of that type until manually reviewed |
| `tool-auth-gate` | After every tool call | Randomly audits whether the authentication tokens used in tool calls match what they're supposed to be |
| `tool-result-audit` | After every tool call | Scans content returned from external tools (web pages, APIs, files) for prompt injection patterns before the agent sees it |
| `memory-ransac-gate` | After every tool call | Before committing new information to memory, checks it against existing memories and rejects it if it looks like an outlier inconsistent with established facts |
| `context-pressure-guard` | After every tool call | Monitors how full the context window is; raises an alarm when it's close to the limit so the agent can decide whether to compact proactively |
| `decision-audit` | After every tool call | Tracks whether tool calls are resolving successfully or stalling; writes a summary to the lifecycle database every 10 calls |
| `delegation-audit-hook` | After every tool call | When the agent spawns a subagent, records the delegation outcome (did it succeed? how long did it take?) for performance tracking |
| `deductive-verifier` | After every model response | Checks the logical structure of the agent's reasoning: are conclusions actually supported by the stated premises? |
| `formal-verify-plugin` | After every tool call | For tool calls that claim to verify a proof or formal property, enforces that the proof state is maintained correctly through the call |
| `compliance-score-hook` | After every tool call | Scores tool outputs for compliance red flags (sensitive data, excessive length, policy violations) and writes scores to a log |
| `post-tool-compliance` | After every tool call | A parallel, observation-only compliance scorer that runs independently from `compliance-score-hook` for cross-checking; never blocks anything |
| `turn-behavior-logger` | After every model response | Logs behavioural metrics for each turn: response length, tool call count, compaction events, model used |
| `hindsight` | Multiple lifecycle events | Manages long-term memory using a knowledge graph with entity resolution — the main memory backend for structured facts across sessions |
| `adaptive-retrieval` | On memory retrieval | Selects the best retrieval strategy (keyword search, semantic search, graph traversal) based on the type of query |
| `billion-context` | On context compression | Handles extremely long contexts (approaching the model's context limit) using a specialised compression method designed for very large inputs |
| `skill-access-logger` | On skill access | Records every skill access with a fingerprint of the query that triggered it and the outcome, for routing analysis |
| `skill-routing-nudge` | On skill access | If the routing confidence for the selected skill falls below a threshold mid-turn, adds a nudge to the agent to reconsider whether this skill is the right one |
| `skill-latency-logger` | On skill access | Records how long each skill takes to load and use; identifies slow skills that add latency |
| `su-observability` | Multiple lifecycle events | Collects system-level observability metrics (memory usage, response times, queue depths) for the monitoring dashboard |
| `orca-status` | Lifecycle events | Reports agent lifecycle events (startup, shutdown, session start, session end) to an external monitoring service |
| `camofox` | Browser tool calls | Provides a stealth browser backend with enhanced fingerprint evasion for web scraping tasks where standard browser detection would block access |

---

## Upstream merge policy

This fork rebases or merges from `NousResearch/hermes-agent` main periodically. Conflicts are resolved in favour of upstream on the core agent loop; fork additions win on scripts and plugins.

**Current base:** See `git log --oneline upstream/main..HEAD` for fork-only commits.

---

## Running this fork

Same as upstream, with the `fork` profile active:

```bash
hermes-fork          # start CLI on the fork profile
hermes-fork doctor   # health check
hermes-fork -z       # fork profile with zero context (fresh session)
```

The fork profile lives at `~/.hermes/profiles/fork/`. The binary at `~/.local/bin/hermes-fork` pins to the Py3.14 store interpreter (not `venv/bin/hermes` 3.11 — pydantic_core ABI mismatch).

---

## What is NOT different from upstream

- Installation procedure, model provider support, MCP integration, messaging gateway, TUI/CLI interface

For anything not covered here: **[hermes-agent.nousresearch.com/docs](https://hermes-agent.nousresearch.com/docs/)**

---

## Original upstream README

Everything below is the original Hermes Agent README.

---

<p align="center">
  <img src="assets/banner.png" alt="Hermes Agent" width="100%">
</p>

# Hermes Agent ☤
<p align="center">
  <a href="https://hermes-agent.nousresearch.com/">Hermes Agent</a> | <a href="https://hermes-agent.nousresearch.com/">Hermes Desktop</a>
</p>
<p align="center">
  <a href="https://hermes-agent.nousresearch.com/docs/"><img src="https://img.shields.io/badge/Docs-hermes--agent.nousresearch.com-FFD700?style=for-the-badge" alt="Documentation"></a>
  <a href="https://discord.gg/NousResearch"><img src="https://img.shields.io/badge/Discord-5865F2?style=for-the-badge&logo=discord&logoColor=white" alt="Discord"></a>
  <a href="https://github.com/NousResearch/hermes-agent/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License: MIT"></a>
  <a href="https://nousresearch.com"><img src="https://img.shields.io/badge/Built%20by-Nous%20Research-blueviolet?style=for-the-badge" alt="Built by Nous Research"></a>
  <a href="README.zh-CN.md"><img src="https://img.shields.io/badge/Lang-中文-red?style=for-the-badge" alt="中文"></a>
  <a href="README.ur-pk.md"><img src="https://img.shields.io/badge/Lang-اردو-green?style=for-the-badge" alt="اردو"></a>
  <a href="README.es.md"><img src="https://img.shields.io/badge/Lang-Español-orange?style=for-the-badge" alt="Español"></a>
</p>

**The self-improving AI agent built by [Nous Research](https://nousresearch.com).** It's the only agent with a built-in learning loop — it creates skills from experience, improves them during use, nudges itself to persist knowledge, searches its own past conversations, and builds a deepening model of who you are across sessions. Run it on a $5 VPS, a GPU cluster, or serverless infrastructure that costs nearly nothing when idle. It's not tied to your laptop — talk to it from Telegram while it works on a cloud VM.

Use any model you want — [Nous Portal](https://portal.nousresearch.com), OpenRouter, OpenAI, your own endpoint, and [many others](https://hermes-agent.nousresearch.com/docs/integrations/providers). Switch with `hermes model` — no code changes, no lock-in.

<table>
<tr><td><b>A real terminal interface</b></td><td>Full TUI with multiline editing, slash-command autocomplete, conversation history, interrupt-and-redirect, and streaming tool output.</td></tr>
<tr><td><b>Lives where you do</b></td><td>Telegram, Discord, Slack, WhatsApp, Signal, and CLI — all from a single gateway process. Voice memo transcription, cross-platform conversation continuity.</td></tr>
<tr><td><b>A closed learning loop</b></td><td>Agent-curated memory with periodic nudges. Autonomous skill creation after complex tasks. Skills self-improve during use. FTS5 session search with LLM summarization for cross-session recall. <a href="https://github.com/plastic-labs/honcho">Honcho</a> dialectic user modeling. Compatible with the <a href="https://agentskills.io">agentskills.io</a> open standard.</td></tr>
<tr><td><b>Scheduled automations</b></td><td>Built-in cron scheduler with delivery to any platform. Daily reports, nightly backups, weekly audits — all in natural language, running unattended.</td></tr>
<tr><td><b>Delegates and parallelizes</b></td><td>Spawn isolated subagents for parallel workstreams. In Desktop, choose their provider, model, and limits under Settings → Model → Subagents, then Apply the complete route. Write Python scripts that call tools via RPC, collapsing multi-step pipelines into zero-context-cost turns.</td></tr>
<tr><td><b>Runs anywhere, not just your laptop</b></td><td>Six built-in terminal backends — local, Docker, SSH, Modal, Daytona, and Vercel Sandbox — plus plugin backends such as Singularity/Apptainer. Daytona and Modal offer serverless persistence — your agent's environment hibernates when idle and wakes on demand, costing nearly nothing between sessions. Run it on a $5 VPS or a GPU cluster.</td></tr>
<tr><td><b>Research-ready</b></td><td>Batch trajectory generation, trajectory compression for training the next generation of tool-calling models.</td></tr>
</table>

---

## Quick Install

### Linux, macOS, WSL2

```bash
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
```

### Windows (native, PowerShell)

> **Heads up:** Native Windows runs Hermes without WSL — CLI, gateway, TUI, and tools all work natively. If you'd rather use WSL2, the Linux/macOS one-liner above works there too. Found a bug? Please [file issues](https://github.com/NousResearch/hermes-agent/issues).

Run this in PowerShell:

```powershell
iex (irm https://hermes-agent.nousresearch.com/install.ps1)
```

The source installer delegates Python 3.14, Node.js, npm, pnpm, ripgrep, FFmpeg,
and Python dependencies to PM. If Git is absent, it stages the verified Git
for Windows archive in Hermes' tool store. It does not replace your system Git.
See [installation methods](https://hermes-agent.nousresearch.com/docs/getting-started/installation)
for the separate MSIX/App Installer package and its update ownership.

> **Android / Termux:** A signed APT repository is available for aarch64 devices, with a `stable` channel (tagged releases) and a prerelease `canary` channel. The package includes Python, Node.js, and the TUI. Use the [Termux guide](https://hermes-agent.nousresearch.com/docs/getting-started/termux), not the desktop/server installer script.
>
> **Windows:** Native Windows is fully supported — the PowerShell one-liner above installs everything. If you'd rather use WSL2, the Linux command works there too. Native Windows install lives under `%LOCALAPPDATA%\hermes`; WSL2 installs under `~/.hermes` as on Linux.

After installation:

```bash
source ~/.bashrc    # reload shell (or: source ~/.zshrc)
hermes              # start chatting!
```

### Troubleshooting

#### Windows Defender or antivirus flags `uv.exe` as malware

If your antivirus (Bitdefender, Windows Defender, etc.) quarantines `uv.exe` from the Hermes `bin` folder (`%LOCALAPPDATA%\hermes\bin\uv.exe`), this is a **false positive**. The file is Astral's `uv` — the Rust Python package manager Hermes bundles to manage its Python environment. ML-based antivirus engines commonly flag unsigned Rust binaries that download and install packages.

**To verify your copy is authentic:**

```powershell
# Install GitHub CLI if needed
winget install --id GitHub.cli

# Login to GitHub
gh auth login

# Run verification
$uv = "$env:LOCALAPPDATA\hermes\bin\uv.exe"
$ver = (& $uv --version).Split(' ')[1]
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$zip = "$env:TEMP\uv.zip"
Invoke-WebRequest "https://github.com/astral-sh/uv/releases/download/$ver/uv-x86_64-pc-windows-msvc.zip" -OutFile $zip -UseBasicParsing
gh attestation verify $zip --repo astral-sh/uv
Expand-Archive $zip "$env:TEMP\uv_x" -Force
(Get-FileHash "$env:TEMP\uv_x\uv.exe").Hash -eq (Get-FileHash $uv).Hash
```

If attestation says "Verification succeeded" and the last line prints `True`, you're good.

**To whitelist Hermes:**
- **Windows Defender:** Run PowerShell as Admin → `Add-MpPreference -ExclusionPath "$env:LOCALAPPDATA\hermes\bin"`
- **Bitdefender:** Add an exception in the Bitdefender console (Protection > Antivirus > Settings > Manage Exceptions)
- Whitelist the **folder**, not the file hash — Hermes updates `uv` and the hash changes every version

For more context, see the upstream Astral reports: [astral-sh/uv#13553](https://github.com/astral-sh/uv/issues/13553), [astral-sh/uv#15011](https://github.com/astral-sh/uv/issues/15011), [astral-sh/uv#10079](https://github.com/astral-sh/uv/issues/10079).

---

## Getting Started

```bash
hermes              # Interactive CLI — start a conversation
hermes model        # Choose your LLM provider and model
hermes tools        # Configure which tools are enabled
hermes config set   # Set individual config values
hermes config get   # Print individual config values
hermes gateway      # Start the messaging gateway (Telegram, Discord, etc.)
hermes setup        # Run the full setup wizard (configures everything at once)
hermes update       # Update to the latest version
hermes doctor       # Diagnose any issues
```

📖 **[Full documentation →](https://hermes-agent.nousresearch.com/docs/)**

---

## Skip the API-key collection — Nous Portal

Hermes works with whatever provider you want — that's not changing. But if you'd rather not collect five separate API keys for the model, web search, image generation, TTS, and a cloud browser, **[Nous Portal](https://portal.nousresearch.com)** covers all of them under one subscription:

- **300+ models** — pick any of them with `/model <name>`
- **Tool Gateway** — web search, image generation (FAL), text-to-speech (OpenAI), cloud browser (Browser Use), all routed through your sub. No extra accounts.

One command from a fresh install:

```bash
hermes setup --portal
```

That logs you in via OAuth, sets Nous as your provider, and turns on the Tool Gateway. Check what's wired up any time with `hermes portal info`. Full details on the [Tool Gateway docs page](https://hermes-agent.nousresearch.com/docs/user-guide/features/tool-gateway).

You can still bring your own keys per-tool whenever you want — the gateway is per-backend, not all-or-nothing.

---

## CLI vs Messaging Quick Reference

Hermes has two entry points: start the terminal UI with `hermes`, or run the gateway and talk to it from Telegram, Discord, Slack, WhatsApp, Signal, or Email. Once you're in a conversation, many slash commands are shared across both interfaces.

| Action                         | CLI                                           | Messaging platforms                                                              |
| ------------------------------ | --------------------------------------------- | -------------------------------------------------------------------------------- |
| Start chatting                 | `hermes`                                      | Run `hermes gateway setup` + `hermes gateway start`, then send the bot a message |
| Start fresh conversation       | `/new` or `/reset`                            | `/new` or `/reset`                                                               |
| Change model                   | `/model [provider:model]`                     | `/model [provider:model]`                                                        |
| Set a personality              | `/personality [name]`                         | `/personality [name]`                                                            |
| Retry or undo the last turn    | `/retry`, `/undo`                             | `/retry`, `/undo`                                                                |
| Compress context / check usage | `/compress`, `/usage`, `/insights [--days N]` | `/compress`, `/usage`, `/insights [days]`                                        |
| Browse skills                  | `/skills` or `/<skill-name>`                  | `/<skill-name>`                                                                  |
| Interrupt current work         | `Ctrl+C` or send a new message                | `/stop` or send a new message                                                    |
| Platform-specific status       | `/platforms`                                  | `/status`, `/sethome`                                                            |

For the full command lists, see the [CLI guide](https://hermes-agent.nousresearch.com/docs/user-guide/cli) and the [Messaging Gateway guide](https://hermes-agent.nousresearch.com/docs/user-guide/messaging).

---

## Documentation

All documentation lives at **[hermes-agent.nousresearch.com/docs](https://hermes-agent.nousresearch.com/docs/)**:

| Section                                                                                             | What's Covered                                             |
| --------------------------------------------------------------------------------------------------- | ---------------------------------------------------------- |
| [Quickstart](https://hermes-agent.nousresearch.com/docs/getting-started/quickstart)                 | Install → setup → first conversation in 2 minutes          |
| [CLI Usage](https://hermes-agent.nousresearch.com/docs/user-guide/cli)                             | Commands, keybindings, personalities, sessions             |
| [Configuration](https://hermes-agent.nousresearch.com/docs/user-guide/configuration)               | Config file, providers, models, all options                |
| [Messaging Gateway](https://hermes-agent.nousresearch.com/docs/user-guide/messaging)               | Telegram, Discord, Slack, WhatsApp, Signal, Home Assistant |
| [Security](https://hermes-agent.nousresearch.com/docs/user-guide/security)                         | Command approval, DM pairing, container isolation          |
| [Tools & Toolsets](https://hermes-agent.nousresearch.com/docs/user-guide/features/tools)           | 40+ tools, toolset system, terminal backends               |
| [Skills System](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills)             | Procedural memory, Skills Hub, creating skills             |
| [Memory](https://hermes-agent.nousresearch.com/docs/user-guide/features/memory)                    | Persistent memory, user profiles, best practices           |
| [MCP Integration](https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp)              | Connect any MCP server for extended capabilities           |
| [Cron Scheduling](https://hermes-agent.nousresearch.com/docs/user-guide/features/cron)             | Scheduled tasks with platform delivery                     |
| [Context Files](https://hermes-agent.nousresearch.com/docs/user-guide/features/context-files)      | Project context that shapes every conversation             |
| [Architecture](https://hermes-agent.nousresearch.com/docs/developer-guide/architecture)            | Project structure, agent loop, key classes                 |
| [Contributing](https://hermes-agent.nousresearch.com/docs/developer-guide/contributing)            | Development setup, PR process, code style                  |
| [CLI Reference](https://hermes-agent.nousresearch.com/docs/reference/cli-commands)                 | All commands and flags                                     |
| [Environment Variables](https://hermes-agent.nousresearch.com/docs/reference/environment-variables)| Complete env var reference                                 |

---

## Migrating from OpenClaw or another agent

If you're coming from OpenClaw, Claude Code, Codex CLI or Cursor, Hermes can import your settings, memories and skills (and, for OpenClaw, API keys when you ask for them).

**During setup:** `hermes setup` asks whether to import from another agent, pre-selects the ones it finds (`~/.openclaw`, `~/.claude`, `~/.codex`, `~/.cursor`), installs the official `agent-importers` plugin and runs the import with a preview first.

**Anytime after install:**

```bash
hermes plugins install agent-importers          # once per profile
hermes import-agent openclaw                    # interactive migration (full preset)
hermes import-agent openclaw --dry-run          # preview what would be migrated
hermes import-agent openclaw --migrate-secrets  # also bring allowlisted API keys
hermes import-agent claude-code                 # or codex / cursor
```

What gets imported from OpenClaw:

- **SOUL.md** — persona file
- **Memories** — MEMORY.md and USER.md entries
- **Skills** — user-created skills → `~/.hermes/skills/openclaw-imports/`
- **Command allowlist** — approval patterns
- **Messaging settings** — platform configs, allowed users, working directory
- **API keys** — allowlisted secrets (Telegram, OpenRouter, OpenAI, Anthropic, ElevenLabs), only with `--migrate-secrets`
- **TTS assets** — workspace audio files
- **Workspace instructions** — AGENTS.md (with `--workspace-target`)

`hermes claw migrate` still works as the older spelling. See the [OpenClaw migration guide](https://hermes-agent.nousresearch.com/docs/guides/migrate-from-openclaw) and [Import from Other Agents](https://hermes-agent.nousresearch.com/docs/user-guide/import-from-other-agents).

---

## Contributing

We welcome contributions! See the [Contributing Guide](https://hermes-agent.nousresearch.com/docs/developer-guide/contributing) for development setup, code style, and PR process.

Start with the [PM developer workflow](website/docs/reference/package-management.md#developer-workflow)
for activation, daily use, dependency changes, and leaving the environment.
[Development Setup](CONTRIBUTING.md#development-setup) covers the separate test environment and verification commands.

---

## Community

- 💬 [Discord](https://discord.gg/NousResearch)
- 📚 [Skills Hub](https://agentskills.io)
- 🐛 [Issues](https://github.com/NousResearch/hermes-agent/issues)
- 🔌 [computer-use-linux](https://github.com/avifenesh/computer-use-linux) — Linux desktop-control MCP server for Hermes and other MCP hosts, with AT-SPI accessibility trees, Wayland/X11 input, screenshots, and compositor window targeting.
- 🔌 [HermesClaw](https://github.com/AaronWong1999/hermesclaw) — Community WeChat bridge: Run Hermes Agent and OpenClaw on the same WeChat account.

---

## License

MIT — see [LICENSE](LICENSE).

Built by [Nous Research](https://nousresearch.com).
