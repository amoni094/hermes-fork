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

The fork's additions fall into nine areas. All extensions are additive (scripts, plugins, configuration) or bug fixes on upstream code. Plugins are fail-open unless noted.

---

### 1. Memory system

~65 scripts extending the upstream memory system with formal operations from information theory, signal processing, and statistics. These run as nightly/hourly cron jobs, not in the hot path.

**Retention and decay**
- `memory-ttl-purge.py` — time-to-live eviction with configurable floor
- `memory-ttl-floor-merge.py` — merges TTL policy with recency signal
- `memory-staleness.py` — staleness scoring against access history
- `memory-mixing-ttl.py` — Markov mixing time as TTL proxy
- `memory-hitting-time.py` — expected hitting time for rarely-accessed facts
- `memory-conductance-ttl.py` — graph conductance as retention weight
- `memory-access-decay.py` — exponential decay on access timestamps

**Compression and distortion**
- `memory-jl-distortion.py` — Johnson-Lindenstrauss projection distortion check on embeddings
- `memory-eckart-young.py` — low-rank approximation gate (Eckart-Young theorem)
- `memory-lp-dct-gate.py` — DCT energy compaction gate for text segments
- `memory-bits-back.py` — bits-back argument estimator for latent compression efficiency
- `memory-kraft-code.py` — Kraft inequality check on memory encoding
- `memory-haar-mra.py` — Haar multi-resolution analysis for temporal memory structure
- `memory-rough-signature.py` — rough path signature for sequential memory streams

**Retrieval and ranking**
- `memory-adaptive-rank.py` — online rank adjustment from access patterns
- `memory-query-router.py` — routes retrieval queries across backend strategies
- `memory-signature-rerank.py` — reranking via rough path signatures
- `memory-redundancy-gate.py` — blocks commits of near-duplicate facts
- `memory-dkw-ue.py` — Dvoretzky-Kiefer-Wolfowitz uncertainty envelope on retrieval scores
- `memory-sprt-commit.py` — SPRT-gated memory commit (stops accumulating when signal is clear)
- `memory-ransac-commit.py` — RANSAC inlier gate before committing facts to long-term store

**Graph and topology**
- `memory-ontology-topology.py` — topological analysis of the memory knowledge graph
- `memory-taxonomy-discover.py` — automated taxonomy discovery from memory clusters
- `memory-coupling-merge.py` — merges tightly coupled memory nodes
- `memory-relation-extractor.py` — extracts typed relations from free-text memories
- `memory-bethe-free-energy.py` — Bethe free energy on the memory factor graph
- `memory-doob-decompose.py` — Doob decomposition of memory value sequences
- `memory-portmanteau.py` — Ljung-Box portmanteau test for memory access autocorrelation

**Drift and anomaly**
- `memory-auto-improvement.py` — nightly self-improvement pass on memory quality
- `memory-gelman-shrink.py` — Gelman-Rubin shrinkage on multi-chain memory estimates
- `memory-kalman-latent.py` — Kalman filter on latent memory state
- `memory-wave18-adversarial.py` / `memory-wave18-invariants.py` — adversarial wave 18 memory invariants

**L1 memory stack** (separate pipeline from conversational memory)
- `l1-extract.py` / `l1-promote.py` — extract and promote high-value facts to L1
- `l1-graphiti-write.py` / `l1-graphiti-reconcile.py` — sync L1 facts to Graphiti knowledge graph
- `l1-gmemory-consolidation.py` — consolidate graph memory nodes
- `l1-hypermem-promote.py` — hypergraph memory promotion
- `l1-tracegrant.py` — TraceGrant provenance tracking for promoted facts
- `unified-recall.py` — unified recall interface over L1, Graphiti, and session search
- `dual-backend-memory-fuser.py` — fuses results from two memory backends
- `hindsight-reembed.py` / `hindsight-watchdog.py` — re-embed and monitor hindsight memory

---

### 2. Skill routing

~60 scripts implementing a multi-arm bandit skill routing layer on top of upstream's BM25-based retrieval. The goal is to learn which skills are actually useful given query context, not just lexically similar.

