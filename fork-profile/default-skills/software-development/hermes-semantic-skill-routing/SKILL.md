---
name: hermes-semantic-skill-routing
depends_on: [hermes-context-budgeting, hermes-context-packet]
provides: [skill_route]
description: >
  Use when: Reduce per-turn skill-injection cost by routing only relevant skills into subagent context using embedding-based ranking (OpenAI text-embedding-3-small). Saves ~2000 tokens/session on fan-out.
version: 1.1.0
triggers:
  - "optimize skill injection for subagents"
  - "reduce token cost on skill block"
  - "semantic skill shortlisting"
  - "embed skills for relevance"
related_skills:
  - hermes-context-budgeting
  - hermes-context-packet
  - hermes-memory-surface-selection
---

# Hermes Semantic Skill Routing

The system-prompt skills block costs ~2,631 tokens/turn (measured baseline:
~9,600 chars in <available_skills>, post July 2026 optimization). This is
injected every turn regardless of which skills are relevant.

The biggest remaining lever (identified in hermes-context-budgeting
references/prompt-component-sizing.md): inject only a top-K semantically
relevant skill subset into the **messages layer** (NOT the system prompt) for
subagents. This preserves prefix-cache stability on the system prompt while
cutting per-turn cost for specialized subagents.

Prior art: Anthropic Tool Search Tool beta (`defer_loading`, ~85% token reduction
in production). Embedding backend: OpenAI text-embedding-3-small (Ollama removed Jul 2026).

## Graph-of-Skills Dependency Metadata Convention

Skills can declare dependency and capability metadata in their YAML frontmatter
(inspired by arXiv:2604.05333). This enables **transitive dependency resolution**
— loading only the prerequisite chain instead of all skills flat.

### Frontmatter fields

```yaml
depends_on: [skill-a, skill-b]   # skill names this skill builds on (prerequisites)
provides: [capability-x, cap-y]  # capability tags this skill offers (outputs)
```

**Rules:**
- `depends_on` entries must be exact skill directory names (e.g. `arxiv`, `firecrawl-research`)
- `provides` are free-form capability tags (kebab-case, no spaces)
- Only add `depends_on` where the dependency is real and obvious (not speculative)
- Both fields are optional; omit rather than guess

### Graph-walk script

The transitive closure resolver lives at:

```
~/.hermes/scripts/skill-graph-walk.py
```

Usage:
```bash
# Resolve load order for a skill (deps first, then the skill)
python ~/.hermes/scripts/skill-graph-walk.py academic-literature-review

# List all skills with dependency metadata
python ~/.hermes/scripts/skill-graph-walk.py --list

# Print the full dependency graph
python ~/.hermes/scripts/skill-graph-walk.py --graph
```

The script reads all `SKILL.md` frontmatter, builds the directed dependency
graph, and returns a topologically sorted load order. This lets subagent
context packets include only the minimal prerequisite chain.

### Integration with semantic routing

When building a context packet for a subagent:
1. Identify the primary skill(s) needed for the task
2. Run `skill-graph-walk.py <skill>` to get the full prerequisite chain
3. Include only those skill names in the `relevant_skills` key of the context packet
4. This combines semantic relevance (top-K embedding ranking) with structural
   correctness (transitive dependency closure)

---

## When to use

Use when spawning subagents with `delegate_task` where the task is clearly
scoped (e.g. "research arXiv", "write a skill", "run a git operation") and
only a subset of the 101 active skills is relevant. **Do not use for the main
session** — the system prompt must stay byte-stable for prefix caching.

## How to do it (messages-layer injection)

For focused subagent tasks, prepend a compressed skill hint to the context
packet instead of relying on the full system-prompt injection:

1. Identify the task domain (e.g. "github", "memory", "research", "coding")
2. Hard-code or embed-rank the top 3-5 relevant skills for that domain
3. Include the skill names and their one-line descriptions in the context packet
   under a `relevant_skills` key
4. Instruct the agent: "Load these skills first: [list]"

This gives the subagent focused guidance without full skill-block overhead.

## Embedding-based ranking (OpenAI text-embedding-3-small)

