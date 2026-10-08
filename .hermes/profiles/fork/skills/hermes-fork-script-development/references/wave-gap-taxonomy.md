# Hermes-Fork Wave Gap Taxonomy

Reference for recursive theory-to-implementation sweeps. Each wave identifies gaps by subsystem,
implements them as scripts, then recurses on what the implementations expose.

## Subsystem partitions (for parallel subagent assignment)

| Subsystem | Domain | Primary corpus sources |
|---|---|---|
| Memory | Compression, TTL, retrieval, commit gating | Wald, Levin-Peres, Vershynin, Cover-Thomas, Villani, Hairer |
| Routing | Skill selection, bandit feedback, adversarial robustness | Lattimore, Borodin-El-Yaniv, Shalev, Manning, Stanley, Lin |
| Loop/Control | Stability, PID, ISS, two-timescale, model comparison | Khalil, Sontag, Berger, Wald |
| Governance/Safety | Falsifiability, multi-principal, taint, minimal footprint | Critch, Amodei, Pearl, Nielson |
| UE/Calibration | Uncertainty estimation, calibration bridges | LM-PolyGraph, Cover-Thomas |
| Compaction | Context channel capacity, R-D advisor | Cover-Thomas, Shannon |

## Gap evaluation criteria (implement vs skip)

Implement if ALL of these hold:
- Stdlib-only implementable (no numpy/scipy unless pre-approved)
- Adds a genuinely new invariant not already covered by existing scripts
- Has a clear --self-test that can pass/fail deterministically
- Has a well-defined output schema (JSON to cache/)
- Grounded in a corpus theorem, not a heuristic

Skip if any of these:
- Requires live LLM inference (belongs in a plugin, not a cron script)
- Duplicates an existing script's invariant (check hermes-scripts/ first)
- Only adds diagnostic UI without an alarm/decision output
- Requires numpy/scipy without pre-approval

## Recursive saturation criterion

Stop recursing when:
- Every new gap identified is either already implemented or fails at least one evaluation criterion above
- The most recent recursive pass produced zero implementable gaps

## Wave history (gap ranges by wave)

| Wave | Gaps | Focus |
|---|---|---|
| 1-17 | Foundation | UE, calibration, routing, PID, governance, shadow |
| 18 | 109 property tests | Invariant coverage |
| 19 | Sheaf, causal, epistemic | Gluing, annotation, S5 modal |
| 20 | Doob, Eckart-Young, VOI, RANSAC, coupling, rough sig | Memory subsystem depth |
| 21 | SPRT, conductance TTL, adaptive rank, channel capacity, OT decay, PAC-Bayes, graph bandits, EXP3, Hamming, Fano, ISS wiring, shadow SPRT, conflict surface, taint lattice | Recursive saturation sweep |

## Script naming convention

- `memory-<theorem>-<action>.py` — memory subsystem
- `routing-<theorem>-<action>.py` — skill routing subsystem
- `loop-<component>-<action>.py` — agent loop / control
- `governance-<topic>-<action>.py` — governance and safety
- `context-<topic>-<action>.py` — context compaction
- `shadow-gate-<method>.py` — shadow feature promotion
- `ue-<method>.py` — uncertainty estimation
- `skill-<topic>-<action>.py` — skill-level analysis
- `callgraph-<analysis>.py` — static analysis / audit
