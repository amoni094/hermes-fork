# Chapter 14: Discrete Real-Time and Quantitative Temporal Analysis

## Core Idea
When “eventually” is not enough, attach discrete time (clock ticks in the Kripke structure) and quantitative operators: bounded F/G, min/max delay.

## Frameworks Introduced
- **Discrete clocks**: a tick action increments counters; R interleaves ticks and discrete events (or synchronous tick).
  - When to use: cron periods, timeouts, calibration deadlines.
  - How: keep clocks finite (max bound + 1 absorbing) so S stays finite.
- **Bounded temporal operators**: AF^{≤k} p — p within k steps; AG^{≤k} p — p for the next k steps.
  - When to use: “sweep within one hour” modelled as k ticks.
  - How: unwind X k times or add a countdown variable and ordinary CTL.
- **Quantitative analysis**: min/max time to a set (value iteration on the graph). Not probabilistic (that is a different book).

## Key Concepts
- **Finiteness**: unbounded clocks ⇒ infinite S. Always cap.
- **Zeno in discrete time**: infinite ticks with no event — usually forbidden by fairness (justice on events) or by “tick only if some clock is needed”.
- **Expressiveness**: bounded operators are still regular; encode in CTL with extra AP.

## Mental Models
- Discrete time is ordinary model checking plus a counter. If you do not cap the counter, you left Ch 2.

## Anti-patterns
- Modelling wall-clock with an unbounded integer and then running SMV.
- Mixing discrete ticks with continuous-time claims (Ch 15).

## Worked Example
Gate-audit: clock c=0..T_max. Sweep must run by T_max. AF(c≤T_max ∧ calibration_data_available) plus AG (c=T_max → available). If the sweep is only weakly fair, AF may fail; add justice on sweep.

## Key Takeaways
1. Bound the clock.
2. Bounded F/G compile to CTL.
3. Fairness still matters at the deadline.

## Connects To
- **Ch 15**: dense time, regions.
- **Cheatsheet**: gate-audit liveness.
