# Chapter 15: Continuous Real Time

## Core Idea
Dense-time systems (timed automata) have infinite state spaces. Region (or zone) equivalence yields a finite Kripke structure on which TCTL/CTL can be decided.

## Frameworks Introduced
- **Timed automaton**: locations + real-valued clocks; guards and resets on edges; invariants on locations.
  - When to use: true dense delays, not just tick counts.
  - How: do not discretize ad hoc; use regions.
- **Clock regions** (Alur–Dill): finitely many equivalence classes given max constants in guards. Region graph is a finite Kripke structure.
- **TCTL**: CTL with time-bounded path quantifiers (AF^{<5} p). Model check on the region graph.

## Key Concepts
- **Time divergence**: fair paths must let time pass (no Zeno: infinitely many actions in finite time).
- **Zones / DBMs**: coarser than regions; the practical engine (UPPAAL lineage; later than much of the 1999 exposition but the same finite-quotient idea).
- **Explosion**: region count is exponential in clocks and constants — worse than untimed products.

## Mental Models
- Continuous time is still model checking after a finite quotient.
- Hermes cron is almost always *discrete* (Ch 14). Use this chapter only if the spec is dense-time.

## Anti-patterns
- Sampling time at 1ms and claiming dense-time completeness.
- Forgetting divergence fairness (Zeno counterexamples).

## Worked Example
A timeout of 5.0s modelled with one clock x, guard x≥5, reset x:=0. Regions split [0,5] at integers. AF^{≤5} ack becomes a CTL property on the region graph.

## Key Takeaways
1. Regions finite-ize timed automata.
2. TCTL on the region Kripke structure.
3. Prefer discrete time for Hermes schedulers.

## Connects To
- **Ch 2**: untimed Kripke.
- **Ch 14**: discrete alternative.
