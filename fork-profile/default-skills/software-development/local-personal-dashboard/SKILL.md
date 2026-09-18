---
name: local-personal-dashboard
triggers:
  - User asks for a web dashboard, start page, or control panel
  - Dashboard should blend current information (news, weather) with user-specific recommendation panes
  - Building a small local web dashboard using existing Hermes recommendation pipelines
  - User wants a personalized browser start page with live daily updates
description: >
  Use when building a small local web dashboard that combines live daily updates with personalized recommendation panes, using existing local skill/reference data when possible.
related_skills:
  - domain-research-synthesis
  - grounded-citations
---

# Local personal dashboard

Use this when the user wants a browser-based dashboard or homepage that mixes live updates with personalized recommendation widgets.

For a compact size/scope triage before loading this whole skill, see `references/dashboard-scope-ladder.md`.
For the smallest first-build boundary, see `references/first-build-boundary.md`.

## When to use
- The user asks for a web dashboard, start page, or control panel.
- The dashboard should blend current information with user-specific recommendation panes.
- Existing Hermes skills or local reference files already contain taste seeds, curation data, or ranking inputs.

## Core approach
1. Prefer a tiny local app first.
   - Default to a single-file Python HTTP server or similarly lightweight stack when the request is small.
   - Avoid introducing frameworks, package installs, or build systems unless the user asks for a larger app.
2. Reuse local knowledge sources before inventing new data stores.
   - For music/film/news panes, look for existing skill reference files, vault notes, or local seeds that already encode the user's taste.
   - Keep the first version stateless unless the user explicitly wants persistence.
3. Make each pane independently refreshable.
   - Provide separate API endpoints per pane.
   - Wire separate refresh buttons so partial failures do not blank the whole dashboard.
4. Keep news low-friction.
   - Prefer RSS or other keyless public feeds for the daily-update pane.
   - Group results into the user's standing topic lanes rather than dumping a raw feed.
5. When the dashboard needs entity watchlists (politicians, companies, teams, creators), separate directory coverage from live enrichment.
   - Build a complete searchable directory from the most stable accessible roster source first.
   - Layer richer live fields only where accessible sources actually expose them.
   - Keep the UI honest: a profile may be directory-complete but live-detail-partial.
   - If "top mentioned in the last 24h" is requested but you only have a subset of accessible media surfaces, label the ranking explicitly as a monitored-source approximation rather than a universal media index.
   - Keep an explicit monitored-source registry in code, not just ad hoc scraping calls. Mix direct source pages with resilient fallbacks such as Google News RSS search when individual outlets are JS-heavy, rate-limited, or structurally inconsistent.
   - Emit the actual monitored source labels in the generated payload (for example `sourceHealth.monitoredSources`) so coverage can be verified from the artifact rather than inferred from code.
   - For public-figure profiles, widen social discovery beyond the primary roster source: merge stable Wikidata handles first, then scrape linked official websites and public profile pages for outbound social anchors.
   - Normalize discovered social URLs before storing them: canonicalize Twitter→X, drop share/intent/post/reel/story links, and prefer durable account/profile URLs.
   - When a dashboard has a legislation/watchlist pane and the canonical parliament site is intermittently WAF-blocked, switch from brittle blind scraping to a curated seeded-watch model: keep explicit APH bill-page URLs and bill IDs in code, then refresh surrounding coverage via resilient feeds such as Google News RSS and official/party announcement searches.
   - For legislation panes, keep the source contract narrow and explainable: federal-only when the user asks for federal tracking, no YouTube/news-video links in the bill coverage lane unless the user explicitly wants video sources, and every tracked bill should either map to an existing dashboard policy lane or be independently justified as a currently trending federal debate.
   - Separate user-facing product behavior from diagnostics: source-health / ingestion-status cards should be gated out of production by default and shown only in non-prod/test builds unless the user explicitly asks for operational telemetry in the live UI.
   - For social-summary sections, prefer real recent-post extraction over profile-level metadata whenever the user asks for "top posts" rather than generic social presence. In practice: use public X profile HTML first when it exposes logged-out post text, timestamps, and engagement counts; rank by a transparent engagement heuristic over the last 7 days; and only fall back to profile/page metadata when no recent public post data is accessible without login.
