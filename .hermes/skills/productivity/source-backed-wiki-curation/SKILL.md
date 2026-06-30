---
name: source-backed-wiki-curation
description: Curate external repositories, articles, or tool catalogs into a local markdown wiki by anchoring provenance in source notes, writing synthesis notes for operator guidance, and avoiding schema invention or bulk noisy imports.
triggers:
  - importing external catalogs or repositories into a local wiki
  - adding vetted source-backed notes to an Obsidian-style knowledge base
  - deciding how to map third-party structured content into an existing markdown schema
  - reviewing a repo or source before adding it to a personal knowledge system
---

# Source-Backed Wiki Curation

Use this when an external source (repo, site, dataset, agent library, docs set) needs to be reviewed and incorporated into an existing markdown knowledge base without polluting the wiki with speculative structure.

## Core principle

Preserve provenance first. Prefer:
1. one canonical `sources/` note for the external artifact
2. one or more `syntheses/` notes for distilled operator-facing guidance
3. targeted index updates

Do NOT invent a new entity/person/card schema just because the source contains many items. First discover the local wiki's actual shape and map into that.

## When this skill fits especially well

- The source is large (dozens or hundreds of items) and a bulk import would create noise.
- The local wiki already has source/report/synthesis conventions.
- The user wants security or quality vetting before adoption.
- The source contains structured metadata that may be better referenced than copied.

## Workflow

1. Discover the local schema before writing anything.
   - Read local `AGENTS.md` or equivalent workspace rules.
   - Inspect top-level indexes and representative notes.
   - Determine whether the wiki primarily uses `sources/`, `syntheses/`, `reports/`, entity cards, or another structure.

2. Inspect the external source enough to classify it.
   - Is it a canonical source artifact, a collection of entities, a tool/plugin, or a library of prompts/agents?
   - Count size and divisions only if useful to downstream curation.

3. Decide the mapping strategy.
   - Default: source note + synthesis note.
   - Only create per-item notes/cards if the local schema already supports them and the user clearly benefits.
   - For large third-party catalogs, prefer shortlist synthesis over full import.

4. Record provenance in the source note.
   - URL/repo
   - reviewed snapshot/commit if applicable
   - concise security/quality review status
   - scope limitations and missing scanners/tools if relevant

5. Distill operator value in a synthesis note.
   - shortlist the items actually worth reusing
   - explain why each is worth keeping
   - note overlap with existing local capabilities
   - recommend the lowest-risk operational adoption path

6. Update navigation/indexes.
   - add the new source note to the source index
   - add the synthesis note to the synthesis index
   - patch the source note to cross-link the synthesis note

7. Verify before claiming completion.
   - re-read every changed markdown file
   - verify links/index entries are present
   - run a targeted diff if the wiki lives in git

## Heuristics

- If the external source has 100+ items, do not mirror it into 100+ local notes by default.
- If the source already ships a native integration for the target platform, prefer referencing that integration over duplicating its content locally.
- Distinguish `safe enough to catalogue` from `fully audited for production use`.
- A clean static-analysis pass is evidence for the reviewed scope only, not a blanket trust statement.

## Pitfalls

- Do not force third-party agent libraries into person/entity cards when the local wiki does not already use that pattern.
- Do not turn a source note into a second synthesis note; keep provenance and recommendations separate.
- Do not overclaim security review depth when important scanners or checks were unavailable.
- Do not bulk-import a full external roster when a shortlist gives more value with less maintenance burden.

## Deliverable shape

Minimum good output:
- one source note
- one synthesis note
- index updates
- explicit import/mapping decision
- verification evidence

## References

- `references/agency-agents-shortlist-pattern.md` — example of mapping a large third-party agent catalog into source + synthesis notes instead of bulk entity imports.
