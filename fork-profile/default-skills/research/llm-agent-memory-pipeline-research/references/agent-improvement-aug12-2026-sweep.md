# Agent Improvement Research — Aug 12 2026 Sweep (Sweep 5)

Baseline cutoff: arXiv 2608.09885. Papers above that ID are in scope but none
were on-topic at sweep time (next arXiv announcement cycle had not yet run).
All papers below are **genuinely new findings** from the Aug 11 announcement batch
not previously captured in sweeps 1–4.

Methodology: exhaustive scan of cs.AI/new, cs.CL/new, cs.LG/new, cs.MA/new + the full
cs.AI/recent 486-entry batch. Individual abstract fetches for all agent-relevant titles in
the ID range 7473–9885. Papers.cool checked; non-English sources had no unique findings
on-topic (Chinese/JP/KO material lags arXiv by 2–4 weeks for LLM-agent topics).

---

## TOPIC 1 — Agent Context Window / KV Cache

**2608.07855** | 8 Aug 2026
Title: CommitKV: Lifecycle-Aware KV Cache Compression via Commit Transitions for Multi-Turn Agents
Key finding: Treats KV entries as having a lifecycle tied to conversation "commits" (resolved intents); prunes entries whose associated intents have been resolved, reducing cache size 40–60% on multi-turn agent benchmarks without quality loss.
Hermes relevance: Models multi-turn CLI sessions as commit sequences — eviction tied to intent completion rather than recency. Applicable to extended context session management.
code_available: no

**2608.07915** | 8 Aug 2026
Title: SPECTRA: Pushing the KV Cache Beyond the 2-Bit Cliff via Spectral Transform Coding
Key finding: Applies DCT/FFT spectral transform to KV cache before quantization; achieves sub-2-bit effective compression with <1% quality loss vs. standard 2-bit quantization.
Hermes relevance: For self-hosted inference (Ollama/vLLM fallback); informs caching strategy — spectral structure exists in KV matrices that token-position schemes miss.
code_available: yes

**2608.08684** | 9 Aug 2026
Title: RippleKV: Cross-Layer KV Cache Allocation via Perturbation Propagation
Key finding: Models KV perturbation propagation across transformer layers; allocates compression budget inversely proportional to layer sensitivity, beating uniform allocation.
Hermes relevance: For local model inference; principle: budget headroom proportionally to importance, not uniformly — applies to Hermes prompt section weighting.
code_available: no

**2608.08569** | 9 Aug 2026
Title: VoxZip: Semantic-Anchored Temporal KV Cache Compression for Long-Context Audio Inference
Key finding: Anchors KV eviction to semantic segment boundaries (speech act / discourse turn) rather than token positions; extends cleanly to text by treating dialogue turns as anchors.
Hermes relevance: Turn-boundary-aware context compression — evict at session turn boundaries rather than raw token counts. Directly applicable to Hermes multi-turn CLI sessions.
code_available: yes

---

## TOPIC 2 — Agent Tool / Function Calling

**2608.08254** | 8 Aug 2026
Title: Your Prompt Is Not the Only Prompt: How Much Do LLMs Weight Structured-Output Schema Descriptions?
Key finding: Schema field descriptions act as a second instruction channel that significantly influences classification — sometimes overriding system prompt instructions; accuracy varies 12–18% based on description placement.
Hermes relevance: DIRECT — Anthropic tool schema design for Hermes tools: put critical constraints in schema field descriptions, not only system prompt. Schema descriptions are instruction-level, not metadata.
code_available: no

**2608.08467** | 9 Aug 2026
Title: LLM within MCP Matters: Measuring Inefficient Resource Utilization Driven by LLMs
Key finding: MCP servers embedding lookup tables in server instructions cause models to ignore them and make redundant API calls; moving data to tool return values reduces LLM calls 34% and latency 41%.
Hermes relevance: DIRECT — Hermes MCP/tool design: keep server instructions lean; return data via tool responses not system-prompt injection. Confirmed Aug 2026.
code_available: yes

