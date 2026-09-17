# Glossary — Khalil: Nonlinear Systems

## A

**Absolute stability** — Stability of a Lur'e system (linear plant + static nonlinearity) for *all* nonlinearities in a given sector [K₁,K₂]. See Ch. 6–7.

**Asymptotically stable (AS)** — Equilibrium is stable AND x(t)→0 as t→∞. Requires both stability (no drift) and attractivity (convergence).

**Attractivity** — Every solution starting nearby converges to the equilibrium. Attractivity alone (without stability) does not imply AS.

**Averaging** — Approximation technique for ẋ=εf(t,x,ε): replace f with its time-average f_av. Valid on O(1/ε) timescales. See Ch. 10.

## B

**Backstepping** — Recursive Lyapunov design for triangular systems. At each step, treat next state as virtual control; augment Lyapunov function. Constructs global certificate. See Ch. 14.3.

**Bendixson's criterion** — Sufficient condition for no closed orbits: div(f)=∂f₁/∂x₁+∂f₂/∂x₂ has constant sign. See Ch. 2.

**BIBO (Bounded Input Bounded Output)** — ℒ∞ stability: bounded input ⟹ bounded output. Equivalent to finite-gain ℒ∞ stability.

**Boundary layer** — In singular perturbation, fast transient near t=t₀ that decays on timescale ε. Analyzed in stretched time τ=t/ε.

## C

