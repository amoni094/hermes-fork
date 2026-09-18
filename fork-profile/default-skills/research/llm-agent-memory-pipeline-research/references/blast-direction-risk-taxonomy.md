# Blast-Direction Risk Taxonomy

**Source:** Zenn.dev JP — agent-sns-react-two-stage-gate (Aug 12 2026)

## The Core Problem

When an agent performs actions with different "blast directions" (who bears the impact of a failure),
routing them through a single shared approval gate causes risk-tolerance cross-contamination.

Demonstrated with SNS automation: posting (self-facing, blast = yourself) vs liking/replying
(other-facing, blast = external parties). Mixing them through one gate means a "yes" to post
also implicitly authorizes a react — but these have different failure consequences.

**Key principle: "Separate not by feature, but by risk boundary."**

## Three Blast Directions

| Direction | Examples | Failure consequence | Reversibility |
|---|---|---|---|
| `SELF_BLAST` | File writes, local config, local process kills | You bear the cost | Usually reversible |
| `THIRD_PARTY_BLAST` | External API calls, emails, social reactions, webhooks | External parties bear the cost | Often irreversible |
| `SYSTEMIC_BLAST` | Schema changes, auth changes, shared resource mutations | Team / system bears the cost | Irreversible |

## Implementation in Hermes

1. **Tag each planned action** with blast direction alongside SAFE/CAUTION/HAZARD
2. **Separate approval prompts** per blast direction — a "yes" to SELF_BLAST does NOT authorize THIRD_PARTY_BLAST
3. **Gate structure**: SELF_BLAST gate → THIRD_PARTY_BLAST gate → SYSTEMIC_BLAST gate (always separate)
4. **Add to trajectory enumeration step** (trajectory-risk-guardrail Step 1): annotate each action with both
   the SAFE/CAUTION/HAZARD rating AND its blast direction

## Relation to Existing Hermes Skills

- **trajectory-risk-guardrail**: use blast direction as an additional annotation layer in Step 2
- **mnemosyne-atp-safety**: blast direction determines rollback scope (THIRD_PARTY_BLAST = no rollback possible)
- **async-agent-nightshift-patterns**: unattended agents should block all THIRD_PARTY_BLAST actions pending
  explicit approval — no HITL = escalate THIRD_PARTY actions to next human review window

## Extension of Prior Sweeps

This is a new refinement of the 10-category failure taxonomy established in the Aug 2026 sweeps.
It adds a cross-cutting "blast direction" dimension that applies across all 10 categories.
A CATEGORY-7 failure (external API call) has a different severity depending on whether it's
THIRD_PARTY_BLAST (reaches users) vs SELF_BLAST (internal service call you control).