**Bandit algorithms**
- `routing-linucb.py` — LinUCB contextual bandit; updates on routing outcome
- `routing-kl-ucb.py` — KL-UCB arm selection for skill routing
- `routing-tsallis-inf.py` — Tsallis-INF algorithm for adversarial routing
- `routing-exp3-adversarial.py` / `routing-exp4-contextual.py` — EXP3/EXP4 for adversarial/contextual skill selection
- `routing-ips-offpolicy.py` — inverse propensity scoring for off-policy routing evaluation
- `routing-pac-bayes-bound.py` — PAC-Bayes generalisation bound on routing policy
- `routing-rademacher-bound.py` — Rademacher complexity bound on the routing model
- `routing-weight-updater.py` — online weight update dispatcher

**Concentration and monitoring**
- `routing-azuma-concentration.py` — Azuma-Hoeffding concentration check on routing rewards
- `routing-mcdiarmid-bm25.py` — McDiarmid inequality on BM25 score shifts
- `routing-fano-bound.py` — Fano lower bound on routing mutual information
- `routing-mutual-information.py` — MI between query features and skill selection
- `routing-convergence-guard.py` — detects routing non-convergence and raises alarm
- `routing-switching-detector.py` — CUSUM detection of routing regime switches
- `routing-alarm-bridge.py` / `wave21a-alarm-bridge.py` / `wave21c-alarm-bridge.py` — alarm aggregators across routing waves

**Graph and topology**
- `routing-skill-markov.py` — Markov chain model of skill transition patterns
- `routing-skill-percolation.py` — percolation threshold analysis of the skill graph
- `routing-graph-bandit-update.py` — graph-structured bandit updates
- `routing-graph-independence.py` — independence test on the routing graph
- `routing-boolean-influence.py` — Boolean influence analysis of routing features
- `routing-mobius-audit.py` — Möbius inversion audit of skill co-occurrence
- `routing-hamming-audit.py` — Hamming distance audit on routing decisions
- `routing-token-setcover.py` — set-cover routing for token budget allocation
- `routing-precision-recall.py` — routing precision/recall tracking

**Skill health and calibration**
- `skill-monitor.py` — CUSUM health monitor per skill; excludes degraded skills from routing
- `skill-lift-tracker.py` — lift metric: does routing a skill improve outcomes?
- `skill-variance-regularization.py` — regularises high-variance skill estimates
- `skill-disagreement-allocation.py` — Neyman allocation based on skill estimate disagreement
- `skill-imbalance-reweight.py` — reweights under-explored skills
- `skill_confidence_calibration.py` — calibration curves per skill
- `skill-hierarchical-routing.py` — hierarchical skill routing via category tree
- `bps-skill-selector.py` — BPS budget-aware skill selection
- `kl-skill-prior.py` — KL-divergence prior update on skill utility distribution
- `occam-skill-ranker.py` — Occam factor ranking (complexity-penalised skill utility)
- `soft-bellman-skill-router.py` — soft Bellman routing for stochastic skill selection
- `skill-admissibility.py` / `skill-dependency-verifier.py` / `skill-integrity-check.py` — skill graph health

**Index and plugins**
- `skill-router-index.py` — builds and updates the BM25+embedding routing index (255 skills)
- `skill-routing-table.py` / `skill-routing-bounds.py` — routing table management and PAC bounds
- `skill-access-logger` plugin — logs every skill access with query fingerprint and outcome
- `skill-routing-nudge` plugin — mid-turn nudge when routing confidence drops below threshold
- `skill-latency-logger` plugin — per-skill latency histogram

---

### 3. Compaction evaluation pipeline

Upstream compaction is a heuristic. The fork adds a multi-axis quality measurement pipeline that runs every compaction and nightly.

**JEV compaction** (`jev-compaction` plugin)
- Entropy-weighted context compaction using joint evaluation voting
- `pre-compact-annotate.py` — annotates context segments before compaction
- `jev_compaction.py` / `jev_verify_fn.py` — JEV scorer and verifier
- `jev-scores-staleness-check.py` — alarm if JEV scores haven't been updated

**Information-theoretic metrics**
- `compaction-aep-typical-set.py` — AEP typical set coverage (are compressed segments in the typical set?)
- `compaction-chain-rule-mi.py` — chain rule mutual information between pre/post compaction
- `compaction-rd-converse.py` — rate-distortion converse bound (lower bound on unavoidable distortion)
- `rd-compaction-advisor.py` — advises on optimal compaction depth given R-D tradeoff
- `eval-compaction-distortion-gate.py` — hard gate: reject compaction if distortion exceeds bound
- `eval-compaction-data-bridge.py` — bridges compaction scores to the eval pipeline
- `statecomp-compression-router.py` — StateComp span-readiness routing for compaction

