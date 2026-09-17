# Poll graph and social dedup regression

Use this when a local political dashboard shows poll summary cards but no visible graph, or when a politician-watch/social pane is populated yet feels like repeated news rather than actual social activity.

## Poll graph failure mode
- Symptom: poll summary cards render, generated payload contains rows, but the SVG/line chart appears blank.
- Common cause: the source table uses date-range labels like `15–21 Jun` and the UI sorts/plots with raw `Date.parse`, which returns `NaN` or an unusable value.
- Fix pattern:
  1. Normalize range labels before plotting. A practical rule is to take the range end plus the current year, then parse that normalized date.
  2. Keep the chart SVG explicit about sizing (`height`, `display:block`, `preserveAspectRatio="none"` where appropriate) so valid geometry is not hidden by layout collapse.
  3. Verify by checking both data and geometry: the payload may be fine while all x coordinates collapse to zero.

## Poll table mapping failure mode
- Symptom: the graph renders but party lines look implausible.
- Cause: after `colspan` expansion, the apparent second primary-vote column may not be the Coalition total. On the Australian federal Wikipedia polling table, Coalition can sit later in the reconstructed primary array, with One Nation later again.
- Fix pattern:
  1. Expand row cells by `colspan`.
  2. Sample-check at least two live rows against the raw reconstructed array.
  3. Confirm final generated values for Labor, Coalition, Greens, One Nation, and 2PP before trusting the chart.

## Polly social-summary repetition failure mode
- Symptom: profile sections are filled, but the social area repeats news/announcement text already used in other sections.
- Cause: enrichment falls back too early to generic metadata or headline-derived items and those same items are reused across announcements, quotes, controversies, and social summaries.
- Fix pattern:
  1. Normalize titles and URLs before comparing items.
  2. Dedup across sections, not just within one list.
  3. Prefer a smaller truly social-only section to a larger repetitive mixed-source section.
  4. If no real post-level social material exists, label the output as social activity summaries and fall back to recent official/public items only after cross-section dedup.

## Bounded social enrichment ranking
- If enrichment is intentionally limited for refresh-time reasons, do not choose the subset solely by mention/news score.
- Rank first by the presence/quality of accessible social links, then use mention score as a secondary ordering signal.
- This prevents the output from collapsing to just one or two heavily covered figures while leaving most profiles with empty social sections.

## Verification order
1. Refresh the generated artifacts.
2. Inspect at least two poll rows in the generated data for sane party mapping.
3. Confirm at least one visible chart test or UI assertion, not just data presence.
4. Count how many profiles now have social summaries.
5. Sample at least one populated profile and ensure the social bullets are not duplicates of the announcements/quotes lists.