**Center** — Equilibrium with purely imaginary eigenvalues. Closed orbits nearby. NOT stable in Lyapunov sense (trajectories don't tend to it), not unstable. Borderline case.

**Center manifold** — Invariant manifold tangent to center eigenspace at origin. Dynamics on it determine stability when linearization fails. See Ch. 8.1.

**Class K** — Function α:[0,∞)→[0,∞), continuous, strictly increasing, α(0)=0.

**Class K∞** — Class K + unbounded (α(r)→∞ as r→∞).

**Class KL** — Function β(r,s): class K in r for each s, decreasing to 0 in s for each r>0. Characterizes transient + decay in stability estimates.

**Comparison lemma** — If u̇≤f(t,u) and v̇=f(t,v), v(t₀)≥u(t₀), then u(t)≤v(t). Used to bound trajectories without explicit solutions.

## D

**Dead zone** — Nonlinearity: output zero for small inputs, linear/nonlinear outside. Sector-bounded.

**Describing function** — Frequency-domain approximation for nonlinear analysis. Approximates nonlinearity by amplitude-dependent gain. Not rigorous but practically useful for finding limit cycles.

**Diffeomorphism** — Smooth bijection with smooth inverse. Used in coordinate changes for feedback linearization.

**Distribution** — Assignment of subspaces to each point in Rⁿ. Involutive distribution: closed under Lie brackets. Required for integrability (Frobenius theorem).

## E

**Equilibrium point** — x* such that f(x*)=0 (continuous) or F(x*)=x* (discrete). All stability notions defined relative to equilibrium.

**Exponential stability** — ‖x(t)‖ ≤ ke^{-γt}‖x(0)‖. Strongest form; robust to perturbations.

**Extended space ℒₑ** — Signals whose truncations belong to ℒ. Allows analysis of potentially unbounded signals.

## F

**Feedback linearization** — Exact cancellation of nonlinearities via state feedback + coordinate change to yield linear system. Requires relative degree and involutivity conditions. See Ch. 13.

**Finite escape time** — Solution x(t)→∞ at finite time T<∞. Impossible for linear systems; possible for nonlinear (e.g., ẋ=x²).

**Finite-gain ℒ stable** — ‖(Hu)_T‖ ≤ γ‖u_T‖ + β for all inputs. γ = gain of system.

**Focus** — Equilibrium with complex eigenvalues. Stable focus: Re(λ)<0 (spiral in). Unstable focus: Re(λ)>0 (spiral out).

## G

**GAS (Globally Asymptotically Stable)** — AS with region of attraction = entire state space. Requires radially unbounded Lyapunov function.

**Gain scheduling** — Controller parameters vary with operating condition. Stability analysis requires additional assumptions beyond frozen-point stability.

**Gronwall inequality** — If u(t)≤α+∫β(s)u(s)ds, then u(t)≤α·exp(∫β(s)ds). Fundamental bound for trajectory error analysis.

## H

**Hartman-Grobman theorem** — Near a hyperbolic equilibrium, nonlinear phase portrait is topologically equivalent to linearization. Justifies local linearization.

**High-gain observer** — Observer with gain O(1/ε) recovering state from output. As ε→0, estimation error→0. Allows output-feedback use of state-feedback designs. See Ch. 14.5.

**Hurwitz matrix** — All eigenvalues have strictly negative real part. A is Hurwitz ⟺ linear system ẋ=Ax is GAS.

## I

**Index (Poincaré)** — Integer assigned to closed curve in R²: counts rotations of f(x). Limit cycle must enclose equilibria with index sum = 1.

**Input-output stability** — Stability in the sense of signal norms: bounded inputs produce bounded outputs. See Ch. 5.

**Input-to-State Stability (ISS)** — ‖x(t)‖≤β(‖x(0)‖,t)+γ(‖u‖_{[0,t]}). Unifies stability and gain. See Ch. 4.9. Key: ISS⟹BIBO, ISS cascade composition.

**Invariant set** — Set S such that x(0)∈S ⟹ x(t)∈S for all t≥0.

**Involutive** — Distribution Δ is involutive if [X,Y]∈Δ whenever X,Y∈Δ. Frobenius: involutive ⟺ integrable (∃ foliation).

## K

**KYP lemma (Kalman-Yakubovich-Popov)** — Conditions equivalent to positive realness: matrix inequality version enabling algebraic test.

## L

**LaSalle's invariance principle** — For autonomous system in compact Ω with V̇≤0: solutions converge to largest invariant set M in {V̇=0}. Extends Lyapunov to non-strict V̇. See Ch. 4.2.

**Lie bracket** — [f,g](x) = (∂g/∂x)f(x) - (∂f/∂x)g(x). Measures non-commutativity of flows. Central to feedback linearization conditions.

**Lie derivative** — L_f h(x) = (∂h/∂x)f(x). Directional derivative of h along f.

**Limit cycle** — Isolated closed trajectory in phase plane. Stable: attracting. Unstable: repelling. Nonlinear phenomenon; linear systems have no isolated closed orbits.

**Lipschitz condition** — ‖f(x)-f(y)‖≤L‖x-y‖. Ensures existence/uniqueness of solutions. C¹ functions are locally Lipschitz.

**Lur'e problem** — Stability of feedback: linear G(s) + static nonlinearity ψ. Absolute stability: stable for all ψ in sector.

**Lyapunov equation** — AᵀP+PA=-Q. Solution P>0 certifies A Hurwitz and gives Lyapunov function V=xᵀPx.

**Lyapunov function** — Scalar V:D→R with V(0)=0, V>0, V̇≤0 (or <0). Certifies stability without solving ODE. See Ch. 4.

**Lyapunov redesign** — Modify nominal control with additive robustifying term derived from Lyapunov function to handle matched uncertainty. See Ch. 14.2.

## M

**Matched condition** — Uncertainty enters system through same channel as control (B·Δ). Sliding mode and Lyapunov redesign handle matched uncertainty exactly.

**Minimum phase** — System with AS zero dynamics. Non-minimum-phase: zero dynamics unstable, input-output linearization may be problematic.

## N

**Node** — Equilibrium with real eigenvalues of same sign. Stable node: both negative (no oscillation, direct convergence).

**Normal form** — Brunovsky canonical form after feedback linearization: chain of integrators.

## O

**Orbital stability** — Stability of periodic orbit (limit cycle). Analyzed via Poincaré return map.

## P

**Passive** — System with storage function V≥0 satisfying V̇≤uᵀy. Cannot create energy. Passivity theorem: negative feedback of passive + strictly passive = stable. See Ch. 6.

**Peaking phenomenon** — High-gain observer produces large transient peaks in state estimates. Mitigated by saturating control.

**Phase portrait** — Collection of trajectories in state space. For 2D autonomous systems: complete qualitative picture.

**Poincaré–Bendixson theorem** — In R², bounded trajectory must approach equilibrium or closed orbit. No chaos in autonomous 2D systems.

**Popov criterion** — Frequency-domain condition for absolute stability, less conservative than circle criterion for time-invariant nonlinearities.

**Positive definite** — V(x)>0 for x≠0, V(0)=0. Necessary for Lyapunov function.

**Positive real (PR)** — Transfer function Z(s): no RHP poles, Re[Z(jω)]≥0. Corresponds to passive system.

## R

**Radially unbounded** — V(x)→∞ as ‖x‖→∞. Together with AS conditions, implies GAS.

**Region of attraction (ROA)** — Set of all initial conditions x(0) from which x(t)→0. Estimated via sublevel sets of Lyapunov function. See Ch. 8.2.

**Relative degree** — Number of times output y must be differentiated before input u appears: y^(r) depends explicitly on u.

## S

**Saddle** — Equilibrium with real eigenvalues of opposite sign. Unstable; separatrices divide phase plane.

**Sector [K₁,K₂]** — Nonlinearity bounded between lines y=K₁u and y=K₂u. Captures saturation, dead zone, etc.

**Singular perturbation** — System with εż=g causing two-time-scale behavior. ε→0: fast dynamics degenerate, dimension reduction. See Ch. 11.

**Sliding manifold** — Surface s(x)=0 to which sliding mode control drives trajectories. Reduced dynamics on manifold independent of matched uncertainty.

**Sliding mode control** — Discontinuous control u=-β·sgn(s) that forces finite-time trajectory convergence to sliding manifold s=0. See Ch. 14.1.

**Small-gain theorem** — Feedback interconnection stable if γ₁γ₂<1. Nonlinear generalization of Nyquist. See Ch. 5.4.

**Stability (Lyapunov)** — For each ε>0, ∃δ>0: ‖x(0)‖<δ ⟹ ‖x(t)‖<ε, ∀t≥0. Solutions don't drift far from equilibrium.

**Storage function** — V≥0 satisfying V̇≤supply rate. Generalizes energy; certificate for passivity.

**Strictly positive real (SPR)** — PR + Z(jω)+Z*(jω)>0 strictly. Corresponds to strictly passive system.

## T

**Tikhonov's theorem** — On finite intervals, singularly perturbed solution approximates slow (reduced) + fast (boundary layer) solutions to O(ε).

**Total stability** — Stability preserved under any small perturbation. UAS ⟹ total stability.

## U

**UAS (Uniformly Asymptotically Stable)** — AS with δ,T independent of initial time t₀. Required for nonautonomous Lyapunov theorems to give clean bounds.

**UUB (Uniformly Ultimately Bounded)** — Solutions enter and remain in compact set after finite time. Weaker than AS; holds when V̇<0 only outside a ball.

## Z

**Zero dynamics** — Internal dynamics of feedback-linearized system when output is constrained to zero. Stability of zero dynamics crucial for minimum-phase classification.
