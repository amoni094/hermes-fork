# Ch 27 — Power Optimization, Busy Periods, Setup

**Use when**: idle-vs-off, setup cost, or busy-period length of M/G/1.

## M/G/1 busy period B
Period from idle→busy until empty again. Started by one job of size S plus all arrivals during their service (branching process):
```
E[B] = E[S] / (1−ρ)
B~(s) = S~(s + λ − λ B~(s))     # functional equation
```
Busy period started by work W: W~(s+λ−λB~(s)). Excess-started busy period appears in LCFS waiting time.

## Setup cost / ON-IDLE vs ON-OFF
If turning a server off saves power but costs a setup time I when the next job arrives:
- ON/IDLE: pay idle power, zero setup delay
- ON/OFF: zero idle power, every busy period starts with I

Compare E[T] + energy. Setup is a busy-period inflation: first job pays I plus the work that piles up during I. Do **not** power-off a latency-sensitive WAL writer unless λ is so low that setup is amortized.

## Hermes
Nightly cron vs always-on gateway: model setup as I. If jobs are Poisson and ρ modest, ON/IDLE often wins tail latency; ON/OFF wins only when idle gaps ≫ I.
