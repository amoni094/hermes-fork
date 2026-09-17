---
name: arxiv-sweep-findings
description: >
  Use when: querying the Hermes research findings bank — what papers were found in past
  sweeps, what technique classes exist, what's pending implementation. NOT for running
  sweeps (use hermes-research), searching arXiv for new papers (use arxiv), or applying
  patches to skills (use trajectory-research-synthesis-to-skills).
version: 1.0.0
author: Hermes Agent (curator)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [arxiv, research, self-improvement, skill-library, memory, agent]
    related_skills: [arxiv, academic-literature-review, llm-agent-memory-pipeline-research, skillopt-continuous-improvement, self-improve-agent, trajectory-risk-guardrail]
# See also: references/sweep-source-config.md — source list, noise pitfalls, CS domain filters

triggers:
  - what did sweep N find
  - arxiv sweep summary
  - research findings bank for Hermes
  - what technique classes have been found
  - what papers are pending implementation
  - sweep boundary log
  - what's the cutoff ID for the last sweep
  - NOT for running a sweep (use hermes-research)
  - NOT for applying findings as skill patches (use trajectory-research-synthesis-to-skills)
  - NOT for searching arXiv for new papers (use arxiv skill)
  - NOT for structured academic surveys (use academic-literature-review)
  - NOT for agent memory research specifically (use llm-agent-memory-pipeline-research)
related_skills:
  - grounded-citations
  - firecrawl-research
  - arxiv
  - academic-literature-review
  - llm-agent-memory-pipeline-research
  - skillopt-continuous-improvement
  - self-improve-agent
  - trajectory-risk-guardrail
---

# arXiv Sweep Findings — Hermes Self-Improvement Research Bank

Condensed actionable findings from periodic arXiv sweeps across cs.AI, cs.CL, cs.MA,
cs.CR, cs.LG, cs.IR, cs.SE. HIGH and MED applicability only. Organised by technique class.


## When to Use

Query the findings bank: what past sweeps found, which technique classes exist, cutoff IDs, pending vs applied.

Do NOT:
- run a new sweep → `hermes-research`
- apply findings as skill patches → `trajectory-research-synthesis-to-skills`
- search arXiv for new papers → `arxiv`
- structured academic surveys → `academic-literature-review`
- agent memory pipeline research → `llm-agent-memory-pipeline-research`

## How to use this skill

1. Check the Sweep Boundary Log for cutoff / HIGH-MED counts.
2. Open the matching technique-class reference (index below). Read the Hermes note.
3. If implementing: hand off to `trajectory-research-synthesis-to-skills`. This skill is the catalog, not the patcher.
4. User-owned targets: record + `hermes curator adopt <name>` — never silent-drop.

Duplicate paper IDs: arXiv:2604.17091 appears as both GenericAgent trilemma and content-relevance decay (same paper, two notes). Do not re-absorb twice.

## Technique class index

| File | Contents |
|------|----------|
| `references/technique-classes-sweep-11-20.md` | Sweeps 11–20 classes (pre-boundary-log body) |
| `references/technique-classes-sweep-16-17.md` | Sweeps 16–17 classes (were duplicated after the log) |
| `references/technique-classes-sweep-18-29.md` | Sweeps 18, 24, 27–29 (were appended after References) |
| `references/sweep-<N>.md` | Per-sweep indexes, defer matrices, pitfalls (pattern — files are `sweep-30.md`, `sweep-31.md`, …; there is no `sweep-N.md`) |
| Applied HIGH 2609.* (adjacent apply — **not** the sweep-33 HIGH table) | Concepts live in target skills, not a new class file: Minimal-sufficient profiles (2609.08180) → `agent-memory-consolidation` + `hermes-memory-surface-selection`; MeClear attribution clearance (2609.09115) → `agent-memory-consolidation`; Context engineering (2606.10209) → `hermes-context-hygiene` + `agent-runtime-loop-patterns`; Prospect-state (2609.08033) → `dispatching-parallel-agents` + `hermes-context-hygiene`; Procedural graphs (2609.09153) → `autonomous-agent-loop-design` + `agent-runtime-loop-patterns`; Cross-substrate authority (2609.08472) → `trajectory-risk-guardrail` + `mnemosyne-atp-safety`. Sweep 33 HIGH/MED (5 HIGH applied, 6 MED logged) live only in `references/sweep-33.md`. |

