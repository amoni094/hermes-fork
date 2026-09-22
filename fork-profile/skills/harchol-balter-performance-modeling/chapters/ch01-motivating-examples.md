# Ch 1 — Motivating Examples of Analytical Modeling

**Use when**: someone wants to "just build it and tune constants" instead of a model.

## Claim of the book
Computer-system design is full of voodoo constants and post-hoc tuning. Queueing models answer the questions designers actually care about *before* buying hardware.

## Recurring conundrums (keep these)
1. One machine of speed *s* vs *n* machines of speed *s/n* — the single fast machine typically wins on mean response time (a job cannot use *n* slow cores at once unless the work is parallel).
2. Doubling arrival *and* service rate does **not** automatically freeze E[T] (see M/G/1 P-K).
3. Load balancing is not always optimal; greedy shortest-queue routing can be bad for the system.
4. Favoring one class does **not** always hurt others — conservation laws are often misread.
5. High job-size variability / heavy tails change the right scheduling policy.
6. Capacity does not scale linearly: 12 servers at λ=9 does **not** imply 12,000 servers at λ=9,000 (square-root staffing).

## Hermes takeaway
Before changing cron packing, WAL, or skill-router policy, write down (λ, E[S], C², preemptible?, size-known?) and pick a model. Intuition without those four is voodoo.
