---
name: gold-class
triggers:
  - User wants to find Gold Class or premium cinema sessions today or within the next 24 hours
  - User asks 'what's on at Gold Class' or 'any good movies at Village Cinemas tonight'
  - Finding a high-Metascore movie showing at a premium cinema near the user
  - User wants cinema session times with quality filtering
description: >
  Use when finding Gold Class or premium cinema sessions within the next 24 hours, using the user's taste database plus 75+ Metascore filtering for movie selection.
version: 1.0.0
author: Hermes Agent
created_by: agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [movies, cinema, gold-class, session-times, metascore, outings]
    related_skills: [stay-in, suggest-music, agent-reach-discovery]
related_skills:
  - grounded-citations
  - firecrawl-research
  - stay-in
  - suggest-music
  - agent-reach-discovery
---

# Gold Class

Use this skill when the user wants to go out to watch something in a premium cinema session.

Core rule: start from the user's taste database and 75+ Metascore quality filter, then find actual premium sessions occurring within the next 24 hours.

## Target cinemas

You must check these venues:
- Village Cinemas Gold Class at Crown
- Village Cinemas Gold Class at Southland
- Hoyts Lux at Chadstone
- Fomo Cinemas

If one venue has no qualifying sessions, say so explicitly rather than omitting it silently.

## Hard requirements

Every recommended title must:
- be similar to titles in the user's taste database
- have Metascore >= 75
- have at least one actual session within the next 24 hours
- be playing at one of the target venues above

## Inputs

You need:
1. access to the user's taste database or seed list
2. optional filters:
   - tonight / specific time window
   - movie only or movie-first preference
   - max travel preference if later expanded
   - number of options wanted

If the database path or source is missing, ask for it once.

## Relationship to stay-in

`gold-class` is the cinema-session sub-case of the broader `stay-in` skill. If the user wants a home watch recommendation (no session time required), use `stay-in` instead. Both share the same taste database and Metascore methodology.

## Workflow

1. Get the current local time using a tool.
2. Define the next-24-hours window from that timestamp.
3. Load the user's taste database and derive taste signals.
4. Generate candidate films similar to the database.
   - Gold Class mode is movie-first because cinema sessions are for theatrical titles.
5. Verify candidate Metascores and keep only titles with Metascore >= 75.
6. Check live session listings for the target venues.
7. Keep only sessions whose start times fall within the next 24 hours.
8. Match qualifying sessions back to the best-fit films.
9. Present the best options ranked by taste match first, then session convenience.

## How to look up sessions

Use live web tools. Prefer direct venue pages when possible.
If direct extraction is weak, use browser automation.
For each venue, verify actual session times rather than relying on search snippets.

Search patterns to use when needed:
- site:villagecinemas.com.au Crown Gold Class [movie title]
- site:villagecinemas.com.au Southland Gold Class [movie title]
- site:hoyts.com.au Chadstone Lux [movie title]
- Fomo Cinemas [movie title] sessions

## Time-window rule

"Within the next 24h" means strictly between now and now + 24 hours in the user's local timezone.
Do not include sessions outside that window even if they are otherwise perfect.

## Output format

Use this structure:

Gold Class options in the next 24h

1. Title (Year) — Metascore: N
   Why it fits: ...
   Sessions:
   - Venue — Day Time
   - Venue — Day Time

2. ...

Then add:
- Best overall pick
- Earliest good session
- No-result notes for any target venues with nothing qualifying

## Constraints

- No titles below 75 Metascore.
- No sessions outside the next 24h.
- No generic "check the cinema website" answer if live session lookup is possible.
- Do not claim a session exists unless you verified it from a live source in this run.

## Verification

Before finalizing, verify:
- current time used for the 24h window
- every recommended title has Metascore >= 75
- every listed session time is within the next 24h
- every listed session belongs to one of the specified venues

## Failure handling

If no titles satisfy both taste match and session constraints, say that clearly and offer either:
- the best 75+ taste matches with no qualifying session in the next 24h, or
- the best live premium sessions even if taste match is weaker

Make the fallback explicit instead of silently weakening the rules.
