---
name: hermes-research
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
description: >
  Use when: Configuring, reviewing, or applying findings from the Hermes Research sweep — the recurring
  multi-source multilingual sweep across the 7 core AI-agent improvement categories
  (reasoning/planning, tool-use, memory, multi-agent, evaluation, self-improvement, agentic-RAG).
  NOT for math/theory categories (use hermes-math-research). NOT for CS topics (use hermes-cs-research).
  NOT for checking/re-running pipeline jobs or dispatching the apply job (use hermes-research-ops).
triggers:
  - hermes research
  - hermes-research
  - configure the research sweep categories or sources
  - review agent-category research findings to apply
  - what's new in agent research
  - research improvements for agents like Hermes
  - AI agent research categories sweep
  - which agent-category papers should Hermes apply
  - update Hermes from latest research
  - NOT for one-off arXiv paper lookup (use arxiv skill)
  - NOT for domain research on non-agent topics (use domain-research-synthesis)
  - NOT for recording/querying individual sweep findings (use arxiv-sweep-findings)
  - NOT for applying findings to skill patches (use trajectory-research-synthesis-to-skills)
  - NOT for deep-diving agent memory research specifically (use llm-agent-memory-pipeline-research)
  - NOT for math/theory categories 8-51 (use hermes-math-research)
  - NOT for CS systems/engineering research (use hermes-cs-research)
  - NOT for math paper findings/spikes (use hermes-math-sweep-findings)
metadata:
  hermes:
    tags: [research, arxiv, agent, self-improvement, sweep, multilingual, pipeline]
    related_skills:
      - arxiv
      - arxiv-sweep-findings
      - hermes-research-ops
      - hermes-math-research
      - hermes-math-sweep-findings
      - hermes-cs-research
      - hermes-cs-sweep-findings
      - trajectory-research-synthesis-to-skills
      - llm-agent-memory-pipeline-research
      - domain-research-synthesis
      - academic-literature-review
      - self-improve-agent
      - skillopt-continuous-improvement
related_skills:
  - arxiv
  - arxiv-sweep-findings
  - trajectory-research-synthesis-to-skills
  - llm-agent-memory-pipeline-research
  - self-improve-agent
  - math-cs-applicability-reasoning
  - transfer-applicability-chain
---

# Hermes Research

The Hermes Research pipeline is the recurring academic sweep that keeps Hermes
informed of the latest findings across the 7 canonical AI-agent improvement categories.
It runs weekly and feeds directly into skill patches and system improvements.

## Research Categories (7 core, consolidated Sep 2026)

See hermes-research-sweep.py CATEGORIES dict for full arXiv query lists.

CORE AGENT (1-7) — this skill owns these categories
  1. Reasoning + Planning
  2. Tool Use / Function Calling
  3. Memory Architecture
  4. Multi-Agent Systems / Collaboration
  5. Agent Evaluation / Benchmarking
  6. Agent Evolution / Self-Improvement
  7. Agentic RAG / Context Management

Math categories (8-51): see hermes-math-research
CS systems/engineering categories: see hermes-cs-research

## Pipeline Flow

```
[cron: hermes-research-weekly]
        |
        v
hermes-research-sweep.py (no_agent=True)
  - arXiv listings (all unique arxiv_cats across 98 categories — deduped)
  - arXiv HTML search (7 core categories x 5 queries each)
  - Semantic Scholar API (7 core categories x 5 queries)
  - OpenAlex (top 2 queries per category, citation-ranked)
  - Crossref (top query per category, DOI-backed)
  - HAL / French: 25 queries
  - AMiner / Chinese: 15 queries
  - J-STAGE / Japanese: 8 queries
  - CyberLeninka / Russian: 20 queries
  - arXiv Korean institution search: 3 queries
  - HuggingFace Papers trending: 20 results
  - Papers With Code trending: 20 results
        |
        v (only if new papers found; silent tick otherwise)
Output: ~/.hermes/cache/research/hermes-research-latest.json
Digest: printed to stdout -> delivered by cron system
        |
        v
[cron: hermes-research-apply] (context_from sweep job)
  - Loads hermes-research-latest.json
  - Triages findings by relevance to each of the 7 categories
  - HIGH: implements patches to relevant skills immediately
  - MED: records in arxiv-sweep-findings for next review
  - LOW: logs skip note only
  - Calls trajectory-research-synthesis-to-skills for implementation
  - Calls adversarial-review for coherence check on any patches
        |
        v
[cron: pending-improvements-review] (weekly, context_from apply job)
  - Incorporates research findings into weekly improvement session
```

