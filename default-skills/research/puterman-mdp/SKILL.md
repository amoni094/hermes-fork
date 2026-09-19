---
name: puterman-mdp
description: "Use when designing agent MDPs, value iteration, or policies."
related_skills:
  - astrom-murray-feedback
  - ralph-loops
  - autonomous-agent-loop-design
  - agent-runtime-loop-patterns
---

# Puterman — Markov Decision Processes

Martin L. Puterman, *Markov Decision Processes: Discrete Stochastic Dynamic Programming* (Wiley, 1994; Wiley-Interscience reprint 2005, ISBN 0-471-72782-2). Knowledge base for agent decision loops, reward shaping, value/policy iteration, and sequential decisions under uncertainty. Source PDF is a 666-page scan (no text layer).

One thesis: **a sequential decision problem is an MDP when the future is independent of the past given the present state and action.** Then an optimal policy exists in a small class (deterministic Markov; stationary when the horizon is infinite and the criterion is discounted), and it is characterized by Bellman optimality equations that can be solved by backward induction, value iteration, policy iteration, modified policy iteration, or LP.

Puterman writes the discount factor as **λ ∈ [0, 1)**. RL literature uses γ for the same object. This skill uses λ for Puterman's results and γ when talking to agent/RL code.


## Model Routing

Algorithm derivation (value iteration, policy iteration, LP formulation): magistral-small-latest (mistral). Implementation + test: grok-4.6 workers via delegate_task — MDP tasks always have a coding tail.


## MDP formalism (Ch 2)

Five objects, plus a policy:

| Object | Puterman | Meaning |
|--------|----------|--------|
| Decision epochs | *T* | Discrete times at which a decision is required. Finite horizon: *T* = {1,…,*N*}. Infinite: *T* = {1, 2, …}. |
| States | *S* | All information needed so that *P*(next, reward ∣ history) = *P*(next, reward ∣ current state, action). |
| Actions | *A_s* | Feasible choices in *s*. |
| Rewards | *r_t(s,a)* or *r(s,a)* | Immediate expected return. May depend on the next state: *r_t(s,a,j)*. |
| Transitions | *p_t(j ∣ s,a)* | *P*(X_{t+1}=j ∣ X_t=s, Y_t=a). Time-homogeneous when *p* does not depend on *t*. |

**Decision rule** *d_t* maps (history or state) → action (or a distribution over actions).

**Policy** π = (*d_1*, *d_2*, …) is a sequence of decision rules.

Classes, nested:

```
history-dependent randomized  ⊃  history-dependent deterministic
        ⊊                              ⊊
Markov randomized             ⊃  Markov deterministic
        ⊊                              ⊊
stationary randomized         ⊃  stationary deterministic
```

A Markov decision rule depends on the current state only, not on the path that reached it. A stationary policy uses the same Markov rule at every epoch.

**Markov property (design invariant):** if the coded "state" is incomplete, the process the agent is solving is not an MDP in those variables. Then history-dependent rules can strictly beat Markov rules. Fix: encode the missing information into the state (belief, remaining horizon, inventory, time index), do not let the decision function take unbounded raw history.

## Finite vs infinite horizon

**Finite horizon (Ch 4).** Value functions are time-indexed. An optimal policy is deterministic Markov and generally *non-stationary* — *d_t* depends on periods remaining. Solve by **backward induction** (Puterman 4.5):

```
u_{N+1}(s) = r_{N+1}(s)                         # terminal reward
for t = N, N-1, …, 1:
    u_t(s) = max_a [ r_t(s,a) + Σ_j p_t(j|s,a) u_{t+1}(j) ]
    A*_t(s) = argmax of the same
return any π* with d*_t(s) ∈ A*_t(s)
```

This *is* Bellman's principle of optimality: an optimal tail from *t* onward depends only on *s* at *t*, not on how *s* was reached (4.3–4.4).

**Infinite horizon (Ch 5–6).** Time-homogeneous data + discounting ⇒ a **stationary** deterministic optimal policy exists (under standard bounded-reward / finite *S*×*A* assumptions). Mixing the two is a defect: a stationary policy on a genuine finite-horizon problem (remaining time is payoff-relevant and not in the state) is not justified.

## Discounting (Ch 5.3, Ch 6)

Expected total discounted reward of π from *s*:

```
v_λ^π(s) = E_s^π [ Σ_{t=1}^∞  λ^{t-1} r(X_t, Y_t) ]
```

- **λ < 1** (equivalently γ < 1): the criterion is well-defined for bounded rewards; the Bellman operator is a contraction of modulus λ on (B, ‖·‖_∞); unique bounded solution to the optimality equation; value iteration converges geometrically.
- **λ = 1** (undiscounted total reward, Ch 7): not a contraction. Split into **positive bounded** (rewards ≥ 0) and **negative** (rewards ≤ 0) models. Value iteration / policy iteration need extra hypotheses; existence of optimal policies can fail.
- **Average reward** (Ch 8–9): long-run gain *g*; optimality equation involves gain + bias, not a discounted *v*. Unichain vs multichain changes the algorithm (one gain vs a gain vector).

