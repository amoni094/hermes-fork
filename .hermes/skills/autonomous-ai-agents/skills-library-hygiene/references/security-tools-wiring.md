# Security Tools: Opt-In Escalation Pattern

## Core principle

Security tools (static analysis, secret scanning, SAST, code audit) should be **opt-in escalations** from the main code-review workflow, NOT hard defaults. This keeps the default path lightweight while making advanced tools discoverable.

## Architecture

### Default path: lightweight grep-based scan
The skill `requesting-code-review` Step 2 runs a **quick grep pass** as the baseline:

```bash
# Hardcoded secrets
git diff --cached | grep "^+" | grep -iE "(api_key|secret|password|token|passwd)\s*=\s*['\""][^'\"]{6,}['\"]"

# Shell injection
git diff --cached | grep "^+" | grep -E "os\.system\(|subprocess.*shell=True"

# Dangerous eval/exec
git diff --cached | grep "^+" | grep -E "\beval\(|\bexec\("

# Unsafe deserialization
git diff --cached | grep "^+" | grep -E "pickle\.loads?\("

# SQL injection (string formatting in queries)
git diff --cached | grep "^+" | grep -E "execute\(f\"|\\.format\(.*SELECT|\\.format\(.*INSERT"
```

This runs on every code review. It's fast (seconds) and catches obvious patterns.

### Escalation path: opt-in tools

When the grep scan finds nothing but you want deeper assurance, or when risk warrants it, **load a specialized skill**:

| Situation | Load |
|-----------|------|
| Secrets / env vars / credentials | `secret-hygiene` |
| Full static analysis (patterns, rules) | `semgrep` (ToB+0xdea rulesets) |
| Interprocedural taint / data flow | `codeql` (needs codeql CLI) |
| OWASP Top 10 / agentic AI threats | `owasp-security` |
| Verify a finding is real before acting | `fp-check` |
| Parse SARIF output from any scanner | `sarif-parsing` |
| GitHub Actions AI injection | `agentic-actions-auditor` |
| Over-hardening / usability regressions | `security-hardening-balance-review` |
| Adversarial pass on agent/runtime code | `security-hardening-code-review` |

### Placement in `requesting-code-review`

Step 2 of `requesting-code-review` now has this structure:

```markdown
## Step 2 — Static security scan

Scan added lines only. Any match is a security concern fed into Step 5.

**Quick grep pass (always run):**
[grep commands here]

**Deeper scan — escalate when risk warrants it:**
[Table of opt-in tools with load commands]
```

This makes the default action obvious (grep) and the escalation path explicit (load a skill when risk changes).

## Decision rules for when to escalate

### Always escalate (do not skip):
- User asks explicitly: "run semgrep", "check for secrets", "scan for AI prompt injection"
- Change involves authentication, API keys, tokens, or credentials
- Change affects agentic AI code (agent prompts, tool calling, context injection)
- Change is in security-sensitive code (validators, auth handlers, trust boundaries)
- Change introduces new dependencies or calls to external services

### Usually escalate (medium-risk changes):
- Significant refactoring where data flow isn't obvious from git diff alone
- Changes to shell commands, subprocess calls, or system interfaces
- Changes to SQL/database queries
- Changes to serialization/deserialization paths

### May skip escalation (low-risk changes):
- Small, obvious fixes to isolated functions with no security touch points
- Documentation-only changes
- Test additions that don't change production code
- Changes already reviewed by domain experts

## Example from this session

After the audit, `requesting-code-review` was patched to:
1. Show grep scan explicitly as the "always run" part.
2. Add a decision table for opt-in escalations.
3. Link to each security skill via load instruction.

Result: Future code reviews will naturally flow from lightweight (grep) to heavyweight (semgrep/codeql) based on actual risk, not by default.

## Related decisions

- `workflow-map` was updated with a "Security Skill Routing" section that maps situations to the right tool.
- No security skills were made hard defaults in any workflow — they remain opt-in.
- The default `requesting-code-review` workflow is still lightweight and fast for routine reviews.
