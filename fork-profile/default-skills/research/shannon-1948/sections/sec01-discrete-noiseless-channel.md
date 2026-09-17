# Section 1: The Discrete Noiseless Channel

## Core Idea
A discrete channel is a system that transmits sequences chosen from a finite set of elementary symbols S1,…,Sn, each of duration ti (not necessarily equal), possibly with constraints on allowed sequences. Capacity is the asymptotic growth rate of the number of allowed signals.

## Key Concepts
- **Discrete channel**: “a system whereby a sequence of choices from a finite set of elementary symbols S1,…,Sn can be transmitted from one point to another.”
- **Allowed signals**: not all sequences of the Si need be transmissible; the allowed ones are the possible signals.
- **Telegraph example**: symbols are (1) dot = 1 unit closed + 1 unit open; (2) dash = 3 closed + 1 open; (3) letter space = 3 open; (4) word space = 6 open; adjacent spaces forbidden (two letter spaces = one word space).
- **Finite-state constraints**: states a1,…,am; from each state only certain symbols may be sent; the next state depends on the old state and the symbol. Graph: junctions = states, lines = allowed symbols and resulting state.
- **Teletype special case**: 32 equal-duration symbols, any sequence allowed → 5 bits per symbol; n symbols/sec → capacity 5n bits/sec. This is a maximum; whether it is attained depends on the source (treated later).

## Key Results
**Definition.** The capacity C of a discrete channel is

C = Lim_{T→∞} [log N(T)] / T

where N(T) is the number of allowed signals of duration T. The limit exists as a finite number in most cases of interest.

If all sequences of S1,…,Sn are allowed with durations t1,…,tn, then N(t) satisfies the delay equation

N(t) = N(t − t1) + … + N(t − tn)

and N(t) ~ X0^t where X0 is the largest real root of

X^{−t1} + … + X^{−tn} = 1

hence C = log X0.

Telegraphy (the constrained example) gives N(t) = N(t−2)+N(t−4)+N(t−5)+N(t−7)+N(t−8)+N(t−10) and C = 0.539 (in the paper’s units).

**Theorem 1.** Let b_{ij}^{(s)} be the duration of the s-th symbol allowable in state i and leading to state j. Then C = log W where W is the largest real root of the determinant equation

| ∑_s W^{−b_{ij}^{(s)}} − δ_{ij} | = 0

with δ_{ij} = 1 if i = j and 0 otherwise. Proof: Appendix 1.

## Key Equations
- C = lim_{T→∞} log N(T) / T
- ∑_i X^{−t_i} = 1  →  C = log X0
- det(∑_s W^{−b_{ij}^{(s)}} − δ_{ij}) = 0  →  C = log W

## Significance
Capacity is defined before any notion of entropy or coding. It is a purely combinatorial growth rate of the allowed signal set. Matching a source to this C is the noiseless coding problem of Theorem 9. The finite-state graph is the same object later used for sources (Markoff processes) and for maximizing entropy on a constrained channel (Theorem 8).

## Connects To
- Sec 8–9: encoding a source into this channel; C/H is the symbol rate limit.
- Sec 12: noisy capacity reduces to this definition when Hy(x) = 0.
- Appendix 1: growth of N_j(L) ~ A_j W^L.
- Appendix 4 / Theorem 8: the probability assignment on the graph that achieves entropy C.
