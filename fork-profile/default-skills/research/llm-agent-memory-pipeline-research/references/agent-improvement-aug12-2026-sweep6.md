# Agent Improvement Research — Aug 12, 2026 (Sweep 6)

**Sweep date:** Aug 12, 2026  
**Scope:** arXiv cs.AI + cs.CL Aug 2026 (IDs 2608.07xxx–2608.09930), 1,806 papers total.  
**Methodology:** Full category-listing walk via cached `.md` file (~1.8MB), keyword scan for agent-relevant titles, then individual `web_extract` on `arxiv.org/abs/{id}` for abstract verification.

## Boundary condition note
arXiv Aug 2026 listing tops out at **2608.09930** (1,806 CS papers through Aug 11 EOD). The prior baseline was "all IDs through 2608.09925." Only 2608.09928 (MMDiff, CV interpretability) and 2608.09930 (TTS evaluator) exist past that threshold — neither is agent-relevant. Aug 12 submissions had not yet appeared. Therefore "new papers" in this sweep are those Aug 7–11 submissions NOT in the named baseline ID list.

---

## PRIORITY 1: IMPLEMENT NOW

### SodaMem — Evidence-Grounded Temporal Graph Memory
| Field | Detail |
|-------|--------|
| **arXiv** | 2608.08055 |
| **Date** | Aug 8, 2026 |
| **Key finding** | Typed FactEvents with mandatory provenance spans; SUPERSEDES/CONTRADICTS/UPDATES edges under hybrid lexical-dense indexing; planner-reader loop gathers citable evidence before composing response. 92.8% on LongMemEval-S at ~$0.00161/question. |
| **Hermes fit** | Direct Hindsight schema upgrade: add `valid_from`, `valid_to`, `superseded_by`, `mention_time` fields to SQLite memory tables. SUPERSEDES/CONTRADICTS edges prevent silent contradiction accumulation. |
| **code_available** | YES — https://github.com/SodaMem/SodaMem |
| **Implement path** | Add edge-type column to Hindsight/staging tables. When l1-promote.py detects contradiction (NLI ≥ 0.75), write SUPERSEDES edge instead of deleting old fact. |

---

### OpenLoopEvolve — Versioned Loop Policies with Champion-Challenger Rollback
| Field | Detail |
|-------|--------|
| **arXiv** | 2608.09380 |
| **Date** | Aug 10, 2026 |
| **Key finding** | Represents agent behavior as versioned "Loop Policy" assets (observation, planning, memory, action, verification, recovery, stopping, budget control) with lineage tracking. Champion-Challenger paired evaluation; auto-rollback on degradation. Both online (feedback-triggered) and offline (archived-trace) evolution modes. |
| **Hermes fit** | YAML skills ARE loop policies. Add `parent_version`, `champion_since`, `rollback_threshold` to skill YAML frontmatter. The cron `skillopt-continuous-improvement` becomes the online evolution trigger; offline mode = mining session_search traces. |
| **code_available** | No |
| **Implement path** | 1. Add versioning fields to skill frontmatter. 2. Add comparative eval run to skillopt cron. 3. Auto-rollback when task_success_rate < parent_version rate by >threshold. |

---

### RADEG — Reward-Aware Dynamic Execution Gating
| Field | Detail |
|-------|--------|
| **arXiv** | 2608.09168 |
| **Date** | Aug 10, 2026 |
| **Key finding** | Lightweight retriever-agnostic decision layer between skill retrieval and agent execution. Learns surrogate model predicting execution utility of query–bundle pairs using local perturbation (delete/add/replace one skill) for supervision. Logistic head updates online from verifier feedback without retraining. |
| **Hermes fit** | Between `skill_view` and execution: check SQLite table of (query_hash, skill_name, outcome) triples. If predicted utility < threshold, skip execution and return "skill not applicable" to avoid wasted Claude API calls. |
| **code_available** | No |
| **Implement path** | 1. Create `skill_execution_log` SQLite table: (query_embedding, skill_name, task_success, timestamp). 2. Fit logistic regression on this table. 3. Gate skill execution on predicted probability. |

---

