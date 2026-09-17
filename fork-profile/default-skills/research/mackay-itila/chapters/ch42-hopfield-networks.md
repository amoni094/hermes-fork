# Chapter 42: Hopfield Networks

## Core Idea
A Hopfield net is a fully connected symmetric feedback network that works as a content-addressable memory (and, secondarily, as an optimizer). Hebbian outer-product weights make stored patterns (approximate) fixed points of a threshold or tanh dynamics. Capacity of the Hebb rule is ~0.14 N patterns in N neurons; better learning rules raise that. An energy function proves convergence for asynchronous updates.

## Key Concepts
- **Feedforward vs feedback**: DAG vs cycles. Hopfield is the fully connected symmetric case: w_{ij}=w_{ji}, w_{ii}=0.
- **Hebb**: w_{ij} ~ Correlation(x_i, x_j); co-active neurons wire together; later, part of a pattern completes the rest. Unsupervised, local.
- **Binary activity**: x_i ← Θ(a_i), a_i = ∑_j w_{ij} x_j (+ bias). Sync (all at once) vs async (one neuron at a time).
- **Continuous activity**: x_i ← tanh(β a_i); η or β sets gain.
- **Energy**: E(x) = −½ ∑_{i≠j} w_{ij} x_i x_j − ∑ b_i x_i. Async threshold updates decrease E (Lyapunov).
- **Associative memory demo**: noisy / partial strings flow to stored city–country pairs.
- **Spurious states**: mixtures and reverses of stored patterns also become attractors if you store too many.

## Frameworks and Methods
- **Sum of outer products**: W = η ∑_n x^{(n)} (x^{(n)})^T, diagonal zeroed. η scale is irrelevant for binary threshold (sign is invariant); it matters for tanh.
- **Convergence**: for symmetric W and async updates, E is a Lyapunov function → no cycles. Sync updates can cycle.
- **Capacity of Hebb**: with random ±1 patterns, crosstalk is Gaussian; signal-to-noise fails when N_patterns / N ≳ 0.14. Compare Ch 40’s 2 bits/weight: Hebb is far from the information limit.
- **Better than Hebb**: pseudoinverse / perceptron-style rules to make each pattern a stricter fixed point; higher capacity, still limited by geometry of ±1 cubes.
- **Optimization**: encode a combinatorial cost as E(x); Hopfield dynamics is a local search (TSP etc.). Quality is heuristic, not a solver guarantee.

## Key Equations
- Hebb: w_{ij} = η ∑_n x_i^{(n)} x_j^{(n)}  (i≠j)
- a_i = ∑_j w_{ij} x_j
- Binary: x_i ← Θ(a_i);  continuous: x_i ← tanh(β a_i)
- E = −½ x^T W x  (zero diagonal)
- Async: ΔE ≤ 0 when a neuron flips to the sign of a_i
- Crosstalk for pattern n, neuron i: (1/N) ∑_{m≠n} x_i^{(m)} (x^{(m)}·x^{(n)})
- Hebb capacity α_c = M_max/N ≈ 0.138
- Signal ~ 1, noise std ~ √(M/N)  (order-of-magnitude)

## Algorithms and Techniques
**Store and recall**
1. Encode memories as ±1 vectors of length I.
2. Set W by Hebb (or pseudoinverse), w_{ii}=0, W symmetric.
3. Initialize x to a cue (partial/noisy pattern).
4. Async: pick i, set x_i ← Θ(∑_j w_{ij} x_j); repeat until stable.
5. Read out x as the completed memory.

**Continuous / high gain**
- Same W; iterate x ← tanh(β W x). Large β ≈ binary.

## Anti-patterns
- **Synchronous updates** if you need the energy proof / no 2-cycles.
- **Self-connections w_{ii}≠0** — they bias toward the current state, not the memories.
- **Storing M ≫ 0.14 N with Hebb** and being surprised by spin-glass garbage.
- **Asymmetric W** — dynamics may oscillate; not the Hopfield theorem.
- **TSP Hopfield as “the” optimizer** — it is an illustration, often a poor heuristic.

## Key Takeaways
1. Symmetric recurrent nets + Hebb = associative memory with an energy.
2. Async threshold descent on E is why it settles.
3. Hebb capacity ~0.14 bits per neuron (≈0.14 N patterns), not the 2 bits/weight of a feedforward threshold.
4. Spurious attractors are the price of superposition in W.
5. Same energy later becomes the Boltzmann distribution (Ch 43).

## Connects To
- **Ch 31**: Ising / spin glass energy.
- **Ch 38**: associative vs address-based memory.
- **Ch 40**: capacity measured as communication.
- **Ch 43**: stochastic Hopfield = Boltzmann machine.
- **Ch 16, 25**: energy minima vs proper probabilistic decoding.