Embedding-based dynamic routing uses OpenAI text-embedding-3-small (1536d) via the Hindsight
embedding backend. Use the OpenAI API directly, or skip to the keyword/BM25 approach below
which needs no embedding call.

For dynamic routing, embed the task query and rank against skill descriptions:

```python
import os, math
from openai import OpenAI

_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

def embed(text: str) -> list:
    resp = _client.embeddings.create(model="text-embedding-3-small", input=text)
    return resp.data[0].embedding

def cosine(a, b) -> float:
    dot = sum(x*y for x,y in zip(a,b))
    na = math.sqrt(sum(x*x for x in a))
    nb = math.sqrt(sum(x*x for x in b))
    return dot / (na * nb + 1e-9)

def rank_skills(query: str, skills: list[dict], top_k=5) -> list[dict]:
    """
    skills: list of {"name": str, "description": str}
    Returns top_k most relevant sorted by cosine similarity.
    Cost: ~$0.00002 per call (1536d, text-embedding-3-small).
    """
    q_emb = embed(query)
    scored = []
    for s in skills:
        text = f"{s['name']}: {s['description']}"
        s_emb = embed(text)
        scored.append((cosine(q_emb, s_emb), s))
    scored.sort(key=lambda x: -x[0])
    return [s for _, s in scored[:top_k]]
```

## Quick domain shortcuts (no embedding needed)

For common subagent types, hard-code the relevant skill list:

| Subagent type | Load these skills |
|---|---|
| GitHub/PR work | github-operations, scoped-pr-fix-and-verification, requesting-code-review |
| Memory audit | agent-memory-consolidation, hermes-memory-surface-selection, hermes-context-hygiene |
| Research/arXiv | arxiv, firecrawl-research, firecrawl-stealth-fallback |
| Skill authoring | hermes-agent-skill-authoring, writing-skills |
| Hermes config | hermes-agent, hermes-context-budgeting |
| Cron/automation | hermes-cron-and-agents, autonomous-agent-loop-design |
| Multi-agent | hermes-context-packet, hermes-swarm-consensus, hermes-role-pipelines |
| Code review | requesting-code-review, risk-based-review, adversarial-review |
| Note/obsidian | obsidian, obsidian-research-ingestion |

## Skillify — Reachability-Checked Skill Publishing (Multilingual, CN/KR, Aug 2026) <!-- rationale: skill authoring without reachability testing produces skills that are never retrieved; Skillify's publish-time test is directly applicable to Hermes -->\n\n**Skillify** (Chinese practitioner toolchain, Aug 2026) adds a mandatory **reachability test** to skill publishing: before a skill enters the library, it must be retrievable in at least K=3 distinct query phrasings that a user would naturally type. If any phrasing fails to retrieve the skill in the top-5, the skill's description or `routing_signals` must be revised before publishing.\n\n**The core insight:** most skills are authored in expert vocabulary, but users query in task vocabulary. A skill about \"trajectory risk guardrail\" may never be retrieved by a user asking \"is this action safe to run?\" even though it is exactly the right skill. The semantic gap is a publish-time failure, not a retrieval-time failure.\n\n**Hermes reachability test procedure (manual, no external tooling needed):**\n\nWhen creating or significantly editing a skill, test 3 natural-language queries before finalising:\n1. How would a new user unfamiliar with the skill's name describe this task?\n2. How would an expert describe it in jargon-dense terms?\n3. How would someone describe the failure they're trying to prevent?\n\nFor each query, run: `skills_list(category='<category>')` and check if the skill is visible and its description clearly matches. If not — patch the `description`, `triggers`, or `routing_signals` until all 3 queries would surface it.\n\n**Korean practitioner addition (Velog, Aug 2026):** \"Minion pattern\" for skill reachability — test skills with minimal context queries (single keywords, not full sentences). Skills that only retrieve on full-sentence queries are brittle; skills that retrieve on key single-word triggers are robust at scale.\n\n**Integration with existing authoring workflow:**\nAdd the 3-query reachability test to the `## Verification Checklist` in `hermes-agent-skill-authoring` as a required pre-publish step for any new skill or major skill revision.\n\n**Routing failure mode this catches (that SkillRet vocabulary gap doesn't):** a skill can have perfect embedding similarity to the query AND still be in position #6 due to lower-priority signals. The reachability test catches rank position failures that cosine-similarity analysis alone misses.\n\n## 2-Level Hierarchical Routing (arXiv:2605.16508, Evolvent AI, Aug 2026)

