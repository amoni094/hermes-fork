# Community Sweep — Aug 12 2026 (Multilingual Sources)
## Non-English and Community Sources: Agent Memory, Skill Routing, Context Patterns

---

## Zero-Mem — Trace-Preserving Memory Without LLM Rewriting
**Source:** arXiv 2607.29377 | **Date:** 2026-07-31 | **HN discussion:** 2026-08-05
**Applicability:** HIGH

**Core finding:** Eliminates LLM calls from all memory operations except the final-QA step.
Preserves raw interaction traces and organizes them via:
- Entity-context graph (cross-session connections and entity relations)
- Temporal hierarchy (conversational locality and session state)

Retrieval: deterministic scoring from both views; LLM called only for the final answer.

**Results:**
- 57.6% reduction in memory-operation time vs fastest compared baseline
- Competitive accuracy on long-memory and long-context QA benchmarks
- Preserves original traces → no provenance loss (generative rewriting mutates the record)

**HN comment (key insight):** "Preserving original traces avoids a subtle auditability problem —
generative rewriting mutates the record and breaks provenance."

**Code:** https://github.com/TheMoon0815/Zero-mem (post peer review)

**Hermes implementation signal:**
- Hermes already has a raw trace store (session DB) — this is half the Zero-Mem architecture
- The novel piece: skip LLM rewriting during consolidation; query raw traces with deterministic scoring
- The entity-context graph maps to Graphiti MCP — but Graphiti still uses LLM for entity extraction
- Zero-Mem's deterministic calibration step (discard conflicting evidence before final-QA reader)
  is a complement to the dual-gate dedup pattern already in agent-memory-consolidation
- Actionable: in agent-memory-consolidation, before the LLM synthesis step, add a
  deterministic pre-pass that discards trace fragments where the same entity has conflicting
  values — surface the conflict rather than letting LLM synthesis paper over it

---

## LLM Wiki + Source Drift Detection (Taktile Engineering)
**Source:** engineering.taktile.com | **Date:** 2026-07-13
**Applicability:** MED

**Core finding:** The "LLM Wiki" pattern (Karpathy) — compile knowledge once, reuse instead of
re-deriving — breaks when source documents change silently. Production solution:
1. Weekly lint job: scan wiki for contradictions and stale claims
2. Source re-validation at query time: re-fetch source for every wiki fact before use

**The unsolved problem they name:** "shared wiki with silently-drifting sources" —
no research has solved it when sources are edited by people who don't know the wiki depends on them.

**SkillDrift concept (derived from this finding):**
Procedural skills go stale when their external dependencies change. This is different from
MemOPD decontextualization (memory losing context — previous sweep) or MemoryOS drift
(memory facts becoming stale). SkillDrift is specifically about *procedural instructions*
that assume a state of the world that no longer holds.

Examples:
- A skill that says "use tool X flag --foo" when --foo was removed in a library update
- A skill that says "model claude-opus-3" when that model is sunset
- A skill that describes an API endpoint that changed

**Hermes mitigation:**
- Add a `source_dependencies` field to skill frontmatter: `["claude-sonnet-4-x API", "hermes>=2.1"]`
- Weekly cron: check if named dependencies have new versions; flag skills for re-validation
- At minimum: skills referencing specific model names or API versions should be reviewed
  when those versions change. The skillspector-guard cron is the right home for this.

---

## Juejin CN: MCP/Skills/Computer-Use Routing Taxonomy
**Source:** 稀土掘金 (Juejin), beiju | **Date:** 2026-08-11
**Applicability:** HIGH

The Chinese dev community has converged on a clean 4-layer taxonomy:

| Layer | Solves | Maps to |
|---|---|---|
| Skills | How to complete the task | Hermes skills |
| MCP | Structured tool connection + discovery | Hermes tool calls / MCP |
| Computer Use | GUI fallback for no-API targets | computer_use tool |
| Agent Runtime | Orchestration, state, routing | Hermes session loop |

**Routing function (Chinese community consensus):**
```typescript
type Route = 'mcp' | 'computer-use' | 'human'
function chooseRoute(step: Step): Route {
  if (toolRegistry.has(step.capability)) return 'mcp'
  if (step.risk === 'high') return 'human'
  if (uiAdapter.supports(step.target)) return 'computer-use'
  return 'human'
}
```

