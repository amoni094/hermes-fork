# Agent Skill Management: Research Knowledge Bank (2026)

Condensed findings from a July 2026 literature sweep (arXiv, Semantic Scholar).
Covers pruning, routing, composition, hierarchy, resurrection, and quality metrics.
Use when advising on skill library design or implementing any of these techniques.

---

## 1. Pruning & Redundancy Removal

### AgentPrune — Communication Redundancy Pruning
**arXiv:2410.02506, ICLR 2025** | https://github.com/yanweiyue/AgentPrune

Models agent message flows as a **spatial-temporal message-passing graph** and performs
one-shot pruning on it — first formal definition of "communication redundancy."
- Spatial dimension → which skills co-depend on each other
- Temporal dimension → which invocation steps can be skipped
- Directly maps to skill co-activation graph pruning for skill libraries

### ToolScope — Tool Merging + Context-Aware Filtering
**arXiv:2510.20036, ACL 2026**

Two components:
- **ToolScopeMerger**: LLM audits semantic overlap, proposes merges, self-corrects via verifier
- **ToolScopeRetriever**: ranks and selects top-K tools per query to stay within context window

Result: **8–38% gain** in tool selection accuracy across 3 LLMs and 3 benchmarks.

**Merge threshold:** cosine similarity > 0.92 between skill description embeddings.

### Four-Tier Pruning Decision Matrix
| Tier | Condition | Action |
|------|-----------|--------|
| Archive | Zero invocations 90d AND semantic substitute exists (cos > 0.80) | Disable |
| ACTIVE_DORMANT | Zero invocations BUT no semantic substitute | Preserve with keyword triggers |
| Merge | Two skills with cos_sim > 0.92 on descriptions | LLM-audited merge proposal |
| Delete | Semantic duplicate exists AND outcome-weighted usage is negative | Hard delete |

**Capability guard:** never disable a skill if no substitute exists with cos_sim > 0.80.

---

## 2. Skill Routing

### VOYAGER — Foundational Skill Library Architecture
**arXiv:2305.16291, NeurIPS 2023** | https://voyager.minedojo.org

Skills stored as executable code. Retrieval: embed descriptions, cosine similarity at query
time, top-5 retrieved. Skills include **self-verification steps** returning binary pass/fail —
used for quality tracking. Iterated prompting on failure to improve skills in-place.

### SkillRouter — Full-Text Routing at Scale
**arXiv:2603.22455, Mar 2026** | https://github.com/zhengyanzhao1997/SkillRouter

**Critical finding:** hiding skill body (showing only name+description) causes a
**31–44 pp drop** in routing accuracy at 80K-skill scale. Full SKILL.md text is the
critical routing signal, not just metadata.

Architecture: BM25 sparse retrieval over full skill text → 1.2B dense reranker over top-100.
- 74.0% Hit@1 on ~80K skills
- 13× fewer params than prior SOTA; 5.8× faster
- Routing gains transfer to improved task success in end-to-end coding agent evals

**Hermes threshold:** Full-text BM25 over SKILL.md bodies is sufficient at ≤500 skills.
Add the 1.2B reranker checkpoint from SkillRouter GitHub when registry grows beyond ~500.

**Reject option (from Toolken+, arXiv:2410.12004):** if top-1 retrieved skill scores
< 0.65 cosine similarity, do NOT inject any skill — let the LLM reason unaided.
This prevents irrelevant skill bodies from confusing the model.

---

## 3. Tool Selection Approaches (Toolken / ToolLLM)

### ToolkenGPT / Toolken+
- **ToolkenGPT (arXiv:2305.11554, NeurIPS 2023):** Each tool = a learnable embedding token.
  Not directly applicable to prompt-only agents — requires fine-tuning the embedding layer.
- **Toolken+ (arXiv:2410.12004, 2024):** Adds top-k reranking using tool documentation +
  a "Reject" option so the model falls back to bare generation when no tool is appropriate.
  The reject option IS directly applicable as a confidence threshold in routing.

### ToolLLM / ToolBench
**arXiv:2307.16789, ICLR 2024 Spotlight** | https://github.com/OpenBMB/ToolBench

16K real-world APIs, auto-constructed via ChatGPT. Key technique: **DFSDT** (Depth-First
Search Decision Tree) explores multiple tool-call paths and backtracks on failure.

CLI adaptation: when a task fails with skill-A, automatically try the second-best retrieved
skill before surfacing failure to the user.

---

## 4. Self-Organizing Skill Hierarchies

### Drop the Hierarchy
**arXiv:2603.28990, Mar 2026**

