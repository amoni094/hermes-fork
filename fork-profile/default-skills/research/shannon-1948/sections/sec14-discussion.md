# Section 14: Discussion

## Core Idea
Theorem 11 is close to an existence proof: following it does not yield a practical code. Good codes place signals so that reasonable noise does not move one closer to another reasonable signal than to the original. Delay now also averages a large noise sample. Theorem 12 recasts C as the growth rate of the largest reliable codebook, matching the noiseless definition of Sec 1.

## Key Concepts
- **Existence vs construction**: “An attempt to obtain a good approximation to ideal coding by following the method of the proof is generally impractical. In fact, apart from some rather trivial cases and certain limiting situations, no explicit description of a series of approximation to the ideal has been found. Probably this is no accident but is related to the difficulty of giving an explicit construction for a good approximation to a random sequence.”
- **Geometry of a good code**: if noise alters the signal “in a reasonable way,” the original is still the nearest reasonable signal. Redundancy must be “introduced in the proper way to combat the particular noise structure involved.”
- **Source redundancy helps if kept**: “any redundancy in the source will usually help if it is utilized at the receiving point.” English on a noiseless telegraph could save ~50% time by encoding; it is not done, so most English redundancy remains in the channel symbols, “allowing considerable noise.” A sizable fraction of letters can be wrong and still reconstructed by context. “This is probably not a bad approximation to the ideal in many cases.”
- **Delay’s second function**: “allowing a large sample of noise to affect the signal before any judgment is made.” Larger samples sharpen statistical assertions.

## Key Results
**Theorem 12.** Let N(T,q) be the maximum number of duration-T signals that can be selected so that, when used equally often and decoded as the most probable cause in the subset, P(incorrect interpretation) ≤ q. Then

lim_{T→∞} [log N(T,q)] / T = C

provided q ≠ 0 or 1.

“No matter how we set our limits of reliability, we can distinguish reliably in time T enough messages to correspond to about CT bits, when T is sufficiently large.” Compare Sec 1: C = lim log N(T)/T with N(T) the number of allowed (noiseless) signals.

## Key Equations
- lim log N(T,q) / T = C    (q ≠ 0,1)
- noiseless analogue: C = lim log N(T)/T

## Significance
Theorem 12 is the operational definition of capacity as the exponential growth rate of packing numbers at any fixed error q ∈ (0,1) — the modern “reliability function at rate C” limit, here only the capacity itself. The English-on-telegraph remark is Shannon’s practical coding theorem: natural language is already a random-like code.

## Connects To
- Sec 1: identical limit form, now with a reliability constraint q.
- Sec 13: Theorem 11.
- Sec 17: an explicit “trivial/limiting” case where a perfect code exists.
- Sec 25: random white-noise codebooks as a continuous analogue of “almost all codes are good.”
