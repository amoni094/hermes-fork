# Chapter 9: Metric Spaces — General Properties

## Core Idea
Abstracts the key structural properties of ℝ (distance, open sets, convergence, completeness, compactness) to general metric spaces, setting the stage for Banach and Hilbert spaces.

## Key Concepts
- **Metric space (X,d)**: d: X×X → [0,∞) with d(x,y)=0 iff x=y, symmetry, triangle inequality.
- **Open ball**: B(x,r) = {y: d(x,y) < r}. Open sets = unions of open balls.
- **Convergence**: xₙ → x iff d(xₙ,x) → 0. Limits are unique.
- **Cauchy sequence**: d(xₙ,xₘ) → 0 as n,m → ∞. Convergent ⟹ Cauchy. Converse holds in complete spaces.
- **Complete metric space**: Every Cauchy sequence converges.
- **Compact metric space**: Every sequence has a convergent subsequence (sequential compactness = compactness for metric spaces). Equivalent: every open cover has a finite subcover.
- **Totally bounded**: For every ε>0, X is covered by finitely many balls of radius ε. Compact ⟺ complete + totally bounded.
- **Separable**: Contains a countable dense subset.
- **Isometry**: d(f(x),f(y)) = d(x,y) — distance-preserving bijection.

## Key Examples Relevant to Hermes
| Space | Metric | Complete? | Compact? |
|-------|--------|-----------|----------|
| ℝⁿ | Euclidean | Yes | Only bounded closed sets |
| Lp(E), 1≤p≤∞ | ‖f-g‖_p | Yes | No (closed unit ball not compact) |
| C[a,b] | ‖f-g‖_∞ | Yes | No (Arzelà-Ascoli gives subsets) |
| Sequence space ℓ² | Σ|xₙ-yₙ|² | Yes | No |

## Key Takeaways
1. Completeness = "no missing limits." Critical for iterative algorithms (Banach contraction, Cauchy sequence arguments).
2. Compact = "finite-ness in the limit." Every optimization problem on a compact set attains its minimum.
3. Total boundedness + completeness = compactness. Check both when proving a set is compact.
4. All Lp spaces are complete but not compact — infinite-dimensional spaces lose compactness of the unit ball.

## Connects To
- **Ch10**: Three foundational theorems built on metric space structure
- **Ch13**: Banach spaces = complete normed linear spaces = special metric spaces
