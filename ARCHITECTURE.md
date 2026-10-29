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

## Wave 12–15 Closures (2026-09-19)

### Wave 12
| Finding | Fix |
|---------|-----|
| W12-A HIGH: shadow-gate-nightly.py TELEMETRY_DIR hardcoded ~/.hermes/cache/shadow-telemetry | Derive from HERMES_HOME+HERMES_PROFILE env vars |
| W12-B MED: mcp-privilege-audit.py DEFAULT_CONFIG hardcoded ~/.hermes/config.yaml | Derive from HERMES_HOME/HERMES_PROFILE |
| W12-C LOW: omni_skill_scan.py eval_script hardcoded ~/.hermes/scripts/gepa_skill_eval.py | Use HERMES_HOME env var |
| Wave-12 adv NI-1 HIGH: mcp-privilege-audit.py L407 report_path.parent.parent.parent → / for /tmp paths | Replace with Path(os.environ.get("HERMES_HOME", ...)) |
| Wave-12 adv NI-2: omni_skill_scan.py L625/636/646 missed skill-router-index.py/pending-improvements/skill-yield-tracker.py paths | Use _hermes_home / "..." pattern |

### Wave 13
| Finding | Fix |
|---------|-----|
| W13-A MED: jev_compaction.py _load_session_messages hardcoded profiles/fork/sessions | Derive from HERMES_HOME+HERMES_PROFILE |
| W13-A2: jev-compaction/__init__.py _SCRIPTS hardcoded ~/.hermes/scripts | Use HERMES_HOME env var |
| W13-B LOW: output-length-predictor.py CALIB_FILE bare write_text | tmp+replace atomic |
| Wave-13 adv residual: jev-compaction/__init__.py _CACHE_DIR + _ha hardcoded | Use HERMES_HOME env var |
| Wave-13 adv residual: output-length-predictor.py SESSIONS_DIR baked fork profile + OUT_FILE bare write | HERMES_HOME+HERMES_PROFILE + atomic |

