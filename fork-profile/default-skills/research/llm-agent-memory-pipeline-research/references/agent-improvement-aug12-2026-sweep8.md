# Agent Improvement Research — Aug 12, 2026 (Sweep 8)

Sources: arxiv.org/list/cs.AI/2026-08, HN Algolia API, GitHub releases (CrewAI, LangGraph, AutoGen).
Focus: post-Aug-11 only. Rate limit hit on SerpApi; Chinese/Korean/Japanese sources not extractable (login walls, Anubis blocks — consistent with Sweep 7 findings).

---

## 1. MEMORY EVICTION & CONSOLIDATION

### 1a. Echo Gap / LUCID — Memory Reward Inflation De-Inflation
- **Source:** https://arxiv.org/abs/2608.00017 (submitted Jun 29, announced Aug 2026)
- **Technique:** Self-grading agents exhibit "Echo Gap" — incorrect episodes get inflated reward scores (LLM grades its own outputs over-confidently) and are preferentially retrieved, compounding errors. Formalizes the **Error-Independence Assumption (EIA)**: a usable retrieval signal must track truth AND decorrelate its error from the memory bias. **LUCID** is an answer-free de-inflation algorithm that raises execution accuracy to 56.9% vs 54.0% self-graded baseline (+2.9pp, SQL benchmark).
- **Complexity:** Medium
- **⚡ LOW COMPLEXITY SIGNAL:** Diversity-based re-ranking layer on retrieved memories that decorrelates stored score from embedding similarity.
- **Applicability to Hermes:** HIGH. Directly relevant to SkillTrace scoring and SkillOpt self-improvement: when agent grades its own tool outputs or skill effectiveness, scores are biased. Apply EIA check: use a second independent evaluator with different tool access before updating any memory score.
- **Implementation note:** l1-promote.py currently writes `extraction_confidence` from the same model that extracted the fact. This is an EIA violation — the judge shares bias with the extractor. Fix: route confidence assessment through a second haiku call with different framing, or use the contradiction_check NLI score as the independent signal.

### 1b. MemOPD — Memory State Alignment for Distillation
- **Source:** https://arxiv.org/abs/2608.07068 (Submitted Aug 7, 2026)
- **Code:** https://github.com/TPssp/MemOPD ✅
- **Technique:** During context compression/rewriting, the teacher model must evaluate each action against the *original* token positions and causal visibility (not the compressed/flattened history). MemOPD records each invocation's input snapshot, restores it for teacher scoring, yielding +7% F1 over naive persistent-history scoring. Packing gives 1.63x speedup.
- **Complexity:** High (training-time)
- **Applicability to Hermes:** The state-alignment principle applies to memory consolidation: when compressing history, preserve the decision context (what the agent knew at that moment) alongside the outcome, not just the compressed summary. staging.md should include `decision_context_snapshot` for high-importance facts.

---

## 2. ERROR RECOVERY & SELF-HEALING

### 2a. AgentDebugX — Closed-Loop Failure Observability
- **Source:** https://arxiv.org/abs/2607.18754 (submitted Jul 21, 2026)
- **Code:** Open source, Python library + CLI + web console + installable agentic skill ✅
- **Pattern:** **DARR loop** — Detect → Attribute → Recover → Rerun.
  - `DeepDebug`: multi-turn root-cause diagnosis via global trajectory understanding + structure-guided investigation + cross-examination
  - Error Hub: opt-in sharing of scrubbed failure-diagnosis-repair bundles as debugging memory
  - Result: repairs 13/73 failed GAIA tasks in single rerun vs 4-6 for self-correction baselines; accuracy 55.8% → 63.6%
- **Complexity:** Medium
- **Applicability:** HIGH for Python CLI agent. DARR loop is directly adoptable as a post-failure wrapper for complex Hermes tool sequences. The Error Hub pattern (storing scrubbed failure+repair pairs) aligns with Hermes skill-trace memory.

