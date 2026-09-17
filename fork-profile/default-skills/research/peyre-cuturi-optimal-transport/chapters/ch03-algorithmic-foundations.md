# Chapter 3 — Algorithmic Foundations

## Core Idea
The Kantorovich OT problem is a linear program (LP) with special network structure. This structure enables specialized algorithms — network simplex, dual ascent, Hungarian, auction — that are far faster than general LP solvers. Complexity is O(n³) in the worst case, better with structure.

## Frameworks Introduced

### 3.1 The Kantorovich LP
Cast as standard LP:
```
min_{p ≥ 0} c^T p    subject to A p = [a; b]
```
where p ∈ R^{nm} is column-stacked P, A encodes row/column sum constraints.

**Dual LP**:
```
max_{h} [a; b]^T h    subject to A^T h ≤ c
```
which splits as: `LC(a,b) = max_{(f,g) ∈ R(C)} ⟨f,a⟩ + ⟨g,b⟩`

### 3.2 C-Transforms
Optimize dual in single variable: freeze f, set g = f^C (C-transform):
```
(f^C)_j = min_{i} (C_{ij} - f_i)
(g^{C̄})_i = min_{j} (C_{ij} - g_j)
```
**Key property**: f^{CC̄} ≥ f (monotone), f^{CC̄C} = f^C (idempotent after one more transform)

### 3.3 Complementary Slackness
Primal P⋆ and dual (f⋆, g⋆) are optimal iff:
```
P⋆_{ij} (C_{ij} - f⋆_i - g⋆_j) = 0  for all (i,j)
```
i.e., mass flows only where dual constraint is tight.

### 3.4 Vertices of the Transportation Polytope
- Vertices of U(a,b) = basic feasible solutions (BFS)
- Each BFS has ≤ n+m-1 nonzero entries
- Graph G(P): bipartite, nodes = sources+targets, edges = support of P
- **Key**: G(P) is a forest (acyclic) for BFS

### 3.5 Network Simplex
Primal simplex adapted for transportation structure:
1. Initialize with a BFS P (e.g., NW corner rule)
2. Compute complementary dual (f,g) via tree traversal
3. Find violating edge (i,j): f_i + g_j > C_{ij}
4. Add edge to G, find/update cycle, augment flow
5. Repeat until dual feasible

**Complexity**: O((n+m) nm log(n+m) log((n+m)||C||_∞)) [Tarjan 1997]

### 3.6 Dual Ascent Methods
Maintain feasible dual, improve primal via max-flow:
- Start from feasible (f,g) ∈ R(C)
- Identify "balanced" edges (tight constraints) → build bipartite graph
- Run max-flow on balanced subgraph
- If flow < 1: use labeling to find ascent direction (S, S')
- Update (f,g) ← (f,g) + ε(1_S, -1_{S'})
- Hungarian algorithm = special case for uniform marginals

### 3.7 Auction Algorithm
Market-price interpretation:
- Goods = target bins j, buyers = source bins i
- Prices g_j bid up at each iteration
- Each buyer i chooses highest-margin target: j⋆ = argmin_j (C_{ij} - g_j)
- Converges in O(n²/δ) where δ = auction bid increment

## Key Concepts
- **NW corner rule**: greedy BFS initialization (not optimal, used as starting point)
- **Degenerate pivot**: violating edge added but no flow change (G is still forest)
- **Reduced cost**: C_{ij} - f_i - g_j; negative ⟹ primal improvement possible
- **Network flow**: OT is a minimum-cost flow problem on bipartite graph

## Mental Models
- Network simplex = specialized LP simplex that maintains forest structure in the primal
- Dual ascent = find market prices for transport such that no buyer overpays
- Tree traversal = efficient way to compute dual prices from primal support

## Anti-patterns
- Using general-purpose LP solvers for OT (100-1000× slower than network simplex)
- Forgetting redundancy: n+m constraints but rank n+m-1 (one is redundant)
- Running naive O(n!) assignment when LP is available

## Code Examples
```python
# Network Simplex via scipy (wraps efficient C implementation)
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import minimum_spanning_tree

# For small problems: use scipy.optimize.linprog with network structure hint
# For large problems: use POT (Python Optimal Transport) library
import ot

def emd(a, b, C):
    """Earth mover's distance via network simplex."""
    return ot.emd(a, b, C)  # calls COIN-BC or network simplex

def emd2(a, b, C):
    """OT cost only (not the plan)."""
    return ot.emd2(a, b, C)

# NW corner rule (initialization)
def nw_corner(a, b):
    n, m = len(a), len(b)
    P = np.zeros((n, m))
    i, j = 0, 0
    a_rem, b_rem = a.copy(), b.copy()
    while i < n and j < m:
        flow = min(a_rem[i], b_rem[j])
        P[i, j] = flow
        a_rem[i] -= flow; b_rem[j] -= flow
        if a_rem[i] == 0: i += 1
        else: j += 1
    return P
```

## Reference Tables

| Algorithm | Type | Complexity | Best For |
|---|---|---|---|
| Network Simplex | Primal LP | O(n²m log n·log nC) | General discrete OT |
| Hungarian | Dual ascent | O(n³) | Square uniform matching |
| Auction | Price iteration | O(n²/δ) | Parallel, approximate |
| Sinkhorn (Ch 4) | Entropic approx | O(n²/ε²) | GPU, large-scale |

## Worked Example
**2×2 problem**: a=[0.5,0.5], b=[0.5,0.5], C=[[0,2],[3,0]]
- NW init: P=[[0.5,0],[0,0.5]], cost=0
- This is already optimal (diagonal coupling has cost 0)
- Dual: f=[0,0], g=[0,0]; check C_{12}-f_1-g_2=2≥0, C_{21}-f_2-g_1=3≥0 ✓

## Key Takeaways
1. OT LP has special network structure → specialized algorithms 100-1000× faster
2. Optimal primal P has ≤ n+m-1 nonzeros (sparse solution)
3. Dual variables (f,g) have economic interpretation as transport prices
4. Network simplex is the algorithm of choice for exact discrete OT
5. Sinkhorn (Ch 4) trades exactness for scalability to GPU computation

## Connects To
- Ch 2: LP formulation derived from Kantorovich relaxation
- Ch 4: Sinkhorn bypasses LP entirely via entropic approximation
- Ch 5: semi-discrete OT uses C-transforms for stochastic gradient