Query by technique name or arXiv ID inside those files. Do not paste class bodies back into this SKILL.md.

## Sweep Boundary Log

| Sweep | Date | Baseline cutoff ID | Highest ID found | Papers reviewed | HIGH | MED | Reference file |
|-------|------|-------------------|-----------------|-----------------|------|-----|----------------|
| 1–7 | pre-2026-08-12 | unknown | ~2608.00xxx | unknown | — | — | ⚠️ No records — session history only |
| 8 | 2026-08-12 | ~2608.09930 | 2608.09930 | ~21 | ~21 | — | `references/sweep-8-10-index.md` |
| 9 | 2026-08-12 | 2608.09930 | 2608.10875 | 4 | 3 | — | `references/sweep-8-10-index.md` |
| 10 | 2026-08-12 | 2608.10875 | 2608.10986 | 3 | 1 | 1 | `references/sweep-8-10-index.md` |
| 11 | 2026-08-12 | 2608.10986 | 2608.11200 | 11 abstracts | 2 | 5 | `references/sweep-11.md` |
| 12 | 2026-08-13 | 2608.11200 | 2608.12311 | 12 abstracts | 5 | 5 | `references/sweep-12.md` |
| 13 | 2026-08-14 | 2608.12311 | 2608.13558 (post-cutoff max) | 21 key findings (14 arXiv + 7 GitHub/social) | 6 | 8 | `references/sweep-13.md` |
| 14 | 2026-08-14 | 2608.13558 | 2608.12990 (below cutoff; sampled, not a new-ID walk) | 20 (14 arXiv + 6 GitHub/social) | 5 | 4 | `llm-agent-memory-pipeline-research` skill → `references/agent-memory-sweep-aug14-2026-sweep14.md` |
| 15 | 2026-08-14 | 2608.13558 | 2608.12984 (below cutoff; Aug 14 sample) | 14 total (9 arXiv + 5 web; 6 HIGH, 8 MED) | 6 | 8 | `references/technique-classes-sweep-11-20.md` |
| 16 | 2026-08-14 | 2608.13558 | 2608.13560 (only paper above cutoff) | 11 total (enumerated sources: 1 arXiv + 3 GitHub + 3 web; 3 net-new; parenthetical is not a full census) | 0 (all blocked) | 3 | `references/technique-classes-sweep-16-17.md` |
| 17b | 2026-08-17 | 2608.13560 | 2608.14109 | 7 findings (4 arXiv: 14109,13334,13574,13606 — one is missed-prior 2605.11032; 2 Qiita; 1 GitHub) | 4 patchable | 3 blocked | applied into named skills (no dedicated sweep file) |
| 17 | 2026-08-17 | 2608.13560 | 2608.14036 | 18 total (8 arXiv + 4 GitHub + 3 web sources + 2 Reddit + 1 Japanese) | 5 HIGH | 1 MED | `references/technique-classes-sweep-16-17.md` |
| 18 | 2026-08-18 | 2608.14109 | 2608.15071 | 4 qualifying (2 arXiv + 2 web; probed range 2608.14110–2608.17999) | 2 HIGH | 2 MED | `references/technique-classes-sweep-18-29.md` |
| 19 | 2026-08-19 | 2608.15071 | 2608.18066 | 9 total (enumerated: 3 arXiv + 2 GitHub + 1 HN + 1 Zenn/JP; 4 net-new applied; parenthetical is not a full census) | 2 HIGH | 2 MED | `references/technique-classes-sweep-11-20.md` |
| 20 | 2026-08-22 | 2608.18066 | 2608.20320 | 30 total (9 arXiv + 6 GitHub/HN + 5 JP/multilingual + 4 practitioner; 18 net-new applied) | 12 HIGH | 6 MED | `references/technique-classes-sweep-11-20.md` |
| 21 | 2026-08-22 | 2608.20320 | 2608.20320+ | 24 net-new (arXiv+ACL+ICLR+Zenn+Qiita+GS redo; 2 tasks re-run due to Brave API inheritance) | 15 HIGH | 6 MED | `references/sweep-21-in-progress.md` |
| 22 | 2026-08-25 | 2608.20320+ | 2608.21341 | multi-source (arXiv+GitHub+HN+social, multilang) | — | — | `references/sweep-22-index.md` |
| 23 | 2026-08-25 | 2608.21341 | 2608.23552+ | multi-source (arXiv+4 subagents+GitHub+HN+Zenn/JP+Habr/RU+Qiita/JP+Juejin/CN+Velog/KR+ACL/ICLR/SearXNG) | 12 HIGH | 9 MED | `agent-memory-consolidation` skill → `references/sweep-23-findings.md` |
| 24 | 2026-08-25 | 2608.23552 | 2608.23566 | 5 subagents (arXiv+GitHub+HN; only 10 papers above cutoff, mostly non-CS) | 1 HIGH (2608.23565 ReWorld) + security/lifecycle findings from adjacent IDs | 6 MED | `agent-memory-consolidation` skill → `references/sweep-24-findings.md` |
| 25 | 2026-08-25 | 2608.23566 | 2608.23566 (no new walk) | Recovery + MemSIF Dual-Track runtime + crash-dump skill tombstone + ephemeral 500 cap + Graphiti 40k/50k check | 1 HIGH applied (runtime) | 0 | `agent-memory-consolidation` skill → `references/sweep-25-findings.md` |
| 26 | 2026-08-25 | 2608.23566 | 2608.23566 (0 new IDs) | 185-backlog triage (347→185→16 HIGH, most already applied) + Dual Process session cap + SkillZip Map-Guided dup | 1 HIGH applied (runtime) | 0 | `references/sweep-26.md` |
| 27 | 2026-08-25 | 2608.23566 | 2608.23566 (0 new IDs) | AutoSaddler + Interaction Tax + CatchBench PRE/LIVE/POST + config/code promote-threshold sync + FAMA gen_gap + config-loaded caps | 3 HIGH applied (skills+runtime) | 0 | `references/sweep-27.md` |
| 28 | 2026-08-26 | 2608.23566 | 2608.24885 | Multi-source above cutoff (~80 IDs). Constraint Weakening + Handoff Tax + Recuris WM + Paritok intent offload + OODA-Tool + belief-miscal + brave→brave-free | 6 HIGH + runtime web fix | 3 MED | `references/sweep-28.md` |
| 29 | 2026-08-29 | 2608.24885 | 2608.27454 | 22 papers above cutoff (cs.AI/CL/MA). JIT-Agent + SKILL.state + CaSKG + WikiSkill + Tool-Outputs-as-Commands + Five Governance Primitives + Agent Mesh Reliability + GraphMemix + INTENT-AS-A-TOOL + MemToC + BCIT + Calibration Gate. GitHub: agent-mesh patterns. Multilingual: Habr diversity/memory costs, Zenn hot/cold memory, Qiita enterprise agent architecture. | 7 HIGH | 5 MED | `references/sweep-29.md` + `references/technique-classes-sweep-18-29.md` |
| 30 | 2026-08-31 | 2608.27454 | 2608.27454 (multi-source; no new IDs above cutoff; new sources added) | 420 raw papers (75 after agent-relevance filter). TrajectorysentinelL failure detection+rollback, Prime Agent harness separation+Continual Harness, Framework Bugs v4 root-cause distribution. Expanded sources: HF Papers, PWC, Crossref, Korean OpenAlex filter. All 5 queries/category (was 3). | 3 HIGH | 3 MED | `references/sweep-30.md` |
| 31 | 2026-09-04 | 2608.27454 | 2609.03201 | 49 titled papers (from 347 in cache: 298 bare arXiv listing IDs excluded per first-pass-count rule). MemoryLACE atomic writes, CAST episodic decomposition, APEx trajectory distillation, Act More/Decide Less chunking, Agentic Graph RAG routing, Delegation Without Trust auth broker, Gated-Memory write gate. | 7 HIGH | 3 MED | `references/sweep-31.md` |
| 32 | 2026-09-06 | see `references/sweep-32.md` | — | apply log | — | — | `references/sweep-32.md` |
| 33 | 2026-09-09 | sweep-32 | 2609.09150 | Sep 9 2026: remaining HIGH apply (EXG, SkillOpt exec, SkillAlign, Flight Recorder, co-evolution) + MED log | 5 HIGH applied | 6 MED logged | `references/sweep-33.md` |
| 34 | 2026-09-10 | 2609.09150 | 2609.08832 | Sep 10 2026: MATH corpus sweep. 18 new math IDs. 6 CHAIN evaluated (2609.08832, 2609.04059, 2609.07787, 2609.03161, 2609.01963, 2604.16416). sweep-34.md written 2026-09-11. | PARTIAL (see sweep-34.md) | 6 CHAIN pending actions | `references/sweep-34.md` |
| 35 | 2026-09-15 | 2609.09151 | 2609.13072 | 14 new agent-cat IDs (from Sep 14 2026 sweep) | 2 | 3 | `references/sweep-35.md` |
| 36 | 2026-09-15 | 2609.13072 | 2609.13072 (no new-ID walk; titled agent papers from Sep 14 batch) | 21 candidates triaged from 404 titled agent-cat papers. 7 HIGH implemented (Memory Portability/2609.05339, Scroll/2608.21690, HyMem/2608.15703, DEAR/2608.03648, Misinformation-MA/2606.16710, Evo-Harness/2608.15071, AdaRubric/2603.21362). Math/CS subagent sweep concurrent. | 7 | 4 | `references/sweep-36.md` |
| CORPUS-CYCLE-1 | 2026-09-11 | all three banks | — | Full corpus consolidation cycle: arxiv-sweep-findings sweeps 1–34 + hermes-cs-sweep-findings + hermes-math-sweep-findings consolidated into /tmp/corpus-consolidated.md (391 total, 57 pending). 25 HIGH/DIRECT skill patches applied across 15 skills. Fork commits: f9025e18cc (entropy decay/IT-weighted/warm-start cache) + e0e3f2e25e (adversarial fixes: entropy bands removed, novelty prior 0.5, _read_hint expiry, single-writer hint). 2 new skills created (information-flow-control, session-warm-start-protocol). Config: prospect_pruning+session_warm_start+governance comments added. Adversarial verdict: CONDITIONAL_PASS after fixes (was FAIL). 176 tests passing. | applied | — | /tmp/corpus-consolidated.md + /tmp/implementation-plan.json (57 remaining items) |

