---
name: code-impact-preflight
description: 'Code impact analysis: blast radius, confidence, skill hooks. Use when analyzing git diffs or planning code changes. Triggers on `diff-impact`, `code impact`, `blast radius`, `impact analysis`, `git diff`, `code change`.'
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [code, impact, git, diff, review, preflight]
    related_skills: [risk-based-review, hermes-coding-review-loop, verification-before-completion, github-operations]

ssl_scheduling:
  triggers: [analyzing git diffs, planning code changes, estimating blast radius]
  preconditions: [git repo exists, diff-impact.py script available]
  estimated_steps: 3

ssl_structural:
  tools_used: [terminal, read_file, write_file]
  subtasks: [gather diff, analyze impact, suggest skill hooks]

ssl_logical:
  side_effects: [runs git diff, executes diff-impact.py]
  resources: [git repo, diff-impact.py script]
  risk_level: low
---

# Code Impact Preflight

## Overview

Run `diff-impact.py` on a git diff to estimate:
- Confidence level (high/medium/low)
- Blast radius (local/module/project/external)
- Symbols touched
- Files changed
- Suggested skill hooks for review and verification

Use this before making code changes to choose the right review depth and verification steps.

## When to Use

- Planning a code change and want to estimate its impact
- Reviewing a git diff before commit or push
- Deciding whether a change needs deeper review or verification
- Automating pre-commit or pre-push impact analysis

## How to Use

1. **Run the script** on a git diff:
   ```bash
   python3 ~/.hermes/scripts/diff-impact.py --repo /path/to/repo --range HEAD~1..HEAD --json
   ```

2. **Interpret the output**:
   - `confidence`: how certain the analysis is (high/medium/low)
   - `blast_radius`: how far the change reaches (local/module/project/external)
   - `symbols`: which identifiers were touched
   - `files`: which files changed
   - `hooks`: which skills to load for review/verification

3. **Choose review depth** based on blast radius:
   - `local`: Depth 0 (inline verification)
   - `module`: Depth 1 (one reviewer)
   - `project`: Depth 2 (reviewer + final verifier)
   - `external`: Depth 3 (multi-role review)

4. **Load suggested skills** for the chosen depth:
   ```bash
   skill_view(name="risk-based-review")
   skill_view(name="hermes-coding-review-loop")
   skill_view(name="verification-before-completion")
   ```

## Example Output

```json
{
  "impact": {
    "confidence": "medium",
    "blast_radius": "project",
    "symbols": ["main", "parse_args"],
    "files": ["scripts/diff-impact.py"],
    "hooks": ["code-impact-preflight", "risk-based-review", "hermes-coding-review-loop"]
  },
  "stats": {
    "lines_added": 10,
    "lines_deleted": 5,
    "files_changed": 1
  }
}
```

## Common Pitfalls

- **Small diff, high blast radius**: A 2-line change in a shared header can touch every file in the project. Always check `blast_radius`.
- **Low confidence**: When the script reports `low` confidence, inspect the diff manually or run narrower ranges.
- **Missing symbols**: The symbol extractor is conservative. If a symbol isn't listed, it may still be affected.
- **External blast radius**: Changes to files outside the repo (e.g. `~/.hermes/scripts/`) have `external` blast radius and need deeper review.

## Verification Checklist

- [ ] Script ran without errors
- [ ] Output matches the expected JSON schema
- [ ] Blast radius is appropriate for the change
- [ ] Suggested skill hooks are loaded for the chosen review depth
- [ ] Review depth chosen matches the blast radius
