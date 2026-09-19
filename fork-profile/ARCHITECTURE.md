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
- GATE: skillspector_guard.py runs on cron every 235m (post-facto batch scan).
- GATE (H-I1: skillspector pre-commit hook): CLOSED — pre-commit hook installed at
  ~/.hermes/hermes-fork/.git/hooks/pre-commit; scans staged SKILL.md files via
  `HERMES_PROFILE=fork python3 ~/.hermes/scripts/skillspector_guard.py --enforce`
  and blocks the commit (exit 1) on high-risk findings. Fail-open: absent guard → warn + exit 0.

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
- GATE (H-I8 advisory): tool_guardrails.py _governance_pre_check() fires for HIGH-risk .hermes writes;
  fail-open advisory (does not hard-block). Full GATE GAP: no hard-blocking auto-call exists yet in agent runtime.

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
The following config.yaml sections have zero AGENT-RUNTIME consumers in agent/*.py. They are documented aspirations,
not enforced gates in the agent loop. Do NOT cite them as active enforcement:
  - calibration_gate: commitment_threshold defined but never evaluated in agent runtime
  - constraint_freshness: config key read by memory-ttl-purge only (not agent routing) — now profile-aware via HERMES_HOME
  - durable_file_write_gate: 0 agent/*.py consumers
  - skill_state: 0 agent/*.py consumers (read by skill-state.py standalone script)
  - tool_slo: 0 agent/*.py consumers (am-sentry.py implements SLO detection independently)
  - loop_harness: 0 agent/*.py consumers (reasoning-hooks.py reads via env-aware HERMES_HOME)

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

## Gap Backlog — verified status as of 2026-09-19

### OPEN (genuinely unresolved)

  H-I8 (governance auto-call): improvement_governance.py is not called automatically
    before HIGH-risk agent writes. tool_guardrails.py fires it as a pre-check for
    writes to .hermes paths, but only as a fire-and-forget advisory (fail-open).
    No hard block exists in agent/*.py. GATE GAP annotation on H-I8 in Tier 1 is correct.
    Status: PARTIAL — advisory wired, hard gate absent.

  l1-extract.py source zeroed: running unauditable bytecode from __pycache__.
    l1-extract-recovered.py was written with RECOVERED FROM BYTECODE header and
    per-function pseudocode. The inner 662-line payload requires pycdc/decompile3
    for full source recovery.
    Status: DOCUMENTED — bytecode stub confirmed identical to shim; decompile pending.

  82 dark output files: scripts that write JSON files never read by any consumer.
    These are standalone metric/research scripts. alarm-aggregator.py handles the
    alarm-format subset (*-alarm.json). Non-alarm dark outputs are accepted as
    standalone observability instruments with no live consumer.
    Status: ACCEPTED — non-alarm dark outputs are out-of-scope for wiring.

  state-wal-checkpoint.py WAL checkpoint is a no-op: state.db uses journal_mode=DELETE,
    so PRAGMA wal_checkpoint(TRUNCATE) has no effect. VACUUM is still useful.
    Status: ACCEPTED LIMITATION — fixing requires migrating state.db to WAL mode
    (risky schema migration). Script renamed intent to VACUUM-only in comments (F-10).

### CLOSED (verified on-disk, not hypothetical)

  H-I1 pre-commit hook: installed at ~/.hermes/hermes-fork/.git/hooks/pre-commit;
    scans staged SKILL.md files via skillspector_guard.py --enforce (HERMES_PROFILE=fork);
    blocks on high-risk findings (exit 1); fail-open when guard absent.
    Wave 8. Adversarial pass: PASS.

  H-I8 advisory gate: tool_guardrails.py _governance_pre_check() wired as pre-check
    for HIGH-risk tool calls on .hermes paths. Fire-and-forget, fail-open.
    Hard auto-block remains OPEN above.

  M3 focus_compress.py phantom tool refs: start_focus / complete_focus appear in
    documentation strings and template text only. focus_compress.py --mode reminder
    prints text; it does NOT call any tools at runtime. pre-compact-annotate.py
    calls it as a subprocess safely. The backlog claim was a false positive — the
    15 refs are doc-only. CLOSED: false positive.

  M4 H2ObstructionLedger dark write: l1-gmemory-consolidation.py reads
    h2-obstructions.json in a post-consolidation step (L541-563), logs unresolved
    obstructions to stderr, profile-aware path, fail-open. Wave 7.

  M5 disconnected skill routers: skill-router-index.py route() has a full ensemble
    layer (L510-620) calling soft-bellman, kl-skill-prior, pareto-phase,
    privacy-constrained, and online-threshold via subprocess (timeout=5, fail-open)
    when BM25 top score < 0.4. All 5 routers have callers. Wave 7.

  B2 unified-recall.py hardcoded lifecycle.db path: _hermes_root() helper added;
    7 path sites (lifecycle.db x2, recall-log, FTRL state, bandit state,
    experience-cache x2) now use HERMES_HOME env var. Wave 10 + adversarial pass.

  B5 mcp-privilege-audit.py always returned 0: now returns 1 when total_flags > 0;
    writes mcp-privilege-alarm.json for alarm-aggregator pickup.
    Adversarial NI-1 (pathlib.Path NameError in alarm block) fixed same session.

  M6 skillspector_guard.py drift suppressed: _drift_count tracks INTEGRITY-FAIL and
    MERKLE-DRIFT events; main() returns 1 if _drift_count > 0. Wave 10.

  M7 hermes-memory-drift-audit.py drift suppressed: returns 1 after printing
    exact/near/overgrowth/stale_refs/rule_leakage findings. Adversarial NI-2
    (rule_leakage missing from exit condition) fixed same session. Wave 10.

  dual-backend-memory-fuser.py hardcoded stubs: _backend_a() calls unified-recall.py
    via subprocess; _backend_b() calls skill-router-index.py via subprocess;
    both timeout=10, fail-open. Wave 7.

  H2ObstructionLedger (profinite-thread-check.py): writes h2-obstructions.json;
    consumed by l1-gmemory-consolidation.py post-consolidation step. Wave 7.

  ContentStore.put() non-atomic write (run_ledger.py): content-addressed store;
    SHA-256 key makes double-write idempotent; if-not-exists guard at L114
    prevents partial overwrites. ACCEPTED: not a real atomicity risk.

  GATE_RECALL_UPLIFT_PP unused: symbol no longer present in unified-recall.py.
    False positive — already removed.

  routing-weight-updater hardcoded route list: _DEFAULT_ROUTES is a seed only;
    _load_known_routes() does dynamic discovery from calibration log at runtime.
    False positive.

  tool-auth-shim blanket except: L51 wraps JSONL shadow-logging (fail-open by design,
    H-I7); L73 wraps injection detector (returns UNKNOWN verdict, not pass-through).
    Both are correct. ACCEPTED.

  skill-yield-tracker feedback dark: yield metrics in state.db not read by any router.
    ACCEPTED: yield tracking is an observability instrument; router coupling would
    create circular dependency on session DB. Out of scope.

  All prior wave closures (waves 1-9, sprint 2-3): see Wave 7, Wave 8, and sprint
    closure tables below.

### ACCEPTED LIMITATIONS (architectural — not fixable by script patch)

  Rate-limit persistence across subprocess callers: improvement_governance.py and
    similar scripts use in-process rate-limit state; each subprocess invocation
    resets the window. Fixing requires caller-side durable state wired at every
    call site. Out of scope.

  retry-budget-guard in-process only: AUTH/RESOURCE cross-restart budgets tracked
    in cache/retry-budget-state.json (PersistentBudgetState, Wave 8). TRANSIENT/
    SEMANTIC/FATAL remain in-process only — fixing those requires redesigning callers.

  rd-compaction-advisor annotation-only: aggressiveness advisory is appended to
    pre-compact-annotate.py output but context_compressor.py does not read it.
    Wiring it into the compressor salvage pass requires agent/*.py changes.
    Partial closure only.


## Wave 7 Closures (2026-09-19)

| Gap | Fix | Status |
|-----|-----|--------|
| skill-router-index scan_skills() relative_to hardcoded path | Changed relative_to(Path.home()/".hermes"/"skills") → relative_to(SKILLS_ROOT); fork profile now builds non-empty index | CLOSED |
| 5 disconnected skill routers (soft-bellman, kl-skill-prior, pareto-phase, privacy-constrained, online-threshold) | Wired into skill-router-index.py route() as post-hoc ensemble layer (fires when BM25 score < 0.4); each called via subprocess timeout=5 fail-open | CLOSED |
| dual-backend-memory-fuser.py hardcoded stubs | Replaced _backend_a() with real subprocess call to unified-recall.py; _backend_b() with real call to skill-router-index.py; both timeout=10 fail-open | CLOSED |
| H-I8: governance.py never called before HIGH-risk agent writes | _governance_pre_check() added to tool_guardrails.py before_call(); fires for write_file/patch/terminal/execute_code on .hermes/hermes-fork/ paths; fail-open | CLOSED |
| _HIGH_RISK_PATH_INDICATORS too broad (any "agent/" path) | Tightened to ".hermes/hermes-fork/agent/", ".hermes/profiles/", ".hermes/plugins/", ".hermes/scripts/", "config.yaml" | CLOSED |
| l1-extract.py source zeroed / unauditable bytecode | l1-extract-recovered.py written with RECOVERED FROM BYTECODE header; bytecode pseudocode per function documented; outer shim confirmed identical to stub | DOCUMENTED (inner 662-line payload requires pycdc/decompile3) |
| H2ObstructionLedger dark write never consumed | l1-gmemory-consolidation.py post-consolidation step reads h2-obstructions.json; logs unresolved obstructions to stderr; profile-aware path; fail-open | CLOSED |
| focus_compress.py phantom tools never injected | pre-compact-annotate.py now calls focus_compress.py --mode reminder; appends output as "## Focus Agent Reminder" annotation section | CLOSED |
| Dead config gates (calibration_gate, durable_file_write_gate, skill_state, tool_slo, loop_harness) | Marked ACCEPTED: removed from scope; comment added to config.yaml; ARCHITECTURE.md updated | CLOSED |
| pre-compact-annotate.py SQLite connection leak on early exit | Replaced multiple con.close() calls before sys.exit() with try/finally block ensuring always-closed | CLOSED |

## Wave 8 Closures (2026-09-19)

| Gap | Fix | Status |
|-----|-----|--------|
| alarm-summary.json dark (no consumer) | monitor-suite-runner.py reads alarm-summary.json at end of main(); prints [monitor-suite] ALARMS: N active (HIGH: M MEDIUM: P); fail-open | CLOSED |
| gate-audit.json dark (no consumer) | alarm-aggregator.py: _gate_audit_alarms() reads gate-audit.json <2h old; REVIEW verdict → HIGH alarm entry; n_records==0 → MEDIUM; flows into alarm-summary.json | CLOSED |
| skill-integrity.json dark (no consumer) | skillspector_guard.py end-of-main block reads skill-integrity.json; prints INTEGRITY-FAIL: SKILL (REASON) for status!='ok'; fail-open | CLOSED |
| skill-merkle.json dark (no consumer) | skillspector_guard.py end-of-main block reads skill-merkle.json; prints MERKLE-DRIFT: SKILL for drift/changed==True; fail-open | CLOSED |
| BN-08: retry-budget-guard in-process only (restart resets AUTH/RESOURCE budgets) | PersistentBudgetState class added; AUTH+RESOURCE tracked cross-restart in cache/retry-budget-state.json; 24h window expiry; atomic save; TRANSIENT/SEMANTIC/FATAL remain in-process only | CLOSED |
| H-I1: skillspector-guard pre-commit hook (cron batch scan != pre-commit hook) | POSIX sh hook written to ~/.hermes/hermes-fork/.git/hooks/pre-commit; scans staged SKILL.md files; runs skillspector_guard.py --enforce with HERMES_PROFILE=fork; fail-open if guard absent; chmod +x | CLOSED |

Adversarial cold pass (Task 4): 5/5 PASS — no HIGH/CRITICAL findings. LOW observations: cron ordering for alarm-summary (scheduling, not a code defect); HERMES_PROFILE=fork hardcoded in hook (correct for this repo). No patches required.

## Wave 11 Closures (2026-09-19)

| Finding | Fix |
|---------|-----|
| G1 HIGH: skillspector_guard.py non-atomic write (skill-integrity.json, skill-merkle.json) | tmp+replace pattern; crash-safe baseline |
| G2 MED: skill-graph-reachability-verifier.py non-atomic baseline write | tmp+replace pattern |
| G3 MED: spec-semantic-graph-builder.py non-atomic baseline write | tmp+replace pattern |
| G4 MED: hermes-gateway-prestart.py never called | cron entry added (hermes-gateway-prestart-0001, daily 0 4 * * *) |
| G6 LOW: dark output count stale (70 → 82) | ARCHITECTURE.md updated |

Accepted (architectural / no single wiring point):
  G5 MED: real-options-deployment-gate.py — always returns 0, no callers.
    Caller-invoked on-demand gate for subagent fan-out commitment decisions.
    No single insertion point in the agent runtime. Accepted as manual-invocation tool.

False positives eliminated this wave:
  - 6 alarm files (*-alarm.json) already caught by alarm-aggregator glob — not dark
  - fuse_results, _update_bandit_state, check_grant, _issue_pet, rq_kmeans_assign — all have internal call sites
  - browser_act_guard, routing-convergence-guard, retry-budget-guard — CLI multi-subcommand tools, return-0-only is correct
  - cobra-skip-guard — uses sys.exit(0/1) correctly; PASS 3 regex missed it
  - skill_prune_audit — caller-only audit library; return values are data, not gate verdicts
  - memory-redundancy-gate — manual-invocation CLI gate, no cron warranted
  - All cron paths clean (fork/scripts/ prefix confirmed); failure streaks all 0