## Running Manually

```bash
# Dry run (no cache writes, no file writes):
python3 ~/.hermes/scripts/hermes-research-sweep.py --dry-run

# Force output even if no new papers:
python3 ~/.hermes/scripts/hermes-research-sweep.py --force

# Full run:
python3 ~/.hermes/scripts/hermes-research-sweep.py
```

## Triggering Apply Manually

After running the sweep, load findings and apply:

1. Load skill: skill_view(name='trajectory-research-synthesis-to-skills')
2. Read output: read_file('~/.hermes/cache/research/hermes-research-latest.json')
3. Triage by category (HIGH/MED/LOW)
4. Apply HIGH findings to relevant skills via skill_manage
5. Record MED findings in arxiv-sweep-findings
6. Run adversarial-review on all patches
7. Call verification-before-completion before declaring done

## Apply Cross-Review Gate (from AutoResearch, arXiv:2608.17906)

Before implementing any HIGH finding, route it through a second model for independent
verification. This is the 'cross-review' pattern from AutoResearch: multi-model generation
+ cross-review produces more grounded, hallucination-resistant implementations.

Pattern in the apply job:
  1. First model triages and proposes implementation.
  2. Second model (adversarial-review skill) independently reviews the proposed patch:
     - Does the paper actually support this change?
     - Is the target correct (skill vs script vs config)?
     - Does the patch introduce risk?
  3. Only apply if cross-review passes.

Also: during triage, explicitly ask 'what is the transferable mechanistic insight?' before
implementing. Papers often have a general pattern that applies beyond their stated domain.

Reference: arXiv:2608.17906 AutoResearch, Ren et al., Aug 2026.

## Apply Target Surface

Research findings can land on ANY of these targets — not just skills.
For each HIGH paper, identify which targets are affected and update all of them.

### 1. Skills (~/.hermes/skills/)
Procedural knowledge — workflows, pitfalls, commands, routing.
Use skill_manage(patch) via trajectory-research-synthesis-to-skills.
Examples: new benchmark prompting technique -> reasoning_planning skill;
new memory retrieval method -> hermes-memory-surface-selection skill.

### 2. Runtime Scripts (~/.hermes/scripts/)
Executable tools that run as part of cron or agent pipelines.
Use patch/write_file directly on the script.
Targets by subsystem:
  l1-extract.py          — memory extraction pipeline (new extraction heuristics)
  l1-promote.py          — memory promotion logic (new scoring/retention signals)
  l1-tracegrant.py       — memory provenance tracking
  memory-ttl-purge.py    — TTL/retention policy
  working-memory.py      — working memory / plan-from-memory logic
  critique-bank.py       — failure critique injection
  tool-auth-gate.py      — tool output trust classification
  skill-state.py         — long-task state tracking
  skill-wiki.py          — per-skill knowledge accumulation
  hermes-research-sweep.py — the sweep itself (new sources, query strategies)
  omni_skill_scan.py     — skill routing / omni index
  skill-router-index.py  — skill semantic routing
  gepa_skill_eval.py     — GEPA optimization loop
  skillopt_score.py      — skill quality scoring

### 3. Config (~/.hermes/config.yaml)
Runtime knobs: compression thresholds, max_turns, model routing,
curation intervals, memory TTLs, security toggles.
Use patch directly on ~/.hermes/config.yaml (always take a .bak first).
Examples: new evidence on optimal context compression ratio -> compression.target_ratio;
new evidence on cron agent safety -> agent.max_turns for cron jobs.