**ROUGE scorer** (stdlib, no pip deps)
- `score-compaction-rouge.py` — ROUGE-1 (unigrams) and ROUGE-L (LCS) with:
  - Case-insensitive tokenisation
  - Sampled LCS for inputs >10k tokens (2500 from each end, denominators adjusted to sampled lengths)
  - `alarm_fabrication` if precision < 0.3; `alarm_coverage` if recall < 0.2
  - `--batch` mode for JSONL; `--self-test`; nightly cron at 04:50 → `cache/compaction-rouge-scores.jsonl`

**compaction-gate plugin**
- MDL-based gate: blocks compaction if `mdl_min_saving` not met at `depth_threshold`
- Settings explicitly declared in `config.yaml` (were silently using hardcoded defaults)

---

### 4. Loop control and anytime algorithms

**PID and control**
- `loop-pid.py` — PID controller on a quality metric; adjusts compaction depth or model temperature
- `loop-pid-cron-step.py` / `loop-pid-iss-wrapper.py` / `loop-pid-synthetic-step.py` — PID cron step, ISS (input-to-state stability) wrapper, synthetic test harness
- `pid-circle-criterion.py` — circle criterion passivity check on the PID loop
- `pid-passivity-index.py` — passivity index measurement

**CUSUM changepoint detection**
- `loop-cusum-changepoint.py` — CUSUM with ADV-022 ring-full freeze fix: when `n_seen == len(xs)`, resets S+/S− and re-runs over full ring rather than processing zero new samples
- `cusum-h-calibrator.py` — calibrates CUSUM threshold h* from calibration file
- `cusum-gain-freeze.py` — freeze-guard: suppresses false alarms during gain-change events
- `conformal-changepoint-detector.py` — conformal prediction variant for changepoint detection
- `rolling-conformal-predictor.py` — rolling conformal prediction intervals on quality metrics

**Anytime evaluation** (Zilberstein/Dean-Boddy anytime framework)
- `anytime-eval-feeder.py` — feeds evaluation jobs into the anytime queue
- `anytime-nspi-evaluator.py` — NSPI (Normalised Score Per Instruction) evaluator
- `anytime-skill-evaluator.py` — per-skill anytime quality profile
- `anytime-quality-monitor.py` — monitors quality vs. time tradeoff across the session
- `loop-rollout-horizon.py` — rollout horizon selection via anytime quality profile
- `loop-model-comparison.py` — A/B comparison across models over rolling windows

---

### 5. Safety, alignment, and governance

**Tool and approval hardening**
- `tools/threat_patterns.py` — refined threat pattern set: removed 48 false-positive patterns that were blocking legitimate tool uses, added 4 precision patterns for actual injection vectors
- `tools/approval.py` — restored and tightened grant allow-list; fixed scan-incomplete paths that could bypass approval on multi-step tool chains
- `tool-auth-gate` plugin — inspection-game strategy: probabilistically audits tool auth tokens
- `tool-result-audit` plugin — shadow post_tool_call: audits external-content tool results for prompt injection
- `browser_act_guard.py` / `browser_orphan_watchdog.sh` — guards against browser tool runaway and orphan processes
- `mcp-privilege-audit.py` — audits MCP server privilege assertions

**Governance and alignment**
- `governance-hard-block` plugin — hard-blocks policy violations before tool dispatch
- `governance-conflict-detector.py` / `governance-conflict-epistemic.py` — detects governance rule conflicts; epistemic variant flags uncertainty in conflict resolution
- `governance-falsifiability-lint.py` — lints governance rules for falsifiability (unfalsifiable rules are rejected)
- `soares-halt-liveness.py` — Soares halt/liveness invariant check on agent decisions
- `ltl-promotion-invariant.py` — LTL temporal logic invariant on memory promotion
- `plan-enforcement-gate.py` / `plan-commitment.py` — enforces plan commitments; blocks mid-plan policy drift
- `iss-justification-gate.py` — ISS (input-to-state stability) gate on agent justifications

