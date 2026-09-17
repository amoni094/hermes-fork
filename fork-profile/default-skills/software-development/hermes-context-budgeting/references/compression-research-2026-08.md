# Context Compression Research — 2025-2026 Findings
# Aggregated from research session 2026-08-10

## Structured vs. Uniform Pruning — Master Comparison

| Strategy | Type | Compression | Quality | Best for |
|---|---|---|---|---|
| Sliding window / full replacement | Uniform | High | Loses long-range context | Short sessions only |
| Full-reconstruction summarisation | Uniform | Medium | Detail drift across cycles | Moderate sessions |
| Anchored iterative summarisation | Structured | Medium (delta) | ↑ Artifact/Decision probes | Long coding sessions |
| Failure-driven guideline (Acon) | Structured | 26–54% | 95%+ retained | Long-horizon tasks |
| Block-wise eviction (PagedEviction) | Structured | Variable | Better than token-level | KV cache / inference |
| Progressive disclosure (SkillReducer) | Structured | 39–48% | +2.8% quality | Skill body injection |
| Subunit-level (SkillRAE) | Structured | 40–60% | +11.7% task success | Skill body injection |

**Key insight:** The 35% floor (arXiv:2608.01056) applies to **uniform** compression of
arbitrary text. Structured compression (task-aware, content-type-aware, failure-aware)
breaks below it without quality loss because it identifies *which 35% to keep* rather
than keeping a random 65%.

## Content-Type Compression Targets

Tag context content by type at ingestion; apply different budgets:

| Type | Max compression | Rationale |
|---|---|---|
| Tool output (raw JSON/HTML/terminal) | 70–80% | Near-zero semantic loss |
| Assistant reasoning chains | 40% | Mid-value; preserve decisions |
| Skill body injections | 39–48% (SkillReducer) | Use progressive disclosure |
| User messages | 20% max | Preserve intent and constraints |
| System anchor / AGENTS.md | 0% | Never compress static prefix |

---

## Acon — Failure-Driven Guideline Optimisation (arXiv:2510.00615, KAIST/Microsoft)

Published: Oct 2025. Benchmarks: AppWorld, OfficeBench, Multi-objective QA.

**Results:**
- Peak token reduction: **26–54%**
- Accuracy preservation: **>95%**
- Smaller LM improvement as long-horizon agent: up to **+46%**
- Gradient-free → compatible with closed-source models (GPT-4.1, Claude)

**Mechanism:**
1. Run agent on task with full context → record outcome
2. Run agent with compressed context → record outcome
3. When compressed fails but full succeeds: LLM analyses the *cause* of failure
4. Compression guideline updated: "When compressing <task type>, always preserve X,
   discard Y"
5. Iterate until guideline converges across task examples

**Hermes application:**
- Current `micro_compact` (every 3 turns) uses a fixed summarisation prompt
- After any task that fails immediately post-compaction: log boundary + failure
- After N=5 failures: ask LLM what class of info was lost → prepend to compression
  system prompt → store as `~/.hermes/compression_guidelines.md`
- Already documented in hermes-context-hygiene SKILL.md; this file adds the numbers

---

## PagedEviction — Structured Block-Wise KV Cache Pruning (EACL 2026)

Chitty-Venkata et al., EACL 2026 findings track.
URL: https://aclanthology.org/2026.findings-eacl.168/

**Results:**
- Structured **block-wise** eviction on vLLM PagedAttention: better accuracy than
  token-level baselines on LongBench (Llama-3.1-8B, 3.2-1B, 3.2-3B)
- Evicting *whole coherent blocks* outperforms token-level eviction because it
  preserves local coherence

**Application for Hermes `proactive_prune_tokens=48000` trigger:**
- Group conversation turns into semantic blocks: [tool-call → result → reasoning →
  response] = one block
- When pruning at 48K token threshold: evict the oldest 2–3 coherent blocks whole,
  rather than snipping individual token spans across all turns
