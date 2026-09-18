# Ch 2 Getting Started — loop invariants and first algorithms

## Insertion sort (2.1)

1-indexed: for i = 2 to n, insert A[i] into the sorted prefix A[1..i-1] by shifting larger keys right.

**Loop invariant** (start of each for-i iteration): A[1..i-1] contains the original A[1..i-1] keys, now sorted.

- **Initialization:** i = 2, prefix is one element — sorted.
- **Maintenance:** the inner while shifts the prefix to make a hole, then writes key; after i++, the new prefix is sorted.
- **Termination:** loop ends when i = n+1; substituting into the invariant, A[1..n] is the original array sorted. Hence the algorithm is correct.

A loop-invariant proof is induction that *stops* at termination (unlike infinite induction). Nested loops need their own invariants (the inner while of insertion sort is the formal maintenance argument).

## Analyzing algorithms (2.2)

Count primitive operations as a function of n. Best / worst / average can differ. Insertion sort: Θ(n) already sorted, Θ(n²) reverse-sorted. RAM model, ignore machine constants when comparing *order of growth*.

## Merge sort (2.3)

Divide at midpoint (Θ(1)), two recursive sorts, merge in Θ(n). Recurrence T(n) = 2T(n/2) + Θ(n) → Θ(n lg n) by Master theorem (Ch 4). Recursion tree: lg n + 1 levels, each Θ(n), total Θ(n lg n). Floors/ceilings on odd n do not change the Θ bound.

## Coding implication

A non-trivial loop without a stated invariant has no correctness argument. Tests that only check the final array miss init and single-iteration failures.