25,000-task experiment across 8 models, 4–256 agents, 8 coordination protocols. Agents
given only mission + communication protocol spontaneously formed **better structures than
pre-designed hierarchies.** Produced 5,006 unique emergent roles from just 8 agents.

Implication for skill categories: LLM-induced re-clustering (monthly) beats static
curator-imposed categories. Run taxonomy induction monthly; use divergence to flag refactors.

```
Taxonomy induction prompt:
"Given these skill descriptions, cluster them into 5-10 coherent categories.
For each: name it, describe when it applies, list members, flag cross-category spans.
Return JSON: [{"category": str, "trigger_patterns": [str], "members": [str]}]"
```

### Agent Skills Survey — Four-Stage Lifecycle
**arXiv:2605.07358, May 2026** | https://github.com/JayLZhou/Awesome-Agent-Skills

Canonical four lifecycle stages: **Representation → Acquisition → Retrieval → Evolution**
Open challenges: quality control, interoperability, safe updating, long-term capability management.

### Agent Skills Architecture + Security Survey
**arXiv:2602.12430, AgentSkills'26 Workshop**

Key security finding: **26.1% of community-contributed skills contain vulnerabilities.**
Proposes a four-tier, gate-based permission model mapping skill provenance to deployment caps.

---

## 5. Skill Composition Patterns

### SkillComposer — Generative Skill Composition
**arXiv:2606.32025, Jun 2026**

Formalizes composition as **task-conditioned ordered-sequence prediction** over skill indices.
Which skills, how many, and what order are a **joint decision** — cannot be decoupled.

Results: +23.1 pp (GPT-5.2-Codex), +18.2 pp (Gemini-3-Pro-Preview) over no-skill baseline,
matching gold upper bound at lower prompt-token cost.

### Five Composition Patterns
| Pattern | Structure | Example |
|---------|-----------|---------|
| Sequential Pipeline | A outputs → B inputs | `arxiv` → `obsidian-research-ingestion` |
| Parallel Gather-Merge | A ‖ B → merge | `web_search` ‖ `arxiv` → synthesize |
| Guard + Execute | A validates → B executes | `verification-before-completion` → `finishing-a-branch` |
| Fallback Chain | A → fail → B → fail → bare LLM | `firecrawl-research` → `web_extract` → `web_search` |
| Critic Loop | A generates → B criticizes → A revises | `claude-code` → `requesting-code-review` → fix |

### SkillComposer (companion paper) — Learning to Evolve Agent Skills
**arXiv:2606.06079, Jun 2026** (distinct paper, same "SkillComposer" name as 2606.32025 above —
do not conflate; this one is about skill *construction/evolution*, the other about *selection order*)

Decomposes skill construction into three learnable operations: **create, improve, merge** —
trained via rejection sampling. Addresses the tension that a task-specific skill fails to
transfer while an abstracted skill under-specifies. Three deployment modes: offline (build a
generalized library), online (task-specific refinement), hybrid.
- Results: SkillComposer-4B improves a 27B executor by +4.5 on agent tasks (τ²-Bench, AppWorld),
  +3.4 on code tasks (LiveCodeBench v6); generalizes to unseen domains/task types.
- Key finding: merge and improve address *orthogonal* quality dimensions (not redundant) —
  skill composition itself is a transferable meta-ability, not task-specific.
- **Hermes relevance**: directly validates the existing `self-improve-agent` create/patch loop —
  independent confirmation that create+improve+merge (not just create) is the right operation
  set for skill lifecycle management. The "orthogonal dimensions" finding suggests Hermes should
  track merge-worthiness and improve-worthiness as separate signals rather than one quality score
  — current `agent-skill-management-research-2026.md` Composite Quality Score (Section 7) collapses
  both into one Q value; consider splitting into Q_merge (redundancy/overlap) and Q_improve
  (task-fit gap) if skill count grows enough to need finer-grained triage.

### Composition Discovery (co-activation mining)
```python
from itertools import combinations
from collections import defaultdict

def find_composition_candidates(session_logs, threshold=5):
    co_occur = defaultdict(int)
    for session in session_logs:
        for a, b in combinations(session["skills_loaded"], 2):
            co_occur[(a, b)] += 1
    return [(a, b, n) for (a, b), n in co_occur.items() if n >= threshold]
```

---

## 6. Dead-Skill Resurrection Criteria

### SkillsVote — Evidence-Gated Lifecycle Governance
**arXiv:2605.18401, May 2026**

Profiles skills for quality, verifiability, and environment requirements. After execution,
decomposes trajectories into skill-linked subtasks and attributes outcomes to four sources:
skill-guided execution / agent exploration / environment effects / final result signals.

