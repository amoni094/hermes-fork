# Agent Runtime Research: Aug 11 2026 Sweep (Post-Baseline Delta)
## 33 new papers not in prior baseline | Hermes subagent sweep

**Baseline ended at:** arXiv 2608.09885 (submitted 2026/08/10)
**Search scope:** cs.AI, cs.CL, cs.MA, cs.LG, cs.IR, cs.NE, cs.SE listings + arXiv keyword search
**Non-English yield:** CyberLeninka (Russian) = survey articles only, no novel techniques.
  HAL (French) = Anubis bot-blocked. J-STAGE (Japanese) = network-blocked. ACL EMNLP/COLM 2026 not yet indexed.

---

## TOPIC 1: AGENT MEMORY (6 papers)

### 2608.07622 | Controlled Memory Interference in Continual LLM Agents
**Date:** 2026/08/07 | **Code:** No
Introduces CMI framework + 1,200-episode benchmark. Shows concurrent memories can reinforce, revise, or interfere. Selective consolidation by **temporal validity** and **authority rank** outperforms pure relevance retrieval.
**Hermes:** Add `authority` + `valid_until` columns to Hindsight SQLite. Interference-aware consolidation: when storing new memories, check temporal validity conflicts with existing entries and priority-rank by authority.

### 2608.08253 | SuperLocalMemory 4.0: The Governed Memory OS for AI Agents
**Date:** 2026/08/08 | **Code:** Yes (GitHub: qualixar/superlocalmemory)
Local-first. Combines dense semantic + BM25 + temporal + Hopfield-associative + spreading-activation via **reciprocal-rank fusion**. Adds bi-temporal recall (event_time + store_time), RBAC, GDPR erasure, audit trails.
**Hermes:** (1) Add BM25 alongside semantic and fuse via RRF. (2) Add `event_time`/`store_time` cols to SQLite. (3) Add `audit_log` table. Direct implementation reference — code available.

### 2608.08995 | Muscle Memory for Agents: Compile not Merely Retrieve
**Date:** 2026/08/10 | **Code:** No
Recurring user intents compiled into purpose-built specialist subagents = 40% fewer turns vs. retrieve+orchestrate. "Compilation" is the right default for repetitive personalized workflows.
**Hermes:** Track skill invocation frequency in SQLite. When same workflow exceeds threshold N, auto-generate a specialist subagent SKILL.md instead of re-retrieving each time. Maps to delegate_task pattern.