At 150+ skills, flat semantic matching hits an accuracy floor (~18.3% error rate).
The fix is 2-level routing: first filter by category (`scope:`), then rank within category.

**Recommended frontmatter extension for all Hermes skills:**
```yaml
scope: [category1, category2]   # category pre-filter (use skill directory name)
trust: core                     # core | community | user
routing_signals: >              # 200-400 char dense keyword bag for sub-description routing
  key phrases, technical terms, pitfall keywords that trigger this skill
```

**2-level routing algorithm:**
1. Extract task domain keywords → match against skill `scope:` fields → shortlist category
2. Within shortlisted category, BM25/embedding rank by `routing_signals` + `description`
3. Load top-K (default 3) into context; trigger any explicit `triggers:` matches

**SkillDAG: graph > flat embedding by +12.8 pts (arXiv:2606.03056, Fudan/NUS/A*STAR)**
Extending `related_skills:` to typed edges improves retrieval at scale:
```yaml
related_skills:
  - name: hermes-context-budgeting
    edge_type: composes_with      # depends_on | composes_with | conflicts_with | supersedes
  - name: hermes-context-packet
    edge_type: depends_on
```
Not yet implemented in Hermes routing — future upgrade path. Current: flat `related_skills` list.

**SkillRAE: subunit-level retrieval +11.7% (arXiv:2605.10114)**
Decompose SKILL.md into labeled subunits (## sections) and inject only relevant subunits.
Not yet implemented — future upgrade for skills with 1000+ char bodies.

## Negative Triggers: Suppress Routing When User Clearly Wants Something Else (Reasonix, 2026)

Skill routing has two failure modes: failing to route (miss) and routing when the user
doesn't want it (false positive). Negative triggers address the second.

A negative trigger is a keyword or phrase pattern that **suppresses** a skill candidate
even when its positive triggers would otherwise match.

### Pattern

```yaml
# In skill frontmatter (SKILL.md), extend trigger format:
triggers:
  - "search arxiv"
  - "find papers"
negative_triggers:
  - "don't use arxiv"
  - "skip the search"
  - "I already have the papers"
  - "no search needed"
```

The routing rule: if ANY negative trigger matches the user's input, suppress the skill
regardless of positive trigger matches.

### Domain shortcuts table (extended with negative triggers)

| Subagent type | Load these skills | Suppress if user says |
|---|---|---|
| GitHub/PR work | github-operations, scoped-pr-fix-and-verification | "no PR needed", "local only" |
| Memory audit | agent-memory-consolidation, hermes-memory-surface-selection | "skip memory", "don't write to memory" |
| Research/arXiv | arxiv, firecrawl-research | "I already have the papers", "no search" |
| Skill authoring | hermes-agent-skill-authoring, writing-skills | "quick note", "don't save as skill" |
| Code review | requesting-code-review, risk-based-review | "skip review", "no review needed" |

### Routing priority order

1. Explicit `/skill-name` invocation → **require** (overrides all negative triggers)
2. Negative trigger match → **suppress** (overrides positive triggers)
3. Positive trigger match → apply the skill's `auto_use` policy (suggest/prefer)
4. No match → do not route

### Implementation (manual routing in context packets)

When building a subagent context packet, apply this logic before adding skills:

```python
def should_route(query: str, skill: dict) -> str:
    """Returns 'require'|'prefer'|'suggest'|'suppress'."""
    # Explicit invocation
    if f"/{skill['name']}" in query or f"use {skill['name']} skill" in query.lower():
        return "require"
    # Negative trigger check
    for neg in skill.get("negative_triggers", []):
        if neg.lower() in query.lower():
            return "suppress"
    # Positive trigger check
    for pos in skill.get("triggers", []):
        if pos.lower() in query.lower():
            return skill.get("auto_use", "suggest")
    return "suppress"
```

## Sub-Agent Task Prompt Discipline (Reasonix DefaultTaskSystemPrompt, 2026)

Reasonix's `DefaultTaskSystemPrompt` encodes two disciplines that improve subagent
reliability in Hermes delegate_task calls. Apply these when writing subagent context
packets:

### 1. Single final answer — no intermediate reasoning in output

> "Return a single final answer that is concise and self-contained — the parent will
> see only that answer, not your tool calls or reasoning."

**Hermes application:** include this line (or equivalent) in the `context` field of
every `delegate_task` call where the parent needs a clean, actionable result:

```
Return a single final answer. The parent sees only your final response —
not your intermediate tool calls, reasoning, or exploratory steps.
Keep it concise and self-contained: include every fact the parent needs
to act on it, but nothing the parent doesn't need.
```

Without this, subagents often return verbose multi-section exploratory output that
inflates the parent's context and buries the actionable result.

### 2. Fail with a precise question rather than guess

> "If you need to ask for clarification, fail with a precise question instead of guessing."

**Hermes application:** subagents that guess on ambiguous inputs produce results the
parent silently inherits, propagating the wrong assumption downstream. Instruct
subagents to fail explicitly:

```
If the task is ambiguous or you lack required information, do NOT guess —
stop and return a single clarifying question as your final answer.
State exactly what information you need and why.
```

This lets the parent re-ask the user rather than discovering the wrong assumption
three delegation levels deep.

### Context for MCP / capability proxy use

> "For MCP, use the stable use_capability proxy (list → inspect → call);
> do not expect direct mcp__* tool schemas."

**Hermes application:** if a subagent needs to call a tool that may or may not be
directly in its toolset, instruct it to check available tools first:

```
Check your available tools with the tool listing before assuming any
specific tool name. If a needed tool is not directly available, use
the highest-level available proxy (e.g. use_capability → mcp__* chain).
```

## routing_signals: Highest-ROI Single Fix for Description-Gap Problem

SkillRouter (2603.22455) quantified the gap: hiding the skill body (using only name +
description) causes **31–44 percentage point drop** in routing accuracy vs full-text.
Hermes's 57-char description limit is exactly this "body-hidden" condition.

The fix that doesn't require full-body embedding at system prompt injection time:
add a `routing_signals` field (200-400 chars) with key phrases extracted from the
skill body — the technical terms, task types, pitfall keywords that trigger the skill.

**How to write routing_signals:**

```yaml
# In SKILL.md frontmatter:
routing_signals: >
  skill pruning, lifecycle, consolidation audit, never-used skills,
  .usage.json, ghost references, dead skills, prune, merge,
  library bloat, utilization, archived, deprecated, curator
```

The routing_signals field is:
- Indexed by the semantic skill routing system (if implemented)
- Human-readable — tells contributors what use cases the skill covers
- Distinct from `description` (one summary sentence) and `triggers` (matching phrases)
- NOT injected into the system prompt automatically — it lives in the YAML frontmatter
  and is only loaded when the full SKILL.md is read

**Priority:** Add `routing_signals` when a skill is frequently NOT loaded when it should
be (under-triggered) OR when it IS loaded when it shouldn't be (over-triggered due to
ambiguous description). This is the highest-ROI single change for Hermes skill routing
at 170+ skills.

