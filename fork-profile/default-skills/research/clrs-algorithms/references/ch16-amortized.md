# Ch 16 Amortized Analysis

Amortized cost is *not* expected cost. It is a worst-case bound on a sequence, divided (or assigned) per operation.

## 16.1 Aggregate

Bound T(n) for any sequence of n ops; each op’s amortized cost is T(n)/n (same for all types).

**Multipop:** a single Multipop is O(n), so n ops look O(n²). But every pop (including those inside Multipop) requires a prior push, so total pops ≤ n. Sequence is O(n); amortized O(1).

**Binary counter:** bit i flips every 2^i increments. Total flips for n increments is < 2n; amortized O(1) per Increment.

## 16.2 Accounting

Charge some operations more than actual; park the surplus as credit on objects. Credit must never go negative, otherwise amortized totals would understate actual cost.

Stack: charge Push 2, Pop 0, Multipop 0. The extra $1 sits on the plate and pays for its later pop.

## 16.3 Potential

Φ maps the whole structure to a real. Amortized ĉ_i = c_i + Φ(D_i) − Φ(D_{i-1}). If Φ(D_i) ≥ Φ(D_0) always (often Φ(D_0)=0 and Φ≥0), total amortized ≥ total actual.

Stack: Φ = object count. Push: ĉ=2. Multipop k′ items: ĉ = k′ + (−k′) = 0.
Counter: Φ = number of 1-bits.

## 16.4 Dynamic tables

Insert into a full table: allocate 2× slots, copy. Load factor stays ≥ 1/2 if only insertions. The i-th insert costs i iff i−1 is a power of 2, else 1. Σ c_i < n + 2n = O(n). Amortized insert O(1) even though one call is Θ(n).

This is the analysis of `vector`/`ArrayList`/`Vec` growth. Review the *sequence*, not the resize in isolation.
