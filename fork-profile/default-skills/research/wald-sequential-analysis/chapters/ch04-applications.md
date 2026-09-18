# Chapter 4: Hermes Applications of Sequential Analysis

Source: Wald, *Sequential Analysis* (full OCR Sep 2026) — applied to Hermes agent systems.

---

## Overview

Four Hermes-specific applications of Wald's sequential framework:

1. **SPRT for agent retry stop decisions** — when is accumulated failure evidence sufficient?
2. **ASN bounds for expected retry count** — how many retries before a decision on average?
3. **OC curve for error rate calibration** — what α/β does the current stopping rule achieve?
4. **Sequential confidence intervals for skill performance** — bound skill success rate p after each outcome

---

## 1. SPRT for Agent Retry Stop Decisions

### Problem

An agent calls a tool repeatedly. Each call either succeeds (x=0) or fails (x=1). We want to decide: is the tool working (p = p₀, low failure rate) or broken (p = p₁, high failure rate)?

- **H₀:** p = p₀ (tool working — keep retrying)
- **H₁:** p = p₁ (tool broken — escalate/abort)

### SPRT formulation

Per-observation log-likelihood ratio:

```
z_i = log[f(x_i, p₁) / f(x_i, p₀)]
    = x_i · log(p₁/p₀) + (1−x_i) · log((1−p₁)/(1−p₀))
```

Running sum S_m = z₁ + … + z_m. Boundaries:

```
log_B = log(β / (1 − α))         ← accept H₀ (tool working)
log_A = log((1 − β) / α)         ← accept H₁ (tool broken)
```

### Implementation

```python
import math

class SPRTRetryDecider:
    """
    SPRT-based retry stop decision for a binary tool outcome.
    
    Parameters
    ----------
    p0 : float  — failure rate under H₀ (tool working), e.g. 0.05
    p1 : float  — failure rate under H₁ (tool broken), e.g. 0.40
    alpha : float — P(declare broken | truly working), e.g. 0.05
    beta : float  — P(declare working | truly broken), e.g. 0.10
    max_retries : int — hard truncation limit
    """
    
    def __init__(self, p0=0.05, p1=0.40, alpha=0.05, beta=0.10, max_retries=30):
        self.p0, self.p1 = p0, p1
        self.log_z_fail    = math.log(p1/p0)
        self.log_z_success = math.log((1-p1)/(1-p0))
        self.log_A = math.log((1 - beta) / alpha)
        self.log_B = math.log(beta / (1 - alpha))
        self.max_retries = max_retries
        self.S = 0.0
        self.n = 0
    
    def observe(self, failed: bool) -> str:
        """
        Record one outcome. Returns:
          'continue'    — keep retrying
          'accept_H0'   — tool working, stop retrying
          'reject_H0'   — tool broken, escalate
          'truncated'   — hit max_retries, forced decision
        """
        self.n += 1
        self.S += self.log_z_fail if failed else self.log_z_success
        
        if self.S >= self.log_A:
            return 'reject_H0'   # tool broken
        if self.S <= self.log_B:
            return 'accept_H0'   # tool working
        if self.n >= self.max_retries:
            mid = (self.log_A + self.log_B) / 2
            return 'reject_H0' if self.S > mid else 'accept_H0'
        return 'continue'
    
    @property
    def asn_estimate(self) -> dict:
        """Approximate ASN at both hypothesis points."""
        Ez0 = self.p0 * self.log_z_fail + (1-self.p0) * self.log_z_success
        Ez1 = self.p1 * self.log_z_fail + (1-self.p1) * self.log_z_success
        alpha = math.exp(-self.log_A)  # approx
        beta  = math.exp(self.log_B)
        asn0 = ((1-alpha)*self.log_B + alpha*self.log_A) / Ez0
        asn1 = (beta*self.log_B + (1-beta)*self.log_A) / Ez1
        return {'asn_under_H0': asn0, 'asn_under_H1': asn1}
```

### Usage pattern

```python
decider = SPRTRetryDecider(p0=0.05, p1=0.40, alpha=0.05, beta=0.10, max_retries=25)

for attempt in range(decider.max_retries):
    result = call_tool()
    decision = decider.observe(failed=(result is None or result.error))
    
    if decision == 'accept_H0':
        # Tool is probably fine — last attempt succeeded or evidence insufficient
        break
    elif decision in ('reject_H0', 'truncated'):
        escalate_to_fallback_tool()
        break
    # else: continue
```

---

## 2. ASN Bounds for Expected Retry Count

### Why ASN matters for agent design

If you don't compute ASN, you may:
- Set max_retries too low (truncation fires before decision, inflating errors)
- Set max_retries too high (wasting latency on obvious failures)

**Rule of thumb:** Set max_retries ≥ 3× max(ASN under H₀, ASN under H₁).

### Typical ASN values (Bernoulli SPRT)

For p₀ = 0.05, p₁ = 0.30, α = 0.05, β = 0.10:

```
log_A = log(0.90/0.05) = 2.89
log_B = log(0.10/0.95) = -2.25

E_{p₀}(z) = 0.05·log(6) + 0.95·log(0.986) ≈ 0.09 − 0.013 ≈ 0.077
ASN under H₀ ≈ [(0.95)(−2.25) + (0.05)(2.89)] / 0.077 ≈ 23

E_{p₁}(z) = 0.30·log(6) + 0.70·log(0.986) ≈ 0.537 − 0.010 ≈ 0.527
ASN under H₁ ≈ [(0.10)(−2.25) + (0.90)(2.89)] / 0.527 ≈ 4.5
```

