# Hermes Memory Topology — Orientation Guide

Use this when onboarding a new person (or a fresh agent session) to how Hermes stores and retrieves knowledge.

## Five-layer memory stack

### 1. In-context memory (injected every turn)
- Hermes "memory" store — compact durable facts saved explicitly. ~2200 char budget. Think of it as working RAM summary.
- User profile — who the user is: tastes, workflow preferences, domain context.
- Both are injected at the top of every session automatically.

### 2. Session search (episodic)
- SQLite-backed FTS5 store of every past conversation.
- Searched via session_search tool by query or session ID scroll.
- Used for "what did we do about X last week" — full conversation history.

### 3. Hindsight (semantic long-term memory)
- Vector-embedded memory layer: OpenAI text-embedding-3-small (1536d) + claude-haiku-4-5 for L1 extraction/promotion.
- Storage: PostgreSQL (pg0-managed, port 5432, db: hindsight, table: memory_units, vector(1536) column via pgvector).
- Daemon: hindsight-api on port 9177.
- Relevant memories auto-injected each turn via semantic similarity search.
- L1 pipeline: l1-extract.py -> memory-facts/ -> l1-promote.py -> staging.md -> Hindsight daemon -> Postgres.

### 4. Skills (procedural memory)
- SKILL.md files with YAML frontmatter. Loaded on demand by the agent.
- Encode proven workflows, tool commands, pitfalls, domain procedures.
- Organized into categories: autonomous-ai-agents, devops, github, research, software-development, productivity, note-taking, superpowers.
- Agent is required to scan and load relevant skills before acting.

### 5. Files / disk (durable structured state)
- MEMORY.md, SOUL.md, TOOLS.md in ~/
- Daily notes in memory/YYYY-MM-DD.md
- Research outputs, plans in .hermes/plans/
- Project-specific data (Religion corpus, policy-dashboard, etc.)

## Key design principles
- Harness-first: skills + memory are the moat, not the model. Swappable models, persistent context layer.
- Verifiable over theoretical: check before claiming.
- Local-first: all inference is cloud (Anthropic API). No local LLMs (Ollama uninstalled 2026-07-12).
- Portable context layer: skills + memory designed to travel across harnesses (Claude Code, Cursor, etc.).

## Embedding backend detail
- Provider: OpenAI text-embedding-3-small, 1536 dimensions
- Storage: pgvector extension on Postgres, vector(1536) column in memory_units table
- Search: cosine similarity ANN via pgvector
- Known pitfall: daemon env file whitelist bug silently drops embeddings_provider config key — see SKILL.md Pitfall 1 for fix.
- QMD disabled (Intel Iris Xe, 256MB VRAM, OOMs on local GGUF models).
