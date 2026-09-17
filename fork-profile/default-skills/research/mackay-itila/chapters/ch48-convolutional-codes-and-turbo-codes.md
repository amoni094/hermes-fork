# Chapter 48: Convolutional Codes and Turbo Codes

## Core Idea
Convolutional codes generate t by streaming source bits s through a linear shift-register filter (taps described in octal). They are described by generators and by trellises; decoded by Viterbi (min-sum) or forward–backward (sum–product) on that trellis (Ch 25). Systematic recursive and nonsystematic nonrecursive encoders can define the *same* code. Turbo codes concatenate two convolutional encoders with an interleaver and decode by iterative message passing — the practical sparse-graph breakthrough alongside LDPC.

## Key Concepts
- **Shift register / constraint length**: memory k bits (MacKay’s figures use k=7). Rate 1/2: one s in, two t out per clock.
- **Three flavours**: (1) systematic nonrecursive — one output is s itself, no feedback; (2) nonsystematic nonrecursive — two tap sets, no feedback; (3) systematic recursive — feedback taps, one output is s.
- **Octal taps**: e.g. 353₈ = binary 011101011 written on the delay line. Recursive codes as ratios (247/371)₈.
- **Code equivalence**: filters 48.1b and 48.1c produce the same set of codewords; source mappings differ. Recursive systematic is preferred in turbo because the encoder is invertible and weight-1 inputs become infinite-weight outputs.
- **Trellis**: state = register contents; edges labelled by s/t. Decoding = inference on this chain.
- **Turbo code**: two RSC encoders, one fed a permuted s; iterative BCJR exchange of extrinsic LLRs through the interleaver.

## Frameworks and Methods
- **Four descriptions of codes**: G, H, trellis, (algebra — omitted). Convolutional codes live in generator-filter + trellis language.
- **Viterbi**: min-sum / max-likelihood path on the trellis (Ch 16, 25).
- **BCJR / forward–backward**: bit-wise APP P(s_t|r) — the algorithm turbo needs.
- **Why recursive for turbo**: a low-weight s would make a low-weight convolutional codeword in a nonrecursive systematic encoder (s itself is sent); feedback spreads 1-bits so the parallel concatenation has huge typical distance.
- **MacKay’s placement**: this chapter “follows tightly on Ch 25”. Algebraic convolutional theory is deliberately skipped.

## Key Equations
- t^{(b)}_n = ∑_κ g_κ z_{n−κ}  (mod 2)   (feedforward taps)
- Recursive: register input = s + ∑ feedback taps · state
- Rate R = 1/2 for the running examples (one in, two out)
- Trellis: state s_{t+1} = A s_t + b u_t  over GF(2)
- Viterbi: min_{paths} ∑ branch metrics
- BCJR: α_t(s) β_t(s) give P(state, edge | r)
- Turbo iteration: L_ext^{(1)} → π → decoder 2; L_ext^{(2)} → π^{−1} → decoder 1
- APP LLR = L_channel + L_prior + L_extrinsic

## Algorithms and Techniques
**Encode (rate 1/2 RSC)**
1. Load s_n, mix with feedback taps into the register.
2. Output (s_n, parity from feedforward taps).
3. Optionally terminate the trellis (flush memory).

**Decode a convolutional code**
1. Build the trellis for the known taps.
2. Viterbi if you want the ML codeword; BCJR if you want bit APPs.

**Turbo decode**
1. Decoder 1: BCJR with channel LLRs + incoming extrinsic from decoder 2 (deinterleaved).
2. Subtract the prior/channel to emit new extrinsic; interleave.
3. Decoder 2 similarly; iterate ~8–20 times.
4. Hard-decide on final APP.

## Anti-patterns
- **Using a nonrecursive systematic encoder inside turbo** — poor distance, error floor.
- **Viterbi inside turbo** — you need *soft* extrinsic, i.e. BCJR or a soft-output Viterbi with care.
- **Forgetting trellis termination** in short blocks (rate loss vs extra errors).
- **Algebra-first teaching** that never reaches iterative decoding.

## Key Takeaways
1. Convolutional codes are linear filters; trellises make them inferable in linear time in N.
2. Octal tap notation is how you read a real standard.
3. Recursive systematic ≡ nonsystematic nonrecursive as *codes*, not as *encoders*.
4. Turbo = two conv nets + interleaver + iterative BCJR.
5. Together with LDPC (Ch 47) this is how you actually approach capacity.

## Connects To
- **Ch 25**: trellises, forward–backward, Viterbi.
- **Ch 16**: min-sum / path counting.
- **Ch 47**: the other sparse-graph family; same iterative decoding religion.
- **Ch 49**: RA codes as even simpler turbo-like graphs.