- Do not present Instagram profile pages as if they contain usable recent-post summaries when the logged-out surface is login-walled. If a platform requires login for meaningful post extraction in the current approach, prefer another public platform with real accessible post data instead of emitting fake or generic summaries.
- For X-based social summaries, extract post-level artifacts (status URL, post text, created-at timestamp, likes/reposts/replies) from the logged-out HTML payload when available, then summarize the top five recent posts with direct links and explicit engagement counts.
- For social-summary sections, prefer page-derived metadata over placeholder prose only as a fallback path: fetch `og:title`, `og:description`, `twitter:description`, or `<title>` from durable profile URLs when true recent-post extraction is unavailable.
- When the user wants an issue-centric policy tab, do not leave a separate generic "source pulls" panel in the UX. Consolidate live items back into the relevant policy issue, keep the issue list ordered by chatter, and make the selected-issue pane explain the issue rather than the ingestion plumbing.
- For policy-issue detail views, de-emphasize generic popularity/support/against dashboards when the user asks for party positioning instead. Prefer: party-by-party position summaries (Labor, Liberals/Coalition, Greens, One Nation when relevant), relative media favourability, key quotes, then concise case-for/case-against bullets and linked thinktank / consultation / white-paper sources.
- For politician-watch detail panes, keep monitored-media items compact and skimmable: a small hyperlinked bullet list beats large repeated announcement cards when the user asks for a cleaner watch surface.
- If the user asks for cleaner product UX, remove broad explanatory sections like "What this build now covers" or methodology blurbs from the visible dashboard and keep that context in code/comments/references instead.
- For polling panes built from irregular public tables such as Wikipedia, keep party-primary extraction column-aware and row-structure-aware: do not rely on naive `colspan` expansion alone when the table mixes aggregate Coalition cells, split LIB/LNP/NAT cells, and follow-on 2PP rows. Parse the logical primary slots first, treat a `colspan=3` Coalition cell as the aggregate Coalition value when present, sum LIB/LNP/NAT only when those cells are genuinely split, and only then consume trailing 2PP cells. Sample-check at least two live rows after refresh before trusting the generated artifact.
- When a user says the polling numbers do not reconcile to the visible source table, treat source reconciliation as the first bug and chart styling as secondary. Verify generated rows against the literal rendered source rows (not just your internal parser assumptions), then reshape the chart only after the numbers match the source.
- For wiki-inspired polling charts, prefer the source page's visual grammar over generic dashboard chrome: line-first presentation, small dot markers at real data points, wide inner plot area, and axis spacing that echoes the upstream chart while still fitting the local card layout.
- If the user says the chart still does not reconcile or the labels feel misaligned, verify against the literal visible source rows first, then anchor x-axis labels to the exact plotted `toX(...)` positions rather than an approximate grid. The first visible x-axis label should line up with the first plotted point.
- For dense polling x-axes, start by reducing label payload before changing geometry: if the user wants a cleaner date lane, format labels as compact numeric `dd/mm` and shrink only the x-axis font slightly while keeping the labels anchored to the exact plotted `toPlotX(...)` positions.
- Prefer date-only x-axis labels for compact poll charts unless the user explicitly asks to keep pollster names in the axis lane; move pollster identity to tooltips, tables, or other secondary UI rather than forcing a mixed date/pollster axis.
- Keep the x-axis label lane tight to the baseline; avoid leaving a large visual gap between the 0-line / chart baseline and the x-axis labels.
- When the product needs both readable labels and a more dramatic line span, split x-positioning into two explicit tracks only if the user truly wants intentional horizontal distortion. For ordinary cleanup passes, keep one shared coordinate system so points, ticks, and labels cannot drift.
- For polling-chart cleanup requests, treat "align the first/last dates with the first/last dots" as a concrete geometry invariant. Verify leftmost label ↔ first dot and rightmost label ↔ last dot after each sizing/layout pass; do not assume a shared grid or flex row is close enough.
- If the user asks for a large size change such as '3x bigger', scale the rendered chart height but re-check proportion afterwards. A successful pass is not just bigger: it must preserve readable vertical proportions, aligned labels, tight baseline-to-label spacing, and wiki-style point visibility.
- Distinguish carefully between 'make it bigger' and 'stretch it wider.' If the user wants the chart 1.5x proportionately bigger, enlarge the rendered chart size and reopen the inner plot area while keeping a normal single SVG coordinate system. Do not fake proportional enlargement by widening the viewBox or using `preserveAspectRatio="none"`; that distorts axis text, shrinks point visibility, and can leave only a few barely visible points.
- For follow-up poll-chart sizing passes, preserve these invariants together: all dots visible, evenly spaced x positions from the same `toPlotX(...)` mapping used by labels, explicit per-dot DOM identity, normal unstretched axis text, and a line that is simply lengthened by point spacing rather than globally stretched by SVG scaling.
- When the user wants polling comparability across majors and minors, start from separate 2PP vs primary surfaces, but treat that split as a product choice rather than a permanent rule. If the user later wants a simpler main polling view, collapse the visible UX back to primaries and keep 2PP only in compact summary cards or other clearly secondary surfaces.
- For issue-centric political dashboards, treat fresh official party policy announcements as first-class policy-surface inputs, not just background source pulls. Bubble recent covered-party announcements into the issue/policy lane itself and link them to the closest tracked issue when possible.
- When a Vite dashboard needs one pane to refresh live without rebuilding the app, keep the generated TS artifact for first paint but also emit the same payload to `public/data/*.json` and have the client refresh from that static JSON on entry plus the requested interval. Scope the polling to the active pane/tab and surface a visible timestamp/status chip so the user can tell live refresh is armed.
- If you add a client-side refresh effect in a Vite/React dashboard, account for jsdom/Vitest explicitly: use an absolute URL built from `window.location.origin` for fetches, and either stub or skip the effect in test mode when the test is not exercising the endpoint.
- For social-summary refreshes that can invoke heavier per-profile extraction, keep enrichment bounded to a ranked subset of profiles so the refresh stays usable; if a profile has no real accessible social-post summaries, fall back in the UI to recent official/public items rather than leaving a dead-looking summary pane.
- When the user says the "social" section is still mostly news repetition, treat cross-section deduplication as a product requirement: normalize titles/URLs, remove near-duplicate items already used in announcements / quotes / controversies, and prefer a smaller genuinely social-only set over a fuller but repetitive mixed-source pane.
- For bounded social enrichment ranking, do not key the subset only off mention/news score if the product goal is profile-level social coverage. Rank primarily by the presence and quality of accessible social links, then use mention score as a secondary ordering signal so the generated artifact does not collapse to one or two richly covered figures.
- For macro tabs that mix static thematic lenses with live content, add a dedicated foreign-policy statement lane when requested: collect recent public statements by Australian officials, foreign governments, and major international bodies, require Australia relevance, filter out generic portal/homepage and stale historical results, and rank the remaining items by a transparent chatter heuristic.
- For polling panes sourced from date-range tables, do not trust `Date.parse` on labels like `15–21 Jun`. Add a normalizer that converts range labels into a comparable single date (for example the range end plus current year) before sorting or plotting, or the SVG can render with all x positions collapsed.
- When a poll SVG renders but looks distorted, treat chart geometry as a separate product bug from data correctness: define an explicit inner plot area (left/right/top/bottom margins), start gridlines and polylines inside that plot box rather than under axis labels, and indent the x-axis date labels so they line up with the plotted points instead of the full card width.
- For poll-chart legibility, do not use `preserveAspectRatio="none"` unless distortion is explicitly desired. Keep y-axis labels visually subordinate to x-axis labels, give point markers a small contrasting stroke so the data points remain readable against the line/background, and tune chart geometry with an explicit middle-ground pass rather than swinging between extremes.
- If the user explicitly asks to make the plotted polling geometry much wider without increasing height or font size, treat that as an intentional horizontal-distortion request. In that case, widen the SVG viewBox/plot span, keep the chart in a horizontally scrollable viewport, and compensate text/stroke/marker sizing separately so the lines and points stretch while fonts remain visually unchanged.
- In practice for poll-chart UI cleanup, prefer iterative rebalancing over one-shot shrink/grow edits: if the chart looks stretched, first tighten the inner plot box and line/dot weight before aggressively shrinking the whole chart; if it then looks tiny, raise the overall chart height slightly and reopen the plot area while keeping the lighter y-axis typography. The goal is medium-size readability, not maximal compaction.
- When the user asks for a cleaner polling surface, treat auxiliary summary cards (for example 2PP lead / rolling average / latest minor-party primary callouts) as removable secondary chrome, not core content. Prefer the primary chart plus table unless the user explicitly wants the summary-card lane retained.
- In politician-watch panes, keep headline/count copy tied to the actual generated data. Do not hardcode `Top 10` when the artifact currently contains fewer profiles.
- When the user asks to make a localhost dashboard available across the LAN, treat network reachability as a two-layer task: app binding plus host firewall policy. Binding the server to `0.0.0.0` (or the explicit LAN IP) is only half the job; verify the listen socket moved off loopback and separately check whether the OS firewall already allows the chosen TCP port.
- For LAN-enabling a lightweight Python dashboard, prefer three explicit knobs in code/config: `HOST` for the bind address, `PORT` for the serving port, and a loopback `HEALTHCHECK_HOST` for single-instance self-probes. This preserves the localhost preflight while allowing LAN clients to connect.
- If firewall changes require privilege you do not have, stop claiming the dashboard is universally reachable and report the split status precisely: app-level LAN bind complete, firewall opening still required. Give the exact privileged command(s) the user must run.
6. Personalize explicitly.
   - Use saved taste/preferences to explain why each recommendation appears.
   - For curated entertainment panes, keep a small verified pool and rotate from it rather than fabricating live discovery.