**Critical observation:** "The most important layer is not the Planner but the Verifier."

**MCP does NOT automatically provide:**
- Cross-step state management
- Idempotency
- Retry / compensation
- Auth approval
- Result verification
- Long-task recovery

These must be in the skill or the Runtime (Hermes session loop).

**Hermes implementation signal:**
- Validates existing layering (skill → MCP → computer_use fallback)
- GAP: Explicit post-tool-call Verifier layer (deterministic postcondition check before next step)
- GAP: Idempotency key guidance for MCP write operations (add to hermes-agent skill)
- The task loop pattern: Skill → MCP/API → Computer Use (fallback) → Verifier → Recovery → Human Confirm → Deliver
- Verifier should be deterministic (not LLM) — check observable state vs expected postcondition

---

## Zenn JP: Two-Stage Gate for Blast-Direction-Partitioned Actions
**Source:** Zenn.dev, jun_uen0 | **Date:** 2026-08-12
**Applicability:** HIGH

**Core finding:** When an agent performs actions with different "blast directions," routing them
through the same approval gate causes cross-contamination of risk tolerance.

Demonstrated with SNS automation: posting (self-facing) vs liking/replying (other-facing).
Mixing them through one gate makes either: the strict gate too loose, or the loose gate too strict.

**Key principle:** "Separate not by feature, but by risk boundary."

Three blast directions requiring separate gates:
- `SELF_BLAST`: file writes, local config, local process — can be undone
- `THIRD_PARTY_BLAST`: external API calls, emails, social reactions — reaches external parties
- `SYSTEMIC_BLAST`: schema changes, auth changes, shared resource mutations — team-wide blast radius

**Hermes implementation signal:**
- trajectory-risk-guardrail covers HAZARD tagging but doesn't distinguish blast direction
- A "yes" to a SELF_BLAST action does NOT authorize a THIRD_PARTY_BLAST action in the same task
- Add blast direction as a dimension to the SAFE/CAUTION/HAZARD taxonomy
- Separate confirmation messages per blast direction in agent approval prompts

---

## Zenn JP: Hermes Deployment 3-Point Framework (Japanese Practitioners)
**Source:** Zenn.dev, shotawatanabe | **Date:** 2026-08-12
**Applicability:** MED (meta/community signal)

The article documents practical deployment of Hermes in Japanese dev orgs. Three identified
critical success factors:

1. **Appropriate data access** — agent needs DB, logs, infra, not just source code
2. **Mechanism-enforced data boundaries** — PII/secret access blocked by MCP scopes / tool
   definitions, NOT by instructions/prompts alone. "Mechanism-not-prompt" security.
3. **Team-shared skill improvement loops** — skills version-controlled in shared git, improved
   collaboratively via PR, not siloed per developer

**Key quote:** "技術そのものの目新しさよりも、この地味な設計判断を積み重ねられるかどうかの方が、
導入の成否を分けている" — "Success depends less on technological novelty and more on whether
you can accumulate these unglamorous design decisions."

**Hermes implementation signals:**
- Mechanism-not-prompt: use MCP server scopes or tool-definition allow/deny lists to hard-limit
  what data reaches the agent. Don't rely on "don't access X" instructions.
- Team skill sync: version-control ~/.hermes/skills/ in a shared git repo with PR-based review.
  This is the "shared wiki" pattern applied to procedural knowledge.

---

## Agent Skills Open Standard — agentskills.io
**Source:** agentskills.io + anthropics/skills (168k stars GitHub trending) | **Date:** Aug 2026
**Applicability:** MED

Anthropic released agentskills.io as an open standard for SKILL.md-based skills.
Key spec additions beyond what Hermes already uses:

- **Progressive disclosure** (3 stages): discovery (name+description only) → activation (full SKILL.md)
  → execution (referenced scripts/files loaded on demand). Hermes already implements this.
- **`acceptance_rules` field**: explicit YAML list of criteria the task output must meet to count as done.
  Hermes skills don't currently have this as a structured frontmatter field.