### 2608.09043 | Don't Scroll Back: Missing-Evidence Memory for Streaming Dialogue
**Date:** 2026/08/10 | **Code:** No
Formalizes streaming summarization as a **gap-resolving evidence** problem. Success = memory contains evidence the current window *presupposes*, not how much history is stored. Dedicated benchmark + eval protocol.
**Hermes:** micro_compact should prioritize "gap-resolving" chunks (context items later turns presuppose but don't repeat) over recency or TF-IDF salience. Presupposition-aware pruning pass.

### 2608.07067 | DocMemo: Dynamic Evidence via Probabilistic Memory-Guided Retrieval
**Date:** 2026/08/07 | **Code:** Yes (GitHub)
Cross-round probabilistic memory states track dynamic page-relevance across retrieval iterations, recovering from early retrieval errors in long multi-modal documents.
**Hermes:** For multi-URL web_extract workflows: probabilistic relevance tracking across tool calls avoids re-fetching covered pages; focus on evidence gaps.

### 2605.13486 | R²-Mem: Reflective Experience for Memory Search
**Date:** 2026/05/13 | **Code:** No
Rubric-guided reflection over high/low-quality historical search trajectories distills search strategies into an experience store, preventing repetition of past memory retrieval errors.
**Hermes:** Hindsight reflect() → rubric-guided trajectory scoring: evaluate past memory queries, distill failure patterns into "search anti-patterns" memory note for future calls.

---

## TOPIC 2: CONTEXT / PROMPT COMPRESSION (2 papers)

### 2608.08389 | Not Worth Another Token: Marginal Value Estimation for Deep Research Agents
**Date:** 2026/08/09 | **Code:** No
Stage-aware marginal value estimation at pre-retrieval, post-retrieval, pre-synthesis. **30-45% token reduction, <2% quality drop.** Learned value model > heuristics at all three stages.
**Hermes:** Before appending a new tool result to context, estimate marginal value vs. existing context. Start with embedding similarity proxy; upgrade to learned model. Cache scores per chunk in SQLite.

### 2608.09412 | KVDiagnosis: Diagnostic Benchmark for KV-Cache Compression
**Date:** 2026/08/10 | **Code:** Yes (GitHub)
25-method KV-cache compression taxonomy (5 mechanism families, 8 verified implementations). C-to-W (FullCache-correct but compressed-wrong) metric as compression quality diagnostic.
**Hermes:** Reference taxonomy when Anthropic API exposes KV-cache controls. C-to-W metric evaluates existing micro_compact quality today.

---

## TOPIC 3: MULTI-AGENT (13 papers)

### 2607.27877 | MSEval: Coordination Mode as First-Class Citizen (Multi-Agent Coding)
**Date:** 2026/07/30 | **Code:** Yes (GitHub)
10 real-world full-stack projects, 10 collaboration topologies. **Coordination topology > model choice** as perf factor. Star topology = decomposable tasks; chain = sequential dependencies.
**Hermes:** delegate_task topology selection is explicit: star for decomposable, chain for sequential. MSEval rubrics → agent-task-signoff verification.

### 2608.06410 | ADIAS: Automated Design of Interactive Agentic Systems
**Date:** 2026/08/03 | **Code:** No
Issue-centric agent optimization: persistent issue state across rounds → warm-start repair, faster convergence, fewer wasted steps.
**Hermes:** autonomous-agent-loop-design: maintain persistent issue state in SQLite per delegate_task call. Enables warm-start re-plans.

### 2608.07556 | MasDrift: Authorization Drift Benchmark
**Date:** 2026/08/02 | **Code:** No
600 tasks, 8 domains. Authorization erodes with hierarchy depth: **3-level hierarchies lose ~25%** of reserved-action enforcement. Explicit constraint manifests → ~95% enforcement preserved.
**Hermes:** delegate_task must carry a `constraint_manifest` field (prohibited/reserved actions). Implement as pre-tool-call guard. YAML extension to hermes-context-packet.

### 2608.07627 | Governed Agent Ecosystems: 23-Pattern Catalogue
**Date:** 2026/08/07 | **Code:** No
23 patterns for governed MAS: Memory Owner Separation, Privilege Escalation Guard, Audit Trail per Delegation. Validated in hospital production deployments.
**Hermes:** Implement 3 key patterns: (1) skill files ≠ runtime state, (2) privilege claims declared in YAML frontmatter, (3) every delegate_task logged to audit trail.

### 2608.08131 | Order 66: Compositional Threat Analysis of Latent Compromise in LLM Agents
**Date:** 2026/08/08 | **Code:** No
"Dormant rule + activation trigger" attack via shared memory/tool. Defenses: memory compartmentalization + activation-pattern auditing.
**Hermes:** Skill content validated at load time (embedding similarity vs. expected behavior). Memory writes from subagents sandboxed (separate SQLite namespace) until verified by orchestrator.

### 2608.08516 | Fluid Structure, Rigid Record: Layered Org Design for Agent-Native Orgs
**Date:** 2026/08/09 | **Code:** No
Separates agent orgs: rigid record layer (immutable audit store) + fluid coordination layer. Permission = operational boundary; Privilege = escalation boundary.
**Hermes:** SKILL.md frontmatter add `permission` + `privilege` fields. Skill router gates on both. Formalizes subagent authorization model.

### 2608.09251 | MoRSE: Mixture of Role-Subtask Experts
**Date:** 2026/08/10 | **Code:** No
(role, subtask) conditioning vs. role alone: **+8-12% on long-horizon benchmarks.**
**Hermes:** SKILL.md YAML frontmatter add `subtask` field alongside `role`. Enables finer-grained routing in compositional-skill-routing.

### 2608.09256 | Distributed Team Orchestration via Supervisor Networks: DTOA
**Date:** 2026/08/10 | **Code:** No
Team fictitious play + distributed belief learning. Convergence proved under Byzantine subagents misreporting joint actions.
**Hermes:** hermes-swarm-consensus: supervisor agents maintain reliability estimates over subagent outputs. Weight aggregation by estimated reliability vs. equal voting.

### 2608.09828 | POLIS: Multi-Agent AI Safety as Institutional Design
**Date:** 2026/08/10 | **Code:** No
Delegation rules + info-flow constraints + resource boundaries = safety properties no single-agent design achieves alone. 5,280-episode study.
**Hermes:** Each delegate_task defines a micro-institution: delegation scope + info-flow constraints (what subagent can read/write) + resource limits (token budget, tool access). Maps to hermes-context-packet extension.

### 2608.04626 | Blockchain Trust Stack for Trustworthy Agent Networks
**Date:** 2026/08/05 | **Code:** No
5-layer trust stack: identity, authorization, reputation, auditability, settlement. Survey 1980-2026.
**Hermes:** (API key ↔ identity), (skill scope ↔ authorization), (hindsight scores ↔ reputation), (audit log ↔ auditability), (result verification ↔ settlement). Architecture for multi-org Hermes deployments.

### 2608.03239 | Relational Priors as Convergence Pressure in LLM-MAS
**Date:** 2026/08/04 | **Code:** No
Explicit signed-network relational priors (trust/challenge/defer/collaborate in system prompts) **reduce rounds-to-consensus by ~35%** without changing task protocol.
**Hermes:** hermes-swarm-consensus: inject relational prior directives alongside role prompts. Minimal cost, measurable speedup.

### 2606.17203 | Trust-Aware Traceability: Confidence-Calibrated KGs for MAS
**Date:** 2026/06/15 | **Code:** No
Shared KG with confidence scores on edges propagated through sequential agent pipelines. Low-confidence nodes trigger clarification before downstream consumption.
**Hermes:** Graphiti edges carry `confidence` metadata. Gate downstream tool calls on minimum confidence threshold.

### 2608.09324 | CoRE: Consensus Rewards via Equilibrium for TTS RL
**Date:** 2026/08/10 | **Code:** No
Replicator-dynamics dominant-set extraction over agreement graph (answer agreement + reasoning similarity + generation confidence). Recovers minority-correct answers majority vote discards.
**Hermes:** hermes-swarm-consensus: build agreement graph across subagent outputs, extract dominant set vs. naive majority vote. Also applies to self-evaluation.

### 2608.09128 | Social Gym + SPaRTan: Multi-Agent Social Reasoning Benchmark
**Date:** 2026/08/10 | **Code:** No
21 social games (Werewolves, Resistance, Spyfall) with verifiable rule-decided outcomes. SPaRTan training improves cross-game social adaptation +18%.
**Hermes:** Low-cost evaluation environment for multi-agent cooperation/negotiation skills with verifiable outcomes (no LLM judge needed).

---

## TOPIC 4: SKILL / TOOL LEARNING (3 papers)

### 2607.01874 | SkillCoach: Self-Evolving Rubrics for Agentic Skill-Use
**Date:** 2026/07/02 | **Code:** No
Auto-derives step-level rubrics from skill metadata (SOPs, domain rules, tool workflows). Rubric-driven feedback improves skill selection + execution. Outperforms final-outcome-only training.
**Hermes:** SKILL.md 'steps' + 'pitfalls' → auto-generate rubric checkpoints. Post-task reflection scores execution against rubric, writes to Hindsight, triggers skill patches on low scores.

### 2608.08303 | Query-Only Backdoor Attacks on Self-Evolving Skills via Trajectory Poisoning
**Date:** 2026/08/08 | **Code:** No
Adversarial queries poison trajectory data used to update self-evolving skills without direct skill file access.
**Hermes (security):** skill_manage must validate trajectory-derived updates: embedding similarity between old/new content; require human approval for diffs >30%. Add `skill_content_hash` to YAML frontmatter.

### 2607.03702 | PivoARL: Pivotal-Aware Self-Feedback Retry
**Date:** 2026/07/04 | **Code:** Yes (GitHub)
Identifies pivotal erroneous turn via structured reflection; retries only from that state. **~60% interaction cost reduction** vs. full-trajectory retry.
**Hermes:** ralph-loops + agent-runtime-loop-patterns: implement pivotal-turn detection via structured reflection before full plan restart. Maps to systematic-debugging approach.

---

## TOPIC 5: ONTOLOGY / KNOWLEDGE GRAPH (3 papers)

### 2608.07949 | Guixu: Valuation-Driven Data Discovery for Autonomous Agents
**Date:** 2026/08/08 | **Code:** No
3-phase valuation: proxy-label utility estimation → dataset selection under budget → on-chain attestation. Prioritizes task-specific utility over raw retrieval ranking.
**Hermes:** domain-research-synthesis: before calling web_extract across multiple URLs, estimate marginal information value per source under token budget. Store utility scores in Hindsight.

### 2608.09393 | FiscalQA Pro: Temporal Misgrounding in Legal RAG
**Date:** 2026/08/10 | **Code:** Yes (GitHub)
Identifies temporal misgrounding: retrieval of current-version document when earlier version applies. Benchmark: 32,436 article-versions, 93 years of French tax code, 209 expert QA pairs.
**Hermes:** Graphiti MCP: tag KG nodes with `valid_from`/`valid_to`. Query against task context-date, not just semantic similarity. Essential for legal/compliance/versioned-document use cases.

### 2608.09779 | KGCaRe: Explainable Complex Conditional QA via KG + RAG
**Date:** 2026/08/10 | **Code:** No
Hybrid neural+symbolic: LLM constructs KG from docs, symbolic reasoning over KG + neural retrieval. **+15% on complex conditional QA** vs. RAG-only.
**Hermes:** Graphiti KG populated from skill content + retrieved docs, then queried symbolically for complex conditions (e.g., "which skills are valid for Python on Fedora for this task type").

---

## TOPIC 6: SELF-IMPROVEMENT (4 papers)

### 2607.06273 | AgentTether: Graph-Guided Diagnosis and Runtime Intervention
**Date:** 2026/07/07 | **Code:** No
Causality graph over trajectory steps identifies error origin → targeted runtime interventions (re-prompting, tool-rollback, context injection) at causal root.
**Hermes:** systematic-debugging: log tool calls as a DAG in SQLite, identify the first error-producing node, intervene there vs. restarting from scratch.

### 2608.09819 | Macaron-V1: Continual Learning with Self-Improvement + MoLoRA
**Date:** 2026/08/10 | **Code:** No
Versioned model-harness pairs: each config evaluated under external contract before generating successor. Mixture-of-LoRA selects specialist adapters per turn from frozen base.
**Hermes:** Skill versioning external-contract pattern: each SKILL.md version passes a contract (test cases in `tests/` subdirectory) before skill_manage commits. Creates verifiable skill evolution chain.

### 2608.09898 | Consilience for Verifier-Free Test-Time Scaling ⭐ POST-BASELINE
**Date:** 2026/08/10 | **Code:** No | **ID > 2608.09885 = confirmed new**
Agreement-weighted confidence ("consilience") across confidence tiers outperforms pure confidence ranking for VF-TTS. Near-zero overhead, improved minority-correct recovery.
**Hermes:** Generate 3-5 candidate responses, select by consilience score (agreement across reasoning paths × per-path confidence) vs. single-sample or majority vote. Applicable via Claude extended thinking.

### 2608.09324 | CoRE: Consensus Rewards via Equilibrium (also Topic 3)
**Date:** 2026/08/10 | **Code:** No
**Hermes:** Also applies to self-evaluation: build agreement graph across reasoning traces, extract dominant set as best answer candidate.

---

## TOPIC 7: CONFIG / SCHEMA (covered by multi-agent papers above)

Key schema additions derived from this sweep:
- `constraint_manifest` in delegate_task / hermes-context-packet (from MasDrift)
- `permission` + `privilege` in SKILL.md frontmatter (from Fluid Structure Rigid Record)
- `subtask` field in SKILL.md YAML alongside `role` (from MoRSE)
- `skill_content_hash` in SKILL.md frontmatter for tamper detection (from Trajectory Poisoning paper)
- `valid_from` / `valid_to` on Graphiti KG nodes (from FiscalQA Pro)
- `confidence` metadata on Graphiti edges (from Trust-Aware Traceability)

---

## TOPIC 8: NEW BENCHMARKS

| ID | Benchmark | What it measures | Hermes use |
|----|-----------|-----------------|------------|
| 2607.27877 | MSEval | Multi-agent coding, 10 topologies, time+cost | Evaluate delegate_task topology selection |
| 2608.09802 | SWE-Bench ProMax | Multi-file code refactoring, 6 languages; 60% of SWE-bench Verified has flawed tests | Coding agents: don't trust test-pass alone |
| 2608.09412 | KVDiagnosis | KV-cache compression, 25-method taxonomy | Guide context compression decisions |
| 2608.09393 | FiscalQA Pro | Temporal RAG correctness | Eval Graphiti temporal retrieval |
| 2608.09128 | Social Gym + SPaRTan | 21 social games, verifiable outcomes | Multi-agent cooperation eval |
| 2608.09072 | Unified Issue Resolution | Req clarification + planning + code gen; clarification = #1 failure | Add clarification phase to isa/tdd skills |

---

## METHODOLOGY NOTES (learned this session)

### arXiv listing page technique (highest yield)
- `https://arxiv.org/list/{cat}/recent` shows 50 papers per category
- `skip=N&show=M` parameters return HTTP 400 — do NOT use them
- Parse with `re.split(r'<dt>', html)` — each entry starts with `<dt>` not `<li>`
- Categories worth scanning: cs.AI, cs.CL, cs.MA, cs.LG, cs.IR, cs.NE, cs.SE
- Supplement with `arxiv.org/search/` keyword searches (different index, different coverage)

### Abstract fetching
- `fetch_abstract_full()` via `https://arxiv.org/abs/{id}` — `citation_title` meta tag for title
- Blockquote abstract: `class="abstract[^"]*"` regex
- GitHub presence: `'github.com' in content`
- Submission date: `<meta name="citation_date" content=...>`

### Non-English source access (Aug 2026 findings)
- **HAL (French):** Anubis proof-of-work bot protection — completely inaccessible to headless scraping
- **J-STAGE (Japanese):** Blocked as "private network address" in this environment  
- **CyberLeninka (Russian):** Accessible, but content is survey/review articles only — no novel techniques ahead of arXiv for AI agent topics. Use AMiner for Chinese institutional AI papers instead.
- **RISS (Korean):** Not tested (connection blocked pattern)
- **ACL Anthology:** EMNLP 2026, COLM 2026 not yet indexed (return 404)
- **Semantic Scholar API:** Rate-limited (429) — requires free API key for reliable use

### Baseline ID interpretation
- The "known baseline" list is the set to skip by arXiv ID
- Papers not in that list but with IDs in the same 2608.XXXXX range are valid new finds
- "Truly post-baseline" = ID > baseline_max (e.g. 2608.09885); but prior-sweep misses also count as new
- arXiv IDs in 2608.XXXXX don't map 1:1 to calendar Aug 11 — papers can be submitted Aug 1-11+ all getting 2608 prefix
