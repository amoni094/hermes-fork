# Chapter 2: OC and ASN Functions

Source: Wald, *Sequential Analysis* Ch 2–3 (OCR Sep 2026).

---

## OC Function — Operating Characteristic (Ch 2.2.1)

**Definition:** L(θ) = P(accept H₀ | true parameter = θ).

L(θ) fully characterizes the decision quality of a sequential test:
- L(θ) near 1 in the H₀ region → rarely reject when H₀ true (low α)
- L(θ) near 0 in the H₁ region → rarely accept when H₁ true (low β)
- Between θ₀ and θ₁ (indifference zone): L(θ) unconstrained

**Requirements (Ch 2.3.2):**

```
L(θ) ≥ 1 − α    for θ in acceptance zone (H₀ preferred)
L(θ) ≤ β        for θ in rejection zone (H₁ preferred)
```

No constraint in the indifference zone — this is the region of practical ambiguity.

### OC approximation formula (Ch 3.5, App A.2, eq. A:19)

For SPRT with boundaries A, B:

```
L(θ) ≈ (A^h(θ) − 1) / (A^h(θ) − B^h(θ))
```

where h(θ) is the **unique nonzero real root** of the equation:

```
E_θ[ exp(h · z) ] = 1
```

(z = log-likelihood ratio per observation). This h(θ) exists and is unique under regularity conditions (App A.2.2).

**Special points:**
- At θ = θ₀: L(θ₀) ≈ 1 − α
- At θ = θ₁: L(θ₁) ≈ β
- At indifference point (E_θ(z) = 0, h = 0): L(θ) ≈ log A / (log A − log B)

### Normal mean OC (Ch 3.5, eq. 3:47–3:48)

H₀: μ = μ₀, H₁: μ = μ₁, σ known. Then:

```
h(μ) = (μ₀ + μ₁ − 2μ) / (μ₁ − μ₀)
```

Substituting into the OC formula gives a closed-form approximation.

---

## ASN Function — Average Sample Number (Ch 2.2.2, Ch 3.6)

**Definition:** E_θ(n) = expected number of observations before stopping, given true θ.

ASN is the "price" of the sequential test. Two tests of equal strength are compared by their ASN functions — lower ASN is better.

### Derivation (Ch 3.6, eq. 3:49–3:57)

From Wald's identity: E(S_n) = E(n) · E(z), i.e., E(z₁ + … + z_n) = E(n) · E_θ(z).

Hence:

```
E_θ(n) = E_θ(S_n) / E_θ(z)
```

At termination (ignoring boundary overshoot), S_n equals log B with probability L(θ) and log A with probability 1 − L(θ):

```
E_θ(S_n) ≈ L(θ) · log B + (1 − L(θ)) · log A
```

Therefore the **ASN approximation formula** (eq. 3:57):

```
E_θ(n) ≈ [ L(θ) · log B + (1 − L(θ)) · log A ] / E_θ(z)
```

### Evaluation at key points

**At θ = θ₀** (H₀ true, L ≈ 1−α):
```
E_{θ₀}(n) ≈ [(1−α) · log B + α · log A] / E_{θ₀}(z)
```

**At θ = θ₁** (H₁ true, L ≈ β):
```
E_{θ₁}(n) ≈ [β · log B + (1−β) · log A] / E_{θ₁}(z)
```

**At indifference θ*** (E_θ*(z) = 0): Formula is indeterminate. ASN is of order **(log A)² / Var_θ*(z)** — large but finite for finite A, B.

### Efficiency comparison (Ch 3, §"Saving in observations")

For a normal mean test (σ known), the fixed-n optimal test requires approximately:

```
n_fixed ≈ (z_α + z_β)² · σ² / (μ₁ − μ₀)²
```

The SPRT achieves the same (α, β) with E(n) ≈ 40–60% of n_fixed at the two hypothesis points. The saving is largest when α and β are both small.

---

## Selecting a sequential test (Ch 2.3)

**Step 1:** Specify the parameter space partition:
- ω (acceptance zone), ω̄ (rejection zone), indifference zone

**Step 2:** Preassign error rates α, β.

**Step 3:** Among all tests meeting the OC constraint, choose the one minimizing ASN.

**Result:** SPRT achieves this optimum (to practical precision) for simple hypotheses.

---

## Hermes application: OC and ASN for retry decisions

Map agent retry to the SPRT framework:
- θ₀ = "tool is working" (low failure rate p₀)
- θ₁ = "tool is broken" (high failure rate p₁)
- Each retry outcome: x_i = 1 (failure), 0 (success)

**OC curve tells you:** Given true failure rate p, what is the probability the SPRT incorrectly concludes the tool is working?

**ASN tells you:** On average, how many retries before a decision? This bounds expected latency.

**Design procedure:**
```python
import math

def sprt_boundaries(alpha: float, beta: float) -> tuple[float, float]:
    """Returns (log_B, log_A) for SPRT with given error rates."""
    A = (1 - beta) / alpha
    B = beta / (1 - alpha)
    return math.log(B), math.log(A)

def sprt_asn(p: float, p0: float, p1: float, 
             log_B: float, log_A: float, alpha: float, beta: float) -> float:
    """ASN approximation at true rate p."""
    if p == 0:
        Ez = math.log((1 - p1) / (1 - p0))
    elif p == 1:
        Ez = math.log(p1 / p0)
    else:
        Ez = p * math.log(p1/p0) + (1-p) * math.log((1-p1)/(1-p0))
    
    if abs(Ez) < 1e-9:
        # Indifference zone: ASN ~ (log_A)^2 / Var(z)
        var_z = p * (math.log(p1/p0) - Ez)**2 + (1-p) * (math.log((1-p1)/(1-p0)) - Ez)**2
        return (log_A ** 2) / max(var_z, 1e-12)
    
    # L(p) at the two boundary points: approximate as linear interpolation
    L_p0 = 1 - alpha
    L_p1 = beta
    t = (p - p0) / (p1 - p0) if p1 != p0 else 0.5
    L = L_p0 + t * (L_p1 - L_p0)
    L = max(0.001, min(0.999, L))
    
    ES_n = L * log_B + (1 - L) * log_A
    return ES_n / Ez
```
