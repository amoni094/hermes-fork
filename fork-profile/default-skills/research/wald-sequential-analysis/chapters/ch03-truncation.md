# Chapter 3: Truncation, Grouping, and Sequential Confidence Intervals

Source: Wald, *Sequential Analysis* Ch 5.6–5.7, Ch 11 (OCR Sep 2026).

---

## Truncation (Ch 5.6–5.7)

In theory, SPRT terminates with probability 1. In practice, every deployed sequential procedure must be **truncated**: a hard maximum n₀ is set, after which a terminal decision is forced.

### Effect on error rates

Let α(n₀) and β(n₀) denote the actual error rates when truncation at n₀ is applied. Wald derives upper bounds (eqs 3:94–3:95):

```
α(n₀) ≤ α + [G(v₂) − G(v₁)]
β(n₀) ≤ β + [G(r₄) − G(r₃)]
```

where G is the standard normal CDF and:

```
v₁ = (log A − n₀ · E₀(z)) / √(n₀ · Var₀(z))
v₂ = (−log B − n₀ · E₀(z)) / (−√(n₀ · Var₀(z)))  [sign per Wald eq 3:89]
r₃, r₄ analogously under H₁
```

**Table 3 values (Wald Ch 5, binomial truncation example):**

| n₀ | Upper bound α(n₀) | Upper bound β(n₀) |
|----|------------------|------------------|
| 1000 | 0.020 | 0.020 |
| 1200 | closer to nominal | closer to nominal |

The bounds improve (shrink toward nominal) as n₀ increases. For n₀ much larger than the expected stopping time, the inflation is negligible.

### Forced terminal decision at n₀

When n₀ is reached without crossing a boundary:
- **Accept H₀** if S_{n₀} < (log A + log B) / 2 (closer to log B)
- **Reject H₀** otherwise

This is the most common convention. Alternatives include choosing the decision that minimizes worst-case risk.

### Hermes truncation rule

Every SPRT-based agent retry loop **must** have a truncation:

```python
MAX_RETRIES = 20   # n₀ — chosen so that expected ASN << MAX_RETRIES

def sprt_retry_loop(tool_fn, log_B, log_A, max_retries=MAX_RETRIES):
    S = 0.0
    for attempt in range(max_retries):
        outcome = tool_fn()            # 1 = failure, 0 = success
        z_i = compute_log_lr(outcome)  # log f(x, θ₁)/f(x, θ₀)
        S += z_i
        
        if S >= log_A:
            return "reject_H0"  # tool is broken
        if S <= log_B:
            return "accept_H0"  # tool is working
    
    # Truncation: forced decision
    midpoint = (log_A + log_B) / 2
    return "reject_H0" if S > midpoint else "accept_H0"
```

---

## Grouping (Ch 5.7)

When observations come in **batches of size k** rather than one at a time:

- Each batch contributes z_{(j-1)k+1} + … + z_{jk} to the cumulative sum
- The test evaluates boundaries only after each batch
- ASN inflates by at most a factor related to the batch variance

**Wald's bound:** The expected sample number for a grouped test does not exceed the SPRT ASN plus k (one batch). For moderate k, the overhead is small.

**Hermes implication:** If tool calls are made in parallel batches, accumulate z_i values for the whole batch before evaluating boundaries. The error rate guarantees still hold; only ASN increases slightly.

---

## Sequential Estimation (Ch 11)

Instead of testing H₀ vs H₁, estimate a parameter θ with a confidence set that has:
- **Condition I:** Coverage ≥ 1 − α (the set contains θ with probability ≥ 1 − α)
- **Condition II:** Diameter ≤ d (the set is small enough to be useful)

**Sequential procedure:** Continue sampling until both conditions are met simultaneously. Stop at the smallest n for which the current confidence set w(E_n) satisfies both.

**Special class (Ch 11.3):** Use the product inequality (10:7) to define w(E_n) as the set of θ for which the likelihood ratio does not exceed A = 1/(1 − γ). This guarantees Condition II automatically; stop when the diameter falls below d.

**Termination:** If the diameter shrinks to 0 as n → ∞ (which holds for regular families), the procedure terminates with probability 1.

### Sequential confidence intervals for skill performance

Applied to Hermes skill success rate p:

```python
import math
from collections import deque

def sequential_ci(outcomes_stream, alpha=0.05, target_width=0.1):
    """
    Sequential confidence interval for binomial p.
    Stops when Wilson interval width < target_width with coverage >= 1-alpha.
    
    outcomes_stream: iterable of 0/1 outcomes
    Returns: (p_hat, ci_lower, ci_upper, n_used)
    """
    successes = 0
    n = 0
    z = 1.96  # approx for alpha=0.05
    
    for outcome in outcomes_stream:
        n += 1
        successes += outcome
        
        if n < 5:
            continue  # too few observations for reliable CI
        
        p_hat = successes / n
        # Wilson interval
        denom = 1 + z**2 / n
        center = (p_hat + z**2 / (2*n)) / denom
        margin = (z / denom) * math.sqrt(p_hat*(1-p_hat)/n + z**2/(4*n**2))
        
        width = 2 * margin
        if width <= target_width:
            return p_hat, center - margin, center + margin, n
    
    # Return best estimate if stream exhausted
    p_hat = successes / n if n > 0 else 0.5
    return p_hat, None, None, n
```

---

## Composite hypotheses (Ch 4)

For composite H₀: θ ∈ Ω₀ (a set of values), replace the simple likelihood ratio by a **weighted average**:

```
Λ_m^(w) = ∫ p_{1m}(θ) w(θ) dθ  /  ∫ p_{0m}(θ) w'(θ) dθ
```

where w, w' are weight functions over Ω₁, Ω₀ respectively. The SPRT with this ratio preserves OC and ASN structure.

**Sequential t-test (Ch 4.2.3, App A.9.2):** Test μ = μ₀ vs μ = μ₁ when σ is unknown. Use the t-statistic as the likelihood ratio increment with appropriate weight function. OC and ASN expressions are more complex but the SPRT form is preserved.

---

## Multi-valued decisions (Ch 10)

When there are k > 2 hypotheses H₀, H₁, …, H_{k-1}:

**Sequential plan:** At each stage, one of k+1 decisions: accept Hⱼ (j=0..k-1) or continue. Use the product inequality (10:7):

```
∏_{j≠i} Λ_m(θⱼ, θᵢ) ≥ A   →   reject Hᵢ
```

**Risk function:** Associate a loss L(decision, true H). The optimal sequential plan minimizes expected loss + cost-per-observation, solved via dynamic programming on the (S_m, m) state.

**Hermes application:** When there are 3+ hypotheses about agent state (working / degraded / broken), use multi-valued SPRT with k=3 to route to the appropriate recovery action with minimal expected observations.
