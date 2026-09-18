# Chapter 4: Discrete Memoryless Channels and Capacity

## Core Idea
For a discrete memoryless channel (DMC), capacity C is the maximum of I(X;Y) over input distributions Q. The converse shows that R > C forces error probability away from zero; achievability is postponed to the random-coding theorem of Ch 5.

## Key Concepts
- Channel specification: input alphabet, output alphabet, and P(y | x) (Gallager often writes P(j | k) for letters).
- Discrete memoryless channel: P_N(y | x) = ∏_{n=1}^N P(y_n | x_n). No intersymbol interference, no state.
- Input assignment Q(k): designer’s choice of letter probabilities (or, for codes, empirical composition).
- Average mutual information I(Q; P) = ∑_{k,j} Q(k) P(j|k) ln [P(j|k) / ∑_i Q(i)P(j|i)].
- Capacity C = max_Q I(Q; P), in nats per channel use.
- Binary symmetric channel BSC(ε): C = ln 2 − H_b(ε) nats (i.e. 1 − h_2(ε) bits), H_b the binary entropy in nats.
- Binary erasure channel: erasures are known positions; C = (1 − p_erasure) ln 2 nats for binary inputs.
- Converse: a theorem that no code of rate > C can have P_e → 0.
- Convex functions: tools for maximizing I(Q; P). I is concave in Q, so a local maximum is global.
- Channels with memory / indecomposable finite-state channels: treated at the end of the chapter; capacity still exists as a limit of I per letter.

## Frameworks and Methods
- Classify the channel first (discrete vs continuous, memoryless vs state, constrained inputs). Do not apply DMC formulas to waveforms (Ch 7–8).
- Capacity as an optimization: maximize a concave function over the probability simplex. Kuhn–Tucker / Gallager’s Theorem 4.4.1: necessary and sufficient conditions on Q.
- Converse architecture: Fano-type bound relating P_e to H(message | Y); then H(message) = NR ≤ I(X;Y) + H(error terms) ≤ NC + o(N) + entropy of errors. If R > C, P_e cannot vanish.
- Memory: if a single-letter P(y|x) still makes sense and memory dies out, interlacing (Ch 6.10) reduces to the DMC with that P.

## Key Results and Theorems
- Definition: C = max_Q I(Q; P) for a DMC.
- Converse to the coding theorem: if R > C, then P_e is bounded away from 0 for any block code (precise Fano form in §4.3). Combined with Ch 5, C is necessary and sufficient.
- Concavity: I(Q; P) is concave ∩ in Q, convex ∪ in the channel transition law P.
- Capacity-achieving Q: I(X = k; Y) ≤ C for all k, with equality for every k with Q(k) > 0. Equivalent: the information density’s conditional mean given each used input equals C.
- Symmetric channels: uniform Q achieves C (BSC, many orthogonal-type discrete channels).
- Memoryless parallel combination: capacities add when each use is independent (energy constraints change this in Ch 7).
- Indecomposable finite-state channels: information rate from any start state converges; a capacity exists.

## Algorithms and Techniques
Finding C for a DMC:
1. If the channel is symmetric, set Q uniform; compute I.
2. Otherwise solve the Kuhn–Tucker conditions: for each input k,
   ∑_j P(j|k) ln [P(j|k) / P_Q(j)] ≤ C, equality if Q(k) > 0.
3. If |input| > |output|, at most |output| inputs need positive Q.
4. Numerically: convex optimization (Blahut–Arimoto is later than 1968; Gallager notes a computer can maximize because of concavity).
5. For the converse: apply Fano to H(M | Y^N) ≤ h(P_e) + P_e ln(M−1) and I(M; Y^N) ≤ NC.

## Anti-patterns
- Computing I for a convenient Q and calling it C. Always maximize, or verify KT conditions.
- Using bit formulas (1 − h_2(ε)) while the rest of a calculation is in nats.
- Applying DMC capacity to channels with ISI or unconstrained analog alphabets.
- Thinking the converse is “weak” because it does not give the exponent. The exponent below C is Ch 5; above C, Ch 5.8 gives strong converses / sphere-packing style lower bounds on P_e.
- Designing Q to maximize minimum distance instead of I or E_0 when the goal is Shannon reliability.

## Key Takeaways
1. C is max I, and the converse makes it an operational limit.
2. Concavity turns capacity into a clean convex program with explicit optimality conditions.
3. Achievability is not proved here; Ch 5 supplies P_e ≤ exp(−N E_r(R)) with E_r(R) > 0 for R < C.
4. Memory does not automatically reduce capacity; it complicates models and decoding.

## Connects To
- Ch 2: I(Q; P) is the objective.
- Ch 3: source entropy vs C is the H < C test.
- Ch 5: random-coding exponent uses the same Q; ∂E_0/∂ρ |_{ρ=0} = I(Q;P).
- Ch 6: parity-check ensembles achieve E_r(R) on the BSC.
- Ch 7: same maximization with densities and energy constraints (waterfilling).
- Ch 9: converse revisited with distortion; R(d*) < C.
