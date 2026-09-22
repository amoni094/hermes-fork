# Ch 11 — Randomized k-Server

## Goal
Beat the deterministic lower bound of k by using coins against an oblivious adversary.

## Key algorithms

**Harmonic algorithm (Raghavan & Snir 1989).**
- k servers on metric (X, d). On request r, move server i with probability proportional to 1/d(s_i, r).
- Competitive ratio: O(k^2) vs OBL. Simple but far from optimal.

**Cat-and-rat / Coppersmith et al. (uniform metric).**
- On a uniform metric of n points (all distances 1), HARMONIC achieves ratio H_k = 1 + 1/2 + … + 1/k.
- Lower bound vs OBL on uniform metric: H_k (matches).
- HARMONIC is therefore optimal on uniform metrics.

**Resistive / electrical networks.**
- Model metric as resistive network. Move current = probability mass.
- Used for trees and special metrics; gives ratio O(k log n).

## Key lower bound (Ch 11.4)
For any randomized ALG vs OBL on a metric of n ≥ k+1 points:
  R_OBL(ALG) ≥ H_k

Proof sketch: Yao's minimax (Ch 8) + a hard distribution over uniform-metric requests.

## k-Server conjecture (open)
The (2k−1) ratio of WFA (det.) and H_k ratio (rand.) are conjectured to be optimal:
- Det. conjecture: every DET ALG needs ≥ k (linear in k, not 2k−1).
- Rand. conjecture: H_k is achievable on every metric.

## Hermes application
Skill router as k-server on a semantic metric:
- k = cache size (number of skills loaded in context).
- Metric = cosine distance between skill embeddings.
- HARMONIC loading policy: next skill to load chosen with prob ∝ 1/d(cached_skill, query).
- Expected competitive ratio on semantic space ≈ H_k; better than LRU's deterministic k.
- Practical: use TF-IDF cosine as distance proxy; sample from softmax(−d/T) with temperature T.
