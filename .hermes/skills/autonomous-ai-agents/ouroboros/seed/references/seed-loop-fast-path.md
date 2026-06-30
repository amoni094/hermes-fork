# Seed Loop Fast Path

Use this as the compact mental model for `ouroboros/seed`.

1. Load the relevant deferred MCP schema before each ouroboros MCP call.
2. Recover the correct interview/session context before drafting.
3. Generate the seed once.
4. Do not regenerate the seed on every revision pass.
5. Run the QA refinement loop against the generated YAML.
6. Track the best attempt and stop at the documented max-iteration boundary.

Use the full `SKILL.md` when you need the exact Path A / Path B / QA-loop behavior.
