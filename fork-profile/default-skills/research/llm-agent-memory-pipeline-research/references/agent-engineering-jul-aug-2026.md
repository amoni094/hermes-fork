# Agent Engineering Findings — Jul–Aug 2026

Research sweep: Anthropic engineering blog, LangChain Deep Agents, arXiv papers,
Python.org, ByteByteGo. Primary sources: direct URL extraction (not search summaries).
Focused on practical improvements not yet in the Aug 11 2026 known-implemented baseline.

---

## 1. Interfaces Beat Examples — Claude 5-Gen Context Engineering (Anthropic, Jul 24 2026)

**Source:** https://claude.com/blog/the-new-rules-of-context-engineering-for-claude-5-generation-models

Anthropic removed >80% of Claude Code's system prompt for Claude Opus 5 / Fable 5 with **no measurable drop** on coding evals. Key shifts (each one independently applicable):

| Old practice | New practice | Applies to |
|---|---|---|
| Few-shot examples | Well-designed tool interface (schema as the teacher) | All tool-using agents |
| Hardcoded rules (`"DO NOT..."`) | Positive heuristics + model judgement | System prompt authoring |
| Repeat instruction in both system prompt and tool description | Instructions in tool description only | Tool schema design |
| All context upfront | Progressive disclosure + deferred loading | Skills, tool schemas |
| Simple specs (markdown plans) | Rich references (test suites, rubrics, HTML artifacts) | Planning/spec artifacts |
| Manual memory hotkey | Auto-memory (agent writes memories automatically) | CLAUDE.md / skill files |

**Deferred tool loading (new pattern):** A `ToolSearch` meta-tool returns full schemas on demand. Tools without a query match don't consume context. Claude Code uses this for "Task tools" that don't load until needed. Applicable to any harness with >20 active tools.

**Hermes application:**
- Audit skills that embed DO NOT rules → replace with positive heuristics.
- Remove duplication between system prompt and tool descriptions.
- Refactor skills using few-shot examples → rely on schema `enum` / typed parameter design instead.
- Implement `tool_search(query)` meta-tool for deferred schema access on the ~60-tool library.
- Run `hermes doctor` / `/doctor` equivalent to audit conflicting instructions across skill files.

---

## 2. Scaling Managed Agents: Brain–Hands Decoupling (Anthropic, Apr 8 2026)

**Source:** https://www.anthropic.com/engineering/managed-agents

### Three-interface architecture (session / harness / sandbox are independent)

```
Session (durable event log)   ← getEvents(slice), emitEvent(id, event), wake(sessionId)
Harness (stateless brain)     ← getSession(id), calls execute(name, input) → string
Sandbox (container/hand)      ← provision({resources}), execute(name, input) → string
```

Each interface can fail and restart independently. No "pet" container that holds state.

**p50 TTFT dropped 60%; p95 dropped >90%** vs the fully-coupled design. Harnesses are stateless — restart with `wake(sessionId)`, read event log, resume. Containers die without losing session state.

### Session-as-external-context-object

The session log lives **outside** the context window. `getEvents(slice)` injects only the needed slice of history per turn. Agents can: pick up from last stop, rewind before a decision, re-read the lead-up to a specific action. All context transformations (compaction, trimming) happen in the harness; the session log is immutable append-only.

> "Context can be an object in a REPL that the LLM programmatically accesses by writing code to filter or slice it." — arXiv:2512.24601

**Context anxiety:** Claude Sonnet 4.5 prematurely wrapped up tasks near context limit. Fix (context resets) became dead weight on Opus 4.5. Lesson: **harnesses encode assumptions that go stale as models improve** — design for evolvability.

### Security: credentials never in sandbox

- Git: clone with token at init; token not available inside sandbox.
- MCP OAuth: vault outside sandbox; proxy fetches per-session token; harness never sees it.

**Hermes application:**
- Write each agent loop turn to SQLite before calling the model → `resume <session_id>` after crash.
- Connect `session_search(session_id=..., around_message_id=...)` as a selective context slice accessor.
- Review harness for context-anxiety guardrails added for older models — remove if no longer needed.

---

## 3. Deep Agents v0.7 — 65% Base Token Reduction (LangChain, Jul 29 2026)

**Source:** https://www.langchain.com/blog/deep-agents-v0-7

### Three changes that produced 65% drop (~6K → ~2K base input tokens/turn)

1. **Removed hidden base system prompt** — general guidelines and tool-usage prose eliminated. Tool schema conveys usage.
2. **Trimmed built-in tool descriptions by 43%** — verbose NL prose → tighter schema-centric descriptions.
3. **TodoListMiddleware opt-in** — planning scaffolding slightly *hurt* performance on capable models. Still useful for: long multi-step tasks, less capable models, UI-facing cases where a visible plan matters.

### 3-Tier Context Compression (cascade order — try each before escalating)