## SkillRet: Retrieval Benchmark Gap (arXiv:2605.05726, Aug 2026)

SkillRet (COLM 2026) built a 17,810-skill benchmark to measure retrieval quality —
the first systematic evaluation of skill retrieval at scale. Key finding: **generic
sentence embeddings significantly underperform skill-specific retrieval** because:

1. Skill descriptions are short, jargon-dense, and lack natural-language context
2. Task queries and skill descriptions use different vocabulary (semantic gap)
3. Distractor skills (similar names, different purpose) cause false positives

Benchmark result: fine-tuned skill retriever vs generic embedding = **+13.1 NDCG@10**
(a large gap — comparable to switching from BM25 to dense retrieval on general corpora).

**What this means for Hermes at 170 skills:**
- Generic text-embedding-3-small works acceptably at this scale (BM25 covers the gap)
- At ~300+ skills, the retrieval quality degradation from the semantic gap becomes
  measurable and skill routing errors start compounding
- The body-embedding approach (SkillRouter: full SKILL.md text, not just description)
  partially addresses this — broader context reduces the vocabulary gap

**SkillRet taxonomy of failure modes** (use as a diagnostic when a skill isn't loading
when it should):
1. **Vocabulary gap**: query uses natural language, skill uses technical jargon
   → Fix: add natural-language trigger phrases to the skill's `triggers:` frontmatter
