# Ch 4 — Tail Inequalities

Exponential concentration. Chernoff on Poisson trials, then routing, wiring, martingales, Azuma.

## Chernoff bound (Ch 4.1)

`X_1,…,X_n` independent **Poisson trials**: `P(X_i=1)=p_i ∈ [0,1]`. `X=∑ X_i`, `μ=E[X]`.

Proof template: `P(X ≥ a) = P(e^{tX} ≥ e^{ta}) ≤ E[e^{tX}]/e^{ta}` (Markov on the mgf); independence ⇒ `E[e^{tX}] = ∏ E[e^{t X_i}]`; optimise `t`.

**Theorem 4.1 (upper tail).** For `δ > 0`,

`P(X > (1+δ)μ) ≤ (e^δ / (1+δ)^{1+δ})^μ =: F⁺(μ,δ)`.

**Theorem 4.2 (lower tail).** For `0 < δ < 1`,

`P(X < (1−δ)μ) ≤ exp(−μ δ² / 2) =: F⁻(μ,δ)`.

**Theorem 4.3.** For `0 < δ ≤ U`, `F⁺(μ,δ) ≤ exp(−c(U) μ δ²)` with `c(U) = [(1+U)ln(1+U) − U]/U²`. Common corollaries:

- `P(|X−μ| ≥ δμ) ≤ 2 exp(−μ δ² / 3)` for `δ ≤ 1` (rough combined form).
- Additive: `P(|X−μ| ≥ ε n) ≤ 2 e^{−2 n ε²}` (Hoeffding, same mgf method).

**PAC sample complexity (Hermes bandits).** For i.i.d. Bernoulli(`p`), `n ≥ (3/ε²) ln(2/δ)` implies `P(|p̂−p| ≥ ε) ≤ δ`. Do not call a Beta posterior “reliable” before this scale (or an equivalent Hoeffding/Chernoff check).

Do **not** apply Chernoff to dependent summands. If dependence is a martingale with bounded steps, use Azuma.

## Routing on a parallel computer (Ch 4.2)

Oblivious permutation routing on an `N=2^n`-node hypercube.

**Theorem 4.4.** Any *deterministic* oblivious algorithm on `N` nodes of out-degree `d` has an instance requiring `Ω(√(N/d))` steps. Hypercube: `Ω(√N / n)`.

Valiant: route `s →` random intermediate `r → t` (bit-fixing paths). Packets finish in `O(n)` steps **w.h.p.**

**Lemma 4.5.** Delay of a packet ≤ number of other packets whose routes share an edge with it.

**Theorem 4.6.** With probability `≥ 1 − 2^{−5n}`, every packet finishes Phase 1 in `≤ 7n` steps.

**Theorem 4.7.** With probability `≥ 1 − 1/N`, every packet reaches its destination in `≤ 14n` steps.

Randomisation exponentially beats the deterministic oblivious lower bound.

## Wiring / gate-array (Ch 4.3)

Global wiring: randomise net order / tracks. Chernoff on channel load. **Theorem 4.8:** with probability `≥ 1−ε`, maximum congestion is `(1+o(1))` times the expected load (form depends on `w_0`).

## Martingales (Ch 4.4)

Sequence `X_0, X_1, …` is a **martingale** if `E[X_{i+1} | X_0,…,X_i] = X_i`. Then `E[X_i] = E[X_0]` (Lemma 4.11).

**Doob construction (Thm 4.13).** For any r.v. `X` and filter `F_i`, `X_i = E[X | F_i]` is a martingale. Typical: reveal input bits / random choices one at a time (edge-exposure, vertex-exposure).

**Theorem 4.15 (Kolmogorov–Doob).** `P(max_{i≤n} |X_i| ≥ λ) ≤ E[|X_n|]/λ`.

**Theorem 4.16 (Azuma).** If `|X_k − X_{k−1}| ≤ c_k`, then

`P(|X_n − X_0| ≥ λ) ≤ 2 exp(−λ² / (2 ∑ c_k²))`.

Use when summands are dependent but each step has a bounded effect (Lipschitz certificates, configuration functions).

**Theorem 4.18 (occupancy via Azuma/Chernoff).** `m` balls, `n` bins, `r=m/n`, `Z` empty bins: `E[Z] ≈ n e^{−r}`; `Z` concentrates.

## Hermes

- Independent success/fail trials, retries, bandit pulls → Chernoff.
- Dependent process with bounded per-step change (streaming feature, one more document in TF-IDF) → Azuma.
- Hypercube / multi-path routing of jobs → Valiant random intermediate (Thm 4.7).