## Implementation pattern
1. Inspect existing skills already relevant to the request.
   - If music or entertainment recommendation skills were loaded, mine their reference files first.
2. Build these minimum routes:
   - `/` for the HTML dashboard
   - `/api/daily-update`
   - `/api/music`
   - `/api/stayin` or equivalent domain-specific pane routes
   - `/healthz`
   - For entity-watch dashboards, add one structured payload per watch pane (for example `/api/polly`, `/api/players`, `/api/companies`) rather than scattering entity state across many tiny endpoints.
3. Keep rendering simple.
   - Static HTML/CSS/JS is enough for a first pass.
   - Use fetch-based refresh buttons for each pane.
4. Sanitize rendered data.
   - Escape interpolated fields before inserting into `innerHTML`, or build DOM nodes safely.
   - Prefer hardened XML parsing when consuming RSS.
5. Verify with live execution.
   - Start the server.
   - Hit every API route.
   - Open the page in a browser tool and confirm the panes render.
   - If localhost browser automation is unavailable or stalls, fall back to terminal-first preview proof: confirm the listening socket (`ss -ltnp` or equivalent), fetch the page with `curl -I` and `curl` to confirm HTTP 200 plus the expected HTML title/root mount, then give the user the exact loopback URL and running process handle so they can open it locally.
   - Click refresh controls and confirm at least one pane actually changes when it is supposed to rotate.
   - For searchable entity panes, verify both the top-card path and the search-result path open the same detail view.
   - Verify the empty-data states are explicit for partially enriched profiles instead of silently omitting sections.

