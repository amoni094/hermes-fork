# Fork Profile Memory Snapshot (sanitized)

This file is a sanitized excerpt of operational memory for the fork profile.
Personal identifiers, network addresses, and private device details have been removed.

## Standing Conventions (Denuto 2026-09-16)

1. "No Same Feedback Twice" — every corrective steering must install a durable control
   (hook/test/script/skill), not just documentation.
2. AIMD cross-agent caveat: each Hermes subagent has independent AIMD state —
   no cross-agent fairness convergence; Chiu & Jain TCP convergence proof does NOT apply.
3. Consistency sampling N=3 calibration: 3/3→1.0, 2/3→0.5, 1/3→0.2, 0/3→0.05.
   Conservative basis (Condorcet jury / Lakshminarayanan 2017). GATE GAP: no calibration logging yet.
4. Tier-1 rule must have named gate; GATE GAP marker for rules lacking enforcement.
5. Shadow path NEVER raises — swallows all exceptions.

## Model Routing Notes

- Aux: mistral-small for triage/titles (no reasoning_effort).
- Compression+vision: haiku-4-5@anthropic.
- Routing skill updated 2026-08-30: 9-dim benchmark matrix; Grok-4.6 workers evidenced;
  devstral scaffolding-only; magistral-small for math.

## Scripts / Key Paths

- Scripts live in ~/.hermes/scripts/
- lifecycle.db at ~/.hermes/memory-facts/lifecycle.db
- ARCHITECTURE.md at ~/.hermes/profiles/fork/ARCHITECTURE.md
- Denuto scripts: aimd_controller.py, consistency_scorer.py, shadow_telemetry.py,
  improvement_governance.py, run_ledger.py
