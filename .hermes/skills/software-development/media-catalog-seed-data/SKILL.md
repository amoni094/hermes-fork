---
name: media-catalog-seed-data
triggers:
  - Building or evolving a curated movie/TV seed dataset with normalized identifiers
  - Exporting or importing media catalog data in CSV or SQL format with schema validation
  - Seeding a media recommendation database from curated sources
  - Updating the media catalog schema or adding new entries to the seed dataset
description: >
  Use when building and evolve curated movie/TV seed datasets with normalized identifiers, schema-aware exports, and verified CSV/SQL artifacts.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [data-modeling, seed-data, csv, sql, sqlite, media, curation, verification]
    related_skills: [verification-before-completion, complexity-gated-planning]
related_skills:
  - verification-before-completion
  - plan
  - complexity-gated-planning
---

# Media Catalog Seed Data

Use this when the user wants a sample or starter database for films/TV, especially when they provide a curated title list and want CSV/SQL deliverables.

## Outcomes

Produce a working seed package, not just a list:
- normalized media rows
- stable slugs/keys
- schema.sql
- seed.sql
- CSV export
- verification evidence from a real database load

## Default modeling

Prefer a normalized core with these concepts:
1. `franchise` or `series_group` for multi-title umbrellas
2. `media_item` for concrete titles or scoped TV entries
3. `user_feedback` when recommendation refinement is part of the task

Recommended `media_item` fields:
- `slug`
- `title_display`
- `title_canonical`
- `media_type` (`film`, `tv_series`, `miniseries`, `tv_season`)
- `release_year`
- `end_year`
- `country`
- `original_language`
- `original_title`
- `director_or_creator`
- `based_on`
- `franchise_slug`
- `series_parent_slug`
- `season_scope`
- `genres`
- `summary`
- `notes`

When the dataset is user-facing, prefer a short `summary` field for each title. Keep it concise and spoiler-free so it works in browsing, recommendation, and export contexts.

## Genre handling

If the dataset is meant for browsing, filtering, or recommendation, include explicit genres even if notes already imply them.

Default lightweight choice:
- `genres TEXT` with semicolon-separated values in CSV and SQL

Escalate to a join table only when the user asks for stronger normalization or genre analytics:
- `genre`
- `media_item_genre`

## Workflow

1. Normalize the input list.
   - dedupe obvious repeats
   - resolve ambiguous remakes/versions
   - normalize typo-driven requests to canonical titles when the intended work is clear
   - if the user names the wrong media type but the intent is obvious, map to the real canonical scope and record that interpretation in `notes` only if the clarification adds catalog value
   - split umbrella requests into concrete titles when the user asks
   - preserve user-specific scope notes like “season 1 only”

2. Build stable identifiers.
   - one durable slug per concrete item
   - distinguish remakes/variants with year or disambiguator in slug

3. Model scope explicitly.
   - franchises as separate rows only in franchise table, not fake media items
   - TV season-only requests should be `tv_season` with `season_scope`
   - franchise membership belongs in `franchise_slug`

4. Add user-facing discovery fields.
   - include `genres`
   - include a concise spoiler-free `summary` when the catalog will be browsed directly by people or downstream agents
   - keep `notes` concise and high-signal: use them for disambiguation, scope, franchise context, adaptation/source context, or canonicalization decisions that matter later
   - remove notes that merely restate genre, tone, or obvious facts already covered by structured fields or the summary

5. Keep exports synchronized.
   Any schema change must be reflected in all artifacts:
   - CSV header and rows
   - schema.sql
   - seed.sql
   - README notes if present

6. Verify with a real database load.
   - create a temporary SQLite database
   - execute schema.sql and seed.sql
   - verify row counts and a few representative rows
   - when deduping or normalizing, also verify duplicate title/year groups are gone or intentionally explained
   - after schema edits, re-run verification from scratch

## Recommendation-aware datasets

If the user wants future recommendations refined by past reactions, include a feedback table such as:
- `title_slug`
- `user_label`
- `seen`
- `preference` (`liked`, `disliked`, `mixed`)
- `notes`
- `created_at`

If the assistant suggests a title and the user says they have seen it, the follow-up should capture whether they liked or disliked it, then store that in the feedback model or memory as appropriate.

## Verification checklist

Before claiming completion, verify:
- CSV exists and header matches schema intent
- schema.sql includes all intended columns and constraints
- seed.sql loads successfully into SQLite
- row count matches the curated item count
- when `summary` exists, every row has a non-empty value and sample rows read naturally without spoilers
- representative rows prove the nuanced cases survived normalization
  - remake/original disambiguation
  - franchise-linked entry
  - TV season-only entry
  - genre-filled row

## Pitfalls

- Do not hide genres in free-text notes when the dataset is meant to support filtering.
- Do not update only the CSV after adding a new field; schema and seed must change too.
- Do not model franchises and concrete titles interchangeably.
- Do not leave ambiguous titles unresolved when the user already clarified the intended version.
- Do not preserve noisy notes that only paraphrase genre, mood, or the summary.
- Do not add a second row for an already-present title when the user asked to drop duplicates; treat it as a no-op and document only the normalization decision if needed.
- Do not claim the seed package is done without reloading it into a real database after schema changes.

## Support files

See `references/media-db-patterns.md` for a compact pattern bank covering franchise modeling, scoped TV entries, and explicit-genre upgrades.
See `references/title-normalization-examples.md` for compact examples of typo normalization, wrong-media-type requests, and high-signal notes discipline.
