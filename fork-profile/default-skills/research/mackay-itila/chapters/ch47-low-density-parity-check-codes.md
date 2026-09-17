# Chapter 47: Low-Density Parity-Check Codes

## Core Idea
LDPC (Gallager) codes are linear block codes whose parity-check matrix H is sparse. They are *good* (and even very good, with slowly growing degree) under optimal decoding, and they have good distance for column weight j≥3. Practical decoding is not optimal (NP-complete); it is sum–product / belief propagation on the Tanner graph. Density evolution predicts the waterfall; sparse H also allows linear-time encoding tricks.

## Key Concepts
- **Regular Gallager code**: every column of H has weight j, every row weight k; constructed at random under those constraints. Rate ≈ 1−j/k (if rows independent).
- **Tanner / factor graph**: variable nodes (bits) and check nodes (parity constraints ∑_{n∈N(m)} t_n = 0 mod 2).
- **Good / very good codes**: in the sense of Ch 11.4 — arbitrarily small error at rates up to C, or up to C with vanishing gap. LDPC achieve this with optimal decoding.
- **NP-complete optimal decode**: MAP/ML is hard; message passing is the effective algorithm.
- **Two viewpoints**: (a) posterior over codewords t with checks Ht=0 and likelihoods P(r_n|t_n); (b) posterior over noise n with syndrome z=Hr=Hn. Isomorphic for sum–product.
- **Density evolution**: track the distribution of messages vs iteration on the cycle-free ensemble; find a noise threshold f* below which error→0 as N→∞.
- **Stop-when-done**: iterate until all checks satisfied or a cap; distinguish undetected (wrong codeword) vs detected (failure to converge) errors.

## Frameworks and Methods
- **Generic problem**: P*(x) ∝ P(x) [H x = z] with separable P(x). Same graph as Ch 26.
- **Sum–product decoding**: bit-to-check: product of channel prior and other checks; check-to-bit: parity-box (tanh / log-likelihood XOR). Loopy BP; works because sparsity ⇒ long cycles.
- **Pictorial Gallager**: MacKay’s famous figures of error probability vs SNR, showing Shannon-limit-approaching waterfalls for large N.
- **Irregular LDPC**: degree distributions optimized by density evolution (Richardson–Urbanke); better thresholds than regular j=3.
- **Encoding**: naive H→G is O(N³); approximate lower-triangulation of H gives nearly linear encoding (Richardson–Urbanke / MacKay).

## Key Equations
- Code: {t ∈ {0,1}^N : H t = 0 mod 2}
- P(t) ∝ ∏_m [ ∑_{n∈N(m)} t_n = 0 ]
- P(t|r) ∝ P(t) ∏_n P(r_n|t_n)
- Syndrome view: z = H r,  r = t + n,  P(n,z) = ∏ P(n_n) ∏_m [z_m = ∑ H_{mn} n_n]
- Check message (LLR): tanh(u_m→n / 2) = ∏_{n'≠n} tanh(v_{n'→m}/2)
- Rate R = K/N ≈ 1 − M/N,  M rows of H
- Density evolution: f_{ℓ+1} = Γ(f_ℓ ; channel, degree dist); threshold = sup{channel noise : f_ℓ → 0}

## Algorithms and Techniques
**Sum–product (LLR) decode**
1. Initialize variable LLRs from the channel (BSC: log((1−f)/f) for 0, etc.; AWGN: 2y/σ²).
2. For each check m, each incident bit n: send the parity-constraint message excluding n.
3. For each bit n: combine channel LLR with all checks except the recipient; send.
4. After each iteration, hard-decide bits; if H t̂ = 0, stop.
5. Cap iterations (e.g. 50–1000). If unsatisfied, declare detected failure.

**Construction**
1. Sample a random (j,k)-regular bipartite graph; remove 4-cycles if easy.
2. Optional: optimize irregular λ(x), ρ(x) by density evolution.

## Anti-patterns
- **Dense H** — BP dies, encoding dies, “LDPC” name is the point.
- **j=2 regular** — not good distance; j≥3 is the theorem’s hypothesis.
- **Calling BP optimal** — it is excellent but can have error floors from trapping sets / low-weight codewords.
- **Forgetting undetected vs detected errors** when plotting P_e.

## Key Takeaways
1. Sparse random H is enough for Shannon-good codes.
2. Decode with sum–product on the factor graph, not algebraic ML.
3. Syndrome and codeword pictures are the same algorithm.
4. Density evolution is the design tool for thresholds.
5. This is MacKay’s flagship “codes that work” chapter, pairing Ch 1 and Ch 26.

## Connects To
- **Ch 1, 11, 13–14**: why we wanted good codes; existence vs construction.
- **Ch 26**: sum–product on graphs.
- **Ch 25**: trellis / forward–backward as the cycle-free special case.
- **Ch 48–50**: turbo, RA, fountain — other sparse-graph codes.
