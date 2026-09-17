---
name: shoham-multiagent-systems
category: research
description: Use when designing multi-agent coordination and games.
trigger: multi-agent coordination, game theory, Nash equilibrium, mechanism design, inspection game, adversarial agents, incentive compatibility
author: subagent (wiring sprint 2, 2026-09-16)
source: Shoham and Leyton-Brown — Multiagent Systems 2009
---

# Shoham & Leyton-Brown — Multiagent Systems

Algorithmic, Game-Theoretic, and Logical Foundations.
Cambridge University Press, 2009. Free PDF: http://www.masfoundations.org

Load this skill when: designing multi-agent Hermes coordination, choosing tool-authorisation inspection-game parameters, evaluating skill routing incentive compatibility, or reasoning about agent learning dynamics.

---

## Core Frameworks

### Nash Equilibrium (Ch 3)
A strategy profile s = (s₁,...,sn) is a **Nash equilibrium** if for all agents i, sᵢ is a best response to s₋ᵢ.
- No player can unilaterally improve by deviating.
- **Nash's theorem**: every finite game has at least one Nash equilibrium (possibly mixed-strategy).
- Mixed-strategy NE always exists; pure-strategy NE may not.
- Strict NE: every agent's strategy is the *unique* best response.
- Weak NE: at least one agent has a non-unique best response (all mixed-strategy NE are weak).

### Dominant Strategy
A strategy sᵢ is **dominant** if it is a best response regardless of what other players do.
- Strictly dominant: strictly better than any other strategy for all opponent strategies.
- If a dominant strategy exists, rational agents will always play it (no coordination needed).
- In Prisoner's Dilemma, Defect is strictly dominant for both players → equilibrium is Pareto-suboptimal.

### Maxmin / Minmax (Ch 3)
- **Maxmin strategy** for player i: maximise worst-case payoff = arg maxₛᵢ minₛ₋ᵢ uᵢ(sᵢ, s₋ᵢ)
- **Minimax theorem (von Neumann, 1928)**: in any finite two-player zero-sum game, maxₛ₁ minₛ₂ u₁ = minₛ₂ maxₛ₁ u₁.
- In two-player zero-sum games: maxmin value = minmax value = Nash equilibrium value.

