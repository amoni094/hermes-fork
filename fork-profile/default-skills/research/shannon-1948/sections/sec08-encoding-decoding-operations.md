# Section 8: Representation of the Encoding and Decoding Operations

## Core Idea
Transmitter and receiver are discrete transducers: finite-state maps from input symbol sequences to output symbol sequences. A non-singular transducer has an inverse that recovers the input. Finite-state encoding cannot increase entropy per unit time; non-singular encoding preserves it. On a constrained channel, a specific transition-probability assignment achieves entropy equal to capacity C.

## Key Concepts
- **Discrete transducer**: input sequence → output sequence; finite internal memory, m states. Output is a function of present state and present input; next state is a second such function:

yn = f(xn, α_n)

α_{n+1} = g(xn, α_n)

- **Tandem connection**: if outputs of one transducer identify with inputs of another, the composition is a transducer.
- **Non-singular transducer**: there exists an inverse transducer recovering the original input.
- **Product state space**: source state β and transducer state α; pairs (β,α) with transitions labeled by output blocks y and probabilities inherited from the source.

## Key Results
**Theorem 7.** The output of a finite state transducer driven by a finite state statistical source is a finite state statistical source, with entropy (per unit time) less than or equal to that of the input. If the transducer is non-singular they are equal.

Proof sketch: entropy of the output is a weighted sum over product states; summing first on the transducer coordinate, each term is ≤ the corresponding source term. If non-singular, connect the inverse: H1' ≥ H2' ≥ H3' = H1' hence H1' = H2'.

**Theorem 8.** Let the system of constraints, considered as a channel, have capacity C = log W. Assign

p_{ij}^{(s)} = (B_j / B_i) W^{−ℓ_{ij}^{(s)}}

where ℓ_{ij}^{(s)} is the duration of the s-th symbol from i to j and the B_i satisfy

B_i = ∑_{s,j} B_j W^{−ℓ_{ij}^{(s)}}

Then H is maximized and equal to C.

Thus “by proper assignment of the transition probabilities the entropy of symbols on a channel can be maximized at the channel capacity.” Proof: Appendix 4.

## Key Equations
- yn = f(xn, α_n),  α_{n+1} = g(xn, α_n)
- non-singular ⇒ H'_out = H'_in; always H'_out ≤ H'_in
- max-entropy assignment: p_{ij}^{(s)} = B_j W^{−ℓ} / B_i ,  H_max = C = log W

## Significance
Theorem 7 is the data-processing inequality for finite-state encoding: invertible coding preserves entropy; any coding cannot increase it. That is why the converse of the noiseless coding theorem is immediate (Sec 9): the channel input entropy cannot exceed C, and equals the source entropy if the encoder is non-singular. Theorem 8 identifies the “matched” source on a constrained noiseless channel — the analogue of waterfilling/max-entropy inputs later.

## Connects To
- Sec 1 / Theorem 1: W is the same root that defines C.
- Sec 9: converse uses Theorem 7; matching interpretation in Sec 10.
- Appendix 4: Lagrange maximization of rate under graph constraints.
- Sec 12: noisy capacity is Max[H(x) − Hy(x)], reducing to Theorem 8 when Hy(x) = 0.