**2608.07952** | 8 Aug 2026
Title: Persistent Semantic Entities in Tool-Augmented LLM Systems
Key finding: Names/IDs created by tool calls in earlier turns are "forgotten" mid-task; maintaining a lightweight entity register across tool calls cuts entity-confusion errors 47%.
Hermes relevance: Implement a lightweight entity register in Hermes session state or SQLite to persist tool-created references across turns (file paths, IDs, URLs created by prior tool calls).
code_available: no

---

## TOPIC 3 — Agent Self-Correction / Re-Planning

**2608.08326** | 8 Aug 2026
Title: StructReward: Efficient Structured Process Rewards for Self-Correcting Multimodal Reasoning
Key finding: Step-level rewards via structured decomposition improve self-correction rates 23% over binary outcome-only rewards.
Hermes relevance: Per-step feedback for Hermes agent loops — intermediate tool results can trigger re-planning rather than waiting for final outcome failure.
code_available: no

**2608.09292** | 10 Aug 2026
Title: Beyond the Capability Boundary: Zeroth-Order Optimization for Self-Evolving LLM Agents
Key finding: Zeroth-order (black-box) optimization generates training signal from hard examples where the agent can't produce correct trajectories, breaking the "can't learn what you can't do" ceiling.
Hermes relevance: Pattern for skill self-improvement on hard tasks — ZO-perturbation of skill YAML content to find improvement directions without gradient access.
code_available: yes

**2608.08466** | 9 Aug 2026
Title: Hierarchical Self-Improvement: A Framework for Task-Specific Evolvable Agent Harnesses
Key finding: Task-family-specific harness modules hot-swap at runtime; each task family independently evolves its own harness config, improving on 8/10 task families vs. a fixed harness.
Hermes relevance: DIRECT — different Hermes skills can carry different harness configs (retry policies, tool sets, context limits) in YAML frontmatter. Per-skill harness is the right level of granularity.
code_available: yes

**2608.08523** | 9 Aug 2026
Title: Discovering Diverse Planning Policies for Multimodal Embodied Agents with Quality-Diversity Optimization
Key finding: QD optimization finds a portfolio of planning policies; fallback to portfolio alternatives when dominant strategy fails improves task completion 31%.
Hermes relevance: Re-planning fallback: maintain a small portfolio of planning templates per skill type and switch on failure, rather than retrying the same strategy.
code_available: no

---

## TOPIC 4 — Instruction Following / Calibration

**2608.09154** | 10 Aug 2026
Title: UNSPECIFIC: General Constraint Synthesis for Breaking Copy-and-Paste Shortcut in LLM Instruction Following
Key finding: Back-translation instruction benchmarks allow models to cheat by copying source text; UNSPECIFIC synthesizes constraints requiring genuine generalization, revealing 15–30% lower true compliance rates.
Hermes relevance: Hermes skill YAML constraint tests should use non-source-echoing tasks; current instruction evals may overestimate compliance. Validation methodology update.
code_available: yes

**2608.07968** | 8 Aug 2026
Title: Thinking Hard, Not Smart: Reasoning Models Fail to Ration Test-Time Compute Across Questions
Key finding: With a shared compute budget across multiple questions, models overthink easy ones and underthink hard ones — fail to allocate proportionally.
Hermes relevance: Hermes token budget (max_tokens, extended thinking budget) should be allocated dynamically based on task complexity signals, not set uniformly per session.
code_available: no

---

## TOPIC 5 — Long-Context Agents / RAG Architecture

**2608.08445** | 9 Aug 2026
Title: Forgotten History or Test-of-Time? Retrospect and Prospect on RAG from an IR Perspective
Key finding: RAG's core ideas predate LLMs by decades; identifies 5 persistent failure modes with IR-sourced solutions including pseudo-relevance feedback and reciprocal rank fusion.
Hermes relevance: Hindsight embedding pipeline can adopt IR-era relevance feedback for better retrieval — reciprocal rank fusion across FTS5 + vector search.
code_available: no

