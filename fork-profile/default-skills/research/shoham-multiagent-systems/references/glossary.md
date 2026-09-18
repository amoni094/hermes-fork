# Shoham & Leyton-Brown — Glossary

**Action-graph game (AGG)**: Compact representation; nodes = actions; payoffs depend on aggregate neighbourhood actions. Exploits anonymity.

**Affine maximiser**: x = arg max_x Σᵢ λᵢ vᵢ(x) + κ(x). Only dominant-strategy implementable mechanisms with unrestricted quasilinear utilities (Roberts, 1979).

**Arrow's impossibility theorem**: No SWF simultaneously satisfying PE, IIA, and non-dictatorship when |O| ≥ 3.

**Bayes-Nash equilibrium (BNE)**: NE where agents best-respond given beliefs about others' private types.

**Best response**: sᵢ* is a best response to s₋ᵢ if uᵢ(sᵢ*, s₋ᵢ) ≥ uᵢ(sᵢ, s₋ᵢ) for all sᵢ.

**Budget balance**: Σᵢ pᵢ = 0. Weak: Σᵢ pᵢ ≥ 0.

**Congestion game**: Players choose resources; payoffs depend on number of players on each resource.

**Correlated equilibrium (CE)**: Distribution over action profiles; following recommendation is a best response. CE ⊇ NE.

**Direct revelation mechanism**: Agents report types; mechanism maps type-reports to outcomes.

**Dominant strategy**: Best response regardless of others' actions.

**Efficiency** (mechanism design): x = arg max_x Σᵢ vᵢ(x).

**ESS (Evolutionarily Stable Strategy)**: NE robust to invasion by small fraction of mutants. ESS ⊆ NE (strictly).

**Fictitious play**: Each agent best-responds to empirical frequency of opponents' past play.

**Folk theorem**: In infinitely repeated games, any feasible individually-rational payoff is a SPE payoff for patient players.

**Gibbard-Satterthwaite theorem**: With ≥3 outcomes and no transfers, any dominant-strategy SCF is dictatorial.

**Graphical game**: Players on a graph; payoffs depend only on direct neighbours.

**Groves mechanism**: Direct quasilinear mechanism; choice maximises declared social welfare; dominant-strategy truthful.

**Hannan consistency**: See no-regret.

**IIA (Independence of Irrelevant Alternatives)**: Social ordering of two outcomes depends only on agents' pairwise orderings of those outcomes.

**Inspection game**: Inspector vs. inspectee. Mixed NE: p* = b/(b+c).

**JAL (Joint Action Learner)**: MAS RL algorithm that models other agents' full joint strategy.

**MAID**: Multiagent influence diagram; combines graphical game + extensive form; exploits strategic relevance.

**Maxmin strategy**: Maximises worst-case payoff. Security level = maxmin value.

**Mechanism design**: Design game rules so agents' equilibrium behaviour produces desired social outcome.

**Minimax theorem**: In finite two-player zero-sum games: max_{s₁} min_{s₂} u₁ = min_{s₂} max_{s₁} u₁.

**Minimax-Q**: Optimal RL for two-player zero-sum stochastic games.

**Mixed strategy**: Probability distribution over pure strategies.

**Nash equilibrium**: Each player's strategy is a best response to others'. Always exists (Nash, 1951).

**No-regret / universally consistent**: Average payoff ≥ any fixed pure strategy in hindsight.

**Normal-form game**: (N, A, u) with simultaneous actions.

**Pareto domination**: s dominates s' if all weakly prefer s and at least one strictly.

**Pareto optimal**: No other profile Pareto dominates it.

**Potential game**: Has potential Φ such that unilateral payoff changes = Φ changes. Pure NE always exists.

**Price of anarchy (PoA)**: Worst-case ratio of optimal social welfare to NE social welfare.

**Quasilinear utility**: uᵢ = vᵢ(x) − pᵢ. Risk neutral, transferable utility.

**Regret-matching**: No-regret algorithm; plays actions proportionally to positive regret. Converges to CE.

**Replicator dynamic**: ṗ(s) = p(s) [u(s,p) − ū(p)]. Fixed points = NE.

**Revelation principle**: Any BNE-implementable mechanism = equivalent truthful direct mechanism.

**Social choice function (SCF)**: Maps preference profiles to a single outcome.

**Social welfare function (SWF)**: Maps preference profiles to a social ordering.

**Subgame-perfect equilibrium (SPE)**: NE in every subgame.

**Support** (mixed strategy): {aᵢ | sᵢ(aᵢ) > 0}.

**Tit-for-Tat**: Cooperate first; copy opponent's last action.

**Truthful mechanism**: Direct mechanism where truth-telling is a dominant strategy.

**VCG**: Groves mechanism with hᵢ(v̂₋ᵢ) = max_x Σ_{j≠i} v̂ⱼ(x). Agent pays externality on others.

**Valuation** vᵢ(x): Maximum agent i would pay for choice x.
