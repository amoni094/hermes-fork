# Display-overlap token hygiene for similarity-driven consolidation

Use this when a consolidation-candidate generator needs human-readable overlap evidence without perturbing ranking.

## Pattern
- Keep normalized/stemmed tokens for internal similarity scoring.
- Build a second display-token view from the same source fields with normalization disabled.
- Compute score from normalized overlap, but render overlap strings from the display-token intersections.

## Why
- Prevents ugly evidence like `plann`, `verifi`, `driven`-style stems in human-facing review output.
- Preserves ranking behavior while improving operator trust and debuggability.
- Limits blast radius to presentation unless you intentionally want to retune scoring.

## Implementation shape
1. Let the tokenization helper accept `normalize=True|False`.
2. In the similarity profile, store both normalized buckets and display buckets for the same fields.
3. In scoring, keep weighted overlap/union on normalized buckets.
4. For reported overlap, read from display buckets in the same bucket order.
5. Keep exact-name/related-skill overlap verbatim in both scoring and display.

## Verification
- Add a regression test asserting a displayed token remains readable, e.g. `planning` appears and `plann` does not.
- Re-run the existing consolidation-ranking tests to prove display cleanup did not change the preferred candidate.
- Do one live readback of generated candidate output, because tests can miss path-noise or metadata-token leakage.

## Follow-up hygiene
If the displayed overlap is now readable but still noisy, inspect for non-semantic tokens from:
- temp/workspace path fragments
- generic frontmatter keys like `metadata`, `name`, `tags`, `description`
- artifact-directory names rather than skill identity

Treat that as a second pass. Do not mix it into the stemming/display-only fix unless you also update the ranking and regression surface deliberately.
