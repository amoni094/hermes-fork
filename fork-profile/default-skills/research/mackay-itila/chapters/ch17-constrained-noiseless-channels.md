# Chapter 17: Communication over Constrained Noiseless Channels

## Core Idea
Even a noiseless channel has a capacity less than log|A| if some sequences are forbidden (run-length limits, no adjacent 1s). Capacity is the growth rate of the number of legal strings, equal to log2 λ_max of the constraint’s transfer matrix. Good codes for constraints are often simple variable-length or state-machine codes; they are the noiseless cousin of channel coding.

## Frameworks Introduced
- **Constrained channel**: a subset of A^N is allowed (e.g. no 11, DVD run-length limits).
- **Transfer-matrix / adjacency method**: states = relevant history; A_{ss'} = 1 if the extension is legal. Number of length-N strings ~ c λ^N, C = log2 λ.
- **Maxentropic process**: the Markov chain on the same graph that achieves the capacity; bit-stuffing or arithmetic coding with that Markov model saturates C.
- **Runlength-limited (RLL) examples** MacKay uses:
  - A: 1s have runlength exactly 1; 0s free (no 11? — “runs of 1s restricted to length one”).
  - B: all runs length ≥2.
  - C: all runs length 1 or 2.

## Key Concepts
- **Forbidden strings** reduce capacity; they also aid synchronization (you can recover clock from transitions).
- **State diagram**: nodes are the constraint memory (last bit, current run length).
- **Simple codes C1, C2**: C1 maps 0→00, 1→10 (rate 1/2, legal for channel A). C2 is a variable-length improvement dropping redundant zeros, average length 1.5 bits per source bit if fair bits, rate 2/3.
- **Capacity ≥ any explicit code rate**; matrix method gives the exact C to compare.

## Key Equations
- N_N = 1^T A^{N} 1  (or appropriate start/end vectors)
- C = lim (1/N) log2 N_N = log2 λ_max(A)
- Maxentropic P(s→s') ∝ v_{s'} A_{ss'} u_s  (Perron vectors)
- Code C2: L = (1/2)·1 + (1/2)·2 = 3/2, rate = 1/L = 2/3
- Fibonacci constraint (no 11): λ=φ=(1+√5)/2, C=log2 φ≈0.694

## Algorithms and Techniques
**Capacity of a finite-state constraint**
1. Draw states and legal labelled edges.
2. Write the adjacency matrix A (possibly weighted by 1 per bit emitted).
3. Compute largest eigenvalue λ of A.
4. C = log2 λ bits per channel use.

**Build a simple inner code**
1. Find a mapping from free bits to legal words (block or variable-length).
2. Compute average rate; compare to C. Iterate (add states, use longer blocks) to close the gap.
3. For near-C, arithmetic-code the source using the maxentropic Markov probabilities.

## Mental Models
- Treat a constraint as a noiseless channel with memory.
- Use the Fibonacci / golden-ratio example as the default mental calculation.
- Synchronization: constraints that force frequent transitions buy clock recovery at the cost of C.

## Worked Example
No adjacent 1s (Fibonacci channel). Let a_N = number of legal N-bit strings. a_N = a_{N−1} (end in 0) + a_{N−2} (end in 01). λ=φ, C≈0.694.
- Naive code: map 0→0, 1→10. Rate 1 / (0.5·1+0.5·2)=2/3≈0.667, only 4% below C.
- Channel A in the book (1-runs of length 1 only): C1 rate 0.5; C2 rate 2/3; capacity is log2 of the growth rate of strings matching the run-length table — strictly above 2/3.

## Anti-patterns
- **Assuming C=1 for any binary wire**.
- **Using a rate-1/2 block code when a trivial variable-length code already gets 2/3**.
- **Ignoring decoder state** — constrained codes need a state machine, not a memoryless lookup, if the constraint has memory.
- **Forgetting that capacity here is noiseless**: adding noise requires a *joint* constraint+ECC design.

## Key Takeaways
1. Constraints have a capacity = log2 of the adjacency spectral radius.
2. Simple state codes often get within a few percent of C.
3. The maxentropic Markov chain is the Shannon-optimal input process.
4. Run-length limits are synchronization in disguise.
5. Matrix method > enumerating strings.

## Connects To
- **Ch 6**: arithmetic coding implements the maxentropic process.
- **Ch 9–10**: this C is the noiseless special case of channel capacity.
- **Ch 25**: trellises are these state diagrams with costs/probabilities.
- **Ch 48**: convolutional encoders are state machines too.