## Personalization guidance
- Music pane:
  - Use local taste seeds and neighbor/reference maps first.
  - If no live provider exists, rotate through a curated candidate pool derived from those seeds.
  - Keep the music pool refreshable after heavy use: once the obvious curated shortlist is exhausted, expand through deeper local seed tracks and neighbor-graph candidates instead of reusing already rated items.
  - When the user asks for taste-based ranking, score music candidates with a blended preference model that includes lifetime ratings, last-30-days ratings, and a strongest-weight recent signal so the newest feedback moves the pane fastest.
  - Treat explicit content-shape requests as product requirements, not soft preferences. If the user says "no artist spotlights," remove spotlight-style artist-only entries from the recommendation surface entirely rather than merely downranking them.
  - If the user wants song links, make the song title itself the clickable link; a YouTube search/result link is a good low-friction default when canonical URLs are not already stored.
- TV/movie pane:
  - Build a compact shortlist from the user's known taste lanes.
  - If you cite scores, verify them during the build and store the verified values in code or a reference file.
  - If the user wants external links, make the title itself the link; Metacritic is a good default when it is also your score source.
- Feedback loop:
  - Prefer inline per-card feedback controls over a separate form so the rate/save action stays attached to the item.
  - Persist small-scale feedback locally with a simple durable store first; SQLite is the default best fit for a lightweight local dashboard.
  - Store at least: item kind, stable item id, rating, and updated timestamp. Add title/artist/type metadata if it helps later personalization.
  - Feed saved ratings back into selection immediately by favoring highly rated seeds/types/items and filtering or demoting poorly rated ones.
  - When the user treats ratings as a proxy for seen/heard state, exclude every rated item from future recommendation surfaces by default, not just low-rated ones.
  - Do not silently fall back to previously rated items just to keep a pane full. If the unseen pool is exhausted, return fewer cards (or none) and say so explicitly in the API/UI note.
  - Do not interpret "prefer songs over artist spotlights" as permission to keep any spotlight cards when the user has explicitly said not to show them. A direct UX/content prohibition should remove that card type from the live surface entirely.
  - Surface existing ratings in the UI so the user can see what has already been seen/heard and so future sessions can verify persistence quickly.

  - After a save, do not reload the whole pane if the user expects continuity. Remove only the rated card, request exactly one replacement with the currently visible item ids excluded, append that replacement, and renumber the survivors in place.
  - Make pane recommendation endpoints support small refill requests (for example `limit=1` plus repeated `exclude_id` query params) so the front end can refill incrementally without changing the rest of the visible shortlist.
  - When wiring per-card save controls, prefer DOM event listeners or delegated click handling plus `data-*` attributes over inline `onclick` HTML attributes. Quote-sensitive ids/titles like `Burnin' for You`, `It's My Life`, or `C'mon Let's Go` can make inline handlers fail intermittently even when most cards still work. Treat `JSON.stringify(...)` escaping as a fallback, not the preferred pattern.
  - For dynamic recommendation panes, do not make the save API depend solely on the current server-side catalog membership. If a visible card can disappear from the next regenerated pool after one save/refresh, include stable card metadata in the POST body (at least title plus the fields needed to rebuild the row, such as artist/seed/type) and let the backend resolve saves by current catalog first, then existing durable row, then client-supplied metadata.
  - Keep the candidate pool deep enough to support refill-after-save behavior. If a pane should stay at five visible items after exclusions, audit both the durable rated-item count and the total curated pool size; the underlying pool must contain materially more than five viable options after rated-item filtering or the pane will visibly shrink.

  - Align categories to the user's ongoing interests instead of generic world-news buckets.