### 4. Memory Pipeline
The l1-* script chain and hindsight stack. Changes here affect every session.
Targets: l1-extract.py (what gets extracted), l1-promote.py (what gets retained),
l1-tracegrant.py (provenance), memory-ttl-purge.py (TTL policy),
hindsight-reembed.py (embedding/retrieval strategy).
High bar: changes must have strong evidence and pass adversarial review.

### 5. Hooks (~/.hermes/hooks/)
Pre/post tool-call hooks that enforce policy at the harness layer.
Examples: new injection attack patterns -> add to tool-auth-gate hook;
new PII patterns -> add to redaction hook.
Use read_file + patch on hook files.

### 6. Cron Jobs (~/.hermes/cron/)
Schedule changes, new watchdog jobs, frequency adjustments.
Use hermes cron edit/add commands or patch on cron job configs.
Examples: new evidence on sweep frequency optimal interval -> adjust research cron schedule;
new maintenance pattern -> add a new no_agent watchdog script.

### 7. SOUL.md (~/.hermes/SOUL.md)
Agent values, persona, core operating principles.
Extremely high bar — only findings that directly inform agent identity/values.
Examples: new evidence on agent safety/alignment norms.
Use patch directly; never overwrite.

### 8. Budget Policy (~/.hermes/budget-policy.yaml)
Per-task token/cost budgets and escalation policy.
Examples: new evidence on optimal model routing by task class.

### 9. System Prompt / Persona layer
Findings that inform the static persona prefix (persona_execution_split).
Only operator-level policy changes. Very high bar.

## Triage Protocol (HIGH / MED / LOW)

  HIGH  — directly implementable signal with clear Hermes target;
           implement immediately; run adversarial review on patch.
  MED   — useful but needs more evidence, or target is high-risk;
           log to arxiv-sweep-findings for next review session.
  LOW   — interesting but no actionable Hermes change; log skip note.

## Recursive Pass Rule (MANDATORY)

A single triage + implement pass is NOT sufficient. After each implementation
wave, recurse until the wave produces zero new HIGH candidates:

  WAVE 1: Triage all candidates. Implement HIGHs. Resolve adversarial findings.
  WAVE 2: Re-examine all SKIPs and DEFERs with the new implementations as context
           (some SKIPs become viable once earlier pieces exist). Also:
           - Fetch full paper text (not just abstract) for every WAVE 1 HIGH paper
             and check its reference list for cited work not yet in the sweep.
           - Re-run math/CS interpreters at full --limit (NOT --limit 30): the
             default 30-paper cap hits ~6% of available papers; use --limit 200
             or omit --limit entirely. Also verify the CS sweep file is not stale
             (flag if >48h old — re-run cs-paper-interpreter.py before triaging).
           - Check whether adversarial fixes opened new implementation surface.
  WAVE N: Repeat until a full wave produces zero HIGH candidates.
  DONE:   Only then run the final adversarial pass + cohesiveness audit.

Never declare research saturation after wave 1. A zero-HIGH wave is the only
valid stopping condition.

### Math/Algorithm Contributions in Agent Papers

Agent papers (cats 1-7) occasionally contain a secondary math or algorithmic
contribution (a bound, algorithm, or heuristic) alongside the primary agent result.
When this occurs:

  1. Triage the agent contribution as normal (HIGH/MED/LOW by category relevance).
  2. For the secondary math/algorithm contribution, load and run the full
     applicability chain:
       skill_view(name='math-cs-applicability-reasoning')
     This produces an independent OPTIMIZATION/SPIKE/SKIP verdict for that contribution.
  3. Record the agent verdict in arxiv-sweep-findings. Record the secondary
     math/CS verdict in hermes-math-sweep-findings (math) or hermes-cs-sweep-findings
     (CS), with a cross-reference note to the arxiv entry and flagged as
     'secondary-contribution: do not action independently of arxiv entry.'

Do NOT run the full chain on every agent paper — only when a paper has a
non-trivial secondary algorithm or bound that warrants separate evaluation.

Minimum bar for 'non-trivial': the secondary contribution has its own named
section in the paper AND either (a) includes pseudocode or a formal definition,
or (b) is independently evaluated in an experiment. A passing mention or a
standard baseline technique is not non-trivial.

## Math Research

