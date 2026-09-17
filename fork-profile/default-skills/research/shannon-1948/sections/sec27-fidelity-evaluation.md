# Section 27: Fidelity Evaluation Functions

## Core Idea
A continuous source has infinite entropy and would need infinite channel capacity for exact recovery. Practically one only requires recovery to within a tolerance. Shannon shows that any reasonable fidelity criterion, for ergodic source and system, is an average of a pairwise “distance” ρ(x,y) between original and recovered messages.

## Key Concepts
- **Exact transmission is impossible**: “a continuously variable quantity can assume an infinite number of values and requires, therefore, an infinite number of binary digits for exact specification.” Ordinary channels have noise, hence finite C.
- **The real issue**: “Practically, we are not interested in exact transmission when we have a continuous source, but only in transmission to within a certain tolerance.” As fidelity requirements increase, the assigned rate will increase.
- **External description of a system**: source density P(x) on duration-T messages; conditional Px(y) that recovered message is y given x; jointly P(x,y). “If this function is known, the complete characteristics of the system from the point of view of fidelity are known.”
- **Fidelity as an ordering**: a criterion must at least rank two systems P1(x,y) and P2(x,y) (first better, second better, or equal). So it is a numerically valued functional v[P(x,y)].
- **Distance function ρ(x,y)**: “the general nature of a ‘distance’ between x and y. It measures how undesirable it is (according to our fidelity criterion) to receive y when x is transmitted.” Footnote: it is not a metric — generally neither ρ(x,y)=ρ(y,x) nor the triangle inequality.

## Key Results
**Representation theorem.** Under (1) ergodicity of source and system (a very long sample is, with probability nearly 1, typical of the ensemble) and (2) reasonableness (observing typical x1, y1 one can form a tentative evaluation that, as duration increases, approaches the exact v based on full knowledge of P(x,y)), one has

v[P(x,y)] = ∬ P(x,y) ρ(x,y) dx dy

The tentative evaluation ρ(x,y) → v[P] for almost all (x,y) in the high-probability region, and therefore also equals the P-average of ρ.

“Any reasonable evaluation can be represented as an average of a distance function over the set of messages and recovered messages x and y weighted according to the probability P(x,y) of getting the pair in question, provided the duration T of the messages be taken sufficiently large.”

**Examples of ρ:**

1. **R.M.S. criterion.** v = [x(t) − y(t)]² (mean square). ρ(x,y) = (1/T) ∫_0^T [x(t)−y(t)]² dt — squared Euclidean distance in function space (apart from a constant).
2. **Frequency-weighted R.M.S.** Pass e(t)=x(t)−y(t) through a shaping filter k, then average power of the output f = k ∗ e. Equivalent to weighting frequency components before RMS.
3. **Absolute error.** ρ(x,y) = (1/T) ∫_0^T |x(t)−y(t)| dt.
4. **Ear and brain.** Speech/music implicitly define evaluations (e.g. intelligibility: ρ = relative frequency of incorrectly interpreted words). “Although we cannot give an explicit representation of ρ(x,y) in these cases it could, in principle, be determined by sufficient experimentation.” Ear relatively insensitive to phase; amplitude and frequency sensitivity roughly logarithmic.
5. **Discrete specialization.** ρ(x,y) = fraction of symbols in y differing from the corresponding symbols in x — frequency of errors. The discrete theory is the special case with this evaluation.

## Key Equations
- v[P] = ∬ P(x,y) ρ(x,y) dx dy
- RMS: ρ(x,y) = (1/T) ∫ [x−y]² dt
- weighted RMS: ρ = (1/T) ∫ (k ∗ (x−y))² dt
- error rate: ρ = (1/n) #{i : yi ≠ xi}

## Significance
This is the conceptual start of rate-distortion theory: fidelity is an expected distortion, not a worst-case metric, and any “reasonable” subjective or physical criterion is of this form once T is large. Intelligibility and hearing experiments are admitted as legitimate ρ. Discrete error frequency is recovered as a special case, unifying Parts I–II with the continuous source.

## Connects To
- Sec 28: rate R1 of a source relative to a fidelity v1; Theorem 21.
- Sec 29: explicit R for white noise vs RMS (Theorem 22) and bounds (Theorem 23).
- Sec 18–19: P(x) lives in 2TW-dimensional function space.
- Discrete error criterion of Parts I–II as example 5.
