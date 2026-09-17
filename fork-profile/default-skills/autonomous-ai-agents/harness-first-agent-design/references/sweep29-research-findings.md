# Sweep 29 Research Findings — harness-first-agent-design

Extracted from SKILL.md 2026-09-09. See also references/sweep32-33-research-findings.md.

## Sweep 29 Additions (Aug 2026)

### JIT-Agent: Harness as Composable Machine-Generatable Artifact (arXiv:2608.25593) ★ HIGH

JIT-Agent trains a harness-intelligence model that synthesizes task-adaptive harnesses
on-the-fly for any off-the-shelf LLM. Core finding: **the harness (memory management,
planning strategy, action protocol, tool/skill orchestration) can dominate the contribution
of the underlying foundation model.** DeepSeek-V4-Flash + JIT harness surpasses GPT-5.6 on
DeepSearchQA (+9.1) and OdysseyBench (+4.3).

Four-module harness protocol (formalized by JIT-Agent — use as canonical harness checklist).
A design that names the model but leaves any module implicit is incomplete.

| Module | Decide | Hermes mapping |
|---|---|---|
| **memory_management** | What stays in context vs offloaded; compaction policy; ring buffers | `hermes-context-hygiene`; SKILL.state ring buffer (`memory.skill_state.activate_threshold_steps: 10`) |
| **planning_strategy** | ReAct / OODA / BATON; step-size; verifier placement | ReAct default; `ralph-loops` / BATON when horizon > 1 window; verifier before durable commit |
| **action_protocol** | Tool permission scope; auth tier; action-induction guard | Min `enabled_toolsets`; `tool-auth-gate.py`; `mnemosyne-atp-safety` for irreversible steps |
| **tool/skill_orchestration** | Which skills are hot-loaded; routing index; wiki co-evolution | Map-guided toolsets (`autonomous-ai-agents`); `hermes-semantic-skill-routing`; `skill-wiki.py` |

JIT-Agent also self-evolves by distilling performance signals from an expanding archive of
prior harness configurations. Hermes analogue: `skill-wiki.py` + `skillopt_score.py` cron
+ `gepa_skill_eval.py` form the evolutionary harness archive.

### Dot Reflex: 10-decision outer controller (github:usedotai/dot-reflex) ★ HIGH <!-- why: implicit continue hides recovery choices; name the exit -->

Keep an **outer controller** separate from the worker. The controller reads a compact trajectory
JSON (not the full transcript) and returns **exactly one** of:
`continue / verify / retry / replan / rollback / branch / switch-model / ask-human / stop-ok / stop-fail`.
No implicit continuation. Use a cheap model for the controller. On `stop-fail`, write a DART-SD
CTB annotation before exiting. Full write-up: `autonomous-agent-loop-design`.

### DART-SD breakpoint (arXiv:2608.18524) ★ HIGH <!-- why: replaying full failed trajectories propagates the error; resume from the breakpoint -->

Never SFT/replay a full failed trajectory. Localize the Critical Topological Breakpoint (CTB =
last successful step), distill **recovery steps only**, resume from the CTB on the next run.

```json
{"ctb_step": 12, "last_good_artifact": "path", "failure": "what diverged", "recovery": "next action"}
```

See `autonomous-agent-loop-design` and `stalled-session-recovery`.

### EvoX persistent-project (arXiv:2608.10450) ★ HIGH <!-- why: long-lived agent memory is the wrong substrate; the worktree is -->

Make the **project** persistent; keep **agents** finite-lived. Each local world = accepted version
+ repo path. Agents propose; only accepted changes advance history; replacement is trivially safe.
Hermes: `ralph-loops` + `using-git-worktrees`. Use for 20+ sequential LLM interactions. Full table:
`autonomous-agent-loop-design`.

### Agent Mesh Reliability Primitives (arXiv:2608.26225) ★ HIGH

Production failure study: 147 incidents, 81 runs with measured cost. All three assumptions
that service-mesh circuit-breakers rest on are **violated in agentic systems**:

1. **Error-rate breaker assumption violated**: a loop of 54 consecutive successful tool calls
   produced zero observable errors — but made no useful progress. Error rate = 0; breaker
   never fires; run burns budget to completion. **Fix:** add progress-rate breaker alongside
   error-rate breaker (detect no_progress, not just errors).

2. **Progress signal stability violated**: a progress signal constant by construction guarantees
   a false trip on the third repair round — driving a 6/6 component run to 3/6. **Fix:** validate
   that progress metrics are genuinely dynamic before using them as loop exit conditions.

3. **Idempotency assumption violated**: 21 events accumulated across 6 invocations of one
   delegation made a correct, idempotent component unwinnable. **Fix:** track
   delegation-level event accumulation, not just per-call success.

Hermes tool_loop_guardrails already covers exact_failure + same_tool_failure. Add:
- `no_effective_progress` guardrail: detect when output state hasn't changed across N calls
- `delegation_event_budget`: cap total events (not just retries) across re-invocations

### SKILL.state: Mutable Execution State Replaces Append-Only History (arXiv:2608.26263) ★ HIGH

Append-only conversation history causes latency degradation and context-poisoning over long
horizons. SKILL.state fixes this: at each step, the model receives only (1) immutable skill
spec, (2) current structured state, (3) latest observation. Intermediate reasoning is
discarded after commit. Result: task accuracy improves while cumulative token cost drops.