## Blocked Patches

Single table. Historical closed rows: `references/blocked-patches-historical.md` (all applied or skipped 2026-08-18). Add a row only for a finding that is **not** already in the target skill. Applied → delete the row.

## Maintenance Notes (for sweep authors)

1. **One Blocked Patches table.** Never add a second `## Blocked Patches` section. Duplicate sections create split-state conflicts invisible to future patch authors.
2. **Sweep log is continuous.** Unbroken row per sweep. Sweeps 1–10 are one gap row. Missing future rows are untraceable.
3. **Split-absorbed state.** If the technique is already in the target skill, close the blocked row — do not add another.
4. **arXiv:2608.10743 provenance gap.** Absorbed into `domain-research-synthesis` with no sweep-log row (ID below Sweep 11 cutoff). Marked sweep-unknown until 1–10 records recover.
5. **Technique class ordering.** New classes go in the matching `references/technique-classes-*.md` (or a new sweep file), chronological, never interleaved back into this SKILL.md body.
6. **First-pass HTML counts are not a backlog.** Downselect via abs pages; implement HIGH only. See `references/sweep-implementation-pitfalls.md` and `references/sweep-26.md`.
7. **Config/code threshold drift.** Promote gates live in both `config.yaml` and scripts; load from config; keep values equal.
8. **Defer/SKIP benefit-cost matrix (required).** For every HIGH/MED left unimplemented, one row in that sweep's file (`references/sweep-30.md`, `sweep-31.md`, … — not a file named `sweep-N.md`): Item | Benefit here | Partial coverage already | Cost/risk | Revisit trigger. Example: `references/sweep-30.md`. This skill is the catalog; apply via `trajectory-research-synthesis-to-skills`.
9. **Config YAML nesting / am-sentry wiring:** `references/sweep-29-implementation-notes.md` — do not re-paste those procedures here.
10. **Broken spike-queue ID extraction.** Interpreter runs occasionally produce queue JSON entries with no `arxiv_id` field (ID extraction silently drops on regex miss). Symptom: `math-spike-queue.json` or `cs-spike-queue.json` entries have `title` but no `id` or `arxiv_id`. Fix: web_search the title verbatim to recover the arXiv ID, then fetch full text and run the chain fresh from Step 0. If the title is LLM-generated (no matching paper found), discard the entry. When a queue is substantially broken (>30% entries missing IDs), run a fresh abstract search for the date range rather than reconstructing entries individually — fresh sweep is faster and more reliable.

