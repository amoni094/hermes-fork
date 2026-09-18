# Research + Autonomous-AI-Agents Full Category Audit — August 2026

**Date:** 2026-08-13  
**Scope:** 17 research skills (excl. comparative-religion, legal-regulatory, computational-text) + 55 autonomous-ai-agents skills  
**Active reference files audited:** 446 (excluding .archive/)  
**Method:** Read every SKILL.md; cross-checked safety chain, memory topology, research pipeline, reference file linkage, stale content

---

## CRITICAL Findings

### CRITICAL-1: `agent-task-signoff` is an island — not referenced by the umbrella or any sibling

The safety chain culminates in `agent-task-signoff`, but it is referenced by **zero** other skills in autonomous-ai-agents. The `autonomous-ai-agents` umbrella's fast-routing section covers trajectory-risk-guardrail, mnemosyne-atp-safety, and hermes-swarm-consensus, but has **no routing entry for agent-task-signoff**.

Only `verification-before-completion` and `subagent-output-contract` (cross-category) mention it.

**Fix needed:** Add agent-task-signoff routing entry to the `autonomous-ai-agents` umbrella. Add it to `related_skills` of trajectory-risk-guardrail, mnemosyne-atp-safety, and async-agent-nightshift-patterns.

### CRITICAL-2: `hermes-swarm-consensus` recommends GPT-4o as neutral arbiter — Anthropic-only instance

The skill explicitly recommends GPT-4o as "neutral arbiter" and states "minimum 2 different provider families." But this instance is Anthropic-only — GPT-4o was explicitly confirmed as a fictional provider in `hermes-config-repo-audit`. No fallback path exists for homogeneous-provider swarms.

Same issue appears in `compositional-skill-routing` which quotes the same research finding about GPT-4o corruption resistance.

**Fix needed:** Add Anthropic-only fallback section: "when only one provider family is available, use Verbalized Sampling + diversity gate as described in Section [X]."

### CRITICAL-3: `defuddle` trigger claims "First-pass extraction" — contradicts canonical chain

`defuddle/SKILL.md` trigger says: *"First-pass extraction before running grounded-citations or research synthesis."*

Canonical chain (documented in `academic-literature-review`):
1. `web_extract` — fast, no auth
2. `firecrawl-research` — JS-heavy, stealth headers
3. `defuddle` — Mozilla Readability
4. `blocked-page-recovery` — archive.org, Unpaywall, etc.

Defuddle is **step 3**, not step 1.

**Fix needed:** Patch defuddle trigger to say "Step 3 in web extraction fallback chain — after web_extract and firecrawl-research have been tried."

### CRITICAL-4: `product-price-monitor` and `firecrawl-stealth-fallback` listed under `research` in system prompt but live elsewhere

- `product-price-monitor` → `/skills/productivity/product-price-monitor/SKILL.md`
- `firecrawl-stealth-fallback` → `/skills/autonomous-ai-agents/firecrawl-stealth-fallback/SKILL.md`

No SKILL.md exists at `research/product-price-monitor/` or `research/firecrawl-stealth-fallback/`.

**Fix needed:** Correct system prompt category listing.

---

## HIGH Findings

### HIGH-1: `hermes-cowork-port-sync` has stale Ollama-as-embedder references

Four locations describe Hindsight as `local_embedded/Ollama`. Ollama was removed 2026-07-12; Graphiti embeddings now use OpenAI `text-embedding-3-small`. Also affects `tencentdb-agent-memory` (one table row).

### HIGH-2: `hermes-config-repo-audit` references Ollama port 11434 as a live service

States Ollama serves embeddings on port 11434. Ollama removed 2026-07-12. An audit pass from this skill will check port 11434 as expected, which no longer exists.

### HIGH-3: Research pipeline only documented end-to-end in `academic-literature-review` — not in the pipeline's own skills

The canonical flow `arxiv → domain-research-synthesis → arxiv-sweep-findings → skill patches` is only fully described in `academic-literature-review`. 

- `arxiv` lists `arxiv-sweep-findings` in related_skills but provides no routing body about downstream flow
- `domain-research-synthesis` lists `arxiv-sweep-findings` but no body text explaining the patch endpoint  
- `arxiv-sweep-findings` documents the patch procedure well but doesn't reference `arxiv` as its upstream

An agent loading `arxiv` or `arxiv-sweep-findings` directly won't see the pipeline unless it also loads `academic-literature-review`.

### HIGH-4: `self-improve-agent` and `harness-first-agent-design` have NO safety stack references

Neither skill mentions trajectory-risk-guardrail, mnemosyne-atp-safety, verification-before-completion, or agent-task-signoff. Both skills involve significant side-effect potential (self-modifying skill library, harness design with tool call chains).

### HIGH-5: Three orphan reference dirs — files exist but SKILL.md has zero `references/` mentions

