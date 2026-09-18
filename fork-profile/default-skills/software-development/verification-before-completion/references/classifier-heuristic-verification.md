# Classifier / heuristic verification

Use this when changing parser, router, ranker, or workflow-family scoring logic.

## Verification order

1. Probe the raw parsed structure directly.
   - Example targets: nested frontmatter, normalized tags, related-skills arrays, tokenized aliases.
   - Goal: prove the signal exists before debugging the scorer.

2. Add or update a synthetic regression fixture.
   - Keep it minimal and targeted.
   - Assert the intended signal contributes to classification.

3. Run the relevant automated test suite.
   - This proves the local contract still holds.

4. Run one representative real-corpus example.
   - Prefer an installed skill, real config, or production-shaped sample.
   - Read back both the selected class and the generated reason/explanation field.

5. If the real example flips implausibly, inspect generic matching.
   - Common culprit: substring alias matches such as `writing-plans` unintentionally matching `plan`.
   - Prefer exact matches or token-based matching for generic aliases.
   - Reserve strong weights for concrete workflow-shape markers; keep stage/finish helpers weaker.

## Session pattern captured

A parser fix for nested metadata can be correct while the live classifier is still wrong.
Typical sequence:
- nested metadata was previously flattened or ignored
- regression fixture starts passing after parser repair
- generic alias scoring still dominates in real data
- increasing weights blindly causes overcorrection
- final fix is usually: direct parser probe + regression test + real-corpus readback + narrower generic matching

## Good evidence

- parser probe output showing nested structure is preserved
- unit/integration suite pass after the scoring change
- generated explanation field naming the intended winning signal on a real representative artifact

## Bad evidence

- only a passing unit fixture
- only the top-line predicted class without the explanation field
- only a synthetic example with no real-corpus check