### Named deferred spikes (pain-gated)

1. **MemSIF** — spike when arc-recall pain or precision@5 < 0.6. Dual-Track ≠ topical+event gating.
2. **Graphiti hard eviction** — spike at >10k nodes or >500ms query. Warn/halt ≠ eviction.

## Apply protocol

Full procedure: `references/apply-protocol.md`. Update every affected surface. HIGH script/config/SOUL.md needs an adversarial net-positive check. Blocked user-owned skills: record + `hermes curator adopt <name>`. Triage with arXiv API titles (HTML index-pairing mislabels). Skill-doc ≠ implementation.

## Reference files

- `references/technique-classes-sweep-11-20.md` — Sweeps 11–20 technique classes
- `references/technique-classes-sweep-16-17.md` — Sweeps 16–17 technique classes
- `references/technique-classes-sweep-18-29.md` — Sweeps 18/24/27–29 technique classes
- `references/blocked-patches-historical.md` — Closed blocked-patch log
- `references/apply-protocol.md` — Full-surface apply map
- `references/sweep-source-config.md` — Source list, noise pitfalls, CS domain filters
- `references/sweep-19-gap-audit.md` — Code-reality gap audit
- `references/sweep-29-implementation-notes.md` — Config-append nesting, am-sentry wiring
- `references/sweep-8-10-index.md` — Sweeps 8–10
- `references/sweep-11.md` — Sweep 11
- `references/sweep-12.md` — Sweep 12
- `references/sweep-12-index.md` — Sweep 12 index
- `references/sweep-13.md` — Sweep 13 (canonical; home-path copy is gone)
- `references/sweep-21-in-progress.md` — Sweep 21
- `references/sweep-22-index.md` — Sweep 22
- `references/sweep-26.md` — Sweep 26
- `references/sweep-27.md` — Sweep 27
- `references/sweep-28.md` — Sweep 28
- `references/sweep-29.md` — Sweep 29
- `references/sweep-30.md` — Sweep 30
- `references/sweep-30-synthesis-pitfalls.md` — Sweep 30 synthesis pitfalls
- `references/sweep-31.md` — Sweep 31
- `references/sweep-32.md` — Sweep 32
- `references/sweep-33.md` — Sweep 33 (Sep 9 2026 HIGH apply + MED log)
- `references/sweep-implementation-pitfalls.md` — Sweeps 23–28 pitfalls
