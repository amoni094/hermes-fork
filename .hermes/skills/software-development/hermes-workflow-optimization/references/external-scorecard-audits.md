# External scorecard audits

Use this when the user points Hermes at an external optimization guide, scorecard, or benchmark and says to conform to it.

## Procedure

1. Load the rubric itself first. Prefer the authoritative upstream file over any local summary note.
2. Treat old local score notes as hints, not evidence.
3. Re-score only from live checks that still hold now.
4. Separate workspace-level posture from repo-level posture:
   - workspace control files: `SOUL.md`, `TOOLS.md`, workspace `AGENTS.md`, `MEMORY.md`, `DREAMS.md`
   - repo-level injected docs: project `AGENTS.md`, large prompt-support files, repo-specific constraints
5. Call out mixed results explicitly when one layer passes and another does not.
6. When the user says "make sure you conform," treat the scorecard as an ongoing operating target, not a one-time report.

## What to capture durably

- The benchmark target itself if it is likely to recur.
- Any reusable audit pattern such as "verify live, do not trust stale score notes."
- User workflow preferences revealed by the benchmark request, such as local-first, compact-context, explicit decomposition, and evidence-backed scoring.

## Pitfalls

- Quoting a historic score without re-verifying current state.
- Collapsing workspace and repo prompt surfaces into one number.
- Claiming compliance based on intent or notes instead of live evidence.
