# Section 28: The Rate for a Source Relative to a Fidelity Evaluation

## Core Idea
The rate of a continuous source, given a fidelity v1, is the minimum mutual information R over all test channels Px(y) that achieve that fidelity. Theorem 21: this R1 is necessary and sufficient channel capacity to reproduce the source at fidelity v1.

## Key Concepts
- **Given**: source P(x); continuous distance ρ(x,y); quality v = ∬ ρ(x,y) P(x,y) dx dy.
- **Rate of flow of binary digits** corresponding to a particular P(x,y):

R = ∬ P(x,y) log [ P(x,y) / (P(x) P(y)) ] dx dy

- **Rate of the source for quality v1**: minimize R over Px(y) subject to v = v1. “We consider, in effect, all the communication systems that might be used and that transmit with the required fidelity. The rate of transmission in bits per second is calculated for each one and we choose that having the least rate.”

## Key Results
**Definition.**

R1 = Min_{Px(y)}  ∬ P(x,y) log [P(x,y)/(P(x)P(y))] dx dy

subject to

v1 = ∬ P(x,y) ρ(x,y) dx dy

**Theorem 21.** If a source has a rate R1 for a valuation v1 it is possible to encode the output of the source and transmit it over a channel of capacity C with fidelity as near v1 as desired provided R1 ≤ C. This is not possible if R1 > C.

**Converse.** Immediate from the definition of R1 and previous results: otherwise one would send more than C bits/s over a channel of capacity C.

**Direct part (quantization + random covering, analogue of Theorem 11).** Divide (x,y) space into small cells so the problem is discrete; continuity of ρ keeps v within ε. Let P1(x,y) be the minimizing system, giving R1. From the high-probability y’s choose a random set of 2^{(R1+ε)T} members, ε→0 as T→∞. For large T each chosen y is joined by a high-probability “fan” (as in Fig. 10) to a set of x’s. Almost all x’s are covered by these fans for almost all choices of the y’s.

**The system.** Selected y-points are assigned binary numbers. When message x originates, it lies (probability → 1) in at least one fan; transmit the corresponding binary number over the channel (possible since R1 ≤ C) with small error probability. Reconstruct that y as the recovered message. Evaluation v′ → v1 because for each long sample the evaluation approaches v1 with probability 1.

**Quantizing noise.** “It is interesting to note that, in this system, the noise in the recovered message is actually produced by a kind of general quantizing at the transmitter and not produced by the noise in the channel. It is more or less analogous to the quantizing noise in PCM.”

## Key Equations
- R = ∬ P(x,y) log [P(x,y)/(P(x)P(y))] dx dy
- R1 = min R  s.t.  E[ρ] = v1
- R1 ≤ C  ⇒  fidelity arbitrarily near v1
- R1 > C  ⇒  impossible

## Significance
This is Shannon’s 1948 statement of the rate-distortion theorem (fully developed in his 1959 paper). Source coding with a fidelity criterion is dual to channel coding: C is a max of mutual information, R1 a min. The encoder’s job is to pick a covering of typical x by about 2^{R1 T} reproduction points. Channel noise can be made irrelevant; distortion is chosen at the transmitter.

## Connects To
- Sec 12–13: R and Theorem 11, copied in geometry (fans, Fig. 10).
- Sec 24: the same integral for channel rate; Appendix 7 for the measure-theoretic meaning.
- Sec 27: v and ρ.
- Sec 29: C vs R as max vs min of the same functional; explicit white-noise RMS rate.
- 1959 “Coding Theorems for a Discrete Source with a Fidelity Criterion”: the modern rate-distortion function R(D).
