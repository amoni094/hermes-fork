# last30days GitHub trends and blindspots

This reference captures a reusable pattern from a live extension session on `last30days`.

## What was added

1. GitHub 7-day trend crawl
- Added a repo-trend path with a 7-day lookback.
- Useful buckets:
  - `weekly-popular`: recent repos sorted by stars
  - `weekly-emerging`: recently active repos sorted by updated activity
- These signals complement issue/PR evidence instead of replacing it.

2. Blindspots section
- Added a report artifact for high-engagement adjacent items not centered in the main ranked clusters.
- Rendering guidance: emit a dedicated `## Blindspots` section before stats.

## Why this matters

A normal ranking tends to reward topical alignment and corroboration. That can hide items that are clearly popular but phrased differently or sitting one hop away from the exact topic. A blindspot pass gives the user a compact answer to: "what is hot around this topic that I might otherwise miss?"

## Practical scoring shape

Good minimal recipe:
- start from finalized normalized items
- exclude URLs already covered by the top ranked set
- require at least some engagement signal
- score on:
  - engagement/popularity
  - lower direct relevance to exact phrasing
  - lower lexical overlap with the main query
- keep the result list short

## Verification pattern

Use a narrow, fertile query and verify both machine-readable and rendered output.

Good live probe from the session:
- source: `github`
- query: `AI coding tools`

Expected verification signals:
- logs mention both weekly trend searches
- JSON artifacts include `blindspots` when enough adjacent evidence exists
- rendered compact output contains `## Blindspots`

## Example observed behavior

The live probe surfaced:
- multiple AI coding-agent repo-trend hits
- one off-center but very popular blindspot item from GitHub issue traffic

Interpretation:
- top-ranked results captured the direct repo-trend story
- blindspots captured a high-engagement adjacent discussion that was clearly popular but not central to the query wording
