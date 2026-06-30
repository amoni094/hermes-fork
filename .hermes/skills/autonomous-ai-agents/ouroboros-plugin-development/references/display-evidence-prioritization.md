# Display evidence prioritization for similarity explanations

Use when consolidation/similarity output is technically correct but still noisy or generic to a human reviewer.

Key rules
- Keep normalized/stemmed tokens for internal similarity math.
- Render human-facing overlap from separate display tokens.
- Suppress entire path-derived display buckets.
- Filter generic frontmatter words from display overlap (`metadata`, `name`, `description`, `tags`, `related_skills`).
- Prefer structured display evidence first: exact related skills, name terms, tags, related-skill tokens, workflow terms.
- Only surface description/generic prose tokens when no stronger evidence buckets are available.
- If live readback still shows weak prose leftovers, add them to display-only stopwords instead of lowering internal scoring weights.
- Make reason strings cite the same evidence shown in overlap output.
- Do not claim shared workflow shape unless the actual workflow-family/profile fields support it; normalized overlap alone is not enough.

Verification pattern
1. Focused regression: readable token appears, stem artifact does not.
2. Focused regression: temp/path fragments do not leak into overlap.
3. Focused regression: weak leftovers like `direct` / `checks` / `for` stay out of overlap when stronger structured evidence exists.
4. Live readback: inspect the emitted candidate JSON and verify overlap + reason string match the intended evidence hierarchy.

Good outcome example
- overlap: `planning`
- reason: `shared skill terms: planning; shared tags: planning`

Bad outcome examples
- overlap: `planning, direct, checks, for`
- overlap: `tmpabc, metadata, tags`
- reason: `shares skill identity, tags, workflow shape` when the displayed evidence does not show that directly
