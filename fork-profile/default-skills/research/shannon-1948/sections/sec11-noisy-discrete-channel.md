# Section 11: Representation of a Noisy Discrete Channel

## Core Idea
If the received signal is a definite invertible function of the transmitted signal, the effect is distortion and can be inverted. The interesting case is chance perturbation: received E = f(S, N) with noise N a stochastic process. Shannon defines the finite-state noisy channel and the family of joint/conditional entropies of input and output.

## Key Concepts
- **Distortion vs noise**: always-the-same change = distortion; if invertible, correct by the inverse. If the signal “does not always undergo the same change in transmission,” noise is a chance variable.
- **General noisy discrete channel**: finite states; p_{α,i}(β,j) = probability that if the channel is in state α and symbol i is transmitted, symbol j is received and the channel is left in state β.
- **Memoryless noise**: one state; described by p_i(j) = Prob(receive j | send i).
- **Two statistical processes**: source and noise. Entropies:
  - H(x): entropy of the source / channel input (equal if transmitter non-singular)
  - H(y): entropy of the received signal (H(y)=H(x) if noiseless)
  - H(x,y): joint entropy of input and output
  - Hx(y): entropy of output given input (noise entropy, in a sense)
  - Hy(x): entropy of input given output (equivocation, named in Sec 12)
- All of these may be per-second or per-symbol.

## Key Results
The identities of Sec 6 still hold:

H(x,y) = H(x) + Hx(y) = H(y) + Hy(x)

These four quantities are the raw material for the rate of transmission and for channel capacity in Sec 12.

The finite-state description includes channels with memory (noise that depends on past symbols/states), not only i.i.d. noise.

## Key Equations
- E = f(S, N)
- H(x,y) = H(x) + Hx(y) = H(y) + Hy(x)

## Significance
This is the mathematical setup of the noisy channel. Distortion is dismissed as invertible; noise is essential uncertainty. The notation Hy(x) for “what was sent, given what was received” becomes the equivocation — the quantity one subtracts from H(x) to get the rate.

## Connects To
- Sec 12: R = H(x) − Hy(x); C = Max R.
- Sec 13: Theorem 11.
- Sec 16: memoryless channel specified by p_{ij}.
- Sec 24: continuous analogue with densities P(x), Px(y).