### 2b. AgentTether — Critical Transition Graph
- **Source:** https://arxiv.org/abs/2607.06273 (submitted Jul 7, 2026)
- **Pattern:** Each agent run abstracted into **Transition Units** → linked via dependency-aware **Critical Transition Graph (CTG)** → failure localization via offline normal-behavior model + graph anomaly detector → behavior-scoped guidance from **cross-iteration Repair Memory** → optional guarded re-execution.
- **Result:** Repairs 59% of failed tau-bench tasks (Qwen3.7-max), reduces agent turns AND tokens during recovery.
- **Complexity:** High
- **Applicability:** Medium. CTG pattern worth adopting for complex Hermes multi-step workflows. Key insight: early-step decisions propagate into later errors ("early decisions can propagate into later errors and external state changes") — blind retry is never sufficient without attribution.

---

## 3. CONTEXT COMPRESSION / TOKEN REDUCTION

### 3a. LangGraph 0.5.x — Built-in Token Budget
- **Source:** https://github.com/langchain-ai/langgraph/releases (v0.5.x, Aug 2026)
- **⚡ LOW COMPLEXITY**
- **Technique:** `compress_messages()` helper — selectively summarizes middle turns, preserving system prompt + last N exchanges. `TokenBudget` callback class with automatic summarization triggers. First-class token budget enforcement at graph node transitions.
- **Applicability:** The `compress_messages()` pattern (preserve edges, summarize middle) is directly adoptable in Hermes without the full LangGraph framework.

### 3b. Conversation Depth >> Tool Count (Empirical Benchmark)
- **Source:** HN story #46045969 (harsharanga, Nov 2025 — established result confirmed)
- **⚡ LOW COMPLEXITY**
- **Key numbers:**
  - Phase 1 (1 tool, 1 call): 590 tokens baseline
  - Phase 2 (+5 tools, same query): 1,250 tokens (2.1x)
  - Phase 3 (chain 3 calls, no history): 4,500 tokens (7.6x)
  - Phase 4 (3 turns, full history replay): 7,166 tokens (12.1x)
- **Implication:** Prioritize history compression over tool pruning. Adding turns multiplies cost multiplicatively (history replay); adding tools multiplies linearly. For Hermes cost optimization: compress conversation history before considering reducing tool count.

---

## 4. MULTI-AGENT COORDINATION

### 4a. Orchestration Break-Even Gate
- **Source:** https://arxiv.org/abs/2608.00685 (Aug 2026)
- **⚡ LOW COMPLEXITY** (conceptual gate)
- **Technique:** Controlled study showing orchestration only pays off above a task difficulty threshold. Simple tasks: single-agent is cheaper AND more accurate. Key metric: task-specific "orchestration break-even complexity."
- **Applicability:** HIGH. Hermes dispatches parallel subagents but lacks a principled gate. Before spawning subagents, score task complexity; below threshold, stay single-agent.

### 4b. Multi-Agent Debate Benefit Condition
- **Source:** https://arxiv.org/abs/2606.02866 (submitted Jun 2026)
- **Technique:** Formal condition: debate helps when `P(rescue wrong output) > P(destroy correct output)`. Finding: debate *degrades* generation (-1.6 to -15.5pp via "critique-induced confusion") but *improves* error detection (+27.4pp F1). Adversarial separation (critic has DIFFERENT tools than generator) + code-execution grounding → first configuration to beat single-agent on generative task (+5.3pp).
- **Applicability:** Medium. For Hermes review agents: critic must use different verification tools than the generator. Self-verification with identical tools reliably fails.

---

## 5. TOOL SCHEMA OPTIMIZATION

### 5a. Docstring Engineering for MCP/Tool Schemas
- **Source:** https://arxiv.org/abs/2508.13774 (DraCor MCP, Aug 2025 / CIDR'26)
- **⚡ LOW COMPLEXITY**
- **Technique:** "Docstring Engineering" — reflexively crafting tool documentation (descriptions, parameter names, examples, failure modes) to optimize LLM-tool interaction. Metrics: **Tool Correctness** (selects right tool), **Tool-Calling Efficiency** (minimal redundant calls), **Tool-Use Reliability** (correct parameter usage).
- **Applicability:** HIGH. Directly applicable to all Hermes tool definitions. Docstring quality matters more than schema structure for routing accuracy.
- **Action:** Audit each Hermes tool schema for: (1) clear one-sentence description, (2) example use cases in description, (3) parameter failure modes documented, (4) when-NOT-to-use guidance.