- **`prohibited_actions` field**: explicit YAML list of actions the skill must never take.
  Distinct from pitfalls — this is machine-readable, not prose.

Cross-ecosystem skill portability: the spec is designed for inter-agent sharing across
Claude Code, Cursor, Copilot, and other SKILL.md-aware runtimes.

---

## Cruxible — Agent Knowledge as Governed Artifacts
**Source:** GitHub cruxible-ai/cruxible | **Date:** Latest commit 2026-08-06
**Applicability:** MED

**Core concept:** Agent-produced intermediate conclusions (judgments, observations, decisions)
should be typed, reviewed, versioned artifacts with outcome contracts — not prose memory.

A "Crux" has: typed claims, review lifecycle (proposed → trusted), outcome contracts, provenance
receipts, version history.

"Code is typed, reviewed, versioned — agent judgments should be too."

**Hermes implementation signal:**
After a research or analysis task, emit a "Crux":
```json
{
  "claim": "This codebase uses event-driven architecture",
  "source_refs": ["session_id:abc", "file:src/events.py"],
  "confidence": 0.85,
  "contradicts": [],
  "expires": "2026-11-12",
  "status": "proposed"
}
```
Store as a Graphiti node with status:proposed. Promote to status:trusted after verification.
Complementary to ENTLORE KG (previous sweep) — adds lifecycle governance to extracted relations.

---

## Alyph — Branch-and-Prune Context Surgery
**Source:** HN Show HN: Alyph | **Date:** 2026-08-07
**Applicability:** MED

**Core concept:** "AI doesn't remember your chat, it rereads it." Failed attempt paths (14 messages
of debugging) pollute every subsequent message because the model rereads the whole context.

Solution: selective surgical pruning — identify "attempt → failure → correction" triplets and
collapse them to just the correction. Called "context surgery" — different from uniform compression.

**Key distinction from hermes-context-hygiene:**
- hermes-context-hygiene compresses uniformly (summarize everything old)
- Alyph branch-prune keeps only terminal success states, drops intermediate failure branches
- Result: the failed install attempts don't ride along rent-free to contaminate "how should I structure the main screen?"

**Hermes implementation signal:**
New skill pattern: "context-branch-prune" — before a major new phase, scan for
"attempt → error → fix" sequences and collapse each to just the fix line.
Heuristic trigger: message sequence where error keywords appear between two messages
from the same role discussing the same topic.

---

## Setoku — Correction-to-Rule Tacit Knowledge Accumulation
**Source:** HN Show HN: Setoku | **Date:** 2026-07-23
**Applicability:** MED

**Core concept:** When an agent produces a wrong answer that the user corrects, capture not just
the correction but the meta-rule that prevents the entire error class.

Example: User corrects "total revenue is $192M" → The meta-rule is "never sum revenue without
excluding Fanatics channel, which is not in this data." The correction-to-rule loop stores this
meta-rule for all future revenue queries.

"It gets better the more you use it" — the tacit knowledge layer grows through correction events.

**Hermes implementation signal:**
- After user correction: prompt "What invariant does this correction imply? State as a rule."
- Store the rule (not just the corrected answer) in Hindsight tagged `correction_rule`
- Distinct from DREAM intent hierarchy (previous sweep, about intent parsing)
- This is about domain facts and invariants that the agent was missing
- The rule should be checkable: "Before aggregating column X, verify field Y is excluded"

---

## Sources with Low Yield This Sweep

- **Reddit r/LocalLLaMA / r/MachineLearning**: blocked by anti-bot (403/redirect). No findings.
- **Qiita API**: returned non-JSON (rate-limit or redirect). No findings.
- **Juejin main feed**: returned frontend articles. Switched to AI-tag-filtered endpoint.
- **Zenn general query**: most results were non-agent articles. Filtered to topic-tagged articles.

**Non-English source observation (consistent with Aug 12 sweep5 finding):**
Japanese and Chinese community sources lag arXiv 2-4 weeks for cutting-edge LLM-agent research.
However, they excel at: (a) applied deployment patterns, (b) practitioner failure analysis,
(c) synthesis articles that clarify how academic concepts map to production.
Use them for "how do teams actually deploy this" questions, not "what is the latest paper."
