# Agent Runtime Behaviour: Research Findings 2025–2026

Compiled from: arXiv (EN + Chinese institution papers), CyberLeninka (Russian academic), HN, Reddit r/LocalLLaMA.
Full report: `/tmp/research_runtime_behaviour.md`
Focus: loop guardrails, tool schema efficiency, multi-turn state, parallel batching, self-correction.

---

## 1. Loop Guardrails & Failure Recovery

### Phantom Guardrails (arXiv:2607.13083, Jul 2026)

- **25%** phantom guardrail insertion rate (15/60 runs) in LLM-based harness proposers; **0%** on featureless control input.
- Conditions: rule-shaped pattern + open-ended rule set + failure-presupposing instruction. Remove any one → fabrication disappears.
- Add-only accept loops cause re-entry even without the presupposing instruction.
- Suppression-only acceptance is blind to phantom guardrails.
- **Hermes:** Fixed thresholds safer than adaptive. Counterfactual oracle required for any self-optimization.
- https://arxiv.org/abs/2607.13083

### MERIT: Typed Failure Memory (arXiv:2608.05906, Aug 2026)

- Dual-polarity store (corrections + unsuccessful directions) typed by failure category.
- Results: **66.34% → 69.79% Spider (+3.45pp); 47.35% → 48.44% BIRD (+1.09pp)** over stateless iterative repair.
- 5–7 failure type categories; schema-local experience most consistent.
- Negative memory (what NOT to retry) as important as positive corrections.
- **Hermes:** Tool failure records need: failure_type + attempts_tried + resolution. Prevents repair cycling.
- https://arxiv.org/abs/2608.05906

---

## 2. Tool Selection & Schema Efficiency

### MemTool: Dynamic MCP Context Eviction (arXiv:2507.21428, Jul 2025)

- Tool schema eviction more impactful than message compression for multi-turn agents.
- ScaleMCP (100 turns, 13+ LLMs): Reasoning LLMs autonomous eviction: **90–94%** tool removal efficiency; medium models: **0–60%**.
- Hybrid mode: best task completion + effective removal.
- **Hermes:** `micro_compact every 3 turns` = message compression only. Tool schema eviction is a separate missing layer. Small models need deterministic eviction; large models can use autonomous.
- https://arxiv.org/abs/2507.21428

### HyperTool: Code-Block Batching (arXiv:2606.13663, Jun 2026)

- Step-wise tool calls create "execution-granularity mismatch" — deterministic sub-workflows unfolded into model-visible decisions.
- MCP-Universe benchmark: Qwen3-32B **15.69% → 35.29%** (+125%); Qwen3-8B **9.93% → 33.33%** (+235%). Surpasses GPT-OSS and Kimi-k2.5.
- Wraps multiple tool calls into single code block; intermediate results stay local to the block.
- **Hermes:** For read-file → parse → write-file chains, wrap as compound tool call. Extends parallel batching to sequential dependencies.
- https://arxiv.org/abs/2606.13663

### LLM-Tool Compiler: Type-Affinity Fusion (arXiv:2405.17438, May 2024)

- Runtime fusion of similar-type tool operations (e.g., multiple web_search) into unified function.
- Large-scale Copilot platform: **4× more parallel calls; −40% token cost; −12% latency**.
- JIT compilation analogy — runtime type similarity profiling, then group before LLM sees them.
- **Hermes:** Type-affinity heuristic for parallel call scheduling: group same-type tools before presenting to LLM.
- https://arxiv.org/abs/2405.17438

### AOrchestra: Per-Step Context Narrowing (arXiv:2602.03786, Feb 2026, Peking U / Alibaba)

- Agent as `(Instruction, Context, Tools, Model)` tuple, concretized per step by orchestrator.
- GAIA/SWE-Bench/Terminal-Bench: **+16.28% relative improvement** vs strongest baseline (Gemini-3-Flash).
- Chinese institution paper.
- **Hermes:** Narrow subagent context per sub-task. Full history forwarding is the opposite of this pattern and degrades performance.
- https://arxiv.org/abs/2602.03786

### Fewer Tools Often Beat More (Sketch.dev, HN 447pts, May 2025)

- Production: 9-line loop + single `bash` tool is surprisingly effective for a wide class of tasks.
- No tool selection overhead; no schema management complexity; model adapts behavior.
- **Hermes:** Tool descriptions should explain *when not to use* a tool. Task-type tool presets (full / standard / minimal) would reduce schema noise.
- https://news.ycombinator.com/item?id=43998472 | https://sketch.dev/blog/agent-loop

---

## 3. Multi-Turn State Management

### General AgentBench: Context Ceiling & Verification Gap (arXiv:2602.18998, Feb 2026, CMU)

