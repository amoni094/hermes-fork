---
name: security-hardening-balance-review
triggers:
  - After a broad hardening pass across scripts, helpers, CI, or validation tooling
  - Risky defaults were replaced with opt-in toggles and the change needs an over-hardening check
  - Security hardening change may have introduced usability regressions or checker-policy mistakes
  - Review a hardening change for balance: preserved security intent without breaking normal use
description: >
  Use when: Review security hardening changes for over-hardening, usability regressions, and checker-policy mistakes; preserve secure-by-default behavior while verifying escape hatches, CI compatibility, and false-positive/false-negative balance.
related_skills:
  - requesting-code-review
  - risk-based-review
---

# Security hardening balance review

Use this when a repo has just been hardened, cleaned up, or made more restrictive and you need to decide whether the changes improved safety without harming usability or correctness.

## When to use
- After broad hardening passes across scripts, helpers, CI, or validation tooling.
- When risky defaults were replaced with opt-in toggles or environment gates.
- When a checker, linter, guardrail, or baseline was tightened or rewritten.
- When the user asks for an "over-hardening review" or wants hardening balanced against usability.

## Goals
1. Keep secure-by-default behavior.
2. Preserve legitimate training, lab, or detection semantics.
3. Catch regressions caused by hardening itself.
4. Verify that escape hatches remain discoverable and intentionally gated.

## Review checklist
1. Inspect the diff, not just current files.
   - Separate behavior changes from checker/policy changes.
   - Identify files that changed because of helper hardening versus files that changed because the validator/checker was adjusted.
2. Look for dependency regressions.
   - New imports in validators, CI helpers, or scripts can create accidental setup requirements.
   - If a new dependency was introduced, either add explicit installation/setup or provide a stdlib fallback.
3. Review secure-by-default escape hatches.
   - Dangerous flags like `--force` or insecure TLS modes should be opt-in, not default.
   - Verify the opt-in is explicit (`HASHCAT_FORCE`, `ACS_INSECURE_TLS`, CLI flag, etc.).
   - Verify users can discover the opt-in from help text, docstrings, or output.
4. Review checker/guardrail logic for both directions.
   - Too strict: false positives against intentional detection/training content.
   - Too loose: false negatives because of broad file-level exemptions.
   - Prefer context-aware matching near the risky line over whole-file allowlisting.
5. Preserve semantics for training/detection repos.
   - Strings like suspicious paths or offensive commands may be detection data, not unsafe implementation defaults.
   - Do not remove domain-significant indicators just to satisfy a pattern check.
6. Re-verify after fixes.
   - Compile edited Python files.
   - Re-run the risky-pattern checker.
   - Re-run the repo validator / quality gate.
   - If possible, simulate the missing-optional-dependency path to verify the fallback really works.

## Good patterns
- Secure by default, with explicit environment-gated or CLI-gated insecure mode.
- Help text that explains how to enable the gated compatibility path.
- Checker exceptions based on nearby conditional logic rather than a token appearing anywhere in the file.
- Stdlib fallback when a validator/parser imports optional dependencies.
- For repo-export validators and redaction checks, prefer narrow secret-key patterns plus a small allowlist for known-safe metadata fields instead of broad substring matching like `token` or `secret` everywhere.
- For scripts that mutate live operator state, default to dry-run/read-only mode and require an explicit `--apply`/`--write` flag before rewriting anything.

Reference: `references/repo-export-validator-patterns.md` for config-export repos where the hardening target is false-confidence reduction: narrow secret detection, dry-run-first mutation scripts, atomic generated-file writes, and verification commands that match the actual changed files.

## Common over-hardening mistakes

See also: `references/private-config-export-hardening.md` for a compact pattern covering sanitized-export repositories, validation scripts, and low-risk script defaults.

- Adding a dependency in CI-critical code without updating workflow/install steps.
- Marking a file safe because a guard token appears anywhere in it.
- Replacing useful compatibility flags with hidden environment toggles and no user-facing hint.
- Treating detection signatures (for example suspicious `/tmp/...` paths) as unsafe temp-file usage.
- Removing intentional offensive/lab semantics from a cybersecurity training repo.

## Output format
Summarize findings as:
- Keep
- Adjust
- Revert

For each issue, include:
- severity
- affected file(s)
- why it is over-hardening or regression risk
- smallest safe fix
- verification performed

## Verification minimum
Do not sign off until you have fresh evidence for:
- changed-file compile/syntax success
- checker/guard output
- validator/test output
- any optional-dependency fallback path you introduced

## Notes
This skill overlaps with `risk-based-review` and `verification-before-completion`: use those for general review discipline, and use this skill when the specific question is whether security hardening has gone too far or hidden a regression.
