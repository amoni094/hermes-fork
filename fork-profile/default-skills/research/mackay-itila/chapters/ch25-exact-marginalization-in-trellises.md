# Chapter 25: Exact Marginalization in Trellises

## Core Idea
A trellis is a time-indexed state graph. Forward–backward on the trellis computes exact marginals (BCJR / APP) and the max-path (Viterbi) in O(T · |S|²) time. This is *the* decoder for convolutional codes and the smoother for HMMs: Ch 16’s soldiers with probabilities.

## Frameworks Introduced
- **Trellis / HMM**: hidden state s_t ∈ S, observations y_t, factors P(s_1) ∏ P(s_{t+1}|s_t) ∏ P(y_t|s_t).
- **Forward α_t(s) = P(y_{≤t}, s_t=s)**
- **Backward β_t(s) = P(y_{>t} | s_t=s)**
- **BCJR / APP**: P(s_t | y) ∝ α_t(s) β_t(s); edge posteriors similarly. Soft bit outputs for concatenated codes.
- **Viterbi**: (max,×) or (min,+) on the same graph; the single most probable *sequence*, which is not the sequence of most probable states.

## Key Concepts
- **Convolutional encoder trellis**: state = shift-register contents; edges labelled by output bits.
- **Hamming distance / Euclidean metric**: BSC uses −log P(y|x)= Hamming; AWGN uses squared Euclidean.
- **Termination**: extra tail bits to drive state to 0, simplifying the end of the trellis.
- **Soft-in soft-out (SISO)**: BCJR in, LLRs out — the inner engine of turbo codes (Ch 48).
- **Underflow**: scale α each step; accumulated log-scale is the log-likelihood of y.

## Key Equations
- α_{t+1}(s') = sum_s α_t(s) P(s'|s) P(y_{t+1}|s')
- β_t(s) = sum_{s'} P(s'|s) P(y_{t+1}|s') β_{t+1}(s')
- P(s_t=s | y) ∝ α_t(s) β_t(s)
- P(s_t=s, s_{t+1}=s' | y) ∝ α_t(s) P(s'|s) P(y_{t+1}|s') β_{t+1}(s')
- Viterbi: δ_{t+1}(s') = max_s δ_t(s) P(s'|s) P(y_{t+1}|s')
- Complexity O(T |S|²) (or O(T |S| |A|) with sparse transitions)

## Algorithms and Techniques
**Forward–backward (BCJR)**
1. α_1(s)=P(s_1)P(y_1|s). Normalize.
2. Recurse α forward, storing all α_t.
3. β_T(s)=1 (or termination). Recurse backward.
4. Combine for node/edge posteriors; convert to bit LLRs by summing edges with that bit =0 vs 1.

**Viterbi**
1. Same recursion with max and back-pointers.
2. Traceback from the best final state.

## Mental Models
- APP answers “what is P(this bit is 1 | all observations)?”
- Viterbi answers “what is the single most probable path?”
- They disagree when the posterior mass is split across two paths that differ in many bits — use APP for bit error rate, Viterbi for sequence error rate.
- A convolutional code is an HMM whose “observations” are noisy code bits.

## Worked Example
2-state trellis, BSC. Two paths of similar posterior mass that differ in bit 5.
- Viterbi emits one path: bit 5 is 0 or 1 with reported certainty 1 (if you naively read the path).
- BCJR gives P(bit 5=1|y)=0.5, correctly refusing to decide. Concatenated with an outer code, that 0.5 LLR is the right message.

Numerical: store log α, use log-sum-exp. The total log Z = log P(y) is a by-product — useful for model comparison of channels.

## Anti-patterns
- **Using Viterbi bit labels as if they were APP bits** in a turbo/LDPC inner loop.
- **Forgetting normalization** → α underflows to 0 by t≈100.
- **Huge unconstrained state** (e.g. “state = last 30 bits”) destroying O(T|S|²).
- **Not terminating** convolutional codes then treating the end bits as known.

## Key Takeaways
1. Trellises make exact inference linear in time, quadratic in |S|.
2. BCJR = forward–backward = APP bits.
3. Viterbi = MAP sequence, different objective.
4. This is the practical decoder for convolutional codes and HMMs.
5. Log-domain + normalization is not optional.

## Connects To
- **Ch 11, 48**: convolutional and turbo codes.
- **Ch 16**: soldiers / path counting.
- **Ch 26**: same algorithm on trees that are not chains.
- **Ch 47**: LDPC uses the same sum–product, loopy.