### SkillReason — CoT-Enhanced Skill Retrieval for Implicit Requests
| Field | Detail |
|-------|--------|
| **arXiv** | 2608.08640 |
| **Date** | Aug 9, 2026 |
| **Key finding** | Two-stage: Stage I uses CoT capability reasoning traces from a teacher as contrastive training supervision; retriever internalizes reasoning in query embedding. Stage II: retrieval-guided GRPO. At inference: query-only encoding (no CoT generation needed). SOTA on SkillReason-Bench (3,729 queries, 61,228 skills, 9 domains). |
| **Hermes fit** | Store capability-reasoning traces at skill invoke time (what reasoning led Claude to select this skill? log it). Use traces to enrich skill embeddings for future retrieval. Immediately actionable: add capability_trace field to skill_execution_log. |
| **code_available** | No |
| **Implement path** | After each successful task, ask Claude: "What capability did skill X provide for this query?" Store that as a retrieval-training signal for Hermes skill router. |

---

### SkillSentry — Runtime Assurance DSL for Skill Execution
| Field | Detail |
|-------|--------|
| **arXiv** | 2608.09253 |
| **Date** | Aug 10, 2026 |
| **Key finding** | DSL for runtime guidance: skill specification + experience mined from historical success/failure traces wraps the agent execution loop to monitor and guide execution. Iteratively refines guidance from new traces. +24.1% task success rate on average across 15 skills with Claude Code and Codex agents. |
| **Hermes fit** | Add `preconditions`, `postconditions`, and `runtime_checks` block to YAML skill frontmatter. The agent execution loop (before/after tool calls) verifies these. Failure traces auto-extend the `pitfalls` section. |
| **code_available** | No |
| **Implement path** | Add optional `runtime_checks` YAML block: list of (condition, action) pairs. At skill execution: Claude checks each condition; on violation, inject corrective prompt before proceeding. |

---

### Branch2Skill — MCTS-Guided Skill Evolution
| Field | Detail |
|-------|--------|
| **arXiv** | 2608.08677 |
| **Date** | Aug 9, 2026 |
| **Key finding** | MCTS under fixed budget → diverse reasoning trajectories. Compares elite paths vs. sibling alternatives sharing prefixes → step-wise evidence for what to retain/revise/avoid. Distills multi-step evidence into reusable skill updates. Uses 73.2% fewer tokens than SkillOpt while achieving superior performance on 6 benchmarks (GPT 5.5 as target model). |
| **Hermes fit** | Replace single-trajectory SkillOpt feedback with MCTS over task variants. `delegate_task` subagents are rollout nodes. SQLite stores trajectories with prefix IDs for sibling comparison. |
| **code_available** | No (announced: "Code will be published") |
| **Implement path** | Within skillopt cron: generate 3–5 agent rollouts per skill on the same task, compare best vs. sibling paths, extract step-level diffs → YAML skill patch candidates. |

---

### LatticeMind — Conflict-Aware Memory Write Protocol
| Field | Detail |
|-------|--------|
| **arXiv** | 2608.08236 |
| **Date** | Aug 8, 2026 |
| **Key finding** | Write-time conflict detection: explicit item status, cheap symbolic conflict checks, LLM reconciliation only for unresolved semantic cases. 0.97 accuracy vs. 0.61 for strongest aggregation baseline (p<10⁻⁶). Removing either symbolic checker OR LLM reconciler costs 12–14 points. |
| **Hermes fit** | Pair with SodaMem: at Hindsight write time, run symbolic check (exact match + field comparison) first; only call Claude for reconciliation when symbolic check finds semantic conflict. Prevents contradictions from silently accumulating in multi-subagent scenarios. |
| **code_available** | No |
| **Implement path** | Add `conflict_check()` to l1-promote.py: 1. BM25/cosine match vs. existing memories. 2. If high overlap: rule-based field check. 3. Only on rule-fail: Claude NLI. This is complementary to the existing `contradiction_check()`. |

---