2. **Distractor collision**: two skills match the same query equally
   → Fix: audit top-K neighbours for any skill returning unexpected results; sharpen
   descriptions to distinguish the two
3. **Under-specified description**: skill description is too short to characterise intent
   → Fix: add more trigger examples; ensure description has a `Use when` clause

**Practical audit step for skill library consolidation pass:**
Check any skill that hasn't been loaded in 30+ days (from .usage.json) for vocabulary
gap — compare its description to the natural language you'd use to ask for its task.
If they diverge significantly, add 2-3 natural-language trigger phrases.

## What to embed: full body, not just description

SkillRouter (arXiv:2603.22455, 2026) tested routing accuracy with different input signals:
- Name only: baseline
- Name + description: moderate improvement
- Full SKILL.md body: 31-44 pp accuracy gain over name+description alone

At 142 skills, BM25 over full skill bodies is sufficient (no reranker needed until ~500 skills).
Implication: embed the full SKILL.md text, not just the `description:` frontmatter field.

## Token savings estimate

- Subagent context packet: ~4000 chars overhead (standard)
- Skill list reduction: 101 skills → 5 skills = ~96% fewer skill injection chars
- At ~24 chars/skill in the listing: (101-5) × 24 = ~2300 chars = ~575 tokens saved
  per subagent invocation
- On a 5-agent fan-out: ~2875 tokens saved per run
- On 10 runs/day × 5 agents: ~28,750 tokens/day → ~$0.05/day at current pricing

## LLM Agents Factory Validation (arXiv:2608.09934, Aug 2026)

Pre-embedding all skill frontmatter descriptions once matches on-the-fly agent configuration generation at dramatically lower inference cost. Validated with 20K+ domain-specific agent profiles — retrieval outperforms generation for controllability and efficiency.

Hermes implication: the current semantic skill routing approach (embed query, find nearest skill descriptions) is validated by production evidence. Optimization: pre-embed all 180+ skill descriptions once per day (triggered when skills change) and store in a lightweight FAISS index alongside Hindsight. This avoids re-embedding at query time and reduces routing latency.

Implementation note: Hindsight already stores embedded memories. Use the same embedding model (OpenAI text-embedding-3-small) to embed skill descriptions; append to Hindsight with `skill_catalog` namespace so they're returned in skill routing queries.

## ratel Progressive Disclosure for Tool Overload (github.com/ratel-ai/ratel, Aug 2026)

ratel achieves ~80% token reduction and fixes "tool overload" (degraded routing accuracy
when too many tools are in context simultaneously) using Progressive Disclosure:

**Core principle:** surface only the tools/skills most relevant to the CURRENT step,
not all tools for the entire task. ratel uses in-process BM25 (no external vector DB)
to select relevant tools per turn.

**Why "tool overload" is distinct from context length:**
Too many tools in context causes routing confusion even when total token count is
manageable. The model's attention diffuses across tool descriptions, reducing the
sharpness of the routing signal. This is a separate failure mode from context overflow.

**ratel's 3-component approach:**
1. **In-process BM25** — no external vector DB needed; BM25 over tool descriptions runs
   in <10ms at 100+ tools. Sufficient for Hermes's 60-80 active tool schemas.
2. **Progressive Disclosure** — tools enter context when their relevance score exceeds
   a per-turn threshold, not at session start. (Already partially covered by TTE above,
   but ratel applies this to tool schemas specifically, not just skills.)
3. **A/B + shadow retrieval** — ratel ships A/B experiment infrastructure to measure
   whether progressive vs full-disclosure is better for a given task category.