**2608.08512** | 9 Aug 2026
Title: Time Present and Time Past: Benchmarking LLMs on Temporally Evolving Document Understanding
Key finding: LLMs fail 40–60% harder on amended vs. original versions of evolving documents (laws, APIs, docs) even with full context — cannot track what changed.
Hermes relevance: Hermes skills referencing external APIs/docs should carry version timestamps and staleness flags in YAML frontmatter. Skill drift is a real failure mode.
code_available: yes

---

## TOPIC 6 — Agent Security / Adversarial Attacks

**2608.08303** | 8 Aug 2026
Title: Query-Only Backdoor Attacks on Self-Evolving Skills via Trajectory Poisoning
Key finding: Attacker needs only query access (no model weights) to poison self-evolving skill systems; malicious trajectories injected via normal queries corrupt skill updates without detection.
Hermes relevance: CRITICAL — Hermes self-evolving skill updates must require human approval or trajectory provenance checking before merging into the skill library.
code_available: no

**2608.08264** | 8 Aug 2026
Title: OBLIVION: Workflow-Level Operational Skill Unlearning for Deployed Agents
Key finding: Removing a skill from registry is insufficient — agents reconstruct it from memory entries, transcripts, and schema residuals; multi-carrier purge (registry + memory + session cache) is required.
Hermes relevance: When deprecating a Hermes skill: also purge SQLite session mentions, Hindsight memory entries referencing the skill, and YAML cross-references in other skills.
code_available: no

**2608.09542** | 10 Aug 2026
Title: Dual-Adversarial Safety Alignment: Cultivating Intrinsic Threat Comprehension in LRMs
Key finding: Pattern-centric alignment (train on prompt patterns) fails to generalize across jailbreaks; training on attack mechanisms improves adversarial robustness 28%.
Hermes relevance: Agent safety prompting should describe threat mechanisms in system prompt rather than listing forbidden patterns — mechanism-level, not surface-level.
code_available: no

**2608.08471** | 9 Aug 2026
Title: Yesterday's Shield, Today's Spear: A Self-Evolving Safety Guardrail in Production (SESG)
Key finding: Static guardrails become attack surfaces within days; SESG monitors live traffic and auto-updates guardrail policies, reducing bypass rate from 8.3% to 1.1%.
Hermes relevance: Hermes tool use guardrails (computer_use safety rules) should be periodically reviewed, not treated as fixed system prompt text. Periodic refresh cadence recommended.
code_available: yes

**2608.07556** | 2 Aug 2026
Title: MasDrift: Benchmarking Authorization Preservation Across Multi-Agent Architectures
Key finding: 600-task benchmark shows all 8 tested multi-agent architectures fail to preserve authorization boundaries during delegation; subagents exceed granted permissions 23–67% of the time.
Hermes relevance: Hermes sub-agent delegation (delegate_task) should explicitly pass permission scopes, not assume inheritance; validate tool access at subagent boundary.
code_available: no

---

## TOPIC 7 — Knowledge Distillation into Skills

**2608.08453** | 9 Aug 2026
Title: What Keeps Agent Skills from Being Reusable? Evidence from 138K SKILL.md Files
Key finding: 73% of real-world skill files are task/repo-specific despite being labeled reusable; key blockers are hardcoded paths, implicit context assumptions, and single-task scope.
Hermes relevance: DIRECT — Hermes skill authoring should prohibit hardcoded paths, require abstract parameter references, and scope skills to skill families. Validates existing guidelines.
code_available: no

