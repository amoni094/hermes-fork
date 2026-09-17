# Chapter 13: Suboptimum Decoding of Convolutional Codes

## Core Idea
When constraint length is too large for 2^ν Viterbi (ν ≳ 10–15), drop optimality: sequential decoding (ZJ stack, Fano) searches only promising paths, and majority-logic decoding of self-orthogonal convolutional codes uses orthogonal checks like Ch 8. You trade a small SNR loss and a variable-complexity / erasure behavior for exponential savings in average work.

## Key Concepts
- **Sequential decoding**: tree (not fully expanded trellis) search guided by a Fano-like metric that rewards likely branches and *penalizes length*, so the decoder does not idle on long garbage paths.
- **Fano metric** (for DMC): μ = log P(r|v) − R_0' n_bits, with bias near the code rate. Essential: unbiased ML path metric grows, wrong paths eventually decline.
- **ZJ (Zigangirov–Jelinek) stack algorithm**: keep a stack of partial paths ordered by metric; extend the top; reinsert children. Average computation is small below the cutoff rate.
- **Fano algorithm**: depth-first with a moving threshold T; tighten/loosen T, move forward/backward. Constant memory (only the current path), more threshold fiddling than ZJ.
- **Cutoff rate R_0**: sequential decoding’s practical limit. For R > R_0, average stack operations blow up (Pareto distribution of computation). For AWGN/BPSK, R_0 is a few tenths of a dB to ~1 dB from capacity depending on rate — historically “the” limit before turbo codes.
- **Buffer overflow / erasure**: sequential decoders have random delay. A finite buffer ⇒ occasional failures, declared as erasures (good for concatenated outer RS).
- **Codes for sequential decoding**: large d_free is not enough; need rapidly growing column distance (distance profile) so wrong paths are rejected early. Complementary generators, ODP (optimum distance profile) codes.
- **Convolutional majority-logic**: self-orthogonal / orthogonalizable codes (Massey, Robinson–Bernstein, Iwadare). J orthogonal checks on each information bit; t_ML = ⌊J/2⌋. Threshold decoding.

## Frameworks and Methods
- **When sequential beats Viterbi**: ν = 20–40 (space / legacy), software decoders, or when an outer code absorbs erasures. Not for modern low-latency 5G (use LDPC).
- **ZJ stack loop**:
  1. Push the root (metric 0).
  2. Pop best path. If it has reached the end, output it.
  3. Else extend by 2^k branches, compute Fano metrics, push.
  4. Optional: drop paths whose metric is worse than best_complete − Δ (not in original ZJ).
- **Fano loop** (conceptual): look at the next node. If μ ≥ T, move forward (maybe tighten T). If not, back up; if cannot, lower T by a step Δ and try again.
- **MLG convolutional decode**:
  1. Form J syndrome checks orthogonal on information bit u_{t−m}.
  2. Majority → estimate e_{t−m}; correct that bit; subtract its contribution from the syndrome register (feedback, like analog of Meggitt).
  3. Very high speed, small ν not required; d_free typically modest.

## Key Results
- Average number of sequential operations per decoded bit is bounded for R < R_0 and grows as (1−R/R_0)^{−α} (Pareto). Above R_0, mean is infinite.
- Computational variability, not BER, is the design constraint. Size the input buffer for a target overflow probability (10^{-3}…10^{-6}).
- Error probability of sequential decoding, when it finishes, is close to ML; almost all loss is overflow erasures.
- Fano and ZJ are similar in average work; ZJ is faster in software (heap), Fano uses O(ν) memory.
- Self-orthogonal codes: any two generators share at most one tap, so checks are automatically orthogonal. Easy construction, not the best d_free.
- MLG convolutional performance is far from Viterbi of the same rate (several dB), but the decoder is an LFSR + majority gate.

## Algorithms and Techniques
**Fano metric for BSC(p), rate R**:
μ = (correct bits)·log(1−p) + (errors)·log p − n R log 2
(or a scaled integer version). Wrong long paths go negative.

**ZJ implementation tips**:
- Store the stack as a heap keyed by metric.
- Quantize metrics so many paths share a key (bucket stack) — Jelinek’s original.
- A “sync” or tail forces termination so the algorithm cannot run forever.

**Majority-logic (threshold) decoder**:
Syndrome s(D) = r(D) h(D). Orthogonal checks = selected shifts of s. Vote; if 1, add the error polynomial into the feedback to clean future checks (otherwise error propagation).

**Code search for sequential**:
Maximize the column-distance function d_c(L) for small L first (ODP), then d_free. Tables of complementary convolutional codes in the chapter.

## Anti-patterns
- **Running sequential at R ≈ C**: you wanted turbo/LDPC; sequential will overflow constantly. Stay below R_0 with margin.
- **Unbounded stack in real time**: always a timeout → erasure, never an infinite search.
- **Viterbi-style traceback thinking**: sequential outputs the first path that reaches the end with no competitor in the stack; there is no ACS survivor set.
- **MLG without feedback correction**: uncorrected bits pollute later orthogonal checks (error propagation).
- **Using NASA (171,133) with sequential**: that code is optimized for Viterbi d_free, not for ODP; pick sequential-specific generators.

## Key Takeaways
1. Sequential decoding ≈ ML with random complexity, practical only below cutoff rate R_0.
2. ZJ = best-first + stack; Fano = depth-first + threshold; same philosophy.
3. Overflow erasures are a feature for RS concatenation (Forney’s classical NASA stack).
4. Convolutional MLG is the high-speed, low-gain option (self-orthogonal codes).
5. After 1993 (turbo), sequential decoding left mainstream wireless; still relevant for huge-ν archival / educational analysis.

## Connects To
- **Ch 8**: block majority-logic; same orthogonality idea.
- **Ch 11–12**: the codes and the ML benchmark sequential is approximating.
- **Ch 15**: concatenated RS + sequential inner was a standard 1970s–80s NASA stack.
- **Ch 16–17**: turbo/LDPC made R_0 obsolete as an operating limit — you can now operate between R_0 and C.