Math/theory categories (8-51) run in a separate pipeline with their own seen-papers cache.
  Sweep + interpretation: hermes-math-research
  Findings/spikes bank:   hermes-math-sweep-findings

CS systems/engineering topics: hermes-cs-research / hermes-cs-sweep-findings

## Handoff to Apply Job

The apply cron job receives the sweep output via context_from. The apply prompt is:

  "Load ~/.hermes/cache/research/hermes-research-latest.json. Triage new papers
  by category against the 7 core Hermes research categories (cats 1–7 only).
  Math/theory categories 8–51 are handled by hermes-math-research; CS systems
  categories are handled by hermes-cs-research — do not re-triage those here.

  For each HIGH-relevance paper:
    1. Check for secondary math/algorithm contributions (see Math/Algorithm
       Contributions section above). If present, run the applicability chain
       (skill_view(name='math-cs-applicability-reasoning')) for that contribution
       before extracting implementation signals. Record chain verdict in
       hermes-math-sweep-findings (math bound/algorithm) or hermes-cs-sweep-findings
       (CS technique), with a cross-reference note to the cat-1-7 arxiv entry.
    2. Extract the implementation signal: what specifically should change in Hermes?
    3. Identify ALL affected targets: skills / runtime scripts / config / memory
       pipeline / hooks / cron / SOUL.md / budget-policy.yaml (see hermes-research
       skill Apply Target Surface section for the full list and per-target rules).
    3. Apply patches to every affected target using the correct tool for each:
       - Skills: skill_manage via trajectory-research-synthesis-to-skills
       - Scripts: patch/write_file on ~/.hermes/scripts/<name>.py
       - Config: patch on ~/.hermes/config.yaml (take .bak first)
       - Hooks: patch on ~/.hermes/hooks/<name>
       - Cron: hermes cron edit/add
       - SOUL.md: patch on ~/.hermes/SOUL.md (very high bar)
    4. Run adversarial-review on every patch before finalizing.

  For MED: add to arxiv-sweep-findings.
  For LOW: log skip note only.

  RECURSIVE PASS (mandatory): After implementing all WAVE 1 HIGHs and resolving
  adversarial findings, run a second triage wave:
    - Re-examine all SKIP/DEFER candidates with new implementations as context.
    - Fetch full paper text for every WAVE 1 HIGH and check its reference list
      for papers not yet in the sweep.
    - Re-run math/CS interpreters at full --limit (>=200, not the default 30).
    - Verify CS sweep file freshness (>48h stale = re-run before triaging).
    - Check whether adversarial fixes exposed new implementation surface.
  Repeat waves until a full wave produces zero new HIGH candidates.
  Only then finalize the apply report.

  Write apply-report to ~/.hermes/cache/research/hermes-research-apply-latest.md
  including: paper, signal extracted, targets patched, adversarial verdict,
  wave count, and reason saturation was reached (zero-HIGH wave).

  Load skills: hermes-research, trajectory-research-synthesis-to-skills,
  arxiv-sweep-findings, adversarial-review, verification-before-completion,
  hermes-system-audit, hermes-operating-pattern, math-cs-applicability-reasoning."

## Output Files

  ~/.hermes/cache/research/hermes-research-latest.json   (always current)
  ~/.hermes/cache/research/hermes-research-YYYY-MM-DD.json (dated archive)
  ~/.hermes/cache/research/hermes-research-apply-latest.md (apply job report)
  ~/.hermes/cache/research/seen_papers.json (rolling dedup cache, max 2000)

## Multilingual Source Notes

  HAL: French/EU academic papers. Query in French for better recall.
  AMiner: Chinese AI/CS. Reliable for Chinese institutional authors.
         Low yield for very recent papers (48h+ lag).
  J-STAGE: Japanese. Low yield for agent-specific queries (small domain).
           Best for NLP/robotics adjacent queries.
  CyberLeninka: Russian OA journals. Mix Russian + English queries.
               Lower quality signal; use for completeness, not primary triage.
  CNKI: Paywalled. Use arXiv search with Chinese institution names instead
        (e.g. "Peking University" OR "Tsinghua" agent memory 2026).