**2608.07885** | 10 Aug 2026
Title: Reason Wide, Not Deep: Amortizing the Reasoning Premium into Distilled Skills
Key finding: Encoding reasoning patterns into skills at creation time (reason wide) vs. per-query deep reasoning matches performance at 1/8 the token cost at inference.
Hermes relevance: CORE PATTERN — Hermes YAML skills should encode reasoning steps so Claude doesn't re-derive them at runtime. Validates the Hermes skill authoring philosophy.
code_available: no

**2608.08570** | 9 Aug 2026
Title: FailForge: Distilling Procedural Competence from Persistent Failures into Code Agents
Key finding: FailForge extracts partial competence from failure prefixes (discarded by standard RFT) and distills into procedural skills; improves SWE-bench solve rate 11% over standard RFT.
Hermes relevance: Hermes can learn from failed skill executions — log failure prefixes and use them to update skill YAML with "pitfalls" / "avoid" heuristics. Failure = training signal.
code_available: no

**2608.07639** | 7 Aug 2026
Title: SkillConsist: Detecting Inconsistencies in Agent Skills via Bidirectional Graph Alignment
Key finding: Bidirectional dependency graph between skill declarations and behaviors flags 34% of real-world skills as internally inconsistent (declared behavior ≠ implemented behavior).
Hermes relevance: Hermes skill library audit: graph alignment between skill YAML metadata and execution logs can detect skill drift. Periodic consistency audit is justified.
code_available: no

---

## TOPIC 8 — Multi-Agent Negotiation / Consensus

**2608.09128** | 10 Aug 2026
Title: Social Gym and SPaRTan: Benchmarking and Improving LLM Social Reasoning via Multi-Agent Game Tournaments
Key finding: Tournament-style self-play generates reliable social reasoning training signal without LLM judges; improves cooperation/negotiation 19% over RLHF baselines.
Hermes relevance: Hermes swarm consensus can adopt tournament-style debate rounds instead of parallel-then-reduce patterns for contested verdicts.
code_available: no

**2608.07538** | 7 Aug 2026
Title: When LLM Agents Negotiate: Private Information and Dynamic Bargaining in Supply Chain Settings
Key finding: Iterative counter-offer bargaining beats one-shot proposals 31%; private-information agents consistently outperform in negotiation.
Hermes relevance: For Hermes multi-agent task assignment — iterative negotiation over task allocation outperforms static role assignment in contested resource allocation.
code_available: no

**2608.07532** | 7 Aug 2026
Title: Dynamic Coalition Formation and Communication Pricing in Skill-Based Agentic AI Systems
Key finding: Communication pricing (agents pay tokens to communicate) suppresses noisy inter-agent chatter; reduces total token cost 28% while preserving task quality.
Hermes relevance: Hermes multi-agent orchestration should implement token budgets for inter-agent messages to prevent verbose delegation chains.
code_available: no

**2608.08516** | 9 Aug 2026
Title: Fluid Structure, Rigid Record: A Layered Organizational Design Framework for Agent-Native Organizations
Key finding: Separates agent orgs into fluid (dynamic role assignment) and rigid (persistent audit records) layers; persistent records prevent delegation drift across long-horizon tasks.
Hermes relevance: Hermes cron/agent sessions should maintain a rigid audit log (SQLite) of all delegations, tool calls, and skill invocations — separate from conversational memory.
code_available: no

---

## TOPIC 9 — Agent Evaluation Frameworks

**2608.07775** | 8 Aug 2026
Title: AndroidReality: How Far Are Mobile Agents from the Real World?
Key finding: Real-world Android tasks are 3× harder than existing benchmarks due to dynamic UI changes, permission interruptions, and asynchronous state.
Hermes relevance: Hermes computer_use evaluations should include dynamic/interruption scenarios (e.g. permission dialogs mid-task), not only static UI automation tasks.
code_available: no