**COBRA guard** (`cobra-guard` plugin)
- Tracks outcome of every agent decision; blocks repeat failures on the same decision type
- `cobra-outcome-logger.py` / `cobra-skip-guard.py` — outcome logging and skip-guard enforcement

**Adversarial robustness**
- `adversarial-robustness-tester.py` — periodic adversarial probing of agent responses
- `adversarial_quarantine_review.py` — quarantine review for flagged adversarial traces
- `adversarial-allocation-auditor.py` — Neyman allocation audit of adversarial test coverage

**SPRT-based gates** (sequential hypothesis testing)
- `shadow-gate-sprt.py` / `shadow-gate-nightly.py` — SPRT gate on shadow model alignment; nightly batch pass
- `sprt-falsifiability-handshake.py` — both parties must agree a claim is falsifiable before SPRT runs
- `sprt-inner-outer-alignment.py` — inner/outer alignment SPRT check
- `sprt-measurement-tamper.py` — detects measurement tampering in SPRT evidence
- `sprt-truncation-gate.py` — prevents SPRT from running on truncated evidence

---

### 6. Uncertainty estimation and evaluation

**Uncertainty estimation**
- `ue-blackbox-scorer.py` — black-box UE scorer (no model internals required)
- `ue-calibration-bridge.py` — bridges UE scores to the calibration pipeline
- `ue-memory-gate.py` — gates memory commits on UE score (high-uncertainty facts not committed)
- `ue-perplexity-proxy.py` — perplexity as a UE proxy for models without logprobs
- `ue-semantic-density.py` / `ue-semantic-graph.py` — semantic density and graph-based UE
- `uncertainty-calibration-monitor.py` — monitors UE calibration drift over time
- `reasoning-ue-integrator.py` — integrates UE scores into reasoning trace confidence

**Evaluation scaffolding**
- `block-bootstrap-sprt.py` — block bootstrap + SPRT for statistically sound eval comparison
- `eval-routing-linucb-features.py` — feeds LinUCB features from eval results back to routing
- `hallucination-detector.py` — UE-based hallucination detection on tool outputs
- `step-level-prm-scorer.py` — process reward model scorer at step level
- `step-level-trajectory-auditor.py` — full trajectory audit with step-level PRM scores
- `circuit-trajectory-scorer.py` — scores agent trajectories against expected circuit patterns

---

### 7. Cost and compute governance

**Compute routing**
- `dcr-compute-router.py` / `dcr-reconcile.py` — dual compute router with reconciliation pass
- `cost-cutoff-task-router.py` — routes tasks to cheaper models when cost exceeds threshold
- `pareto-phase-router.py` — Pareto-frontier router: quality vs. cost
- `triple-objective-frontier-router.py` — three-objective (quality, cost, latency) frontier
- `real-options-deployment-gate.py` — real options valuation gate for model upgrades

**Budget control**
- `token-budget-controller.py` — per-session token budget with hard cutoff
- `cascade-error-budget-allocator.py` — allocates error budget across the tool cascade
- `relay-routing-capacity-allocator.py` — capacity allocation for relay routing
- `feedback-budget-optimizer.py` — optimises feedback-loop budget across eval arms
- `cost-aware-escalation.py` / `cost-aware-eval-framework.py` — escalation and eval with cost constraints

**Scaling and autoscaling**
- `llm-autoscaler.py` — LLM autoscaler: adjusts parallel subagent count based on queue depth and cost
- `spawning-utility-estimator.py` — estimates utility of spawning a subagent before dispatch
- `campaign-scorer.py` — multi-arm campaign scorer for model A/B campaigns

---

### 8. Data versioning (Dolt-inspired)

Implements Dolt's data merge semantics in Python on SQLite, without the Dolt binary or Prolly trees.

**PK three-way merge** (`dolt-merge.py`)
- Rows keyed by primary key; different PKs auto-merge
- Same PK, different field, changed from base → field-level auto-merge
- Both sides changed same field from base → explicit conflict (never silent last-write-wins)
- Conflict record: `{pk_val, field, base_val, ours_val, theirs_val}`; resolve via `strategy='ours'|'theirs'`
- JSON/dict column values: one-level sub-key merge; delete+modify = conflict; delete+unmodified = drop
- CLI: `dolt-merge.py merge --base B.json --ours O.json --theirs T.json --pk job_id`
- Used for safe concurrent writes to `jobs.json` from multiple cron workers

