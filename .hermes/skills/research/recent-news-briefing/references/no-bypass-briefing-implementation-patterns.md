# No-bypass briefing implementation patterns

Condensed patterns from building a hosted-first recurring news summarizer.

## Source registry curation
- Favor a checked-in `sources.toml` aligned to the user's standing briefing buckets rather than a grab-bag of feeds.
- Keep source IDs stable and human-readable because they surface in bundles and verification output.
- Prefer sources that were actually reachable during verification; remove brittle feeds rather than pretending broad coverage exists.

## Rendering shape
- Markdown should group stories under the requested topic headings first.
- Keep one fallback bucket such as `blind-spots-and-general` for high-signal items that do not map cleanly to the requested headings.
- Preserve JSON as the stable machine-readable output; avoid reshaping it just to mirror Markdown sections.

## Recency and repeat runs
- Default daily or recurring briefings to a recent-window cutoff such as 7 days.
- Keep seen-story state in SQLite so repeat runs can produce an explicit empty state instead of silently repeating yesterday's bundle.
- Write timestamped Markdown + JSON bundle pairs so cron-driven runs are inspectable after the fact.

## Failure isolation
- Treat malformed XML or truncated feed bodies as per-source failures.
- Skip the bad source, continue the run, and emit a compact skipped-source line to stderr/logs for later cleanup.
- Do not collapse the whole run because one publisher feed returned bad XML.

## Topic and clustering hygiene
- For short tokens like `ai`, use whole-word matching instead of substring checks.
- Tighten clustering so cross-topic stories from broad feeds do not merge unless title similarity is strong or topic overlap is real.
- If a cluster summary clearly borrows text from an unrelated story, inspect the merge threshold before changing the summarizer.
