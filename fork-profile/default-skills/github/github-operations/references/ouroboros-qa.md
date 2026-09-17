# Ouroboros QA for GitHub workflows

Use Ouroboros as a second-opinion QA layer after executable verification, not instead of it.

## When to use
- Reviewing a drafted PR body before posting
- Checking a GitHub Actions workflow diff for readability/scope/safety
- Reviewing a commit summary, review reply, or generated patch explanation
- Sanity-checking a repo summary derived from measured output

## Rule
Run repo-native checks first: diff review, targeted tests/builds, and any repo-required preflight. Then run Ouroboros on the artifact you plan to publish or rely on.

## Preferred command shape
```bash
toolbox run ouroboros qa <artifact-path> -t <artifact-type> -q "<pass bar>"
```

## Good examples
```bash
toolbox run ouroboros qa .github/workflows/ci.yml -t code \
  -q "Workflow YAML is safe, scoped, syntactically plausible, and matches the intended GitHub Actions behavior."

toolbox run ouroboros qa /tmp/pr-body.md -t document \
  -q "PR summary is accurate, complete, and consistent with the verified branch state."

toolbox run ouroboros qa /tmp/test-output.txt -t test_output \
  -q "Test output summary correctly distinguishes branch regressions from unrelated baseline failures."
```

## Interpretation
- Trust executable verification over prose QA when they disagree.
- Use file inputs when possible so the check is reproducible.
- Report Ouroboros as an optional QA pass in the final handoff, especially if it was skipped.
