# Chapter 21: Exact Inference by Complete Enumeration

## Core Idea
If the hypothesis space is small, do not approximate: write the joint, enumerate, and sum. Pearl’s burglar-alarm network is the canonical belief-network example — explaining-away is just Bayes on a 32-row table. Exact enumeration is the gold standard that later algorithms (trellis, junction tree, MCMC) must match.

## Frameworks Introduced
- **Belief network (Bayes net)**: a DAG factorizing P(z) = ∏_i P(z_i | parents(i)).
- **Complete enumeration**: list all 2^n (or |A|^n) configurations, weight by the joint, sum out nuisances.
- **Explaining away**: when two causes can produce one effect, observing the effect makes them *dependent*; observing one cause lowers P(the other | effect).

## Key Concepts
- **Burglar-alarm variables**: b burglar, e earthquake, a alarm, p phonecall, r radio. Factorization:
  P(b,e,a,p,r)=P(b)P(e)P(a|b,e)P(p|a)P(r|e)
- **Base rates**: β=P(b=1)=0.001, ε=P(e=1)=0.001 — without them the alarm story is meaningless.
- **Evidence**: phonecall raises P(b|p); then radio report of earthquake *lowers* P(b|p,r) (explaining away).
- **Complexity**: exact enumeration is O(|states|); already hopeless at n≈30 binary latents.

## Key Equations
- P(b,e,a,p,r)=P(b)P(e)P(a|b,e)P(p|a)P(r|e)
- P(b=1)=β, P(e=1)=ε
- P(a=1|b,e) ≈ 1 − (1−α_b)^b (1−α_e)^e (1−α_false)  (noisy-or style)
- P(b | p=1) = sum_{e,a,r} P(b,e,a,p=1,r) / P(p=1)
- Explaining away: P(b=1 | p=1, r=1) < P(b=1 | p=1)

## Algorithms and Techniques
**Enumerate a tiny Bayes net**
1. Write every variable’s CPT.
2. For each full assignment, compute the product of CPTs.
3. Zero out rows inconsistent with observed evidence.
4. Normalize remaining mass; sum columns to get any marginal.
5. Check explaining-away by comparing P(cause1 | effect) vs P(cause1 | effect, cause2).

## Mental Models
- If you can enumerate, you should — it debugs your model before you trust MCMC.
- Explaining away is not a special rule; it is dependence induced by conditioning on a common effect (Berkson’s collider).
- Use noisy-or for alarms with several rare causes.

## Worked Example
Fred’s alarm. Neighbour calls (p=1). Without earthquake info, P(b=1|p=1) is much larger than 0.001 (alarm is unlikely unless b or e). Then radio says earthquake (r=1), which makes e probable, which already explains a, so b’s posterior falls toward its tiny base rate. MacKay’s numbers (α_b=0.99, etc.) make this numerically vivid: the earthquake “explains away” the burglar.

If you incorrectly assumed b ⟂ e | a, you would miss this entirely. The collider a *opens* dependence.

## Anti-patterns
- **Ignoring base rates** (Ch 3 legal example again).
- **Using enumeration for n>20 binary latents**.
- **Assuming causes stay independent after observing the effect**.
- **Forgetting to normalize after zeroing impossible rows**.

## Key Takeaways
1. Exact inference = sum the joint. Start here.
2. Bayes nets are just factorizations; the DAG tells you which sums are allowed to factor.
3. Explaining away is collider conditioning.
4. Enumeration does not scale; it calibrates scalable algorithms.
5. Always plug in the actual tiny probabilities.

## Connects To
- **Ch 3**: base rates, Bayes.
- **Ch 24–26**: smarter exact summation (variable elimination, trellises, trees).
- **Ch 29**: MCMC when enumeration dies.
- **Ch 36**: decisions after you have P(burglar|data).