### NeSy-Spatial — Self-Evolving Neuro-Symbolic Tool Skills
| Field | Detail |
|-------|--------|
| **arXiv** | 2608.07955 |
| **Date** | Aug 8, 2026 |
| **Key finding** | Abstracts tool interactions into typed atomic instructions ("Tool-Use Skills" + "Geometry Skills"). Closed-loop execution; failure trajectory analysis → refine skill structures + prune unreliable/inactive entries. Consistently improves spatial reasoning accuracy. |
| **Hermes fit** | Typed atomic instructions = YAML skill steps. The pruning criterion ("unreliable or inactive entries") is actionable: add `usage_count` and `success_rate` to skill frontmatter, prune skills below threshold in curator audit. |
| **code_available** | No |
| **Implement path** | Track per-skill: `usage_count`, `last_used`, `success_count`, `failure_count` in SQLite. In curator audit: flag skills with `failure_rate > 0.5` and `usage_count > 5` for rewrite or deletion. |

---

## PRIORITY 2: HIGH VALUE, MEDIUM EFFORT

### KVDiagnosis — Diagnostic Taxonomy for KV-Cache Compression
| Field | Detail |
|-------|--------|
| **arXiv** | 2608.09412 |
| **Date** | Aug 10, 2026 |
| **Key finding** | 25-method taxonomy of KV-cache compression across 5 mechanism families. Evidence-attention boost (4×) repairs 29.2% of compression failures vs. 6.3% sham. Code and data available. |
| **Hermes fit** | Placing retrieved Hindsight memories near the query (not buried in the middle of context) is the prompt-level equivalent of evidence-attention boosting. Actionable immediately. |
| **code_available** | YES — https://github.com/ChosenQC/KVDiagnosis |

### P³ — Joint Program-and-Proof Planning
| Field | Detail |
|-------|--------|
| **arXiv** | 2608.09277 |
| **Date** | Aug 10, 2026 |
| **Key finding** | Co-develops program and formal proof simultaneously from spec. +4.6–11.2 pp solve rate; ~40% API cost reduction and ~37% wall-clock reduction vs. sequential baseline. |
| **Hermes fit** | For subagent coding tasks: planning phase should simultaneously sketch implementation AND test/correctness criteria. Layers into `isa` skill (spec-as-test-suite). |
| **code_available** | No (benchmark Lean4Commit0 released) |

### STAIR — Graph-as-State Agentic Planning with Stage Routing
| Field | Detail |
|-------|--------|
| **arXiv** | 2608.09524 |
| **Date** | Aug 10, 2026 |
| **Key finding** | Graph-as-State + Stage Router + historical experience retrieval. Execution feedback updates state; action effects validated for future experience reuse. +9.5% normalized defense score on 100 Docker cyber ranges. |
| **Hermes fit** | Graph-as-State maps to Graphiti memory layer. Stage Router pattern: stages (clarify → plan → execute → verify) as SQLite state transitions, guiding which subagent skill loads next. |
| **code_available** | No |

### SymDiag — Neuro-Symbolic Verification via Step-Level SAT Checking
| Field | Detail |
|-------|--------|
| **arXiv** | 2608.08786 |
| **Date** | Aug 9, 2026 |
| **Key finding** | Translates CoT to symbolic constraints; SAT/entailment checks localize failing steps. Self-Auditor distinguishes translation errors from reasoning errors via dual encoding consistency. Accepted at ACM venue (DOI: 10.1145/3770855.3818004). |
| **Hermes fit** | For planning validation: symbolically verify plan steps against constraints (file must exist before read, etc.) and return precise failure location to guide repair prompts — more targeted than retry-from-scratch. |
| **code_available** | No |

### DocAtlas — Mutable-State Document Harness with Working Memory
| Field | Detail |
|-------|--------|
| **arXiv** | 2608.07527 |
| **Date** | Jul 21, 2026 (appeared in Aug listing) |
| **Key finding** | Long-document QA as mutable-state process: search/read/note/review tools + hierarchical tree + note store, updated as agent records evidence. GPT-5.4: 71.4% MMLongBench-Doc (above 65.8% human-expert). Qwen3.5-4B + RL: 63.7% vs. 54.4% direct baseline. |
| **Hermes fit** | Hierarchical tree + note store = Hindsight + session working memory. The mutable-state harness pattern (read → store → review under fixed context budget) is the principled version of Hermes's current ad-hoc multi-step document analysis. |
| **code_available** | No |

