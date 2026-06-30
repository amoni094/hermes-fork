# Agency Agents shortlist pattern

Use this as a concrete example of the source-backed wiki curation workflow.

Scenario
- External source: `msitarzewski/agency-agents`
- Local destination: Hermes Memory Wiki
- Problem: large third-party agent catalog (232 agent files, 16 divisions) with no established local entity-card schema for direct import

What worked
1. Treat the repository as the canonical `sources/` artifact.
2. Confirm the local wiki pattern first by reading workspace guidance and representative `sources/`, `syntheses/`, and report indexes.
3. Add a source note for provenance and review status.
4. Create a synthesis note containing only a vetted shortlist of practically useful imports.
5. Update both source and synthesis indexes.
6. Cross-link the source note to the synthesis note.
7. Re-read changed files and run a targeted git diff for verification.

Why this pattern is reusable
- Avoids exploding a large external catalog into many low-value local notes.
- Preserves provenance cleanly.
- Keeps operator-facing guidance concise.
- Makes later adoption reversible: the synthesis can recommend native plugin/router use instead of local duplication.

Shortlist criteria used
- strong fit with Hermes/local-first workflows
- evidence-first verification value
- minimal overlap with existing local skills
- direct reuse for security, orchestration, verification, or MCP work

Resulting shortlist types
- evidence/reality-check QA roles
- minimal-change/surgical engineering roles
- AppSec review roles
- orchestration/workflow architecture roles
- MCP-building roles

Security-review wording pattern
- say `safe enough to catalogue` when review scope is limited
- do not say `fully audited` unless deeper checks were actually run
- if shell review found destructive operations, describe their scope precisely
- record missing scanners as review-depth limits, not permanent tool incapabilities