**Evidence-gated resurrection:** only re-enable a disabled skill when:
1. New tasks arrive where the **active set fails**, AND
2. The disabled skill's description matches the task (cosine > 0.70)

### SkillRevise — Trace-Conditioned Skill Revision
**arXiv:2606.01139, May 2026**

Diagnoses skill defects from execution evidence, retrieves repair principles from a memory
bank, applies execution-anchored edits. Raises success rate **36% → 62%** on SkillsBench.

**Resurrection from behavioral failure:** apply SkillRevise (≤3 revision iterations) before
re-enabling. If still failing after 3 iterations → keep disabled, file for rewrite.

### Resurrection Decision Logic (compact)
```
Is the skill's domain still relevant?
  No  → Stay disabled. Review in 6 months.
  Yes:
    Disabled for behavioral failure
      → SkillRevise first; re-enable only if verifier passes
    Disabled for zero usage
      No semantic substitute → RE-ENABLE as ACTIVE_DORMANT with trigger keywords
      Substitute exists     → Merge proposal or keep disabled
    Superseded by newer skill
      → Paired eval; if old skill wins on ≥1 task type → keep both (niche value)
New task arrives, active set fails, disabled skill matches (cos > 0.70)
  → TEMPORARY RESURRECTION for this task
```

---

## 7. Skill Quality Metrics

### SkillsBench — Empirical Quality Findings
**arXiv:2602.12670, Feb 2026** | https://www.skillsbench.ai

87 tasks, 8 domains, 18 model-harness configurations. Key empirical findings:
- Skills raise avg pass rate **33.9% → 50.5%** (+16.6 pp)
- **Focused skills with ≤ 3 modules outperform larger/exhaustive bundles**
- Smaller models + skills can match larger models without skills

### Outcome-Oriented Evaluation (11-Metric Framework)
**arXiv:2511.08242, Nov 2025**

Most useful per-skill metrics:
- **Goal Completion Rate (GCR):** paired eval — with-skill vs without-skill pass rate delta
- **Autonomy Index (AIx):** user interventions/corrections when skill was loaded
- **Multi-Step Task Resilience (MTR):** recovery rate when skill-triggered error occurred

### Composite Quality Score
```
Q = 0.35 × task_success_rate
  + 0.25 × (1 - user_correction_rate)
  + 0.20 × routing_precision          # how often retrieved skill was actually used
  + 0.10 × (1 / max(module_count, 1)) # brevity bonus: ≤3 modules is ideal
  + 0.10 × recency_decay              # decays with days since last invocation
```
Skills with Q < 0.3 → surface for curator review. Track in per-skill `SKILL_METRICS.json` sidecar.

### User Correction Rate — Detection Signals
- **Explicit:** user says "no, use X instead" / "that skill wasn't helpful"
- **Implicit:** user re-issues task without loading the recommended skill
- **Patch signal:** user calls `skill_manage(action='patch')` immediately after skill was used
- Log to: `.hermes/skill_telemetry.jsonl`
  `{"ts": "...", "skill": "name", "event": "user_rejected", "session": "id"}`

---

## Source Reference Table

| Paper | arXiv ID | Venue | Year |
|-------|---------|-------|------|
| AgentPrune | 2410.02506 | ICLR 2025 | 2024 |
| ToolScope | 2510.20036 | ACL 2026 | 2025 |
| VOYAGER | 2305.16291 | NeurIPS 2023 | 2023 |
| SkillRouter | 2603.22455 | — | 2026 |
| ToolkenGPT | 2305.11554 | NeurIPS 2023 | 2023 |
| Toolken+ | 2410.12004 | — | 2024 |
| ToolLLM | 2307.16789 | ICLR 2024 | 2023 |
| CREATOR | 2305.14318 | — | 2023 |
| Drop the Hierarchy | 2603.28990 | — | 2026 |
| Agent Skills Survey | 2605.07358 | — | 2026 |
| Agent Skills: Architecture | 2602.12430 | AgentSkills'26 | 2026 |
| SkillComposer | 2606.32025 | — | 2026 |
| SkillRevise | 2606.01139 | — | 2026 |
| SkillsVote | 2605.18401 | — | 2026 |
| SkillsBench | 2602.12670 | — | 2026 |
| Outcome-Oriented Eval | 2511.08242 | — | 2025 |
| EvoAgent | 2406.14228 | — | 2024 |
| SEAgent | 2508.04700 | — | 2025 |
| SkillReact | 2606.00448 | — | 2026 |
| SkillTV-Bench | 2608.05573 | — | 2026 |
| GenericAgent | 2604.17091 | — | 2026 |
| SkillTrace | 2608.02356 | — | 2026 |
| Canary Tools | 2608.04719 | — | 2026 |
| AgentSkill Survey 4-paradigm | 2606.11435 | — | 2026 |