### Wave 14
| Finding | Fix |
|---------|-----|
| W14-HIGH: jev_verify_fn.py _CALIB_LOG/_BUDGET_FILE/_HERMES_AGENT_PATH hardcoded | HERMES_HOME env var |
| W14-HIGH: context-pressure-guard/__init__.py _SCRIPT_PATH+cache_dir hardcoded | HERMES_HOME env var |
| W14-HIGH: tool-result-audit/__init__.py _SHIM_PATH hardcoded | HERMES_HOME env var |
| W14-MED: unified-recall.py tool-auth-shim+memory-provenance subprocess paths hardcoded | _hermes_root() |
| W14-MED: skill-router-index.py LATTICE_SCRIPT (×2) hardcoded | HERMES_HOME env var |
| W14-MED: consistency_scorer.py calibration-log path hardcoded | HERMES_HOME env var |
| W14-LOW: 54 monitor scripts SESSIONS_DIR/FORK_SESSIONS/SKILLS_DIR/FORK_SKILLS baked fork profile | _HH/_HP/_RT block; _RT/sessions and _RT/skills |
| Wave-14 adv NI-1 CRITICAL: skill-router-index.py os.environ.get NameError (alias _os_sri) | os.environ.get → _os_sri.environ.get at L471+L662 |
| Wave-14 adv NI-2: 21 monitor scripts CACHE_DIR/SESSIONS still HOME/.hermes/* | _HH/cache/monitors and _HH/sessions |

### Wave 15
| Finding | Fix |
|---------|-----|
| W15-A: 82 monitor/router scripts bare OUT_FILE.write_text on shared state | tmp+replace atomic (2 batch passes) |
| W15-B: circuit-trajectory-scorer.py L105 sessions hardcoded fork profile | _RT/sessions |
| W15-C: spec-graph-extractor.py L206 argparse default hardcoded fork profile | HERMES_HOME+HERMES_PROFILE |

**Post-wave-15 saturation scan results:**
- Fork-baked profile paths in code: 0
- Bare shared-state write_text (non-atomic): 0
- os.environ NameError risks: 0
- Plugin compile errors: 0
- Cron scripts missing on disk: 0

## Artefact Inventory

Generated: 2026-10-28T09:06:14.711666+00:00 (Wave 25 saturation pass).
Covers the fork profile plus shared `~/.hermes/hermes-scripts/` canonicals.

- Canonical scripts: 378
- Fork wrappers/scripts: 296
- Two-tier both present: 224
- Canonical-only: 154
- Wrapper-only: 72

### SCRIPTS — canonical (`~/.hermes/hermes-scripts/`)

| Script | Purpose | Inputs | Outputs |
|--------|---------|--------|---------|
| `absorption-capacity-regime-monitor.py` | absorption-capacity-regime-monitor.py | CLI | cache/recall-experience-cache.json |
| `action-divergence-monitor.py` | action-divergence-monitor.py | CLI |  |
| `action-log.py` | action-log.py — Append-only, hash-chained tamper-evident action log. | CLI | cache/action-log.json |
| `adaptive-context-mesh.py` | adaptive-context-mesh.py | CLI |  |
| `adaptive-key-leakage-monitor.py` | adaptive-key-leakage-monitor.py | CLI |  |
| `adaptive-leakage-accumulator.py` | adaptive-leakage-accumulator.py | CLI |  |
| `adversarial-allocation-auditor.py` | adversarial-allocation-auditor.py | CLI |  |
| `adversarial-robustness-tester.py` | adversarial-robustness-tester.py | CLI |  |
| `adversarial_quarantine_review.py` | Adversarial review helper for skillspector_guard pending-quarantine proposals. | CLI |  |
| `afanet-failure-attributor.py` | Attribute agent failures via lightweight graph betweenness (AFANet-style). | --self-test, --json/stdin | cache/failure-attribution.json |
| `agent-action-planner.py` | agent-action-planner.py | CLI |  |
| `agent-escalation-classifier.py` | agent-escalation-classifier.py | CLI |  |
| `agent-mailbox-ipc.py` | agent-mailbox-ipc.py — File-based encrypted agent-to-agent IPC for Hermes sessions. | CLI |  |
| `am-sentry.py` | am-sentry.py — AM-Sentry memory poisoning defense: passive scanner for injection patterns. | CLI |  |
| `appa-path-taint.py` | Named-variable path-taint propagation over Hermes delegation logs. | CLI |  |
| `autonomy-router-mdp.py` | MDP autonomy router: escalate to human-in-the-loop by confidence. | --self-test | cache/autonomy-routing-state.json |
| `belief-consistency-validator.py` | belief-consistency-validator.py | CLI |  |
| `belief-probe-evaluator.py` | belief-probe-evaluator.py | CLI | cache/belief-probe-log.json |
| `belief-state-threshold-router.py` | belief-state-threshold-router.py | CLI |  |
| `benchmark-fingerprint-check.py` | benchmark-fingerprint-check.py — Pre-eval contamination check for Hermes paper sweeps. | CLI |  |
| `block-bootstrap-sprt.py` | block-bootstrap-sprt.py — Wald SPRT with block-bootstrap thresholds. | --self-test | cache/loop-pid-state.json, cache/block-bootstrap-sprt.json |
| `bound-hierarchy-monitor.py` | bound-hierarchy-monitor.py | CLI |  |
| `boundary-aware-context-allocator.py` | boundary-aware-context-allocator.py | CLI |  |
| `boundary-information-monitor.py` | boundary-information-monitor.py | CLI |  |
| `bps-skill-selector.py` | bps-skill-selector.py — Best Prefix Selection for budget-aware skill selection. | CLI |  |
| `browser_act_guard.py` | Browser-act helpers borrowed from browser-use patterns (no nested Agent). | --text/stdin, --json/stdin |  |
| `callgraph-taint-audit.py` | callgraph-taint-audit.py — Intra-procedural taint tracking (abstract interpretation). | --self-test | cache/callgraph-taint-report.json, cache/out.json |
| `canvas-offload.py` | canvas-offload.py — Mermaid canvas symbolic memory for Hermes sessions. | CLI |  |
| `cascade-error-budget-allocator.py` | cascade-error-budget-allocator.py | CLI | cache/cascade-allocation.json, cache/cascade-risk.json |
| `causal-memory-annotator.py` | causal-memory-annotator.py — Pearl causal ladder annotation for memory commits. | --self-test | cache/ue-blackbox-scores.json |
| `circuit-trajectory-scorer.py` | circuit-trajectory-scorer.py | lifecycle.db | cache/circuit-scores.json, cache/circuit-routing-hints.json |
| `citation-confidence-router.py` | Route answers by citation confidence: cite if >0.7 else silent. | --self-test | cache/citation-routing.json |
| `cmtf-tool-frontier.py` | cmtf-tool-frontier.py — Causal Minimal Tool Filtering (CMTF). | CLI |  |
| `coalitional-reviewer-panel.py` | coalitional-reviewer-panel.py | CLI |  |
| `cobra-outcome-logger.py` | cobra-outcome-logger.py — CoBRA prospective outcome logging for tool-use usefulness signals. | CLI |  |
| `cobra-skip-guard.py` | cobra-skip-guard.py — CoBRA-approximation tool-use skip guard | CLI | cache/cobra-probe.json |
| `compaction-aep-typical-set.py` | compaction-aep-typical-set.py — AEP typical-set guard for compaction. | --self-test | cache/compaction-aep-typical-set.json |
| `compaction-chain-rule-mi.py` | compaction-chain-rule-mi.py — Shannon chain rule on multi-stage compact. | --self-test | cache/compaction-chain-rule-mi.json |
| `compaction-rd-advisor.py` | compaction-rd-advisor.py — Pareto pick from eval R-D curve. | CLI | cache/eval-compaction-results.json, cache/compaction-rd-advice.json |
| `compaction-rd-converse.py` | compaction-rd-converse.py — Shannon rate-distortion converse for compaction. | --self-test | cache/context-channel-capacity.json, cache/compaction-rd-converse.json |
| `concept-lattice-index.py` | concept-lattice-index.py — ContextRAG-style nightly concept lattice over Hindsight facts. | CLI | cache/concept-lattice.json |
| `consensus-convergence-monitor.py` | consensus-convergence-monitor.py | CLI | cache/consensus-state.json, cache/consensus-alarm.json |
| `consensus-reward-scorer.py` | consensus-reward-scorer.py | CLI |  |
| `consistency_scorer.py` | Consistency-sampled calibrated confidence scorer for Hermes. | CLI | cache/calibration-log.json |
| `constraint-alignment-validator.py` | constraint-alignment-validator.py | CLI |  |
| `constraint-binding-lint.py` | constraint-binding-lint.py — Detect Constraint Weakening (arXiv:2608.24569). | CLI |  |
| `constraint-validator-with-rollback.py` | constraint-validator-with-rollback.py | CLI | cache/hermes-math-sweep-latest.json |
| `containment-monitor.py` | containment-monitor.py | CLI |  |
| `context-budget-potential-monitor.py` | context-budget-potential-monitor.py | CLI |  |
| `context-channel-capacity.py` | context-channel-capacity.py — mutual-information proxy at compaction. | --self-test | cache/rd-compaction-advisory.json, cache/context-channel-capacity.json |
| `continuity_token.py` | CONTINUITY signed context-token for delegate_task child construction. | CLI |  |
| `corpus-consolidation-index.py` | corpus-consolidation-index.py — Unify the three Hermes research corpora. | CLI | cache/cs-interpretation-latest.json, cache/math-interpretation-latest.json |
| `cost-aware-eval-framework.py` | Cost-aware evaluation: success rate minus alpha * normalized cost. | --self-test, --json/stdin | cache/cost-aware-eval.json |
| `cost-cutoff-task-router.py` | cost-cutoff-task-router.py | CLI |  |
| `cot-injection-detector.py` | cot-injection-detector.py | CLI |  |
| `counterfactual-context-filter.py` | counterfactual-context-filter.py — Decision-Aware Memory Cards (R3). | --json/stdin |  |
| `counterfactual-tool-gate.py` | counterfactual-tool-gate.py — Pearl Rung-3 minimal tool-set gate. | --self-test |  |
| `critique-bank.py` | critique-bank.py — CritICL critique bank for inference-time failure conditioning. | CLI | cache/critique-bank.json |
| `cron-sandbox-runner.py` | cron-sandbox-runner.py — invoke OpenShell wrapper for Hermes cron jobs. | --self-test |  |
| `cs-paper-interpreter.py` | cs-paper-interpreter.py | CLI | cache/hermes-cs-sweep-latest.json |
| `cs-primers-overnight.py` | cs-primers-overnight.py | CLI |  |
| `cs-research-sweep.py` | cs-research-sweep.py | CLI |  |
| `cusum-gain-freeze.py` | cusum-gain-freeze.py — Liberzon: freeze PID gains after CUSUM. | --self-test | cache/cusum-gain-freeze.json |
| `cusum-h-calibrator.py` | cusum-h-calibrator.py — Calibrate Page CUSUM threshold h for ARL_0 >= 500. | --self-test | cache/loop-pid-state.json, cache/cusum-h-calibration.json |
| `dcr-compute-router.py` | Route queries between divergent and convergent reasoning (DCR). | --self-test, --text/stdin | cache/dcr-routing.json |
| `dcr-reconcile.py` | dcr-reconcile.py — Divergent-Convergent Reconciliation for Hermes. | CLI |  |
| `diff-impact.py` | diff-impact.py — code impact analysis from git diffs. | --json/stdin |  |
| `divergence-curvature-monitor.py` | divergence-curvature-monitor.py | CLI |  |
| `dual-backend-memory-fuser.py` | dual-backend-memory-fuser.py | --json/stdin |  |
| `duality-gap-monitor.py` | duality-gap-monitor.py | CLI | cache/duality-alarm.json, cache/circuit-scores.json |
| `embedding-based-context-compactor.py` | embedding-based-context-compactor.py | CLI |  |
| `entropy-fidelity-stability-monitor.py` | entropy-fidelity-stability-monitor.py | lifecycle.db | cache/entropy-fidelity-alarm.json |
| `epistemic-state-tracker.py` | epistemic-state-tracker.py — K/B/C epistemic state table. | --self-test | cache/epistemic-state.json, cache/epistemic-regressions.json, cache/consistency-scores.json |
| `eval-compaction-data-bridge.py` | eval-compaction-data-bridge.py — wire compaction eval output into IT scripts. | --self-test | cache/current-token-count.json |
| `eval-compaction-distortion-gate.py` | eval-compaction-distortion-gate.py — character-level Jaccard distortion gate. | --self-test |  |
| `eval-hindsight-ingest.py` | Ingest needle lines into local hindsight-episodes.jsonl. | --self-test | cache/hindsight-episodes.json |
| `eval-memory-planted-needle.py` | eval-memory-planted-needle.py — LongMemEval-style planted-fact recall. | --self-test, --json/stdin | cache/eval-memory-planted-needle.json |
| `eval-routing-linucb-features.py` | eval-routing-linucb-features.py — 8-d contextual LinUCB on qrels.jsonl. | --self-test | cache/skill-router-index.json, cache/qrels.json, cache/eval-routing-linucb-features.json |
| `eval-shadow-synthetic.py` | eval-shadow-synthetic.py — Write synthetic shadow telemetry JSONL. | --self-test |  |
| `evo-harness-compile.py` | Propose harness-skill updates from session summaries. | --json/stdin |  |
| `evograph-skill-editor.py` | evograph-skill-editor.py — EvoGraph-Mem failure-aware skill insight editor. | CLI | cache/evograph-insight-graph.json, cache/skill-yield-state.json |
| `experience-verifier.py` | experience-verifier.py | CLI |  |
| `explanation-narrativizer.py` | explanation-narrativizer.py | CLI |  |
| `fact-attribution-verifier.py` | Verify factual claims in output are attributed to sources (SEVA). | --self-test, --text/stdin | cache/fact-attribution.json |
| `federated-consensus-monitor.py` | federated-consensus-monitor.py | CLI |  |
| `feedback-budget-optimizer.py` | feedback-budget-optimizer.py | CLI | cache/feedback-budget.json |
| `feedback-memory-ranker.py` | UCB episode-replay ranker for tool sequences. | --self-test | cache/feedback-memory-ranker-state.json |
| `feedback-robustness-scorer.py` | Huber-loss robust regression on skill feedback (delta=1.35). | --self-test, routing-events.jsonl, lifecycle.db | cache/routing-events.json, cache/skill-robustness-scores.json |
| `filter-only-optimization-reducer.py` | filter-only-optimization-reducer.py | CLI |  |
| `firecrawl_stealth_fetch.py` |  | --json/stdin |  |
| `focus_compress.py` | focus_compress.py — Focus Agent intra-trajectory compression helper for Hermes. | CLI |  |
| `free-energy-task-optimizer.py` | free-energy-task-optimizer.py | CLI |  |
| `frequency-stability-monitor.py` | frequency-stability-monitor.py | lifecycle.db | cache/freq-stability-alarm.json, cache/circuit-scores.json |
| `gdop-aware-tool-selector.py` | gdop-aware-tool-selector.py | CLI | cache/gdop-tool-chains.json |
| `gepa_skill_eval.py` | GEPA Skill Evaluation Harness | CLI |  |
| `governance-conflict-detector.py` | governance-conflict-detector.py — Multi-principal conflict surface. | --self-test | cache/governance-conflicts.json, cache/governance-conflict-summary.json, cache/tool-auth-gate-log.json, cache/governance |
| `governance-conflict-epistemic.py` | governance-conflict-epistemic.py — TYPE_A is not common knowledge of DENY. | --self-test | cache/governance-conflict-epistemic.json |
| `governance-falsifiability-lint.py` | governance-falsifiability-lint.py — Popper/Critch failure_observable gate. | --self-test | cache/governance-falsifiability-report.json, cache/improvement-proposals.json |
| `hallucination-detector.py` | Blackbox UE hallucination detector (zlib CCR, hedge, trigram Jaccard). | --self-test, --text/stdin, lifecycle.db |  |
| `hermes-chat-sync-precheck.py` | hermes-chat-sync-precheck.py | CLI |  |
| `hermes-hud.py` | hermes-hud — live status of active subagents and session budget | CLI |  |
| `hermes-math-sweep.py` | hermes-math-sweep.py | CLI |  |
| `hermes-memory-drift-audit.py` |  | CLI |  |
| `hermes-research-sweep.py` |  | CLI | cache/seen_papers.json |
| `hierarchy-coherence-monitor.py` | hierarchy-coherence-monitor.py | CLI |  |
| `hierarchy-radius-monitor.py` | hierarchy-radius-monitor.py | CLI |  |
| `hindsight-reembed.py` | hindsight-reembed.py — Batch re-embed all NULL-embedding rows in Hindsight DB | CLI |  |
| `hindsight-watchdog.py` | hindsight-watchdog.py - Proactive Hindsight health monitor | CLI |  |
| `horizon-constraint-validator.py` | horizon-constraint-validator.py | CLI |  |
| `impact-regularizer-gate.py` | impact-regularizer-gate.py — Amodei cat.3 side-effect footprint. | --self-test | cache/impact-regularizer-alarm.json |
| `improvement_governance.py` | Improvement Governance for Hermes self-improvement proposals. | CLI | cache/governance-rate-state.json |
| `information-bottleneck-monitor.py` | information-bottleneck-monitor.py | CLI |  |
| `information-refinement-utility-monitor.py` | information-refinement-utility-monitor.py | CLI |  |
| `iss-justification-gate.py` | iss-justification-gate.py — Passivity/sector/nyquist certificate gate. | --self-test | cache/iss-justification.json |
| `issue-to-agents.py` | issue-to-agents.py — Route open GitHub issues to Hermes subagents with worktree isolation | --json/stdin |  |
| `iterative-critique-convergence-monitor.py` | iterative-critique-convergence-monitor.py | CLI |  |
| `jev-scores-staleness-check.py` | jev-scores-staleness-check.py — Sentinel for missing jev-turn-scores producer. | --self-test | cache/jev-scores-missing-alarm.json |
| `jev_compaction.py` |  | CLI |  |
| `jev_verify_fn.py` | jev_verify_fn.py | CLI | cache/calibration-log.json, cache/jev-call-budget.json |
| `kg-contradiction-check.py` | kg-contradiction-check.py — Lightweight KG contradiction detector (M3). | CLI |  |
| `kl-curvature-memory-monitor.py` | kl-curvature-memory-monitor.py | --self-test |  |
| `kl-skill-prior.py` | KL-distance skill prior (heuristic, not Sanov's theorem). | --json/stdin, lifecycle.db |  |
| `l01-efficiency.py` |  | --text/stdin |  |
| `l1-context-offload.py` | l1-context-offload.py — LangChain-style 3-tier context offload for Hermes sessions. | --text/stdin |  |
| `l1-extract.py` | l1-extract.py — lockfile wrapper + bytecode restore. | CLI |  |
| `l1-gmemory-consolidation.py` | l1-gmemory-consolidation.py — Three-tier G-Memory nightly cross-session consolidation. | CLI | cache/h2-obstructions.json |
| `l1-gmemory-consolidation.restored.py` |  | CLI |  |
| `l1-graphiti-reconcile.py` | l1-graphiti-reconcile.py — Scatter-gather reconciliation for the Hindsight → Graphiti write path. | CLI |  |
| `l1-graphiti-write.py` | l1-graphiti-write.py — Write staged Hindsight facts to Graphiti as episodes. | CLI |  |
| `l1-hypermem-promote.py` | l1-hypermem-promote.py — HyperMem episode grouping at l1-promote time. | CLI | cache/hypermem-promote.json |
| `l1-promote.py` | l1-promote.py — extract-running lock + bytecode restore. | CLI |  |
| `l1-tracegrant.py` | l1-tracegrant.py — Shared TraceGrant namespace policy + grant log for the l1 memory pipeline. | lifecycle.db |  |
| `legendre-state-compactor.py` | legendre-state-compactor.py | CLI | cache/legendre-compaction.json |
| `lifecycle-schema-extension.py` | Add episode DAG and step snapshot tables to lifecycle.db (idempotent). | --self-test, lifecycle.db |  |
| `loop-cusum-changepoint.py` | loop-cusum-changepoint.py — Page CUSUM on PID error (Wald/Page). | --self-test | cache/cusum-state.json, cache/loop-cusum-changepoint.json, cache/loop-cusum-baseline.json, cache/cusum-h-calibration.jso |
| `loop-lyapunov-stability.py` | loop-lyapunov-stability.py — empirical Lyapunov decrease on loop-pid history. | --self-test | cache/loop-lyapunov-stability.json, cache/loop-pid-state.json |
| `loop-model-comparison.py` | loop-model-comparison.py — Sequential Bayesian comparison of PID error models. | --self-test | cache/loop-model-comparison.json, cache/loop-pid-state.json |
| `loop-pid-cron-step.py` | Cron stepper for the session-stability PID loop. | --self-test | cache/loop-pid-state.json |
| `loop-pid-iss-wrapper.py` | loop-pid-iss-wrapper.py — Composite Lyapunov + ISS + two-timescale check. | --self-test | cache/loop-stability-composite.json, cache/pid-passivity-index.json, cache/pid-circle-criterion.json, cache/nyquist-time |
| `loop-pid-synthetic-step.py` | loop-pid-synthetic-step.py — Bootstrap PID history for Lyapunov/ISS eval. | --self-test | cache/loop-pid-state.json |
| `loop-pid.py` | Discrete PID controller for agent retry/refinement loops. | CLI | cache/loop-pid-state.json |
| `loop-rollout-horizon.py` | loop-rollout-horizon.py — Bertsekas one-step rollout when PID model fails. | --self-test | cache/loop-pid-state.json, cache/loop-rollout-horizon.json |
| `ltl-promotion-invariant.py` | ltl-promotion-invariant.py — Clarke LTL G(PROMOTE -> failure_observable). | --self-test | cache/ltl-promotion-invariant.json |
| `lyapunov-analysis.py` | KHALIL-3: Lyapunov stability analysis for Hermes agent loops. | CLI |  |
| `magnitude-mirage-calibrator.py` | magnitude-mirage-calibrator.py | CLI |  |
| `mask-coupling-monitor.py` | mask-coupling-monitor.py | CLI |  |
| `math-paper-interpreter.py` | math-paper-interpreter.py | CLI | cache/hermes-math-sweep-latest.json |
| `math-prefetch-abstracts.py` | math-prefetch-abstracts.py — Pre-populate math sweep JSON with titles + abstracts. | CLI | cache/hermes-math-sweep-latest.json |
| `math-primers-overnight.py` | math-primers-overnight.py | lifecycle.db |  |
| `mcp-privilege-audit.py` | MCP least-privilege auditor (cs-mcp-overpriv / arXiv:2603.21641). | CLI | cache/mcp-privilege-alarm.json |
| `memory-access-decay.py` | memory-access-decay.py — access-weighted retention decay. | --self-test, lifecycle.db | cache/memory-access-decay-apply-state.json, cache/memory-access-decay.json |
| `memory-adaptive-rank.py` | memory-adaptive-rank.py — concentration-bound adaptive SVD rank. | --self-test | cache/memory-svd-singular.json, cache/memory-eckart-young.json, cache/memory-adaptive-rank.json |
| `memory-auto-improvement.py` | memory-auto-improvement.py — session-log review → proposed memory/skill patches. | --self-test | cache/memory-auto-improvement.json |
| `memory-bethe-free-energy.py` | memory-bethe-free-energy.py — Bethe entropy on Jaccard memory graph. | --self-test | cache/memory-bethe-free-energy.json |
| `memory-bits-back.py` | memory-bits-back.py — MacKay bits-back identity on memory latents. | --self-test | cache/memory-bits-back.json |
| `memory-conductance-ttl.py` | memory-conductance-ttl.py — Cheeger conductance TTL floor. | --self-test | cache/memory-mixing-ttl.json, cache/memory-conductance-ttl.json |
| `memory-coupling-merge.py` | memory-coupling-merge.py — OT coupling merge of two memory snapshots. | --self-test |  |
| `memory-displacement-convexity.py` | memory-displacement-convexity.py — McCann displacement convexity of entropy. | --self-test | cache/memory-ot-decay.json, cache/memory-displacement-convexity.json |
| `memory-dkw-ue.py` | memory-dkw-ue.py — DKW inequality band on empirical UE CDF. | --self-test | cache/memory-dkw-ue.json |
| `memory-doob-decompose.py` | memory-doob-decompose.py — Doob decomposition of working-memory entries. | --self-test, --json/stdin |  |
| `memory-doob-strata-consumer.py` | memory-doob-strata-consumer.py — Score working-memory by Doob stratum. | --self-test | cache/doob-quality-advisory.json |
| `memory-eckart-young.py` | memory-eckart-young.py — truncated SVD memory compressor (Axler). | --self-test | cache/memory-svd-basis.json |
| `memory-fano-bound.py` | memory-fano-bound.py — Fano lower bound on retrieval error after compaction. | --self-test | cache/context-channel-capacity.json, cache/memory-fano-bound.json |
| `memory-gelman-shrink.py` | memory-gelman-shrink.py — hierarchical partial pooling of importance. | --self-test | cache/memory-ot-decay.json, cache/memory-gelman-shrink.json |
| `memory-haar-mra.py` | memory-haar-mra.py — Haar multi-resolution energy of UE / access path. | --self-test | cache/memory-haar-mra.json |
| `memory-heisenberg-tf.py` | memory-heisenberg-tf.py — time–frequency uncertainty of UE path. | --self-test | cache/memory-heisenberg-tf.json |
| `memory-hitting-time.py` | memory-hitting-time.py — Brownian hitting time as commit wait. | --self-test | cache/memory-hitting-time.json |
| `memory-jl-distortion.py` | memory-jl-distortion.py — Johnson–Lindenstrauss hash-embedding check. | --self-test | cache/memory-jl-distortion.json |
| `memory-kalman-latent.py` | memory-kalman-latent.py — 1D Kalman filter for scalar numeric memory facts. | --self-test |  |
| `memory-kraft-code.py` | memory-kraft-code.py — Kraft inequality on memory description lengths. | --self-test | cache/memory-kraft-code.json |
| `memory-lens.py` | memory-lens.py — Harper PFPL / Reynolds separation lens laws for WM. | --self-test |  |
| `memory-log-ode-sig.py` | memory-log-ode-sig.py — log-ODE reconstruction of a memory path. | --self-test | cache/memory-log-ode-sig.json |
| `memory-lp-dct-gate.py` | memory-lp-dct-gate.py — L^p / dominated-convergence gate on UE streams. | --self-test | cache/memory-lp-dct-gate.json |
| `memory-malliavin-ibp.py` | memory-malliavin-ibp.py — Gaussian integration-by-parts sensitivity. | --self-test | cache/memory-malliavin-ibp.json |
| `memory-matrix-bernstein.py` | memory-matrix-bernstein.py — matrix Bernstein on hash Gram. | --self-test | cache/memory-matrix-bernstein.json |
| `memory-mcdiarmid-rrf.py` | memory-mcdiarmid-rrf.py — bounded-differences retrieval score (Lugosi, Vershynin). | --self-test |  |
| `memory-mixing-ttl.py` | memory-mixing-ttl.py — mixing-time lower bound vs TTL (Hairer, Durrett). | --self-test, lifecycle.db | cache/ripple-mem-recall.json, cache/memory-mixing-ttl.json |
| `memory-monad.py` | memory-monad.py — MemoryMonad: Categorical wrapper for Hermes memory operations. | CLI | cache/memory-monad.json, cache/hyperskill-combos.json, cache/provenance-graph.json |
| `memory-ontology-topology.py` | memory-ontology-topology.py — Ghrist applied topology over the skill ontology. | --self-test | cache/concept-lattice.json, cache/taxonomy-candidates.json, cache/relation-triples.json, cache/ontology-topology-state.j |
| `memory-optional-stopping.py` | memory-optional-stopping.py — optional sampling bound on SPRT stopping. | --self-test | cache/memory-sprt-decisions.json, cache/memory-optional-stopping.json |
| `memory-ot-decay.py` | memory-ot-decay.py — Wasserstein-1 geodesic forgetting. | --self-test | cache/memory-ot-decay.json |
| `memory-portmanteau.py` | memory-portmanteau.py — Billingsley portmanteau on split UE laws. | --self-test | cache/memory-portmanteau.json |
| `memory-provenance.py` | memory-provenance.py — Provenance edge store for dependency-guided rollback. | CLI | cache/trust-posterior.json |
| `memory-query-router.py` | memory-query-router.py — Query-type routing for Hermes memory retrieval. | --json/stdin | cache/routing-calibration.json, cache/routing-weights.json |
| `memory-ransac-commit.py` | memory-ransac-commit.py — RANSAC-style outlier gate before memory commit. | --self-test |  |
| `memory-redundancy-gate.py` | Lexical redundancy gate for MEMORY.md / USER.md (not Hindsight, not Shannon). | CLI |  |
| `memory-reference-frequency.py` | memory-reference-frequency.py — Bayesian TTL from reference frequency. | --self-test | cache/memory-reference-frequency.json |
| `memory-relation-extractor.py` | memory-relation-extractor.py — LLMs4OL Task C analog (Non-Taxonomic Relation Extraction). | --self-test | cache/relation-triples.json, cache/wave22ol-relation-alarm.json |
| `memory-renorm-counterterm.py` | memory-renorm-counterterm.py — Hairer Wick/renormalization of UE products. | --self-test | cache/memory-renorm-counterterm.json |
| `memory-rough-signature.py` | memory-rough-signature.py — order-2 rough-path signature of irregular events. | --self-test | cache/memory-rough-signature.json |
| `memory-sanov-ld.py` | memory-sanov-ld.py — Sanov large-deviation test on UE histograms. | --self-test | cache/memory-sanov-ld.json |
| `memory-signature-rerank.py` | memory-signature-rerank.py — rough-path signature re-ranking. | --self-test | cache/memory-signature-rerank.json |
| `memory-sprt-commit.py` | memory-sprt-commit.py — Wald SPRT stopping rule for memory commit. | --self-test |  |
| `memory-staleness.py` | memory-staleness.py — Typed memory staleness detector for Hermes MEMORY.md. | CLI |  |
| `memory-taxonomy-discover.py` | memory-taxonomy-discover.py — LLMs4OL Task B analog. | --self-test | cache/wave22ol-taxonomy-alarm.json |
| `memory-term-typer.py` | memory-term-typer.py — LLMs4OL Task A analog. | --self-test | cache/wave22ol-term-typer-alarm.json |
| `memory-ttl-floor-merge.py` | memory-ttl-floor-merge.py — merge spectral-gap and Cheeger TTL floors. | --self-test | cache/memory-conductance-ttl.json, cache/memory-ttl-floor.json, cache/wave21a-memory-ttl-floor-alarm.json |
| `memory-ttl-purge.py` | memory-ttl-purge.py — TTL enforcement for Hermes staged memories. | lifecycle.db | cache/recall-misses.json, cache/adaptive-ttl-state.json |
| `memory-voi-consolidation.py` | memory-voi-consolidation.py — VOI-gated G-Memory consolidation trigger. | --self-test, lifecycle.db |  |
| `memory-wave18-adversarial.py` | memory-wave18-adversarial.py — cold attacker pass on Wave 18 memory scripts. | --self-test |  |
| `memory-wave18-invariants.py` | memory-wave18-invariants.py — property tests for Wave 18 memory hard cores. | --self-test | cache/memory-wave18-invariants.json |
| `memory-zscore-retention.py` | memory-zscore-retention.py — Z-score based memory retention policy. | lifecycle.db |  |
| `merge-beta-seed.py` | One-time merge of BM25-seeded beta priors into live skill-beta-state.json. | CLI | cache/skill-beta-state-seeded.json, cache/skill-beta-state.json |
| `merkle-evidence-chain.py` | Merkle-linked evidence chain for tool-call provenance. | --self-test |  |
| `merkle-skill-check.py` | merkle-skill-check.py — Merkle root over all SKILL.md SHA256 hashes. | CLI | cache/skill-merkle.json |
| `metacognitive-harness.py` | Metacognitive Harness for Hermes Agent | CLI | cache/calibration-log.json, cache/confidence-trajectory.json |
| `minority-sentinel.py` | minority-sentinel.py — Meta-classifier for Hermes swarm/multi-agent consensus. | --json/stdin | cache/minority-sentinel-stats.json |
| `monitor-suite-runner.py` | monitor-suite-runner.py | CLI | cache/alarm-summary.json |
| `motion-dsl-compiler.py` | motion-dsl-compiler.py | CLI |  |
| `msprt-shadow-gate.py` | msprt-shadow-gate.py — Mixture SPRT wrapper for the nightly shadow gate. | --self-test | cache/msprt-shadow-gate.json |
| `multimodal-skill-decomposer.py` | multimodal-skill-decomposer.py | CLI |  |
| `mutation-rubric-engine.py` | Bloom-filter mutation testing for LLM tool-call evaluation rubrics. | --self-test |  |
| `news_diff_watchdog.py` | news_diff_watchdog.py - Hermes cron watchdog: emits new news items only. | CLI | cache/seen_items.json |
| `nuisance-parameter-projector.py` | nuisance-parameter-projector.py | CLI | cache/nuisance-projector-calibration.json |
| `nyquist-timescale-bridge.py` | nyquist-timescale-bridge.py — Consistency of Nyquist aliasing vs two-timescale. | --self-test | cache/nyquist-timescale-bridge.json, cache/nyquist-bandwidth.json, cache/two-timescale.json |
| `observation-budget-allocator.py` | Secretary-problem / Bayes-factor allocator for cached-intent re-checks. | --self-test |  |
| `obstruction-certificate-cache.py` | Cron stub: quantify removal risk for stale skills and memory entries. | --self-test, lifecycle.db | cache/obstruction-certificate-cache.json |
| `occam-skill-ranker.py` | Occam-weighted skill ranker (MACKAY-1 coverage volume ratio). | CLI | cache/ranker-policy.json |
| `omni_skill_scan.py` | omni_skill_scan.py — Scheduled GEPA Omni continuous improvement driver. | CLI |  |
| `online-allocation-regret-monitor.py` | online-allocation-regret-monitor.py | CLI |  |
| `online-threshold-skill-router.py` | online-threshold-skill-router.py | CLI |  |
| `ot_utils.py` | ot_utils.py — Shared Optimal Transport utility for Hermes scripts. | CLI |  |
| `output-formalizer-verifier.py` | Output formalizer/verifier: JSON, completeness, repetition, emptiness. | --self-test, --text/stdin, lifecycle.db |  |
| `output-length-predictor.py` | output-length-predictor.py | CLI |  |
| `parametric-retrieval-validator.py` | parametric-retrieval-validator.py | --text/stdin |  |
| `pareto-phase-router.py` | pareto-phase-router.py | CLI |  |
| `pareto-resource-allocator.py` | pareto-resource-allocator.py | CLI | cache/pareto-allocations.json |
| `participation-surplus-monitor.py` | participation-surplus-monitor.py | CLI |  |
| `pddl-state-abstractor.py` | Abstract a task description into PDDL-like typed objects, predicates, transitions. | --self-test, --text/stdin | cache/pddl-state.json |
| `perception-reasoning-splitter.py` | Split agent errors into perception failures vs reasoning failures. | --self-test, --json/stdin | cache/perception-reasoning-split.json |
| `performative-stability-monitor.py` | performative-stability-monitor.py | CLI |  |
| `pid-circle-criterion.py` | pid-circle-criterion.py — Sector nonlinearity of PID saturation. | --self-test | cache/pid-circle-criterion.json, cache/loop-pid-state.json |
| `pid-passivity-index.py` | pid-passivity-index.py — Khalil/Sontag passivity of the PID loop. | --self-test | cache/pid-passivity-index.json, cache/loop-pid-state.json |
| `plan-commitment.py` | plan-commitment.py — SHA256 commitment scheme for agent plans. | CLI |  |
| `plan-enforcement-gate.py` | plan-enforcement-gate.py | CLI |  |
| `pre-compact-annotate.py` | pre-compact-annotate.py — Pre-compaction signal annotation for Hermes sessions. | CLI |  |
| `prediction-tradeoff-monitor.py` | prediction-tradeoff-monitor.py | CLI |  |
| `prestudy-cache-manager.py` | prestudy-cache-manager.py | CLI |  |
| `priority-intersection-matcher.py` | priority-intersection-matcher.py | CLI |  |
| `privacy-capacity-router.py` | privacy-capacity-router.py | CLI |  |
| `privacy-constrained-skill-router.py` | privacy-constrained-skill-router.py | CLI |  |
| `process-reward-ranker.py` | Rank candidate process steps by a lightweight process reward model (SWE-TRACE). | --self-test, --json/stdin | cache/process-reward-rankings.json |
| `process-verifier-agent.py` | Verify multi-agent process traces against invariants. | --self-test, --json/stdin | cache/process-verification-report.json |
| `profinite-thread-check.py` | profinite-thread-check.py — Profinite thread-validity gate for memory promotion. | CLI | cache/profinite-threads.json, cache/h2-obstructions.json |
| `progress-mirage-gate.py` | progress-mirage-gate.py — Out-of-band grounded evaluation gate. | CLI |  |
| `projection-implication-scorer.py` | projection-implication-scorer.py | CLI | cache/projection-skill-index.json |
| `promotion-at-most-once.py` | promotion-at-most-once.py — Lynch at-most-once of SPRT PROMOTE. | --self-test | cache/promotion-ledger.json, cache/promotion-at-most-once.json |
| `proportionality-monitor.py` | proportionality-monitor.py | CLI |  |
| `quantization-behavior-monitor.py` | quantization-behavior-monitor.py | CLI |  |
| `quantization-state-divergence-monitor.py` | quantization-state-divergence-monitor.py | CLI |  |
| `quickest-change-detector.py` | quickest-change-detector.py | CLI |  |
| `racs-prefix-tracker.py` | RACS prefix-drift tracker for Hermes sessions. | CLI | cache/racs-state.json |
| `radius-hierarchy-monitor.py` | radius-hierarchy-monitor.py | CLI |  |
| `rd-compaction-advisor.py` | Rate-distortion-*shaped* compaction aggressiveness advisor. | CLI | cache/rd-compaction-advisory.json, cache/eval-compaction-results.json, cache/current-token-count.json |
| `real-options-deployment-gate.py` | real-options-deployment-gate.py | CLI |  |
| `reasoning-complexity-classifier.py` | reasoning-complexity-classifier.py — Adaptive reasoning depth classifier for Hermes. | --text/stdin | cache/reasoning-calibration.json |
| `reasoning-hooks.py` | Runtime consumer for loop_harness.reasoning_hooks + feature_list.json. | CLI | cache/kapro-check.json, cache/feature_list.json |
| `reasoning-trace-evaluator.py` | Score whether a reasoning trace helps human evaluation of LLM outputs. | --self-test, --text/stdin | cache/reasoning-trace-eval-log.json |
| `reasoning-ue-integrator.py` | reasoning-ue-integrator.py — Central reasoning predicate dispatcher. | --self-test | cache/ue-blackbox-scores.json, cache/consistency-scores.json, cache/ue-perplexity-proxy.json, cache/calibration-log.json |
| `recovery-classifier.py` | Recovery Classifier for Hermes Agent | CLI |  |
| `recursive-causal-explorer.py` | recursive-causal-explorer.py | CLI |  |
| `recursive-exploration-manager.py` | recursive-exploration-manager.py | CLI | cache/recursive-exploration-manager-report.json |
| `recursive-reasoner-skill.py` | recursive-reasoner-skill.py | CLI |  |
| `redundancy-stability-monitor.py` | redundancy-stability-monitor.py | CLI |  |
| `regime-transition-monitor.py` | regime-transition-monitor.py | CLI | cache/regime-transition-alarm.json |
| `relaxation-gap-monitor.py` | relaxation-gap-monitor.py | CLI |  |
| `relay-routing-capacity-allocator.py` | relay-routing-capacity-allocator.py | CLI |  |
| `relevance-scorer.py` | relevance-scorer.py | CLI |  |
| `retrieval-saturation-monitor.py` | retrieval-saturation-monitor.py | CLI | cache/retrieval-saturation.json, cache/retrieval-saturation-alarm.json |
| `retry-budget-guard.py` | retry-budget-guard.py — 5-class error retry budget for Hermes pipeline scripts. | CLI | cache/retry-budget-state.json |
| `ripple-mem-expander.py` | ripple-mem-expander.py — RippleMem-inspired associative memory expansion. | CLI | cache/ripple-mem-graph.json |
| `robustness-cost-governance-router.py` | robustness-cost-governance-router.py | CLI |  |
| `route-preemption-scheduler.py` | route-preemption-scheduler.py | CLI |  |
| `routing-alarm-bridge.py` | routing-alarm-bridge.py — promote routing JSON `alarm` flags to *-alarm.json. | --self-test | cache/routing-conflicts.json, cache/routing-conflicts-alarm.json, cache/routing-alarm-bridge.json, cache/skill-descripti |
| `routing-azuma-concentration.py` | routing-azuma-concentration.py — Azuma-Hoeffding tail on routing regret. | --self-test | cache/routing-regret-log.json, cache/routing-azuma-concentration.json |
| `routing-belief-propagation.py` | routing-belief-propagation.py — loopy BP on the skill-overlap MRF. | --self-test | cache/skill-router-index.json, cache/skill-beta-state.json, cache/routing-belief-propagation.json |
| `routing-boolean-influence.py` | routing-boolean-influence.py — O'Donnell influence of description tokens on top-1. | --self-test | cache/skill-router-index.json, cache/routing-boolean-influence.json |
| `routing-convergence-guard.py` | routing-convergence-guard.py — VIL-2 + VIL-7 | CLI |  |
| `routing-exp3-adversarial.py` | routing-exp3-adversarial.py — EXP3 mixed strategy over skills. | --self-test | cache/skill-router-index.json, cache/skill-beta-state.json, cache/routing-exp3-skill-weights.json, cache/routing-exp3-st |
| `routing-exp4-contextual.py` | routing-exp4-contextual.py — EXP4 contextual experts over skills. | --self-test | cache/skill-router-index.json, cache/skill-beta-state.json, cache/routing-exp4-state.json |
| `routing-fano-bound.py` | routing-fano-bound.py — Fano inequality lower bound on router error. | --self-test | cache/skill-router-index.json, cache/skill-beta-state.json, cache/calibration-log.json, cache/routing-exp3-state.json |
| `routing-graph-bandit-update.py` | routing-graph-bandit-update.py — graph-structured bandit credit on the skill lattice. | --self-test | cache/skill-beta-state.json, cache/skill-beta-state.prev.json, cache/concept-lattice.json, cache/skill-router-index.json |
| `routing-graph-independence.py` | routing-graph-independence.py — independence number of the skill-overlap graph. | --self-test | cache/skill-router-index.json, cache/routing-graph-independence.json |
| `routing-hamming-audit.py` | routing-hamming-audit.py — Jaccard distance over skill-description n-grams. | --self-test | cache/routing-hamming-alarm.json |
| `routing-ips-offpolicy.py` | routing-ips-offpolicy.py — inverse-propensity evaluation of a target routing policy. | --self-test | cache/routing-exp3-log.json, cache/routing-ips-offpolicy.json, cache/routing-exp3-skill-weights.json |
| `routing-kl-ucb.py` | routing-kl-ucb.py — Bernoulli KL-UCB indices from beta-bandit state. | --self-test | cache/skill-beta-state.json, cache/routing-kl-ucb.json |
| `routing-linucb.py` | routing-linucb.py — LinUCB ridge contextual bandit over hashed skill features. | --self-test | cache/skill-router-index.json, cache/skill-beta-state.json, cache/routing-linucb-state.json, cache/routing-linucb.json |
| `routing-mcdiarmid-bm25.py` | routing-mcdiarmid-bm25.py — McDiarmid bounded-differences radius on BM25 top-gap. | --self-test | cache/skill-router-index.json, cache/routing-mcdiarmid-bm25.json |
| `routing-mobius-audit.py` | routing-mobius-audit.py — poset Mobius inversion for BM25 inclusion-exclusion. | --self-test | cache/skill-router-index.json, cache/routing-mobius-audit.json |
| `routing-mutual-information.py` | routing-mutual-information.py — I(S; Q) informativeness of the skill codebook. | --self-test | cache/skill-router-index.json, cache/skill-beta-state.json, cache/routing-mutual-information.json |
| `routing-pac-bayes-bound.py` | routing-pac-bayes-bound.py — McAllester PAC-Bayes bound on skill-router error. | --self-test, routing-events.jsonl | cache/skill-beta-state.json, cache/routing-events.json, cache/routing-pac-bayes.json |
| `routing-precision-recall.py` | routing-precision-recall.py — P@k / R@k of BM25 self-rank vs beta successes. | --self-test | cache/skill-router-index.json, cache/skill-beta-state.json, cache/routing-precision-recall.json |
| `routing-rademacher-bound.py` | routing-rademacher-bound.py — empirical Rademacher complexity of BM25 scoring. | --self-test | cache/skill-beta-state.json, cache/skill-router-index.json, cache/routing-rademacher-bound.json |
| `routing-skill-markov.py` | routing-skill-markov.py — bigram skill-transition entropy from calibration-log. | --self-test | cache/calibration-log.json, cache/routing-calibration.json, cache/routing-skill-markov.json |
| `routing-skill-percolation.py` | routing-skill-percolation.py — giant-component percolation of the Jaccard skill graph. | --self-test | cache/skill-router-index.json, cache/routing-skill-percolation.json |
| `routing-switching-detector.py` | routing-switching-detector.py — CUSUM / discounted-mean shift on beta posteriors. | --self-test | cache/skill-beta-state.json, cache/routing-switching-state.json, cache/routing-switching-detector.json |
| `routing-token-setcover.py` | routing-token-setcover.py — greedy set-cover of query tokens by skill descriptions. | --self-test | cache/skill-router-index.json, cache/routing-token-setcover.json |
| `routing-tsallis-inf.py` | routing-tsallis-inf.py — 1/2-Tsallis-INF (best-of-both-worlds) mix over skills. | --self-test | cache/skill-router-index.json, cache/skill-beta-state.json, cache/routing-tsallis-inf.json |
| `routing-wald-sprt.py` | routing-wald-sprt.py — Wald SPRT explore/exploit stop for each skill arm. | --self-test | cache/skill-beta-state.json, cache/routing-wald-sprt.json |
| `rr_compaction_spike.py` | RR Compaction Spike — Relevance Realization two-signal scorer | --json/stdin, lifecycle.db |  |
| `run-header.py` | run-header.py — Content-addressed execution identity for Hermes cron runs | CLI |  |
| `safety-metric-evaluator.py` | safety-metric-evaluator.py | CLI |  |
| `save-primer-batch.py` | save-primer-batch.py | CLI |  |
| `se-gos-graphiti-bridge.py` | se-gos-graphiti-bridge.py — SE-GoS Graphiti skill-graph evolution bridge. | CLI |  |
| `secure-message.py` | secure-message.py — AES-GCM (or XOR+HMAC fallback) message encryption/decryption. | CLI |  |
| `semantic-triangulation-verifier.py` | semantic-triangulation-verifier.py | CLI | cache/triangulation-log.json |
| `session-stability-monitor.py` | session-stability-monitor.py | CLI | cache/stability-alarm.json |
| `session-token.py` | session-token.py — HMAC-SHA256 session token generator/verifier. | CLI |  |
| `session-type-tool-protocol.py` | session-type-tool-protocol.py — Honda session types for tool sequences. | --self-test | cache/session-type-tool-protocol.json |
| `shadow-gate-nightly.py` | shadow-gate-nightly.py — Nightly shadow telemetry gate report. | CLI |  |
| `shadow-gate-sprt.py` | shadow-gate-sprt.py — Wald SPRT for shadow-feature promotion. | --self-test | cache/shadow-sprt-decisions.json, cache/block-bootstrap-sprt.json, cache/jev-turn-scores.json |
| `signal-separation-monitor.py` | signal-separation-monitor.py | CLI |  |
| `simulator-fisher-estimator.py` | simulator-fisher-estimator.py | CLI |  |
| `skill-admissibility.py` | BERGER-2: admissibility pruning of dominated skills. | CLI |  |
| `skill-beta-seed.py` | skill-beta-seed.py — seed Beta priors from BM25 self-rank reciprocal rank. | --self-test | cache/skill-beta-state-seeded.json, cache/skill-beta-state.json, cache/skill-router-index.json |
| `skill-bootstrap.py` | ESL-4: .632 bootstrap skill test-error estimator (ESL §7.11). | CLI |  |
| `skill-caskg.py` | skill-caskg.py — CaSKG candidate DAG: skill-load → terminal-outcome edges. | CLI | cache/skill-caskg-dag.json |
| `skill-composition-gf.py` | skill-composition-gf.py — ordinary generating function blow-up of skill DAG walks. | --self-test | cache/concept-lattice.json, cache/skill-router-index.json, cache/skill-composition-gf.json |
| `skill-dependency-verifier.py` | skill-dependency-verifier.py | CLI |  |
| `skill-description-entropy.py` | skill-description-entropy.py — character-level entropy of skill descriptions. | --self-test | cache/skill-description-entropy.json |
| `skill-embedding-geometry.py` | skill-embedding-geometry.py — VIL-1 + VIL-4 | CLI |  |
| `skill-graph-reachability-verifier.py` | skill-graph-reachability-verifier.py | CLI |  |
| `skill-graph-walk.py` | skill-graph-walk.py — Graph-of-Skills dependency traversal for the Hermes skill library. | CLI | cache/provides-taxonomy.json |
| `skill-gw-compare.py` | skill-gw-compare.py — OT-7 | CLI |  |
| `skill-integrity-check.py` | skill-integrity-check.py — HMAC-SHA256 integrity baseline for all SKILL.md files. | CLI | cache/skill-integrity.json |
| `skill-persistent-homology.py` | skill-persistent-homology.py — Persistent homology on the Hermes skill graph. | CLI |  |
| `skill-ranker.py` | skill-ranker.py | CLI |  |
| `skill-router-index.py` | skill-router-index.py — SkillRouter pattern: TF-IDF semantic index over Hermes skill descriptions. | --json/stdin, routing-events.jsonl | cache/skill-router-index.json, cache/skill-beta-state.json, cache/routing-events.json |
| `skill-routing-bounds.py` | skill-routing-bounds.py — ROY-9: tail-bounds for skill routing stability. | lifecycle.db | cache/loop-pid-state.json |
| `skill-stacking.py` | ESL-5: nonnegative stacking weights on LOO skill predictions. | CLI |  |
| `skill-state.py` | skill-state.py — SKILL.state runtime: mutable execution state for long-horizon skills. | CLI |  |
| `skill-wiki.py` | skill-wiki.py — WikiSkill pattern: co-evolve agent skills with a persistent wiki. | --text/stdin |  |
| `skill-yield-tracker.py` | SYNAPSE — Skill Yield Normalization and Adaptive Pruning | --json/stdin |  |
| `skill_prune_audit.py` | skill_prune_audit.py — AutoRefine-inspired skill library health check. | --json/stdin |  |
| `skillopt_score.py` | skillopt_score.py — SkillOpt-inspired skill quality scorer for Hermes. | CLI |  |
| `skillspector_guard.py` |  | CLI | cache/skill-integrity.json, cache/skill-merkle.json |
| `soares-halt-liveness.py` | soares-halt-liveness.py — Corrigibility: HALT remains reachable. | --self-test | cache/loop-pid-state.json, cache/soares-halt-liveness.json |
| `soft-bellman-skill-router.py` | soft-bellman-skill-router.py | CLI | cache/soft-bellman-routing.json |
| `spatial-mixing-error-budget.py` | spatial-mixing-error-budget.py | CLI |  |
| `spawning-utility-estimator.py` | spawning-utility-estimator.py | CLI |  |
| `spec-graph-extractor.py` | spec-graph-extractor.py | CLI | cache/spec-graph.json |
| `spec-semantic-graph-builder.py` | spec-semantic-graph-builder.py | CLI |  |
| `sprt-effective-decision.py` | sprt-effective-decision.py — Merge SPRT + vetoes into one effective decision. | --self-test | cache/sprt-effective-decision.json, cache/effective-shadow-decisions.json |
| `sprt-falsifiability-handshake.py` | sprt-falsifiability-handshake.py — PROMOTE requires failure_observable. | --self-test | cache/shadow-sprt-decisions.json, cache/sprt-falsifiability-handshake.json |
| `sprt-inner-outer-alignment.py` | sprt-inner-outer-alignment.py — Hubinger mesa: inner score vs outer error. | --self-test | cache/sprt-inner-outer-alignment.json |
| `sprt-measurement-tamper.py` | sprt-measurement-tamper.py — Hendrycks/Amodei measurement tampering on SPRT. | --self-test | cache/jev-turn-scores.json, cache/sprt-measurement-tamper.json |
| `sprt-oc-eval.py` | sprt-oc-eval.py — Monte Carlo OC/ASN calibration for the hermes-fork SPRT gate. | --self-test | cache/sprt-oc-calibration.json |
| `sprt-truncation-gate.py` | sprt-truncation-gate.py — Wald truncated SPRT (no infinite CONTINUE). | --self-test | cache/sprt-truncation.json |
| `staleness-monitor.py` | staleness-monitor.py — Monitor freshness of critical Hermes log files. | --self-test | cache/staleness-alarms.json |
| `state-concentration-monitor.py` | state-concentration-monitor.py | CLI |  |
| `state-machine-synthesizer.py` | Synthesize a finite state machine from observed action sequences. | --self-test, --json/stdin, lifecycle.db | cache/synthesized-fsm.json, cache/action-log.json |
| `state-wal-checkpoint.py` | state-wal-checkpoint.py | CLI |  |
| `statecomp-compression-router.py` | statecomp-compression-router.py — StateComp-inspired compression timing router. | CLI |  |
| `step-level-prm-scorer.py` | Score each tool-use step with a lightweight process reward (ToolPRMBench). | --self-test, --json/stdin | cache/prm-step-scores.json |
| `step-level-trajectory-auditor.py` | Audit each step in an agent trajectory for process quality (AgentProcessBench). | --self-test, --json/stdin, lifecycle.db | cache/trajectory-audit.json |
| `strategic-prediction-validator.py` | strategic-prediction-validator.py | CLI |  |
| `subgoal-verifier-rubric.py` | Rubric-based verifier for subgoals in tool-use chains (SCRIBE). | --self-test, --json/stdin | cache/subgoal-verification.json |
| `sybil-risk-monitor.py` | sybil-risk-monitor.py | CLI | cache/sybil-risk-alarm.json |
| `task-assignment-optimizer.py` | task-assignment-optimizer.py | CLI | cache/task-assignments.json |
| `test_browser_act_guard.py` | Unit tests for browser_act_guard.py — run: pytest -q ~/.hermes/scripts/test_browser_act_guard.py | --text/stdin, --json/stdin |  |
| `token-budget-controller.py` | Token Budget Controller for Hermes Agent | --text/stdin |  |
| `tool-auth-gate.py` | tool-auth-gate.py — Separate action induction from runtime authorization. | CLI | cache/active-capability-grant.json |
| `tool-effect-validator.py` | tool-effect-validator.py | CLI |  |
| `trace2skill.py` | trace2skill.py — Trace2Skill pattern: session trajectory → candidate SKILL.md draft. | CLI |  |
| `triple-objective-frontier-router.py` | triple-objective-frontier-router.py | CLI |  |
| `ue-blackbox-scorer.py` | Blackbox uncertainty estimation (lm-polygraph-style, API-only). | --self-test | cache/consistency-scores.json, cache/ue-length-stats.json, cache/condorcet-last.json |
| `ue-calibration-bridge.py` | Bridge UE scores into calibration-log.jsonl for calibration-threshold-updater. | --self-test | cache/ue-calibration-bridge-state.json |
| `ue-memory-gate.py` | Gate memory commits using blackbox UE scores. | --self-test |  |
| `ue-perplexity-proxy.py` | ue-perplexity-proxy.py — compression-based perplexity proxy (no logprobs). | --self-test |  |
| `ue-semantic-density.py` | ue-semantic-density.py — SemanticDensity (Qiu et al., 2024) blackbox adaptation. | --self-test |  |
| `ue-semantic-graph.py` | Graph-based blackbox UE metrics (EigValLaplacian / DegMat / Eccentricity). | --self-test |  |
| `uncertainty-calibration-monitor.py` | uncertainty-calibration-monitor.py | CLI | cache/calibration-alarm.json |
| `unified-recall.py` | unified-recall.py — Execute a memory query against both Hindsight and Graphiti, | --self-test, --json/stdin, lifecycle.db | cache/hindsight-episodes.json, cache/recall-ftrl-state.json, cache/recall-bandit-state.json, cache/recall-query-log.json |
| `validate-skill-ssl.py` | validate-skill-ssl.py — Validate SSL frontmatter in a Hermes SKILL.md file. | CLI |  |
| `wave21a-alarm-bridge.py` | wave21a-alarm-bridge.py — Re-emit Wave 21A memory/IT reports as *-alarm.json. | --self-test | cache/context-channel-capacity.json |
| `wave21c-alarm-bridge.py` | wave21c-alarm-bridge.py — Re-emit 21C reports as *-alarm.json for aggregator. | --self-test |  |
| `wave21c-invariants.py` | wave21c-invariants.py — Nipkow-style property tests for Wave 21C/21D. | --self-test | cache/wave21c-invariants.json, cache/wave21c-invariants-alarm.json |
| `working-memory.py` | working-memory.py — Recuris-style Experiential vs Working Memory split for Hermes. | --text/stdin, --json/stdin | cache/skill-sequences.json, cache/risk-floor.json |

### SCRIPTS — fork wrappers (`profiles/fork/scripts/`)

Runpy two-tier wrappers delegate to `hermes-scripts/<name>.py` when present. Wrapper-only files are local implementations.

| Script | Purpose | Tier |
|--------|---------|------|
| `absorption-capacity-regime-monitor.py` | absorption-capacity-regime-monitor.py | wrapper+canonical |
| `adversarial-allocation-auditor.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `adversarial-robustness-tester.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `adversarial_quarantine_review.py` | Adversarial review helper for skillspector_guard pending-quarantine proposals. | wrapper+canonical |
| `afanet-failure-attributor.py` |  | runpy-wrapper |
| `agent-output-verifier.py` | Infra stub: Agent Output Verifier | wrapper-only |
| `aimd_controller.py` | AIMD Concurrency Controller for Hermes scripts. | wrapper-only |
| `alarm-aggregator.py` | alarm-aggregator.py — Scan cache/ for *-alarm.json files, aggregate active alarms. | wrapper-only |
| `amd-memory-loader.py` | AMD Memory Loader — 3-Tier Proactive/Reactive/Deferred Memory Router | wrapper-only |
| `ann-embeddings-probe.py` | Data collection hook: probe whether real embedding vectors exist. | wrapper-only |
| `autonomy-router-mdp.py` |  | runpy-wrapper |
| `bandit-model-selector.py` | Thompson Sampling model selector from routing-quality.jsonl. | wrapper-only |
| `block-bootstrap-sprt-cron.py` |  | wrapper-only |
| `block-bootstrap-sprt.py` | Fork profile wrapper: delegates to hermes-scripts/block-bootstrap-sprt.py | runpy-wrapper |
| `calibration-threshold-updater.py` | Read calibration-log.jsonl and update Condorcet consistency thresholds. | wrapper-only |
| `callgraph-audit.py` | Interprocedural call-graph audit for Hermes fork scripts. | wrapper-only |
| `callgraph-taint-audit.py` | Fork profile wrapper: delegates to hermes-scripts/callgraph-taint-audit.py | runpy-wrapper |
| `catastrophic-forgetting-guard.py` | catastrophic-forgetting-guard.py — Continual learning protection for skill patches | wrapper-only |
| `causal-memory-annotator.py` | Fork profile wrapper: delegates to hermes-scripts/causal-memory-annotator.py | runpy-wrapper |
| `checkpoint-rollback-tracker.py` | Checkpoint Rollback Tracker | wrapper-only |
| `citation-confidence-router.py` |  | runpy-wrapper |
| `cmtf-tool-frontier.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `cobra-skip-guard.py` | cobra-skip-guard.py — CoBRA-approximation tool-use skip guard | wrapper+canonical |
| `compaction-aep-typical-set.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `compaction-chain-rule-mi.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `compaction-rd-advisor.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `compaction-rd-converse.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `concept-lattice-index.py` | concept-lattice-index.py — ContextRAG-style nightly concept lattice over Hindsight facts. | wrapper+canonical |
| `constraint-validator-with-rollback.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `containment-monitor.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `context-channel-capacity.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `corpus-consolidation-index.py` | corpus-consolidation-index.py — Unify the three Hermes research corpora. | wrapper+canonical |
| `cost-aware-eval-framework.py` |  | runpy-wrapper |
| `cot-injection-detector.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `counterfactual-tool-gate.py` | Fork profile wrapper: delegates to hermes-scripts/counterfactual-tool-gate.py | runpy-wrapper |
| `cron-mdp-policy.py` | cron-mdp-policy.py — tabular discounted MDP for cron dispatch (Puterman). | wrapper-only |
| `cron-sandbox-runner.py` | Fork profile wrapper: delegates to hermes-scripts/cron-sandbox-runner.py | runpy-wrapper |
| `cron-ucb-safe.py` | cron-ucb-safe.py — UCB1 cron-script selection with P(fail) <= 0.1 envelope. | wrapper-only |
| `cross-calibration-monitor.py` | Cross-calibration monitor: detect drift across the three independent calibration silos. | wrapper-only |
| `cs-paper-interpreter.py` | cs-paper-interpreter.py | wrapper+canonical |
| `cs-primers-overnight.py` | cs-primers-overnight.py | wrapper+canonical |
| `cs-research-sweep.py` | cs-research-sweep.py | wrapper+canonical |
| `cusum-gain-freeze.py` | Fork profile wrapper: delegates to hermes-scripts/cusum-gain-freeze.py | runpy-wrapper |
| `cusum-h-calibrator-cron.py` |  | wrapper-only |
| `cusum-h-calibrator.py` | Fork profile wrapper: delegates to hermes-scripts/cusum-h-calibrator.py | runpy-wrapper |
| `dcr-compute-router.py` |  | runpy-wrapper |
| `deductive-verifier.py` | Spike stub: Deductive Verifier — pre-execution invariant enforcement | wrapper-only |
| `epistemic-state-tracker.py` | Fork profile wrapper: delegates to hermes-scripts/epistemic-state-tracker.py | runpy-wrapper |
| `eval-compaction-data-bridge-cron.py` |  | wrapper-only |
| `eval-compaction-data-bridge.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `eval-compaction-distortion-gate.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `eval-hindsight-ingest.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `eval-memory-planted-needle.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `eval-routing-linucb-features.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `eval-shadow-synthetic.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `evograph-skill-editor.py` | evograph-skill-editor.py — EvoGraph-Mem failure-aware skill insight editor. | wrapper+canonical |
| `evograph-with-homology.py` | evograph-with-homology.py — Daily skill health: evograph build + persistent homology gaps. | wrapper-only |
| `execution-integrity-guard.py` | execution-integrity-guard.py — APEXA execution integrity post-tool-call hook | wrapper-only |
| `fact-attribution-verifier.py` |  | runpy-wrapper |
| `feedback-memory-ranker.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `feedback-robustness-scorer.py` |  | runpy-wrapper |
| `fork-regression-check.py` | Regression check for hermes-fork protected symbols post-merge. | wrapper-only |
| `fork-state-vacuum.py` | fork-state-vacuum.py — Weekly VACUUM for the fork profile's state.db. | wrapper-only |
| `gate_audit.py` | gate_audit.py — Audit calibrated gate decisions for consistency and error rates. | wrapper-only |
| `governance-conflict-detector.py` | Fork profile wrapper: delegates to hermes-scripts/governance-conflict-detector.py | runpy-wrapper |
| `governance-conflict-epistemic.py` | Fork profile wrapper: delegates to hermes-scripts/governance-conflict-epistemic.py | runpy-wrapper |
| `governance-falsifiability-lint.py` | Fork profile wrapper: delegates to hermes-scripts/governance-falsifiability-lint.py | runpy-wrapper |
| `graphiti-edge-health.py` | graphiti-edge-health.py — Spectral edge health check for Graphiti KG | wrapper-only |
| `hallucination-detector.py` |  | runpy-wrapper |
| `hallucination-probe-hook.py` | Hallucination probe hook — ground-truth dataset collector. | wrapper-only |
| `hermes-chat-sync-precheck.py` | hermes-chat-sync-precheck.py | wrapper+canonical |
| `hermes-daily-update.py` |  | wrapper-only |
| `hermes-gateway-prestart.py` | hermes-gateway-prestart.py | wrapper-only |
| `hermes-math-sweep.py` | hermes-math-sweep.py | wrapper+canonical |
| `hermes-memory-drift-audit.py` |  | wrapper+canonical |
| `hermes-research-apply.py` | hermes-research-apply.py — Apply accumulated research findings to Hermes skills. | wrapper-only |
| `hermes-research-sweep.py` |  | wrapper+canonical |
| `hierarchy-coherence-monitor.py` | hierarchy-coherence-monitor.py | wrapper+canonical |
| `impact-regularizer-gate.py` | Fork profile wrapper: delegates to hermes-scripts/impact-regularizer-gate.py | runpy-wrapper |
| `information-refinement-utility-monitor.py` | information-refinement-utility-monitor.py | wrapper+canonical |
| `iss-justification-gate.py` | Fork profile wrapper: delegates to hermes-scripts/iss-justification-gate.py | runpy-wrapper |
| `iss-small-gain-check.py` | iss-small-gain-check.py — Sontag/Khalil ISS small-gain composition. | wrapper-only |
| `it-task-complexity-estimator.py` | Information-theoretic task complexity estimator (Cover & Thomas AEP). | wrapper-only |
| `jev-gate-nightly.py` | jev-gate-nightly.py — Nightly promotion gate for jev-turn-evaluator. | wrapper-only |
| `jev-scores-staleness-check.py` | Fork profile wrapper: delegates to hermes-scripts/jev-scores-staleness-check.py | runpy-wrapper |
| `kl-curvature-memory-monitor.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `kl-skill-prior.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `l1-extract.py` | l1-extract.py — lockfile wrapper + bytecode restore. | wrapper+canonical |
| `l1-gmemory-consolidation.py` | l1-gmemory-consolidation.py — Three-tier G-Memory nightly cross-session consolidation. | wrapper+canonical |
| `l1-graphiti-reconcile.py` | l1-graphiti-reconcile.py — Scatter-gather reconciliation for the Hindsight → Graphiti write path. | wrapper+canonical |
| `l1-hindsight-promote.py` | l1-hindsight-promote.py — Promote L1 memory facts to Hindsight long-term memory. | wrapper-only |
| `l1-hypermem-promote.py` | l1-hypermem-promote.py — HyperMem episode grouping at l1-promote time. | wrapper+canonical |
| `l1-promote.py` | l1-promote.py — extract-running lock + bytecode restore. | wrapper+canonical |
| `lifecycle-schema-extension.py` |  | runpy-wrapper |
| `loop-cusum-changepoint.py` | Fork profile wrapper: delegates to hermes-scripts/loop-cusum-changepoint.py | runpy-wrapper |
| `loop-lyapunov-stability.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `loop-model-comparison.py` | Fork profile wrapper: delegates to hermes-scripts/loop-model-comparison.py | runpy-wrapper |
| `loop-pid-cron-step.py` | Cron stepper for the session-stability PID loop. | wrapper+canonical |
| `loop-pid-iss-wrapper.py` | Fork profile wrapper: delegates to hermes-scripts/loop-pid-iss-wrapper.py | runpy-wrapper |
| `loop-pid-synthetic-step.py` | Fork profile wrapper: delegates to hermes-scripts/loop-pid-synthetic-step.py | runpy-wrapper |
| `loop-pid.py` | Thin runpy delegate — forwards to canonical hermes-scripts/loop-pid.py. | runpy-wrapper |
| `loop-rollout-horizon.py` | Fork profile wrapper: delegates to hermes-scripts/loop-rollout-horizon.py | runpy-wrapper |
| `ltl-promotion-invariant.py` | Fork profile wrapper: delegates to hermes-scripts/ltl-promotion-invariant.py | runpy-wrapper |
| `math-paper-interpreter.py` | math-paper-interpreter.py | wrapper+canonical |
| `mcp-auth-drift-check.py` | mcp-auth-drift-check.py — MCP authorization drift detection | wrapper-only |
| `mcp-privilege-audit.py` | MCP least-privilege auditor (cs-mcp-overpriv / arXiv:2603.21641). | wrapper+canonical |
| `mdp-session-planner.py` | MDP session planner (Puterman value iteration). | wrapper-only |
| `memory-access-decay.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `memory-adaptive-rank.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `memory-auto-improvement.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `memory-bethe-free-energy.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `memory-bits-back.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `memory-bottleneck-monitor.py` | Spike stub: Memory Bottleneck Monitor — I(episodic; semantic) tracking | wrapper-only |
| `memory-coherence-probe-hook.py` | Memory coherence probe hook. | wrapper-only |
| `memory-conductance-ttl.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `memory-contamination-tagger.py` | Infra stub: Memory Contamination Tagger (PSE) | wrapper-only |
| `memory-coupling-merge.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `memory-displacement-convexity.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `memory-dkw-ue.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `memory-doob-decompose.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `memory-doob-strata-consumer.py` | memory-doob-strata-consumer.py — Score working-memory by Doob stratum. | wrapper+canonical |
| `memory-eckart-young.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `memory-fano-bound.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `memory-gelman-shrink.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `memory-haar-mra.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `memory-heisenberg-tf.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `memory-hitting-time.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `memory-jl-distortion.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `memory-kalman-latent.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `memory-kraft-code.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `memory-lens.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `memory-log-ode-sig.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `memory-lp-dct-gate.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `memory-malliavin-ibp.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `memory-matrix-bernstein.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `memory-mcdiarmid-rrf.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `memory-mixing-ttl.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `memory-ontology-topology.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `memory-optional-stopping.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `memory-ot-decay.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `memory-portmanteau.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `memory-provenance-tagger.py` | memory-provenance-tagger.py — Provenance attestation for Hindsight staging facts | wrapper-only |
| `memory-query-router.py` | memory-query-router.py — Query-type routing for Hermes memory retrieval. | wrapper+canonical |
| `memory-ransac-commit.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `memory-reference-frequency.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `memory-relation-extractor.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `memory-renorm-counterterm.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `memory-rough-signature.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `memory-sanov-ld.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `memory-signature-rerank.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `memory-sprt-commit.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `memory-staleness-cron.py` |  | wrapper-only |
| `memory-staleness.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `memory-taxonomy-discover.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `memory-term-typer.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `memory-topology-consolidator.py` | Spike stub: Memory Topology Consolidator — RAG graph merge | wrapper-only |
| `memory-ttl-floor-merge-cron.py` |  | wrapper-only |
| `memory-ttl-floor-merge.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `memory-ttl-purge.py` | memory-ttl-purge.py — TTL enforcement for Hermes staged memories. | wrapper+canonical |
| `memory-voi-consolidation.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `memory-wave18-adversarial.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `memory-wave18-invariants.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `memory-zscore-retention.py` | memory-zscore-retention.py — Z-score based memory retention policy. | wrapper+canonical |
| `merge-beta-seed.py` | Fork profile wrapper: delegates to hermes-scripts/merge-beta-seed.py | runpy-wrapper |
| `merkle-evidence-chain.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `merkle-skill-check.py` | merkle-skill-check.py — Merkle root over all SKILL.md SHA256 hashes. | wrapper+canonical |
| `metacognitive-harness.py` | Metacognitive Harness for Hermes Agent | wrapper+canonical |
| `monitor-suite-runner.py` | monitor-suite-runner.py | wrapper+canonical |
| `msprt-shadow-gate.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `mutation-rubric-engine.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `news_diff_watchdog.py` | news_diff_watchdog.py - Hermes cron watchdog: emits new news items only. | wrapper+canonical |
| `nyquist-bandwidth-estimator.py` | nyquist-bandwidth-estimator.py — sampling theorem check for cron periods. | wrapper-only |
| `nyquist-timescale-bridge.py` | Fork profile wrapper: delegates to hermes-scripts/nyquist-timescale-bridge.py | runpy-wrapper |
| `observation-budget-allocator.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `obstruction-certificate-cache.py` |  | runpy-wrapper |
| `occam-skill-ranker.py` | Occam-weighted skill ranker (MACKAY-1 coverage volume ratio). | wrapper+canonical |
| `omni_skill_scan.py` | omni_skill_scan.py — Scheduled GEPA Omni continuous improvement driver. | wrapper+canonical |
| `online-allocation-regret-monitor.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `online-threshold-skill-router.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `ontology-query-expander.py` | Self-ontology query expansion hook for Graphiti/Hindsight. | wrapper-only |
| `ot_utils.py` | ot_utils.py — Shared Optimal Transport utility for Hermes scripts. | wrapper+canonical |
| `output-formalizer-verifier.py` |  | runpy-wrapper |
| `parametric-saturation-monitor.py` | Spike stub: Parametric Saturation Monitor | wrapper-only |
| `pddl-state-abstractor.py` |  | runpy-wrapper |
| `pending-improvements-review.py` | pending-improvements-review.py — Real evaluator for queued Hermes self-improvement proposals. | wrapper-only |
| `perception-reasoning-splitter.py` |  | runpy-wrapper |
| `persistent-memory-fuzzer.py` | Spike stub: When Correct Memory Goes Wrong — Persistent Memory Fuzzer | wrapper-only |
| `pid-circle-criterion.py` | Fork profile wrapper: delegates to hermes-scripts/pid-circle-criterion.py | runpy-wrapper |
| `pid-passivity-index.py` | Fork profile wrapper: delegates to hermes-scripts/pid-passivity-index.py | runpy-wrapper |
| `plan-commitment.py` | plan-commitment.py — SHA256 commitment scheme for agent plans. | wrapper+canonical |
| `plan-enforcement-gate.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `plugin-pipeline-scan.py` | plugin-pipeline-scan.py — Wave 18 theory checks on fork plugins. | wrapper-only |
| `pre-compact-annotate.py` | pre-compact-annotate.py — Pre-compaction signal annotation for Hermes sessions. | wrapper+canonical |
| `process-reward-ranker.py` |  | runpy-wrapper |
| `process-verifier-agent.py` |  | runpy-wrapper |
| `progress-mirage-gate.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `promotion-at-most-once.py` | Fork profile wrapper: delegates to hermes-scripts/promotion-at-most-once.py | runpy-wrapper |
| `rd-compaction-advisor.py` | Rate-distortion-*shaped* compaction aggressiveness advisor. | wrapper+canonical |
| `real-options-deployment-gate.py` | real-options-deployment-gate.py | wrapper+canonical |
| `real-options-fanout-gate.py` | real-options-fanout-gate.py — Cron wrapper for real-options-deployment-gate. | wrapper-only |
| `reasoning-complexity-classifier.py` | reasoning-complexity-classifier.py — Adaptive reasoning depth classifier for Hermes. | wrapper+canonical |
| `reasoning-trace-evaluator.py` |  | runpy-wrapper |
| `reasoning-ue-integrator.py` | Fork profile wrapper: delegates to hermes-scripts/reasoning-ue-integrator.py | runpy-wrapper |
| `recall-miss-ttl-adjuster.py` | recall-miss-ttl-adjuster.py — MRAS-inspired adaptive TTL policy updater. | wrapper-only |
| `redundancy-stability-monitor.py` | redundancy-stability-monitor.py | wrapper+canonical |
| `reflection-distiller.py` | Reflection Distiller | wrapper-only |
| `relevance-compaction-trigger.py` | Relevance-decay compaction trigger. | wrapper-only |
| `research-pipeline-weekly.py` | research-pipeline-weekly.py — Consolidated Hermes research pipeline. | wrapper-only |
| `ripple-mem-expander.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `router-login.py` | router-login.py — Get a TP-Link AX55 stok in one shot. | wrapper-only |
| `routing-alarm-bridge.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `routing-azuma-concentration.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `routing-belief-propagation.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `routing-boolean-influence.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `routing-convergence-guard.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `routing-exp3-adversarial.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `routing-exp4-contextual.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `routing-fano-bound.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `routing-graph-bandit-update.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `routing-graph-independence.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `routing-hamming-audit.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `routing-ips-offpolicy.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `routing-kl-ucb.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `routing-linucb.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `routing-mcdiarmid-bm25.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `routing-mobius-audit.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `routing-mutual-information.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `routing-pac-bayes-bound.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `routing-precision-recall.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `routing-rademacher-bound.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `routing-skill-markov.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `routing-skill-percolation.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `routing-switching-detector.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `routing-token-setcover.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `routing-tsallis-inf.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `routing-wald-sprt.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `routing-weight-updater.py` | routing-weight-updater.py — FTRL routing weight feedback loop closure. | wrapper-only |
| `run-header.py` | run-header.py — Content-addressed execution identity for Hermes cron runs | wrapper+canonical |
| `safety-metric-evaluator.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `se-gos-graphiti-bridge.py` | Thin wrapper: SE-GoS lives in the skill scripts/ dir (host scripts/ is root-owned). | runpy-wrapper |
| `semantic-early-stopping.py` | Convergence detector for iterative LLM agent loops. | wrapper-only |
| `session-gc-probe.py` | Data collection hook for Self-GC retry. | wrapper-only |
| `session-resource-audit.py` | session-resource-audit.py — Runtime-acquired resource authorization audit | wrapper-only |
| `session-type-tool-protocol.py` | Fork profile wrapper: delegates to hermes-scripts/session-type-tool-protocol.py | runpy-wrapper |
| `shadow-gate-nightly.py` | shadow-gate-nightly.py — Nightly shadow telemetry gate report. | wrapper+canonical |
| `shadow-gate-sprt.py` | Fork profile wrapper: delegates to hermes-scripts/shadow-gate-sprt.py | runpy-wrapper |
| `sheaf-memory-gluing.py` | sheaf-memory-gluing.py — Curry/Robinson sheaf consistency across memory shards. | wrapper-only |
| `skill-beta-feedback.py` | skill-beta-feedback.py -- Skill beta-bandit feedback writer. | wrapper-only |
| `skill-beta-seed.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `skill-composition-gf.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `skill-compressor.py` | Spike stub: SkillZip — MDL Skill Compression | wrapper-only |
| `skill-description-entropy.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `skill-integrity-check.py` | skill-integrity-check.py — HMAC-SHA256 integrity baseline for all SKILL.md files. | wrapper+canonical |
| `skill-router-index-rebuild.py` | Cron wrapper: rebuild skill-router-index unconditionally. | wrapper-only |
| `skill-router-index.py` | skill-router-index.py — SkillRouter pattern: TF-IDF semantic index over Hermes skill descriptions. | wrapper+canonical |
| `skill-routing-bounds.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `skill-routing-causal-audit.py` | skill-routing-causal-audit.py — Pearl/Schölkopf observational vs interventional. | wrapper-only |
| `skill-shadow-registry.py` | skill-shadow-registry.py — MedRSI slow-registration gate for skill patches | wrapper-only |
| `skill-wiki.py` | skill-wiki.py — WikiSkill pattern: co-evolve agent skills with a persistent wiki. | wrapper+canonical |
| `skill-yield-tracker.py` | SYNAPSE — Skill Yield Normalization and Adaptive Pruning | wrapper+canonical |
| `skill_prune_audit.py` | skill_prune_audit.py — AutoRefine-inspired skill library health check. | wrapper+canonical |
| `skillspector_guard.py` |  | wrapper+canonical |
| `soares-halt-liveness.py` | Fork profile wrapper: delegates to hermes-scripts/soares-halt-liveness.py | runpy-wrapper |
| `soft-bellman-skill-router.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `spike-actuator.py` | spike-actuator.py — Build stub artifacts and layer1 demo tests from IMPLEMENT items. | wrapper-only |
| `spike-queue-actuator.py` | spike-queue-actuator.py — Dispatch accepted SPIKE items from cs/math spike queues | wrapper-only |
| `sprt-effective-decision.py` | Fork profile wrapper: delegates to hermes-scripts/sprt-effective-decision.py | runpy-wrapper |
| `sprt-falsifiability-handshake.py` | Fork profile wrapper: delegates to hermes-scripts/sprt-falsifiability-handshake.py | runpy-wrapper |
| `sprt-inner-outer-alignment.py` | Fork profile wrapper: delegates to hermes-scripts/sprt-inner-outer-alignment.py | runpy-wrapper |
| `sprt-measurement-tamper.py` | Fork profile wrapper: delegates to hermes-scripts/sprt-measurement-tamper.py | runpy-wrapper |
| `sprt-truncation-gate.py` | Fork profile wrapper: delegates to hermes-scripts/sprt-truncation-gate.py | runpy-wrapper |
| `staleness-monitor.py` | staleness-monitor.py — Monitor freshness of critical Hermes log files. | wrapper+canonical |
| `state-machine-synthesizer.py` |  | runpy-wrapper |
| `statecomp-compression-router.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `step-level-prm-scorer.py` |  | runpy-wrapper |
| `step-level-trajectory-auditor.py` |  | runpy-wrapper |
| `stepshield-trajectory-monitor.py` | StepShield Trajectory Monitor | wrapper-only |
| `stuck-job-detector.py` | Detect cron jobs stuck in running state for >2x expected duration. | wrapper-only |
| `subgoal-verifier-rubric.py` |  | runpy-wrapper |
| `test_plugin_pipeline_theory.py` | Property tests for Wave 18 plugin/hook theory (Honda, Khalil, Soares tiling). | wrapper-only |
| `tool-auth-shim.py` | Lightweight inspection-game shim for tool result auditing. | wrapper-only |
| `trigger-phrase-validator.py` | Validate SKILL.md trigger phrases (OMH trigger_language_packs.py inspired). | wrapper-only |
| `two-timescale-check.py` | two-timescale-check.py — Khalil ch.11 singular perturbation separation. | wrapper-only |
| `ue-blackbox-scorer.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `ue-calibration-bridge-cron.py` |  | wrapper-only |
| `ue-calibration-bridge.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `ue-memory-gate-cron.py` |  | wrapper-only |
| `ue-memory-gate.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `ue-perplexity-proxy.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `ue-semantic-density.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `ue-semantic-graph.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `validate-skill-ssl.py` | validate-skill-ssl.py — Validate SSL frontmatter in a Hermes SKILL.md file. | wrapper+canonical |
| `wave21a-alarm-bridge.py` | Fork profile wrapper: delegates to hermes-scripts implementation. | runpy-wrapper |
| `wave21c-alarm-bridge.py` | Fork profile wrapper: delegates to hermes-scripts/wave21c-alarm-bridge.py | runpy-wrapper |
| `wave21c-invariants.py` | Fork profile wrapper: delegates to hermes-scripts/wave21c-invariants.py | runpy-wrapper |
| `working-memory.py` | working-memory.py — Recuris-style Experiential vs Working Memory split for Hermes. | wrapper+canonical |

### SKILLS (`profiles/fork/skills/`) — 230

| Skill | Trigger (description) | What it does |
|-------|----------------------|--------------|
| `abiteboul-foundations-databases` | Use when studying formal database theory. | Mathematical/computational reference. See source PDF for full content. |
| `abramsky-domain-theory-logic` | Use when studying domain theory logically. | Mathematical/computational reference. See source PDF for full content. |
| `abramsky-jung-domain-theory` | Use when studying denotational semantics and domains. | Mathematical/computational reference. See source PDF for full content. |
| `agent-runtime-loop-patterns` | Use when structuring agent turns. Fast-slow routing + loop. | Each agent turn follows: receive → classify → retrieve context → execute → compress → respond. |
| `amari-info-geometry-ml` | Use when applying information geometry to ML. | Mathematical/computational reference. See source PDF for full content. |
| `amari-information-geometry` | Use when studying statistical manifolds and Fisher. | Mathematical/computational reference. See source PDF for full content. |
| `amodei-concrete-ai-safety` | Use when checking tool calls for accident risk patterns. | Amodei et al. (2016) Concrete Problems in AI Safety. |
| `anchored-context-distillation` | Use when context fills with tool output. Compress floatsam. | Source: arXiv:2609.31430 - Compress What You See, Not What You Say. |
| `android-remote-management` | Use when managing Android phone remotely via SSH/ADB. | The confirmed working path: |
| `arora-barak-complexity` | Use when studying computational complexity theory. | Mathematical/computational reference. See source PDF for full content. |
| `astrom-feedback-systems` | Use when designing feedback control systems. | Mathematical/computational reference. See source PDF for full content. |
| `autonomous-ai-agents` | Use when spawning agents. SAGE decomp + merge. | Before spawning subagents, decompose the goal via a 3-level hierarchy: |
| `awodey-homotopy-type-theory` | Use when studying homotopy and identity types. | Mathematical/computational reference. See source PDF for full content. |
| `axler-linear-algebra` | Use when studying linear algebra without determinants. | Mathematical/computational reference. See source PDF for full content. |
| `axler-measure-theory` | Use when studying Lebesgue measure and integration. | © Sheldon Axler 2020. This book is an open access publication. This book is licensed under the terms of the Creative Commons Attribution-Non |
| `baez-physics-topology-logic` | Use when connecting physics topology and computation. | Mike Stay Computer Science Department, University of Auckland *and* Google, 1600 Amphitheatre Pkwy Mountain View, California 94043, USA emai |
| `barber-bayesian-reasoning-ml` | Use when doing Bayesian machine learning. | Mathematical/computational reference. See source PDF for full content. |
| `barocas-fairness-ml` | Use when addressing fairness in ML systems. | Mathematical/computational reference. See source PDF for full content. |
| `berger-statistical-decision-theory` | Use when studying statistical decision theory. | Mathematical/computational reference. See source PDF for full content. |
| `bertsekas-alphazero` | Use when studying AlphaZero rollout-based planning. | Mathematical/computational reference. See source PDF for full content. |
| `bertsekas-rl-textbook` | Use when studying RL from optimal control view. | Mathematical/computational reference. See source PDF for full content. |
| `bertsekas-rollout-rl` | Use when studying rollout and policy iteration methods. | Mathematical/computational reference. See source PDF for full content. |
| `billingsley-probability-measure` | Use when studying measure-theoretic probability. | Mathematical/computational reference. See source PDF for full content. |
| `bishop-prml` | Use when studying probabilistic ML with PRML. | Mathematical/computational reference. See source PDF for full content. |
| `blum-foundations-data-science` | Use when studying mathematical foundations of data. | Mathematical/computational reference. See source PDF for full content. |
| `boneh-shoup-cryptography` | Use when studying provably secure cryptography. | Mathematical/computational reference. See source PDF for full content. |
| `book-to-skill` | Converts books and documents (PDF, EPUB, DOCX, HTML, Markdown, plain text, RTF, MOBI/AZW with Calibre) into structured a | <!-- |
| `borodin-elyaniv-online-computation` | Use when analysing competitive ratio or FTRL/regret. | Graduate reference for **worst-case online algorithms**. Measure ALG against an offline OPT that sees the whole request sequence. Source PDF |
| `boyd-convex-optimization` | Use when solving convex optimization problems. | Mathematical/computational reference. See source PDF for full content. |
| `boyd-vmls` | Use when applying linear algebra to data science. | Mathematical/computational reference. See source PDF for full content. |
| `bps-skill-budget` | Use when loading skills. BPS budget-aware selection. | Based on arXiv:2608.19993. Bicriteria (1-1/e, 1) approximation. |
| `bronstein-geometric-dl` | Use when applying geometric deep learning. | Mathematical/computational reference. See source PDF for full content. |
| `budget-aware-cron-adaptation` | > | From arXiv 2609.10201 (Nakamura et al., 2026): "Online Job Scheduling with Utility Budgets" |
| `buss-proof-theory` | Use when studying proof theory and cut elimination. | Mathematical/computational reference. See source PDF for full content. |
| `camofox-retry-on-failure` | Use when using camofox browser server for scraping or when camofox fails. REST API pattern, retry on failure, environmen | If ANY browser tool call fails with a connection error, timeout, or "server not running" message, DO NOT report failure to the user. Silentl |
| `cannas-symplectic-geometry` | Use when studying symplectic geometry. | Mathematical/computational reference. See source PDF for full content. |
| `channel-fracture-cron` | Use when cron memory writes look successful. Verify receiver-side, not writer-side. | Source: arXiv:2606.04896 — Channel Fracture (production Hermes deployment). |
| `chazal-tda-introduction` | Use when introducing topological data analysis. | Mathematical/computational reference. See source PDF for full content. |
| `chlipala-certified-programming` | Use when writing certified programs in Coq. | Mathematical/computational reference. See source PDF for full content. |
| `chung-spectral-graph-theory` | Use when analyzing graphs via spectral methods. | Mathematical/computational reference. See source PDF for full content. |
| `clarke-model-checking` | Use when verifying concurrent properties with CTL/LTL. | **Authors**: Edmund M. Clarke Jr., Orna Grumberg, Doron A. Peled / **Pages**: xiv+314 / **ISBN**: 0-262-03270-8 / **Chapters**: 16 |
| `cliff-compaction` | Use when compacting long-horizon context. Drop originals; never rephrase or recompact. | Source: arXiv:2609.26779 — CliffCompaction. |
| `clrs-introduction-to-algorithms` | Use when designing or analyzing algorithms. | Mathematical/computational reference. See source PDF for full content. |
| `cmtf-tool-filtering` | Use when checking tools. CMTF causal minimal filter. | Based on arXiv:2606.06284. Training-free causal contracts reduce tool exposure 60-90%. |
| `compositional-skill-routing` | Use when a task needs multiple skills. Decompose, retrieve per subtask, then compose. | Source: arXiv:2606.18051 — SkillWeaver: Decompose, Retrieve, and Compose. |
| `consumer-product-research` | Use when researching products to buy. Config + narrowing. | Use when the user wants to buy something and needs research, shortlisting, and configuration advice. This user cares about aesthetics and qu |
| `cover-thomas-information-theory` | Use when studying entropy and channel capacity. | Mathematical/computational reference. See source PDF for full content. |
| `critch-ai-research-considerations` | Use when checking prepotence and multi-principal risks. | Critch & Krueger (2020) 'AI Research Considerations for Human Existential Safety' |
| `cross-fit-recall-bias` | > | If you score a skill on the same data used to select it, you introduce selection bias: |
| `cross-lingual-compression-audit` | Use for multilingual text. English compressors widen gap. | Source: arXiv:2608.26175 - Lost in Compression: A Controlled Cross-Lingual Audit. |
| `cross-lingual-context-compression` | > | From MSCLAR et al., NeurIPS 2025 (extended 2026): Cross-lingual prompt compression exploits |
| `cruttwell-categorical-gradient-descent` | Use when studying categorical ML foundations. | BRUNO GAVRANOVIĆ and NEIL GHANI, University of Strathclyde, UK PAUL WILSON and FABIO ZANASI, University College London, UK We propose a cate |
| `curry-sheaves` | Use when studying sheaves and cosheaves. | Mathematical/computational reference. See source PDF for full content. |
| `dean-reverse-mathematics` | Use when studying reverse mathematics and subsystems. | Mathematical/computational reference. See source PDF for full content. |
| `decision-centric-memory` | Use when compressing agent memory. Keep decision distinctions, not descriptions. | Source: arXiv:2605.10870 — Remember the Decision, Not the Description. |
| `deductive-verifier` | Use when verifying reasoning chains before propagation. | Verifying agent reasoning chains for logical validity before propagation. |
| `degroot-statistical-decisions` | Use when studying optimal statistical decisions. | Mathematical/computational reference. See source PDF for full content. |
| `deisenroth-math-for-ml` | Use when studying mathematics for machine learning. | Mathematical/computational reference. See source PDF for full content. |
| `durrett-probability` | Use when studying graduate probability theory. | Mathematical/computational reference. See source PDF for full content. |
| `dwork-differential-privacy` | Use when applying differential privacy algorithms. | Mathematical/computational reference. See source PDF for full content. |
| `edelsbrunner-computational-topology` | Use when studying computational topology. | Mathematical/computational reference. See source PDF for full content. |
| `edelsbrunner-persistent-homology` | Use when studying persistent homology. | Mathematical/computational reference. See source PDF for full content. |
| `embedded-device-setup` | Use when setting up a Raspberry Pi or embedded Linux device. | Covers: flashing Raspberry Pi OS from a Linux host, headless first-boot configuration (cloud-init), Pi-hole installation, detecting a Pi on  |
| `erickson-algorithms` | Use when studying algorithms with rigorous proofs. | Mathematical/computational reference. See source PDF for full content. |
| `evans-secure-computation` | Use when implementing secure multi-party computation. | Mathematical/computational reference. See source PDF for full content. |
| `evograph-skill-health` | Use when auditing skills. EvoGraph health tracker. | Based on arXiv:2606.04917. Failure-aware editable skill health graph. |
| `experience-amortized-recall` | > | From arXiv 2608.22767 (Deng et al., 2026): "Experience-Amortized Retrieval Reranking" shows |
| `fabricated-consensus-gate` | Use when merging multi-agent debate. Active Provenance Gate (arXiv:2609.31422). Block ungrounded consensus before publis | Source: arXiv:2609.31422 — Active Provenance Gate for Multi-Agent Debate Synthesis. |
| `fagin-reasoning-about-knowledge` | Use when typing epistemic state of agent assertions. | Fagin, Halpern, Moses, Vardi (1995) Reasoning About Knowledge. |
| `firefox-config` | Use when configuring Firefox policies or search defaults. | Covers: deploying enterprise policies.json, setting default search engine, resolving correct paths for native RPM vs Flatpak installs on Fed |
| `flajolet-analytic-combinatorics` | Use when analyzing algorithms via generating functions. | Mathematical/computational reference. See source PDF for full content. |
| `flatpak-game-configuration` | Use when configuring Flatpak games or rulesets. | Use when a Flatpak game needs non-default rulesets, graphics, or auto-launch of a bundled server + client. |
| `fong-spivak-seven-sketches` | Use when applying category theory to data science. | Mathematical/computational reference. See source PDF for full content. |
| `gallager-information-theory` | Use when studying Gallager-style information theory. | Mathematical/computational reference. See source PDF for full content. |
| `garrabrant-logical-induction` | Use when calibrating beliefs under logical uncertainty. | Garrabrant et al. (2016) prove a computable market-based inductor P_n that assigns |
| `gelman-bayesian-data-analysis` | Use when doing Bayesian data analysis. | Mathematical/computational reference. See source PDF for full content. |
| `ghrist-elementary-applied-topology` | Use when studying applied algebraic topology. | Mathematical/computational reference. See source PDF for full content. |
| `ghrist-sensor-networks` | Use when applying topology to sensor networks. | Mathematical/computational reference. See source PDF for full content. |
| `girard-linear-logic` | Use when studying resource-sensitive linear logic. | Mathematical/computational reference. See source PDF for full content. |
| `girard-proofs-and-types` | Use when studying the Curry-Howard correspondence. | Mathematical/computational reference. See source PDF for full content. |
| `github-pr-review` | Use when reviewing GitHub PRs. Adversarial loop required. | Use when asked to review PRs on a GitHub repo — finding open PRs, reading diffs, writing review comments, and posting them as amoni094. |
| `grimmett-probability` | Use when studying probability and random processes. | Mathematical/computational reference. See source PDF for full content. |
| `hairer-malliavin` | Use when studying Malliavin calculus. | Mathematical/computational reference. See source PDF for full content. |
| `hairer-markov-convergence` | Use when studying Markov chain convergence rates. | Mathematical/computational reference. See source PDF for full content. |
| `hairer-regularity-structures` | Use when studying regularity structures for SPDEs. | Mathematical/computational reference. See source PDF for full content. |
| `hairer-rough-paths` | Use when studying rough path theory. | Mathematical/computational reference. See source PDF for full content. |
| `hairer-spde` | Use when studying stochastic PDEs. | Mathematical/computational reference. See source PDF for full content. |
| `hallucination-detector` | Use when detecting hallucinated content. | Detecting potentially hallucinated or hedge-heavy generated text before memory/skill promotion. |
| `harper-pfpl` | Use when studying practical foundations of PLs. | Mathematical/computational reference. See source PDF for full content. |
| `harrison-practical-logic` | Use when doing automated theorem proving. | Mathematical/computational reference. See source PDF for full content. |
| `hartline-mechanism-design` | Use when designing approximately optimal mechanisms. | Mathematical/computational reference. See source PDF for full content. |
| `hastie-esl` | Use when studying statistical learning methods. | Mathematical/computational reference. See source PDF for full content. |
| `hatcher-algebraic-topology` | Use when studying algebraic topology. | Mathematical/computational reference. See source PDF for full content. |
| `hatcher-spectral-sequences` | Use when computing with spectral sequences. | Mathematical/computational reference. See source PDF for full content. |
| `hatcher-vector-bundles` | Use when studying vector bundles and K-theory. | Mathematical/computational reference. See source PDF for full content. |
| `hendrycks-ml-safety` | Use when identifying unsolved ML safety problems. | - Unsolved Problems in ML Safety |
| `hennessy-semantics-pl` | Use when studying denotational semantics. | Mathematical/computational reference. See source PDF for full content. |
| `hermes-compaction-eval` | Use when running Hermes compaction or toolperf A/B evals. | Two eval harnesses live in the fork repo: the compaction recall eval and the toolperf A/B eval. Run together when the fork architecture chan |
| `hermes-fork-bottleneck-audit` | Use when finding hermes-fork bottlenecks. Recon + patch. | Cron passes HERMES_HOME=/var/home/rainbow/.hermes (the .hermes ROOT, NOT the profile root). |
| `hermes-fork-script-development` | Use when writing hermes-fork scripts. Two-tier pattern. | Every functional script uses two tiers: |
| `hermes-host-maintenance` | Use when recovering Hermes DB crashes, updating host OS, or pulling hermes-agent main. | Covers two recurring classes: (1) Hermes state.db recovery after crashes, and (2) OS-level system updates. |
| `hermes-plugin-wiring-audit` | Use when auditing hermes-fork plugin wiring post-build. | Use after building or modifying hermes-fork plugins, before declaring implementation |
| `hermes-swarm-consensus` | Use when merging multi-agent results. Shapley + consensus. | After any `delegate_task` with 2+ subagents where results are merged into a single output. |
| `hofstad-random-graphs` | Use when studying random graphs and complex networks. | Mathematical/computational reference. See source PDF for full content. |
| `honda-session-types` | Use when studying session types for concurrent systems. | Mathematical/computational reference. See source PDF for full content. |
| `hott-univalent-foundations` | Use when studying HoTT and univalent foundations. | Mathematical/computational reference. See source PDF for full content. |
| `hubinger-mesa-optimization` | Use when detecting deceptive alignment signals in output. | Hubinger et al. (2019) Risks from Learned Optimization. |
| `humanizer` | / | Rewrite AI-sounding text so it reads like the writer, not a chatbot. Do not change what it says or make up details. |
| `huth-ryan-logic-in-cs` | Use when modeling systems with logic. | Mathematical/computational reference. See source PDF for full content. |
| `hutter-aixi` | Use when applying MDL/Solomonoff to selection. | Hutter (2004) Universal Artificial Intelligence: Sequential Decisions Based |
| `hutter-universal-ai` | Use when studying universal AI Solomonoff induction. | Consolidated into hutter-aixi skill. All operational content |
| `izhikevich-computational-neuroscience` | Use when modeling neural dynamics computationally. | Mathematical/computational reference. See source PDF for full content. |
| `jacobs-coalgebra` | Use when modeling coinductive and stream systems. | Mathematical/computational reference. See source PDF for full content. |
| `jaynes-probability-logic-of-science` | Use when studying Bayesian probability theory. | Mathematical/computational reference. See source PDF for full content. |
| `jev-system-one-patterns` | Use when designing JEV harness patterns. | Jev is TypeSafe AI's System One Model (released 2026-09-15). It is NOT an LLM. |
| `ji-alignment-survey` | Use when checking alignment properties of agent behaviour. | Ji et al. (2023) 'AI Alignment: A Comprehensive Survey'. Maps the |
| `jurafsky-martin-nlp` | Use when studying NLP and speech processing. | Mathematical/computational reference. See source PDF for full content. |
| `katz-lindell-cryptography` | Use when studying modern cryptography definitions. | Mathematical/computational reference. See source PDF for full content. |
| `khalil-nonlinear-systems` | Use when analyzing nonlinear dynamical systems. | Mathematical/computational reference. See source PDF for full content. |
| `kidger-neural-odes` | Use when studying neural differential equations. | Mathematical/computational reference. See source PDF for full content. |
| `klein-sel4-microkernel` | Use when studying formally verified OS kernels. | Mathematical/computational reference. See source PDF for full content. |
| `knapp-advanced-algebra` | Use when working with advanced algebraic structures. | Knapp's Advanced Algebra (2007) is a rigorous graduate-level reference covering commutative algebra, homological algebra, algebraic number t |
| `knapp-advanced-real-analysis` | Use when studying advanced analysis and PDEs. | Mathematical/computational reference. See source PDF for full content. |
| `knapp-basic-algebra` | Use when grounding in groups rings and modules. | Knapp's Basic Algebra (2006) is a comprehensive graduate text covering group theory, ring theory, module theory, multilinear algebra, and st |
| `knapp-basic-real-analysis` | Use when grounding in real analysis fundamentals. | Mathematical/computational reference. See source PDF for full content. |
| `knapp-differential-geometry` | Use when studying differential forms and manifolds. | Mathematical/computational reference. See source PDF for full content. |
| `knapp-lie-groups` | Use when studying Lie groups and representations. | Mathematical/computational reference. See source PDF for full content. |
| `kreyszig-functional-analysis` | Use when studying Banach and Hilbert spaces. | Mathematical/computational reference. See source PDF for full content. |
| `lattimore-bandit-algorithms` | Use when studying bandit algorithms and regret. | Mathematical/computational reference. See source PDF for full content. |
| `legal-agent-harness` | Use when improving legal AI agent benchmark harness design. | Use when implementing or improving a legal AI agent's harness to close the gap |
| `leinster-basic-category-theory` | Use when starting category theory. | Mathematical/computational reference. See source PDF for full content. |
| `leroy-compcert-compiler` | Use when studying formally verified compilers. | Mathematical/computational reference. See source PDF for full content. |
| `levin-peres-markov-mixing` | Use when studying Markov chain mixing times. | Mathematical/computational reference. See source PDF for full content. |
| `li-vitanyi-kolmogorov-complexity` | Use when studying Kolmogorov complexity and MDL. | Mathematical/computational reference. See source PDF for full content. |
| `liberzon-optimal-control` | Use when studying calculus of variations for control. | Mathematical/computational reference. See source PDF for full content. |
| `lin-error-control-coding` | Use when studying error control and channel coding. | Mathematical/computational reference. See source PDF for full content. |
| `linux-software-installation` | Use when installing software on Linux. Flatpak first. | This machine runs immutable Fedora (rpm-ostree base). `dnf` is NOT available in the PATH — `sudo dnf install` fails with 'command not found' |
| `llms4ol-ontology-integration` | Use when applying LLMs4OL to Hermes memory/skill ontology. | Source: Babaei Giglou et al., LLMs4OL (ISWC 2023) |
| `lm-polygraph-ue` | Use when estimating LLM output uncertainty or gating memory. "Use when estimating LLM output uncertainty. | Use when estimating LLM output uncertainty, detecting potential hallucinations, gating memory commits, or calibrating confidence scores. All |
| `luenberger-optimization` | Use when studying optimization in vector spaces. | Mathematical/computational reference. See source PDF for full content. |
| `lugosi-concentration-measure` | Use when bounding deviations via concentration. | Mathematical/computational reference. See source PDF for full content. |
| `lynch-distributed-algorithms` | Use when reasoning about atomicity, consensus, failure. | Knowledge base from Nancy Lynch & Boaz Patt-Shamir, *Distributed Algorithms* lecture notes for MIT 6.852 (Fall 1992; MIT/LCS RSS series, Jan |
| `mackay-information-theory` | Use when studying inference and learning via IT. | Mathematical/computational reference. See source PDF for full content. |
| `maclane-categories-working-mathematician` | Use when studying category theory deeply. | Mathematical/computational reference. See source PDF for full content. |
| `mallat-wavelet-tour` | Use when studying wavelets and sparse representations. | Mathematical/computational reference. See source PDF for full content. |
| `manning-information-retrieval` | Use when designing information retrieval systems. | Mathematical/computational reference. See source PDF for full content. |
| `memory-retrieval-over-write` | Use when diagnosing agent memory failures. Prefer retrieval over write pipelines. | Source: arXiv:2603.02473 — Diagnosing Retrieval vs. Utilization Bottlenecks. |
| `memory-topology-consolidator` | Use when merging co-accessed memory for RAG latency. | Reducing multi-hop RAG latency by merging frequently co-accessed memory entries. |
| `mezard-montanari-stat-physics` | Use when studying spin glasses and belief propagation. | Mathematical/computational reference. See source PDF for full content. |
| `milewski-category-for-programmers` | Use when applying CT to functional programming. | Mathematical/computational reference. See source PDF for full content. |
| `milne-abelian-varieties` | Use when studying abelian varieties. | Mathematical/computational reference. See source PDF for full content. |
| `milne-algebraic-geometry` | Use when working with schemes and algebraic geometry. | Mathematical/computational reference. See source PDF for full content. |
| `milne-algebraic-number-theory` | Use when studying algebraic number theory. | Mathematical/computational reference. See source PDF for full content. |
| `milne-class-field-theory` | Use when studying class field theory. | Mathematical/computational reference. See source PDF for full content. |
| `milne-etale-cohomology` | Use when studying etale cohomology. | These are the notes for a course taught at the University of Michigan in 1989 and 1998. In comparison with my book, the emphasis is on heuri |
| `milne-galois-theory` | Use when studying fields and Galois theory. | Milne's Fields and Galois Theory (v4.61) is a concise graduate text covering field extensions, separability, normality, and the Galois corre |
| `milne-group-theory` | Use when working with group theory fundamentals. | Milne's Group Theory (v3.16) is a concise graduate reference covering basic group theory through Sylow theorems, solvable groups, and free g |
| `milne-lie-algebras` | Use when studying Lie algebras and algebraic groups. | Mathematical/computational reference. See source PDF for full content. |
| `morters-brownian-motion` | Use when studying Brownian motion rigorously. | Mathematical/computational reference. See source PDF for full content. |
| `multi-agent-scaling-steiner` | Use when sizing fan-outs. Steiner task-type scaling rules. | Source: arXiv:2609.31563 - Multi-agent Scaling Across Disjunctive and Compensatory Tasks. |
| `murphy-pml-vol1` | Use when studying probabilistic ML volume 1. | Mathematical/computational reference. See source PDF for full content. |
| `murphy-pml-vol2` | Use when studying probabilistic ML volume 2. | Mathematical/computational reference. See source PDF for full content. |
| `network-vulnerability-scanning` | Use when scanning LAN hosts for vulnerabilities. Security audit, network reconnaissance, vulnerability assessment, nmap, | Covers: LAN host discovery, CVE/vuln scanning with nmap NSE, nuclei, and nikto. Runs from the Pi (192.168.0.138) which has nmap pre-installe |
| `ngo-alignment-dl` | Use when applying DL theory insights to agent reliability. | Ngo, Chan, Mindermann (2022) 'The Alignment Problem from a Deep Learning |
| `nica-speicher-free-probability` | Use when studying free probability theory. | Mathematical/computational reference. See source PDF for full content. |
| `nipkow-concrete-semantics` | Use when verifying programs with Isabelle/HOL. | Mathematical/computational reference. See source PDF for full content. |
| `nisan-algorithmic-game-theory` | Use when analyzing algorithmic game theory. | Over the last few years, there has been explosive growth in the research done at the in- terface of computer science, game theory, and econo |
| `nordstrom-martin-lof-tt` | Use when studying Martin-Lof type theory. | Mathematical/computational reference. See source PDF for full content. |
| `obstruction-certificate-cache` | Use when safely cleaning stale skills and memory. | Safely cleaning stale skills and memory entries; quantify removal risk first. |
| `odonnell-boolean-functions` | Use when analyzing Boolean functions and Fourier. | Mathematical/computational reference. See source PDF for full content. |
| `otter-tda-roadmap` | Use when surveying TDA tools and software. | Mathematical/computational reference. See source PDF for full content. |
| `parametric-saturation-monitor` | Use when detecting parametric-memory exhaustion. | Long sessions where the context window is filling and parametric memory may be exhausted. |
| `pearl-causality` | Use when detecting or gating causal claims in responses. | Pearl (2000/2009) Causality. Pearl & Mackenzie (2018) Book of Why. |
| `perrone-category-theory-notes` | Use when learning category theory concretely. | Mathematical/computational reference. See source PDF for full content. |
| `peyre-cuturi-computational-ot` | Use when computing optimal transport distances. | Mathematical/computational reference. See source PDF for full content. |
| `pi-os-cloudinit-ssh-setup` | Use when setting up a fresh Pi OS via SD card or cloud-init. | The singular `user:` key does NOT support `ssh_authorized_keys`. Must use list form: |
| `pierce-types-programming-languages` | Use when studying type systems for PLs. | Mathematical/computational reference. See source PDF for full content. |
| `progress-mirage-verification` | Use when verifying fixes. Grounded evidence required. | Based on arXiv:2604.28831. Self-reported success fails on 62% of tasks. |
| `puterman-mdp` | Use when analyzing Markov decision processes. | Mathematical/computational reference. See source PDF for full content. |
| `rasmussen-gaussian-processes` | Use when applying Gaussian process models. | Mathematical/computational reference. See source PDF for full content. |
| `rate-distortion-context-budget` | > | Rate-Distortion theory (Shannon, 1948; Cover & Thomas, 1991) provides the optimal tradeoff |
| `recursive-adversarial-hardening` | Use when hardening recursively. Cold audit-fix-reaudit loop. | Use when the user asks for a recursive adversarial pass until all high/medium issues are fixed, or when doing security hardening on a system |
| `reynolds-separation-logic` | Use when verifying heap-manipulating programs. | Mathematical/computational reference. See source PDF for full content. |
| `riehl-category-theory` | Use when studying category theory rigorously. | Mathematical/computational reference. See source PDF for full content. |
| `rijke-hott` | Use when learning homotopy type theory. | Mathematical/computational reference. See source PDF for full content. |
| `ripple-mem-recall` | Use when recalling skills. RippleMem anchor expansion. | Based on arXiv:2607.18844. Anchor expansion via similarity graph finds related skills. |
| `robinson-sheaf-engineering` | Use when applying sheaf methods to engineering. | Mathematical/computational reference. See source PDF for full content. |
| `roughgarden-game-theory` | Use when studying game theory via Roughgarden lectures. | Mathematical/computational reference. See source PDF for full content. |
| `royden-real-analysis` | Use when studying measure theory and Lp spaces. | Mathematical/computational reference. See source PDF for full content. |
| `scholkopf-causal-representation` | Use when studying causal representation learning. | Mathematical/computational reference. See source PDF for full content. |
| `schrijver-combinatorial-optimization` | Use when studying combinatorial optimization. | Mathematical/computational reference. See source PDF for full content. |
| `shalev-understanding-ml` | Use when studying learning theory and PAC learning. | Mathematical/computational reference. See source PDF for full content. |
| `shannon-communication-theory` | Use when grounding in Shannon information theory. | Mathematical/computational reference. See source PDF for full content. |
| `shiebler-category-theory-ml` | Use when applying CT to ML architectures. | /University of Oxford/University of Strathclyde/University of Southampton/ /daniel.shiebler@kellog.ox.ac.uk/bruno@brunogavranovic.com/paul@s |
| `shoham-multiagent-systems` | Use when designing multiagent systems. | Mathematical/computational reference. See source PDF for full content. |
| `sipser-theory-computation` | Use when studying automata and computability. | Mathematical/computational reference. See source PDF for full content. |
| `skill-fulltext-routing` | Use when routing among many skills. Full skill text beats description-only routing. | Source: arXiv:2603.22455 — SkillRouter. |
| `soares-agent-foundations` | Use when checking agent corrigibility and decision theory. | Soares & Fallenstein (2014) 'Aligning Superintelligence with Human Interests'. |
| `sontag-control-theory` | Use when studying mathematical control theory. | Mathematical/computational reference. See source PDF for full content. |
| `spielman-spectral-graph-theory` | Use when studying spectral graph algorithms. | Mathematical/computational reference. See source PDF for full content. |
| `spivak-category-for-scientists` | Use when modeling systems with category theory. | Mathematical/computational reference. See source PDF for full content. |
| `stanley-enumerative-combinatorics` | Use when counting combinatorial structures. | Mathematical/computational reference. See source PDF for full content. |
| `statecomp-compression-timing` | Use when compressing context. StateComp span-readiness. | Based on arXiv:2609.27298. Only compress spans where reasoning is externalized to files/tools. |
| `strogatz-nonlinear-dynamics` | Use when studying nonlinear dynamics and chaos. | Mathematical/computational reference. See source PDF for full content. |
| `sutton-barto-rl` | Use when studying reinforcement learning fundamentals. | Mathematical/computational reference. See source PDF for full content. |
| `szeliski-computer-vision` | Use when studying computer vision algorithms. | Mathematical/computational reference. See source PDF for full content. |
| `teschl-odes` | Use when studying ordinary differential equations. | Mathematical/computational reference. See source PDF for full content. |
| `teschl-spectral-theory` | Use when studying spectral theory operator methods. | page 46 (1 page) — after "0.7. Appendix: The uniform boundedness principle 33 In other" (p45) page 48 (1 page) — after "Part 1 Mathematical  |
| `theory-to-implementation-extrapolation` | Use when deriving Hermes components from theory. | Use when a textbook theorem, lemma, or framework should force a new Hermes runtime piece: memory (SQLite), scheduler/cron, compressor (lambd |
| `thompson-type-theory-fp` | Use when studying type theory for functional programming. | Mathematical/computational reference. See source PDF for full content. |
| `tool-schema-filter-first` | Use when cutting agent token cost. Filter tool schemas before content compression. | Source: arXiv:2609.22114 — Empirical Cost Attribution of Context-Compression Gateways. |
| `tplink-ax55-api-auth` | Use when authenticating to TP-Link AX55 router API. Router authentication, network device API, admin session management. | The AX55 web UI uses RSA+AES encrypted login — plaintext POST/GET won't work. The browser vault_fill also fails with hash URLs on camofox ta |
| `treil-linear-algebra` | Use when studying linear algebra rigorously. | Mathematical/computational reference. See source PDF for full content. |
| `vakil-algebraic-geometry` | Use when learning algebraic geometry via schemes. | page 12 (1 page) — after "© 2025 Ravi Vakil. Published by Princeton University Press. " (p11) page 24 (1 page) — after "© 2025 Ravi Vakil. P |
| `vazirani-approximation-algorithms` | Use when designing approximation algorithms. | Mathematical/computational reference. See source PDF for full content. |
| `vershynin-hdp` | Use when studying high-dimensional probability. | Mathematical/computational reference. See source PDF for full content. |
| `vetterli-signal-processing` | Use when studying foundations of signal processing. | Mathematical/computational reference. See source PDF for full content. |
| `villani-optimal-transport` | Use when studying optimal transport theory. | Mathematical/computational reference. See source PDF for full content. |
| `wainwright-jordan-graphical-models` | Use when studying graphical models variational inference. | Mathematical/computational reference. See source PDF for full content. |
| `wald-sequential-analysis` | Use when studying sequential hypothesis testing. | Mathematical/computational reference. See source PDF for full content. |
| `watrous-quantum-information` | Use when studying quantum information theory. | Mathematical/computational reference. See source PDF for full content. |
| `wave21b-routing-bandits` | Use when Wave 21B routing/bandits/online. | Wave 21B PAC-Bayes, EXP3/EXP4, Fano, Möbius, KL-UCB, Tsallis-INF, LinUCB, token influence, skill-graph percolation, loopy BP, or routing ala |
| `wave21c-loop-governance` | Use when Wave 21C ISS/SPRT/governance gates. | Wave 21C composite stability, Wald SPRT promotion, multi-principal governance conflicts, falsifiability lint, taint audit, or PID model comp |
| `web-app-api-reverse-engineering` | Use when reverse-engineering an undocumented web/app API. | Use when a target service has no public API docs and you need to discover endpoints, auth schemes, and request formats by inspecting the app |
| `wigderson-mathematics-computation` | Use when connecting complexity and mathematics. | Mathematical/computational reference. See source PDF for full content. |
| `wilde-quantum-information` | Use when studying quantum Shannon theory. | Mathematical/computational reference. See source PDF for full content. |
| `williams-probability-martingales` | Use when studying martingale theory. | Mathematical/computational reference. See source PDF for full content. |
| `windows-remote-management` | Use when managing Windows PCs remotely via SSH or Tailscale. | Covers: connecting to Windows machines over Tailscale SSH, setting up passwordless key auth, running Windows Update remotely, and auditing d |
| `zhang-d2l-deep-learning` | Use when studying deep learning with code. | Mathematical/computational reference. See source PDF for full content. |
| `zhao-additive-combinatorics` | Use when analyzing additive structure in sets/graphs. | - Exploring Structure and Randomness |

### CRONS (`profiles/fork/cron/`)

| Job ID | Schedule | What it does | Outputs |
|--------|----------|--------------|---------|
| `shadow-gate-0001` | `{'kind': 'cron', 'expr': '0 8 * * *'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/shadow-gate-0001.sh |  |
| `calibration-threshold-updater-0001` | `{'kind': 'cron', 'expr': '0 6 * * *'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/calibration-threshold-updater-0001.sh |  |
| `recall-miss-ttl-adjuster-0001` | `{'kind': 'cron', 'expr': '0 5 * * *'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/recall-miss-ttl-adjuster-0001.sh |  |
| `routing-weight-updater-0001` | `{'kind': 'cron', 'expr': '0 7 * * *'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/routing-weight-updater-0001.sh |  |
| `pre-compact-annotate-0001` | `{'kind': 'cron', 'expr': '*/15 * * * *'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/pre-compact-annotate-0001.sh |  |
| `fork-state-vacuum-0001` | `{'kind': 'cron', 'expr': '0 3 * * 0'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/fork-state-vacuum-0001.sh |  |
| `memory-ttl-purge-0001` | `{'kind': 'cron', 'expr': '0 4 * * *'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/memory-ttl-purge-0001.sh |  |
| `concept-lattice-rebuild-0001` | `{'kind': 'cron', 'expr': '0 2 * * *'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/concept-lattice-rebuild-0001.sh |  |
| `omni-skill-scan-0001` | `{'kind': 'cron', 'expr': '0 1 * * *'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/omni-skill-scan-0001.sh |  |
| `spike-queue-actuator-0001` | `{'kind': 'cron', 'expr': '0 10 * * *'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/spike-queue-actuator-0001.sh |  |
| `cross-calibration-monitor-0001` | `{'kind': 'cron', 'expr': '0 11 * * *'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/cross-calibration-monitor-0001.sh |  |
| `monitor-suite-runner-0001` | `{'kind': 'cron', 'expr': '0 */2 * * *'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/monitor-suite-runner-0001.sh |  |
| `mcp-privilege-audit-0001` | `{'kind': 'cron', 'expr': '0 3 * * 1'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/mcp-privilege-audit-0001.sh |  |
| `hermes-gateway-prestart-0001` | `{'kind': 'cron', 'expr': '0 4 * * *'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/hermes-gateway-prestart-0001.sh |  |
| `52776e518fc1` | `{'kind': 'interval', 'minutes': 1440, 'display': 'every 1440m'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/52776e518fc1.sh |  |
| `3170e542c493` | `{'kind': 'interval', 'minutes': 1440, 'display': 'every 1440m'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/3170e542c493.sh |  |
| `064999e8aff3` | `{'kind': 'interval', 'minutes': 10, 'display': 'every 10m'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/064999e8aff3.sh |  |
| `2b3f3a0f79a0` | `{'kind': 'interval', 'minutes': 720, 'display': 'every 720m'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/2b3f3a0f79a0.sh |  |
| `1ea1d2459f51` | `{'kind': 'interval', 'minutes': 245, 'display': 'every 245m'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/1ea1d2459f51.sh |  |
| `ebe4fd06d379` | `{'kind': 'interval', 'minutes': 180, 'display': 'every 180m'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/ebe4fd06d379.sh |  |
| `e034d0179aa9` | `{'kind': 'cron', 'expr': '0 9 * * *', 'display': '0 9 * * *'}` | Read ~/.hermes/memory-facts/staging.md. For each bullet line in that file:  1. Strip the timestamp and score prefix (e.g. "- [2026-07-09T09: |  |
| `3f5af7731df4` | `{'kind': 'interval', 'minutes': 220, 'display': 'every 220m'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/3f5af7731df4.sh |  |
| `7dc01def3354` | `{'kind': 'cron', 'expr': '0 3 * * *', 'display': '0 3 * * *'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/7dc01def3354.sh |  |
| `061dfd4d2bb9` | `{'kind': 'interval', 'minutes': 250, 'display': 'every 250m'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/061dfd4d2bb9.sh |  |
| `625d44f3ef9f` | `{'kind': 'cron', 'expr': '0 6 * * 0', 'display': '0 6 * * 0'}` | Run the WikiSkill maintenance pass: for each active skill in ~/.hermes/skills/, check if there are recent session insights (from the past 7  |  |
| `fa1df4f4270e` | `{'kind': 'interval', 'minutes': 230, 'display': 'every 230m'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/fa1df4f4270e.sh |  |
| `bcb9c8082d9c` | `{'kind': 'cron', 'expr': '0 17 * * 5', 'display': '0 17 * * 5'}` | The script has already run and written a weekly review scaffold to the Obsidian vault at ~/Documents/SecondBrain/Reviews/YYYY-MM-DD-weekly.m |  |
| `d984a185e83a` | `{'kind': 'cron', 'expr': '0 3 * * 0', 'display': '0 3 * * 0'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/d984a185e83a.sh |  |
| `f8aa4b717a18` | `{'kind': 'cron', 'expr': '0 9 1 * *', 'display': '0 9 1 * *'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/f8aa4b717a18.sh |  |
| `8dea5993a20b` | `{'kind': 'interval', 'minutes': 90, 'display': 'every 90m'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/8dea5993a20b.sh |  |
| `670a8904edf4` | `{'kind': 'cron', 'expr': '0 5 * * 0', 'display': '0 5 * * 0'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/670a8904edf4.sh |  |
| `ea4a9468f4d9` | `{'kind': 'cron', 'expr': '0 5 * * 6', 'display': '0 5 * * 6'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/ea4a9468f4d9.sh |  |
| `d026ce426364` | `{'kind': 'interval', 'minutes': 360}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/d026ce426364.sh |  |
| `stuck-job-detector-beb3cf57` | `{'kind': 'interval', 'minutes': 15, 'display': 'every 15m', 'type': 'interval', 'interval_seconds': 900}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/stuck-job-detector-beb3cf57.sh |  |
| `staleness-monitor-24f8e4a1` | `{'kind': 'interval', 'minutes': 60}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/staleness-monitor-24f8e4a1.sh |  |
| `skill-index-weekly-rebuild-4fffb154` | `{'kind': 'cron', 'expr': '0 3 * * 0'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/skill-index-weekly-rebuild-4fffb154.sh |  |
| `d2916301202e` | `{'kind': 'cron', 'expr': '0 */6 * * *', 'display': '0 */6 * * *'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/d2916301202e.sh |  |
| `06e4c802b583` | `{'kind': 'cron', 'expr': '0 23 * * *', 'display': '0 23 * * *'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/06e4c802b583.sh |  |
| `w16-statecomp-f3622785` | `{'kind': 'interval', 'minutes': 360, 'display': 'every 360m'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/w16-statecomp-f3622785.sh |  |
| `w16-ripple-build-6848b287` | `{'kind': 'interval', 'minutes': 720, 'display': 'every 720m'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/w16-ripple-build-6848b287.sh |  |
| `w16-evograph-b03ef1d3` | `{'kind': 'cron', 'expr': '0 5 * * *', 'display': 'daily at 05:00'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/w16-evograph-b03ef1d3.sh |  |
| `w16-mirage-audit-02cdb6c7` | `{'kind': 'interval', 'minutes': 480, 'display': 'every 480m'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/w16-mirage-audit-02cdb6c7.sh |  |
| `w16-cmtf-audit-91ca72ad` | `{'kind': 'interval', 'minutes': 480, 'display': 'every 480m'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/w16-cmtf-audit-91ca72ad.sh |  |
| `wave18-sheaf-memory-gluing-0001` | `{'kind': 'cron', 'expr': '30 4 * * *'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/wave18-sheaf-memory-gluing-0001.sh |  |
| `wave18-skill-routing-causal-audit-0001` | `{'kind': 'cron', 'expr': '30 5 * * *'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/wave18-skill-routing-causal-audit-0001.sh |  |
| `cron-mdp-policy-0001` | `{'kind': 'interval', 'minutes': 60, 'tz': 'Australia/Sydney'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/cron-mdp-policy-0001.sh |  |
| `nyquist-bandwidth-0001` | `{'kind': 'interval', 'minutes': 60, 'tz': 'Australia/Sydney'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/nyquist-bandwidth-0001.sh |  |
| `iss-small-gain-0001` | `{'kind': 'interval', 'minutes': 60, 'tz': 'Australia/Sydney'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/iss-small-gain-0001.sh |  |
| `two-timescale-0001` | `{'kind': 'interval', 'minutes': 60, 'tz': 'Australia/Sydney'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/two-timescale-0001.sh |  |
| `cron-ucb-safe-0001` | `{'kind': 'interval', 'minutes': 30, 'tz': 'Australia/Sydney'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/cron-ucb-safe-0001.sh |  |
| `wave18-memory-invariants-0001` | `{'kind': 'interval', 'minutes': 720}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/wave18-memory-invariants-0001.sh |  |
| `real-options-fanout-gate-0001` | `{'kind': 'interval', 'minutes': 30}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/real-options-fanout-gate-0001.sh |  |
| `doob-strata-decompose-0001` | `{'kind': 'cron', 'expr': '30 3 * * *'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/doob-strata-decompose-0001.sh |  |
| `shadow-gate-sprt-0001` | `{'kind': 'interval', 'minutes': 60, 'display': 'every 60m'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/shadow-gate-sprt-0001.sh |  |
| `governance-conflict-detector-0001` | `{'kind': 'cron', 'expr': '30 9 * * *'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/governance-conflict-detector-0001.sh |  |
| `governance-falsifiability-lint-0001` | `{'kind': 'cron', 'expr': '0 6 * * 2'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/governance-falsifiability-lint-0001.sh |  |
| `loop-model-comparison-0001` | `{'kind': 'interval', 'minutes': 120, 'display': 'every 120m'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/loop-model-comparison-0001.sh |  |
| `callgraph-taint-audit-0001` | `{'kind': 'cron', 'expr': '30 5 * * *'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/callgraph-taint-audit-0001.sh |  |
| `nyquist-timescale-bridge-0001` | `{'kind': 'interval', 'minutes': 120, 'display': 'every 120m'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/nyquist-timescale-bridge-0001.sh |  |
| `loop-cusum-changepoint-0001` | `{'kind': 'interval', 'minutes': 120, 'display': 'every 120m'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/loop-cusum-changepoint-0001.sh |  |
| `wave21c-alarm-bridge-0001` | `{'kind': 'interval', 'minutes': 30, 'display': 'every 30m'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/wave21c-alarm-bridge-0001.sh |  |
| `sprt-falsifiability-handshake-0001` | `{'kind': 'cron', 'expr': '15 8 * * *', 'display': 'daily 08:15'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/sprt-falsifiability-handshake-0001.sh |  |
| `governance-conflict-epistemic-0001` | `{'kind': 'cron', 'expr': '45 9 * * *', 'display': 'daily 09:45'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/governance-conflict-epistemic-0001.sh |  |
| `pid-passivity-index-0001` | `{'kind': 'interval', 'minutes': 120, 'display': 'every 120m'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/pid-passivity-index-0001.sh |  |
| `pid-circle-criterion-0001` | `{'kind': 'interval', 'minutes': 120, 'display': 'every 120m'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/pid-circle-criterion-0001.sh |  |
| `ltl-promotion-invariant-0001` | `{'kind': 'cron', 'expr': '35 8 * * *', 'display': 'daily 08:35'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/ltl-promotion-invariant-0001.sh |  |
| `loop-rollout-horizon-0001` | `{'kind': 'interval', 'minutes': 120, 'display': 'every 120m'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/loop-rollout-horizon-0001.sh |  |
| `sprt-measurement-tamper-0001` | `{'kind': 'cron', 'expr': '10 8 * * *', 'display': 'daily 08:10'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/sprt-measurement-tamper-0001.sh |  |
| `soares-halt-liveness-0001` | `{'kind': 'interval', 'minutes': 120, 'display': 'every 120m'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/soares-halt-liveness-0001.sh |  |
| `cusum-gain-freeze-0001` | `{'kind': 'interval', 'minutes': 120, 'display': 'every 120m'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/cusum-gain-freeze-0001.sh |  |
| `sprt-inner-outer-alignment-0001` | `{'kind': 'cron', 'expr': '20 8 * * *', 'display': 'daily 08:20'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/sprt-inner-outer-alignment-0001.sh |  |
| `iss-justification-gate-0001` | `{'kind': 'interval', 'minutes': 30, 'display': 'every 30m'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/iss-justification-gate-0001.sh |  |
| `wave21c-invariants-0001` | `{'kind': 'cron', 'expr': '30 6 * * 2', 'display': 'weekly Tue 06:30'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/wave21c-invariants-0001.sh |  |
| `routing-pac-bayes-bound-0001` | `{'kind': 'cron', 'expr': '30 7 * * *'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/routing-pac-bayes-bound-0001.sh |  |
| `routing-fano-bound-0001` | `{'kind': 'cron', 'expr': '45 7 * * *'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/routing-fano-bound-0001.sh |  |
| `routing-graph-bandit-update-0001` | `{'kind': 'cron', 'expr': '30 8 * * *'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/routing-graph-bandit-update-0001.sh |  |
| `routing-exp3-adversarial-0001` | `{'kind': 'cron', 'expr': '0 9 * * *'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/routing-exp3-adversarial-0001.sh |  |
| `routing-hamming-audit-0001` | `{'kind': 'cron', 'expr': '0 6 * * 0'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/routing-hamming-audit-0001.sh |  |
| `routing-mobius-audit-0001` | `{'kind': 'cron', 'expr': '0 7 * * 0'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/routing-mobius-audit-0001.sh |  |
| `skill-description-entropy-0001` | `{'kind': 'cron', 'expr': '0 6 * * 1'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/skill-description-entropy-0001.sh |  |
| `sprt-truncation-gate-0001` | `{'kind': 'cron', 'expr': '12 8 * * *', 'display': 'daily 08:12'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/sprt-truncation-gate-0001.sh |  |
| `promotion-at-most-once-0001` | `{'kind': 'cron', 'expr': '40 8 * * *', 'display': 'daily 08:40'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/promotion-at-most-once-0001.sh |  |
| `sprt-effective-decision-0001` | `{'kind': 'cron', 'expr': '25 8 * * *', 'display': 'daily 08:25'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/sprt-effective-decision-0001.sh |  |
| `routing-azuma-concentration-0001` | `{'kind': 'cron', 'expr': '25 7 * * *'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/routing-azuma-concentration-0001.sh |  |
| `routing-graph-independence-0001` | `{'kind': 'cron', 'expr': '40 8 * * *'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/routing-graph-independence-0001.sh |  |
| `routing-ips-offpolicy-0001` | `{'kind': 'cron', 'expr': '18 9 * * *'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/routing-ips-offpolicy-0001.sh |  |
| `routing-mutual-information-0001` | `{'kind': 'cron', 'expr': '40 7 * * *'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/routing-mutual-information-0001.sh |  |
| `routing-switching-detector-0001` | `{'kind': 'cron', 'expr': '10 8 * * *'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/routing-switching-detector-0001.sh |  |
| `routing-wald-sprt-0001` | `{'kind': 'cron', 'expr': '55 8 * * *'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/routing-wald-sprt-0001.sh |  |
| `memory-sprt-commit-0001` | `{'kind': 'cron', 'expr': '*/30 * * * *'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/memory-sprt-commit-0001.sh |  |
| `memory-conductance-ttl-0001` | `{'kind': 'cron', 'expr': '45 3 * * *'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/memory-conductance-ttl-0001.sh |  |
| `memory-adaptive-rank-0001` | `{'kind': 'cron', 'expr': '15 4 * * *'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/memory-adaptive-rank-0001.sh |  |
| `context-channel-capacity-0001` | `{'kind': 'cron', 'expr': '*/15 * * * *'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/context-channel-capacity-0001.sh |  |
| `memory-ot-decay-0001` | `{'kind': 'cron', 'expr': '45 4 * * *'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/memory-ot-decay-0001.sh |  |
| `memory-fano-bound-0001` | `{'kind': 'cron', 'expr': '16 4 * * *'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/memory-fano-bound-0001.sh |  |
| `compaction-rd-converse-0001` | `{'kind': 'cron', 'expr': '*/15 * * * *'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/compaction-rd-converse-0001.sh |  |
| `compaction-aep-typical-set-0001` | `{'kind': 'cron', 'expr': '*/15 * * * *'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/compaction-aep-typical-set-0001.sh |  |
| `memory-haar-mra-0001` | `{'kind': 'cron', 'expr': '0 5 * * *'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/memory-haar-mra-0001.sh |  |
| `memory-hitting-time-0001` | `{'kind': 'cron', 'expr': '15 5 * * *'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/memory-hitting-time-0001.sh |  |
| `memory-jl-distortion-0001` | `{'kind': 'cron', 'expr': '30 4 * * *'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/memory-jl-distortion-0001.sh |  |
| `memory-renorm-counterterm-0001` | `{'kind': 'cron', 'expr': '0 3 * * *'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/memory-renorm-counterterm-0001.sh |  |
| `kl-curvature-memory-monitor-0001` | `{'kind': 'cron', 'expr': '0 6 * * *'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/kl-curvature-memory-monitor-0001.sh |  |
| `wave21a-alarm-bridge-ev15` | `{'kind': 'cron', 'expr': '*/15 * * * *'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/wave21a-alarm-bridge-ev15.sh |  |
| `memory-ttl-floor-merge-0400` | `{'kind': 'cron', 'expr': '0 4 * * *'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/memory-ttl-floor-merge-0400.sh |  |
| `memory-sanov-ld-ev30` | `{'kind': 'cron', 'expr': '*/30 * * * *'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/memory-sanov-ld-ev30.sh |  |
| `memory-optional-stopping-ev30` | `{'kind': 'cron', 'expr': '*/30 * * * *'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/memory-optional-stopping-ev30.sh |  |
| `compaction-chain-rule-mi-ev15` | `{'kind': 'cron', 'expr': '*/15 * * * *'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/compaction-chain-rule-mi-ev15.sh |  |
| `memory-dkw-ue-ev30` | `{'kind': 'cron', 'expr': '*/30 * * * *'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/memory-dkw-ue-ev30.sh |  |
| `memory-displacement-conv-0450` | `{'kind': 'cron', 'expr': '50 4 * * *'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/memory-displacement-conv-0450.sh |  |
| `memory-bethe-free-energy-0500` | `{'kind': 'cron', 'expr': '0 5 * * *'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/memory-bethe-free-energy-0500.sh |  |
| `memory-lp-dct-gate-ev30` | `{'kind': 'cron', 'expr': '*/30 * * * *'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/memory-lp-dct-gate-ev30.sh |  |
| `memory-malliavin-ibp-0510` | `{'kind': 'cron', 'expr': '10 5 * * *'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/memory-malliavin-ibp-0510.sh |  |
| `memory-kraft-code-0520` | `{'kind': 'cron', 'expr': '20 5 * * *'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/memory-kraft-code-0520.sh |  |
| `memory-matrix-bernstein-0530` | `{'kind': 'cron', 'expr': '30 5 * * *'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/memory-matrix-bernstein-0530.sh |  |
| `memory-gelman-shrink-0540` | `{'kind': 'cron', 'expr': '40 5 * * *'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/memory-gelman-shrink-0540.sh |  |
| `memory-log-ode-sig-0550` | `{'kind': 'cron', 'expr': '50 5 * * *'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/memory-log-ode-sig-0550.sh |  |
| `memory-bits-back-0600` | `{'kind': 'cron', 'expr': '0 6 * * *'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/memory-bits-back-0600.sh |  |
| `memory-portmanteau-ev30` | `{'kind': 'cron', 'expr': '*/30 * * * *'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/memory-portmanteau-ev30.sh |  |
| `memory-heisenberg-tf-0610` | `{'kind': 'cron', 'expr': '10 6 * * *'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/memory-heisenberg-tf-0610.sh |  |
| `routing-kl-ucb-0720` | `{'kind': 'cron', 'expr': '20 7 * * *'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/routing-kl-ucb-0720.sh |  |
| `routing-rademacher-0735` | `{'kind': 'cron', 'expr': '35 7 * * *'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/routing-rademacher-0735.sh |  |
| `routing-prec-recall-0750` | `{'kind': 'cron', 'expr': '50 7 * * *'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/routing-prec-recall-0750.sh |  |
| `routing-skill-markov-0755` | `{'kind': 'cron', 'expr': '55 7 * * *'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/routing-skill-markov-0755.sh |  |
| `routing-belief-prop-0845` | `{'kind': 'cron', 'expr': '45 8 * * *'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/routing-belief-prop-0845.sh |  |
| `routing-exp4-ctx-0905` | `{'kind': 'cron', 'expr': '5 9 * * *'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/routing-exp4-ctx-0905.sh |  |
| `routing-linucb-0910` | `{'kind': 'cron', 'expr': '10 9 * * *'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/routing-linucb-0910.sh |  |
| `routing-tsallis-inf-0912` | `{'kind': 'cron', 'expr': '12 9 * * *'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/routing-tsallis-inf-0912.sh |  |
| `routing-bool-infl-sun0630` | `{'kind': 'cron', 'expr': '30 6 * * 0'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/routing-bool-infl-sun0630.sh |  |
| `routing-skill-perc-sun0645` | `{'kind': 'cron', 'expr': '45 6 * * 0'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/routing-skill-perc-sun0645.sh |  |
| `routing-mcdiarmid-sun0715` | `{'kind': 'cron', 'expr': '15 7 * * 0'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/routing-mcdiarmid-sun0715.sh |  |
| `skill-comp-gf-mon0630` | `{'kind': 'cron', 'expr': '30 6 * * 1'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/skill-comp-gf-mon0630.sh |  |
| `routing-token-setcover-mon0640` | `{'kind': 'cron', 'expr': '40 6 * * 1'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/routing-token-setcover-mon0640.sh |  |
| `memory-mixing-ttl-0001` | `{'kind': 'cron', 'expr': '30 3 * * *'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/memory-mixing-ttl-0001.sh |  |
| `routing-alarm-bridge-ev15` | `{'kind': 'cron', 'expr': '*/15 * * * *'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/routing-alarm-bridge-ev15.sh |  |
| `85eb5f1008eb` | `{'kind': 'cron', 'expr': '0 8 * * *', 'display': '0 8 * * *'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/85eb5f1008eb.sh |  |
| `a1236b11e683` | `{'kind': 'interval', 'minutes': 60, 'display': 'every 60m'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/a1236b11e683.sh |  |
| `7a754d5b1b04` | `{'kind': 'cron', 'expr': '0 2 * * 0', 'display': '0 2 * * 0'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/7a754d5b1b04.sh |  |
| `d2974213a3cc` | `{'kind': 'cron', 'expr': '0 3 * * 0', 'display': '0 3 * * 0'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/d2974213a3cc.sh |  |
| `4c18ade84cdf` | `{'kind': 'cron', 'expr': '0 6 * * *', 'display': '0 6 * * *'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/4c18ade84cdf.sh |  |
| `ue-memory-gate-cron-0001` | `{'kind': 'cron', 'expr': '0 5 * * *'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/ue-memory-gate-cron-0001.sh |  |
| `1a6ee3fc9a9c` | `{'kind': 'cron', 'expr': '0 3 * * 0', 'display': 'Sunday 03:00 UTC (14:00 AEDT)'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/1a6ee3fc9a9c.sh |  |
| `memory-auto-improvement-0001` | `{'kind': 'cron', 'expr': '0 3 * * *'}` | /var/home/rainbow/.hermes/profiles/fork/scripts/cron-sandboxed/memory-auto-improvement-0001.sh |  |

### MEMORY

- `memory.md`: not present in fork profile
- `user.md`: not present in fork profile
- `/var/home/rainbow/.hermes/profiles/fork/SOUL.md` (1 lines). Head: You are Hermes Agent, built by Nous Research. Be direct: match the length of your reply to the weight of the ask — a one-line question gets a one-line answer, and finished work gets a short report of what changed, what's verified, and what'
- `/var/home/rainbow/.hermes/profiles/fork/AGENTS.md` (15 lines). Head: # hermes-fork profile  This is the **amoni094/hermes-fork** build — a private fork of NousResearch/hermes-agent on branch `feature/adaptive-compression-plugin-api`.  Install: `~/.hermes/hermes-fork/` (venv at `.../venv`) Profile: `~/.hermes
- Update cadence: session-end / explicit user fact; writers: agent (memory.md), user+agent (user.md). H-I2: one writer per fact class.

### LIFECYCLE.DB (`~/.hermes/memory-facts/lifecycle.db`)

| Table | Columns | Writers / readers |
|-------|---------|-------------------|
| `episode_dag_edges` (0 rows) | edge_id, parent_episode_id, child_episode_id, edge_type, created_at | lifecycle-schema-extension.py |
| `fact_lifecycle` (11 rows) | memory_id, fact_text, fact_type, volatility_class, valid_from, valid_to, superseded_by, access_count, last_accessed, int | memory TTL / access scripts; readers: consolidator, obstruction stub |
| `sqlite_sequence` (0 rows) | name, seq | various scripts |
| `step_state_snapshots` (0 rows) | snapshot_id, episode_id, step_num, state_json, timestamp | lifecycle-schema-extension.py |
| `tracegrant_grants` (132 rows) | grant_id, session_id, caller, source_type, allowed_ns, granted_at, revoked, revoked_at, taint_path, decision_hash | l1-tracegrant.py |

### CACHE (`profiles/fork/cache/` and `cache/research/`)

Enumerated 350 files (cap 350).

| File | Role |
|------|------|
| `cache/.ai-memory-post-20261026_155623_978c4b` | blob |
| `cache/.ai-memory-post-20261026_155858_a27f0e` | blob |
| `cache/.ai-memory-post-20261026_163531_c359b8` | blob |
| `cache/.ai-memory-post-20261026_171136_ef5636` | blob |
| `cache/.ai-memory-post-20261026_171136_fb01d4` | blob |
| `cache/.ai-memory-post-20261026_171728_adc9a8` | blob |
| `cache/.ai-memory-post-20261026_171933_6e3e64` | blob |
| `cache/.ai-memory-post-20261026_173025_3ad9c6` | blob |
| `cache/.ai-memory-post-20261027_110701_32806b` | blob |
| `cache/.ai-memory-post-20261027_110701_464d7a` | blob |
| `cache/.ai-memory-post-20261027_111544_3812de` | blob |
| `cache/.ai-memory-post-20261027_111544_db9da0` | blob |
| `cache/.ai-memory-post-20261027_113551_310fe8` | blob |
| `cache/.ai-memory-post-20261027_113551_b0c84b` | blob |
| `cache/.ai-memory-post-20261027_114757_43a597` | blob |
| `cache/.ai-memory-post-20261027_114757_e3864a` | blob |
| `cache/.ai-memory-post-20261027_120336_ac332c` | blob |
| `cache/.ai-memory-post-20261027_120336_cf0ee4` | blob |
| `cache/.ai-memory-post-20261027_121624_6214cc` | blob |
| `cache/.ai-memory-post-20261027_121624_9932e2` | blob |
| `cache/.ai-memory-post-20261027_123036_30ea1e` | blob |
| `cache/.ai-memory-post-20261027_123036_e73aed` | blob |
| `cache/.ai-memory-post-20261027_131641_bf3f45` | blob |
| `cache/.ai-memory-post-20261027_142824_5699fa` | blob |
| `cache/.ai-memory-post-20261027_142824_9fa950` | blob |
| `cache/.ai-memory-post-20261027_153013_127dd2` | blob |
| `cache/.ai-memory-post-20261027_174813_b645ab` | blob |
| `cache/.ai-memory-post-20261027_191238_57f26c` | blob |
| `cache/.ai-memory-post-20261028_162052_ba089d` | blob |
| `cache/.ai-memory-post-20261028_162727_7db50f` | blob |
| `cache/.ai-memory-post-20261028_194952_711e9d` | blob |
| `cache/.ai-memory-post-20261028_194952_ce2df3` | blob |
| `cache/.ai-memory-post-abc-123` | blob |
| `cache/.ai-memory-post-local-198adbc2f3013cf4b57e9c2d50174133d440773fb5e898ea96055da385a685bd` | blob |
| `cache/.ai-memory-post-local-3088f1b924d6dbeaf705512dd2839db729cdf3528e416d093770fbe69a681977` | blob |
| `cache/.ai-memory-post-local-4378f2abb3e1276144b61072a97225d37f9be75ff26b950499e0c69dbec9b60d` | blob |
| `cache/.ai-memory-post-local-4f56be0d51c9bbfdaa4fc8d5bb7bd52b833949c7a32c2b099c833b3c3824fe73` | blob |
| `cache/.ai-memory-post-local-9f222b8b22f6cb2d9638e43024333cb5511d379bbfc09c47b898b4757c4e213a` | blob |
| `cache/.ai-memory-post-local-a6f62f9a1367f822d77f02588ec094bf3600eb260de34a636b0fd72fca85dddc` | blob |
| `cache/.ai-memory-post-local-a7ca68911ff4dd0747143aaa6376ef5f26d4703e31147709ecd9461b955a4752` | blob |
| `cache/.ai-memory-post-local-c90785c71301879a0585b9c417c35e74910e6fecd9646e0031664fe8e99a211a` | blob |
| `cache/.ai-memory-post-local-e25777aabf9916cc01c7e23386bbbd6076ccdda01c1c7c655a7d552764dc5187` | blob |
| `cache/.ai-memory-post-local-ebdd867f1f04d5c5b165191360c1bd16ba19bb8041e37f1a980621d577032e43` | blob |
| `cache/.ai-memory-post-local-f83aae8c8f3b7d3e2ffb9c614665ef2f2addfd28245a6453c261a6e195cdc7d3` | blob |
| `cache/action-log.jsonl` | append-only event log |
| `cache/adaptive-ttl-state.json` | JSON state/report |
| `cache/adv-audit-findings.json` | JSON state/report |
| `cache/alarm-summary.json` | JSON state/report |
| `cache/ann-embeddings-probe.json` | JSON state/report |
| `cache/banner_snapshot.json` | JSON state/report |
| `cache/block-bootstrap-sprt.json` | JSON state/report |
| `cache/bps-selection-log.jsonl` | append-only event log |
| `cache/calibration-log.jsonl` | append-only event log |
| `cache/calibration-map.json` | JSON state/report |
| `cache/callgraph-taint-report.json` | JSON state/report |
| `cache/compacted-context.txt` | blob |
| `cache/compaction-aep-typical-set.json` | JSON state/report |
| `cache/compaction-chain-rule-mi.json` | JSON state/report |
| `cache/compaction-rd-advice.json` | JSON state/report |
| `cache/compaction-rd-converse.json` | JSON state/report |
| `cache/concept-lattice.json` | JSON state/report |
| `cache/concept-lattice.jsonl` | append-only event log |
| `cache/condorcet-thresholds.json` | JSON state/report |
| `cache/confidence-trajectory.json` | JSON state/report |
| `cache/consensus-alarm.json` | JSON state/report |
| `cache/consensus-state.json` | JSON state/report |
| `cache/context-channel-capacity.json` | JSON state/report |
| `cache/context-channel-capacity.jsonl` | append-only event log |
| `cache/cron-mdp-policy.json` | JSON state/report |
| `cache/cron-ucb-safe.json` | JSON state/report |
| `cache/cross-calibration-alarm.json` | JSON state/report |
| `cache/current-token-count.json` | JSON state/report |
| `cache/cusum-gain-freeze.json` | JSON state/report |
| `cache/cusum-h-calibration.json` | JSON state/report |
| `cache/cusum-state.json` | JSON state/report |
| `cache/doob-quality-advisory.json` | JSON state/report |
| `cache/duality-alarm.json` | JSON state/report |
| `cache/effective-shadow-decisions.json` | JSON state/report |
| `cache/epistemic-regressions.jsonl` | append-only event log |
| `cache/eval-memory-planted-needle.json` | JSON state/report |
| `cache/evograph-insight-graph.json` | JSON state/report |
| `cache/freq-stability-alarm.json` | JSON state/report |
| `cache/gate-audit.json` | JSON state/report |
| `cache/governance-conflict-epistemic.json` | JSON state/report |
| `cache/governance-conflict-summary.json` | JSON state/report |
| `cache/governance-falsifiability-report.json` | JSON state/report |
| `cache/governance-rate-state.json` | JSON state/report |
| `cache/hindsight-episodes.jsonl` | append-only event log |
| `cache/image_token_costs.json` | JSON state/report |
| `cache/iss-justification.json` | JSON state/report |
| `cache/iss-small-gain.json` | JSON state/report |
| `cache/iss-threshold-justification.md` | markdown note |
| `cache/jev-call-budget.json` | JSON state/report |
| `cache/jev-scores-missing-alarm.json` | JSON state/report |
| `cache/jev-turn-scores.jsonl` | append-only event log |
| `cache/jev_eval_budget.json` | JSON state/report |
| `cache/kl-curvature-alarm.json` | JSON state/report |
| `cache/kl-curvature-report.json` | JSON state/report |
| `cache/last-session-type.json` | JSON state/report |
| `cache/left-core-hindsight.failed` | blob |
| `cache/lifecycle.db` | blob |
| `cache/loop-cusum-baseline.json` | JSON state/report |
| `cache/loop-cusum-changepoint.json` | JSON state/report |
| `cache/loop-lyapunov-stability.json` | JSON state/report |
| `cache/loop-model-comparison.json` | JSON state/report |
| `cache/loop-pid-state.json` | JSON state/report |
| `cache/loop-rollout-horizon.json` | JSON state/report |
| `cache/loop-stability-composite.json` | JSON state/report |
| `cache/ltl-promotion-invariant.json` | JSON state/report |
| `cache/mcp_schema_cache.json` | JSON state/report |
| `cache/memory-access-decay.json` | JSON state/report |
| `cache/memory-adaptive-rank.json` | JSON state/report |
| `cache/memory-auto-improvement.json` | JSON state/report |
| `cache/memory-bethe-free-energy.json` | JSON state/report |
| `cache/memory-bits-back.json` | JSON state/report |
| `cache/memory-conductance-ttl.json` | JSON state/report |
| `cache/memory-contamination-report.json` | JSON state/report |
| `cache/memory-displacement-convexity.json` | JSON state/report |
| `cache/memory-dkw-ue.json` | JSON state/report |
| `cache/memory-fano-bound.json` | JSON state/report |
| `cache/memory-gelman-shrink.json` | JSON state/report |
| `cache/memory-haar-mra.json` | JSON state/report |
| `cache/memory-heisenberg-tf.json` | JSON state/report |
| `cache/memory-hitting-time.json` | JSON state/report |
| `cache/memory-jl-distortion.json` | JSON state/report |
| `cache/memory-kraft-code.json` | JSON state/report |
| `cache/memory-log-ode-sig.json` | JSON state/report |
| `cache/memory-lp-dct-gate.json` | JSON state/report |
| `cache/memory-malliavin-ibp.json` | JSON state/report |
| `cache/memory-matrix-bernstein.json` | JSON state/report |
| `cache/memory-mixing-ttl.json` | JSON state/report |
| `cache/memory-optional-stopping.json` | JSON state/report |
| `cache/memory-ot-decay.json` | JSON state/report |
| `cache/memory-portmanteau.json` | JSON state/report |
| `cache/memory-reference-frequency.json` | JSON state/report |
| `cache/memory-renorm-counterterm.json` | JSON state/report |
| `cache/memory-sanov-ld.json` | JSON state/report |
| `cache/memory-sprt-decisions.jsonl` | append-only event log |
| `cache/memory-staleness.json` | JSON state/report |
| `cache/memory-ttl-floor.json` | JSON state/report |
| `cache/memory-wave18-invariants.json` | JSON state/report |
| `cache/mesa-detection-log.jsonl` | append-only event log |
| `cache/mid-compact-context.txt` | blob |
| `cache/model_catalog.json` | JSON state/report |
| `cache/monitor-suite-alarm.json` | JSON state/report |
| `cache/msprt-shadow-gate.json` | JSON state/report |
| `cache/nightly-gate-summary.json` | JSON state/report |
| `cache/nous_recommended_cache.json` | JSON state/report |
| `cache/nyquist-bandwidth.json` | JSON state/report |
| `cache/nyquist-timescale-bridge.json` | JSON state/report |
| `cache/oauth_heal_clean.json` | JSON state/report |
| `cache/ontology-topology-state.json` | JSON state/report |
| `cache/ontology-topology.json` | JSON state/report |
| `cache/openrouter_curated_catalog.json` | JSON state/report |
| `cache/openrouter_model_metadata.json` | JSON state/report |
| `cache/openshell-violations.log` | blob |
| `cache/pending-fanout-queue.json` | JSON state/report |
| `cache/pet-session-key` | blob |
| `cache/pid-circle-criterion.json` | JSON state/report |
| `cache/pid-passivity-index.json` | JSON state/report |
| `cache/plan-token-af493296.json` | JSON state/report |
| `cache/plan-token-bb80235c.json` | JSON state/report |
| `cache/plugin-catalog.json` | JSON state/report |
| `cache/plugin_toolset_keys.json` | JSON state/report |
| `cache/post-compact-context.txt` | blob |
| `cache/pre-compact-context.txt` | blob |
| `cache/progress-mirage-gate.jsonl` | append-only event log |
| `cache/promotion-at-most-once.json` | JSON state/report |
| `cache/promotion-ledger.json` | JSON state/report |
| `cache/qrels.jsonl` | append-only event log |
| `cache/rd-compaction-advisory.json` | JSON state/report |
| `cache/rd-lambda-floor.json` | JSON state/report |
| `cache/rd-lambda-target.json` | JSON state/report |
| `cache/reasoning-audit-log.jsonl` | append-only event log |
| `cache/reasoning_caps.json` | JSON state/report |
| `cache/relation-triples.json` | JSON state/report |
| `cache/research-pipeline-last-run.json` | JSON state/report |
| `cache/retrieval-saturation-alarm.json` | JSON state/report |
| `cache/retrieval-saturation.json` | JSON state/report |
| `cache/ripple-mem-graph.json` | JSON state/report |
| `cache/routing-alarm-bridge-alarm.json` | JSON state/report |
| `cache/routing-azuma-concentration-alarm.json` | JSON state/report |
| `cache/routing-azuma-concentration.json` | JSON state/report |
| `cache/routing-belief-propagation-alarm.json` | JSON state/report |
| `cache/routing-belief-propagation.json` | JSON state/report |
| `cache/routing-boolean-influence-alarm.json` | JSON state/report |
| `cache/routing-boolean-influence.json` | JSON state/report |
| `cache/routing-calibration.jsonl` | append-only event log |
| `cache/routing-competitive-ratio.jsonl` | append-only event log |
| `cache/routing-conflicts.jsonl` | append-only event log |
| `cache/routing-eligibility-alarm.json` | JSON state/report |
| `cache/routing-eligibility.json` | JSON state/report |
| `cache/routing-events.jsonl` | append-only event log |
| `cache/routing-exp3-shadow-alarm.json` | JSON state/report |
| `cache/routing-exp3-shadow.json` | JSON state/report |
| `cache/routing-exp3-skill-weights-alarm.json` | JSON state/report |
| `cache/routing-exp3-skill-weights.json` | JSON state/report |
| `cache/routing-exp3-state-alarm.json` | JSON state/report |
| `cache/routing-exp3-state.json` | JSON state/report |
| `cache/routing-exp4-state-alarm.json` | JSON state/report |
| `cache/routing-exp4-state.json` | JSON state/report |
| `cache/routing-fano-bound-alarm.json` | JSON state/report |
| `cache/routing-fano-bound.json` | JSON state/report |
| `cache/routing-graph-bandit-alarm.json` | JSON state/report |
| `cache/routing-graph-bandit.json` | JSON state/report |
| `cache/routing-graph-independence-alarm.json` | JSON state/report |
| `cache/routing-graph-independence.json` | JSON state/report |
| `cache/routing-hamming-alarm.json` | JSON state/report |
| `cache/routing-ips-offpolicy-alarm.json` | JSON state/report |
| `cache/routing-ips-offpolicy.json` | JSON state/report |
| `cache/routing-kl-ucb-alarm.json` | JSON state/report |
| `cache/routing-kl-ucb.json` | JSON state/report |
| `cache/routing-linucb-alarm.json` | JSON state/report |
| `cache/routing-linucb-state-alarm.json` | JSON state/report |
| `cache/routing-linucb-state.json` | JSON state/report |
| `cache/routing-linucb.json` | JSON state/report |
| `cache/routing-mcdiarmid-bm25-alarm.json` | JSON state/report |
| `cache/routing-mcdiarmid-bm25.json` | JSON state/report |
| `cache/routing-mobius-audit-alarm.json` | JSON state/report |
| `cache/routing-mobius-audit.json` | JSON state/report |
| `cache/routing-mutual-information-alarm.json` | JSON state/report |
| `cache/routing-mutual-information.json` | JSON state/report |
| `cache/routing-pac-bayes-alarm.json` | JSON state/report |
| `cache/routing-pac-bayes.json` | JSON state/report |
| `cache/routing-precision-recall-alarm.json` | JSON state/report |
| `cache/routing-precision-recall.json` | JSON state/report |
| `cache/routing-rademacher-bound-alarm.json` | JSON state/report |
| `cache/routing-rademacher-bound.json` | JSON state/report |
| `cache/routing-regret-log.jsonl` | append-only event log |
| `cache/routing-skill-markov-alarm.json` | JSON state/report |
| `cache/routing-skill-markov.json` | JSON state/report |
| `cache/routing-skill-percolation-alarm.json` | JSON state/report |
| `cache/routing-skill-percolation.json` | JSON state/report |
| `cache/routing-switching-detector-alarm.json` | JSON state/report |
| `cache/routing-switching-detector.json` | JSON state/report |
| `cache/routing-switching-state-alarm.json` | JSON state/report |
| `cache/routing-switching-state.json` | JSON state/report |
| `cache/routing-token-setcover-alarm.json` | JSON state/report |
| `cache/routing-token-setcover.json` | JSON state/report |
| `cache/routing-tsallis-inf-alarm.json` | JSON state/report |
| `cache/routing-tsallis-inf.json` | JSON state/report |
| `cache/routing-wald-sprt-alarm.json` | JSON state/report |
| `cache/routing-wald-sprt.json` | JSON state/report |
| `cache/routing-weights-alarm.json` | JSON state/report |
| `cache/routing-weights.json` | JSON state/report |
| `cache/schema_columns.json` | JSON state/report |
| `cache/session-gc-probe.json` | JSON state/report |
| `cache/session-type-tool-protocol.json` | JSON state/report |
| `cache/session.key` | blob |
| `cache/shadow-sprt-decisions.json` | JSON state/report |
| `cache/sheaf-gluing-report.json` | JSON state/report |
| `cache/skill-beta-state-seeded.json` | JSON state/report |
| `cache/skill-beta-state.json` | JSON state/report |
| `cache/skill-beta-state.prev.json` | JSON state/report |
| `cache/skill-composition-gf.json` | JSON state/report |
| `cache/skill-description-entropy.json` | JSON state/report |
| `cache/skill-integrity.json` | JSON state/report |
| `cache/skill-integrity.key` | blob |
| `cache/skill-merkle.json` | JSON state/report |
| `cache/skill-router-index.json` | JSON state/report |
| `cache/skill-routing-causal-audit.json` | JSON state/report |
| `cache/skill-wiki-export.md` | markdown note |
| `cache/soares-halt-liveness.json` | JSON state/report |
| `cache/spike-actuator-log.json` | JSON state/report |
| `cache/sprt-effective-decision.json` | JSON state/report |
| `cache/sprt-falsifiability-handshake.json` | JSON state/report |
| `cache/sprt-inner-outer-alignment.json` | JSON state/report |
| `cache/sprt-measurement-tamper.json` | JSON state/report |
| `cache/sprt-oc-calibration.json` | JSON state/report |
| `cache/sprt-truncation.json` | JSON state/report |
| `cache/stability-alarm.json` | JSON state/report |
| `cache/staleness-alarm.json` | JSON state/report |
| `cache/staleness-alarms.jsonl` | append-only event log |
| `cache/statecomp-router-state.json` | JSON state/report |
| `cache/taxonomy-candidates.json` | JSON state/report |
| `cache/term-typer-output.json` | JSON state/report |
| `cache/tmpuqshlo5m.py` | cached script/spike |
| `cache/tool-schema-cost-audit.json` | JSON state/report |
| `cache/tool_discovery_cache.json` | JSON state/report |
| `cache/ttl-gain-history.jsonl` | append-only event log |
| `cache/two-timescale.json` | JSON state/report |
| `cache/typesafe-jev-research.md` | markdown note |
| `cache/ue-blackbox-scores.jsonl` | append-only event log |
| `cache/ue-calibration-bridge-state.json` | JSON state/report |
| `cache/ue-length-stats.json` | JSON state/report |
| `cache/ue-memory-gate-log.jsonl` | append-only event log |
| `cache/ue-perplexity-proxy.jsonl` | append-only event log |
| `cache/ue-semantic-graph.jsonl` | append-only event log |
| `cache/wave21a-alarm-bridge.json` | JSON state/report |
| `cache/wave21a-compaction-aep-typical-set-alarm.json` | JSON state/report |
| `cache/wave21a-compaction-chain-rule-mi-alarm.json` | JSON state/report |
| `cache/wave21a-compaction-rd-converse-alarm.json` | JSON state/report |
| `cache/wave21a-context-channel-capacity-alarm.json` | JSON state/report |
| `cache/wave21a-kl-curvature-alarm-alarm.json` | JSON state/report |
| `cache/wave21a-memory-adaptive-rank-alarm.json` | JSON state/report |
| `cache/wave21a-memory-bethe-free-energy-alarm.json` | JSON state/report |
| `cache/wave21a-memory-bits-back-alarm.json` | JSON state/report |
| `cache/wave21a-memory-conductance-ttl-alarm.json` | JSON state/report |
| `cache/wave21a-memory-displacement-convexity-alarm.json` | JSON state/report |
| `cache/wave21a-memory-dkw-ue-alarm.json` | JSON state/report |

### INTER-SCRIPT DEPENDENCIES (this wave + notable edges)

- `lifecycle-schema-extension.py` creates tables consumed by `hallucination-detector.py`, `output-formalizer-verifier.py`, `step-level-trajectory-auditor.py`, `state-machine-synthesizer.py`.
- `feedback-robustness-scorer.py` reads `cache/routing-events.jsonl` (else lifecycle episodes, else synthetic) → `cache/skill-robustness-scores.json`.
- `routing-linucb.py` reads `skill-router-index.json`, `skill-beta-state.json`; writes `routing-linucb.json`, `routing-linucb-state.json`, HITL `linucb-routing-state.json`.
- `pending-improvements-review.py` reads `cache/research/cs-spike-queue.json`, `math-spike-queue.json`, `math-ideas-queue.json` → `cache/pending-improvements-report.json`.
- `obstruction-certificate-cache.py` scans skills + `fact_lifecycle` → `cache/obstruction-certificate-cache.json` (report-only).
- `state-machine-synthesizer.py` reads `cache/action-log.json` or lifecycle `action_log` → `cache/synthesized-fsm.json`.
- `dcr-compute-router.py` → `cache/dcr-routing.json`; `autonomy-router-mdp.py` → `cache/autonomy-routing-state.json`.
- `citation-confidence-router.py` → `cache/citation-routing.json`; `cost-aware-eval-framework.py` → `cache/cost-aware-eval.json`.
- `step-level-trajectory-auditor.py` → `cache/trajectory-audit.json` + `trajectory_audits` table.
- `process-reward-ranker.py` / `step-level-prm-scorer.py` → `cache/process-reward-rankings.json`, `cache/prm-step-scores.json`.
- `reasoning-trace-evaluator.py` → `cache/reasoning-trace-eval-log.json`.
- `pddl-state-abstractor.py` → `cache/pddl-state.json`.
- `process-verifier-agent.py` → `cache/process-verification-report.json`.
- `subgoal-verifier-rubric.py` → `cache/subgoal-verification.json`.
- `fact-attribution-verifier.py` → `cache/fact-attribution.json`.
- `perception-reasoning-splitter.py` → `cache/perception-reasoning-split.json`.
- `afanet-failure-attributor.py` → `cache/failure-attribution.json`.

Governance-required (change_type != script): none in the 16 CS spikes (all `change_type=script`). Ideas typed as skill were implemented as skills; discarded ideas were not implemented.

