# Blindspot expansion pattern

Use this when a first-pass blindspot section is too thin or empty even though the topic clearly has adjacent popular discourse.

## Goal

Surface "popular things you might be missing" without contaminating the main ranked results.

## Pattern

1. Run the normal retrieval, ranking, and clustering flow first.
2. Compute blindspots from finalized items only.
3. If blindspots are below a small threshold (for example, fewer than 3), launch a second-pass expansion.
4. Build expansion queries from:
   - compact core subject extracted from the user topic
   - recurring non-topic tokens/entities in top candidates
   - recurring non-topic tokens/entities in finalized source items
5. Keep the expansion query count small; 2-4 queries is usually enough.
6. Restrict second-pass sources to popularity/trend-friendly sources.
7. Deduplicate expansion results against the original evidence pool by URL or stable item identity.
8. Feed expansion results only into blindspot extraction, not the main ranking.
9. Emit an audit artifact showing:
   - expansion queries
   - sources used
   - optionally the threshold that triggered the second pass

## Good uses

- Narrow technical queries whose main results are relevant but omit adjacent high-attention debates.
- Trend briefings where the user explicitly asks what they may be missing.
- Source-native trend feeds such as GitHub, Reddit, YouTube, or Hacker News.

## Verified example from a live session

Topic: "AI coding tools"

Initial behavior:
- the main GitHub run could return zero blindspots

Second-pass expansion queries that improved coverage:
- ai coding stars
- ai coding weekly
- ai coding popular

Verified outcome:
- the run produced a non-empty `blindspots` artifact
- the run also recorded `blindspot_expansion` metadata with queries and sources
- compact rendered output included a `## Blindspots` section populated by expansion-only discoveries

## Practical guidance

- Keep expansion results out of the main top clusters.
- Prefer semantically adjacent nouns/entities over generic popularity words when available.
- Generic tokens like "popular" or "weekly" can still be useful bootstraps, but they should be treated as a fallback, not the ideal final heuristic.
- Classifying blindspots into subtypes makes the section easier to skim.
