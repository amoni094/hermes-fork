# Runtime Layer Audit — August 2026

**Scope:** 19 target skills across `autonomous-ai-agents/` and `software-development/`
covering agent loops, safety, planning, and orchestration.

**Target skills audited:** autonomous-agent-loop-design, agent-runtime-loop-patterns,
mnemosyne-atp-safety, trajectory-risk-guardrail, complexity-gated-planning,
hermes-role-pipelines, hermes-agent-sync, hermes-swarm-consensus, merge-reconciler,
preact-trajectory-compilation, ralph-loops, async-agent-nightshift-patterns,
harness-first-agent-design, hermes-cron-and-agents, verification-before-completion,
agent-task-signoff, dispatching-parallel-agents, subagent-driven-development,
subagent-output-contract.

---

## Summary: 2 CRITICAL · 15 HIGH · 13 MEDIUM · 5 LOW

---

## CRITICAL

### CRITICAL-B1 — Broken `related_skills` entry in autonomous-agent-loop-design
- **File:** `autonomous-ai-agents/autonomous-agent-loop-design/SKILL.md` line 18
- `related_skills` contains `- auto` — not a valid skill name (truncated stub,
  possibly "autonomous-ai-agents" or "auto-improve").
- Will cause lookup failure if any system resolves related_skills programmatically.
- **Action:** Run `hermes curator adopt autonomous-agent-loop-design` then fix line 18.

### CRITICAL-C1 — PlanBench fallback paths not synthesised in any target skill
- **Research:** arXiv:2606.22388 (PlanBench-XL — long-horizon tool-use failure enumeration)
- **Found:** Only in `research/arxiv-sweep-findings/references/sweep-12.md` line 162
- **Gap:** No target skill (especially `autonomous-agent-loop-design` or
  `agent-runtime-loop-patterns`) documents structured fallback path enumeration for
  long-horizon tasks. `autonomous-agent-loop-design` covers failure cascade at line 516
  ("≥N consecutive tool failures") but N is undefined and no structured fallback taxonomy exists.

---

## HIGH

### HIGH-A1 — Trigger overlap: autonomous-agent-loop-design vs async-agent-nightshift-patterns
- Both fire on "designing a cron job" / "unattended agent" / "background agent task"
- `autonomous-agent-loop-design` trigger line 7: "designing a cron job or background agent task"
- `async-agent-nightshift-patterns` trigger line 3: "unattended agent design", "nightshift agent"
- No disambiguation stated in either skill. The distinction is implicit:
  - auto-loop-design = loop architecture, eval design, long-run optimization patterns
  - async-nightshift = unattended safety: deny-by-default, sandbox, HITL timeout=deny
- **Fix:** Add disambiguation note + cross-reference in both skills.

### HIGH-A2 — Trigger overlap: autonomous-agent-loop-design vs agent-runtime-loop-patterns
- `agent-runtime-loop-patterns` triggers on "designing agent loop guardrails or failure
  recovery logic" and "agent self-correction, reflection, or repair patterns"
- `autonomous-agent-loop-design` covers the same concepts (Phantom Guardrail, AUQ/PreFlect)
- `autonomous-agent-loop-design` does NOT reference `agent-runtime-loop-patterns` anywhere
  in its body (grep confirmed — only in related_skills)
- The distinction (auto-loop-design = architecture; runtime-loop-patterns = per-turn/per-tool
  tuning) is implicit but unstated.
- **Fix:** auto-loop-design body should explicitly reference agent-runtime-loop-patterns
  for per-tool guardrail patterns.

