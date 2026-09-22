# Glossary — Harchol-Balter Performance Modeling

| Term | Meaning |
|------|---------|
| **Age** | Service received so far. Under FB, lowest age wins. |
| **All-Can-Win** | For typical HT M/G/1, E[T(x)]^{SRPT} ≤ E[T(x)]^{PS} for all x (no class loses vs PS). |
| **BCMP** | Product-form network class including PS / P-LCFS / IS with general service. |
| **Birth-death** | CTMC with only neighbor transitions (M/M/1, M/M/k). |
| **Bounded Pareto(k,p,α)** | Pareto truncated to [k,p]; finite moments, still elephants/mice. |
| **Brumelle H=λG** | Generalization of L=λW: time-average cost = λ × expected cost per customer. Higher-moment L↔W needs FCFS-like order. |
| **Busy period B** | Idle-to-idle sojourn of the server. E[B]=E[S]/(1−ρ). |
| **C², SCV** | Var(X)/E[X]². Exp=1; D=0; HT ≫1. **C²>1 ⇒ leave FCFS.** |
| **DFR / IFR** | Decreasing / increasing failure rate. Pareto DFR: older ⇒ stochastically longer residual. |
| **Excess / residual S_e** | Remaining interval seen by a random observer. E[S_e]=E[S²]/(2E[S])=(E[S]/2)(C²+1). |
| **FB / LAS** | Foreground-Background / Least-Attained-Service: serve lowest age. Size-unknown SEPT under DFR. |
| **FCFS** | First-come-first-served. Size-blind, non-preemptive. Mean T explodes with C² (P-K). |
| **Forced Flow** | X_i = X V_i (visit ratio). |
| **Heavy tail** | Power-law tail; few jobs hold most work. Pareto α<2. |
| **Inspection paradox** | Random observer lands in a long interval (length-bias). |
| **Jackson network** | Open exponential network, probabilistic routing, product form. |
| **Kendall** | A/S/k[/K][/policy]. M=memoryless, G=general, D=deterministic. |
| **LCFS** | Last-come-first-served. Same E[T] as FCFS if non-preemptive size-blind; **worst Var(T)**. P-LCFS ≈ PS means. |
| **Little's Law** | E[N]=λE[T] (open); N=X E[T] (closed). Any ergodic system. |
| **Load / utilisation ρ** | λE[S] (single server); λ/(kμ) for k servers. Stable iff ρ<1. Target ρ<0.7 for latency-critical M/G/1. |
| **M/G/1** | Poisson arrivals, general service, one server. Workhorse model. |
| **M/M/1** | Poisson, exponential, one server. π_n=(1−ρ)ρ^n, E[T]=1/(μ−λ). |
| **MVA** | Mean Value Analysis for closed product-form nets (Arrival Theorem). |
| **PASTA** | Poisson Arrivals See Time Averages: a_n=p_n. |
| **PH / Coxian / H2** | Phase-type approximations of G; H2 matches C²>1. |
| **P-K** | Pollaczek–Khinchin: E[T_Q]=λE[S²]/(2(1−ρ)) for M/G/1 FCFS. |
| **PS** | Processor-Sharing (RR quantum→0). Insensitive: E[T]=E[S]/(1−ρ). Fair slowdown. |
| **PSJF** | Preemptive Shortest-Job-First (priority = original size). E[Res(x)]=x/(1−ρ_x). |
| **ρ_x** | Load of jobs of size < x: λ∫_0^x t f(t)dt. |
| **SEPT / SERPT** | Shortest Expected (Remaining) Processing Time. Size unknown. FB implements this under DFR. Not a book chapter name. |
| **SITA** | Size-interval task assignment: isolate size classes on FCFS farms. |
| **SJF** | Shortest-Job-First, non-preemptive. Residual of a started elephant still hurts. |
| **Slowdown** | T/S ≥ 1. PS: 1/(1−ρ) for all x. SRPT does not minimise mean slowdown. |
| **Sojourn / response T** | Time in system = wait + service (+ residences under preemption). |
| **Square-root staffing** | k*≈R+c√R to keep P_Q<α. α=0.2 ⇒ c≈1. |
| **SRPT** | Shortest Remaining Processing Time. Minimises mean T on every sample path. |
| **Stability** | Open single server: ρ<1. Else N→∞. |
| **Tail latency** | P(T>x), high percentiles. Driven by E[S³] under FCFS; LCFS worst among size-blind NP. |
| **Work-conserving** | Never idle with work present; never create work. Same remaining-work process, **not** same E[T]. |
| **Weibull** | F̄=exp(−(x/λ)^α). α<1 DFR, C² arbitrary. Used in Ch 33 plots. |
| **z-transform / Laplace** | N^(z)=E[z^N]; X~(s)=E[e^{−sX}]. M/G/1: T~(s)=S~(s)(1−ρ)s/(λS~(s)−λ+s). |
