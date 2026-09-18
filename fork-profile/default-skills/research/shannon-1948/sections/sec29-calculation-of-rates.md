# Section 29: The Calculation of Rates

## Core Idea
Source rate R1 is a constrained minimum of mutual information; channel capacity C is a constrained maximum of the same functional. The variational solution is an exponential of −λ ρ(x,y). Closed forms exist for white noise versus mean-square error; otherwise Shannon gives entropy-power bounds.

## Key Concepts
- **Duality**:

R = Min_{Px(y)} ∬ P(x,y) log [P(x,y)/(P(x)P(y))] dx dy

with P(x) and v1 = ∬ P ρ fixed.

C = Max_{P(x)} ∬ P(x,y) log [P(x,y)/(P(x)P(y))] dx dy

with Px(y) fixed and possibly K = ∬ P(x,y) λ(x,y) dx dy (e.g. average power).

- **Formal solution**: Lagrange variation on P(x,y) yields

Py(x) = B(x) e^{−λ ρ(x,y)}

with λ chosen for the required fidelity and B(x) so that ∫ B(x) e^{−λ ρ(x,y)} dx = 1.

“With best encoding, the conditional probability of a certain cause for various received y, Py(x), will decline exponentially with the distance function ρ(x,y).”

- **Difference-only ρ**: if ρ(x,y) = ρ(x−y), then B(x) is constant and Py(x) = α e^{−λ ρ(x−y)}. “Unfortunately these formal solutions are difficult to evaluate in particular cases and seem to be of little value. In fact, the actual calculation of rates has been carried out in only a few very simple cases.”

## Key Results
**White noise, mean-square fidelity.** Distance = mean square discrepancy; message ensemble = white noise power Q, band W1; N = (x−y)² allowed.

R = Min [H(x) − Hy(x)] = H(x) − Max Hy(x)

Max Hy(x) occurs when y−x is white noise, and equals W1 log(2π e N). H(x) = W1 log(2π e Q). Therefore

R = W1 log(Q/N)

**Theorem 22.** The rate for a white noise source of power Q and band W1 relative to an R.M.S. measure of fidelity is

R = W1 log(Q/N)

where N is the allowed mean square error between original and recovered messages.

**Theorem 23.** The rate for any source of band W1 is bounded by

W1 log(Q1/N)  ≤  R  ≤  W1 log(Q/N)

where Q is the average power of the source, Q1 its entropy power, and N the allowed mean square error.

Lower bound: Max Hy(x) for given (x−y)² = N is largest in the white-noise case, so R = H(x) − Max Hy(x) is smallest when the source is white of power Q1 (entropy power). Upper bound: place the covering points of Theorem 21 not optimally but at random in a sphere of radius √(Q−N).

## Key Equations
- Py(x) = B(x) exp(−λ ρ(x,y))
- white RMS: R = W1 log(Q/N)
- general RMS: W1 log(Q1/N) ≤ R ≤ W1 log(Q/N)
- dual: R = min I,  C = max I

## Significance
Theorem 22 is the first explicit rate-distortion function: R(D) = W log(Q/D) for Gaussian white sources and MSE, the continuous analogue of “bits needed = excess entropy over the allowed noise.” Theorem 23 sandwiches any source between its entropy power and its actual power — the same N1 vs N pattern as Theorems 18–19 for channels. The exponential kernel Py(x) ∝ e^{−λρ} is the 1948 form of the later “backward test channel” (Gaussian noise for MSE).

## Connects To
- Sec 21: entropy power Q1.
- Sec 23 / Theorem 15: EPI used implicitly in the bounds.
- Sec 25: C = W log((P+N)/N) is dual to R = W1 log(Q/N).
- Acknowledgments: Wiener’s filtering and prediction of stationary ensembles “has considerably influenced the writer’s thinking in this field.”