**Source:** https://www.langchain.com/blog/context-management-for-deepagents (Jan 28, 2026)

| Tier | Trigger | Action | Reversibility |
|------|---------|--------|---------------|
| **Offload tool results** | Tool result >20K tokens | Write to filesystem; replace inline with pointer + 10-line preview | Fully reversible — agent reads file on demand |
| **Offload stale tool inputs** | Context at 85% capacity | Replace write/edit tool args (already on disk) with path pointer | Reversible via filesystem |
| **Summarization** | Offloading still insufficient | LLM generates session intent + artifacts + next steps; original conversation archived to filesystem | Lossy — but raw preserved on disk |

Key insight: **offloading is cheaper and more reversible than summarization**. Summarize only as last resort.

**Needle recovery test:** embed a key fact early → force summarization → require the agent to retrieve it via `read_file` on the archived conversation. Tests whether compression preserved recoverability, not just summary coherence.

**Summarization prompt pattern that reduced goal drift:** include dedicated fields for "session intent" and "next steps" (not just free-form summary).

### Configurable middleware stack (new in v0.7)

```python
agent = create_deep_agent(
    model="anthropic:claude-sonnet-5",
    middleware=[
        SummarizationMiddleware(
            model="fireworks:accounts/fireworks/models/kimi-k3",
            trigger=("fraction", 0.5),  # 50% instead of default 85% (for stress testing)
            summary_prompt="Summarize the conversation so far, keeping any file paths and decisions verbatim...",
        ),
    ],
)
```

**Hermes application:**
- Implement 3-tier compression: auto-offload tool results >4K tokens → `~/.hermes/offload/<session_id>/<turn>_<tool>.txt`, replace inline with pointer + 5-line preview.
- At 75% context budget: scan for write/edit tool calls already reflected on disk; evict the argument content.
- Fall back to full summarization only after offloading insufficient.
- Add "session intent" + "next steps" fields to Hermes compaction summary prompt.
- Stress-test compression by triggering at 25-50% threshold to generate more events for evals.

---

## 4. Progressive Disclosure Depth: Empirical Study (arXiv:2607.17598, Jul 20 2026)

**Source:** https://arxiv.org/html/2607.17598v1  
He et al., UC Davis / Zhejiang University / University of Hong Kong

**First controlled study** of progressive disclosure depth in agent skill systems across three harnesses and three model families on ∞Bench.

### Key findings

| Finding | Implication |
|---|---|
| **One level of disclosure is enough** | Flat SKILL.md (always-loaded description → body + references/ on activation) is optimal |
| **Hierarchical (2-level) never wins; sometimes catastrophically fails** | En.MC accuracy collapsed 0.91 → 0.64 on one model/harness combo with 2-level hierarchy |
| **Scale determines when disclosure matters** | Single doc: strong agents navigate raw well; 20 books: raw collapses (0.26 accuracy), flat holds (0.46) |
| **Progressive disclosure buys context, not intelligence** | Doesn't improve reasoning; prevents context starvation when corpus is large |
| **Always-loaded descriptions are cache-friendly** | Caching them reduces disclosure cost further — highest-ROI cache target |

**Library-scale cost comparison (K=20 books, English open QA):**
- Raw navigation: 68.3M tokens/question, accuracy 0.26, uncached cost ~$52
- Flat disclosure: 32.5M tokens/question, accuracy 0.46, uncached cost ~$25
- Both more accurate AND half the cost at scale.

**Hermes application:**
- **Do not add a second routing layer** (meta-skill-index or skill-of-skills hierarchy) — empirically harmful.
- Current flat skill header (≤100 tokens) → always-loaded disclosure index. This is the validated design.
- Skill bodies + references/ load on activation only — correct one-level flat disclosure.
- The skill header block is the highest-ROI prompt cache target in Hermes.

---

## 5. Explainable Model Routing: Topaz (arXiv:2604.03527, Apr 4 2026)

**Source:** https://arxiv.org/html/2604.03527v1  
Okamoto, Kaplan Erol, Riedl — Georgia Institute of Technology

**Problem:** Silent model routing (cheap model for simple tasks, expensive for complex) lacks auditability. Developers can't distinguish intelligent efficiency from budget-forced quality compromise.

**Topaz framework:**
1. **Skill-based profiling:** Decompose model capabilities from public benchmarks into a shared skill taxonomy (logical reasoning, math, coding, summarization, etc.) — not aggregate scores.
2. **Cost-aware routing:** Two algorithms — fixed-budget optimization (maximize quality within budget) and multi-objective optimization (pareto-optimal tradeoff).
3. **Developer-facing explanations:** Natural language rationale per routing decision — which model, why, what tradeoffs.

**Demonstrated allocation behavior at $50 budget:**
- Gemini-3 Pro: Knowledge Base Search, Refund Calculation, Response Drafting (advanced reasoning + math)
- Mistral-Small: Ticket Classification, Escalation Summary (basic summarization, instruction-following)

