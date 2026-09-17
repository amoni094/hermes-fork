---
name: obsidian-research-ingestion
depends_on: [obsidian, firecrawl-research, grounded-citations]
provides: [vault-ingestion, knowledge-filing, bi-directional-linking]
related_skills:
  - obsidian
  - hermes-obsidian-sync
  - academic-literature-review
  - domain-research-synthesis
  - grounded-citations
  - hermes-memory-surface-selection
  - hindsight-stack-operations
description: >
  Use when ingesting articles, PDFs, or raw notes from the Obsidian Inbox into the vault knowledge base with bi-directional linking and contradiction flagging.
triggers:
  - "ingest this article"
  - "file this to obsidian"
  - "process inbox note"
  - "research ingestion"
  - "add to vault"
  - "save research findings to vault"
  - "file these paper findings into obsidian"
  - Output of academic-literature-review or domain-research-synthesis needs to be filed to the vault
---

# Obsidian Research Ingestion Pipeline

Paste an article, PDF transcript, or raw notes into `00 Inbox/`, then run this skill to file it into the vault's `04 Resources/` with linking and contradiction detection.

## Vault paths

- Inbox: `/var/home/rainbow/Documents/SecondBrain/00 Inbox/`
- References/Resources: `/var/home/rainbow/Documents/SecondBrain/04 Resources/`
- Projects: `/var/home/rainbow/Documents/SecondBrain/02 Projects/`

## Steps

1. **Identify the inbox note** — look for the most recently modified `.md` file in `00 Inbox/` or the file the user names explicitly.

2. **Extract metadata** from the note content:
   - Title (from frontmatter or first H1)
   - Author (if present)
   - Source URL (if present)
   - Date (if present, else today)
   - Primary topic/domain
   - **Temporal fields** (J1 pattern, IPSJ TDP 2025): extract explicit dates, effective
     dates, and revision markers as structured fields — not just prose. These become
     Graphiti node properties for filtered temporal retrieval later. E.g.:
     `published: 2025-03, effective: 2025-06, revised: null`
     Add these to the reference note frontmatter and to any Graphiti write step.

3. **Write the reference note** to `04 Resources/<slug>.md`:
   ```markdown
   ---
   title: <title>
   author: <author>
   source: <url>
   date: <date>
   ingested: <today>
   tags: [<inferred tags>]
   type: reference
   ---

   # <title>

   ## Key Insights
   - <3-5 bullet takeaways>

   ## Summary
   <2-3 sentence summary>

   ## Related Notes
   <links to existing vault notes on the same topic>

   ## Contradictions / Flags
   <anything in this source that contradicts existing vault notes — or "None found">

   ## Source Note
   [[00 Inbox/<original filename>]]
   ```

4. **Search the vault** for existing notes on the same topic:
   - Use `search_files` on the vault for keywords from the title/summary
   - Link any matches as "Related Notes" in the new reference note
   - Add a backlink line to each matched note pointing to the new reference

5. **Contradiction detection**: scan matched notes for claims that conflict with the new source. Add them to "Contradictions / Flags" section.

6. **Archive or clear inbox note**: add a `processed: true` tag to the inbox note frontmatter so it's not re-ingested. Do not delete it.

6b. **Write episode to Graphiti** (optional but recommended for research ingestion):
   ```python
   # Use mcp__graphiti__add_memory tool:
   # name=<title>, episode_body=<2-3 sentence summary + key claims>, source_description=<url or "Obsidian vault ingestion">
   # group_id="hermes"
   ```
   This makes the research findable via graph queries and hindsight_recall. Include temporal fields from step 2 in the episode_body.

7. **Report**: "Ingested: <title> → 04 Resources/<slug>.md | Related: N notes linked | Contradictions: N"

## Pitfalls

- The vault has no live web browser — paste content in first, don't try to fetch URLs.
- Vault path has spaces ("00 Inbox") — always quote in shell commands.
- If a Resources note for the same URL/title already exists, update it rather than duplicating.
- Keep summaries concise — users read these as quick-reference, not full article replacements.
- Contradiction flagging is best-effort; don't false-positive on different contexts for the same concept.
