# Appendix 1: Capacity of a Discrete Noiseless Channel

## Core Idea
The number of allowed signals of duration T grows exponentially; the growth rate is log W, where W is the largest real root of a characteristic equation built from symbol durations and (if present) state constraints.

## Key Concepts
- **Unrestricted sequences**: symbols S1…Sn of durations t1…tn. Let N(t) be the number of sequences of duration t.
- **State-constrained channel**: states 1…m; a symbol of type s from state i to state j has duration b_{ij}^{(s)}. N_i(t) = number of sequences of duration t ending in state i.

## Key Results
Without constraints, N(t) = ∑_i N(t − t_i). For large t, N(t) ∼ A W^t, so

C = lim_{T→∞} (log N(T))/T = log W

where W is the largest real root of ∑_i W^{−t_i} = 1.

With states:

N_i(t) = ∑_{j,s} N_j(t − b_{ij}^{(s)})

Asymptotically N_i = A_i W^t, and W is the largest real root of the determinant equation

| ∑_s W^{−b_{ij}^{(s)}} − δ_{ij} | = 0

Then C = log W. This is Theorem 1 of Sec 1.

## Key Equations
- ∑_i W^{−t_i} = 1
- |∑_s W^{−b_{ij}^{(s)}} − δ_{ij}| = 0
- C = log W = lim (log N(T))/T

## Significance
Capacity is a linear-algebra / renewal-theory growth rate, defined before any entropy of a source. Matching a source to this C is Theorem 9.

## Connects To
- Sec 1: statement of Theorem 1 and telegraph examples (Morse, with and without word space).
- Sec 8–9: encoding into this channel.