**Cell changelog / blame** (`lifecycle-changelog.py`)
- Adds `fact_commits` + `fact_changelog` tables to the shared `~/.hermes/memory-facts/lifecycle.db` (append-only, no effect on existing tables)
- Operations: `new_commit()`, `log_change()`, `get_history()`, `time_travel()`, `blame()`
- Read operations use `uri=ro` SQLite connections — WAL pragma never issued on read path
- `time_travel(db, table, pk, as_of_commit)` replays I/U/D operations through commit ancestry
- `blame(db, table, pk, field)` returns last commit that changed that field

---

### 9. System maintenance and infrastructure

**System update** (`daily-silverblue-update.sh`)
- Per-step timeouts: toolbox DNF (1200s), fwupdmgr (300s), git repos (60s each)
- Flatpak appstream-only errors treated as non-fatal (was causing full timeout on slow mirrors)
- Login-trigger variant for systems where update needs an active session

**Cron infrastructure**
- 100+ managed cron jobs across compaction eval, memory maintenance, skill evaluation, security audits, system updates, and research pipelines
- `cron-sandbox-runner.py` — sandboxed cron execution with openshell policy enforcement
- `cron-admission-control.py` — admission control: drops low-priority cron jobs under load
- Skill-index weekly rebuild correctly passes `--build` (was a silent no-op in upstream-inherited config)
- `HERMES_NO_SANDBOX=1` explicitly blocked in cron wrapper as a security boundary

**Security monitoring**
- `firewall-port-audit.sh` / `sysctl-verify.sh` — periodic firewall and sysctl audit
- `mcp-auth-drift-check.py` — detects MCP authentication config drift
- `secure-message.py` — message signing and verification utility

**openshell sandbox policy**
- `openshell-policy.yaml` maintained with clean RO/RW separation
- All cron scripts run inside the openshell sandbox; bypass attempts are logged and rejected

---

## Plugin summary

| Plugin | Hook | Description |
|---|---|---|
| `jev-compaction` | `on_pre_compress` | Entropy-weighted compaction gate |
| `compaction-gate` | `on_pre_compress` | MDL saving gate (depth_threshold, mdl_min_saving) |
| `jev-turn-evaluator` | `post_llm_call` | Shadow model scores every LLM turn; gates policy arm promotion |
| `governance-hard-block` | `pre_tool_call` | Hard-blocks policy violations |
| `cobra-guard` | `post_tool_call` | Outcome tracking; blocks repeat decision failures |
| `tool-auth-gate` | `post_tool_call` | Probabilistic inspection-game auth audit |
| `tool-result-audit` | `post_tool_call` | Prompt injection detection on external tool results |
| `memory-ransac-gate` | `post_tool_call` | RANSAC inlier gate before memory commit |
| `context-pressure-guard` | `post_tool_call` | Alarm when context pressure exceeds threshold |
| `decision-audit` | `post_tool_call` | Per-session tool resolvability accumulator; writes to lifecycle.db |
| `delegation-audit-hook` | `post_tool_call` | Audits subagent delegation outcomes |
| `deductive-verifier` | `post_llm_call` | Verifies reasoning chain deductive validity |
| `formal-verify-plugin` | `post_tool_call` | Hard core enforcement on proof-state tool calls |
| `compliance-score-hook` | `post_tool_call` | Red-flag and length compliance scoring |
| `post-tool-compliance` | `post_tool_call` | Shadow compliance scorer (observation-only) |
| `turn-behavior-logger` | `post_llm_call` | Logs turn-level behavior metrics |
| `hindsight` | multiple | Long-term memory with knowledge graph and entity resolution |
| `adaptive-retrieval` | retrieval | Adaptive retrieval strategy selection |
| `billion-context` | compaction | Billion-context CCR compression |
| `skill-access-logger` | skill | Logs skill accesses with query fingerprint |
| `skill-routing-nudge` | skill | Mid-turn nudge on low-confidence routing |
| `skill-latency-logger` | skill | Per-skill latency histogram |
| `su-observability` | multiple | System-under-observation metrics |
| `orca-status` | lifecycle | Lifecycle event reporting |
| `camofox` | browser | Stealth browser integration |

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