### Search-G1 — Representation-Based Intrinsic Rewards for Search Agents
| Field | Detail |
|-------|--------|
| **arXiv** | 2608.07531 |
| **Date** | Jul 24, 2026 (appeared in Aug cs.CL listing) |
| **Key finding** | Two readouts: (1) prompt-state readout = closed-book sufficiency (complement = retrieval necessity); (2) answer-commit readout = evidence reliance. Together: grounded intrinsic rewards without annotation. Reduces search trajectory length at competitive accuracy. |
| **Hermes fit** | Before each Hindsight memory lookup: probe whether context already suffices. If closed-book sufficiency high → skip retrieval. Reduces unnecessary Hindsight embedding lookups. Approximable via Claude self-rating of confidence. |
| **code_available** | YES — https://github.com/Rosy0912/Search-G1 |

### Agentic Router — Dual-Path Continual Learning with Memory
| Field | Detail |
|-------|--------|
| **arXiv** | 2608.09184 |
| **Date** | Aug 10, 2026 |
| **Key finding** | Proposal path: abstracts reusable operational lessons into retrievable guidance (improves coverage without modifying proposal LLM). Selection path: session-level adaptation via execution feedback. Complementary gains. |
| **Hermes fit** | "Abstract reusable lessons" pattern: after each successful tool call, extract lesson and store in Hindsight as retrievable note. Dual-path separation = skill retrieval (coverage) + RADEG gating (selection). |
| **code_available** | No |

---

## PRIORITY 3: USEFUL REFERENCE / LOWER COMPLEXITY

### StructReward — Structured Process Rewards Without Verifier Model
| Field | Detail |
|-------|--------|
| **arXiv** | 2608.08326 |
| **Date** | Aug 8, 2026 |
| **Key finding** | Step-level reward via lightweight numerical/symbolic/lexical matching against reference steps. Recycles rollouts as self-correction training instances. No separate trained verifier. |
| **Hermes fit** | Skill failure analysis: align failed trajectory steps with YAML skill procedure steps using difflib/semantic similarity to identify exact divergence point. More targeted than retry-from-scratch. |
| **code_available** | No |

### SkillCDG — Constraint Dependency Graph for SKILL Compliance
| Field | Detail |
|-------|--------|
| **arXiv** | 2608.08146 |
| **Date** | Aug 8, 2026 |
| **Key finding** | Two-layer constraint dependency graph: upper = skill routing, lower = atomic constraint dependencies within each skill. Two-level retrieval + dependency closure for compliance judgment. +12.8 pp F1, −64.3% token consumption. |
| **Hermes fit** | Replace flat YAML skill description with dependency DAG: encode which steps must precede others. Enables step-level compliance checking with 64% token reduction for complex skills. |
| **code_available** | No |

### Emotion2Skill — Internal Emotion Signals for Skill Routing
| Field | Detail |
|-------|--------|
| **arXiv** | 2608.09248 |
| **Date** | Aug 10, 2026 |
| **Key finding** | 27-dim emotion vector from LLM residual stream → confidence-gated routing injection. Emotion trajectory shifts pinpoint problematic skill invocations → targeted SOP rewriting. +26.9%/+25.5% WebShop/ALFWorld. |
| **Hermes fit** | Internals unavailable via Anthropic API. Conceptual proxy: Claude self-rates confidence before routing decision. The skill-failure trajectory → SOP rewriting component IS applicable. |
| **code_available** | YES — https://github.com/BoHan-LIN04/Emotion2Skill |

### ColluSkill + ChainGuard — Cross-Skill Composition Attack/Defense
| Field | Detail |
|-------|--------|
| **arXiv** | 2608.09732 |
| **Date** | Aug 10, 2026 |
| **Key finding** | Collusive multi-skill-chain attack decomposes malicious intent into interdependent sub-payloads across individually benign skills. 96.0% attack success rate vs. 6 scanners. ChainGuard (context-aware chain scanner): 22.5% residual attack, 99.5% benign pass-through. |
| **Hermes fit** | As skill library grows: at skill load time, build dependency graph across co-invoked skills and flag artifact flows that cross trust boundaries. ChainGuard pattern for skill security. |
| **code_available** | No |