## Pitfalls
- Do not stop after writing the dashboard; run it and verify actual responses and browser rendering.
- Do not add heavyweight dependencies for a simple local dashboard.
- Do not make the whole page depend on one refresh path.
- Do not claim a pane is refreshable unless repeated requests change output or truly re-pull live data.
- Do not hardcode fabricated “live” recommendations; if discovery is curated, label it clearly.
- Do not present a subset-media mention ranking as if it were the entire media universe; name the monitored surfaces and the approximation.
- Do not rely on direct-page scraping alone for outlet coverage; keep at least one resilient fallback path (such as RSS/search-backed retrieval) for brittle sources and verify the realized source set from the generated artifact.
- Do not store social links straight from arbitrary anchors without normalization; post/share/reel/story URLs rot quickly and should not replace durable profile URLs.
- Do not leave diagnostic ingestion/source-health panels visible in the normal production UX when the user asked for a cleaner product-facing dashboard; gate them behind environment checks.
- Do not keep legislation cards cluttered with coverage and quote blocks when the bill itself is supposed to be the focal point; collapse secondary material into explicit expandable sections.
- Do not keep telling the user a canonical source is "blocked" in the visible UI once a seeded/fallback acquisition model is in place; use the workaround internally and present the APH-linked artifact directly.
- Do not mix state and federal legislation when the watch pane is meant to track federal politics only.
- Do not use video-only sources such as YouTube in a legislation monitoring lane unless the user explicitly requests video coverage.
- Do not block search just because live enrichment is incomplete; keep the full directory searchable and degrade profile richness gracefully.
- In Vite React dashboards, keep Vitest config separate from `vite.config.ts` when plugin/type-version friction appears; a dedicated `vitest.config.ts` avoids build breakage while preserving test setup.
- Do not embed unescaped or quote-sensitive item ids directly into inline `onclick` handlers for rating/save buttons. Apostrophes in titles or song names can break the handler and make saves appear intermittent; prefer delegated listeners or `data-*` attributes, with `JSON.stringify`-escaped inline payloads only as a fallback.
- Do not assume refill bugs are only front-end issues. If a recommendation pane shows fewer than its target count after many saves, compare durable rated-item count against total unique curated candidates before debugging the fetch path; the pool may simply be exhausted.
- Do not assume rating-save HTTP 400s on visible recommendation cards are only bad input or front-end escaping bugs. In dynamic panes, the server may have already rotated the item out of its current candidate pool; verify whether the save path can still resolve the visible card from durable data or POSTed metadata.
- Do not present a polling pane as fixed just because the payload contains rows. For SVG/chart UIs, verify the plotted geometry too: range-style dates can parse to `NaN`/zero and leave the graph visually blank even while summary cards still render.
- Do not respond to 'make it bigger' by widening the SVG coordinate space alone. If fonts, strokes, or markers need compensating variables just to stay readable, you are probably stretching rather than enlarging. Prefer a larger rendered chart plus a modestly reopened inner plot area.
- Do not let social-summary panes recycle the same headline-derived text across announcements, quotes, controversies, and "social" sections. If the user notices repetition, tighten normalization/dedup before adding more sources.
- Do not score social-summary eligibility purely by news mentions when the requested outcome is broader profile coverage; low-news but high-social-link profiles should still be able to surface.
- Do not launch a fresh server instance blindly on a fixed localhost port. Probe the dashboard's own `/healthz` first and exit cleanly if the intended instance is already serving.
- Poll chart blank on date-range labels: Date.parse on range labels like '15-21 Jun' returns NaN, collapsing all x-coordinates to zero and leaving the SVG visually blank even when summary cards render correctly. Add a normalizer that converts range labels to a single comparable date (e.g. range end + current year) before sorting or plotting. Verify chart geometry separately from payload presence: confirm x-coordinates are non-zero and first/last dots align with first/last labels.
- colspan=3 Coalition aggregate rule: When the Wikipedia Coalition column arrives as a single colspan=3 cell, treat that value as the Coalition aggregate directly - do NOT redistribute it to LIB/LNP/NAT sub-columns. Only sum LIB/LNP/NAT when those cells are genuinely separate (no colspan). Send remaining cell-span overflow to trailing 2PP slots. Sample-check at least two generated rows against the literal rendered source rows before trusting the artifact.

