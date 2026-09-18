---
name: portable-context-layer
description: >
  Use when designing and maintain a context layer (memory + skills + business logic) that is decoupled from any specific harness. Your context layer is your moat — skills, memory, and domain knowledge that travels with you across Claude Code, Cursor, OpenCode, or any future harness. Prevents harness lock-in.
version: 1.0.0
triggers:
  - "harness lock-in"
  - "portable memory"
  - "context layer"
  - "switch harness"
  - "own my agent memory"
  - "harness-independent skills"
  - "knowledge graph for my agent"
related_skills:
  - harness-first-agent-design
  - hermes-obsidian-sync
  - autonomous-agent-loop-design
---

# Portable Context Layer

> "Free open-source harnesses don't make you free. What you want to own is the context layer.
> Every agent is the same model + runtime + harness underneath, rebuildable on an open stack."
> — Paul Iusztin, Jun 30 2026

## The Three Lock-In Failure Modes

**Failure 1 — Start from scratch**: Switch harnesses after 6 months, lose every past
conversation, every preference the agent learned about you. Zero transfer.

**Failure 2 — Skills are hostage**: Business logic coupled to one harness's keywords
and features. Switching doesn't just lose history — your custom logic breaks or silently
performs worse on the new platform.

**Failure 3 — Billing at their mercy**: The plan you depend on can be pulled, repriced,
or restricted. With high switching friction, you can't leave.

## The Architecture: 3 Components

### 1. Unified Memory
A single store that holds everything you know:
- Filesystem (canonical primary state)
- Keyword search (BM25)
- Semantic vector search
- Knowledge graph (typed entities: Person, Organization, Location, Event, Object + Facts + Preferences)

**Design principle**: Build on a single database that supports text + semantic + graph search
(e.g., MongoDB with vector indexes). Start simple; add complexity only when demanded.

### 2. Serving Layer (MCP server + filesystem skills)
Two angles, use both:

**MCP server** (portable, harness-agnostic):
- Exposes Tools, Resources, Prompts, Skills as MCP protocol
- Any agent (Claude Code, OpenCode, Cursor, custom) plugs in via MCP config
- Wraps the business logic for how memory is queried and updated
- Swapping harness = one-line config change

**Filesystem skills** (leaner, no server):
- `AGENTS.md` + folder of skill markdown files
- Cheaper to maintain, zero infrastructure
- More coupled to a specific harness's conventions
- Best for: project-level skills, conventions, tactical guidance

Best setup: **MCP server for memory access** + **skills layered on top** for higher-level workflows.
Host skills directly on your MCP servers to avoid fragmenting business logic.

### 3. Business Logic Layer
Your domain-specific intelligence:
- How to query and update memory (search patterns, write patterns)
- Domain vocabulary (DDD glossary, entity types)
- Workflow patterns specific to your work
- Preferences and behavioral rules

This layer is what makes the context valuable. The infrastructure is generic.

## Tool Design for Memory MCP Servers

Design 6 high-leverage primitives the agent can compose like LEGOs:

**3 search tools:**
1. `nl_query_memory` — default: LLM maps natural language to hybrid search + graph query
2. `query_memory` — deterministic fallback for structured filters when NL is ambiguous
3. `deep_search_memory` — progressive disclosure for large result sets (50+ docs);
   writes intermediate results to a YAML index (LLM wiki on the fly). Trades latency for
   performance and lower costs — avoids exploding context with uncompressed chunks.

**3 write tools:**
1. `ingest_url` — fetch and index a URL into memory
2. `ingest_file` — index a local file
3. `ingest_conversation` — auto-triggered by a hook every ~10 turns + on session end

The `ingest_conversation` hook is what creates **continual learning**: the system writes
back what it just learned without you asking. Memory compounds over time.

## Status-Discriminated Responses (Tool Design Discipline)

When designing MCP memory tools, avoid returning free-form prose as the only output.
Return a machine-readable `status` discriminator alongside the prose so callers can
branch precisely:

**Recommended status set** (from Curion's design, validated pattern):
- `saved` — write confirmed
- `answered` — recall succeeded, answer provided
- `weak_match` — recall returned candidates below confidence threshold; agent should NOT treat as authoritative
- `no_memory` — nothing stored for this query
- `rejected` — input filtered by safety/policy; nothing stored
- `provider_error` — LLM provider call failed

**Clarification-needed forwarding contract** (companion pattern):
When recall is `weak_match` or `no_memory`, include a `clarification_needed: { question: "..." }`
block. The calling agent must forward this question verbatim to the user rather than
synthesizing a guess. This is the explicit no-answer escalation path — it forces
uncertainty to surface rather than be papered over.

This pattern replaces the fragile heuristic of "if result is empty, say 'I don't know'"
with a structured, testable contract between the memory tool and its caller.

**Normalize-before-persist discipline**:
Never write raw input to the memory store. Pass it through a controller that extracts
a normalized summary plus metadata (topic, confidence, safety flags, timestamps). Only
the normalized form is stored. Raw inputs belong in transient session logs, not in
persistent memory.

## Don't Expose Raw Database Operations

Agents struggle with raw DB operations. Instead:
- Design the server around how agents actually search and write
- Give high-leverage primitives that compose naturally
- The 6-tool pattern above is a proven starting point
- Avoid exposing CREATE TABLE / INSERT / UPDATE directly

## Keeping Skills Portable

A skill is portable if it:
- Uses standard filesystem operations (read/write files, git)
- Uses MCP tool calls via the memory server (not harness-specific APIs)
- Doesn't hardcode harness-specific slash commands or config paths
- Describes behavior in natural language that any agent can follow

A skill is NOT portable if it:
- Calls `hermes` CLI directly (except in Hermes-specific skills)
- Uses harness-specific syntax that doesn't transfer
- Depends on session state from a specific harness

For Hermes: keep harness-specific skills in `~/.hermes/skills/`. Keep portable/project-level
skills in `<project>/.claude/skills/` or host them on an MCP server.

## Migration Path (0 to portable)

**Level 0 — today**: Everything in `~/.hermes/skills/`, no memory layer.
**Level 1 — filesystem skills**: Organize skills so they're portable to other agents.
**Level 2 — MCP skill server**: Host skills on an MCP server. Any harness can plug in.
**Level 3 — unified memory**: Add memory layer (vector + graph). Auto-ingest conversations.

Start at Level 1. Most of the value comes from just keeping skills well-organized and
using standard patterns.

## Evaluating Third-Party Memory/Identity Frameworks

Before integrating an external memory framework, do a layer-by-layer overlap analysis against
the existing Hermes stack. See `references/third-party-memory-framework-evaluation.md` for the
checklist and a case study on the Adam Framework (Jun 2026 — verdict: skip, all 5 layers already covered).

Key question: does it require a specific harness? If so, ask whether a Hermes/MCP adapter exists
before investing further.

## Integration with Hermes Obsidian Sync

The `hermes-obsidian-sync` skill already implements a form of portable context — Obsidian
notes + Readwise highlights as the canonical memory source. This is Level 1/2 of the
portable context layer architecture.

Upgrade path: expose Obsidian notes + vault through an MCP server so other agents
(Cursor, OpenCode) can access the same knowledge without re-importing it.
