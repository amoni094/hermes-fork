# Section 13: The Fundamental Theorem for a Discrete Channel with Noise

## Core Idea
A noisy channel has a definite capacity C: one can send at rate C with arbitrarily small error (or equivocation) by proper encoding. Above C, equivocation is at least the excess. Redundancy need not → ∞ as error → 0; that is why C is well-defined rather than a family of error-dependent capacities.

## Key Concepts
- **Surprise Shannon addresses**: “we can never send certain information” on a noisy channel, so a definite C may seem odd. Repeating a message many times can drive error probability down, but one might expect the rate to approach zero. “This is by no means true.”
- **Payment metaphor**: if one attempts rate C + R1, “there will necessarily be an equivocation equal to or greater than the excess R1. Nature takes payment by requiring just that much uncertainty, so that we are not actually getting any more than C through correctly.”
- **Fig. 9**: input entropy H(x) horizontal, equivocation Hy(x) vertical; attainable region is above a line of slope 1 starting from (C, 0). Points on the line generally unattainable except usually two of them.
- **Random coding**: existence via averaging error frequency over a group of codes; if the average is < ε, some code is < ε. “Almost all the systems are arbitrarily close to the ideal.”

## Key Results
**Theorem 11 (noisy channel coding theorem).** Let a discrete channel have capacity C and a discrete source entropy per second H.
- If H ≤ C there exists a coding system such that the source output can be transmitted with an arbitrarily small frequency of errors (or an arbitrarily small equivocation).
- If H > C it is possible to encode so that the equivocation is less than H − C + ε for arbitrarily small ε.
- There is no method of encoding which gives an equivocation less than H − C.

**Proof of H ≤ C (random coding / typical fans).** Let S0 achieve (or approximate) C. For duration T:
1. ~ 2^{T H(x)} high-probability inputs.
2. ~ 2^{T H(y)} high-probability outputs.
3. Each high-probability output has ~ 2^{T Hy(x)} reasonable causes (Fig. 10).

A source of rate R < C has 2^{TR} typical messages. Associate them at random with S0’s typical inputs. For a received y1, the probability a particular input point is a message is 2^{T(R−H(x))}. Probability that none of the other points in the fan is a message:

P = [1 − 2^{T(R−H(x))}]^{2^{T Hy(x)}}

Since R < H(x) − Hy(x), R − H(x) = −Hy(x) − η, η>0, so P → 1 − 2^{−Tη} → 1. Error probability → 0.

**H > C.** Send C bits/s, neglect the rest: neglected part contributes equivocation H(x)−C.

**Converse.** If H(x)=C+a were encoded to Hy(x)=a−ε, then H(x)−Hy(x)=C+ε, contradicting maximality of C.

## Key Equations
- C = Max [H(x) − Hy(x)]
- R < C ⇒ Pe → 0
- R = C + a ⇒ Hy(x) ≥ a
- P_no_collision → 1 when R < C

## Significance
This is the noisy channel coding theorem, the paper’s central result. It creates the entire field of error-correcting codes: reliable communication below C, impossible (in the equivocation sense) above C. The proof is non-constructive (random coding); Shannon notes in Sec 14 that explicit approximations are generally impractical. “Almost all codes are good” is already here.

## Connects To
- Sec 9: noiseless special case Hy(x)=0.
- Sec 12: definition of C and R.
- Sec 14: Theorem 12 restates C as a noisy analogue of lim log N(T)/T.
- Sec 17: Hamming (7,4) as an explicit code meeting C in a block-noise model.
- Sec 21, 24, 28: same typical-volume geometry in continuous spaces; Theorem 21 copies the method.