---

## 9. SkillTrace: Query-Skill Graph Traversal for Composable Selection (arXiv:2608.02356, Aug 2026) ⭐ CODE

**SOTA on SkillsBench (53.17%), 91.43% ALFWorld.** Three-level graph traversal:
1. Compositional query hierarchy (decompose task into sub-queries)
2. Similarity → skill library (embed sub-queries, find matching skills)
3. Skill dependency propagation (if skill A is selected, propagate to required skill B)

**Key insight:** flat embedding search misses skill dependencies — a skill retrieved
for step 3 may require a skill that wasn't retrieved for step 1. The dependency
propagation layer fixes this by following explicit `requires:` relationships.

**Hermes implementation:** add a `requires: [skill-name, ...]` field to SKILL.md
frontmatter listing prerequisite skills. At skill-load time, resolve the dependency
graph and auto-load required skills. This prevents "skill A works but fails because
skill B's pitfalls weren't loaded" failures.

---

## 10. Canary Tools: 6-Type Tool Selection Failure Taxonomy (arXiv:2608.04719, Aug 2026) ⭐ CODE

**Canary Susceptibility Rate (CSR) varies 36x across models.** Six failure types:
| Canary type | Description | Model most affected |
|---|---|---|
| Semantic decoys | Similar-sounding tool with different purpose | Small models |
| Parameter traps | Tool with same name but wrong param signature | Small models |
| Capability mirages | Tool described as able to do X but cannot | Frontier models |
| Prerequisite blindness | Tool requires prior tool not selected | All models |
| Temporal decoys | Tool only valid in certain system states | Medium models |
| Granularity traps | Too-coarse or too-fine tool for the task | All models |

**Claude Opus 4.8 has lowest CSR** — frontier model advantage on capability mirages
(unrealistic tool descriptions) but not on prerequisite blindness.

**Hermes application:** plant canary probes in MCP tool schemas during development
testing. Specifically: add one "capability mirage" canary (tool described as doing X
but actually does Y) and one "prerequisite blindness" canary (tool that requires
`web_search` to have been called first) to verify Claude routes correctly.

---

## 11. AgentSkill Survey: 4-Paradigm Lifecycle + Dual-Rollout Eval (arXiv:2606.11435, Jun 2026) ⭐ CODE

Four skill evolution paradigms (apply in order of cost):
1. **Execution-feedback loops** — sparse signal, best for failure correction only
2. **Trajectory distillation** — curate across multiple runs, not individual traces
3. **Compression/augmentation** — annotate core steps as `protected_steps` before compression
4. **RL with reusable rewards** — highest cost; only for high-frequency, stable skills

**Dual-rollout evaluation protocol:** run the same benchmark task WITH and WITHOUT
each skill loaded; measure the accuracy delta as "skill contribution score". A
shrinking delta over time = the agent is bypassing the skill (reward hacking).
A negative delta = the skill is actively harming performance and should be flagged.

**`protected_steps` frontmatter field (add to critical skills):**
```yaml
protected_steps:
  - "Step 3: verify tool output before writing to memory"
  - "Step 7: contradiction check before memory write"
```
These steps are marked non-compressible in context compression — they survive
micro_compact even if surrounding context is evicted.

---

## 8. Compositional Safety (SkillReact, arXiv:2606.00448, May 2026)

211,575 individually-safe skill pairs from 1,520 ClawHub skills evaluated.
18.2% of flagged pairs contain genuine compositional risk (population-weighted validity).
Every flagged pair is individually safe — per-skill scanning misses all of them.

**Four pairwise risk patterns:**
| Pattern | Combined capability | Detection |
|---|---|---|
| Permission escalation | file-read skill + HTTP-write skill = data exfil | |
| Scope amplification | user-input skill + shell-exec skill = injection | |
| Authority confusion | role-impersonation skill + irreversible-action skill | |
| Confidentiality leak | env/key-read skill + external POST skill | |

**Threshold:** flag any skill pair where both patterns are co-present above.
Per-skill scans are insufficient — always check pairs when loading ≥2 skills.

**SkillTV-Bench (arXiv:2608.05573, Aug 6 2026):** trajectory-level benchmark for
skill use correctness. The right evaluation frame for compositional skill workflows
is trajectory success rate, not per-skill flag accuracy.