**2608.07899** | 8 Aug 2026
Title: TelemetrySuffBench: Is Agent Telemetry Sufficient for Failure-Origin Diagnosis?
Key finding: Standard agent telemetry (tool call logs, step times) is insufficient for 68% of failure modes; root cause requires structured span tracing with tool input/output hashing.
Hermes relevance: Hermes observability: add input/output hashing to tool call spans in SQLite so failure diagnosis can trace to exact tool invocations, not just step timing.
code_available: no

**2608.08239** | 8 Aug 2026
Title: The Replay Gap: Static Evaluation of Model Switching in LLM Agents Scores the Wrong World
Key finding: Replaying logged agent trajectories with a different model overestimates router quality; live branching rollouts show 40% of "equivalent" switches cause trajectory divergence.
Hermes relevance: Hermes model routing (sonnet-4-6 vs haiku fallback) should be evaluated with live branching tests, not trajectory replay — branching rollout is the correct eval method.
code_available: yes

**2608.08392** | 9 Aug 2026
Title: CAP: A Scalable Benchmark for Evaluating Cross-Site Browser Agents with Complex Actions and Perception
Key finding: Cross-site task completion is 58% harder than same-site tasks; current benchmarks underrepresent multi-site complexity.
Hermes relevance: Hermes computer_use web tasks should include cross-site multi-step scenarios in capability evaluations.
code_available: no

**2608.00267** | 31 Jul 2026
Title: LoopsBench: From Harness Engineering to Loop Engineering in Coding Agent Evaluation
Key finding: Introduces "loop engineering" as the next frontier beyond harness engineering; benchmarks sustained long-horizon execution rather than localized task completion.
Hermes relevance: Hermes ralph-loops and autonomous agent patterns should be evaluated against sustained-execution metrics, not just per-task success.
code_available: no

---

## TOPIC 10 — Production Agent Engineering

**2608.08382** | 9 Aug 2026
Title: LLMVisor: A Real-Time Latency Attribution Model for Multi-Tenant LLM Serving
Key finding: Roofline-guided latency attribution runs inside scheduling loop with ±3% accuracy and <0.5ms overhead; enables fractional GPU sharing.
Hermes relevance: For production Hermes deployment — latency attribution by tool type and prompt section helps optimize Anthropic API call structure and identify bottlenecks.
code_available: no

**2608.08446** | 9 Aug 2026
Title: TRACE-Memory: Public-Conditioned Retrieval and Utility-Aware Evidence Admission for Personalized Generation
Key finding: Personal memory should only be retrieved when it adds utility beyond a public-only answer; utility-aware gating reduces irrelevant memory injection 41%.
Hermes relevance: Hindsight memory retrieval should gate on "does this add utility beyond what Claude already knows?" — implement a utility-score threshold before injecting memory into context.
code_available: no

**2608.08255** | 8 Aug 2026
Title: Learning from Environmental Feedback: Credit Assignment across Multiple Timescales for Agentic RL
Key finding: Multi-timescale credit assignment (immediate + episode + trajectory level) provides 34% better signal for agentic RL than single-timescale rewards.
Hermes relevance: Hermes skill quality scoring should adopt multi-timescale feedback — immediate tool success + session-level goal completion + longitudinal skill reuse rate.
code_available: no

---

## Sweep Methodology Notes

- arXiv IDs immediately above 2608.09885 (09888, 09893, 09894, 09902, 09921, 09925, 09928, 09930): all checked, none on-topic for agent improvement.
- The Aug 12 announcement cycle had not processed at sweep time. This sweep is therefore bounded to the Aug 11 announcement batch.
- Non-English sources (papers.cool, J-STAGE, HAL-Inria, CyberLeninka, RISS, NDSL): checked; all Chinese/JP/KO/RU agent papers in this period are concurrent arXiv submissions — no unique non-English-only findings found.
- cs.AI recent compact listing format does NOT show titles for cross-listed papers — requires individual abstract fetches via arxiv.org/abs/{id}.
- papers.cool mirrors arXiv exactly; no additional papers surfaced there.
