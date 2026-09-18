# Chapter 2: Probability, Entropy, and Inference

## Core Idea
Information theory is probability theory with a logarithm: define an ensemble, write joint/marginal/conditional probabilities, then entropy, conditional entropy, and mutual information measure uncertainty and the value of data. Inverse probability (Bayes) is the same calculus run backwards from observations to hypotheses.

## Frameworks Introduced
- **Ensemble X = (x, AX, PX)**: outcome x, alphabet AX = {a1..aI}, probabilities PX with pi ≥ 0, sum pi = 1.
  - When to use: any discrete uncertainty. MacKay prefers “ensemble” over “random variable” when the alphabet and measure matter.
- **Forward vs inverse probability**
  - Forward: known process → P(data | hypothesis). Easy, generative.
  - Inverse: data in, infer hypothesis via Bayes. This is inference.
- **Product rule / Bayes**
  - P(x,y) = P(x) P(y|x) = P(y) P(x|y)
  - P(H|D) = P(D|H) P(H) / P(D)
- **Entropy calculus**: H(X), H(X|Y), I(X;Y), chain rule, decomposability.

## Key Concepts
- **Joint ensemble XY**: ordered pairs (x,y); P(x,y). Marginal P(x) = sum_y P(x,y).
- **Conditional P(x|y)**: P(x,y)/P(y) when P(y)≠0; undefined otherwise.
- **Independence**: P(x,y)=P(x)P(y) ⇔ P(x|y)=P(x).
- **Shannon information content**: h(x) = log2 1/P(x)  (nats if ln).
- **Entropy**: H(X) = sum_i pi log2 1/pi = E[h(x)].
- **Conditional entropy**: H(X|Y) = sum_y P(y) H(X|Y=y) = H(X,Y)−H(Y).
- **Mutual information**: I(X;Y) = H(X)−H(X|Y) = H(Y)−H(Y|X) = H(X)+H(Y)−H(X,Y).
- **Kullback–Leibler divergence**: DKL(P||Q) = sum p log(p/q) ≥ 0, =0 iff P=Q (Gibbs).
- **Degrees of belief**: MacKay treats probabilities as degrees of belief consistent with Cox/Ramsey, not merely frequencies — but frequencies are the calibration.

## Key Equations
- P(x) = sum_y P(x,y)  -- marginalization
- P(x|y) = P(x,y)/P(y)
- H(X) = −sum p(x) log2 p(x)
- H(X,Y) = H(X) + H(Y|X)  -- chain rule
- I(X;Y) = DKL( P(x,y) || P(x)P(y) )
- Gibbs: DKL(P||Q) ≥ 0
- Jensen: for convex f, f(E[x]) ≤ E[f(x)]
- Binary entropy: H2(p) = H(p, 1−p)

## Algorithms and Techniques
**From a joint table to information quantities**
1. Write P(x,y) as a matrix over AX × AY (English bigrams in the chapter).
2. Row-normalize → P(y|x); column-normalize → P(x|y).
3. Sum rows/columns → marginals.
4. Compute H(X), H(Y), H(X,Y), then I(X;Y)=H(X)+H(Y)−H(X,Y).

**Inverse probability (Bayes update)**
1. Specify prior P(H) and likelihood P(D|H).
2. Evidence P(D) = sum_H P(D|H)P(H).
3. Posterior P(H|D) ∝ likelihood × prior.
4. Predictions: P(D'|D) = sum_H P(D'|H) P(H|D).

## Mental Models
- Use **forward probability** when you can simulate the data generator; use **inverse probability** when you must guess the generator from data.
- Think of H(X|Y) as leftover uncertainty after seeing Y; I(X;Y) as the bits Y tells you about X.
- Think of DKL(P||Q) as extra nats you pay for encoding P-data with a Q-code (Ch 4–6).
- White Knight warning: distinguish the RV, its value, and the proposition “RV = value”. Then relax notation.

## Worked Example
English letters (27-ary, including space). From MacKay’s monogram table, vowels V={a,e,i,o,u} have P(V)≈0.31. Joint bigrams XY of successive letters have identical marginals P(x)=P(y)=monogram. Conditional P(y|x=q) is peaked on u (and space): seeing ‘q’ collapses uncertainty about the next character. Mutual information I(X;Y) is the average number of bits the previous letter saves when predicting the next — the source of *dependency* that symbol codes (Ch 5) and stream codes (Ch 6) exploit if they model context.

A bent coin with unknown bias f: forward model P(r|f,N) is binomial. Inverse problem: infer f from r heads in N tosses (developed in Ch 3). Do not confuse P(data|f) with P(f|data).

## Anti-patterns
- **Using P(H|D) and P(D|H) interchangeably** (“prosecutor’s fallacy”).
- **Conditioning on measure-zero events** without a limiting process.
- **Assuming I(X;Y)=0 from uncorrelatedness**: uncorrelated ≠ independent except for Gaussians.
- **Maximizing likelihood and calling it Bayesian**: ML is the posterior mode only for flat priors, and even then discards posterior width (Ch 22, 28).
- **Entropy of a single outcome**: h(x) is information content of an outcome; H(X) is the average. Do not say “the entropy of this message is …”.

## Key Takeaways
1. Write the joint; everything else is a marginal or a conditional.
2. Entropy is expected Shannon information content, in bits if log2.
3. Mutual information is reduction in entropy, and is a KL between joint and product of marginals.
4. Inference *is* inverse probability; keep likelihoods and priors explicit.
5. Gibbs and Jensen are the two inequalities you will reuse for typicality, EM, and variational methods.

## Connects To
- **Ch 3**: Bayesian model comparison, bent-coin worked example.
- **Ch 4**: entropy as the compression limit (AEP / typicality).
- **Ch 8**: dependent variables, I(X;Y) for channels.
- **Ch 22–28**: ML vs Bayesian clustering and Occam factors.
