# Policy dashboard issue-centric UX and polling heuristics

Use this note when a local dashboard mixes policy issues, politician watchlists, polling, and macro/foreign-policy feeds.

## Product-surface guidance from session

- If the user wants a policy tab centered on issues, remove standalone ingestion/source-pull panels from the visible UX.
- Consolidate live source items into the selected issue pane and keep issue cards sorted by descending chatter.
- For selected-policy detail, prefer this order when requested:
  1. short issue summary / stance
  2. party positions (Labor, Liberals/Coalition, Greens, One Nation if relevant)
  3. relative media favourability
  4. key quotes
  5. current linked updates
  6. concise case-for / case-against bullets
  7. thinktank / consultation / white-paper links
- Remove generic explainer sections like "What this build now covers" or methodology blurbs from the visible dashboard when the user wants a cleaner product-facing page.
- In politician-watch panes, recent monitored media should be a small hyperlinked bullet list rather than a wall of cards if the user asks for compactness.
- Social media summaries should be a top-N linked summary list of actual surfaced items. Avoid filler like "detected during refresh" or "open the link for the current social lane."

## Polling extraction note

The federal polling Wikipedia table can expose primaries and coalition sub-columns in an irregular shape.

Safer pattern from this session:
- expand `colspan` values when reading cells so the row is reconstructed back into the visible table shape
- map primary cells positionally from the expanded row instead of inferring Greens / One Nation from the raw percent list
- map 2PP from the trailing 2PP cells after expansion, not by scanning percent pairs globally
- sample-check at least two live rows after refresh, especially a row with coalition `colspan` and a row without 2PP, to confirm One Nation / Greens values stayed column-correct
- verify the generated artifact itself contains plausible One Nation values before claiming the polling lane is fixed

Important pitfall:
- do not derive One Nation by taking the minimum or "remaining" percent after removing a max candidate; coalition sub-columns can be smaller than ONP and will silently corrupt the output

This is still a lightweight parser, but the extraction should be column-aware rather than percent-order heuristic.

## Macro / foreign-policy lane pattern

When the user asks for a foreign-policy live section:
- aggregate from multiple public-statement queries covering Australian officials, foreign governments, major international bodies, and wires
- require Australia relevance explicitly unless the source is an Australian official feed
- prefer statement-style titles/signals such as `statement`, `meeting`, `address`, `speech`, `remarks`, `joint statement`, `press conference`, `says`, `announces`, or `communique`
- filter out generic portal/homepage results, broad live-news hubs, timeless explainer pages, and stale historical items from old years
- rank by a transparent chatter score, but keep the lane honest: it is a scored statement lane, not a full diplomatic discourse model

Important pitfall:
- do not present generic Reuters/world or thinktank analysis hits as if they were recent Australia-focused public statements just because they matched the keyword query

## Sparse politician-surface recovery

For politician-watch dashboards, a workable compromise is:
- keep the full searchable federal directory even if enrichment is partial
- lower the mention-hit threshold modestly when too many profiles are empty, but keep the top-mentioned list filtered to non-zero scores
- keep the headline/count copy honest: if the generated list only has 6 profiles, render `Top 6`, not a hardcoded `Top 10`
- prefer page metadata over brittle full post scraping when platforms resist extraction
- do not strip every useful public profile/social artifact from low-signal politicians just because richer post-level extraction failed; degrade gracefully without reintroducing filler prose
- if direct party-site extraction is inconsistent, use a clearly labelled search-indexed workaround feed rather than leaving the lane empty