| Skill | Reference files | 
|---|---|
| `autonomous-ai-agents/anthropic-agent-api-patterns` | `anthropic-agent-api-aug2026.md` — unreachable |
| `superpowers/dispatching-parallel-agents` | 2 files — unreachable |
| `software-development/workflow-map` | 1 file — unreachable |

### HIGH-6: Memory topology dual-write not documented in `agent-memory-consolidation`

`agent-memory-consolidation` covers MEMORY.md and Hindsight extensively but has **no mention** of the Hindsight→Graphiti dual-write via `l1-graphiti-write.py`. The dual-write is documented in `hindsight-stack-operations` but not propagated here. This skill is the most likely landing point for memory pipeline work.

### HIGH-7: `llm-agent-memory-pipeline-research` trigger overlaps with `agent-memory-consolidation` — no disambiguation

Both can fire on "memory consolidation," "cross-session memory transfer," "knowledge graph agent memory." Neither has a NOT-gate distinguishing research-bibliography mode from operational mode.

---

## MEDIUM Findings

### MEDIUM-1: `visual-document-review` hardcodes `claude-opus-4-8` — will drift
Two command examples embed a versioned model string. Should use generic `-m opus` alias.

### MEDIUM-2: `academic-literature-review` has 40+ reference files — most are de facto orphans
Only ~5 explicitly named in SKILL.md body. ~35 topic-specific research dumps (legal-ai-evals, pead-earnings, asian-trading-strategies, etc.) are undiscoverable unless the agent enumerates the directory. A reference-files-index.md exists but isn't routed to from the main skill body.

### MEDIUM-3: `agent-reach-discovery` is an isolated island
No `related_skills`, `depends_on`, `provides` in YAML. Not referenced by any peer research skill (firecrawl-research, domain-research-synthesis, academic-literature-review) despite serving those workflows. No reference files.

### MEDIUM-4: `competitor-news-monitor` / `political-source-monitoring` — near-identical trigger overlap
`political-source-monitoring` has a NOT-gate ("not for companies"). `competitor-news-monitor` has no reciprocal NOT-gate for political monitoring. A "monitor these politicians" request may load the wrong skill.

### MEDIUM-5: `async-agent-nightshift-patterns` safety chain incomplete
`related_skills` includes trajectory-risk-guardrail and mnemosyne-atp-safety. Missing: verification-before-completion and agent-task-signoff. For unattended agents specifically, the final steps are critical.

### MEDIUM-6: `hermes-self-evolution` reference is a passive pointer, not an active handoff
Body says "Reference: `references/self-evolution-validation.md`" but no `skill_view` call syntax, no key findings surfaced inline. Future agents won't know to load it.

### MEDIUM-7: Model version strings embedded in `autonomous-agent-loop-design` body
"Not available on claude-sonnet-4-6/opus-4-8" — specific version strings that will drift with model generations.

### MEDIUM-8: `deepseek-reasonix-patterns` trigger overlap with adjacent skills
Triggers like "tiered context compaction," "cache-first agent design," "guardian safety gate" overlap substantially with `hermes-context-hygiene`, `harness-first-agent-design`, and `mnemosyne-atp-safety`. Description too broad — matches harness-first-agent-design's domain exactly.

### MEDIUM-9: `preact-trajectory-compilation` missing `depends_on`/`provides` fields
Has `related_skills` but no graph metadata. Limits DAG planning for the compilation→execution→guardrail chain.

### MEDIUM-10: `arxiv-sweep-findings` `hermes curator adopt` prerequisite not reflected upstream
Many target skills are curator-managed (user-owned), so patches are blocked without `hermes curator adopt <skill>`. This is documented inside arxiv-sweep-findings but not mentioned in `arxiv` or `domain-research-synthesis` which feed it. Agents running the pipeline from the top will hit blocked patches unexpectedly.

### MEDIUM-11: `firecrawl-stealth-fallback` in autonomous-ai-agents/ listed as research/ in system prompt
Even if skill_view resolves correctly by name, the category label misleads about when to consider it vs. `firecrawl-research` (which is actually in research/).

### MEDIUM-12: `hermes-obsidian-sync` has 23 reference files — SKILL.md body names ~4
Most patterns (timestamp maintenance, daily bootstrap, cron sync variants) are undiscoverable from the skill body. An agent must enumerate the directory.

---

## LOW Findings

- `defuddle` has zero YAML metadata fields (`related_skills`, `depends_on`, `provides`)
- `gold-class` and `stay-in` reference each other in metadata but not in body text
- `ralph-loops` mentions TRG + mnemosyne in related_skills but omits verification-before-completion and agent-task-signoff
- `hermes-swarm-consensus` states live model is claude-sonnet-4-6 but recommends GPT-4o without noting it's unavailable on this instance
- Research pipeline end-to-end flow not documented as a single canonical sequence anywhere in `research/` category
- `political-source-monitoring` has no `depends_on`/`provides` fields — thin metadata

