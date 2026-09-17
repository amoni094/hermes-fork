# Section 16: The Channel Capacity in Certain Special Cases

## Core Idea
For a memoryless noisy channel given by transition probabilities p_{ij} = Prob(receive j | send i), Shannon writes the Lagrange system for the maximizing input Pi, then evaluates C in two tractable families: (i) channels with the same outgoing (and incoming) transition pattern at every symbol; (ii) channels whose symbols partition into groups that noise never confuses.

## Key Concepts
- **Memoryless channel**: successive symbols independently perturbed; matrix p_{ij}.
- **Symmetric-type examples** (Fig. 12): “each input symbol has the same set of probabilities on the lines emerging from it, and the same is true of each output symbol.” Then Hx(y) is independent of the input distribution.
- **Isolated groups**: noise never maps a symbol of one group to another group; each group is a subchannel of capacity C_n.

## Key Results
**General Lagrange system.** Maximize

−∑_{i,j} Pi p_{ij} log(∑_k Pk p_{kj}) + ∑_{i,j} Pi p_{ij} log p_{ij}

subject to ∑ Pi = 1. This yields

∑_j p_{sj} log ( p_{sj} / ∑_i Pi p_{ij} ) = μ    (s = 1, 2, …)

Multiplying by Ps and summing shows μ = C. If h_{st} is the inverse of p_{sj} (when it exists), ∑_s h_{st} p_{sj} = δ_{tj}, then

Pi = ∑_t h_{it} exp( −C ∑_s h_{st} + ∑_{s,j} h_{st} p_{sj} log p_{sj} )

with C chosen so ∑ Pi = 1. Then C is the capacity and the Pi are the capacity-achieving input probabilities.

**Uniform-line case.** Hx(y) = −∑ pi log pi independent of input (pi = transitions from any input). Max H(y) = log m with m output symbols, achieved by making outputs equiprobable (here: equiprobable inputs). Therefore

C = log m + ∑ pi log pi

Fig. 12a: C = log 4 − log 2 = log 2 (achieved using only the 1st and 3rd symbols).

Fig. 12b: C = log 4 − (2/3) log 3 − (1/3) log 6 = log(4 / (3 · 2^{1/3}))

Fig. 12c: C = log 3 − (1/2) log 2 − (1/3) log 3 − (1/6) log 6

**Isolated groups.** Let C_n be the capacity (bits per second) of group n used alone. For best use of the whole set,

P_n = 2^{C_n} / ∑ 2^{C_n}

and within a group the distribution is as if those were the only symbols. Total capacity:

C = log ∑_n 2^{C_n}

## Key Equations
- C = Max_P [ H(y) − Hx(y) ] = Max_P [ −∑ Pi p_{ij} log ∑ Pk p_{kj} + ∑ Pi p_{ij} log p_{ij} ]
- uniform type: C = log m + ∑ pi log pi
- groups: C = log ∑ 2^{C_n},  P_n ∝ 2^{C_n}

## Significance
The uniform-line formula is the discrete ancestor of “symmetric channel” capacity (including the BSC: m=2, p=(1−p_e, p_e) gives C = 1 − h(p_e)). The group formula is log-sum-exp combination of parallel unused-confusion components — max-entropy allocation across disjoint alphabets.

## Connects To
- Sec 12–13: definition and operational meaning of C.
- Sec 15: a channel that is not fully symmetric; solved by the same Lagrange method.
- Sec 17: another case where C is explicit and a perfect code exists.
- Modern: BSC C = 1 − h(p); BEC C = 1 − p (erasure as a third output; not drawn here, but the group/symmetric formulas cover it).
