---
name: memory-layer-gate
version: 1.0.0
description: Use before memory write. Routes fact; heals broken layer.
triggers:
  - deciding where to store a fact
  - about to call memory(), hindsight_retain(), or mcp__graphiti__add_memory
  - auditing memory layer placement
  - memory tool returns an error
  - memory layer is unavailable
related_skills:
  - hermes-memory-surface-selection
  - hindsight-stack-operations
created_by: agent
---

# Memory Layer Gate

Run this gate BEFORE any memory write. If a layer is broken, fix it FIRST before continuing the task.

---

## Layer Definitions

| Layer | Tool | What belongs here |
|-------|------|-------------------|
| Core memory | `memory()` | Always-needed-every-turn facts ONLY: tool routing quirks, backend URLs, hard safety rules, procedural write-guards. NOT people, places, events, config, or project state. Budget: ~2200 chars total. |
| Hindsight | `hindsight_retain()` | Cross-session facts recalled on demand: people, machine configs, project state, tool findings, decisions. Unlimited vector store. |
| Graphiti | `mcp__graphiti__add_memory` | Named entity relationships, temporal facts, multi-hop connections (X relates to Y). |
| Session search | (implicit) | Session-specific outcomes: PR numbers, build results, job IDs. Never write explicitly - already in transcript. |
| Skills | `skill_manage()` | Reusable procedures, workflows, API patterns, proven command sequences. |

---

## Write Gate (run before EVERY memory write)

