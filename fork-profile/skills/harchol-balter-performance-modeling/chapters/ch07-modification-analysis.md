# Ch 7 — Modification Analysis (Closed Systems)

**Use when**: "what if we speed the CPU 2×?" on a closed interactive system.

## Asymptotic bounds (closed)
Throughput X(N) sandwiched between:
- Optimistic (no queueing): X ≤ min(N/(D_0+Z), 1/D_max), D_0=∑ D_i
- Pessimistic balanced-system bound

As N→∞, X → 1/D_bottleneck and E[R] ~ N D_max − Z.

## Modification analysis
Changing one device's demand moves the bottleneck. Speeding a non-bottleneck does almost nothing. Closed systems re-circulate; open systems do not. In open networks a local speedup still cuts that node's T_i.

Hermes: a faster model on a closed "one user, sequential tools" loop may not raise throughput if the bottleneck is I/O or think time Z.