If the coded loop has γ ≥ 1 and you expect contraction-style convergence, the theory does not give it.

## Bellman equations and optimality (Ch 4.3, Ch 6.2)

**Discounted infinite horizon, finite *S*, *A*.** Let

```
(T_d v)(s) = r(s, d(s)) + λ Σ_j p(j|s, d(s)) v(j)
(T v)(s)   = max_{a ∈ A_s} [ r(s,a) + λ Σ_j p(j|s,a) v(j) ]
```

Facts (6.2):

1. *T* is a contraction of modulus λ: ‖Tv − Tw‖_∞ ≤ λ ‖v − w‖_∞.
2. Unique bounded fixed point *v** = *T v** = sup_π *v_λ^π*.
3. *v** is the optimal value. A deterministic stationary *d** is optimal iff *T_{d*} v** = *T v** (it attains the max in every state).
4. History does not appear on the right-hand side. Value of a state = immediate reward + discounted expected future value.

**Certificate of optimality:** a claimed (*v*, *d*) is optimal iff *v* = *T v* and *d* attains the max. Scoring above a threshold is not this certificate.

## Value iteration (Ch 6.3, 6.6)

```
v^{0} arbitrary bounded
v^{n+1} = T v^n
```

- ‖v^{n} − v*‖_∞ ≤ λ^n ‖v^{0} − v*‖_∞ — geometric, rate λ.
- Stopping via span seminorm / bounds (6.6), not an arbitrary iteration cap.
- Relative value iteration and action elimination (6.6–6.7) speed this up; they do not change the fixed point.
- **Oscillation / non-convergence:** typical when λ ≥ 1, or average-reward VI without aperiodicity (8.5.4 aperiodicity transform). Do not "tune step size" on a Bellman backup; there is no step size.

## Policy iteration (Ch 6.4)

```
1. Evaluate: solve v^n = r_{d^n} + λ P_{d^n} v^n     # linear system
2. Improve:  d^{n+1}(s) ∈ argmax_a [ r(s,a) + λ Σ_j p(j|s,a) v^n(j) ]
             keep d^n(s) if it remains greedy
3. Stop when d^{n+1} = d^n
```

For **finite** *S* and *A*, there are finitely many deterministic stationary policies; each improvement is a strict increase until optimum; **PI terminates at an optimal stationary policy in finitely many steps** (6.4.2). That is stronger than VI's asymptotic convergence.

**Modified policy iteration** (6.5): *m* partial evaluation backups between improvements. Recovers VI at *m*=0 and PI as *m*→∞.

**When a loop does not converge, distinguish:**

| Algorithm | Finite MDP, λ < 1 | λ ≥ 1 or average reward |
|-----------|-------------------|-------------------------|
| Value iteration | Geometric → *v**; may look like it "moves forever" if ε is tiny | May oscillate; need positivity/negativity, unichain, aperiodicity |
| Policy iteration | Finite termination at π* | Finite-ish under unichain + extra conditions; multichain needs the Ch 9 algorithm |

## Structured / monotone policies (Ch 4.7, 6.11)

If rewards and transitions are stochastically monotone and the reward is superadditive in (*s*, *a*), an optimal policy is monotone in the state. Do not search the full *A^S* when the model has this structure — restrict to monotone decision rules.

## Continuous time (Ch 11)

Semi-Markov and continuous-time MDPs reduce, after embedding / uniformization, to a discrete-time discounted or average-reward MDP. Same Bellman shape; rates replace probabilities.

## Optimal Stopping: Ask-vs-Act Decision Rule (Ch 3, Optimal Stopping)

A stopping rule for finite-horizon MDPs (Puterman Ch 3): at each epoch, stop (act now) iff the immediate reward of stopping ≥ expected future value of continuing. Applied to clarification decisions:

**Ask-vs-Act rule:**
1. Count plausible interpretations of the current task from context (1–5 range).
2. If ≤ 2 plausible interpretations AND the last user message resolves one of them → **act** (optimal stopping: continuation value is negative).
3. If ≥ 3 plausible interpretations remain after re-reading all available context → **ask exactly one** question that covers all remaining ambiguities (do not ask multiple questions).
4. If the task is irreversible (file deletion, external POST, email send) → **always ask** regardless of interpretation count — stopping reward asymmetry: wrong-action cost dominates continuation cost.

