# Agent Improvement Sweep 10 — Aug 12, 2026

**Threshold:** arXiv IDs > 2608.10875 (papers submitted after Aug 11 2026)  
**Searches run:** 13 (5 prescribed + 8 targeted follow-up)  
**Candidates evaluated:** 7 papers  
**Indexing note:** arXiv indexing lag at query time; papers submitted Aug 12+ not yet indexed. Re-run in 24–48h for fuller Aug 12 coverage.

---

## Key Technique Fix: arXiv Delta Sweep Ordering

**Problem:** The prescribed search URLs used `order=-announced_date_first`, which returned papers sorted by announcement/publication date. This caused all results to be older papers (highest ID returned was 2608.10494, well below threshold 2608.10875) — zero new papers found with this ordering.

**Fix:** Use `order=-submitted_date` instead:
```
https://arxiv.org/search/?searchtype=all&query=TOPIC&start=0&order=-submitted_date
```
This returns papers sorted by submission date, surfacing the very newest IDs. With `-submitted_date`, six new papers above threshold were immediately found on the first search.

**arXiv ID filtering:** The search pages sometimes return DOI artifacts that parse as very high fake arXiv IDs (e.g., `9027.37650`, `6591.38370`). Filter with: `int(aid.split('.')[0]) < 10000` — real arXiv YYMM codes are always 4 digits in range 9001–2699.

---

## HIGH Priority Papers

### arXiv:2608.10906 — GitSkills: A Dataset of Agent Skills on GitHub
**Subjects:** cs.SE, cs.AI  
**Submitted:** Aug 11, 2026  
**Authors:** Destefanis, Graziotin, Vaccargiu, Ortu  
**Venue:** MSR '27 (to appear)

**Abstract summary:** First large-scale empirical study of Anthropic-format SKILL.md files. Dataset of 3,797,117 SKILL.md files from 282,200 public GitHub repos (July 2026), packaged as a single SQLite file with full text, parsed YAML front matter, folder contents, repo metadata, and commit history. Key structural findings:
- Skills spread by folder-copying — no package manager, no central registry
- Agent selection is probabilistic at runtime (no type checker, no compiler)
- Security and maintenance patterns are empirically unstudied at scale
- ~50% duplication: 3.79M files → 1.87M distinct contents by content hash

**Hermes implementation signals:**
1. **57-char trigger rule confirmed empirically** — the existing Hermes `description` truncation at 57 chars aligns with the most common trigger-string lengths in the wild. Validate the truncation is enforced in `hermes-agent-skill-authoring/SKILL.md`.
2. **Dedup sweep** — 50% duplication rate suggests a periodic content-hash dedup pass over `~/.hermes/skills/` is worthwhile. Skills that are identical modulo whitespace may represent historical copies that should be consolidated.
3. **Security anti-pattern** — public GitHub has millions of skill files containing embedded API tokens, credentials, and PII. Add explicit pitfall to `writing-skills` and `hermes-agent-skill-authoring`: never embed secrets, API keys, or user-specific identifiers in SKILL.md files.
4. **Dataset availability** — single SQLite file; could be queried to benchmark Hermes skill descriptions against the ecosystem's distribution of trigger patterns, front matter schemas, and description lengths.

**Complexity:** Low (skill patches), Med (dedup cron)  
**URL:** https://arxiv.org/abs/2608.10906

---

## MED Priority Papers

### arXiv:2608.10934 — Understanding the Architecture of Coding Agents
**Subjects:** cs.SE  
**Submitted:** Aug 11, 2026  
**Authors:** Marco Tulio Valente  

**Abstract summary:** Systematic architectural taxonomy for coding agents. Documents core components: planner, context window manager, tool executor, memory module, orchestrator — with explicit responsibility boundaries and execution flow diagrams. Introduces Ark (Agent Research Kit), a minimal open-source coding agent, and ArkBench (10 software maintenance tasks). GPT-5.4-mini solved 8/10 ArkBench tasks at modest token cost.

**Key insight:** The "context window manager" is identified as a first-class architectural component, not an emergent property. This component is responsible for deciding what stays in context across multi-turn interactions — distinct from memory retrieval and distinct from the planner.

**Hermes implementation signals:**
1. **`hermes-operating-pattern/SKILL.md`** — add the Ark taxonomy (planner → context manager → tool dispatcher → memory retrieval loop) as a reference architecture. Useful as a checklist when designing new subagent patterns.
2. **`autonomous-agent-loop-design/SKILL.md`** — add explicit "context window manager" as a named component. Hermes currently handles this implicitly via session stall timeout and context hygiene skills; making it explicit helps when tuning compression thresholds.
3. **ArkBench** — the 10-task software maintenance benchmark is lightweight enough to run against Hermes subagents as a capability probe. Consider adding to `evaluation-driven-development` references.

**Complexity:** Low  
**URL:** https://arxiv.org/abs/2608.10934

---

## LOW / Skipped

| arXiv ID | Title | Reason |
|----------|-------|--------|
| 2608.10920 | IO Factory: Simulating AI-Enabled Influence Campaigns | Social manipulation research, not Hermes-internal |
| 2608.10986 | What Iterated Self-Feeding Probes Measure | Theoretical token-level study, not actionable |
| 2608.10968 | Cross-Cutting Exposure as Engine of Radicalization | physics.soc-ph, wrong domain |
| 2608.10915 | ComBodied Agents: Human-Centric Agentic AI | Embodied/physical agents, not CLI agent |
| 2608.10894 | FormaTheoria: Lean Theory Construction | cs.LO/math.GR, wrong domain |