**Implemented:** `~/.hermes/scripts/skill-state.py` — manages mutable execution state with
ring-buffered observations (default 3), step-level commit, reasoning trace discard, spec-drift
detection, and token savings estimation. Use for autonomous loops > 10 steps.

**Config:** `memory.skill_state.activate_threshold_steps: 10`

### CaSKG: Counterfactual-Causal Skill Graphs (arXiv:2608.25500) ★ HIGH

Reusable skill libraries turn memory access into a retrieval problem. CaSKG builds a
calibrated skill graph using counterfactual probes (remove/substitute/reorder skill pairs)
with Bayesian smoothing, then uses state-filtered graph expansion for retrieval.

Results vs Graph-of-Skills: ScienceWorld 72.62 → 80.50, ALFWorld 80.01% → 86.79% across 6 LLMs.
Edge-confidence calibration is the key — skill dependencies are **directional and
probabilistic**, not flat keyword matches.

Hermes application: `skill-graph-walk.py` currently does semantic similarity. Add edge-direction
calibration (precondition → postcondition relationships between skills) as a next improvement.

### Tool-Output-as-Command Guard (arXiv:2608.27146) ★ HIGH

Tool outputs can become implicit commands that drive side effects beyond user intent. An
external tool output containing directive language can cause the model to execute actions
the user never requested — this is distinct from prompt injection (which targets the system
prompt) because it exploits the action-induction gap in tool result handling.

**Implemented:** `~/.hermes/scripts/tool-auth-gate.py` — classifies tool outputs as
DATA vs ACTION_INDUCING, checks proposed actions against trust-tier policy (SYSTEM/VERIFIED/
DELEGATED/EXTERNAL), and logs supply-chain provenance (tool→output→action).

**Config:** `memory.tool_auth.enabled: true`

### Five Governance Primitives (arXiv:2608.26696) ★ HIGH

Deployment tiers: singular (one org governs all agents), federated (shared rules), open
(unknown counterparties). As org perimeter is crossed, no single actor can govern end-to-end.
Five required primitives for any cross-boundary deployment:
1. **Discovery**: agents must be findable and enumerate their capabilities
2. **Identity**: declared name + capability claims before each interaction
3. **Governance**: per-tier authorization policy (maps to tool_auth trust tiers above)
4. **Attestation**: hash log of output + decision for auditability
5. **Supply chain**: track tool→output→action provenance chain

Hermes: tool_auth.governance_primitives config implements identity + attestation + supply_chain.

### Calibration Gate: Don't Commit Under Authoritative-Looking Uncertainty (arXiv:2608.27167) ★ MED

Across 12 frontier models, commitment to directional calls rises from 6.5% (bare question) to
54.0% (professional-looking market panel) — **even when all numbers are fabricated**. The agent
is not more informed, just presented with authority-framed packaging.

For Hermes: when context contains professional dashboards, statistics panels, or structured data
displays, the calibration_gate config warns against high-certainty commitment. The agent should
explicitly verify data provenance before committing to an irreversible action driven by displayed figures.

**Config:** `memory.calibration_gate.warn_on_authoritative_display: true`

### WikiSkill: Co-Evolving Skill + Wiki Knowledge Base (arXiv:2608.27454) ★ MED

Each skill co-evolves with a structured wiki that captures WHY it works, known failure modes,
and verified successor patterns. This separates raw execution from optimization insight —
preventing improvement notes from scattering across cron logs.

**Implemented:** `~/.hermes/scripts/skill-wiki.py` — manages wiki entries per skill with
sections: description_why, failure_modes, successor_patterns, precondition_notes,
calibration_notes, evidence_refs. Weekly export to markdown for review.

**Config:** `memory.skill_wiki.enabled: true`

### MemToC: Tools Override Parametric Memory Even When Wrong (arXiv:2608.26295) ★ MED

Across 5 open-weight models, tool returns strongly dominate closed-book answers. Models retain
a verified-correct answer against an incorrect tool in only 6.5-17.1% of cases; they follow
a correct tool in 86-93% of cases. Models can be confidently wrong when the tool is wrong.

**Implication:** Do not treat tool outputs as ground truth without verification. High-stakes
decisions driven by tool returns should be cross-checked against parametric knowledge,
especially when tool provenance is uncertain (EXTERNAL tier).

### BCIT: Bind Experience to Source Context Before Reuse (arXiv:2608.26730) ★ MED

Boundary-Calibrated Intervention Transfer: past success as "context-free permission" is wrong.
An update's effect depends on its parent model, data, and training stage. BCIT binds an
observed effect to its source context, checks applicability conditions, and vetoes candidates
with named hard conflicts.

**Hermes application:** When l1-promote.py promotes a memory or skill-wiki adds a
successor pattern, record the context conditions under which it was observed (model version,
task type, tool set). Don't reuse without checking applicability.

### Agent Mesh: One Model Many Minds via MoRe (arXiv:2608.27338) ★ LOW

Mixture of Roles (MoRe) adaptively composes multiple specializations into a single steering
vector for single-turn inference, avoiding multi-turn context inflation from true multi-agent
systems. Useful when multi-agent overhead is unacceptable but diverse perspectives are needed.

