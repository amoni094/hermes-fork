# Third-Party AI Memory / Identity Framework Evaluation

Use this as a decision template when evaluating an external agent memory or identity framework
(e.g., Adam, MemGPT, Letta, OpenMemory, custom vault systems) against the existing Hermes stack.

## Evaluation Checklist

### 1. Harness compatibility
- Does it require a specific harness (OpenClaw, LangChain, custom gateway)?
- Is there a Hermes/MCP adapter? If not, is the work to build one proportional to the benefit?

### 2. Layer-by-layer overlap analysis
Map each framework layer against the current Hermes stack:

| Framework layer | What it does | Hermes equivalent |
|----------------|--------------|-------------------|
| Vault injection | Identity files loaded at boot | Hermes durable memory + MEMORY.md + SOUL.md |
| Mid-session search | Live memory retrieval | Hindsight (local_embedded) + MemPalace + session_search |
| Neural/associative graph | Concept-to-concept recall | MemPalace knowledge graph |
| Nightly reconciliation | Merge daily logs into core memory | hourly-hermes-chat-sync cron + Obsidian sync |
| Coherence monitor | Detect within-session drift | hermes-context-hygiene skill |

If every layer has a direct equivalent, the integration value is low.
If 2+ layers solve problems that are genuinely unaddressed, it may be worth adapting.

### 3. Marketing vs. substance filter
Red flags that indicate a project is mostly packaging over generic techniques:
- Claims of "quantum verification", "emergent consciousness", "identity sovereignty" without concrete ML evidence
- The actual mechanism is file-based context injection with a watchdog script — valid technique, but not novel
- "Production-validated" framed as proof of architectural superiority when it's evidence of personal use

Useful signals even in hype-heavy repos:
- Specific algorithmic insights (e.g., "scratchpad dropout as coherence signal")
- Concrete data structures or schema designs
- Real failure modes documented and mitigated

### 4. Portability check
- Are the memory files plain markdown / standard formats you could recover from?
- Can the memory layer survive a model swap, vendor change, or machine wipe?
- Does it depend on proprietary plugin formats or closed APIs?

### 5. Verdict framework

**Skip**: every layer covered by existing stack, harness-specific, no novel technique
**Borrow ideas**: novel concept or specific technique worth extracting, but not worth full install
**Integrate selectively**: one layer adds real value and is harness-agnostic
**Install fully**: multiple layers not covered, standard formats, MCP-compatible

## Case Study: Adam Framework (Jun 2026)

- Repo: https://github.com/strangeadvancedmarketing/Adam
- Built for: OpenClaw (now acquired by OpenAI)
- Verdict: **Skip**

Reason: All 5 layers fully covered by existing Hermes stack. No MCP adapter exists.
Harness-specific throughout (SENTINEL daemon, memory-core OpenClaw plugin, nmem_context graph plugin).
Marketing is heavy ("quantum-verified emergent values"). Actual mechanism is file-based context
injection + scratchpad dropout detection — valid but already present in hermes-context-hygiene.

One concept worth noting: **scratchpad dropout as a within-session coherence signal** — tracking
when the model stops using its scratchpad/reasoning steps as a proxy for context saturation.
Could be added to hermes-context-hygiene if a lightweight implementation emerges.
