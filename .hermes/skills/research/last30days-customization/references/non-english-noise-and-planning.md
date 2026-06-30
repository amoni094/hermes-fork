# Non-English noise suppression and named-entity planning

Use this reference when a local `last30days` customization session exposed two recurring issues:

1. English-topic runs picked up mostly non-English noise.
2. Named-entity topics produced degraded fallback output because no explicit `--plan` was supplied.

## Noise-filter pattern that verified cleanly
- File touched: `skills/last30days/scripts/lib/relevance.py`
- Keep the filter lightweight and pre-ranking.
- Gate it on clearly Latin-script queries only.
- A robust gate in this session was effectively `q_non_latin == 0` for the query side.
- Suppress a candidate only when non-Latin alphabetic text dominates the candidate and reaches a clear majority threshold (this session validated a 60% non-Latin share threshold).
- Do not use full language detection; simple script-share heuristics were easier to reason about and less brittle.

## Regression coverage that caught the right class of breakage
- Unit coverage belongs in `tests/test_relevance.py`.
- Integration/ranking-path coverage belongs in `tests/test_pipeline_v3.py`.
- After changing thresholds or query gating, run both targeted tests first, then full pytest if the ranking path changed.

## Named-entity run pitfall
- `--auto-resolve` alone is not enough for richer named-entity runs when no live web-search backend is available.
- For named entities like product/app/tool names, the runtime should generate and pass an explicit `--plan` JSON instead of relying on the deterministic fallback planner.
- Without a plan, the report can still complete, but source coverage and retrieval quality may collapse toward fallback sources.

## Operational takeaway
- Treat “clear out non-English noise” as a retrieval-quality customization problem, not a synthesis problem.
- Verify the fix with a real topic run after tests, because a passing suite can still hide degraded source coverage or planner fallback behavior.