**Hermes adaptation — tool schema context at delegate_task time:**
When spawning a subagent, DO NOT include all available tools in the context packet.
Instead, include only the tool schemas relevant to that subagent's task:
```
context: |
  Tools for this task: [web_extract, web_search] for research;
  [skill_view, skill_manage] for skill updates.
  Do not load or call terminal/file tools unless explicitly needed.
```
This prevents tool overload at the subagent level without requiring any infrastructure
change. The `enabled_toolsets` parameter in `delegate_task` already implements this —
use it consistently. <!-- why: 80% token reduction in ratel validates the design already
present in Hermes; the gap is inconsistent usage of enabled_toolsets -->

**The BM25 gap:** ratel's in-process BM25 over tool descriptions outperforms embedding
similarity for tools with similar-sounding names but distinct parameter schemas (e.g.
`hindsight_recall` vs `hindsight_retain` vs `hindsight_reflect`). Embedding conflates
these; BM25 on exact parameter names disambiguates them. Worth testing if tool routing
confusion is observed at >80 tool schemas.

## Set-Shifting: Frame Tool Alternatives as Competing (arXiv:2607.13396, Sweep 15)

LLM agents settle into small recurring tool-call routines within a few turns ("set formation").
When a tool's reliability shifts, agents fail to adapt — they stay stuck in the established routine
even when the tool is failing.

Key finding: **how alternatives are framed changes routing dynamics significantly.**
- Framing tools as *complementary* → agents pick one and commit (set formation accelerates)
- Framing tools as *competing* → agents maintain routing flexibility longer

**Hermes application — in skill prompts and context packets:**

When there are 2+ valid tools for a step, explicitly frame them as competing alternatives:

```
# WRONG: complementary framing (encourages set formation)
"Use web_extract for page content, or browser tools for interactive pages."

# RIGHT: competing framing (keeps agent routing-flexible)
"web_extract and the browser tool compete for this task:
 - web_extract wins when the page is static and extractor returns clean content
 - browser wins when web_extract returns bot-block or empty; do NOT default to browser
 Check web_extract first; re-evaluate per attempt."
```

**For long-running workflows (5+ tool calls to the same tool):**
Add a periodic tool-health checkpoint at the midpoint of the workflow:
```
"After step 5: re-assess whether your primary tool is still the right choice.
 Check: did the last 3 calls succeed? If not, switch strategy now."
```

This prevents the agent from continuing to call a degraded tool because it has committed
to a routine — the explicit checkpoint creates a re-evaluation trigger.

**Note:** this applies to skill routing too, not just tool calls. If you loaded skill X
at task start and later discover it may not be the right approach, explicitly re-evaluate
rather than continuing the established path.

## Sort Lower Bound and Ranking Cost (CLRS Ch 8)

**Theory:** Ranking N skills by relevance requires Ω(N log N) comparisons in the worst case — no comparison-based sort can do better (CLRS Ch 8, comparison-sort lower bound via decision trees). This is a fundamental lower bound, not an implementation artifact.

**Hermes rules:**
- Batch-sort the skill relevance ranking once per session (or once after a skill library change), not per-query. Re-ranking on every query wastes O(N log N) work repeatedly.
- Cache the sorted skill list and invalidate only when skills are added/removed or when the task domain shifts significantly.
- For the main session, the prefix-stable system-prompt injection already implements this (sort once at startup). Do not re-sort for every turn.

**Citation:** Cormen, Leiserson, Rivest, Stein — *Introduction to Algorithms* (4th ed.), Ch 8 (Sorting in Linear Time — establishes Ω(N log N) lower bound for comparison sorts).

## Yoneda Redundancy Detection (Milewski Ch 14)

**Theory:** The Yoneda lemma states that a mathematical object is fully characterized by its morphisms (how it maps to/from other objects). Two skills with identical query-to-action maps are isomorphic — they are effectively the same skill and one is redundant.

**Hermes rules:**
- Flag skill pairs where the query trigger set and the output action set are identical: by Yoneda, they are the same skill under different names.
- Cross-reference with MDL-based dedup (ToolScope cosine > 0.80 audit) to detect Yoneda-redundant pairs.
- Before creating a new skill, verify it differs in at least one trigger or output from all existing skills.

**Citation:** Bartosz Milewski — *Category Theory for Programmers*, Ch 14 (Yoneda Lemma).

