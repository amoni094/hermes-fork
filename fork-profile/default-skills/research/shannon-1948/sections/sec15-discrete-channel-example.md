# Section 15: Example of a Discrete Channel and Its Capacity

## Core Idea
A three-symbol channel (Fig. 11): symbol 1 is never affected by noise; symbols 2 and 3 each pass undisturbed with probability p and swap with probability q. Capacity is obtained by maximizing H(x) − Hy(x) under P + 2Q = 1.

## Key Concepts
- **Channel**: three symbols. The first is noiseless. The second and third form a binary confusion pair.
- **χ = −[p log p + q log q]**: entropy of the 2–3 confusion.
- **P**: probability of using the first symbol. **Q**: probability of using the second (and, at the optimum, of the third).

## Key Results
H(x) = −P log P − 2Q log Q

Hy(x) = 2Q χ

Maximize H(x) − Hy(x) subject to P + 2Q = 1. Lagrange:

∂U/∂P = −1 − log P + λ = 0

∂U/∂Q = −2 − 2 log Q − 2χ + 2λ = 0

so log P = log Q + χ, hence P/Q = 2^χ (log base 2). With P + 2Q = 1:

P = 2^χ / (2 + 2^χ),    Q = 1 / (2 + 2^χ)

C = log(2 + 2^χ) − χ

**Checks.**
- p = 1 ⇒ χ = 0 ⇒ C = log 3: noiseless ternary channel.
- p = 1/2 ⇒ χ = 1 ⇒ C = log 2: symbols 2 and 3 cannot be distinguished and act as one symbol. The first is used with probability P = 1/2; the remaining 1/2 may be split arbitrarily between 2 and 3.

For intermediate p, log 2 < C < log 3. Distinction between 2 and 3 conveys some information, but less than in the noiseless case. “The first symbol is used somewhat more frequently than the other two because of its freedom from noise.”

## Key Equations
- χ = −(p log p + q log q)
- P = 2^χ / (2 + 2^χ),  Q = 1/(2 + 2^χ)
- C = log(2 + 2^χ) − χ

## Significance
A fully worked maximization of mutual information. The optimizer puts more mass on the clean symbol. Capacity interpolates between a ternary noiseless channel and a binary noiseless channel.

## Connects To
- Sec 12: C = Max[H(x) − Hy(x)]
- Sec 16: general p_{ij} system; isolated groups combine as C = log ∑ 2^{C_n}
