# Agent Skill Architecture Research — 2026 Synthesis
*Condensed from August 2026 multilingual sweep. 27 verified arXiv sources. Full report: /tmp/skill-architecture-research-2026-08.md*

## MOST CRITICAL FINDINGS FOR HERMES

### R3: Flat retrieval degrades at 64–128 skills (TMLR survey, arXiv:2607.10113)
124-paper audit 2023-2026 by Yubo Li (CMU). Selection accuracy ~96-98% at 16-32 skills,
drops to **78% at 128, 64% at 256**. Hermes at 170 skills is in the degradation zone.
Structured retrieval (tree → DAG) is required at this scale.

### R6: Maintenance is load-bearing at moderate library sizes (AutoRefine, arXiv:2601.22758)
Without periodic prune+merge: pass rate 35.6%→31.1%, repository bloats **4.5×**,
skill utilization crashes 0.71→0.08. Maintenance cycles are survival, not cosmetic.

### The body-hiding problem (SkillRouter, arXiv:2603.22455)
Hiding the skill body (name + description only, no full SKILL.md text) causes
**31–44 pp drop** in routing accuracy vs. full-body retrieval at 80K skill scale.
This is exactly the condition Hermes is in with its 57-char description limit in the
system prompt index. Mitigation: add a `routing_signals` frontmatter field with
200-400 chars of task vocabulary not in the description.

### Focused libraries beat comprehensive ones (R5, multiple sources)
SWE-Skills-Bench: average gain only +1.2% across 49 public SWE skills. SkillX,
Wild-Skills, CASCADE, SkillMOO all find distractor load is the failure mechanism.
Pruning stale/low-utility skills improves the library more than adding new ones.

---

## THE TMLR LIFECYCLE SURVEY (arXiv:2607.10113)
**Yubo Li (CMU) — TMLR 2026. Companion: github.com/yubol-bobo/Awesome-Dynamic-Agent-Skills**

### Eight-Stage Lifecycle Architecture (applicable to Hermes curator design):
1. Evidence acquisition (trajectories, failures, user edits)
2. Proposal (Add/Refine/Merge/Split/Distill/Abstract)
3. **Verify & Admit** ← the GATE; most critical stage
4. Organize (topology & index: flat → tree → DAG → graph)
5. Retrieve & Compose
6. **Maintain & Repair** ← load-bearing at 100+ skills
7. Distill & Port (slow loop, cross-agent transfer)
8. Governance (provenance, rollback, lineage)

### Seven-Tuple Skill Formalism (adds to 4-tuple options framework):
`S = ⟨C, π, T, R, φ, ν, ≺⟩`
- φ = edit operator (how revisions are generated)
- **ν = verification predicate** (admission gate — most important addition)
- **≺ = lineage** (partial order for rollback/supersession)

### Seven Empirical Regularities (evidence-graded):
| Reg. | Strength | Finding |
|------|----------|---------|
| R1 | Strong | Curated skills > unverified self-generated. ASI: +23.5pp WebArena. |
| R2 | Strong | Verifier quality decisive in RL. CODE-SHARP: 24.3%→41.0% w/ learned gate. |
| R3 | Moderate | Flat retrieval degrades at ~64-128 skills. |
| R4 | Moderate | Larger gains for weaker backbone models. |
| R5 | Strong | Focused libraries > comprehensive. Distractor load is failure mechanism. |
| R6 | Strong | Maintenance load-bearing at moderate sizes. |
| R7 | Moderate | Write-time abstraction > read-time. SimpleMem: F1 43.24→31.29 w/o compression. |

---

## ROUTING BEYOND SKILLROUTER

### SkillRet — Retrieval Benchmark (arXiv:2605.05726, Korean institution, May 2026)
17,810 public skills, structured semantic tags. Task-specific fine-tuning: **+13.1 NDCG@10**
over strongest prior retriever, **+16.9** over off-the-shelf. The 2-level taxonomy
(6 categories / 18 sub-categories) outperforms Hermes's current 1-level (10 categories).

**SkillRet's 6-category taxonomy** (production-validated at 17K+ skills):
1. Code / Development  2. Data & Analysis  3. Communication & Content
4. Workflow & Automation  5. Domain-Specific  6. Infrastructure & DevOps

### AgentSkillOS — Capability Tree + DAG (arXiv:2603.02176, Mar 2026)
Tree-based retrieval approximates oracle selection at 200→200K scale.
DAG-based orchestration "substantially outperforms flat invocation with identical skill set."
Hermes already uses category trees. Missing: DAG-based multi-skill composition with
explicit dependency management. GitHub: ynulihao/AgentSkillOS