**Information value estimate (Ch 3.3):** The value of one clarifying question ≈ P(wrong_interpretation) × rework_cost − delay_cost_of_one_round. When P(wrong) < 0.25 AND rework_cost is low (edit a file, re-run a command), act without asking — the continuation value is negative. When rework_cost is high (irreversible, multi-file, externally visible), the stopping threshold lowers: ask even at P(wrong) ≈ 0.15.

**Anti-pattern to avoid:** asking for clarification on every non-trivial task (infinite-horizon framing — continuation is always available). The Markov property says: given the current state (context so far), act optimally NOW; past exchanges that were already sufficient should not be re-opened.

## Agent-loop translations

1. **State, not history.** Decision code must be a function of an explicit state sufficient for the Markov property. Unbounded conversation/trace as the decision key violates Ch 2/4.4; encode what matters (goal, constraints, remaining budget/horizon, last observation) into a finite or structured state.
2. **Horizon type is a type error if mixed.** Finite-horizon ⇒ time-indexed *v_t*, non-stationary *d_t*. Infinite discounted ⇒ one *v*, stationary *d*. Putting remaining-time into the state converts finite horizon into a stationary problem on an augmented state.
3. **γ < 1 is a convergence assumption, not a style choice.** If γ ≥ 1, do not debug "why VI oscillates" as a coding bug until the criterion is well-posed (Ch 7–8).
4. **Rewards define the objective.** Changing *r* changes *v** and usually π*. Potential-based shaping *F(s,a,s') = γ Φ(s') − Φ(s)* (Ng, Harada, Russell 1999) is the standard condition that *preserves* π*; Puterman does not discuss shaping, but his optimality equation makes the failure mode obvious: a non-potential bonus is a different MDP.
5. **Tests should check Bellman residuals.** For a reported (*v*, π), assert *v ≈ T v* and that π is greedy w.r.t. *v*. A return threshold is not an optimality certificate (6.2.4).

## Bellman-Residual Stopping Rule for Agent Planning Loops (Ch 6.3, 6.6)

When an agent iterates over candidate plans/actions (rescoring, belief updating, policy refinement), use the **span seminorm** as the convergence criterion rather than an iteration cap or a 'nothing changed' heuristic:

**Convergence rule:**
```
span_n = max(improvements[n]) - min(improvements[n])
if span_n < 0.05 * abs(mean(improvements[0])):  # 5% relative span threshold
    stop("Bellman span criterion met — policy stable")
```

**Divergence check (Ch 6.3):** if the ratio ‖v^{n+1} − v^n‖ / ‖v^n − v^{n-1}‖ > 1.0 over 2 consecutive pairs, the value iteration is diverging. Log: 'Discount must be < 1 or reward model is inconsistent — halting'. Do NOT continue iterating.

**Practical mapping for agent loops:**
- v^n = current ranking/score of candidate options after n rounds of refinement
- span = (best_score_gain − worst_score_gain) across all options in round n
- Stop when span < 5% of initial score range, or after a hard cap of 10 iterations
- Never stop because ONE option's score stopped changing (that is `min(improvements)`, not `span`)

**Why span not max:** max(improvements) can stop because one action's value converged while others still move — the policy may not be optimal. Span = 0 iff ALL actions have equal Bellman residual, i.e., the policy IS greedy w.r.t. the current value (Puterman 6.6 span seminorm stopping criterion).

## Chapter index

| Ch | Title | Use when |
|----|-------|----------|
| 1 | Introduction | Sequential decision examples |
| 2 | Model formulation | States, actions, *p*, *r*, policies |
| 3 | Examples | Inventory, stopping, bandits, queues |
| 4 | Finite-horizon MDPs | Backward induction, time-indexed *v_t* |
| 5 | Infinite-horizon foundations | Criteria, discounting, Markov policies |
| 6 | Discounted MDPs | VI, PI, MPI, LP, span bounds |
| 7 | Expected total reward | λ=1, positive vs negative models |
| 8 | Average reward (unichain) | Gain, bias, relative VI |
| 9 | Average reward (multichain) | Multiple recurrent classes |
| 10 | Sensitive discount optimality | Blackwell / *n*-discount |
| 11 | Continuous-time models | SMDP, CTMDP |
| App A–D | Markov chains, LP | Classification, Laurent series |

## Value-of-Information Stopping Rule (Puterman Ch 3)

Before asking a clarifying question, estimate: (1) uncertainty cost if acting now, (2) information gain from the question, (3) delay cost of asking. Ask iff (information_gain * rework_cost) > delay_cost. Concrete: if task has <=2 plausible interpretations AND user last message resolves one, act without asking. If >=3 interpretations remain, ask exactly one disambiguating question.

## Bellman-Residual Stopping Criterion (Puterman Ch 6.3)

Use span seminorm as convergence criterion for iterative agent planning: stop when max_improvement - min_improvement < 0.05 relative. If improvement ratio across iterations exceeds 1.0 (diverging), log MDP criterion violated: discount must be < 1 and halt.
