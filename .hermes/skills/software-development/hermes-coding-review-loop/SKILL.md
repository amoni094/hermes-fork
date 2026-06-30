---
name: hermes-coding-review-loop
description: "Use when you are making bounded code changes and want the Hermes inspect-edit-verify-review loop with minimal diffs and explicit validation."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [hermes, coding, review, verification, diffs, tests]
    related_skills: [hermes-agent, test-driven-development, requesting-code-review, systematic-debugging, hermes-workflow-optimization]
---

# Hermes Coding and Review Loop

## Overview

Use this skill for bounded implementation work where correctness matters more than speed alone.

The loop is: inspect the relevant files, make the smallest useful patch, run the local checks that match the change, fix what verification reveals, and only then report the result.

## When to Use

- You are editing code in a repository.
- You need to keep diffs minimal and understandable.
- You want a repeatable review loop that does not rely on vague judgment.
- You need to convert review feedback into durable changes.

## Review Loop

1. Inspect the target files and nearby context.
2. Make the smallest patch that solves the problem.
3. Run the relevant tests, lint, format, or validation steps.
4. Fix issues that the verification reveals.
5. Repeat until the result is clean.
6. Record the durable lesson in docs or notes.

## Practical Rules

- Prefer a narrow patch over a broad rewrite.
- Avoid blind search-and-replace unless the match is clearly safe.
- Keep symbols and blast radius in mind before changing shared code.
- Use structured outputs and explicit checks when the result will be reused.
- Treat “looks good” as insufficient without a real check.
- When reviewing an external guide or optimization repo against the current codebase, first separate real product gaps from discoverability gaps. If the feature already exists, prefer tightening help text, docstrings, prompt-size labels, or tool-schema descriptions over inventing a larger implementation.
- For small doc/help patches that touch executable Python modules, verify cheaply but explicitly: run the narrow pytest slice that exercises the changed surface and a syntax pass such as `python -m py_compile` on every edited file.
- If a patch tool corrupts a long string or nested literal, inspect the exact damaged region and repair it with the narrowest possible replacement before continuing. Do not trust a successful partial patch when lint or syntax checks disagree.

## External Guide Audit Pattern

Use this pattern when a repo, blog post, or optimization guide claims there are improvements to make:

1. Read the guide and extract concrete claims, not just vibes.
2. Compare each claim against the current checkout.
3. Mark each item as one of:
   - already implemented,
   - implemented but under-documented or hard to discover,
   - genuinely missing.
4. Implement the smallest real improvement that closes the gap.
5. Add or update a targeted regression test for the user-facing behavior you changed.
6. Run lightweight verification before reporting success.

See `references/external-guide-audit.md` for a compact worked pattern.

## Common Pitfalls

1. Editing before inspecting nearby context.
2. Shipping a patch without running the relevant checks.
3. Rewriting more than needed and increasing risk.
4. Reporting success before the change is verified.

## Verification Checklist

- [ ] Relevant files were inspected first.
- [ ] The patch is as small as practical.
- [ ] The right checks ran for the touched surface.
- [ ] Verification passed or failures were fixed.
- [ ] The durable lesson was recorded if the workflow will repeat.
