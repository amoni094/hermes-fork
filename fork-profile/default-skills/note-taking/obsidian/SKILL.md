---
name: obsidian
provides: [file_read, file_write]
version: 1.1.0
triggers:
  - Reading, searching, creating, or editing notes in the Obsidian vault
  - User asks to 'open a note', 'find a note', 'create a note in Obsidian'
  - Need to read or write Markdown files in the Obsidian vault directory
  - Linking or querying existing Obsidian notes as part of a research or planning task
description: >
  Use when: Read, search, create, and edit notes in the Obsidian vault.
platforms: [linux, macos, windows]
related_skills:
  - obsidian-research-ingestion
  - hermes-obsidian-sync
---

# Obsidian Vault

Use this skill for filesystem-first Obsidian vault work: reading notes, listing notes, searching note files, creating notes, appending content, and adding wikilinks.

> **Graphiti integration:** When ingesting research articles, papers, or structured knowledge into the vault, also load `obsidian-research-ingestion` — it adds a Graphiti episode write step (via `mcp__graphiti__add_memory`) so the content lands in the knowledge graph. Plain note edits using this skill alone do NOT write to Graphiti.

## Vault path

Use a known or resolved vault path before calling file tools.

The documented vault-path convention is the `OBSIDIAN_VAULT_PATH` environment variable, for example from `~/.hermes/.env`. If it is unset, use `/var/home/rainbow/Documents/SecondBrain` (the confirmed local vault path — `~/Documents/Obsidian Vault` is the upstream default but does NOT exist here).

File tools do not expand shell variables. Do not pass paths containing `$OBSIDIAN_VAULT_PATH` to `read_file`, `write_file`, `patch`, or `search_files`; resolve the vault path first and pass a concrete absolute path. Vault paths may contain spaces, which is another reason to prefer file tools over shell commands.

If the vault path is unknown, `terminal` is acceptable for resolving `OBSIDIAN_VAULT_PATH` or checking whether the fallback path exists. Once the path is known, switch back to file tools.

## Read a note

Use `read_file` with the resolved absolute path to the note. Prefer this over `cat` because it provides line numbers and pagination.

## List notes

Use `search_files` with `target: "files"` and the resolved vault path. Prefer this over `find` or `ls`.

- To list all markdown notes, use `pattern: "*.md"` under the vault path.
- To list a subfolder, search under that subfolder's absolute path.

## Search

Use `search_files` for both filename and content searches. Prefer this over `grep`, `find`, or `ls`.

- For filenames, use `search_files` with `target: "files"` and a filename `pattern`.
- For note contents, use `search_files` with `target: "content"`, the content regex as `pattern`, and `file_glob: "*.md"` when you want to restrict matches to markdown notes.

## Create a note

Use `write_file` with the resolved absolute path and the full markdown content. Prefer this over shell heredocs or `echo` because it avoids shell quoting issues and returns structured results.

## Append to a note

Prefer a native file-tool workflow when it is not awkward:

- Read the target note with `read_file`.
- Use `patch` for an anchored append when there is stable context, such as adding a section after an existing heading or appending before a known trailing block.
- Use `write_file` when rewriting the whole note is clearer than constructing a fragile patch.

For an anchored append with `patch`, replace the anchor with the anchor plus the new content.

For a simple append with no stable context, `terminal` is acceptable if it is the clearest safe option.

## Targeted edits

Use `patch` for focused note changes when the current content gives you stable context. Prefer this over shell text rewriting.

## Wikilinks

Obsidian links notes with `[[Note Name]]` syntax. When creating notes, use these to link related content.

## Obsidian-Flavored Markdown syntax

For Obsidian-specific syntax beyond standard markdown, load these references:

- `references/PROPERTIES.md` — frontmatter property types (text, number, checkbox, date, list, links)
- `references/CALLOUTS.md` — callout types, foldable callouts, nested callouts
- `references/EMBEDS.md` — embedding notes, images, PDFs, audio, bases, search results

## Hermes Memory Wiki reconnaissance

If the vault includes an Hermes Memory Wiki or another generated knowledge layer, use a short orientation pass before diving into individual notes:

- Start from the vault home/dashboard.
- Read the wiki index and the syntheses/reports indices before reading sources.
- Use the main memory bridge source to understand the durable workspace index behind the wiki.
- Treat counts, open questions, and empty reports as coverage signals, not facts to repeat verbatim.
- Preserve generated blocks inside managed markers; edit human notes outside markers only.
- Prefer source-backed claims over wiki-to-wiki citation loops.

For this workspace, the live vault and routing notes are documented in `references/hermes-second-brain-orientation.md`.

See `references/hermes-memory-wiki-recon.md` for the compact orientation playbook.

## Pitfalls

- **Shell variable paths fail in file tools** — `read_file`/`write_file`/`patch`/`search_files` do not expand `$OBSIDIAN_VAULT_PATH`. Always resolve to a concrete absolute path first.
- **Wrong fallback path** — the upstream default `~/Documents/Obsidian Vault` does not exist on this host. Fallback is `/var/home/rainbow/Documents/SecondBrain`.
- **Spaces in vault path** — prefer file tools over shell commands for paths containing spaces; shell quoting is fragile.
- **Editing inside managed marker blocks** — generated blocks (Hermes Memory Wiki sections) are inside managed markers. Edit human-authored content only; preserve the markers and the generated block contents.
- **Wiki-to-wiki citation loops** — always prefer source-backed claims over notes that cite other generated notes. Read the primary source, not the wiki's summary of it.
- **Overwriting without reading first** — use `patch` for targeted edits; only use `write_file` when rewriting the whole note is intentional and you have the full current content.
