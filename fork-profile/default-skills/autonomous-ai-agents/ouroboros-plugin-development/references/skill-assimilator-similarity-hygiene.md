# Skill assimilator similarity hygiene

Use this when patching or reviewing Hermes skill-assimilation / skill-governance generators that suggest consolidation candidates.

Key durable lessons
- Treat structured signals as primary ranking evidence: `related_skills`, tags, workflow family, and skill/category identity should outweigh free-text overlap.
- Treat generic descriptive text as weak evidence only. Common workflow words produce noisy false positives.
- Do not score against absolute filesystem paths. Full paths leak environment-specific tokens (`/var/home/...`) into overlap lists and make human-facing recommendations noisy.
- Prefer path/category components over full paths when building identity tokens.
- Keep a stopword list for generic workflow vocabulary and expand it when human-facing overlap output shows recurring junk tokens.
- Regression tests should allow the generic/noisy candidate to disappear entirely after stricter filtering. Assert that the structured candidate wins; do not require weak candidates to remain present.

Concrete pattern
1. Normalize tokens conservatively.
2. Filter generic workflow terms with a stopword list.
3. Build separate token buckets for:
   - path/category identity
   - skill name
   - description
   - workflow shape
   - tags
   - related skills
   - generic residual text
4. Weight structured buckets more heavily than residual text.
5. For human-facing overlap displays, prefer exact related-skill matches and structured buckets first.

Verification pattern
- Re-run syntax checks after edits.
- Run targeted unit tests for similarity ranking.
- Run at least one live generation against real installed skills and read back the produced balance plan to confirm noisy path tokens disappeared from overlap output.
