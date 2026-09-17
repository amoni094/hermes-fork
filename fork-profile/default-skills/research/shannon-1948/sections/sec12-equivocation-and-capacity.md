# Section 12: Equivocation and Channel Capacity

## Core Idea
On a noisy channel one cannot in general reconstruct the message with certainty. The proper correction to the source rate is not the raw error count but the residual uncertainty about what was sent given the received signal — the equivocation Hy(x). Rate of transmission is R = H(x) − Hy(x); capacity is the maximum of R over input distributions.

## Key Concepts
- **Naive error subtraction fails.** Binary source 1000 bits/s, 1% errors: subtracting errors gives 990, but the recipient does not know where the errors are. Extreme: received symbols independent of sent, ~50% “correct” by chance — that would credit 500 bits/s while “actually no information is being transmitted at all. Equally ‘good’ transmission would be obtained by dispensing with the channel entirely and flipping a coin at the receiving point.”
- **Equivocation**: Hy(x), “the average ambiguity of the received signal.” “The amount of this information which is missing in the received signal.”
- **Rate of actual transmission**: R = H(x) − Hy(x).
- **Correction channel** (Fig. 8): an observer who sees both sent and recovered messages sends correction data to the receiver.

## Key Results
**Binary example.** p0 = p1 = 1/2, 1000 symbols/s, error rate 1%. Posterior 0.99 / 0.01.

Hy(x) = −[0.99 log 0.99 + 0.01 log 0.01] = 0.081 bits/symbol = 81 bits/s.

Rate = 1000 − 81 = 919 bits/s.

If posteriors are 1/2, 1/2: Hy(x) = 1 bit/symbol = 1000 bits/s, rate = 0.

**Theorem 10.** If the correction channel has capacity equal to Hy(x) it is possible to encode the correction data so as to send it over this channel and correct all but an arbitrarily small fraction of the errors. This is not possible if the capacity is less than Hy(x).

Roughly: Hy(x) “is the amount of additional information that must be supplied per second at the receiving point to correct the received message.”

Proof sketch: ~ T Hy(x) bits identify which of the ~ 2^{T Hy(x)} plausible M produced M'; send them on a channel of capacity Hy(x). Conversely, for any x,y,z: Hy(x,z) ≥ Hy(x), so Hyz(x) ≥ Hy(x) − H(z). If H(z) < Hy(x) then residual uncertainty given received signal and correction is > 0, so error frequency cannot be arbitrarily small.

Random binary errors with P(wrong)=p: correction need only mark positions, i.e. a source of entropy −[p log p + q log q], equal to the equivocation.

**Three forms of R:**

R = H(x) − Hy(x)     // sent, minus uncertainty of what was sent
  = H(y) − Hx(y)     // received, minus the part due to noise
  = H(x) + H(y) − H(x,y)   // bits per second common to the two

“All three expressions have a certain intuitive significance.” (This last quantity is later called mutual information; Shannon does not name it.)

**Definition of noisy channel capacity:**

C = Max [ H(x) − Hy(x) ]

maximum over all possible information sources used as input. If noiseless, Hy(x)=0 and this coincides with Sec 1, since max entropy for the channel is its capacity.

## Key Equations
- R = H(x) − Hy(x) = H(y) − Hx(y) = H(x) + H(y) − H(x,y)
- C = Max [H(x) − Hy(x)]
- binary BSC-like numerical: 1% errors, R = 919 bits/s from 1000

## Significance
This is the definition of mutual information (unnamed) and of channel capacity as its maximum. Equivocation is operationalized by Theorem 10 (correction-channel characterization). The coin-flip argument kills “fraction correct” as a rate.

## Connects To
- Sec 13: Theorem 11 — C is achievable with arbitrarily small error.
- Sec 15–16: computing C for concrete p_{ij}.
- Sec 24: same R and C for continuous channels; integral form of mutual information.
- Theorem 10 is a characterization of Hy(x), parallel to Theorem 9’s characterization of H.
