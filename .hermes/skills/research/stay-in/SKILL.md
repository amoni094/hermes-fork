---
name: stay-in
description: "Recommend movies and TV series for staying in by finding high-Metascore titles similar to the user's taste database, without restricting results to current streaming catalogs."
version: 1.0.0
author: Hermes Agent
created_by: agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [movies, tv, recommendations, metascore, similarity, research]
---

# Stay In

Use this skill when the user wants something to watch at home and cares about quality and taste match more than streaming availability.

Core rule: do NOT limit recommendations to what is currently on streaming. Recommend the best-fitting movies and TV series first, then optionally mention where to watch only if asked.

## Goal

Find movies and TV series that:
- are similar to items in the user's taste database or stated comps
- by default, favor well-reviewed picks and verify quality signals
- include both films and series unless the user narrows it
- are ranked for likely taste match, not just popularity

Important: this skill has two modes.

1. Quality-first mode
- Use the 75+ Metascore floor when the user is explicitly asking for high-quality picks, a curated shortlist, or when no other preference outweighs critic quality.

2. Vibe-first mode
- If the user is casually asking for something to watch tonight, gives strong comp titles, asks for "trashier" fun, or reacts against your first prestige-leaning picks, optimize for vibe match first and drop the 75+ floor.
- In vibe-first mode, still verify basic reception signals when useful, but do not let Metascore override an obviously better taste match.

## Inputs

You need these before making strong recommendations:
1. access to the user's taste database, seed list, or explicit comparison titles
2. optional mood or constraints:
   - movie, series, or both
   - genre or vibe
   - runtime or commitment level
   - language / country
   - how many picks
   - quality-first vs vibe-first

If the database path or source is not given, first check for a known local taste source already present in the workspace or vault before asking. If a maintained local media database exists, use it as the default taste source and say that you did so. Ask only when no usable local source is available.

If the user names comp titles directly (for example "like Pirates of the Caribbean / The Mummy / Indiana Jones"), treat those as the primary taste source for this turn even if a broader database exists.

If the user gives exemplar titles in-chat (for example: "more like Pirates of the Caribbean / The Mummy / Indiana Jones"), treat those titles as a valid temporary seed list immediately. In that case, prioritize matching the cited vibe first and do not keep steering back to the stored database unless the user asks for database-driven picks.

## Database expectations

The taste database can be:
- a plain text list
- CSV / JSON / Markdown table
- a local file containing favorite movies and TV shows

At minimum, extract title and whether it is a film or series if available.
If richer metadata exists, use genre, director, cast, year, language, tags, and user rating to sharpen similarity.

## Workflow

1. Load the user's taste database, or use their explicit comps if they gave them.
2. Identify strong taste signals:
   - repeated genres
   - directors / creators
   - tone
   - pacing
   - countries / languages
   - themes
   - prestige vs. pulpy preference
   - tolerance for older titles, animation, and "trashy but fun" picks
3. Generate candidate titles similar to the database items or comps.
4. Verify each serious candidate with live lookup:
   - in quality-first mode: verify Metascore >= 75
   - in vibe-first mode: verify only enough to avoid inventing facts; reception can be mixed if the vibe fit is strong
5. Remove obvious duplicates, franchise repeats that add little value, and titles already in the database.
6. If the user says they have seen a pick, immediately ask or infer whether they liked it, disliked it, or rated it, then use that feedback to refine the next batch.
7. Treat fresh in-session watch feedback as high-priority taste evidence. If the user says something like "I watched X and it was 8/10" or "quite good," explicitly update the recommendation axis it affects before generating the next list. Example axes: historical/samurai appetite, tolerance for brutality, pacing tolerance, appetite for prestige vs pulp, or openness to non-English titles.
8. When a fresh rating materially changes the recommendation mix, say so briefly in the output (for example: "your 13 Assassins 8/10 pushes historical power-struggle picks up the list"). This makes the adaptation legible instead of feeling random.
9. Mix safe bets with a few adjacent discoveries.
10. Return concise picks with a one-line reason tied to the user's taste.

Conversational recommendation rule:
- For casual back-and-forth, do not get stuck defending a rigid score floor when the user is clearly steering toward a mood or vibe.
- When the user rejects picks because they are too old, too animated, or not pulpy/funny enough, explicitly pivot the next batch around that correction.

## Research method

Prefer local database evidence first, then live web research.
Use web tools to confirm:
- Metascore
- title type (movie or TV series)
- brief premise or fit signals if needed

When searching, combine the candidate title with terms like:
- Metascore
- Metacritic
- TV series or film

If direct Metacritic extraction is blocked, verify the Metascore from a secondary authoritative page that explicitly quotes Metacritic (for example, the title's Wikipedia critical-response section or an IMDb critic-reviews page carrying Metacritic data). Record that this was a fallback verification path and exclude titles when the score still cannot be verified cleanly.

Do not invent scores. Verify them.

## Ranking heuristic

Rank by this order:
1. taste similarity to the user's database
2. Metascore strength
3. diversity across the final set
4. novelty relative to the database

A title with an 80 Metascore that strongly matches the user's taste is usually better than a 95 that is only loosely related.

## Output format

Use this structure:

Stay-in picks

1. Title (Year) — Movie or Series — Metascore: N
   Why it fits: ...
2. ...

Then add:
- Fastest match: the safest immediate pick
- Wild card: one slightly broader pick that still fits

Keep the reasons specific to the database, not generic review language.

If the picks are being rendered in a UI/dashboard rather than plain chat:
- make each title clickable
- default to a Metacritic title-search URL when you do not already have a clean canonical page URL
- search-result links are acceptable as the minimum reliable behavior; do not block the UI on perfect deep-link resolution

## Constraints

- Do not filter by streaming availability unless the user asks.
- Do not recommend titles already present in the user's database unless they explicitly ask for rewatches.
- In quality-first mode, do not include titles below 75 Metascore.
- In vibe-first mode, you may include lower-scoring titles when the user explicitly prioritizes fun, pulp, adventure, comedy, trashiness, or a narrow reference vibe over critic quality.
- If too few close matches exist, say so and broaden carefully.

## Scarcity handling for tight filters

When the user combines a narrow content filter (for example: medieval only, court-intrigue only, Korean zombie period only) with a hard critic threshold such as 75+ Metascore, do not pad the list with weak or unverified matches.

Use this fallback order:
1. Return the strongest exact matches that fully satisfy the constraint.
2. If the user asked for a specific count and there are not enough exact matches, fill the remaining slots with clearly labeled adjacent matches that preserve the same taste signal (for example: historical court intrigue adjacent to medieval), while keeping the verified score floor.
3. Explicitly label the boundary: say which picks are direct matches and which are adjacent compromises.
4. If the user wants a stricter list instead, offer a second pass that relaxes score threshold or expands era, but do not silently do both.

Pitfall:
- Do not present a broadened list as if every title fully satisfied the user's original narrow constraint. Be explicit when the catalog is thin.

## Verification

Before finalizing, make sure every recommended item has a verified Metascore >= 75 from live lookup or trusted local data.
If any score is uncertain, exclude that title.

## Good final phrasing

Good:
- "Based on your database's mix of bleak crime thrillers and prestige character dramas, these 5 fit best and all clear 75+ Metascore."

Bad:
- "Here are some things you might like" with no explicit connection to the database.
