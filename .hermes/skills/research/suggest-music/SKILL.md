---
name: suggest-music
triggers:
  - User asks for music recommendations or says 'suggest some songs'
  - Using the local music-taste seed data and Music-Map to find similar artists
  - User wants personalized song suggestions based on listening history or taste profile
  - Browsing recent YouTube or browser history for music signals to feed a recommendation
description: >
  Use when: Suggest a few songs using the user's local music-taste seed data, recent YouTube/browser history, and Music-Map neighbor checks.
version: 1.0.1
author: Hermes Agent
license: MIT
related_skills:
  - agent-reach-discovery
  - stay-in
  - gold-class
---

# suggest-music

Use this when the user says things like:
- suggest some music to me
- recommend a few songs
- what should I listen to?
- give me some music like this band

Goal: return 3-6 song suggestions that are plausibly aligned with the user's taste, not generic chart picks.

## Inputs to use in order
1. `references/music_taste_seeds.yaml` — canonical local taste seeds normalized from the user's library.
2. `references/music_map_seed_neighbors.yaml` — cached artist-neighbor hints gathered from Music-Map.
3. Recent local browser / YouTube history when available:
   - prefer Firefox history under the active profile
   - use local notes/daily logs if they contain explicit music activity
4. Web or browser lookups only to fill metadata gaps or confirm an artist/song relationship.

## Output shape
Return:
- a short heading
- 3 to 6 songs
- for each song: `Artist — Song` plus one brief reason tied to the user's taste
- optional closing question asking which one landed best

Keep it concise.

If the recommendations are being surfaced in a UI/dashboard rather than plain chat:
- make the song title clickable
- default to a YouTube search URL for `Artist + Song` when you do not already have a canonical watch URL
- prefer a simple, reliable outbound link over leaving the item unlinked

## Related skills
- `agent-reach-discovery` — for social/YouTube/community signal (Reddit music threads, Bilibili, X) to augment seed data
- `stay-in` — companion recommendation skill for movies/TV
- `gold-class` — companion skill for cinema outing recommendations

## Workflow
1. Read `references/music_taste_seeds.yaml`.
2. Identify 2-4 active taste clusters from:
   - repeated artists in the seed file
   - recent YouTube/search signals
   - any explicit user request like "more like X"
3. Prefer recommendations that are:
   - adjacent to seed artists on Music-Map
   - same-scene or same-era fits
   - not obvious overplayed defaults when a slightly deeper cut is available
4. Avoid recommending tracks that are already clearly present in the seed file unless the user asked for favorites/rewinds.
5. Mix familiarity and discovery:
   - 1-2 safe picks
   - 2-4 discovery picks
6. If the user names a specific artist, weight that cluster heavily and down-weight unrelated clusters.
7. If the user gives a current-mood update (for example, "right now I'm more into X, Y, and Z"), treat that as stronger than older seed/history signals for this recommendation pass.
8. When the mood update looks stable enough to matter later, save a compact preference memory about the active music lane.

## Recommendation heuristics
- Heavy / classic / hard rock cluster:
  Black Sabbath, Dio, Rainbow, UFO, Uriah Heep, Iron Maiden, Scorpions, Van Halen, Wolfmother, Clutch, Blue Öyster Cult
- Progressive / psychedelic cluster:
  King Gizzard, Pink Floyd, Jethro Tull, Alan Parsons Project, Supertramp, Cream, Hendrix
- Gothic / darkwave / synth cluster:
  The Sisters of Mercy, The Crüxshadows, Visage, Talking Heads-adjacent art pop, Kajagoogoo/80s synth signals
- Blues / roots cluster:
  B.B. King, Otis Rush, Rory Gallagher, Eric Clapton, The Black Keys, The Dead South, The Handsome Family
- Pop / new wave / alt cluster:
  Blondie, Fleetwood Mac, Metric, Coldplay, RHCP, Suzi Quatro / Duffy / Kajagoogoo / The Animals browser-history signals

## Iterative rating calibration
When the user starts rating tracks numerically, treat that as a calibration loop, not a one-off reaction.

1. Preserve the strongest signal, not every score verbatim.
   - Compress repeated feedback into the current active lane (for example: "likes catchy, driving 80s pop-rock/new wave more than quirkier new wave or lighter sophisti-pop").
2. Detect micro-lanes inside broad artists.
   - Example: Blondie can mean several different lanes.
   - `Heart of Glass` does NOT imply the same target as `Call Me` or `Maria`.
   - If the user anchors Blondie with `Call Me` / `Maria`, bias toward glossy, driving, hook-heavy pop-rock/new wave rather than quirky art-pop, synth novelty, or softer dreamier material.
