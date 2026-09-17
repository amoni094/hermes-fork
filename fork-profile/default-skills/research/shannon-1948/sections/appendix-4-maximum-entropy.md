# Appendix 4: Maximum Entropy for Given Symbol Frequencies

## Core Idea
Among sources using letter frequencies p_i, the independent (zero-memory) source maximizes entropy, and that maximum is −∑ p_i log p_i. The number of sequences with those frequencies is about 2^{HN}.

## Key Concepts
- **Type / composition**: sequences of length N with n_i = p_i N occurrences of symbol i.
- **Number of such sequences**: multinomial N! / ∏ n_i !.

## Key Results
By Stirling, (1/N) log (N! / ∏ n_i!) → −∑ p_i log p_i.

Any dependence among letters can only reduce the number of typical sequences relative to the independent case, hence can only reduce entropy. Therefore H ≤ −∑ p_i log p_i, equality for independent letters.

This underwrites Sec 6 property 2 (max at uniform) and the relative-entropy / redundancy discussion of Sec 7: compression into the same alphabet cannot beat H / log n.

## Key Equations
- (1/N) log (N! / ∏ (p_i N)!) → −∑ p_i log p_i
- H ≤ −∑ p_i log p_i  (given letter frequencies p_i)

## Significance
The multinomial / method-of-types count is how entropy first appears as a growth rate of sequence counts — parallel to Appendix 1’s growth rate of channel signals.

## Connects To
- Sec 6–7: maxent and relative entropy.
- Sec 9: method 2 (Shannon–Fano) uses the p_i directly.
