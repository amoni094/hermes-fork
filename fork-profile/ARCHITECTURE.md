# Hermes Architecture — Canonical Reference

Patterns ported from Denuto (jesterG1979/hello_agent) + Hermes-native patterns.
This is the authoritative single source of truth for how Hermes is structured,
what rules are enforced, and what the invariants are.

Last updated: 2026-09-16 (wiring sprint 2 + book-to-skill ingestion)

---

## Tier System

Rules are split into two tiers (borrowed from Denuto's architecture contract):

Tier 1 — Enforced Invariants: hard rules. Each names the check that enforces it
  (a script, test, or hook). An agent may not weaken or route around a Tier-1 rule
  in a normal change. If a rule has no gate, it is marked GATE GAP.

Tier 2 — Operating Posture: non-binding guidance. Real, but not mechanically
  checkable. An agent must NOT cite a Tier-2 statement to claim a change is "verified."

Honesty rule: if a rule has no gate today, mark it GATE GAP (proposed: ...) rather
than implying it runs. Gate gaps accumulate into a backlog.

---

## Tier 1 — Enforced Invariants

### H-I1 — Skills are the single source of truth for agent procedures
- Skills in ~/.hermes/profiles/fork/skills/ are canonical.
- User-owned skills require `hermes curator adopt` before any curator write.
- No procedure lives only in memory or in session history.
- GATE: skillspector_guard.py runs on cron every 240m (post-facto batch scan).
- GATE GAP: no git pre-commit hook; skillspector_guard.py is NOT a pre-commit checker —
  it is a batch quarantine scanner. H-I1 is enforced reactively, not at write time.

### H-I2 — Memory surfaces have strict ownership (one writer per fact class)
- skills: reusable procedures and task-specific patterns
- memory: facts that apply to EVERY session regardless of task (who the user is, env facts, conventions)
- session history: within-session recall, transient state
- Overlapping stores with no ownership rule = four places a stale claim can survive.
- No mirroring: a fact lives in exactly one store. Cross-reference by link; never copy.

### H-I3 — Evidence over assertion
- Claims about tool results, file writes, deploys, and fixes must include verifiable output.
- "Implemented, not yet tested" is a valid status. An unqualified success claim without evidence is not.
- Report failures faithfully. Never round a partial pass up to "passing."
- State skipped steps: if a required step was skipped, name it and say why.
- Source: Denuto golden-principles.md #2, agent-operating-rules.md Progress Reporting section.

### H-I4 — No same feedback twice
- Corrective user steering is a high-signal defect report against the agent operating system.
- Convert repeated or behavior-level feedback into a durable control: skill update, memory update,
  config change, script, or cron job.
- Empty assurances ("I will remember", "going forward") are not a fix unless backed by a durable control.
- Source: Denuto golden-principles.md #11, agent-steering-feedback-loop.md.

### H-I5 — Small, reversible changes
- Prefer narrow changes that are easy to review, test, and roll back.
- Especially before touching config.yaml, plugin hooks, or runtime scripts.
- Source: Denuto golden-principles.md #3.

### H-I6 — Hermes scripts must be stdlib-only unless explicitly approved
- Scripts in ~/.hermes/scripts/ must not introduce new pip deps without explicit approval.
- Exception: lyapunov-analysis.py uses numpy/scipy (pre-approved, analysis-only, never on critical path).
- Use execute_code + Path.write_text() to write scripts (write_file false-alarms on scripts/).
- Source: local convention, discovered 2026-09-16.

### H-I7 — Shadow paths never raise; annotation only
- Any shadow/telemetry/middleware annotation path MUST swallow all exceptions.
- A shadow failure must not contaminate the live path.
- Source: Denuto shadow_telemetry.py design constraint.

### H-I8 — Improvement proposals are risk-classified before execution
- LOW (skill_update, skill_create, memory_update): auto-approved.
- MEDIUM (script_add, script_modify, cron_add): needs 1 reviewer.
- HIGH (config_change, plugin_update, cron_modify): needs 2 senior approvals + 24h cooldown after rollback.
- These targets always escalate to HIGH: config.yaml, plugin_stream_hooks, conversation_compression,
  api_request_hooks, gateway, compression.
- CLI: python3 ~/.hermes/scripts/improvement_governance.py propose --change-type TYPE --target TARGET --description DESC
- GATE GAP: no agent/*.py hook calls governance.py before HIGH-risk writes. Enforcement is manual only.

---

## Tier 2 — Operating Posture

### Agent loop design
- Deterministic control plane wrapping nondeterministic LLM nodes is the textbook-correct shape.
- Keep deterministic logic and LLM judgment physically separated where possible.
- Source: Denuto I5 invariant + AWS GenAI Lens guidance.

### Ponytail (lazy senior dev mode)
Before writing any agent code or skill, stop at the first rung that holds:
  1. Does this need to be built at all? (YAGNI)
  2. Does the standard library already do this?
  3. Does a native Hermes feature cover it?
  4. Does an already-installed dependency solve it?
  5. Can this be one line?
  6. Only then: write the minimum that works.

Not lazy about: input validation at trust boundaries, error handling that prevents
data loss, security, and anything explicitly requested.
Source: Denuto ponytail-lazy-senior-dev.md.

### Memory division of labour
- Session history: what we just tried, why we backed out. Do NOT write durable facts here.
- memory: who the user is, env facts, standing conventions. Max 2200 chars — consolidate aggressively.
- skills: task-specific procedures, patterns, pitfalls, tool commands. Load only when relevant.
- Citation rule: any claim that changes a skill or config must cite a tool result from this session.
- Promotion rule: a fact recalled from session history that matters gets written to skill/memory in the same session.
- No-mirroring rule: a fact lives in exactly one store. Two copies = one of them is wrong.
Source: Denuto harness-and-memory-contract.md.

### Concurrency (AIMD controller)
- Use ~/.hermes/scripts/aimd_controller.py for bounded parallel subagent dispatch.
- AIMD limitation: each subagent has independent state — no cross-agent convergence.
- For truly concurrent work, prefer delegate_task with explicit output contracts.

### Skill routing
- Primary: BM25 index (skill-router-index.py, build_tfidf with k1=1.5, b=0.75).
- Semantic fallback: when BM25 top-2 score gap < 0.12, concept-lattice-index.py is called
  via subprocess --query to re-rank candidates. Output flags semantic_reranked=True.
- Known failure: concept-lattice requires a warm Hindsight cache; falls back to pure BM25 if cold.

### Loop stability (PID + internal Lyapunov check)
- loop-pid.py implements discrete linear PID with anti-windup and an internal Lyapunov decrease
  check (cmd_lyapunov_check, citing KHALIL-1/KHALIL-7). This is self-contained in loop-pid.py.
- lyapunov-analysis.py is a SEPARATE standalone tool (requires numpy/scipy) for offline phase-portrait
  and bifurcation analysis. It is NOT called by loop-pid.py. Use it manually for stability diagnosis.
- Do NOT claim "loop-pid is wired to lyapunov-analysis" — they are independent instruments.

### Middleware stack
- See ~/.hermes/profiles/fork/skills/hermes-llm-middleware-stack/SKILL.md for composable middleware.
- Loop detection: MD5-hash responses per (session_id, stage). Catches syntactically identical loops.
- Rephrased-loop detection: _is_rephrased_loop() in metacognitive-harness.py — 4-gram Jaccard
  similarity over last 5 history items (threshold=0.85). Catches semantically equivalent paraphrases.
- Cost guard: redirect to cheaper model when cumulative cost > threshold.
- Grounding: verify quoted strings against source text. Annotate only, never retry.

### Shadow evaluation
- See ~/.hermes/profiles/fork/skills/hermes-shadow-evaluation/SKILL.md.
- New features ship behind shadow_<feature>: false flags before going live.
- Gate script at ~/.hermes/scripts/shadow_telemetry.py evaluates JSONL telemetry.
- Nightly report: shadow-gate-nightly.py cron job (0 8 * * *, no_agent=True, id=shadow-gate-0001).
  Reads ~/.hermes/cache/shadow-telemetry/*.jsonl; prints promote/disable/keep-shadow per flag.

### Improvement governance
- See ~/.hermes/profiles/fork/skills/hermes-improvement-governance/SKILL.md.
- Gate script at ~/.hermes/scripts/improvement_governance.py classifies risk and tracks proposals.
- CLI subcommands: propose, approve, rollback, list.
- GATE GAP: agent runtime does not call this automatically before HIGH-risk writes.

### Run ledger
- See ~/.hermes/scripts/run_ledger.py for durable agent task state with OCC conditional writes.
- Hash-chain audit log, clock injection, IllegalRunTransition on invalid state machine transitions.
- CLI subcommands: create, complete, fail, status.

### Consistency scoring
- See ~/.hermes/scripts/consistency_scorer.py for calibrated LLM confidence.
- N=3 Condorcet majority: 3/3=1.0, 2/3=0.5, 1/3=0.2, 0/3=0.05 (conservative, not prob-theoretically derived).
- Wired into metacognitive-harness.py cmd_gate() for L2/L3 scope factual claims (MH_CONSISTENCY=1 env var).
- Calibration logging: (predicted_confidence, query_hash, scope) appended to ~/.hermes/cache/calibration-log.jsonl.

### Context compression advisory
- rd-compaction-advisor.py is called by pre-compact-annotate.py (runs every 15m, no_agent=True).
- Estimates aggressiveness [0,1] from current token count vs threshold (R-D curve shape, k=3).
- Appended to annotation output as: "Compaction advisory: aggressiveness=X.XX, focus=TOPIC".
- NOTE: rd-compaction-advisor.py is NOT wired into context_compressor.py directly — it is an advisory
  annotation only. The compressor does not read the annotation and adapt its salvage pass.

### Dead config sections (confirmed 2026-09-16)
The following config.yaml sections have zero consumers in agent/*.py. They are documented aspirations,
not enforced gates. Do NOT cite them as active enforcement:
  - calibration_gate: commitment_threshold defined but never evaluated in agent runtime
  - constraint_freshness: config key read by memory-ttl-purge only (not agent routing)
  - durable_file_write_gate: 0 agent/*.py consumers
  - skill_state: 0 agent/*.py consumers
  - tool_slo: 0 agent/*.py consumers
  - loop_harness: 0 agent/*.py consumers (reasoning_hooks are LLM prompt hints, not code gates)

---

## Runtime Scripts Reference

~/.hermes/scripts/:
  aimd_controller.py         - AIMD concurrency controller for parallel subagent dispatch
  consistency_scorer.py      - Calibrated LLM confidence via N=3 Condorcet; wired into metacognitive-harness
  shadow_telemetry.py        - Shadow-mode feature flag evaluation and JSONL telemetry
  shadow-gate-nightly.py     - Nightly cron wrapper: evaluates all shadow flags, prints promote/disable report
  improvement_governance.py  - Risk-classified self-improvement proposal lifecycle; CLI: propose/approve/rollback/list
  run_ledger.py              - Durable agent task state with OCC conditional writes + hash-chain audit; CLI: create/complete/fail/status
  rd-compaction-advisor.py   - R-D shaped compaction aggressiveness advisor; called from pre-compact-annotate.py
  concept-lattice-index.py   - Nightly concept lattice over Hindsight facts; --query CLI for semantic reranking
  skill-router-index.py      - BM25 skill router + concept-lattice semantic fallback (gap < 0.12 → rerank)
  loop-pid.py                - Discrete linear PID + internal Lyapunov decrease check (KHALIL-1/7)
  lyapunov-analysis.py       - STANDALONE offline phase-portrait/bifurcation tool (numpy/scipy); NOT called by loop-pid
  memory-ttl-purge.py        - TTL purge for staged memories; fixed 2026-09-16 (forward-ref NameError resolved)
  tool-auth-shim.py          - Tool-call authorisation shim (inspection-game mixed strategy; wired into unified-recall.py EXTERNAL tier — wiring sprint 2)
  calibration-threshold-updater.py - Reads calibration-log.jsonl; updates Condorcet thresholds; EMA now seeds from prior run (wiring sprint 2)
  context-pressure-reader.py - Reads context token pressure; advisory annotation (wiring sprint 2)
  recall-miss-ttl-adjuster.py - MRAS adaptive TTL adjuster; reads recall-misses.jsonl; closes bottleneck #8 (wiring sprint 2)

---

## Key Skills (Denuto-derived)

  hermes-llm-middleware-stack    - Loop detection, grounding, cost guard, few-shot injection
  hermes-shadow-evaluation       - Shadow feature flags + promotion gate
  hermes-improvement-governance  - Self-improvement lifecycle with risk gating
  comment-sicko                  - Adversarial comment audit (Denuto-ported)

---

## Gap Backlog (confirmed open as of 2026-09-16)

OPEN — no partial progress:
  - H-I1: skillspector-guard pre-commit check (cron batch scan is not a pre-commit hook)
  - H-I8: governance.py called automatically before HIGH-risk agent writes
  - Dead config gates: calibration_gate, durable_file_write_gate, skill_state, tool_slo, loop_harness
    need agent/*.py consumers or should be removed/marked disabled

CLOSED this session (2026-09-16, wiring sprint 2 + adversarial fixes):
  - Skill router semantic fallback: concept-lattice wired as BM25 tiebreaker
  - Consistency scorer: wired into metacognitive-harness L2/L3 gate + calibration logging
  - improvement_governance.py: CLI entrypoint added (propose/approve/rollback/list)
  - run_ledger.py: CLI entrypoint added (create/complete/fail/status)
  - shadow_telemetry.py: nightly cron (shadow-gate-0001, 0 8 * * *)
  - rd-compaction-advisor.py: wired into pre-compact-annotate.py annotation output
  - memory-ttl-purge.py: fixed NameError (check_constraint_freshness forward reference) — function moved before call site (line 349 < 416)
  - l1-graphiti-reconcile.py concurrent call race: fcntl exclusive lockfile added at module load;
    l1-graphiti-periodic interval staggered to 250m (was 240m); schedule_display corrected
  - Embedding loop detection (rephrased loops): _is_rephrased_loop() wired into cmd_gate() (exit_code=4 REPHRASED_LOOP);
    --response/--history args added to gate CLI; 4-gram Jaccard, threshold=0.85; stdlib-only; shadow-wrapped
  - Calibration loop closure: calibration-threshold-updater.py; EMA now seeds from prior run (M1 fix);
    cron schedule fixed from {} to {"kind":"cron","expr":"0 6 * * *"}
  - Tool injection shim: tool-auth-shim.py wired into unified-recall.py fuse_results() on EXTERNAL tier;
    cron schedule fixed from {} to {"kind":"cron","expr":"*/30 * * * *"} for context-pressure-monitor
  - Context pressure reader: context-pressure-reader.py; cron schedule fixed
  - UCB1 bandit feedback loop (H1): _update_bandit_state() now called after fuse_results() with enriched_weight as reward; bandit now learns
  - Beta-Binomial trust posterior (H3): unified-recall.py dynamically imports get_trust_weight() from memory-provenance.py; static dict is fallback
  - Tool-auth gate (H4): unified-recall.py imports tool-auth-shim and calls audit_tool_result() on EXTERNAL items
  - logger_mh NameError (H6): replaced with stderr print in metacognitive-harness.py
  - calibration-log naming (L6): metacognitive-harness.py _CALIB_LOG unified to dash variant
  - recall-miss-ttl-adjuster.py: new script; MRAS adaptive TTL; reads recall-misses.jsonl; closes bottleneck #8;
    cron 0 5 * * * (recall-miss-ttl-adjuster-0001)
  - Books ingested as skills: slotine-li-nonlinear-control, lattimore-bandit-algorithms,
    shalev-shwartz-understanding-ml, gelman-bda3, shoham-multiagent-systems

BOTTLENECK STATUS (9 identified):
  #1 COMPACTION MONOTONICITY    — FULLY CLOSED (prior sprint)
  #2 MEMORY QUERY ROUTING       — FULLY CLOSED (routing-weight-updater.py reads routing-calibration.jsonl,
                                    FTRL-EMA updates routing-weights.json, wired into memory-query-router.py
                                    confidence downgrade; cron 0 7 * * *)
  #3 LOOP STABILITY             — DOCUMENTED (Lyapunov annotation; loop-pid.py implementation confirmed correct)
  #4 SKILL ROUTING              — FULLY CLOSED (prior sprint)
  #5 UNIFIED-RECALL FUSION      — FULLY CLOSED (UCB1 + trust posterior wired with feedback loops)
  #6 CONTEXT PRESSURE           — FULLY CLOSED (context-pressure-guard plugin via pre_llm_call hook;
                                    registered in fork config.yaml; fires at consecutive_high>=2)
  #7 TRUST WEIGHTING            — FULLY CLOSED (Beta posterior wired: read via get_trust_weight() in
                                    unified-recall.py; written via update_trust_posterior() in H10 feedback block)
  #8 MEMORY TTL                 — FULLY CLOSED (recall-misses.jsonl written + recall-miss-ttl-adjuster.py reads it)
  #9 TOOL AUTH GATE             — FULLY CLOSED (tool-result-audit plugin via post_tool_call hook on
                                    INJECTION_RISK_TOOLS: web_search/web_extract/browser_exec/js;
                                    registered in fork config.yaml)

ADVERSARIAL FIXES (sprint 3, 2026-09-17):
  - l1-graphiti-reconcile.py: tracegrant import shadow-wrapped (H1); sys.exit replaced with
    _RECONCILE_LOCK_HELD flag + atexit release + main() early return (H2)
  - memory-ttl-purge.py: staging.md write made atomic via tmp+rename (H3)
  - unified-recall.py: stale TODO removed (M6); trust posterior update_trust_posterior() wired
    into recall feedback block (H10); _mp resolved via locals()/globals() to avoid Pyright error
  - recall-miss-ttl-adjuster.py: adaptive-ttl-state.json write atomic (M5)
  - calibration-threshold-updater.py: Condorcet threshold write atomic (M7)
  - memory-provenance.py: trust-posterior.json write atomic (L8); module-level documented shadow-safe
  - memory-query-router.py: ot_utils import guarded with try/except ImportError (L9)
  - routing-weight-updater.py: new script; reads routing-calibration.jsonl, updates routing-weights.json (bottleneck #2)
  - Plugins created: context-pressure-guard (pre_llm_call), tool-result-audit (post_tool_call)
    Both registered in ~/.hermes/profiles/fork/config.yaml plugins.enabled