Step 1 - Classify intent level:
  L0 = act on this turn only (ephemeral tool output) -> DISCARD
  L1 = this session only (PR number, today's decision) -> SKIP (already in session_search)
  L2 = stable across sessions (weeks+) -> WRITE

If L0 or L1 -> stop here. Do not write.

Step 2 - Route L2 facts:

  Needed EVERY turn without a query?
    YES -> Core memory. Check it's <90% full first.

  Named entity relationship or temporal graph fact?
    YES -> Graphiti (group_id="hermes")

  Reusable procedure or workflow?
    YES -> Skill

  Person, machine, config, tool finding, cross-session fact?
    YES -> Hindsight

  None of the above -> Does it need to survive? If not, drop it.

Step 3 - MCB check before Hindsight writes:
  PERSIST      - stable, stated, high-confidence -> write
  CONTEXT-ONLY - turn-specific or volatile -> skip
  VERIFY       - may contradict existing memory -> recall first
  ASK          - inferred, not stated -> ask user first

Step 4 - 3-axis score (core memory and Hindsight both require this):
  Recency   = still matters in 30+ days? (1=yes, 0=no)
  Utility   = forces re-ask if missing? (1=yes, 0=no)
  Uniqueness = not captured elsewhere? (1=yes, 0=no)
  Write only if total >= 2.

Step 5 - Decontextualize before writing:
  Replace pronouns and context references with full referents.
  BAD:  "Fixed it by restarting"
  GOOD: "Fixed Hindsight daemon crash (Sep 2026) via: systemctl --user restart hindsight-api.service"

---

## Layer Health Check

IF a layer is broken, fix it BEFORE continuing the current task.

  Core memory:
    Test: memory() call succeeds
    Fix: batch remove stale entries + add new in one operations call to free space

  Hindsight:
    Test: curl -sf http://127.0.0.1:9177/health
    Quick fix: systemctl --user restart hindsight-api.service; wait 45s
    Full recovery: load hindsight-stack-operations skill
    Hard reset: pkill -f hindsight-api; rm -f ~/.hindsight/profiles/hermes.lock; trigger hindsight_retain

  Graphiti:
    Test: curl -sf http://127.0.0.1:8765/mcp/ (exit 0 = up; 307 redirect is fine)
    Fix: load graphiti-mcp-setup skill
    Fallback: use session_search instead; note the outage

  Session search:
    Test: session_search(query="test") works
    Fix: FTS lives in `~/.hermes/state.db` (`messages_fts`). `sessions.db` is a legacy stub and is not the index. Use `hermes sessions stats` / `optimize`; do not run fictional `hermes sessions rebuild` for FTS.

  Skills:
    Test: skill_view(name) returns non-pruned content
    Fix: reload with skill_view; ignore [SKILL_PRUNED] markers in old history

---

## Memory Research Findings (Sep 2026, Round 3)

### Oblivion: Decay-Driven Read/Write Control (arXiv:2604.00131)
Always-on retrieval causes interference and latency as memory grows. Oblivion:
  Read path: retrieve ONLY when agent is uncertain (not always-on)
  Write path: reinforce only memories that contributed to the response
  Result: up to 73% token cost reduction at 120K interaction spans (Oblivion system; not Hermes)

Rules:
  - Gate retrieval on task need, NOT on in-turn FOK score:
    (a) Start-of-similar-task lesson retrieval: ALWAYS run (do not skip on FOK)
    (b) Mid-task: retrieve when missing a required fact, encountering a novel error,
        or when explicit 'recall' keyword is present
    (c) Routine turns with no information gap: skip retrieval
  - After a successful response, strengthen only the memories that were actually cited
  - 73% token reduction is Oblivion's decay-control framework at 120K spans; NOT a
    Hermes API outcome. Hermes has no decay_factor(age, access_count) API.
  NOTE: Do NOT gate start-of-task lesson retrieval behind FOK. FOK is an uncalibrated
  in-turn proxy; blocking it would suppress exactly the lesson-injection that prevents
  repeated failure modes (arXiv:2604.17399).

### TraceRetain: Eviction Under Noisy Writes (arXiv:2606.29178)
Unbounded memory under 75% SYNTHETIC DISTRACTORS: Precision@5 drops 20.2% → 12.4%.
TraceRetain (evict by multi-factor score) stays essentially unchanged at 16.6%.
On CLEAN ALFWorld (no distractors), policies are within confidence intervals —
this result is specifically for noisy-write / capacity-pressure conditions.

Eviction priority (apply ONLY at memory capacity; do NOT evict from unlimited stores):
  1. success: was this memory from a verified successful task? (highest weight; requires
     outcome tracking via recovery-classifier — without labels, skip this factor)
  2. access_frequency: how often retrieved in last N sessions?
  3. specificity: broad generalizations score lower than specific facts
  4. age: older = lower score
  5. similarity to retained entries: near-duplicates evicted first
  NOTE: The specific weights (0.35/0.25/0.20/0.10/0.10) are NOT from the paper abstract;
  treat them as illustrative placeholders and calibrate on your own workload.
  ALWAYS PIN: rules, safety constraints, preferences, PROFILE facts — exempt from eviction.
  Eviction is NOT implemented for Hindsight (unlimited store); apply only if you build
  a bounded external cache.

### Momento: Re-Validate Volatile Prior Session Facts (arXiv:2606.00832)
Current agents fail by treating prior session history as a reliable proxy for CURRENT context.

Rules:
  - Flag VOLATILE memory classes retrieved from a PRIOR session as 'stale: needs_revalidation'
    VOLATILE classes: task state, environment state, user preferences that change,
    external resources, API results, tool outputs
  - EXEMPT from revalidation: PROFILE facts (identity, machine specs, name),
    pinned rules, safety constraints, RECORD entries for stable infrastructure
    (API endpoints that do not change), skill procedures
  - Before acting on stale volatile memory: check if the underlying fact might have changed
  - If revalidation is not possible: state the uncertainty to the user
  Do NOT: flag all cross-session memory as stale — stable PROFILE/RECORD facts
  are the exact content the memory system is designed to persist reliably.

### Cross-Session Memory: Semantic Triples + Summaries (arXiv:2603.19935)
Raw conversation injection is expensive (full-context = 20x more tokens than structured).
Semantic triples + conversation summaries: 81.95% LoCoMo accuracy at only 5% token cost.

Storage policy for cross-session facts:
  - Convert to semantic triples: (subject, relation, object) at write time
  - Summarize episodes into compact narrative summaries (1–3 sentences)
  - Store both; retrieve triples for factual queries, summaries for episodic queries
  - Do NOT inject raw conversation history across sessions
  NOTE: 81.95% is Memori on LoCoMo; your dataset may differ. Monitor on your own benchmark.

### Proactive Memory Sidecar Agent (arXiv:2607.08716)
Passive retrieval misses behavioral state decay. A separate memory agent:
  - Runs alongside the action agent (plug-and-play)
  - Updates a structured memory bank from recent trajectory
  - Decides whether to inject a memory-grounded reminder or remain SILENT
  Result: +8.3pp Terminal-Bench, +6.8pp tau^2-Bench (separate memory agent with silence policy)

Implementation:
  - DEFAULT: in-prompt structured block tracking open subgoals, prior attempts, key facts
    (no extra delegate_task cost; inject only when open subgoal is about to be violated)
  - FOR LONG-HORIZON UNATTENDED RUNS ONLY: delegate_task sidecar with:
    max_turns=1, explicit output schema {inject: true/false, reminder: str},
    silence as the default output (do NOT inject on every call)
  - IB gate still applies: only spawn sidecar when relay-sufficiency passes
  NOTE: Spawning an unbounded sidecar on every L2/L3 task adds delegation tax.
  The in-prompt structured block is the right default; sidecar is the exception.

### Post-Retrieval Assembly: Separate Evidence from Answer (arXiv:2606.01435)
Entangling evidence extraction + conflict resolution + answer generation in one step:
always-on failure mode. Structured assembly (two-stage) improves dramatically:
  Single-hop: 54% → 82%/93% (gpt-4o-mini/gpt-4o)
  Multi-hop: 7% → 27%/41%

Protocol:
  Stage 1 (Evidence Extraction): LLM extracts semantically matching evidence into
    a candidate representation from raw retrieved chunks. No answer generation.
  Stage 2 (Policy Execution): LLM answers from the candidate representation only.
    Not from the raw retrieved context.
  NOTE: Gains depend on tasks with explicit version metadata (current-value queries).
  Apply when retrieval returns multiple conflicting or time-varying facts.

### Memory Conflict Resolution (arXiv:2608.13921, 2606.06240, 2607.01935)
Don't collapse conflicts to one definitive answer. Policy:

  TANGLE (2608.13921): Three conflict types:
    CPC: context-partitioned (valid in different contexts → store both with context tag)
    BOC: behavior-oscillation (evolving preference → store with recency weight)
    SCC: source-contradiction (conflicting sources → escalate for clarification)
  Actions: recognize underdetermination, retain conflicting evidence, seek clarification
  Do NOT: force a single answer when conflict type is SCC or unresolvable BOC.

  ATMA/Ghost Memory (2607.01935): Keep superseded facts with state labels:
    - current: the live fact
    - historical: an old fact that was replaced
    - transition: a fact mid-change
  On retrieval: filter by requested state view (current vs historical)
  On QA: expose labels so the answer model knows which state it's reading
  NOTE: Graphiti+ATMA on LoCoMo: temporal F1 0.0295 → 0.1705; gains are host-dependent.

  TOKI (2606.06240): Type contradiction heuristics explicitly:
    - last-writer-wins: requires isolation; loses prior fact in audit
    - evidence-weighted merge: requires consistent evidence signals
    - await-confirmation: safe for high-stakes; adds latency
    - per-rule policy: fastest; needs domain-specific rules upfront
  Always: preserve losing facts in an audit row (do not silently overwrite)

  MemGuard (2608.21867): Treat verifier signals as LIFECYCLE METADATA:
    - Attach {reward, confidence, label, uncertainty} to every memory candidate
    - Reuse these at retrieval, conflict resolution, summarization, archival
    - Do NOT treat verification as a one-shot admission filter


This table defines the AUTHORITATIVE storage policy. All other entries defer to this.

  Type: rules / preferences / constraints / safety / policy
    Store as: VERBATIM FULL TEXT (pin; NEVER compress or summarize)
    Retrieve: always prepend to context before semantic hits
    Note: 2608.22752 TypeCompact: uniform compaction keeps only 10% of rules after 5 rounds.

  Type: tool output (> 2KB)
    Store as: verbatim offload to SQLite/file with citation stub in context
    Note: ARC (arXiv:2607.25066) pattern — 99.4% needle on Qwen eval. No real recall_by_id
      tool exists in Hermes yet — store in SQLite sessions table, retrieve by rowid.
    Implementation status: PARTIAL (SQLite session log exists; recall_by_id tool does NOT).

  Type: episodic events / tool outputs (< 2KB) / conversations
    Store as: distilled lesson (< 500 chars: goal + what failed/worked + reusable rule)
    Note: arXiv:2609.05553 EdgeMem: verbatim beats summarized for long-term QA.
      However, Hermes Hindsight has a budget; use verbatim only for rules and large tool blobs.
      For small events: 500-char distillation is the right tradeoff.

  Type: correction / verified outcome
    Store as: VERBATIM full correction text + outcome verdict
    Admission: unconditional (arXiv:2603.04549 — corrections have highest utility prior).

### Context Compaction Rules (arXiv:2608.22752 Compaction Cliff)
PIN in context (never compact): rules, preferences, constraints, safety text, current goal,
  open files, last tool error, pending plan steps (D-state arXiv:2608.16370).
COMPACT first: tool dumps, scratchpad, old dialogue.
Avoid r < 0.4 prompt-instruction retention (r=0.2 raises cost +1.8% via output expansion
  arXiv:2603.23525 RCT on Sonnet 4.5). Note: r here is prompt-instruction retention fraction,
  NOT compression.threshold_tokens — do not conflate the two.

### Retrieval Stack and Hybrid RRF (AUTHORITATIVE — ONE RULE)
This entry is the SINGLE authoritative routing and fusion rule.
Demote duplicate 'Hybrid RRF Retrieval: Always Fuse Dense + FTS' entry (Round 1) to reference.

Fusion rule:
  ALWAYS fuse Hindsight dense + SQLite FTS5 via Reciprocal Rank Fusion (RRF).
  For session-local recent facts: prefer session_search (lexical exact match wins).
  For cross-session semantic retrieval: prefer hindsight_recall.
  The session_search vs hindsight_recall SPLIT remains valid as a routing heuristic;
  when BOTH apply (cross-session semantic over a large corpus), add RRF fusion.
  Do NOT replace the existing routing split with a 'forbid one or the other' rule
  until RRF fusion tooling exists in Hermes (current status: NOT IMPLEMENTED).

Retrieval stack order:
  Stage 1: RRF(Hindsight-dense, SQLite-FTS5) -> top-20 [UNIMPLEMENTED — approximate
    by running hindsight_recall + session_search and manually combining]
  Stage 2: LLM rerank -> top-5 (emit {relevant, contribution, evidence_span})
  Inject only evidence_spans into next turn (not full memory records).
  Cap at 2 retrieval hops (95% of 5-hop gain).
  BM25/FTS5 is a first-class peer (not fallback) — especially for code/table queries.

### Memory Admission Gate (arXiv:2603.04549) — ONE AUTHORITATIVE RULE
Score each candidate on 5 factors before promoting to Hindsight:
  1. content_type_prior: rules/corrections ALWAYS; factual HIGH; trivia LOW
  2. utility: would this prevent a recurrence or answer a future query?
  3. novelty: cosine distance from Hindsight top-1 > 0.2 (not a near-duplicate)
     NOTE: Round 1 entry uses similarity < 0.85 (equivalent framing: distance > 0.15);
     use 0.2 distance / 0.8 similarity as the single threshold — do not apply both.
  4. factual_confidence: HIGH for verified; LOW for hallucinated/uncertain
  5. recency: prefer recent; decay old unless rule/preference
Require content_type_prior=HIGH OR (utility AND novelty AND factual_confidence).

### Episodic-Semantic Dual Process (arXiv:2605.17625)
Keep last ~10 turns raw (working memory).
Async/nightly consolidate into growing semantic profile in Hindsight.
Route queries:
  numbers / dates / exact values -> consolidated semantic profile
  historical events / 'what did we do last week' -> Hindsight RAG
Consolidation quality (not window size) is the scaling bottleneck.

### Spreading Activation for Retrieval (arXiv:2601.02744 SYNAPSE)
After Hindsight vector anchors, do 1-2 Graphiti hops from retrieved entities.
Decay older neighbors; suppress highly activated siblings (lateral inhibition).
Fused score: 0.5 * dense + 0.3 * graph-activation + 0.2 * recency.

### Compaction Cost Measurement (arXiv:2607.12161)
Do NOT optimize compression on token count alone.
Score cost-per-success including cache writes/reads and retrieval calls.
If retrieval calls jump after a compact, reduce compression severity.
Prefer stable prefixes (system+skills) for cache hits; compress volatile tails.

### Unimplemented Patterns (do not advertise as available)
  recall_by_id tool: NOT YET IMPLEMENTED
  seek_transcript tool: NOT YET IMPLEMENTED
  compress_context / offload_span / recall_span tools: NOT YET IMPLEMENTED
  Agent-controlled ARC offload: NOT YET IMPLEMENTED
Until these exist: use SQLite session log rowids as approximation for exact recall.

## Memory Research Findings (Sep 2026, Round 1 — carried forward)

### Compaction Cliff: Type-Aware Protection (arXiv:2608.22752)
Uniform compaction destroys safety/policy text: after 5 rounds, only 10%
of rules survive. TypeCompact preserves 2-4x more. Protocol:
  - CLASSIFY every context line before compression:
      rule/preference/constraint -> PIN (never compress)
      episodic/tool-output/scratchpad -> COMPRESS aggressively
  - Pinned rules go at TOP of compressed window, above semantic results
  - On Hindsight recall, ALWAYS prepend matching rule/preference memories
    before semantic hits (100% recall@50 vs 73% for LLM retrieval)

### Addressable Recall Compaction (arXiv:2607.25066 ARC)
Instead of summarizing large tool outputs, offload them:
  - Write tool results to: ~/.hermes/offload/<session_id>/<obs_id>.txt
  - Leave a one-line citation in context: "[OBS-42: tool output, see recall_by_id]"
  - Expose a recall_by_id(obs_id) tool that returns the raw blob on demand
  - Do NOT rely on Hindsight similarity search for exact tool output recovery
  - ARC achieves 99.40% needle accuracy vs 88.12% for summarize/retrieve

### Hybrid RRF Retrieval: Always Fuse Dense + FTS (arXiv:2606.21553)
Fixed hybrid RRF (Reciprocal Rank Fusion of dense + BM25/FTS5) beats
rule-based adaptive routing (+1.8 EM):
  - ALWAYS fuse Hindsight dense + SQLite FTS5 via RRF
  - Do NOT route on named-entity heuristics
  - Cap agentic RAG loops at 2 hops (captures 95% of 5-hop gain)
  - After RRF: rerank top-20 with cheap cross-encoder -> inject top-5 only
  - Do NOT paste full memory records; extract evidence_span only

### BM25 > Dense for Mixed Content (arXiv:2604.01733)
BM25/FTS5 beats text-embedding-3-large on mixed text/table/code docs.
  - Keep FTS5 as a first-class peer, NOT a fallback
  - Two-stage: RRF hybrid -> then rerank
  - Skip HyDE for ID/path/number/code queries (no benefit)
  - Add document-context prefix at index time (title + neighboring chunk)

### Memory Admission Gate (arXiv:2603.04549)
Five-factor gate before any Hindsight write:
  1. Content-type prior (STRONGEST signal): always admit rule/correction/preference
  2. Utility: does this change future behavior?
  3. Factual confidence: is this actually true?
  4. Novelty: cosine similarity to top-1 Hindsight hit < 0.85
  5. Recency bonus for time-sensitive facts
For chat trivia: require high utility + confidence.
For corrections/preferences/rules: admit unconditionally.

### Never Drop D-State on Compression (arXiv:2608.16370)
At 5x compression, task completion is unchanged but retrieval calls
explode (21->63.9 extra calls, p=.002), canceling savings.
Protected D-state fields (NEVER compress or drop):
  - Current goal and active subgoal
  - Open file paths and working variables
  - Last error message and its step
  - Pending plan steps
Measure re-retrieve rate per session; if it jumps after compact, reduce severity.

### Eviction Index for Efficient Long-Context Recovery (arXiv:2608.21690 Scroll/ARC)
On any compaction event, write an eviction index:
  {"id": obs_id, "summary": one-line, "rowid": sqlite_rowid, "timestamp": iso}
Agent gets a seek_transcript(id) -> full content tool.
SQLite session log is ground truth; prompt projection is a view only.
This yields 99.40% needle accuracy and +37.4 LOCA_256K vs prior methods.

### Agent-Controlled Compression Tools (arXiv:2607.23809 ACM)
Expose three tools instead of only auto-compact:
  compress_context(keep_ids): compress all except specified IDs
  offload_span(start, end): move span to external storage, leave citation
  recall_span(id): retrieve any offloaded span by ID
Auto-compact at 85% context remains as safety net. Not the only path.

### Episodic Critique + Semantic Promotion (arXiv:2510.19897 +8.1pp)
On any failed or corrected task:
  1. Write episodic critique: {"what": task, "error": what went wrong, "fix": what corrected it}
     -> Hindsight, tag: ["episodic-critique", task_type]
  2. If same error appears 3+ times: promote to semantic rule
     -> Hindsight, tag: ["semantic-rule", task_type]
Retrieve BOTH on similar tasks. Inject critiques as working-memory prefix.
Precomputed critiques cut thinking tokens 31.95%.

### 10-Turn Episodic Window + Async Consolidation (arXiv:2605.17625)
Optimal episodic window for most tasks: last ~10 turns raw.
Consolidate older turns asynchronously (nightly/end-of-session) into
a growing semantic profile. Routing:
  - Numbers, dates, counts -> consolidated semantic profile
  - "What did we do last week?" -> Hindsight RAG
  - "What is the current state?" -> raw episodic window
Consolidation QUALITY, not window size, is the scaling bottleneck.

### Prompt Compression: r=0.5 Is Pareto-Optimal for Claude Sonnet (arXiv:2603.23525)
RCT on 358 Claude Sonnet 4.5 production runs:
  r=0.5 (50% retention): -27.9% total cost (input + output)
  r=0.2 (aggressive): +1.8% cost due to output expansion from confusion
  Recency-weighted at r=0.5: -23.5% cost, Pareto frontier
Rule: cap config.yaml compression at 50% retention.
Always measure output tokens, not just input savings.

### Don't Optimize Compression on Token Count (arXiv:2607.12161)
Aggressive compression cut delivered tokens 38.4% but raised billed cost
6.8% (r=0.15 vs cost) due to cache traffic + extra retrieval turns.
  - Score cost-per-success including cache writes/reads and extra tool rounds
  - Prefer stable prefixes (system+skills) for Anthropic prompt cache hits
  - Compress only volatile tails (tool dumps, old scratchpad)
  - Avoid compression that forces extra retrieval rounds

### Verbatim Storage Beats LLM-Summarized Memory (arXiv:2609.05553 EdgeMem)
LLM-generated summaries at ingest lose precision. Verbatim chunked storage:
  - Store: raw turn/tool-output chunks tagged {session_id, timestamp, episode_id}
  - Retrieve: hybrid dense + time-window filter + episode-id filter
  - Use LLM only for final answer synthesis, NOT for summary at write time
  - EdgeMem: 61.01 vs 58.70 strict-judge LoCoMo with zero generative calls at ingest

## Memory Research Findings (Sep 2026)

### LeanMem Typed Store Mapping
Each memory write should be explicitly typed as one of:
  PROFILE   - stable user/env identity facts (name, prefs, machine specs)
  EVENT     - what happened at a specific time (outage, experiment, decision)
  RECORD    - structured reference data (API endpoints, schema, config values)
  PROCEDURE - how to do something (goes to skills, NOT Hindsight)

When writing to Hindsight: prefix the content with the type tag:
  PROFILE: Rainbow's desktop is DESKTOP-PH4F2DK, Win11, 192.168.0.181
  EVENT: Sep 9 2026 - reasoning capability upgrade applied to Hermes
  RECORD: Hindsight API = http://127.0.0.1:9177

### MemMachine Rule: Extractions Do NOT Replace Transcripts
Never overwrite a raw session or search result with an extracted summary
in Hindsight. Extracted facts are ADDITIVE (hindsight_retain), not
replacements for the original. The original transcript remains in
session_search; Hindsight holds the distilled fact. Summaries are lossy
by design — do not treat them as the ground truth.

### Dual-Process Memory: Episodic Window + Semantic Store
Within a session: the most recent 10 messages constitute an "episodic
working window" — facts here do NOT need to be written to Hindsight;
they are available in context. Write to Hindsight only when a fact needs
to survive BEYOND the current session (recency=1, utility=1).
For long sessions: when a fact first appeared >10 messages ago, write it
to Hindsight before it falls out of the episodic window.

### Hindsight Retrieval Ordering
Hindsight uses dense vector retrieval by default. When searching manually
(hindsight_recall vs session_search): prefer session_search for recent
facts within this session (lexical exact match wins); prefer hindsight_recall
for cross-session semantic retrieval. Never run hindsight_recall to
confirm something already in context — that's the tool necessity anti-pattern.

---

## Anti-Patterns

- NOT core memory: people, machine configs, project state, contacts, events
- NOT Hindsight: tool routing rules, safety guardrails (those must be core memory - always-injected)
- NOT anywhere: L0/L1 facts (PR numbers, build results, one-off outputs)
- NOT raw: summarize before writing; 500 chars max per entry
- NOT cosine-only dedup: dual-gate required (cosine >0.85 AND LLM equivalence check)
- NOT inferences as facts: context-only until confirmed in 2+ independent sessions
- NOT context-dependent phrasing: every entry must be self-contained

---

## Routing Examples

  "Galina's laptop GRUB boots silently, hold Shift for menu"  -> HINDSIGHT
  "web.search_backend=brave-free"                             -> CORE MEMORY (needed every turn)
  "KWM contacts: Cheng Lim, Michael Swinson"                  -> HINDSIGHT
  "PR #847 merged today"                                      -> SESSION SEARCH (implicit, skip)
  "Always read skill before patching it"                      -> CORE MEMORY [procedural]
  "How to run hindsight-reembed.py"                           -> SKILL
  "Galina laptop connects to MacKinnon network SSID"          -> GRAPHITI (entity relationship)