### Pareto Optimality
- Strategy profile s **Pareto dominates** s' if all agents weakly prefer s and at least one strictly prefers it.
- **Pareto optimal**: no profile Pareto dominates it.
- NE can be Pareto suboptimal (classic: Prisoner's Dilemma).

### Correlated Equilibrium (Ch 3)
- A probability distribution over action profiles such that, given the recommended action, no agent benefits from deviating.
- Weaker than NE (every NE induces a correlated equilibrium).
- No-regret learning converges to correlated equilibria.

---

## Mechanism Design & Revelation Principle (Ch 10)

See: [ch07-mechanism-design.md](references/ch07-mechanism-design.md) for full detail.

### Core definitions
- **Mechanism**: a game form (action sets + outcome function) designed by a principal.
- **Direct revelation mechanism**: agents report their types directly; mechanism maps reports to outcomes.
- **Truthful / Incentive-compatible (IC)**: truth-telling is a dominant strategy for every agent.
- **Revelation principle**: any mechanism implementable in Bayes-Nash equilibrium can be replaced by an equivalent truthful direct revelation mechanism. Never build an indirect mechanism when a direct one suffices.

### Groves mechanisms (Ch 10.4)
- Family of efficient, dominant-strategy truthful mechanisms in quasilinear settings.
- Choice: x(v̂) = arg maxₓ Σᵢ v̂ᵢ(x) — maximise declared social welfare.
- Payment to agent i: ℘ᵢ(v̂) = hᵢ(v̂₋ᵢ) − Σⱼ≠ᵢ v̂ⱼ(x(v̂)) — agent internalises others' externalities.
- **VCG mechanism**: special case of Groves; used in combinatorial auctions.
- Green-Laffont theorem: Groves is the *only* dominant-strategy efficient mechanism for agents with unrestricted quasilinear utilities.

### Arrow's impossibility / Muller-Satterthwaite
- No social welfare function can simultaneously satisfy Pareto efficiency, IIA, and non-dictatorship (Arrow, 1951).
- No weakly Pareto efficient, monotonic social choice function is non-dictatorial (Muller-Satterthwaite, 1977).

---

## Inspection Game (Ch 6 / adversarial agents)

See: [ch06-adversarial-agents.md](references/ch06-adversarial-agents.md) for full detail.

**Setup**: Inspector decides whether to audit (cost c > 0); inspectee decides whether to comply or violate (benefit b if undetected).

**Optimal mixed strategy for inspector**:
```
p* = b / (b + c)   # probability of inspecting
```
Where b = benefit to inspectee of violation, c = audit cost to inspector.

- At p*, inspectee is indifferent → plays mixed strategy.
- Key insight: increasing audit cost c *reduces* optimal inspection rate p*.
- **Hermes application**: tool-auth-shim.py uses this for LLM tool authorisation — set audit frequency proportional to tool risk / benefit ratio.

---

## Multi-Agent Learning (Ch 7)

See: [ch06-adversarial-agents.md](references/ch06-adversarial-agents.md) for learning section.

### Fictitious play
- Each agent best-responds to the empirical frequency of opponents' past play.
- Converges to NE in two-player zero-sum games and some coordination games.
- Does NOT generally converge in arbitrary games.

### Reinforcement learning in multiagent settings
- Single-agent RL (Q-learning) does not converge to NE in general multiagent settings.
- Joint action learners (JAL): maintain model of other agents' strategies; computationally expensive.
- Independent learners (IL): no explicit model of others; fast but may not converge.
- Minimax-Q: optimal in two-player zero-sum stochastic games.

### No-regret learning / Hannan consistency
- A learning rule is **universally consistent** (no-regret) if average payoff ≥ payoff from any fixed pure strategy in hindsight.
- Regret-matching converges to correlated equilibria in self-play.
- **Hermes application**: skill routing can be framed as no-regret — regret = best-skill-in-hindsight minus skill-used payoff.

### Evolutionary learning / replicator dynamics
- Replicator dynamic: proportion playing strategy s grows proportionally to excess payoff above mean.
- Evolutionarily stable strategies (ESS): fixed points robust to invasion.

---

## Repeated Games and Folk Theorem (Ch 6.1)

- In infinitely repeated games with sufficiently patient players (discount factor δ close to 1), any feasible individually-rational payoff can be sustained as a NE (Folk theorem).
- Enables cooperation where single-shot NE is Pareto-suboptimal.
- **Hermes application**: long-running cron agent relationships can sustain cooperative norms that single-shot reasoning would not.

---

## Hermes Applications

| Framework | Hermes component | Notes |
|-----------|-----------------|-------|
| Inspection game (p* = b/(b+c)) | tool-auth-shim.py | Set audit rate by tool risk/cost ratio |
| Mechanism design / IC | Skill routing incentives | Skill descriptions should elicit truthful routing signals |
| Dominant strategy | Cron job design | Give each cron job a dominant action (run/skip) with no ambiguity |
| No-regret learning | Skill selection feedback loop | Regret = best-skill-in-hindsight minus skill-used payoff |
| Revelation principle | Agent self-reporting | Design to make truthful reporting a dominant strategy |
| Nash equilibrium | Multi-agent task allocation | Stable allocation = no agent benefits from unilateral re-assignment |
| Folk theorem | Long-horizon agent norms | Cooperative norms hold under repeated interaction + patient agents |

---

## References

- Chapter files: [ch03-game-theory.md](references/ch03-game-theory.md), [ch06-adversarial-agents.md](references/ch06-adversarial-agents.md), [ch07-mechanism-design.md](references/ch07-mechanism-design.md)
- Quick reference: [cheatsheet.md](references/cheatsheet.md)
- Glossary: [glossary.md](references/glossary.md)
- Book PDF: /var/home/rainbow/Downloads/shoham09a.pdf
- Web: http://www.masfoundations.org