## Pitfalls

- Do NOT apply to the main session system prompt — that breaks prefix cache
- Domain shortcuts go stale as skills are added/removed — verify quarterly
- Embedding ranking adds ~200ms latency per skill (101 embeds = ~20s) — only
  worth it for large swarms; use domain shortcuts for 1-3 agents
- nomic-embed-text scores are not calibrated — use top-K, not a score threshold
- Skills with vague descriptions rank poorly; fix descriptions first

## Integration

- Always use with hermes-context-packet (add `relevant_skills` key to packet)
- Run embedding index build after any skill create/patch (5-10 seconds, one-time per change)
- Pair with hermes-context-budgeting for full cost picture

## Skill overlap detection (ToolScope pattern)

ToolScope (ACL 2026, arXiv:2510.20036): auto-merges semantically overlapping tools,
then context-aware retrieves top-K. Achieves 8-38% accuracy gains.

For Hermes: periodically audit skill pairs with embedding cosine similarity > 0.80.
Named overlap candidates: github-issues / github-operations, hermes-context-budgeting /
hermes-context-hygiene (already verified clean), obsidian / obsidian-research-ingestion.

Run merger audit:
```python
# Find high-similarity skill pairs
import json
pairs = [(skills[i], skills[j], float(sims[i][j]))
         for i in range(len(skills))
         for j in range(i+1, len(skills))
         if float(sims[i][j]) > 0.80]
pairs.sort(key=lambda x: -x[2])
for a, b, s in pairs[:10]:
    print(f"{s:.3f}  {a} <-> {b}")
```
Then LLM-review each pair: consolidate if one is a subset, keep both if distinct use cases.

## Compositional routing upgrade: SAD + TTE (Aug 2026 sweep)

Standard semantic routing picks ONE best-match skill. This is correct for single-skill tasks.
For multi-skill tasks, the decomposition step is the bottleneck — not retrieval quality.

### Skill-Aware Decomposition (SAD) — arXiv:2606.18051 (SkillWeaver)
Standard LLM decomposition: 34.2% category recall. With SAD (one retrieval-feedback iteration): 67.7% (+32.7%).
Rule: before routing, decompose the task into atomic sub-tasks. Then call skills_list() and
align sub-task granularity to match available skill boundaries. Repeat once.
Correct granularity is the prerequisite for effective retrieval (CatR@1: 34% -> 41% at accuracy=1).

When decomposition granularity is wrong (sub-task too coarse OR too fine), skill retrieval
returns the wrong skill even with a perfect embedding index. Fix the granularity, not the query.

### Topology-Aware Task Execution (TTE) — arXiv:2606.13317 (SkillCAT)
Do NOT load all matched skills upfront for a multi-step task. Load only the skill executing NOW.
Context reduction: >99% vs full-corpus loading on CompSkillBench (2,209 real MCP skills).
Pre-loading future-step skills causes:
  - Context bloat that degrades all active steps
  - Description conflicts that confuse routing
  - Stale skill content for steps that don't execute until later

### Routing failure diagnosis
| Symptom | Root cause | Fix |
|---|---|---|
| Loaded skill not used | Granularity wrong (sub-task too coarse) | Split sub-task |
| Wrong skill retrieved | Description mismatch | Fix description first, then re-embed |
| Two skills match equally | Distractor collision | Sharpen descriptions |
| Skill loaded but context bloated | Too many skills pre-loaded | Switch to TTE (just-in-time) |

For multi-skill tasks: delegate to compositional-skill-routing skill (implements SAD + TTE + DAG planning).

## Shapley-Value Marginal Routing (arXiv:2608.07532, Jul 2026)

Coalition game theory grounding for skill selection. Greedy marginal-value activation achieves
99.5% of optimal utility while activating 1.96/8 agents on average (vs. 38.8% full broadcast).

**When 3+ skills compete for the same context slot:**
Embedding similarity alone can pick redundant skills. Use marginal utility ranking instead:
- Step 1: embed the task, retrieve top-K candidates by cosine similarity
- Step 2: among candidates, rank by *marginal contribution given skills already committed*
  (does adding skill X still add useful capability, or is it covered by skill Y already loaded?)