## Verification checklist
- Server starts cleanly.
- If the app uses a fixed localhost port, verify second-launch behavior too: a duplicate start should detect the live `/healthz` endpoint and exit without creating a competing instance.
- `/healthz` returns success.
- Each pane endpoint returns structured data with the expected item count.
- The browser page loads and shows all requested sections.
- Refresh buttons work independently.
- Any randomized/rotating pane demonstrably changes across repeated calls.
- When a pane has clickable recommendation titles, verify both the API payload and rendered DOM contain the expected destination URLs.
- For entity-watch dashboards that claim specific outlet coverage, verify both the code path and the generated payload: inspect the collected headline/source-label counts and assert the final artifact names every requested outlet.
- When social discovery is expanded, verify coverage by counting populated link fields in the generated data and confirm at least a sample of profiles gained non-primary-platform links.
- When feedback controls exist, verify both interpretations the user might mean by a rating: preference scoring and seen/heard state. If the user says "don't recommend stuff I've already seen," confirm the recommendation API/browser output excludes all rated items, not merely poorly rated ones.
- For music refresh logic, verify the live pane the user actually consumes: confirm the returned items reflect the intended ranking signals in their reason/explanation text, confirm the pool still produces the target count after many ratings, and confirm any explicitly banned card types (for example artist spotlights) are absent from the live API payload.
- For incremental save/refill UX, verify that saving one card leaves the other visible cards intact and requests at most one replacement item not already present in the pane.
- For rating/save controls, verify at least one item whose id/title contains quote-sensitive characters (apostrophes or double quotes) by exercising the real save path and reading the durable store back afterward. This catches inline-handler escaping bugs that ordinary items will not expose.
- For dynamic recommendation panes with rating persistence, verify a rerate path too: save a visible item, let the pane/catalog refresh or rotate, then save a changed rating for that same item again and confirm the backend no longer returns HTTP 400 just because the item fell out of the current live pool.
- For legislation panes, verify the generated artifact contains APH bill-page links, bill IDs, related policy IDs where applicable, and no disallowed domains such as YouTube when the source policy excludes them.
- For entity-watch dashboards with both monitored-news sections and social-summary sections, sample at least one populated profile and confirm the social bullets are source-distinct from announcements/quotes in the generated artifact, not merely populated.
- For polling panes built from public wiki tables, inspect at least two generated rows after refresh and confirm the mapped party-primary values match the table semantics (especially Coalition vs One Nation / other minor-party columns after `colspan` expansion).
- For poll-chart UI regressions, verify more than "the chart exists": confirm the rendered geometry leaves visible left padding for y-axis labels, that gridlines/polylines start inside the plot area, and that x-axis date labels are indented to the same horizontal span as the plotted series.
- When the user asks for stricter poll-chart geometry, treat these as concrete invariants rather than visual preferences: use dates on the x-axis itself (not a mixed date/pollster lane), anchor each date label to the exact same x-position as its plotted dot, start the first visible date at the x/y-axis intersection, add explicit axis lines, remove extra SVG padding that makes the chart float right, and keep x- and y-axis label sizing matched so neither axis visually dominates.
- For product-facing dashboards, verify the production build hides diagnostic ingestion/source-health panels while non-production builds still expose them for testing.