### CMI — Controlled Memory Interference Study
| Field | Detail |
|-------|--------|
| **arXiv** | 2608.07622 |
| **Date** | Aug 7, 2026 |
| **Key finding** | Relationship-specific interference (authority/temporal conflicts) sharply suppresses update plasticity. Lexical vs. dense retrieval have distinct interference pathways. Poisoning sensitive to authority cues > recency. |
| **Hermes fit** | (1) Tag memories with authority level for poisoning resistance. (2) Combine lexical + dense retrieval since their interference pathways differ → lower aggregate vulnerability. (3) Use validity window, not just recency. |
| **code_available** | No |

### Agentic Harnesses — LLM-Judge Ensemble for Plan Verification
| Field | Detail |
|-------|--------|
| **arXiv** | 2608.09857 |
| **Date** | Aug 10, 2026 |
| **Key finding** | LLM-as-Judge ensemble with CoT across multiple models as middleware gating plans before execution. ~85% precision across accept/escalate/reject; 97% adversarial containment. |
| **Hermes fit** | Lightweight pre-dispatch verification for `delegate_task`: quick Claude call to approve/escalate/reject the plan before spawning subagent. Extends `trajectory-risk-guardrail` skill. |
| **code_available** | No (work in progress) |

### SWE-RPG — Coding Agent Benchmark with Intermediate Ground Truth
| Field | Detail |
|-------|--------|
| **arXiv** | 2608.09072 |
| **Date** | Aug 10, 2026 |
| **Key finding** | 163 tasks (31 Python/Java repos) with ground truth for Requirement Clarification AND Implementation Planning steps. Only 31.5% average resolved rate. Implicit requirement recovery = #1 bottleneck (24.5%–46.0% of failures). |
| **Hermes fit** | Validates `grill-me` skill (upfront clarification) and `isa` skill (spec-as-test-suite). Add explicit "implicit requirement extraction" step to `github-issue-to-pr` skill before planning phase. |
| **code_available** | YES — https://github.com/Xin-Zhou-smu/SWE-RPG-Bench |

### Idea Search — Dynamic Idea Bank + Tree Search
| Field | Detail |
|-------|--------|
| **arXiv** | 2608.08958 |
| **Date** | Aug 9, 2026 |
| **Key finding** | Dynamic "Idea Bank" integrated into tree search — atomic ideas guide mutation branches; bank updated from execution. Breaks pure tree search plateau; exploratory prompting beats sampling-level exploration. |
| **Hermes fit** | Skill library as Idea Bank: new skills discovered during subagent execution stored and reused as branching guidance for subsequent planning. SQLite for bank; exploratory prompting via Claude. |
| **code_available** | No |

---

## Source / Access Notes
- **arXiv category listing:** Full 1,806-paper listing cached locally as 1.8MB file; scanned via keyword regex for agent-relevant titles.
- **SerpApi:** Rate-limited (HTTP 429) — fell back to direct `web_extract` on `arxiv.org/abs/{id}` for all abstract verification.
- **ACL Anthology / IJCAI / ECAI / NeurIPS workshops:** Rate-limited; covered by arXiv cross-listing (most venue papers also appear as arXiv preprints).
- **HAL-Inria / CyberLeninka / RISS:** No unique agent papers found in this window; consistent with prior sweep finding that non-English sources lag arXiv 2–4 weeks for LLM-agent topics.
- **papers.cool / AMiner / Semantic Scholar:** Rate-limited; arXiv pool is the authoritative source for these papers anyway.

## Implementation Priority Ranking
1. SodaMem (2608.08055) — code available, SQLite-native, direct Hindsight schema upgrade
2. OpenLoopEvolve (2608.09380) — YAML skill versioning + auto-rollback; fits existing cron
3. RADEG (2608.09168) — trivial logistic gate; saves Claude API cost
4. SkillReason (2608.08640) — capability trace logging; immediate retrieval improvement
5. SkillSentry (2608.09253) — precondition/postcondition in YAML; +24.1% task success
6. LatticeMind (2608.08236) — write-time conflict detection; pair with SodaMem
7. Branch2Skill (2608.08677) — MCTS skill evolution; replaces single-trajectory SkillOpt
8. NeSy-Spatial (2608.07955) — typed tool steps + usage-count pruning
