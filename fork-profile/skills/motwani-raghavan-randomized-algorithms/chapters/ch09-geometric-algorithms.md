# Ch 9 — Geometric Algorithms and Linear Programming

Random incremental construction and random sampling as the geometry toolkit.

## Random incremental construction (Ch 9.1)

Insert sites in **random order**. Backward analysis: the cost of the last insertion equals the structural change if that site were deleted from the final structure; each of the `n` sites is equally likely to be last.

Typical: expected `O(n log n)` convex hull, Delaunay, trapezoidal map.

## Convex hulls, duality, halfspaces (Ch 9.2–9.4)

Clarkson–Shor / Seidel incremental hull. Duality: hulls ↔ halfspace intersections. Random permutation again.

## Delaunay / trapezoids / BSP (Ch 9.5–9.7)

Delaunay = lower convex hull of lifted points. Trapezoidal decomposition of a planar map: expected query `O(log n)`, expected size `O(n)`. Binary space partitions: random auto-partition (ties back to Ch 1).

## Diameter (Ch 9.8)

Randomised diameter of a planar point set; prune-and-search with random sampling.

## Random sampling (Ch 9.9)

A random sample `R` of size `r` from an arrangement of `n` objects **ε-nets / cuttings**: the sample's conflict graph has size `O(n)` in expectation and, w.h.p., every region is cut by `O((n/r) log r)` objects. This is the geometric form of “a sample represents the population.”

## Linear programming (Ch 9.10)

Seidel / Clarkson–Sharir randomised LP in fixed dimension `d`: expected `O(d! n)` or better (Clarkson’s `O(d² n + d^{O(d)})`). Random permutation of constraints; when the last constraint is violated, recurse on the optimum of the prefix (which lies on the new hyperplane).

Subexponential algorithms (Sharir–Welzl) are the 1990s state; Motwani presents the incremental view.

## Johnson–Lindenstrauss (Hermes, not a Motwani theorem)

A random `k`-dimensional projection with `k = O(ε^{-2} log n)` preserves all pairwise Euclidean distances among `n` points to factor `(1±ε)` w.h.p. Proof: each distance is a sum of subgaussians → Chernoff/Hoeffding + union bound over `n²` pairs. Use for TF-IDF skill-index approximate similarity (user application 1).

## Hermes

- Incremental index builds: randomise insertion order to avoid pathological trees.
- Approximate nearest skill: JL projection, then exact cosine in `k` dimensions.
