# Porting notes: obra/superpowers -> Hermes

This local port preserves the upstream workflow shape:

clarify -> plan/spec -> isolate workspace -> execute -> review -> verify -> finish branch

Adaptation decisions:

1. Reuse existing Hermes skills where they already closely match upstream:
   - test-driven-development
   - systematic-debugging
   - requesting-code-review
   - subagent-driven-development
   - verification-before-completion

2. Add Hermes-native wrappers for upstream concepts that were missing by name:
   - using-superpowers
   - brainstorming
   - writing-plans
   - using-git-worktrees
   - dispatching-parallel-agents
   - executing-plans
   - finishing-a-development-branch
   - receiving-code-review
   - writing-skills

3. Keep the port concise and tool-realistic for Hermes instead of copying harness-specific instructions verbatim.

4. Prefer local repo reality over framework ritual when they conflict; the workflow is a guardrail, not an excuse to ignore project-specific requirements.
