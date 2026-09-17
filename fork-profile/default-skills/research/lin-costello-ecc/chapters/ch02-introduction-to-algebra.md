# Chapter 2: Introduction to Algebra

## Core Idea
Algebraic coding (cyclic, BCH, Reed–Solomon, finite-geometry) is arithmetic in finite fields. This chapter supplies groups, fields, GF(2^m) construction, polynomials, vector spaces, and matrices at an engineering level — enough to build and decode those codes without a full algebra course.

## Key Concepts
- **Group**: set closed under an associative binary operation, with identity and inverses. Commutative (abelian) if a*b = b*a. Order = number of elements.
- **Field**: set with addition and multiplication that is an abelian group under +, the nonzero elements form an abelian group under ×, and multiplication distributes over addition.
- **Finite field GF(q)**: exists iff q = p^m for prime p (characteristic) and integer m ≥ 1. Unique up to isomorphism.
- **Prime field GF(p)**: integers {0,…,p−1} with mod-p addition and multiplication.
- **Extension GF(2^m)**: polynomials of degree < m over GF(2), modulo an irreducible polynomial of degree m.
- **Primitive element α**: generator of the multiplicative group GF(q)*; every nonzero field element is a power of α. Order of α is q−1.
- **Minimal polynomial φ(X) of β**: monic polynomial of least degree over the base field having β as a root. Irreducible. Conjugates β, β^2, β^4, … (in char 2) share the same minimal polynomial.
- **Primitive polynomial**: minimal polynomial of a primitive element; generates GF(2^m) as a shift-register field.
- **Vector space V_n over GF(2)**: all binary n-tuples with componentwise mod-2 addition and scalar multiplication.
- **Linear independence / basis / dimension**: k independent vectors span a k-dimensional subspace (a linear code).
- **Matrix rank, generator G, parity-check H**: G has k independent rows spanning the code; H has n−k independent rows orthogonal to every codeword: v H^T = 0.

## Frameworks and Methods
- **Modulo-m addition group**: {0,…,m−1} under remainder of i+j divided by m. Identity 0; inverse of i is m−i.
- **Modulo-p multiplication group** (p prime): {1,…,p−1}. Inverses exist by Bézout: ai + bp = 1 ⇒ a is inverse of i mod p.
- **Construct GF(2^m)**:
  1. Choose an irreducible p(X) of degree m over GF(2).
  2. Let α be a root: p(α) = 0.
  3. Represent elements as a0 + a1 α + … + a_{m−1} α^{m−1}, ai ∈ {0,1}.
  4. Add componentwise mod 2; multiply as polynomials then reduce mod p(X).
  5. If p(X) is primitive, powers 1, α, α^2, …, α^{2^m−2} exhaust all nonzero elements (useful as a log table).
- **Euclid’s algorithm**: gcd of polynomials (later: RS/BCH key equation). Divide, remainder, repeat; also yields inverses.
- **Binary field arithmetic**: + is XOR; × is AND for bits, polynomial multiply for GF(2^m). Characteristic 2 ⇒ a+a = 0, (a+b)^2 = a^2 + b^2 (freshman’s dream).

## Key Results
- Identity and inverse in a group are unique.
- GF(q) exists ⇔ q is a prime power.
- Multiplicative group of GF(q) is cyclic of order q−1. Hence X^{q−1} − 1 = ∏_{β ≠ 0} (X − β).
- Every element of GF(2^m) is a root of X^{2^m} − X.
- Degree of the minimal polynomial of α^i over GF(2) equals the size of the cyclotomic coset of i modulo 2^m − 1.
- A k × n matrix G of rank k has an (n−k) × n matrix H of rank n−k with G H^T = 0. Row space of G is the null space of H.

## Algorithms and Techniques
**Build a log/antilog table for GF(2^m)** (used in every BCH/RS decoder):
1. Pick primitive p(X) = 1 + p1 X + … + X^m.
2. Set α^0 = 1. Recur α^{i+1} = X · α^i mod p(X) (a linear-feedback shift register).
3. Store vector representation of α^i (antilog) and the discrete log of each vector.
4. Multiply via logs: a·b = antilog(log a + log b mod 2^m−1); add in vector form.

**Worked example (GF(2))**: G = {0,1} under XOR is the additive group; {1} under AND is the multiplicative group. This is the alphabet of all binary codes.

**Worked example (modulo-5)**: additive group Table 2.1; multiplicative group {1,2,3,4} with 2·3 = 1 so 2^{-1} = 3.

**Polynomial division**: to test if g(X) divides v(X), run the LFSR with taps of g; remainder 0 ⇔ codeword (Ch 5).

## Anti-patterns
- **Using a reducible p(X) to “build GF(2^m)”**: the quotient is not a field (zero divisors).
- **Confusing primitive polynomial with any irreducible**: not every irreducible is primitive; non-primitive generators do not give a single-cycle LFSR of period 2^m−1.
- **Integer arithmetic in the field**: 1+1 = 0 in GF(2), not 2. Never carry.
- **Forgetting conjugates**: the minimal polynomial of α includes α^2, α^4, …; BCH generator degree is not always mt if even powers share polynomials.
- **Treating matrices over reals**: rank, inverses, and orthogonality are over GF(2) (or GF(q)).

## Key Takeaways
1. All algebraic ECC is finite-field linear algebra plus polynomial rings.
2. GF(2^m) is implemented as m-bit vectors with XOR add and log-table multiply, or as an LFSR.
3. Primitive elements and minimal polynomials are the raw material of BCH/RS generators.
4. A linear code is a subspace: specified equally by G (encoder) or H (syndrome).
5. Characteristic 2 simplifies squares and makes subtraction = addition.

## Connects To
- **Ch 3**: linear codes as subspaces; G and H from this chapter’s matrix theory.
- **Ch 5–7**: generator polynomials over GF(2) and GF(q); roots in GF(2^m).
- **Ch 8, 17**: finite geometries over GF(2^s) for majority-logic and LDPC constructions.