**Hermes simplified cascade (MEDIUM complexity):**
```python
def route_to_model(task_text: str) -> str:
    """Two-tier cascade based on task signals."""
    simple_keywords = ["summarize", "what is", "list", "define", "translate", "classify"]
    complex_signals = ["implement", "debug", "analyze", "design", "write code", "refactor"]
    
    lower = task_text.lower()
    if any(kw in lower for kw in simple_keywords) and not any(s in lower for s in complex_signals):
        return "anthropic/claude-haiku-4-5"  # or cerebras/gpt-oss-120b (free)
    return "anthropic/claude-sonnet-4-6"  # default
```
Expected savings: 30-50% cost reduction on mixed workloads.

---

## 6. Python stdlib `typing.tool` Pre-PEP (Python Discuss, May 2026)

**Source:** https://discuss.python.org/t/pre-pep-discussion-typing-tool-inspect-tool-schema-close-the-zod-gap-for-python-agent-dev/107431

**Status:** Pre-PEP parked pending ecosystem maturity. Pydantic team building underlying infrastructure (PEP 746). Not in stdlib yet.

**What was proposed:**
```python
from inspect import tool_schema

def search_web(query: str, limit: int = 10) -> list[dict]:
    """Search the web for recent results.
    Args:
        query: The search query
        limit: Max results to return
    """
    ...

tool_schema(search_web)
# → {"name": "search_web", "description": "...", "parameters": {...}}
```

**What to use now:**
- `pydantic-ai`: `@tool` decorator generates JSON schema from type hints + docstrings
- `instructor`: Pydantic models → Anthropic/OpenAI tool schemas
- `pydantic.create_model()`: dynamic schema generation

**Why this matters:** Python agent frameworks (OpenAI SDK, LangChain, LlamaIndex, Pydantic AI, Semantic Kernel, FastMCP, autogen, instructor) each ship their own `@tool` decorator. Eleven competing implementations. TypeScript has Zod as a de facto standard. The pre-PEP shows the Python community actively working toward standardization.

**Hermes application:** Migrate hand-written JSON Schema dicts to Pydantic-based tool schema generation for: IDE completion, automatic LLM argument validation, and forward-compatibility with stdlib `inspect.tool_schema()`.

---

## 7. Trending Frameworks (ByteByteGo, Mar 2026 / LangChain, Jul 2026)

**Source:** https://blog.bytebytego.com/p/top-ai-github-repositories-in-2026

| Project | Stars | Key Property |
|---------|-------|---|
| **OpenClaw** (fka Clawdbot/Moltbot) | 210K+ | Personal local-first AI; writes its own new skills from observed task patterns; 50+ integrations. **Risk:** skill repository lacks vetting for malicious submissions. |
| **Deep Agents** (LangChain) | OSS | Batteries-included agent harness with 3-tier compression, configurable middleware, filesystem-as-context-layer. `uv pip install -U deepagents`. v0.7: Jul 29, 2026. |
| n8n | OSS | Visual workflow + LangChain native AI; 400+ integrations; self-hosted. |
| Dify | OSS | Production-ready agentic workflow platform; MCP integration; multi-provider LLM. |
| Ollama | OSS | Local LLM management; Go-based; the backbone of local AI stack. |

**OpenClaw self-writing skills risk:** Any agent-generated skill should go through an eval gate (`skillopt_score.py` equivalent) before acceptance. The skill repository lacks rigorous vetting — malicious/incorrect self-written skills degrade the agent over time.

---

## 8. Proactive Event-Driven Agent Architecture (2026)

**Source:** https://www.zerotoai.in/blogs/proactive-ai-agents-event-driven-automation-2026

### 4-Pillar pattern

```
1. Event Listener (webhooks/cron/DB triggers)
2. Persistent State + Memory lookup (historical context + policy rules)
3. LLM Reasoning Engine + MCP tool execution
4. HITL Approval Gate (tiered by risk score)
```

**Risk tier gating:**
- Low risk (auto-execute): draft email, update CRM, summarize ticket
- High risk (human approval required): refund >$200, modify production DB, public statement

**Production rules:**
- **Idempotency keys:** SQLite table `processed_event_ids` prevents duplicate webhook → duplicate action
- **Hard execution caps:** max tool calls per event prevents infinite loops
- **Real-time logs:** all agent decisions + tool outputs + escalation queues visible

**Hermes application:**
- Hermes cron handles scheduled events. Missing: webhook ingestion + risk-tier HITL gating.
- Add FastAPI endpoint (`POST /webhook/event`) → dispatches to Hermes agent with event payload.
- Add SQLite idempotency table: `CREATE TABLE processed_events (event_id TEXT PRIMARY KEY, processed_at TIMESTAMP)`.
- Risk-tier config in skill frontmatter: `risk_tier: high` → requires user confirmation before execution.
- Max tool call cap per agent invocation.