## References
- Add session-specific source paths, route names, and verification examples under `references/` for reuse in future dashboard tasks.
- See `references/politician-watch-dashboard.md` for an entity-watch dashboard pattern covering full-directory search, monitored-source top-mention ranking, partial live enrichment, and portfolio/department drill-down caveats.
- See `references/politician-watch-sources-and-socials.md` for a compact pattern covering outlet-registry design, Google News RSS fallbacks, monitored-source artifact verification, and normalized social-link augmentation.
- See `references/federal-legislation-and-social-summary-patterns.md` for a compact pattern covering APH-seeded federal bill tracking, production-gated diagnostics, no-YouTube legislation-source policy, and metadata-derived social summary bullets.
- See `references/policy-dashboard-pulse-polls-and-social-enrichment.md` for a compact pattern covering issue-lane promotion of official party announcements, separate 2PP vs primary comparables, bounded social enrichment, and generated-artifact verification order.
- See `references/rating-save-escaping.md` for a compact pattern covering quote-safe inline save handlers, reproduction with `Girlschool — C'mon Let's Go`, and durable-store verification for rating persistence bugs.
- See `references/incremental-rating-refill-and-single-instance.md` for the pattern covering localhost single-instance startup, `limit=1` plus `exclude_id` incremental pane refill, and in-place renumbering after a saved rating.
- See `references/music-pane-rating-regression-and-pool-exhaustion.md` for the paired failure mode where quote-sensitive save handlers only fail on the last few remaining items after the candidate pool becomes too shallow.
- See `references/music-refresh-recency-and-no-spotlights.md` for the pattern covering recency-weighted music scoring, deep-pool refresh after many ratings, and treating "no artist spotlights" as a hard product constraint verified against the live API.
- See `references/music-rating-save-catalog-rotation.md` for the paired failure mode where visible music cards can return HTTP 400 on rerate after the live catalog rotates, plus the fix pattern of POSTing stable metadata and resolving saves by catalog → existing row → client metadata.
- See `references/lan-bind-and-firewalld.md` for the pattern covering LAN-enabling a localhost dashboard, preserving loopback health probes with `HEALTHCHECK_HOST`, and separating app bind proof from firewalld proof.
- See `references/wikipedia-poll-table-reconciliation-and-wiki-style-charting.md` for the concrete failure mode where naive `colspan` expansion broke Coalition / One Nation reconciliation and the chart then had to be restyled toward the visible wiki presentation.
- See `references/poll-chart-horizontal-stretch-with-font-compensation.md` for the pattern covering intentional 2.5x-style horizontal widening, first-date indentation, scrollable SVG viewports, and compensating text/stroke sizes so only the plotted geometry appears stretched.
- See `references/poll-chart-proportional-enlargement-without-distortion.md` for the contrasting pattern where 'make it bigger' means increasing rendered size and inner plot area without widening the SVG coordinate system or stretching axis text.
- See `references/poll-chart-compact-axis-labels.md` for the follow-up pattern where geometry is already correct and the fix is to reduce x-axis label payload with compact `dd/mm` dates plus a slightly smaller x-axis font.

