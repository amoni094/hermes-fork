# Software-Dev & GitHub Cluster Audit — August 2026

Audit of the 44-skill SOFTWARE DEVELOPMENT & GITHUB cluster. Findings from a
subagent parallel-read pass (all files batched concurrently in groups of 12).

## Ghost files (HIGH — 5 skills in manifest, missing from disk)

These 5 skills appear in skill system-prompt indexes and `related_skills` pointers
but have no SKILL.md on disk. They were confirmed absent via `read_file` returning
`File not found`. Each one is now a silent dead-end for any agent that tries to load it.

| Skill | Expected path | Disposition |
|-------|--------------|-------------|
| `github-auth` | `github/github-auth/SKILL.md` | Likely absorbed into `github-operations` |
| `github-pr-workflow` | `github/github-pr-workflow/SKILL.md` | Likely absorbed into `github-operations` |
| `github-code-review` | `github/github-code-review/SKILL.md` | Likely absorbed into `github-operations` |
| `github-pr-followup-automation` | `github/github-pr-followup-automation/SKILL.md` | Likely absorbed into `github-operations` |
| `codebase-inspection` | `github/codebase-inspection/SKILL.md` | Unknown — never created or deleted |

**Fix:** Add an "Absorbed Skills" section to `github-operations/SKILL.md` listing each
absorbed skill name with a one-line description of what domain it covered. Then remove
the ghost names from any `related_skills` blocks in other skills that still reference them.

**How to find all related_skills references to these ghosts:**
```bash
grep -rn 'github-auth\|github-pr-workflow\|github-code-review\|github-pr-followup-automation\|codebase-inspection' \
  ~/.hermes/skills/ --include='*.md'
```

## Structural defects found

### Duplicate YAML key in `requesting-code-review`
The frontmatter contains `name: requesting-code-review` at BOTH line 3 and line 26.
YAML spec: when a key appears twice, the second value silently wins. This is a real
defect — if the two values ever diverged, the skill would be indexed under the wrong name.

**Fix:** Remove the duplicate `name:` at line 26. After the fix, verify with:
```python
import yaml
parts = open('~/.hermes/skills/software-development/requesting-code-review/SKILL.md').read().split('---')
fm = yaml.safe_load(parts[1])
assert list(parts[1]).count('name:') == 1
```

### Missing `name:` field in `adversarial-review`
The frontmatter has `author`, `depends_on`, `provides`, `description`, `keywords`,
`license`, `metadata` — but NO top-level `name:` key. This means `skills_list()` and
`related_skills` resolution may fall back to the directory name rather than a declared
canonical name.

**Fix:** Add `name: adversarial-review` and `version: 1.0.0` to the frontmatter.

## Overlap / consolidation findings

### Three review skills — distinct but under-cross-referenced

| Skill | Focus | Trigger discriminator |
|-------|-------|----------------------|
| `requesting-code-review` | Broad pre-commit gate: security scan, quality gates, auto-fix pipeline | "review my code", "pre-merge", "security scan" |
| `risk-based-review` | Decision skill: how much review depth does THIS change warrant? | "should I get a reviewer?", "is this change risky?" |
| `adversarial-review` | Structural contradiction detection, cross-platform consistency | "self-consistency check", "adversarial QA", cross-platform porting |

**They are distinct; do not merge.** But `risk-based-review` should explicitly say:
"After deciding depth here, route to `requesting-code-review` (medium/high) or
`adversarial-review` (high structural risk)." Currently it doesn't.

### `hermes-coding-review-loop` vs `hermes-operating-pattern` overlap (~30%)

`hermes-operating-pattern` (umbrella) re-describes the inspect-edit-verify-review loop
in its body without pointing to `hermes-coding-review-loop` (the focused skill for
exactly that loop). The umbrella should delegate, not re-describe.

**Fix:** Add to `hermes-operating-pattern` body:
```
> For bounded iterative patch-and-review sessions, see `hermes-coding-review-loop`
> rather than following the generic loop description here.
```

### `github-operations` has absorbed multiple missing skills without documenting it

Since `github-pr-workflow`, `github-code-review`, and `github-pr-followup-automation`
are absent, `github-operations` is the de facto owner of those domains. Its description
correctly says "Broad GitHub workflow skill" but doesn't mention the absorbed domains
explicitly, making it hard for future auditors to know the absorption happened.

## Handoff gaps

| Skill | Missing handoff | Fix |
|-------|----------------|-----|
| `github-issues` | No pointer to `github-issue-to-pr` or `github-issue-agent` | Add "once ready for implementation" note |
| `scoped-pr-fix-and-verification` | No pointer to `github-operations` for post-fix PR management | Add to `related_skills` |
| `plan` | No prerequisite pointer to `complexity-gated-planning` | Add "load complexity-gated-planning first" note |
| `symbolic-context-offload` | No pointer to `hermes-context-budgeting` (adjacent domain) | Add bidirectional cross-references |
| `gepa-omni-optimization` | No pointer to `hermes-agent-skill-authoring` (outputs must conform to format) | Add to `related_skills` |
| `split-ci-workflow-change-and-draft-pr` | Missing `scoped-pr-fix-and-verification` in `related_skills` | Add it |

## Trigger quality issues

| Skill | Issue |
|-------|-------|
| `hermes-operating-pattern` | Description too broad ("any Hermes workflow") — competes with `workflow-map`, `plan`, `complexity-gated-planning`. Tighten to "full umbrella, not a single workflow". |
| `subagent-output-contract` | Trigger reads as a formatting instruction rather than a skill. Clarify: this is for subagent tasks where the parent expects machine-parseable JSON output. |
| `workflow-map` | Does not explicitly mention `complexity-gated-planning` as the gate before choosing a workflow path. |

## Audit methodology note (reusable)

This cluster was audited using parallel batch reads (12 files/batch, 4 batches).
For clusters > 30 skills, this approach is essential — serial reads would exceed
context budget before all files are read.

**Pattern:**
1. Read all files in parallel batches (group into ≤12 per tool call).
2. Note files that return `File not found` immediately — these are ghost entries.
3. For large files (>20KB), read only the first 40-60 lines to capture frontmatter
   and section headers; full body read only when overlap/stale content is suspected.
4. Compile findings in one pass; emit structured JSON report.

Ghost-file discovery is the highest-value check in any cluster audit — dead entries
cause silent routing failures that are impossible to diagnose without this check.