- **Context ceiling:** More sequential turns ≠ better results. Context accumulation rate exceeds useful signal rate.
- **Verification gap:** Parallel trajectory sampling fails — agents cannot reliably self-verify best result without ground truth.
- All 10 tested LLM agents show "substantial performance degradation" in general-agent vs domain-specific settings.
- **Hermes:** `agent.max_turns=500` is a ceiling, not a target. Adaptive compression trigger: use tool-result density (proportion of raw tool output in context), not just total length. `verify_on_stop=auto` correctly addresses verification gap.
- Code: https://github.com/cxcscmu/General-AgentBench
- https://arxiv.org/abs/2602.18998

### Reddit r/LocalLLaMA: Parallel Local Agent Practitioner Report (Dec 2025)

- 2 weeks, Qwen2.5-Coder-32B on RTX 3090, 3 parallel Ollama instances.
- Over-isolation: incompatible changes (wrong function signatures). Over-sharing: eliminates parallel benefit.
- Hard VRAM ceiling: 3×32B instances exceed VRAM even with shared weights → dropped to 14B with quality loss.
- **Hermes:** Interface/schema context only between parallel agents, not full history. VRAM ceiling bounds parallel fan-out independently of orchestration quality.
- https://www.reddit.com/r/LocalLLaMA/comments/1pf0qbz/been_experimenting_with_parallel_agent_execution/

---

## 4. Agent Self-Correction Patterns

### PreFlect: Prospective Reflection (arXiv:2602.07187, Feb 2026)

- Retrospective reflection: act → fail → correct. Prospective: critique and refine plan *before* execution.
- Distills planning errors from historical trajectories — recurring success and failure patterns.
- "Significantly improves overall agent utility, outperforming strong reflection-based baselines and several more complex agent architectures."
- **Hermes:** Plan-critique step before multi-step sequences: outline planned tool calls → identify likely failure modes → revise plan. Most valuable for multi-turn agentic tasks where late-stage failures are expensive.
- Code: https://github.com/wwwhy725/PreFlect
- https://arxiv.org/abs/2602.07187

### REGREACT: Observe-Diagnose-Repair (ODR) Loop (arXiv:2604.12054, Apr 2026)

- 7-stage multi-agent pipeline; each stage: validate → diagnose → repair. Corrections for both model hallucinations AND source cross-reference errors.
- Outperforms GPT-4o single-pass on all structural and semantic metrics.
- **Hermes:** `verify_on_stop` = task-level. ODR = tool-call-level. Lightweight schema validator at each tool boundary prevents downstream error cascade. Complementary, not redundant.
- Code: https://github.com/RECOR-Benchmark/RECOR
- https://arxiv.org/abs/2604.12054

### LLM Agents Making Agent Tools (arXiv:2502.11705, ACL 2025)

- Agents dynamically synthesize Python tool functions from task descriptions; self-critique tool before use.
- Extreme self-correction: rewriting the tool itself, not just retrying the call.
- **Hermes (soft version):** Tool call fails with schema error → model suggests improved schema/description → cache session-local improvement for subsequent calls.
- ACL Anthology: https://aclanthology.org/2025.acl-long.1266/
- https://arxiv.org/abs/2502.11705

---

## 5. Non-English Sources (CyberLeninka / Russian Academic)

### AI Agent Maturity in Russian Enterprises (2026)

- 5-level maturity model. Russian companies cluster at "defined" / "managed" levels.
- Full autonomy virtually nonexistent. Hybrid human-in-the-loop models dominate.
- Greatest potential: repetitive tasks with rare non-standard situations.
- Language: Russian (*Бизнес-информатика*, HSE / VAK / RSCI), 2026.
- Validates Hermes's fixed warning thresholds and `verify_on_stop` as appropriate production posture.
- https://cyberleninka.ru/article/n/maturity-model-and-success-factors-for-the-implementation-of-ai-agents-in-russian-companies

### Multi-Agent LLM Systems Modelling (2025)

- Russian academic review (*Discrete and Continuous Models*, RUDN / VAK), 2025.
- Primary multi-agent failure modes: context drift, state synchronization, inter-agent protocol overhead.
- Independent non-English confirmation of General AgentBench context ceiling finding.
- https://cyberleninka.ru/article/n/on-modelling-multi-agent-systems-based-on-large-language-models

---

## Priority Action Items (Hermes Config/Code)

| Priority | Finding | Suggested Change |
|----------|---------|-----------------|
| P1 | Context ceiling (§3) | Adaptive compression by tool-result density, not just message length |
| P1 | HyperTool batching (§2) | Group sequential deterministic sub-workflows into compound tool calls |
| P2 | Phantom guardrails (§1) | Counterfactual oracle before accepting any new guardrail in self-optimization |
| P2 | MERIT failure typing (§1) | 5–7 category failure taxonomy + typed resolution history in retry logic |
| P2 | PreFlect reflection (§4) | Pre-execution plan critique for multi-step sequences |
| P3 | ODR per-tool validation (§4) | Lightweight schema validation at each tool boundary |
| P3 | Scoped subagent context (§2) | Narrow context forwarded to delegated subagents |
| P3 | Tool schema eviction (§2) | Track relevance decay per tool; evict stale schemas independently of message compression |
