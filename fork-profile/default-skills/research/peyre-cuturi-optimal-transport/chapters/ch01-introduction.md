# Chapter 1 — Introduction

## Core Idea
Optimal transport (OT) is the theory of comparing probability distributions by the cheapest way to move mass from one to another. Originating with Monge (1781), it formalizes the intuition of the "shortest path principle" applied to distributions rather than single points.

## Frameworks Introduced
- **Monge's problem** (1781): deterministic transport map T: X → Y minimizing total cost
- **Kantorovich relaxation** (1942): relax deterministic maps to probabilistic couplings
- **Earth mover's distance** (EMD): same as Wasserstein distance, named in computer vision context
- **Sinkhorn approximation**: entropic regularization enabling large-scale computation

## Key Concepts
- OT lifts a ground cost between points to a cost between distributions
- History: Monge → Tolstoi/Hitchcock/Kantorovich (logistics) → Dantzig LP → Brenier (analysis) → EMD (computer vision) → Sinkhorn revolution (ML)
- Three layers of exposition: histograms (practical), discrete measures (flexible), general measures (theoretical)

## Mental Models
- Sand and shovel: move a sand pile into a target shape with minimum effort
- Mines and factories: optimally route raw materials from warehouses to factories
- Comparing bags of features: document word histograms, image color palettes

## Anti-patterns
- Don't use OT when mass normalization fails (use unbalanced OT)
- Don't compute OT naively on high-dimensional continuous densities without approximation

## Key Notation
```
Σ_n  : probability simplex (histograms with n bins)
U(a,b): transportation polytope (feasible coupling matrices)
LC(a,b): optimal transport cost for cost matrix C
Wp   : p-Wasserstein distance
K = e^{-C/ε}: Gibbs kernel (Sinkhorn)
(f,g): dual potentials (Kantorovich)
(u,v): Sinkhorn scalings (u=e^{f/ε}, v=e^{g/ε})
```

## Key Takeaways
- OT provides a natural geometry on probability measures that respects the ground metric
- The computational revolution came from Sinkhorn (2013), enabling GPU-parallel approximation
- OT is now used in ML for: generative models (WAE/WGAN), domain adaptation, barycenter computation, statistical testing

## Connects To
- Ch 2: theoretical foundations (Kantorovich formulation)
- Ch 4: Sinkhorn algorithm
- Ch 9: variational Wasserstein (ML applications)
