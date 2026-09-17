# Chapter 24: Exact Marginalization

## Core Idea
Marginalization — summing or integrating out nuisance variables — is the computational heart of Bayesian inference. When the joint factorizes, you can push sums inside products and eliminate variables one at a time (variable elimination) instead of enumerating the full table (Ch 21). Complexity follows the factor graph’s width, not the raw number of variables.

## Frameworks Introduced
- **Variable elimination**: pick an order; for each variable, multiply all factors that mention it, sum it out, replace them by the resulting factor.
- **Factor graphs**: bipartite graph of variables vs factors; visualization of what can be eliminated locally.
- **The distributive law**: sum_b f(a,b) g(b,c) = message(a,c) — same as Ch 16’s path counting with probabilities.

## Key Concepts
- **Nuisance parameters**: variables you do not care to report but must integrate because uncertainty in them affects the answer.
- **Treewidth**: the bottleneck clique size of the best elimination order. Exact inference is exponential in treewidth, polynomial in n for fixed treewidth.
- **Sum vs max**: the same elimination with max instead of sum is MAP (Viterbi on graphs).
- **Numerical stability**: work in log-space; normalize messages as you go.

## Key Equations
- P(x) = sum_{z} P(x,z)
- If P(a,b,c)=f(a,b) g(b,c), then P(a,c)= g̃(a,c) with g̃(a,c)=sum_b f(a,b)g(b,c)
- Elimination cost ~ |A|^{w+1} per step if factors become size w+1
- P(evidence) = Z after all unobserved / unqueried vars eliminated

## Algorithms and Techniques
**Variable elimination**
1. Write the joint as a product of small factors (CPTs, likelihoods).
2. Choose an elimination order (min-fill / min-degree heuristics).
3. For variable v: F ← product of all factors including v; F' ← sum_v F; replace those factors by F'.
4. Remaining factor on the query variables is the (unnormalized) marginal.

**When to stop trying exact**
- If the largest intermediate factor has > ~20 binary variables, switch to MCMC (Ch 29) or variational (Ch 33) or loopy BP (Ch 26).

## Mental Models
- Enumeration is elimination with the worst order (one giant factor).
- Think “push sums through products as far as possible”.
- Trees are easy (Ch 16, 26); grids are hard (Ising, Ch 31) because treewidth ~ min(width,height).

## Worked Example
Burglar net: P(b,e,a,p,r)=P(b)P(e)P(a|b,e)P(p|a)P(r|e). Query P(b|p=1).
- Clamp p=1 in P(p|a).
- Eliminate r: sum_r P(r|e)=1, factor disappears (unless r observed).
- Eliminate a: sum_a P(a|b,e) P(p=1|a) produces T(b,e).
- Eliminate e: sum_e P(e) T(b,e) produces T'(b).
- Multiply P(b) T'(b) and normalize. Same answer as 32-row enumeration, fewer multiplications, and the pattern scales.

## Anti-patterns
- **Eliminating high-degree variables first** without a heuristic — huge intermediate tables.
- **Summing in probability space** with tiny numbers → underflow. Use logs.
- **Forgetting to clamp evidence** before eliminating.
- **Exact inference on a densely connected Bayes net with 50 nodes**.

## Key Takeaways
1. Marginalization is the operation; elimination is the algorithm.
2. Cost is exponential in treewidth, not in n.
3. The distributive law is message passing.
4. If treewidth is large, approximation is mandatory.
5. Always check against enumeration on a tiny instance.

## Connects To
- **Ch 16**: messages on chains.
- **Ch 21**: enumeration as the brute-force baseline.
- **Ch 25**: elimination on trellises (HMM / convolutional codes).
- **Ch 26**: sum–product on trees; loops.
- **Ch 31**: grids where exact elimination is exponential.
