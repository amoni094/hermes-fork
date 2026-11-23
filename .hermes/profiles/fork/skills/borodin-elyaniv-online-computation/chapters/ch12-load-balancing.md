# Ch 12 — Load Balancing and Bin Packing

## Makespan minimization (load balancing)

**Problem.** n jobs arrive online, each with processing time p_j. Assign to m machines. Minimize makespan = max_i (load on machine i).

**Greedy (List Scheduling, Graham 1966).**
- Assign each job to the least loaded machine.
- Ratio: 2 − 1/m (optimal for online deterministic).

**Randomized lower bound.** Ω(log m / log log m) vs OBL (Aspnes et al.).

**Restricted machines (graph model).** Each job can go to a subset of machines → ratio Θ(log m).

## Bin packing

**Problem.** Items with size s_i ∈ (0,1] arrive online. Pack into unit-capacity bins; minimize number of bins.

**First Fit (FF).** Open new bin only if item doesn't fit anywhere. Ratio: 1.7 asymptotically (vs OPT offline).
**Next Fit (NF).** Only try current bin; ratio: 2.
**First Fit Decreasing (FFD).** Offline sort + FF: 11/9 · OPT + 6/9.
**Best Fit (BF).** Pack into tightest-fitting bin; asymptotic ratio ≈ 1.7 (same as FF).

**Online lower bound.** No online algorithm achieves ratio < 5/4 asymptotically.

## Hermes application
Cron job scheduling as bin packing:
- Bins = time slots (CPU windows).
- Item sizes = estimated job duration (from executions.db history).
- First Fit on time slots: place next cron job in first window where it fits.
- Prevents 3AM cluster contention (bin = 03:00–04:00 window; don't overpack).
- Track per-slot load sum; alarm at > 0.85 capacity.