### Skill-RAG — 4-Skill Failure Taxonomy (arXiv:2604.15771, Apr→Jun 2026)
When retrieval fails, selects among 4 correction actions:
1. Query rewriting  2. Question decomposition  3. Evidence focusing  4. Exit (irreducible)
"Misalignment is typed rather than monolithic." Not directly applicable to black-box
models, but the 4-action taxonomy is implementable at prompt level.

---

## SKILL REPAIR & RESURRECTION

### Rethinking Self-Evolving Agent Skills (arXiv:2608.02636, HKUST KnowComp, Jul 2026)
42 runs across 14 model-benchmark settings:
- Evolution is sparse: only 55/388 candidates establish distinct validation bests
- **All 11 successful repairs used conditions including failed trajectories**
- Success-only feedback is insufficient for repair
- Test-time scaling (Parallel Sampling) cannot match persistent skill evolution on
  SpreadsheetBench (evolved: +32pp; Sequential Refinement: +0pp recovery)

**Key implication:** when a skill is loaded but task fails, that failure trace is the
most valuable repair input. Hermes has no structured failure log per skill currently.
Adding failure logging (session ID, task description, failure mode) would enable
targeted curator-driven repair — even lightweight logging would help.

---

## RECOMMENDED HERMES FRONTMATTER EXTENSIONS

Priority 1 — highest ROI, addresses 37-44pp routing accuracy drop:
```yaml
routing_signals: |
  Key phrases, task vocabulary, pitfall keywords not in the 57-char description.
  Indexed for retrieval without appearing in system prompt listing.
```

Priority 2 — lifecycle management for curator:
```yaml
lifecycle_stage: trusted     # experimental|trusted|deprecated|archived
invocation_cost: low         # low|medium|high (token cost estimate)
```

Priority 3 — composition structure (SkillX 3-tier model):
```yaml
skill_tier: functional       # strategic|functional|atomic
composes_with: []            # explicit composition hints
fallback_skills: []          # try these if this skill's approach fails
```

Priority 4 — lineage/governance:
```yaml
supersedes: []               # skills this replaces
failure_log_path: null       # path to failure trajectory log for repair
```