---

## Reference File Audit Summary

**Active (non-archive) reference .md files:** 446  
**True orphan reference dirs (refs exist, SKILL.md has zero `references/` mentions):**
- `autonomous-ai-agents/anthropic-agent-api-patterns` (1 file)
- `superpowers/dispatching-parallel-agents` (2 files)  
- `software-development/workflow-map` (1 file)

**Large collections with sparse SKILL.md pointer coverage:**

| Skill | Ref files | Body pointers | Gap |
|---|---|---|---|
| `academic-literature-review` | 40+ | ~5 named | ~35 unreachable |
| `hermes-obsidian-sync` | 23 | ~4 named | ~19 unreachable |
| `domain-research-synthesis` | 25+ | ~6 named | ~19 unreachable |
| `agent-memory-consolidation` | 13 | ~8 named | Better coverage |

---

## Cross-Cutting Chain Status

### Memory Topology: Hindsight → Graphiti dual-write → MEMORY.md → system prompt
- `hindsight-stack-operations`: ✅ well documented, dual-write and l1-promote no-op stub both present
- `graphiti-mcp-setup`: ✅ covers topology
- `hermes-memory-surface-selection`: ✅ marginal coverage
- `agent-memory-consolidation`: ❌ **missing dual-write leg** — only covers Hindsight and MEMORY.md

### Agent Safety Stack: TRG → mnemosyne-atp-safety → verification-before-completion → agent-task-signoff
- `trajectory-risk-guardrail`: ✅ documents all four steps with correct ordering (lines 102-104)
- `mnemosyne-atp-safety`: ✅ references TRG and VBC, correct ordering in body
- `verification-before-completion`: ✅ references agent-task-signoff
- `agent-task-signoff`: ✅ references VBC in `depends_on`
- `autonomous-ai-agents` umbrella: ❌ **missing agent-task-signoff routing entry**
- `self-improve-agent`: ❌ **zero mentions of any stack member**
- `harness-first-agent-design`: ❌ **zero mentions of any stack member**
- `async-agent-nightshift-patterns`: ⚠️ only TRG + mnemosyne — missing VBC + signoff
- `ralph-loops`: ⚠️ only TRG + mnemosyne in related_skills

### Research Pipeline: arxiv → domain-research-synthesis → arxiv-sweep-findings → skill patches
- `academic-literature-review`: ✅ documents canonical chain AND fallback chain completely
- `arxiv-sweep-findings`: ✅ patch procedure well documented; ⚠️ no upstream reference to arxiv skill
- `domain-research-synthesis`: ⚠️ lists arxiv-sweep-findings in related_skills but no pipeline body
- `arxiv`: ⚠️ lists downstream skills in related_skills but no pipeline routing body
- Gap: curator-adopt prerequisite for blocked patches undocumented in upstream skills

### Web Extraction Fallback Chain: web_extract → firecrawl-research → defuddle → blocked-page-recovery
- `academic-literature-review`: ✅ canonical chain documented correctly (lines 102-108)
- `firecrawl-research`: ✅ positions correctly as step 2
- `blocked-page-recovery`: ✅ positions correctly as final step
- `defuddle`: ❌ **calls itself "First-pass extraction" — contradicts chain position as step 3**

---

## Priority Remediation Order

| Priority | Skill | Action |
|---|---|---|
| CRITICAL | `autonomous-ai-agents` umbrella | Add agent-task-signoff routing entry |
| CRITICAL | `hermes-swarm-consensus` | Add Anthropic-only fallback path for single-provider swarms |
| CRITICAL | `defuddle` | Fix trigger: "Step 3 in fallback chain" not "First-pass" |
| CRITICAL | System prompt category listing | Fix product-price-monitor, firecrawl-stealth-fallback categories |
| HIGH | `hermes-cowork-port-sync` | Remove/update 4 Ollama-as-embedder lines |
| HIGH | `hermes-config-repo-audit` | Remove port 11434 as expected live service |
| HIGH | `self-improve-agent` | Add safety stack pre-condition routing |
| HIGH | `harness-first-agent-design` | Add safety stack pre-condition routing |
| HIGH | `agent-memory-consolidation` | Add Hindsight→Graphiti dual-write topology section |
| HIGH | 3 orphan reference skills | Add `skill_view` loading instructions to SKILL.md bodies |
| MEDIUM | `llm-agent-memory-pipeline-research` | Add NOT-gate distinguishing from agent-memory-consolidation |
| MEDIUM | `async-agent-nightshift-patterns` | Add VBC + agent-task-signoff to related_skills and body |
| MEDIUM | `agent-reach-discovery` | Add related_skills, depends_on, provides fields |