- Step 3: greedy add — stop when no remaining skill adds positive marginal utility

This prevents loading two overlapping skills (e.g., adversarial-review + requesting-code-review)
when one already covers the relevant capability.

**Stability warning from the paper:** greedy routing degrades to 66% performance under strong
violations of submodularity or noisy value estimates. Do NOT apply Shapley routing for tasks
where skill boundaries are blurry (overlapping content); fix skill descriptions/boundaries first.

## Two-Tier Skill Retrieval — SkillRL (arXiv:2602.08234, Feb 2026) <!-- why: flat retrieval treats all skills equally; two-tier separates always-applicable general heuristics from task-specific skills, reducing token footprint while improving reasoning utility -->

SkillRL (UNC-Chapel Hill) identifies that raw experience → skill extraction requires
separating two retrieval tiers to avoid noisy retrieval:

**Tier 1 — General heuristics (always retrieve):**
Skills that apply across essentially all task types. Should be small and stable.
Examples: `adversarial-review`, `verification-before-completion`, `trajectory-risk-guardrail`.
Add `retrieval_tier: general` to these skills' frontmatter.

**Tier 2 — Task-specific heuristics (conditional retrieval):**
Skills that apply only when the task context matches. Can be large/specialized.
Examples: `gold-class`, `obsidian`, `xlsx`, `pdf`, `law-firm-briefing-memo`.
Add `retrieval_tier: task-specific` to these skills' frontmatter.

**Routing rule:** at session start, always load `retrieval_tier: general` skills into
the routing context. For `retrieval_tier: task-specific`, apply semantic/BM25 retrieval.
This reduces the retrieval pool for the semantic step, improving precision.

**Domain shortcut extension (add `retrieval_tier` to routing table):**

| Tier | Skills | Load condition |
|---|---|---|
| general | adversarial-review, trajectory-risk-guardrail, verification-before-completion | Always |
| general | hermes-context-hygiene, mnemosyne-atp-safety | Always (safety) |
| task-specific | Everything else | Semantic match ≥ threshold |

## Aug 2026: Feedback-Driven Routing (Sakana "Learning to Orchestrate")

Semantic similarity alone is a weak routing signal. Augment with success-rate feedback:
1. Log (task_category, skills_loaded, outcome: success/failure) to a lightweight store
2. Build a routing weight table: skills that succeed on a task-type get higher weight
3. Blend: routing_score = 0.6 * semantic_sim + 0.4 * success_rate_weight (bootstrap at 0.5)
4. Reweight after every 10 completed tasks of the same category

This matches the Sakana finding: RL-trained routing with retrieval-relevance reward achieves
NDCG@10 0.918 vs 0.539 for pure semantic-similarity baselines, 82.4% latency reduction.

**Current Hermes implementation gap:** no persistent routing feedback loop exists.
The skill load pattern (skill_view → execute) happens but outcomes aren't logged back.
Near-term shortcut: add a `## Usage outcome` comment at the end of task runs where a skill
was loaded — future self-improve sweeps can parse these to build the weight table.
## KARE-RAG Domain-Coherence Re-Rank (CS queue: arXiv:2506.02503) — S1

After TF-IDF + PAC-Bayes initial ranking, apply a domain-coherence re-rank pass:

1. If a retrieved skill's category tag matches the current session type (research / code / mixed from session_classifier), boost its score by +0.15.
2. If the skill's related_skills list contains a skill already loaded in this turn, boost by +0.10 (graph-neighbour coherence).
3. Cap total boost at +0.20 per candidate.

This addresses the KARE-RAG finding: pure embedding similarity misses domain-coherent matches. A memory-management skill and a research-sweep skill may be semantically close in embedding space but only one is domain-coherent with the current session.

Wire: skill-router-index.py should apply these boosts after computing the base TF-IDF + PAC-Bayes posterior_mean score, before final sort.

Concrete implementation gate: requires session_classifier output (session_type) to be available at routing time. Skip the session-type boost if session_type is None (first-turn, pre-classification).

<!-- why: domain coherence is orthogonal to embedding similarity; a research session should prefer research skills even when a code skill has higher embedding match -->

