# Section 10: Discussion and Examples

## Core Idea
Ideal encoding is statistical matching of source to channel, analogous to impedance matching. Exact match is generally impossible, but Theorem 9 says it can be approximated as closely as desired. Long delay is the price of matching probabilities to sequence lengths.

## Key Concepts
- **Matching analogy**: “In order to obtain the maximum power transfer from a generator to a load, a transformer must in general be introduced so that the generator as seen from the load has the load resistance.” The encoder should make the source, as seen from the channel, have the same statistical structure as the max-entropy source on the channel (Theorem 8).
- **Efficiency**: actual transmission rate / C, equal to actual entropy of channel symbols / maximum possible entropy.
- **Delay**: “ideal or nearly ideal encoding requires a long delay in the transmitter and receiver.” In the noiseless case the delay’s main function is matching probabilities to sequence lengths. For a good code, log(1/p)/T − C must be small for all but a small fraction of long messages.
- **Choosing to ignore statistics**: a machine computing digits of π produces a definite sequence, entropy zero, “no channel is required” — one could compute π at the destination. If that is impractical, treat the digits as random (any sequence of 0–9). Similarly one may use only letter frequencies of English, not all structure: then the relevant source is the first-order approximation, and its entropy sets necessary and sufficient C.

## Key Results
**Example 1.** Alphabet A,B,C,D with probabilities 1/2, 1/4, 1/8, 1/8, independent.

H = −(1/2 log 1/2 + 1/4 log 1/4 + 2·(1/8 log 1/8)) = 7/4 bits per symbol.

Shannon–Fano code (exactly achieving the limit):

- A → 0
- B → 10
- C → 110
- D → 111

Average length = (1/2)·1 + (1/4)·2 + (2/8)·3 = 7/4. Coded bits are equiprobable, so H = 1 bit per binary symbol; time-basis entropies match. Maximum entropy on four symbols is log 4 = 2, so relative entropy = 7/8. Mapping 00,01,10,11 back onto A',B',C',D' compresses the original alphabet by 7/8.

**Example 2.** Binary source, P(A)=p, P(B)=q, p ≪ q.

H = −p log p − (1−p) log(1−p) ≈ p log(e/p) as p → 0.

A fairly good 0–1 code: send a special sequence (0000) for rare A, then a binary count of following B’s, deleting numbers that contain the special sequence. As p → 0, with special-sequence length properly adjusted, the coding approaches ideal.

## Key Equations
- efficiency = (actual rate)/C = H_channel / C
- good code: log(1/p)/T ≈ C
- Example 1: H = 7/4, relative entropy 7/8
- rare-event: H ~ p log(e/p)

## Significance
The matching picture and the exact 7/4-bit code are the pedagogical core of noiseless coding. The π remark distinguishes logical entropy (zero for a computable sequence) from the engineering decision to treat a sequence as random. Partial use of statistics is formalized as: take the maximum-entropy source subject to the constraints one is willing to exploit.

## Connects To
- Theorem 8–9: matching and the C/H limit.
- Sec 7: relative entropy and redundancy.
- Sec 14: leftover source redundancy, not removed in matching, helps combat noise (English on telegraph).
