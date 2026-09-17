# Appendix 5: Invariant Operators Preserve Stationarity and Ergodicity

## Core Idea
If T is time-invariant (commutes with shifts) and the input ensemble is stationary (resp. ergodic), so is the output ensemble.

## Key Concepts
- **Shift H_τ**: moves every function in a set by time τ.
- **Invariant operator T**: shifting the input only shifts the output: H_τ T = T H_τ. Filters and rectifiers are invariant under all translations; modulation is invariant under multiples of the carrier period.
- **Push-forward measure**: S1 = T S2; g-measure of S1 is defined as f-measure of S2.

## Key Results
**Stationarity.** Let S1 ⊂ g-ensemble, S2 the preimage under T. Then H_τ S1 = T H_τ S2, so

m[H_τ S1] = m[T H_τ S2] = m[H_τ S2] = m[S2] = m[S1]

the third equality because f is stationary. Thus g is stationary.

**Ergodicity.** Suppose S1 ⊂ g is invariant under all H_τ, and S2 = T^{−1} S1. Then T H_τ S2 = S1, so H_τ S2 ⊂ S2. Measure equality m[H_τ S2] = m[S1] forces H_τ S2 = S2 whenever m[S2] ≠ 0,1 — contradicting ergodicity of f unless no such nontrivial S1 exists. Hence g is ergodic.

## Key Equations
- H_τ T = T H_τ
- m[H_τ S1] = m[S1]

## Significance
Justifies applying entropy, entropy power, and coding theorems to filtered, rectified, or modulated ensembles (Secs 18, 22, 26). Communication theory studies operations on ensembles, not on particular functions (Wiener).

## Connects To
- Sec 18: definition of stationary/ergodic ensembles and invariant operators.
- Sec 22: linear filters.
- Sec 5: discrete ergodicity of Markoff sources.