3. Use scores to tighten, not widen, the search space.
   - 8-10/10 = core lane, produce more like this.
   - 6-7.5/10 = adjacent lane, keep only a few bridge picks.
   - below 6/10 = back away unless the user asks to keep exploring.
4. In multi-round recommendation sessions, explicitly summarize the inferred lane before giving the next batch.
   - Keep that summary to one sentence.
5. Prefer 1-3 strongest bets over broad variety once the lane is clear.
6. If the user says vocals need not be female, immediately widen candidates to male-fronted acts in the same energy/production lane instead of staying stuck on gender.

## Useful lane examples from practice
- `Blondie -> Call Me / Maria`:
  catchy, driving, glossy 80s pop-rock/new wave; Joan Jett / Pat Benatar / Billy Idol / Cars-adjacent energy can fit better than quirkier new-wave acts.
- `Sade + Avalon + Supertramp/Alan Parsons positives`:
  sophisticated, polished, melodic production matters more than pure genre matching.

## Iterative taste-tuning from ratings
When the user starts rating suggestions track-by-track, do not just continue recommending from the same bucket. Infer the lane they are actually selecting for and pivot hard.

Useful axes seen in practice:
- `Blondie -> Maria` = glossy, dramatic, adult pop-rock
- `Blondie -> Call Me` = fast, punchy, hook-heavy pop-rock/new wave
- lighter sophisti-pop vs richer groove-driven sophisti-pop
- quirky new wave vs radio-sized female-fronted pop-rock

How to use the ratings:
1. Compress individual ratings into lane summaries after each batch.
   - Example: `likes fast catchy female-fronted new wave/pop-rock around 7-8/10; harsher punk and softer detours weaker`
2. Treat explicit anchor-song references as stronger than generic artist references.
   - `I like Blondie` is broad.
   - `Closer to Maria` or `like Call Me` is the real routing signal.
3. If a user asks for `closer to X`, narrow the next batch around that exact song's pace, polish, and emotional tone rather than the artist's whole catalog.
4. Prefer adjacent songs that preserve the winning combination of:
   - female-fronted
   - strong chorus
   - driving tempo
   - glossy/dramatic production when requested
5. De-emphasize tracks that are merely era/genre matches if prior ratings show they are too quirky, too soft, or too punky.
6. After 2+ feedback rounds, give `best bets first` and mention the lane in one short sentence.

## Local-history hints
If local YouTube history is available, treat repeated searches/watches as a temporary mood boost.
Examples already seen in this environment included signals for:
- Suzi Quatro
- Kajagoogoo
- Shakin' Stevens
- Duffy
- The Animals
- AMH

These should bias suggestions when no stronger user prompt is given.

History-parsing pitfall:
- Do not use loose substring regexes for artist detection when mining browser history.
- Use word boundaries, exact query terms, or artist/title extraction from the page title.
- Example false positive seen in practice: `Dio` matched the word `video` inside YouTube titles/URLs, which polluted recency inference.
- If parsing is noisy, trust the canonical seed YAML over inferred browser-history matches.

## Music-Map usage
If browser access is available and you need an adjacency check:
1. Open `https://www.music-map.com/<artist>`
2. Read the nearest names around the seed artist
3. Use 1-2 of those adjacent artists as candidate sources
4. Verify with a quick web/browser lookup if the artist/song pairing is uncertain

## Avoid
- giant essays
- album-only recommendations when the user asked for songs
- obviously random genre jumps unless the user asked for variety
- pretending you verified a song if you did not

## Fallback mode
If history is unavailable, use only the seed file and cached Music-Map neighbors.
If both are sparse, say that you are giving best-effort suggestions from the saved taste seeds.

## Feedback loop
When the user gives track-by-track ratings or like/dislike feedback:
- treat the highest-rated items as the strongest signal for the next recommendation pass
- infer the lane behind the rating, not just the exact track (for example: sophisticated female-vocal groove-pop, polished prog-pop, lighter sophisti-pop)
- bias the next batch toward the highest-rated lanes and away from the weaker-rated lane
- keep the next set concise and explicitly shaped by that feedback

## Maintenance
When the user says they liked or disliked a suggestion:
- capture that as durable preference memory if it seems stable
- prefer a compact summary of the taste shift over storing every score verbatim when memory space is tight
- if memory storage fails because the user profile is near capacity, first consolidate or remove overlapping entries, then retry in the same turn
- update the seed data or cached neighbor file if a new artist repeatedly appears
