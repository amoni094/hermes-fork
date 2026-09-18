# Multilingual Community Sweep — Aug 12 2026 Findings

**Session:** Subagent multilingual sweep — Zenn.dev, Qiita, Juejin, Zhihu, Velog.io, Reddit, HN, GitHub trending
**Date:** Aug 12 2026
**Status of patches:** hermes-skill-library-consolidation-audit updated (this file + skill-governance-contamination-2026.md).
Three skills blocked by user-ownership guard — pending `hermes curator adopt`:
- `agent-memory-consolidation` → needs InMind world-bridge anchoring + CIAD pitfall
- `mnemosyne-atp-safety` → needs HOLD outcome + retrospective policy scan
- `hermes-context-hygiene` → needs CIAD monolithic injection pitfall

---

## FINDING 1 — InMind: Implicit-Association Blind Spot (HIGH applicability)
**Source:** arXiv:2607.24368, Jul 27 2026 | Korean review: velog.io/@mini_knows, Jul 31 2026

All vector/graph/agent memory systems fail when world knowledge bridges query and memory.
"Nut allergy" stored + "macaroon recipe" queried → 14.4% retrieval success vs 84% if
memory is in-context. The bottleneck is retrieval ordering (relevance runs before world model).

**Patch target: `agent-memory-consolidation`**
Add after Step 4 (Synthesize):
- Write-time world-bridge anchor generation (5–8 domain objects world knowledge connects to the fact)
- Ambient memory category (`ambient: true` tag) for ≤5 safety-critical always-visible facts
- Task-type-conditional injection (cooking task → always inject dietary constraints)
- NOT a retrieval quality problem — better embeddings / more iterations don't close the gap

Full detail: references/inmind-worldbridge-retrieval-2026.md (in agent-memory-consolidation once adopted)

**Patch target: `hermes-memory-surface-selection`**
Add "ambient" memory bucket as a surface option for safety-critical user constraints.

---

## FINDING 2 — CIAD: Semantic Context Injection Drift (MED applicability)
**Source:** reddit.com/r/MachineLearning/comments/1vm16hs/, Aug 12 2026

Semantically coherent 600–1200 token context blocks cause deep-layer activation drift
in small models (<7B): KL 22.87 nats, L2 shift 3434. Shuffled text of same length does NOT.
Effect: passive RLHF alignment decoupling from benign content.

**Patch target: `hermes-context-hygiene`**
Add pitfall section before Branch-and-Prune:
```
## CIAD Pitfall: Monolithic Injection for Small Local Models
For models <7B via Ollama/llama.cpp, avoid injecting thematically adjacent skill blocks
in sequence. Prefer 2–3 relevant skills over 8–10 loosely relevant. Interleave with
neutral content. Does NOT apply to large frontier models (Claude Sonnet 4.6+).
```

---

## FINDING 3 — Kastra: HOLD Outcome + Retrospective Policy Scan (MED applicability)
**Source:** kastra.ai, HN Show HN Aug 12 2026

Production ATP needs a third outcome beyond ALLOW/DENY: **HOLD** — pause, surface human-
readable action summary, wait for confirmation. Prevents both blind execution and hard abort.
Also: Recon feature scans local agent session history to auto-generate constraint rules from
risky actions already taken.

**Patch target: `mnemosyne-atp-safety`**
Add before "Explicit Verifier Layer":
- HOLD outcome implementation pattern (extend `propose()` to return `verdict: hold`)
- `_is_hold_candidate()` heuristic (irreversible action type not yet confirmed this session)
- `_format_hold_summary()` human-readable summary
- Retrospective policy scan pseudocode (search session log for risk patterns, promote to constraints)

---

## FINDING 4 — TencentDB Team Memory: Provenance and Contamination (MED applicability)
**Source:** github.com/TencentCloud/TencentDB-Agent-Memory (Aug 6 2026); velog.io/@ax_central (Aug 9 2026)

Shared skills have fleet-wide contamination risk. Need: provenance (`last_validated` field),
contamination audit (spot-check patched skills), authority tiers for propagation risk.
See: references/skill-governance-contamination-2026.md (already written to this skill)

**Patch target: `hermes-skill-library-consolidation-audit`** ← DONE (as reference file)
- `last_validated: YYYY-MM-DD` frontmatter standard
- Post-patch contamination audit step (5+ patches → spot-check each)
- Error propagation vector check (does this skill feed others?)
- `trust:` field extension for contamination risk tier

---

## FINDING 5 — Logprob First-Recall Uncertainty (LOW applicability)
**Source:** reddit.com/r/LocalLLaMA/comments/1vlvq2s/, Aug 12 2026

Pre-self-conditioning factual recall events show distributable logprob mass; rival semantically
distinct tokens signal genuine uncertainty vs tokenization splitting. Models can't self-interpret
well. Requires logprob API access (not available in Claude).

**Patch target: `subagent-output-contract`**
Future note: for local-model subagents with logprob access, flag responses where first
factual recall token entropy > 0.3 as `uncertainty: HIGH` in output contract.
LOW priority — Anthropic API does not expose logprobs.

---

## FINDING 6 — Agent-Stash: Tiered Scraping + Reasoning Budget Map (LOW applicability)
**Source:** github.com/blob42/agent-stash, reddit.com/r/LocalLLaMA, Aug 12 2026

Thin Go CLI (`net-search`) wraps SearxNG; agents discover available engines dynamically.
Tiered scraping: readability first → w3m traversal → pup structured HTML.
Reasoning budget: map thinking levels to `reasoning_budget_tokens` for local inference.

**Patch target: `firecrawl-stealth-fallback`**
Add tiered scraping sequence as a fallback: readability extraction → browser traversal →
structured HTML extraction. Currently not curator-managed (check before patching).

---

## FINDING 7 — Harvey LAB: Domain Benchmark Architecture (LOW applicability)
**Source:** github.com/harveyai/harvey-labs (1.1k stars), 2026

Open-source legal agent benchmark: task-as-rubric + execution harness + LLM judge + sweep
dashboards. Template for domain-specific agent evaluation.

**Patch target: `evaluation-driven-development`**
Add note: "Domain-specific agent benchmarks use rubric-based LLM judge + execution harness.
Harvey LAB (harveyai/harvey-labs) is the structural template for this pattern."

---

## Sources NOT yielding new findings
- Zenn.dev: login-walled / JavaScript-rendered, minimal extraction
- Qiita: mostly introductory content, nothing post Aug 12
- Juejin / Zhihu: login-walled
- GitHub trending (full language list): rendered language dropdown, not repo list
- Korean Velog (general LLM agent posts): pre-Aug 12 content, confirmatory only