## Vite Runtime Refresh — Generated JSON Pattern

**When:** a pane needs live client-side refresh without rebuilding the whole app (e.g. polling data, live recommendations).

**Pattern:**
- Keep the generated TypeScript module (`src/generated/...ts`) for initial render
- Also emit the same payload to `public/data/live-data.json` in the refresh script
- Hydrate React state from the imported generated payload first, then refresh from the JSON endpoint on entry + on an interval
- Scope the interval to the active tab/pane so background tabs don't keep polling

**Implementation notes:**
- Write both artifacts (TS + JSON) from the same in-memory payload in the refresh script — prevents schema drift between outputs
- Use `new URL('/data/live-data.json?t='+Date.now(), window.location.origin)` to bust cache
- In Vitest/jsdom, guard the live-refresh effect with `import.meta.env.MODE === 'test'` to avoid noisy 404/fetch failures in tests
- Show a refresh-status chip + current payload timestamp so the user can tell if they're seeing a fresh fetch or the last successful payload

**Verification:** run the refresh script and confirm both the TS artifact and `public/data/*.json` were written; run tests; build the app and confirm the production bundle succeeds with the JSON asset present.

See `references/vite-runtime-refresh-generated-json.md` for full pattern.

## Reference files

- `references/news-music-stayin-dashboard.md` — News/music/stay-in dashboard reference
- `references/policy-dashboard-issue-centric-ux-and-polling-heuristics.md` — Policy dashboard issue-centric UX and polling heuristics
- `references/poll-graph-and-social-dedup-regression.md` — Poll graph and social dedup regression
- `references/public-social-post-summaries-without-login.md` — Public social post summaries without login
- `references/vite-dashboard-url-and-lan-startup.md` — Vite dashboard URL discovery and LAN startup
- `references/vite-runtime-refresh-generated-json.md` — Vite runtime refresh from generated JSON
