# Chapter 10 — Mechanism Design

Source: Shoham & Leyton-Brown, Multiagent Systems, Ch 10.
(Book Ch 10; file named ch07 per Hermes skill convention.)

---

## 10.1 Introduction

**Mechanism design** = 'reverse game theory': design game rules so rational agents' equilibrium behaviour produces desired social outcome.

- Designer chooses outcome function; agents choose actions strategically.
- Key challenge: agents have **private information** (types θᵢ).
- Goal: elicit truthful information despite strategic behaviour.

## 10.2 Revelation Principle

### Direct revelation mechanism
- Agents report types directly; mechanism maps reports to outcomes.

### Revelation principle (Theorem 10.2.2)
> Any mechanism implementable in Bayes-Nash equilibrium can be replaced by a direct, truthful mechanism yielding the same outcome.

- **Implication**: restrict attention to truthful direct mechanisms without loss of generality.
- **Hermes implication**: design agent self-reports (capability, confidence, context) so truth-telling is dominant.

### Impossibility (Gibbard-Satterthwaite)
- With ≥3 outcomes and no transfers: any dominant-strategy SCF is dictatorial.
- Escape route: quasilinear preferences + monetary transfers.

## 10.3 Quasilinear preferences

- uᵢ(x, pᵢ) = vᵢ(x) − pᵢ (valuation minus payment; assumes risk neutrality).

### Key properties
- **Truthfulness**: truth-telling is a dominant strategy.
- **Efficiency**: x = arg max_x Σᵢ vᵢ(x) (social welfare maximisation).
- **Budget balance**: Σᵢ pᵢ = 0.
- **Individual rationality**: no agent loses by participating.
- **Tractability**: x and p computable in polynomial time.

## 10.4 Groves mechanisms

```
x(v̂) = arg max_x  Σᵢ v̂ᵢ(x)                      # maximise declared social welfare
℘ᵢ(v̂) = hᵢ(v̂₋ᵢ) − Σ_{j≠i} v̂ⱼ(x(v̂))          # payment: arbitrary term minus others' welfare
```

**Theorem 10.4.2**: Truth-telling is a dominant strategy under any Groves mechanism.

Intuition: agent i's utility = vᵢ(x(v̂)) + Σ_{j≠i} v̂ⱼ(x(v̂)) − hᵢ(v̂₋ᵢ).
Setting v̂ᵢ = vᵢ maximises total social welfare, which is exactly what agent i maximises.

**Green-Laffont theorem**: Groves is the *only* dominant-strategy efficient family for agents with unrestricted quasilinear utilities.

### VCG mechanism
- hᵢ(v̂₋ᵢ) = max_x Σ_{j≠i} v̂ⱼ(x)
- Payment = externality imposed on others by agent i's participation.
- Individually rational + weakly budget-balanced.
- NOT strongly budget-balanced in general.

### Drawbacks of VCG
- Not strongly budget-balanced.
- Susceptible to collusion.
- Not monotone in combinatorial settings.

## 10.5 Affine maximisers (Roberts 1979)

With unrestricted quasilinear utilities and ≥3 outcomes: only affine maximisers are dominant-strategy implementable.
```
x = arg max_x  Σᵢ λᵢ vᵢ(x) + κ(x)
```
VCG = affine maximiser with λᵢ = 1 for all i, κ = 0.

## 10.6 Social choice impossibilities

- **Arrow (1951)**: No PE + IIA + non-dictatorial SWF with |O| ≥ 3.
- **Muller-Satterthwaite (1977)**: No wPE + monotonic + non-dictatorial SCF with |O| ≥ 3.
- Approval voting satisfies all three in the ranking-systems setting (symmetric preferences).

## Hermes Applications

### Skill routing as mechanism design
- Agents declare capability/confidence; route to skill maximising expected yield.
- IC design: reward honest declarations via yield tracking; penalise overconfidence.
- Revelation principle: design routing so truthful capability declarations lead to better outcomes.

### Tool authorisation
- Groves framing: authoriser picks tool set maximising declared utility minus externality (auth cost).
- Combine with inspection game for audit rate (see ch06-adversarial-agents.md).

### Agent self-reporting
- Design workflows so honest uncertainty reporting leads to delegation, not punishment.
- This creates IC incentive: agents truthfully report confidence (→ calibration-threshold-updater.py benefits).

## Pitfalls

- VCG is not budget-balanced; do not claim it is without checking.
- Revelation principle reduces analysis to direct mechanisms, not necessarily implementation.
- VCG winner determination in combinatorial auctions is NP-hard.
- Gibbard-Satterthwaite: without transfers, dominant-strategy IC is essentially impossible.
- Groves mechanisms vulnerable to collusion (coordinated misreports by coalitions).
