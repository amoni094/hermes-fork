---
name: last30days-customization
description: Extend and tune a local last30days skill installation with new artifacts, render sections, source-specific heuristics, and verification runs.
---

# When to use
Use this when you need to modify the locally installed `last30days` skill rather than just run it: adding report sections, changing blindspot logic, introducing new source heuristics, or wiring in extra artifacts for downstream synthesis.

# Scope
This skill is for local customization of a working last30days installation. It is not for upstream contribution workflow or generic news research usage.

# Core workflow
1. Confirm whether the installed skill path resolves through a symlink.
   - In this environment, edits under `~/.hermes/skills/research/last30days/...` may resolve to a development tree such as `/tmp/last30days-skill/...`.
   - Verify the real path before assuming there are two independent copies.
2. Patch pipeline behavior in `scripts/lib/pipeline.py`.
   - Add new retrieval, expansion, scoring, or artifact-writing logic here.
   - Keep main ranking/clustering separate from side-channel sections like blindspots or curated auxiliary lists.
3. Patch rendering in `scripts/lib/render.py`.
   - New artifact-backed report sections should get a dedicated renderer and be inserted explicitly into the report flow.
4. Store extra computed data in `report.artifacts`.
   - Good pattern: `artifacts["feature_name"] = {...}` with stable keys.
   - Keep artifact payloads JSON-serializable and easy to inspect in `--emit json` output.
5. For user-personalized briefings, add a browser-history side channel instead of forcing it into the main topical ranking.
   - Read recent Firefox history from the local profile database and summarize it as a separate artifact such as `browsing_history_signal`.
   - Include recent YouTube activity when it is visible in browser history, but label it as browser-history-derived rather than account-API-derived.
   - Treat this as a personalization section for "what the user has recently been reading/watching," not as a substitute for broader public-source coverage.
6. For geopolitics/conflict/infrastructure-heavy news updates, add a WorldMonitor side channel instead of forcing those signals into the main ranking logic.
   - Use `/var/home/rainbow/.hermes/scripts/worldmonitor_news_signal.py --format json` as the compact local-first probe.
   - Store the result as a dedicated artifact such as `worldmonitor_signal` and render it under a short explicit heading rather than merging it into the main ranked evidence list.
   - Treat WorldMonitor health as a source-freshness/situational-awareness check, not as proof that every cited claim is independently verified.
7. Verify both JSON and rendered output.
   - Run one verification pass with `--emit json` to confirm artifact keys and values.
   - Run one rendered pass to confirm section placement, labels, and human readability.

# Patterns that worked
## Blindspot expansion
- Run blindspot expansion only when the initial blindspot set is thin.
- Keep expansion results out of the main ranked clusters.
- Merge expansion results only into the blindspot extraction path.
- Prefer extracted compound phrases/entities from titles/snippets before single-token expansions.
- Filter generic engagement/time words aggressively (`weekly`, `popular`, `trending`, `best`, `top`, `review`, `release`, `day/week/month`, etc.).
- Split candidate phrases on hyphens, underscores, and slashes before noise filtering so tokens like `weekly-popular` and `7-day` are rejected.

## Auxiliary curated sections
- For sections like well-rated movies/TV, collect data separately from the main topic ranking.
- Gate the collector on topic keywords so unrelated reports stay clean.
- Save the section to a dedicated artifact such as `well_rated_screen_releases` and render it independently.
- Use dedupe/merge logic across multiple evidence sources so IMDb/Metacritic signals combine by title.

## Browser-history personalization section
- Keep recent Firefox browsing history separate from main research retrieval and ranking.
- Read from the local history database, summarize the most recent/repeated themes, and render them as a dedicated section such as `## Personal signal` or `## From your browsing/history`.
- Include YouTube URLs/titles found in browser history as a sub-signal when present.
- Use browser history to bias or contextualize the briefing, not to replace the main 7-day / 24h / blindspot public-source sections.

## Non-English noise suppression for English queries
- Add lightweight script-mix filtering in `scripts/lib/relevance.py` when retrieval is pulling mostly non-English noise for clearly Latin-script queries.
- Keep it as a pre-ranking cleanup step in `scripts/lib/pipeline.py` (for example inside `_normalize_score_dedupe`) so ranking, pruning, and clustering logic stay unchanged.
- Trigger only when the query is clearly Latin-script; mixed-script or non-Latin queries should bypass the filter.
- Use simple alphabetic script counts and dominance thresholds rather than full language detection.
- Filter only when non-Latin alphabetic characters clearly dominate the candidate text; do not punish normal English posts that mention a few non-Latin terms.

# Verification checklist
- `--emit json` shows the new artifact key.
- Rendered output shows the new `##` section.
- Browser-history-derived sections clearly say they come from recent Firefox/YouTube history rather than direct account APIs.
- Expansion queries are legible and topic-adjacent, not generic popularity boilerplate.
- Threshold-based sections only include items that actually satisfy the threshold.
- Title cleanup strips source-specific suffixes like ` - IMDb` and ` Reviews - Metacritic`.
- Add unit coverage in both `tests/test_relevance.py` and the pipeline-level suite (`tests/test_pipeline_v3.py`) so the helper and the pre-ranking integration are both exercised.
- Run at least the targeted relevance/pipeline tests after tuning thresholds; if the filter changed ranking-path behavior, run the full pytest suite too.

# Pitfalls
- Do not assume `~/.hermes/skills/...` and the apparent dev tree are separate; resolve symlinks first.
- If the apparent `last30days` skill path is broken or missing entirely, identify the active fallback skill/job/prompt before patching. In this workspace the active reusable news-update path may live in `research-briefing` or a restored `recent-news-briefing` skill rather than an installed `last30days` tree.
- Do not let blindspot expansion contaminate the main ranked candidate set.
- Do not use noisy popularity/time tokens as expansion terms; they produce weak blindspots.
- Do not add a renderer without a JSON artifact path; verification becomes much harder.
- Do not overfit the non-English noise filter into full language detection; keep it lightweight, query-gated, and easy to reason about.
- Do not describe browser-history signal as private account/API history; label it honestly as what was visible in local Firefox history.
- Do not read Firefox SQLite databases in place when a temp-copy pattern is available; browser locks can make verification flaky.

# References
- See `references/blindspot-and-screen-patterns.md` for concrete artifact shapes, heuristics, and verification examples from a working customization session.
- See `references/non-english-noise-and-planning.md` for the validated non-English noise filter pattern, test placement, and the named-entity `--plan` pitfall from a real customization/debugging pass.
- See `references/firefox-history-personal-signal.md` for the validated Firefox/YouTube history side-channel pattern, Flatpak Firefox paths, and verification notes for a personalized briefing section.
