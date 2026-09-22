# Cheatsheet — Motwani & Raghavan

## Which bound?

```
X ≥ 0, only E[X] known?          → Markov: P(X ≥ t) ≤ E[X]/t
Var known, or pairwise ind.?     → Chebyshev: P(|X−μ|≥t) ≤ σ²/t²
Independent Bernoullis / bounded?→ Chernoff (Thm 4.1–4.3)
Dependent, Lipschitz steps?      → Azuma (Thm 4.16)
Need existence, not concentration?→ Probabilistic method (Ch 5)
```

## Chernoff (copy these)

Poisson trials, `μ=E[X]`, `δ>0`:

- `P(X > (1+δ)μ) ≤ (e^δ / (1+δ)^{1+δ})^μ`
- `P(X < (1−δ)μ) ≤ exp(−μ δ² / 2)`   (`δ<1`)
- Combined (δ≤1): `P(|X−μ| ≥ δμ) ≤ 2 exp(−μ δ² / 3)` (use the theorem forms in proofs)

PAC Bernoulli: `n ≥ (3/ε²) ln(2/δ)` ⇒ `|p̂−p|<ε` w.p. `≥1−δ`.

## Algorithm pick

| Task | Algorithm | Guarantee |
|---|---|---|
| Sort | RandQS | `E[comps] ≤ 2n H_n` (Thm 1.1), Las Vegas |
| Min-cut | contract random edges | success `> 2/n²`; amplify |
| MAX-3SAT | random assignment | `7/8` in expectation |
| MAX-SAT | better of 1/2 and LP-round | `3/4` (Thm 5.5) |
| Set cover | greedy / LP round | `H_n` / `O(log n)` |
| Membership | 2-universal hash | expected `O(1+α)` |
| Static dict. | FKS perfect hash | `O(1)` worst-case |
| Ordered dict. | treap / skip list | expected `O(log n)` |
| `AB=C`? | Freivalds | one-sided error `≤ 1/2` |
| Poly identity | Schwartz–Zippel | error `≤ d/|S|` |
| 2-SAT | random-walk flips | expected `O(n²)` |
| `s–t` undirected | random walk `O(n³)` | RL |
| Paging (oblivious) | Marker | `2 H_k` (Thm 13.3) |
| Paging (det.) | LRU | `k` (tight) |
| Ski rental | rent until `B` then buy | 2-competitive |
| Unique matching | Isolating Lemma | success `≥ 1/2` |
| Primality | Miller–Rabin `t` bases | error `≤ 2^{−t}` |

## Las Vegas vs Monte Carlo

- Must never be wrong → Las Vegas (or MC + verifier, Exercise 1.3).
- Error `δ` OK → Monte Carlo; set repeats `k = Θ(log(1/δ)/log(1/p))`.
- Few random bits → pairwise independence or expander walk, not `k` independent seeds.

## Hermes four

1. **Skill TF-IDF ≈ cosine** — JL: `k = O(ε⁻² log n)` random projection; Chernoff + union bound.
2. **Beta-bandit ready?** — Chernoff PAC `n ≥ (3/ε²) ln(2/δ)`, not “posterior looks peaked.”
3. **Route / bucket weights** — 2-universal `h=(ax+b mod p) mod m`; Chebyshev on load.
4. **Cron timeout** — `t = E[T]/δ` (Markov). Variance known → Chebyshev. Independent stages → Chernoff.

## Do not

- Apply Chernoff to dependent summands (use Azuma or bound the dependence).
- Claim randomised online beats det. against adaptive *offline* adversaries (Thm 13.4).
- Contract random *vertices* for min-cut (Exercise 1.2, exponentially bad).
- Treat Fermat-only tests as primality (Carmichael).
- Quote JL / Goemans–Williamson / AKS as Motwani theorems — they are later or adjacent.