## Skill Write Ownership (Class H safety)

  hermes-research skill  -> read/routing only, no skill_manage writes
  trajectory-research-synthesis-to-skills -> owns skill_manage writes
  self-improve-agent     -> human-gated proposals only
  skillopt-continuous-improvement -> scoring only, no writes
  runtime-skill-synthesis -> crystallize/merge/promote only

Never call skill_manage directly from this skill. Route all writes through
trajectory-research-synthesis-to-skills.

## Stage 3 — Theorem/Technique-to-Implementation Ideation

Both math-paper-interpreter.py and cs-paper-interpreter.py implement a Stage 3 pass on full-chain SKIPs. After Stage 2 rules out a direct component match, Stage 3 asks haiku: "what Hermes artifact could embody this paper's mathematical structure?"

Output files:
  ~/.hermes/cache/research/math-ideas-queue.json   (math papers, append-deduped)
  ~/.hermes/cache/research/cs-ideas-queue.json     (CS papers, append-deduped)

Each idea has: math_structure, hermes_artifact, artifact_type (script/skill/config/cron), implementation_sketch, hermes_benefit, source_title, source_category, source_url.

Triage ideas the same way as spikes: score by concreteness (script > skill, longer sketch = more concrete), dedupe by artifact name (case-insensitive), discard network/GPU/RL-training-adjacent entries. Top ideas become implementation targets after the spike/optimization queue is clear.

## Feasibility Gate — Infrastructure-Buildable Rule (standing user preference)

Applies to ALL paper interpreters (math, CS, agent categories). The feasibility gate ABSOLUTE blockers are narrow:
  (a) Gradient computation / backpropagation / weight updates
  (b) Direct model weight or activation access
  (c) Continuous per-turn training signal

Do NOT fire SKIP for: iterative algorithms, state accumulation, scoring functions, graph/eigenvalue computation, bandit state tracking, discrete structures, scheduling policies. Hermes can build infrastructure (Python, SQLite, numpy, cron) for all of these. "Requires iterative state" is a build task, not a blocker.

When calibrating pre-filter prompts: include an explicit positive statement "Do NOT skip for: iterative algorithms, state accumulation, scoring functions, graph computation, bandit state — we can build infrastructure for these." Prompts that only list SKIP criteria without this positive statement will over-fire on Track B papers.

## Research Category Gap Identification

When asked to survey the knowledge corpus for missing research categories, use this procedure.
A gap is a math/theory field with (a) clear structural analogy to a Hermes component, and
(b) no existing sweep category covering it.

Step 1: Extract existing categories.
  python3 -c "
  import re; content = open('/var/home/rainbow/.hermes/scripts/hermes-research-sweep.py').read()
  for k, label in re.findall(r'\"([a-z_]+)\"\s*:\s*\{[^}]*\"label\"\s*:\s*\"([^\"]+)\"', content, re.DOTALL):
      print(f'{k:<45} {label}')
  "

Step 2: Map existing categories against candidate fields. For each candidate field ask:
  - Does Hermes have a named component with analogous structure? (required)
  - Is the application concrete (a specific script, routing table, or scoring formula)?
  - Is the field not already covered by an existing category or partially by two categories?

Priority tiers:
  HIGH — concrete Hermes target exists with no current mitigation; field provides certificates
         or guarantees the current heuristic lacks (e.g. Lyapunov for loop stability, OT for
         KG drift, tropical algebra for min-cost routing)
  MED  — useful but existing categories partially cover it, or application is speculative
  LOW  — implementation-level or already handled ad-hoc; skip

Step 3: For each HIGH/MED gap, add to hermes-research-sweep.py CATEGORIES dict with:
  - 5 targeted arXiv keyword queries (include "2025 2026" for recency)
  - arxiv_cats list (use math.* and cs.* arXiv taxonomy codes)
  Then add to math-paper-interpreter.py MATH_CATS set and COMPONENT_MAP.
  Then update hermes-math-research SKILL.md category list and component map section.

Pitfall: use patch tool directly on absolute file paths for default-profile skills —
skill_manage refuses writes when running as a non-default profile (e.g. fork profile).
The error message names the profile mismatch explicitly.