- This avoids breaking mid-tool-call context (e.g. a result that references a prior
  call's output)

---

## Anchored Iterative Summarisation — Factory.ai Study (Dec 2025)

Factory.ai Research: https://factory.ai/news/evaluating-compression
Dataset: 36,000 real engineering session messages (debug, PR review, feature impl,
CI, ML research).

**Results:**
- Structured summarisation (Factory) outperforms OpenAI and Anthropic native
  compaction on ALL probe dimensions
- Probe types evaluated:
  - **Recall** — factual retention ("what was the original error message?")
  - **Artifact** — file tracking ("which files were modified and how?")
  - **Continuation** — task planning ("what should we do next?")
  - **Decision** — reasoning chain ("what did we decide about the Redis issue?")
- Anchored iteration > full reconstruction on Artifact and Decision probes

**Why anchored beats full-reconstruction:**
- Full reconstruction: summarise the ENTIRE history from scratch each time
  → Details drift or disappear across multiple compression cycles
  → Expensive: must re-process full history
- Anchored: maintain a persistent anchor state; summarise ONLY the newly-dropped span;
  merge mini-summary into anchor

**Hermes application:**
- Maintain `~/.hermes/sessions/<id>/anchor_state.md` across compactions
- Each `micro_compact` call: summarise only turns [last_compact_turn:now]
- Merge result into anchor (don't regenerate from scratch)
- The compression-config-reference-2026-08.md already shows micro_compact=true
  every 3 turns — confirm implementation is delta-merge, not full-reconstruct

---

## Context Drift as Primary Failure Mode (Zylos Research, Feb 2026)

URL: https://zylos.ai/research/2026-02-28-ai-agent-context-compression-strategies/

**Results:**
- **65% of enterprise AI failures** in 2025 attributed to context drift / memory loss
  — not raw context window exhaustion
- At 95% per-step reliability over 20 steps: combined success rate = only **36%**
- 2% misalignment introduced early compounds to **40% failure rate** by end
- Industry shifting from expanding context windows → smarter context management in 2026

**Anthropic native compaction:** `compact-2026-01-12` API available across Claude API,
AWS Bedrock, Vertex AI, Foundry — with Zero Data Retention support. When provider is
Anthropic and native compaction is available, prefer it over custom summarisation prompt.

**Hermes `idle_compact_after_seconds: 1800` limitation:**
- Currently triggered by time, not by drift severity
- Improvement: add embedding-similarity drift detector — before each LLM call, compute
  similarity between current task description and compressed anchor state; if <0.65,
  trigger early compaction even if turn threshold not hit

---

## YAML AgentSpec — JSON Schema Validation Pattern (Pydantic AI, 2026)

URL: https://pydantic.dev/docs/ai/core-concepts/agent-spec/

**Key pattern (declarative YAML agent config with editor validation):**

```yaml
# agent.yaml
model: anthropic:claude-opus-4-6
instructions: You are a helpful research assistant.
model_settings:
  max_tokens: 8192
capabilities:
  - WebSearch:
      local: duckduckgo
  - Thinking:
      effort: high
```

```python
# One-line construction from validated YAML
from pydantic_ai import Agent
agent = Agent.from_file('agent.yaml')
```

- `AgentSpec.to_file()` auto-generates companion `agent_schema.json` for YAML Language
  Server validation (editor autocompletion + inline validation)
- Merge semantics: scalar fields override; `instructions` and `capabilities` merge
  additively; `model_settings` merge with keyword args overriding spec

**Recommended Hermes SKILL.md frontmatter JSON Schema (for CI/CD validation):**

```json
{
  "$schema": "http://json-schema.org/draft-07/schema",
  "type": "object",
  "required": ["name", "description"],
  "properties": {
    "name":        {"type": "string", "maxLength": 64, "pattern": "^[a-z][a-z0-9-_]*$"},
    "description": {"type": "string", "maxLength": 57, "minLength": 10},
    "triggers":    {"type": "array", "items": {"type": "string"}},
    "negative_triggers": {"type": "array", "items": {"type": "string"}},
    "related_skills":    {"type": "array", "items": {"type": "string"}},
    "conflicts_with":    {"type": "array", "items": {"type": "string"}},
    "depends_on":        {"type": "array", "items": {"type": "string"}},
    "composes_with":     {"type": "array", "items": {"type": "string"}},
    "supersedes":        {"type": "array", "items": {"type": "string"}},
    "trust":  {"type": "string", "enum": ["core", "community", "user"]},
    "scope":  {"type": "array", "items": {"type": "string"}},
    "last_validated": {"type": "string", "format": "date"},
    "routing_signals":   {"type": "string", "maxLength": 400}
  }
}
```

Save as `~/.hermes/skills/skill_schema.json`. Reference in `.vscode/settings.json`:
```json
{"yaml.schemas": {"~/.hermes/skills/skill_schema.json": "**/SKILL.md"}}
```
Run `hermes skills validate` (once available) as pre-commit hook.

---

## Prompt Caching Discipline — Static Prefix = 60-80% Cost Reduction

Source: Anthropic docs + r/LocalLLaMA 2025-2026 threads + hermes-context-hygiene.

**Core rule:** system prompt = read-only once session starts. Any dynamic content
(task state, tool results, per-turn memory) goes in the **user message prefix**, not
the system prompt.

**Strict prompt section order for cache preservation:**
1. `[SYSTEM STATIC]` AGENTS.md + persona (never changes → cache hits every turn)
2. `[SKILLS STATIC]` skill descriptions set at session start (don't add mid-session)
3. `[TASK DYNAMIC]` conversation history / compressed anchor (changes every turn)

**Timing note:** Hermes `micro_compact` runs every 3 turns at ~2 min/turn = ~6 min.
Anthropic cache TTL = 5 minutes. If micro_compact changes the system prompt prefix,
every compaction is a cache miss. Solution: micro_compact should write to the
TASK DYNAMIC section only, keeping the SYSTEM STATIC prefix byte-stable across all turns.

**`idle_compact_after_seconds: 1800` and cache TTL:** 30-minute idle compact fires well
after the 5-minute cache TTL expires anyway — no cache benefit expected. The value
primarily prevents session bloat on resume, not cache optimisation.