The test is fast when the tool is broken (ASN ≈ 5 retries) and slower when working (ASN ≈ 23) — exactly the right asymmetry for retry decisions.

### Sensitivity: approaching the indifference zone

As p → some value between p₀ and p₁ where E(z) → 0, ASN grows rapidly. If the true failure rate is exactly halfway, expect many more observations. Build in a timeout (truncation) for this case.

---

## 3. OC Curve for Error Rate Calibration

### What the OC curve tells you

L(p) = P(SPRT accepts H₀ | true failure rate = p) for any p between 0 and 1.

- L(p₀) ≈ 1 − α: rarely declares broken when working
- L(p₁) ≈ β: rarely declares working when broken
- L(p) for p ∈ (p₀, p₁): how gracefully the test degrades in the indifference zone

### Computing OC for Bernoulli case

```python
def oc_bernoulli_sprt(p, p0, p1, log_A, log_B):
    """
    Approximate OC function L(p) for Bernoulli SPRT.
    Uses the h(p) root of E_p[exp(h*z)] = 1.
    """
    if abs(p - p0) < 1e-6:
        return None  # use 1 - alpha directly
    if abs(p - p1) < 1e-6:
        return None  # use beta directly
    
    # Binary search for h: E_p[exp(h*z)] = 1
    # E_p[exp(h*z)] = p*(p1/p0)^h + (1-p)*((1-p1)/(1-p0))^h
    def mgf_minus_1(h):
        return (p*(p1/p0)**h + (1-p)*((1-p1)/(1-p0))**h) - 1
    
    import scipy.optimize as opt
    try:
        h = opt.brentq(mgf_minus_1, -50, 50, xtol=1e-8)
    except ValueError:
        return 0.5  # fallback
    
    # OC formula: L(p) ≈ (A^h - 1) / (A^h - B^h)
    A = math.exp(log_A)
    B = math.exp(log_B)
    Ah = A ** h
    Bh = B ** h
    if abs(Ah - Bh) < 1e-12:
        return 0.5
    return (Ah - 1) / (Ah - Bh)
```

### Calibration workflow

1. Choose target α (false alarm rate) and β (missed detection rate)
2. Choose p₀ (acceptable tool failure rate) and p₁ (unacceptable tool failure rate)
3. Compute boundaries A, B
4. Plot L(p) for p ∈ [0, 1] to verify the OC meets requirements
5. If not, tighten α/β (which increases ASN) or widen p₀/p₁ gap (easier test)

---

## 4. Sequential Confidence Intervals for Skill Performance

### Problem

After each successful/failed use of a Hermes skill, update a running estimate of its success rate p with a **confidence interval** that narrows as evidence accumulates. Stop collecting when the CI width drops below a target.

### Connection to Wald Ch 11

This is sequential estimation (Ch 11): stop at the smallest n such that the current CI satisfies both:
- Coverage ≥ 1 − α (Condition I)
- Width ≤ d (Condition II)

### Implementation

```python
import math

class SequentialSkillCI:
    """
    Sequential Wilson confidence interval for skill success rate.
    Stops when CI width < target_width with coverage >= 1-alpha.
    """
    
    def __init__(self, alpha=0.05, target_width=0.10, min_n=10):
        self.alpha = alpha
        self.z = 1.96  # approx for alpha=0.05
        self.target_width = target_width
        self.min_n = min_n
        self.successes = 0
        self.n = 0
    
    def observe(self, success: bool) -> dict:
        self.n += 1
        self.successes += int(success)
        
        p_hat = self.successes / self.n
        result = {'n': self.n, 'p_hat': p_hat, 'converged': False,
                  'ci_lower': None, 'ci_upper': None, 'width': None}
        
        if self.n < self.min_n:
            return result
        
        # Wilson interval
        z = self.z
        denom = 1 + z**2 / self.n
        center = (p_hat + z**2 / (2*self.n)) / denom
        margin = (z / denom) * math.sqrt(
            p_hat*(1-p_hat)/self.n + z**2/(4*self.n**2)
        )
        width = 2 * margin
        result.update({
            'ci_lower': max(0, center - margin),
            'ci_upper': min(1, center + margin),
            'width': width,
            'converged': width <= self.target_width
        })
        return result
```

### Usage

```python
ci = SequentialSkillCI(alpha=0.05, target_width=0.10)

for outcome in skill_outcome_stream:
    result = ci.observe(success=outcome)
    if result['converged']:
        print(f"Skill p = {result['p_hat']:.3f} "
              f"[{result['ci_lower']:.3f}, {result['ci_upper']:.3f}] "
              f"after n={result['n']}")
        break
```

---

## Cross-reference to SPRT spikes

See `/tmp/sipser_wald_spikes.json` for formal spike proposals:
- **WALD2-1:** SPRT retry stop (this chapter § 1)
- **WALD2-2:** ASN bounds for retry count (§ 2)
- **WALD2-3:** OC curve for error rate calibration (§ 3)
- **WALD2-4:** Sequential CI for skill performance (§ 4)
