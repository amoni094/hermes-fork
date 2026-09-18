# Chapter 37: Bayesian Inference and Sampling Theory

## Core Idea
Sampling theory guarantees long-run error rates of procedures (p-values, confidence intervals) under a null. Bayes answers P(hypothesis | this dataset). They can agree, but p-values are not posterior probabilities; they can reject a null the data actually support, miss evidence Bayes and intuition call strong, and change when you alter an irrelevant stopping rule.

## Key Concepts
- **p-value**: P(data as or more extreme than observed | H_0). Not P(H_0|data).
- **Null-hypothesis significance test**: specify H_0 and H_1 then *ignore H_1* except as a source of a statistic; reject H_0 if the statistic is surprising under H_0.
- **χ² test / Yates correction**: textbook machinery MacKay mocks as arbitrary; used in the vaccination example.
- **Confidence interval**: a random set with advertised coverage P(set ∋ θ | θ) = 95%. Not “95% probability that θ is in this interval” unless you are Bayesian with a matching prior.
- **Stopping rules / optional stopping**: sampling-theory significance depends on why you stopped; the likelihood principle says only the observed likelihood matters.
- **MacKay’s advice**: if the debate is hard, skip it and use Bayes — it is easier and answers the question you asked.

## Frameworks and Methods
- **Medical example (microsoftus)**: 30 on vaccine A (1 ill), 10 on placebo B (3 ill). Intuition: A looks better. χ² vs H_0: “equal rates” may or may not hit p<0.05 depending on exact test and design. Bayes compares P(data | p_A, p_B) with priors (independent Beta, or p_A=p_B) and can report P(p_A < p_B | data).
- **Trigger-happy tests**: Ch 3 exercises already showed p<0.05 while the Bayes factor favours H_0.
- **Under-sensitive tests**: designs where sampling theory calls the result “not significant” while the likelihood ratio is large.
- **Irrelevant information**: two experiments with the same likelihood but different sample-space stories get different p-values (binomial vs negative binomial stopping).
- **Compromises**: MacKay notes attempts (empirical Bayes, matching priors) but does not treat them as a reason to prefer p-values.

## Key Equations
- p = P(T(X) ≥ T(x_obs) | H_0)
- χ² = ∑ (F_i − ⟨F_i⟩)² / ⟨F_i⟩   (Yates: (|F_i−⟨F_i⟩|−0.5)² / ⟨F_i⟩)
- Bayes: P(H|D) ∝ P(D|H) P(H)
- Bayes factor B_{01} = P(D|H_0)/P(D|H_1)
- Likelihood principle: if P(D|θ) ∝ P(D'|θ) as functions of θ, inference about θ should match
- Coverage: P_θ(θ ∈ C(X)) = 1−α  vs  posterior P(θ ∈ C | x)

## Algorithms and Techniques
**Do the Bayesian analysis MacKay wants**
1. Write the sampling model both schools agree on (e.g. binomial counts).
2. Put priors on the parameters of H_0 and H_1 (or a single model with p_A, p_B).
3. Report posterior probabilities or a Bayes factor, and posterior of the effect.
4. Optionally compute the p-value to see how it misleads.

**When reading a paper that only gives p**
1. Do not translate p=0.05 into “5% chance the null is true”.
2. Ask what statistic, what stopping rule, what H_1.
3. If you have the counts, reanalyse with a Beta-binomial / Gaussian model.

## Anti-patterns
- **Interpreting p as a posterior**.
- **Accept/reject H_0 without ever scoring H_1 on the data**.
- **Changing significance by changing an unused stopping intention**.
- **Building confidence intervals around an estimator with huge variance** (Luria–Delbrück, Ch 35) and calling that “guaranteed”.

## Key Takeaways
1. p-values are tail probabilities under H_0, not beliefs about H_0.
2. Tests can be both too trigger-happy and too deaf, relative to Bayes.
3. If two experiments share a likelihood, they should share the inference.
4. Confidence is coverage of a procedure; posterior probability is about this θ.
5. Use Bayesian methods; this chapter exists for the curious, not as a prerequisite.

## Connects To
- **Ch 3**: bent coin, legal evidence, p vs Bayes factor.
- **Ch 28**: Occam factors — sampling theory has no natural model comparison.
- **Ch 35**: Luria–Delbrück estimators.
- **Ch 36**: decisions need P(x|data), not a reject/accept bit.
