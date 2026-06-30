# Async review gating and generated-dashboard pitfalls

Use this note when a coding task mixes generated artifacts, scraping/ranking surfaces, and pre-push review.

Key lessons:

1. Async reviewer verdicts are not optional gates.
- If an independent reviewer was dispatched with `delegate_task`, commit/push must wait for the verdict.
- If the verdict arrives after a push and contains real issues, do an immediate follow-up fix and re-run verification.

2. Empty states must stay semantically honest.
- Do not fill a section titled as one source/type (for example, social posts) with another source/type (for example, official announcements) just to avoid an empty state.
- Prefer the real empty-state message or add a clearly labeled separate fallback section.

3. Broader scraping must stay relevance-gated.
- When expanding profile/post extraction across platforms, keep expensive scraping limited to entities with current signal, such as non-zero mention/engagement score.
- Cap the number of enriched profiles and subprocess-heavy probes.

4. Brittle parsed tables should not drive headline summaries without sanity checks.
- If upstream tables are position/index parsed and layout can drift, keep suspicious values out of prominent summary cards until validated.
- Raw table display can remain, but add UI copy warning that imported primary rows may be incomplete or shifted.

5. Good verification order for generated dashboards:
- run generator/refresh scripts
- run tests
- run build
- run lint if configured
- inspect a sample of generated output for semantic correctness, not just compilation
