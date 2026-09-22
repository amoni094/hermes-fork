# Ch 31–32 — Priority, SJF, PSJF

**Use when**: classes or job sizes are known.

## M/G/1 priority (n classes)
Class 1 highest. λ_k=λ p_k, ρ_k=λ_k E[S_k], ∑ρ_k=ρ<1.

**Non-preemptive priority:** once started, a job finishes even if a higher class arrives. Wait of class k sees: residual of whoever is in service (all classes' excess, P-K style) + full work of classes 1..k already waiting + arrivals of classes 1..k−1 during the wait.
```
E[T_Q(k)]^{NP} = (λ E[S²]/2) / [(1−∑_{i=1}^{k−1} ρ_i)(1−∑_{i=1}^{k} ρ_i)]
```
(the "1/2 λ E[S²]" residual uses **all** classes).

**Preemptive priority:** higher class interrupts. Class k ignores classes >k completely (as if they did not exist). Residence of class k is inflated only by 1..k−1.

## SJF = non-preemptive priority with infinitely many size classes
Smaller original size = higher priority. Cannot stop a giant once it starts — residual of an elephant still freezes mice. That is **the problem with all non-preemptive policies** under HT: one started elephant.

SJF looks poor at low ρ + high C² (that residual), but **gains vs PS at high ρ** because of a (1−ρ_x) in the denominator vs PS's (1−ρ).

## PSJF = preemptive SJF
Priority = original size, and a smaller arrival preempts. Residence of a size-x job:
```
E[Res(x)]^{PSJF} = x / (1−ρ_x)
```
ρ_x = λ ∫_0^x t f(t) dt. A busy period of only jobs ≤ x, started by x.

Transform analysis of PSJF (32.4) yields higher moments analogously to priority queues.

## Rank
Knowing size helps; being able to preempt helps more:
FCFS ≪ SJF < PS ≈ P-LCFS < FB (if DFR) < PSJF < SRPT
(ordering of E[T] at high C²; see Ch 33 plots).