### Cross-linking discipline (currently inconsistent in Hermes):
- `related_skills` should be **bidirectional** — if A lists B, B must list A
- `composes_with` is non-symmetric (A composes with B doesn't require B→A)
- The skill_xref_audit.py script should be extended to check bidirectionality

---

## COMPOSITION PATTERNS

### SkillX — 3-Tier Hierarchy (arXiv:2604.04804, ZJU/zjunlp group, Apr 2026)
Raw trajectories → three-tier hierarchy:
1. **Strategic Plans** (goal-level) 
2. **Functional Skills** (reusable subroutines) ← analogous to current Hermes skills
3. **Atomic Skills** (execution-oriented patterns) ← sub-skill components
Enables cross-agent skill transfer. GitHub: zjunlp/SkillX

### Programmatic Tool Calling (arXiv:2608.06370, Aug 2026)
PTC (typed Python stubs, chained in code) beats JSON in 11/14 models.
GPT-5.6: **+10.6%** over JSON. Stable under "context rot" where JSON degrades 2.3%.
Code-based skill chaining is more robust than structured JSON invocations.

---

## SECURITY FINDINGS

- 26.1% of community-contributed skills contain vulnerabilities (arXiv:2601.10338, 31K analyzed)
- BadSkill: model-level backdoors embedded in skills survive normal vetting (arXiv:2604.09378)
- Proposed 4-tier governance (arXiv:2602.12430): Untrusted → Audited → Validated → Production
- Hermes `created_by:agent` flag approximates Tier 1 (untrusted). Tiers 2-4 absent.
- Currently Hermes does not import external SKILL.md packages — this is the right posture.

---

## SOURCES (all verified via direct arXiv abstract extraction, August 2026)
- TMLR lifecycle survey: arXiv:2607.10113
- SkillRouter (routing): arXiv:2603.22455
- SkillRet (retrieval benchmark): arXiv:2605.05726
- AgentSkillOS (tree+DAG): arXiv:2603.02176
- SkillX (3-tier KB): arXiv:2604.04804
- SkillMOO (multi-objective): arXiv:2604.09297
- SAGE (RL skill library): arXiv:2512.17102
- Rethinking Self-Evolving Skills: arXiv:2608.02636
- Skill-RAG (failure-state routing): arXiv:2604.15771
- AutoRefine (maintenance): arXiv:2601.22758
- Bitter Lesson Tool Calling: arXiv:2608.06370
- Agent Skills LLMs survey: arXiv:2602.12430
- AgentSkills-Wild (vulnerability): arXiv:2601.10338

---

## ADDENDUM — Aug 2026 Research Session (2026-08-10)

New papers not in the original sweep above.

### Scaling Laws of Skills — Logarithmic Routing Decay (arXiv:2605.16508, May 2026)

Evolvent AI. 15 frontier LLMs, 1,141 skills, 3M+ routing decisions.
GitHub: https://github.com/evolvent-ai/skill-laws

**Adds quantitative specificity to R3 above:**
- Routing accuracy decays logarithmically with R²>0.97 across all 15 models
- At 170 skills: unoptimised accuracy can drop to **18.3%** with 0% hallucinations —
  the model stays inside the library but routes to the wrong skill
- Black-hole skills (over-broad) create **22.4% hijack rate**
- Three failure stages: local competition → cross-family drift → black-hole capture
- Law-guided optimisation: 71.3% → **91.7%** accuracy; hijack 22.4% → **4.1%**
- Downstream: ClawBench 49.3% → **61.6%**, ClawMark 28.4% → **34.5%**

**Actionable:** add `scope: [category_list]` frontmatter to pre-filter routing pool;
audit any skill with >5% capture rate that shouldn't have it (black-hole candidate).

### SkillReducer — Body and Description Optimisation (arXiv:2603.29919, Jun 2026)

Gao et al. Analysis of 55,315 public skills.

- **26.4% of skills** have no routing description → blind full-body evaluation
- **>60% of skill body** content is non-actionable (background, examples, boilerplate)
- Progressive disclosure: 39% body compression + 2.8% quality gain (less-is-more)

**Reinforces the "routing_signals" approach already in this file AND adds body-structure:**
- Split SKILL.md into `## Core` (≤300 tokens, always injected) + `## Detail` (on-demand)
- Audit command: `grep -rL "^description:" ~/.hermes/skills/**/*.md`

### SkillDAG — Typed Skill Graphs (arXiv:2606.03056, Jun 2026)

Bai et al. (Fudan/NUS/A*STAR). GitHub: https://github.com/Ericbai06/SkillDAG

- +12.8 pp over Graph-of-Skills on ALFWorld; +8.6 pp on SkillsBench reward
- Ret@K: 65.5 → 78.2; robust as pool grows 10× (where fixed pipelines degrade)
- Edge types: `similar_to`, `specializes`, `depends_on`, `composes_with`, `conflicts_with`
- Search returns: (vector matches, typed-edge neighbours, conflict signals)
- Online evolution: agent proposes edges from execution evidence; acyclicity checked

**Extends Priority 3 frontmatter recommendation above** — `composes_with` is already
listed; add `depends_on` and `conflicts_with` as well. The 2-view embedding (self +
needs) for cold-start edge assignment is the key operational detail missing from the
earlier recommendation.

### SkillRAE — Subunit-Level Context Compilation (arXiv:2605.10114, May 2026)

Meng et al., CUHK-Shenzhen.

- +11.7% over SOTA on SkillsBench; 40–60% body token reduction per skill
- Multi-level graph: communities → skills → **subunits**
- Subunit types: procedure steps, command blocks, pitfall bullets, domain table rows
- Online: inject only the subunits relevant to current task intent (not full body)

**Most actionable change for Hermes token efficiency:** decompose SKILL.md bodies into
labelled subunits. At retrieval, inject only the matching subunit types.

### SoK Agentic Skills — Security Taxonomy (arXiv:2602.20867, Feb 2026)

Jiang et al. Systematisation of knowledge.

- **~1,200 malicious skills** in major marketplace (ClawHavoc) — exfiltrated API keys
- 7 design patterns including trust-tiered execution and metadata-driven progressive
  disclosure
- Self-generated skills may degrade; curated skills substantially improve success rates

**Trust-tier values (recommended for Hermes frontmatter):**
- `trust: core` — shipped, never scanned
- `trust: community` — lightweight audit before injection
- `trust: user` — untrusted until validated, scanned for prompt injection

**Add to this skill's Scale thresholds table:** the SoK ClawHavoc attack demonstrates
that community skill marketplaces require active security review — not just a routing
quality concern but a supply-chain attack surface.

### Hierarchical Routing (arXiv:2601.04748, Jan 2026)

- Flat selection hits Bounded Capacity accuracy ceiling as library grows
- Hierarchical: category-level routing first → within-category (~15–25 skills)
- Reduces effective embedding comparison 170 → 15–25 for step 2

**Directly addresses R3 gap** identified in the TMLR survey. The "capability tree" in
AgentSkillOS (arXiv:2603.02176, already in this file) is the implementation; the
arXiv:2601.04748 paper quantifies *why* it beats flat selection.