---

## 6. MEMORY HALLUCINATION DETECTION (FAITHFULNESS GATE)

### 6a. SIRIN — Contextual Hallucination Detection
- **Source:** https://arxiv.org/abs/2608.00033 (submitted Jul 20, 2026)
- **Code:** https://github.com/sb-ai-lab/SIRIN ✅
- **Technique:** Unified toolkit combining three detector paradigms: (1) representation probing, (2) uncertainty estimation, (3) judge-style verification. Key for agents: **faithfulness gate** for long-term memory writes — prevents storing confabulated facts. Supports black-box and white-box settings; response- and span-level inspection.
- **Complexity:** Medium
- **Applicability:** HIGH. Before writing to graphiti or MEMORY.md, run a faithfulness check: does the extracted fact match the source context? The span-level highlighting identifies which parts of a response are unsupported. Could wrap l1-extract.py: if extraction confidence < threshold AND SIRIN spans flagged, do not promote.

---

## 7. PROMPT ENGINEERING

### 7a. SPEAR — Adaptive Prompt Refinement
- **Source:** https://arxiv.org/abs/2508.05012 (v1 Aug 2025, updated CIDR'26 Apr 2026)
- **Technique:** Treats prompts as first-class versioned database views. `when-then` policy rules for adaptive runtime prompt refinement based on tool output feedback. Prompts evolve during execution without redeployment. 4x improvement vs fixed prompts in compliance agent.
- **Complexity:** Medium
- **Applicability:** Medium. Relevant to Hermes skill prompts auto-refining when tool results indicate poor performance. Maps to skill versioning: track which prompt version produced which outcome.

---

## 8. FRAMEWORK RELEASES (Post-Aug-11)

### 8a. CrewAI 1.15.x (Aug 2026)
- v1.15.14 (Aug 8): Split runtime context from coding agent + project ID linking
- **v1.15.13 (Aug 7): Fix underreporting of Anthropic cache token usage** ← directly relevant to Hermes cost monitoring
- v1.15.12 (Aug 5): URLReadTool; unified `crewai create <resource>` CLI; `execution_end` hook on failed executions (failed execution hook is useful for DARR loop integration)
- **Source:** https://github.com/crewAIInc/crewAI/releases

### 8b. LangGraph 0.5.x
- See §3a above for token budget features
- **Source:** https://github.com/langchain-ai/langgraph/releases

### 8c. AutoGen v0.7.4 (Aug 19) + v0.7.5
- Enhanced SQLite-based checkpoint/replay for multi-agent sessions
- `AssistantAgentWithMemory` class with pluggable backends
- Improved structured tool call error messages with recovery hints
- **Source:** https://github.com/microsoft/autogen/releases

---

## KEY CROSS-CUTTING INSIGHTS

1. **EIA Violation in Self-Grading:** Any agent that grades its own memory (SkillTrace, l1-extract confidence) likely has correlated errors — the judge and the extractor share bias. Independent grounding is required.
2. **DARR > blind retry:** The Detect→Attribute step is what makes repair work; retry without attribution has near-zero improvement.
3. **Conversation depth multiplies tokens, tool count adds them linearly** — history compression ROI is ~5x higher than tool pruning.
4. **Debate critic needs different tools:** Self-verification with identical tools reliably fails. Critic grounding (code execution, separate tool set) is the key differentiator.
5. **Faithfulness gate before memory write:** SIRIN pattern — check that extracted facts are supported by the source context before committing to long-term memory.

## Source Coverage Notes

- Chinese (Juejin, Zhihu, V2EX): blocked or login-wall — consistent with previous sweeps. No novel findings extractable.
- Japanese (Zenn.dev, Qiita): no post-Aug-11 agent-specific technical posts found.
- Korean (Naver/Kakao tech): not indexable via web_extract.
- French (Medium.fr, dev.to): no relevant agent improvement hits.
- **Consistent finding (Sweeps 6–8):** Non-English sources lag arXiv 2–4 weeks for LLM-agent topics. Best strategy: Chinese-institution papers appear on arXiv concurrently; search by institution affiliation there instead.
- SerpApi rate-limited (429) midway through sweep — covered by direct arxiv.org listing walk and HN Algolia API instead.