### HIGH-B2 — Missing handoff: autonomous-agent-loop-design → trajectory-risk-guardrail
- auto-loop-design correctly hands off to mnemosyne at line 501 ("Trigger: any loop step
  that cannot be undone. See mnemosyne-atp-safety skill.")
- BUT it has no mention of trajectory-risk-guardrail as the REQUIRED pre-flight step
- TRG itself documents the correct order: TRG (pre-flight) → mnemosyne-atp-safety
  (per-action) at line 91-93. The upstream skill omits TRG entirely.

### HIGH-B3 — Missing handoff: dispatching-parallel-agents → hermes-agent-sync
- `dispatching-parallel-agents` warns about write-timing conflicts (line 93) and references
  `merge-reconciler` and `hermes-swarm-consensus` in related_skills
- But does NOT reference `hermes-agent-sync` in its body
- The canonical pattern for "parallel agents writing to shared files" is hermes-agent-sync
  (blackboard + structured findings)

### HIGH-B4 — Missing handoff: merge-reconciler → hermes-swarm-consensus
- `merge-reconciler` resolves GIT branch conflicts (code); `hermes-swarm-consensus` resolves
  VERDICT/finding conflicts (semantic)
- `hermes-swarm-consensus` at line 215 says "Already covered in merge-reconciler. Summary
  for swarm context..." — it is aware of merge-reconciler
- But `merge-reconciler` has NO reference to `hermes-swarm-consensus` in related_skills
  (only lists "hermes-agent" at line 11)
- A user with verdict conflicts who loads merge-reconciler gets git-conflict resolution,
  not the right tool.
- **Fix:** merge-reconciler should reference hermes-swarm-consensus and add routing note:
  "For semantic verdict conflicts (not code), use hermes-swarm-consensus instead."

### HIGH-B5 — Missing handoff: ralph-loops → mnemosyne-atp-safety (one-directional)
- `ralph-loops` line 150: "NEVER run Ralph loops with irreversible side effects outside repo"
- Prohibits them but does NOT hand off to mnemosyne for cases where irreversible steps ARE
  justified and need ATP wrapping
- `mnemosyne-atp-safety` line 487 references ralph-loops; handoff is one-directional only.

### HIGH-C2 — SQA semantic quorum confined to mnemosyne-atp-safety only
- Research: arXiv:2606.08021
- Found: `mnemosyne-atp-safety/SKILL.md` line 659
- Gap: SQA's lightweight two-framing approval ("what could go wrong?" + "is this within
  scope?") is actionable in `verification-before-completion` and `hermes-swarm-consensus`.
  Neither synthesises it.

### HIGH-C3 — Vera-Bench gates missing from trajectory-risk-guardrail
- Research: arXiv:2607.01793; found: `mnemosyne-atp-safety/SKILL.md` lines 646-656
- TRG is the pre-flight safety skill but its 5-step process (lines 53-87) omits
  Vera-Bench's lateral-movement check ("does the planned action access resources outside
  the declared scope?")

### HIGH-C4 — RADEG not synthesised as actionable runtime pattern
- Research: arXiv:2608.09168 (retroactive policy generation / pre-execution utility gating)
- Found: mnemosyne line 549 (brief audit trail mention only), hermes-agent-skill-authoring
  line 271 (fuller, but in skill-authoring context)
- RADEG pattern (log query-skill-outcome triples → build logistic classifier → gate
  low-utility skill loads) is a runtime loop optimization
- Should appear in `agent-runtime-loop-patterns` as a self-optimization/waste-reduction
  pattern. Not present there.

### HIGH-D1 — api_max_retries contradiction: 1 vs 3
- `agent-runtime-loop-patterns/SKILL.md` line 62: `api_max_retries=1` (operative)
- `hermes-context-budgeting/references/compression-config-reference-2026-08.md` line 116:
  `api_max_retries: 1 # Fail fast to fallback_providers. Default 3 is too slow.`
- `claude-routing-hierarchy/references/multi-agent-config-tuning.md` line 28:
  `api_max_retries: 1 → 3: Single retry insufficient for 429/5xx in long chains.`
- **Contradiction:** agent-runtime-loop-patterns + hermes-context-budgeting say "use 1
  (fail fast)"; claude-routing-hierarchy ref says "use 3 (prevents cascade failure in
  multi-agent long chains)".
- No target SKILL.md reconciles this. Both recommendations are context-dependent but
  the context is never stated.
- **Fix:** agent-runtime-loop-patterns should acknowledge the 1 vs 3 tradeoff:
  1 = fast fallback (single provider, speed-sensitive); 3 = resilience (multi-agent long chains).

### HIGH-E1 — SquadCue timeout=deny duplicated: mnemosyne + async-nightshift
- `mnemosyne-atp-safety/SKILL.md` lines 533-547: full SquadCue implementation
- `async-agent-nightshift-patterns/SKILL.md` lines 104-120: parallel implementation
- Same code, no cross-reference from nightshift to mnemosyne.
- **Candidate:** async-nightshift should delegate to mnemosyne for implementation, keep only concept.

### HIGH-E2 — ColluSkill duplicated: async-nightshift + hermes-swarm-consensus
- `async-agent-nightshift-patterns/SKILL.md` lines 198-208
- `hermes-swarm-consensus/SKILL.md` lines 157-168
- Same paper (arXiv:2608.09732), similar actionable patterns, no cross-reference.
- **Candidate:** consolidate into hermes-swarm-consensus (authoritative for swarm security);
  async-nightshift references it for the unattended case.

### HIGH-F1 — autonomous-agent-loop-design related_skills broken "auto" stub
- `autonomous-ai-agents/autonomous-agent-loop-design/SKILL.md` line 18: `- auto`
- Not a resolvable skill name. (Same as CRITICAL-B1 from handoff perspective.)

---

## MEDIUM

### MEDIUM-A3 — Trigger overlap: autonomous-agent-loop-design vs ralph-loops
- auto-loop-design body references ralph-loops at line 144 — handoff IS present
- But "run until CI is green" could route to either; ralph-loops should add a
  "when NOT to load this" note directing users to auto-loop-design for long-horizon strategy

### MEDIUM-A4 — Trigger overlap: dispatching-parallel-agents vs hermes-role-pipelines vs hermes-agent-sync
- All three fire on fan-out scenarios. No body-level reference to hermes-agent-sync
  from dispatching-parallel-agents for the "shared file results" case.

### MEDIUM-B6 — Missing handoff: hermes-cron-and-agents → async-agent-nightshift-patterns
- `hermes-cron-and-agents/SKILL.md` (94 lines) has NO mention of: timeout=deny, disposable
  sandboxes, scoped agent identity, or SquadCue-style unattended safety.
- async-nightshift lists hermes-cron as a related skill but not vice versa.

### MEDIUM-B7 — Missing handoff: hermes-cron-and-agents → preact-trajectory-compilation
- hermes-cron-and-agents covers scheduling repeated tasks but doesn't reference
  preact-trajectory-compilation (8.5-13x speedup for repeated deterministic cron tasks)
- preact correctly references hermes-cron; handoff is one-directional only.

### MEDIUM-C5 — 4-layer vulnerability taxonomy missing from trajectory-risk-guardrail
- Research: arXiv:2608.10530; found: mnemosyne (line 569), async-nightshift (line 235)
- TRG's immediate-hazard scan (lines 57-62) classifies SAFE/CAUTION/HAZARD by reversibility
  only — doesn't use the 4-layer taxonomy (perception → reasoning → action → reflection)
  to categorize hazard TYPE.

### MEDIUM-C6 — SquadCue timeout=deny missing from hermes-cron-and-agents
- hermes-cron-and-agents is the primary scheduling skill but has no reference to
  SquadCue's timeout=deny / "never proceed on silence" HITL rule.

### MEDIUM-D2 — Retry count ambiguity: "≥N" in autonomous-agent-loop-design
- `autonomous-agent-loop-design` line 516: "≥N consecutive tool failures on different
  approaches → escalate" (N is unspecified)
- `subagent-output-contract` line 123: "retry once → ESCALATE"
- `agent-runtime-loop-patterns` line 62: `api_max_retries=1`
- `requesting-code-review` line 478: "retry once ... then treat as FAIL"
- "retry once" is consistent across three skills; N undefined in auto-loop-design is ambiguous.
- **Fix:** auto-loop-design should define N=2 to match the "retry once" pattern in peers.

### MEDIUM-E3 — DreamGuard triple description
- Described in trajectory-risk-guardrail (primary), mnemosyne-atp-safety (line 625-641),
  AND agent-runtime-loop-patterns
- Core "prefix-risk score" concept explained redundantly across three skills.
- **Candidate:** TRG as single authoritative source; others reference it.

### MEDIUM-E4 — 4-layer vuln taxonomy: mnemosyne (full) vs async-nightshift (one-liner)
- mnemosyne lines 569-589; async-nightshift line 235 (brief)
- Cross-reference would suffice; full detail in mnemosyne, pointer in nightshift.

### MEDIUM-F2 — hermes-cron-and-agents underspecified (94 lines, no SSL metadata)
- No ssl_scheduling, ssl_structural, ssl_logical sections
- Missing: safety patterns, preact handoff, async-nightshift reference
- Given how many other skills depend on this as the scheduling entry point, it is thin.

### MEDIUM-F3 — merge-reconciler related_skills too narrow
- `autonomous-ai-agents/merge-reconciler/SKILL.md` lines 10-11: only lists "hermes-agent"
- Missing: hermes-swarm-consensus (verdict conflicts), hermes-agent-sync (file-based resolution)

---

## LOW

### LOW-B8 — complexity-gated-planning → trajectory-risk-guardrail (missing)
- Level 3 plans with irreversible actions have no TRG gate in the Pre-Execution Meta-Workflow
  (lines 73-99).

### LOW-E5 — Episode model vs ralph-loops fresh-context: related failure modes
- mnemosyne episode model (lines 402-490): in-process generation counter for stale state
- ralph-loops: fresh context spawn to avoid stale state
- Same root failure mode, different mechanisms, no cross-reference.

### LOW-F4 — preact-trajectory-compilation doesn't mention mnemosyne-atp-safety
- Compiled replays can include irreversible tool calls; no mention of ATP wrapping for these.

### LOW-F5 — complexity-gated-planning: no safety skills in related_skills
- related_skills line 19: [workflow-map, plan, systematic-debugging, test-driven-development,
  isolated-workspace-preflight, subagent-driven-development]
- Missing: trajectory-risk-guardrail, mnemosyne-atp-safety, verification-before-completion.
- Level 3 plans have no safety chain.

---

## Research Coverage Summary

| Term | Status | Location |
|------|--------|----------|
| DreamGuard prefix-risk | ✓ synthesised | trajectory-risk-guardrail L34, mnemosyne L625 |
| SquadCue timeout-deny | ⚠ confined | mnemosyne L533, async-nightshift L29 — NOT in hermes-cron |
| SQA semantic quorum | ⚠ confined | mnemosyne L659 only |
| Vera-Bench gates | ⚠ confined | mnemosyne L646-656 only — missing from TRG |
| CDH detection | ⚠ confined | TRG L188, hermes-swarm-consensus — NOT in async-nightshift |
| ATP provenance edges | ✓ synthesised | mnemosyne L81, L128, L258 |
| Verbalized Sampling | ✓ synthesised | hermes-swarm-consensus L183-212 |
| First-mover bias | ✓ synthesised | hermes-swarm-consensus L109 |
| DEAR echo-chamber | ✓ synthesised | hermes-swarm-consensus L123-127 |
| ColluSkill | ✓ synthesised | hermes-swarm-consensus L157, async-nightshift L198 (duplicated) |
| PreFlect | ✓ synthesised | agent-runtime-loop-patterns L200-215 |
| ODR/REGREACT | ✓ synthesised | agent-runtime-loop-patterns L211-215 |
| Cruxible state-engine | ⚠ confined | mnemosyne L680 only — should cross-ref TRG |
| RADEG policy gen | ✗ missing | mnemosyne L549 (brief); not actionable in any runtime skill |
| PlanBench fallback paths | ✗ missing | Research ref only — not in any target skill |
| 4-layer vuln taxonomy | ⚠ confined | mnemosyne L569, async-nightshift L235 — missing from TRG |

---

## Audit Methodology (for reproducibility)

### Grep patterns used for research term coverage check:
```bash
# Per-term, across all .md files in skills/:
grep -rl 'DreamGuard' ~/.hermes/skills/ --include='*.md'
grep -rl 'SquadCue' ~/.hermes/skills/ --include='*.md'
grep -rl 'quorum' ~/.hermes/skills/ --include='*.md'           # SQA
grep -rl 'Vera.Bench\|2607.01793' ~/.hermes/skills/ --include='*.md'
grep -rl 'CDH\|Convergent.Detour' ~/.hermes/skills/ --include='*.md'
grep -rl 'provenance.edge\|2608.10502' ~/.hermes/skills/ --include='*.md'
grep -rl 'Verbalized.Sampl' ~/.hermes/skills/ --include='*.md'
grep -rl 'first.mover\|2608.02827' ~/.hermes/skills/ --include='*.md'
grep -rl 'DEAR\|echo.chamber\|2608.03648' ~/.hermes/skills/ --include='*.md'
grep -rl 'ColluSkill\|ChainGuard\|2608.09732' ~/.hermes/skills/ --include='*.md'
grep -rl 'PreFlect\|2602.07187' ~/.hermes/skills/ --include='*.md'
grep -rl 'REGREACT\|2604.12054' ~/.hermes/skills/ --include='*.md'
grep -rl 'Cruxible' ~/.hermes/skills/ --include='*.md'
grep -rl 'RADEG\|2608.09168' ~/.hermes/skills/ --include='*.md'
grep -rl 'PlanBench\|2606.22388' ~/.hermes/skills/ --include='*.md'
grep -rl '4.layer.vuln\|2608.10530' ~/.hermes/skills/ --include='*.md'
```

### Retry count contradiction check:
```bash
grep -rn 'api_max_retries' ~/.hermes/skills/ --include='*.md'
grep -rn 'retry.once\|retry once\|retry.twice' ~/.hermes/skills/\
  autonomous-ai-agents software-development --include='SKILL.md'
```

### Cross-reference verification (handoff check):
```bash
# Does skill A reference skill B?
grep -n 'skill-B-name\|skill_B_name' ~/.hermes/skills/.../skill-A/SKILL.md
```

### Protected skills identified (user-owned, not patchable by autonomous agent):
All 19 target skills are user-owned. Any fixes require `hermes curator adopt <name>` first.
