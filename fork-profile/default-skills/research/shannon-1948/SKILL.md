---
name: shannon-1948
description: "Knowledge base from Shannon's foundational 1948 paper 'A Mathematical Theory of Communication'. Use when applying core information theory: entropy, channel capacity, source/channel coding theorems, or referencing Shannon's original formulations."
related_skills:
  - cover-thomas-eit
  - mackay-itila
  - gallager-itrc
---

# Shannon 1948 — A Mathematical Theory of Communication

Bell System Technical Journal 27 (1948). Notation is Shannon’s: H(x), Hx(y), Hy(x). He does not name “mutual information” or “rate-distortion.” Prefer these files over textbook paraphrases.

- [glossary.md](glossary.md) — definitions, often verbatim
- [theorems.md](theorems.md) — Theorems 1–23 with proof sketches
- [cheatsheet.md](cheatsheet.md) — formulas
- [sections/](sections/) — per-section notes

## Three fundamental theorems

**1. Noiseless source coding (Theorem 9).** Source entropy H bits/symbol, channel capacity C bits/s: one can encode to send (C/H − ε) source symbols/s; not more than C/H. Entropy is the bits needed per symbol.

**2. Noisy channel coding (Theorem 11).** Capacity C = Max[H(x) − Hy(x)]. If source rate H ≤ C, some code has arbitrarily small error (or equivocation). If H > C, equivocation is at least H−C; none smaller. One number C: below it, Pe→0; above it, Nature “takes payment” in uncertainty.

**3. Rate relative to a fidelity (Theorem 21).** Continuous sources need a tolerance ρ. Rate R1 = Min I(x;y) subject to E[ρ]=v1. If R1 ≤ C, encode to fidelity arbitrarily near v1; if R1 > C, impossible. Distortion may be imposed at the transmitter (PCM-like quantizing).

AWGN specialization (Theorem 17): C = W log((P+N)/N). White source, RMS error N (Theorem 22): R = W1 log(Q/N).

## Key formulas

```
H = −∑ pi log pi
H(x,y) = H(x)+Hx(y) = H(y)+Hy(x)
R = H(x)−Hy(x) = H(y)−Hx(y) = H(x)+H(y)−H(x,y)
C = Max R
C_noiseless = lim (log N(T))/T
C_AWGN = W log((P+N)/N)
N1 = exp(2H′)/(2π e)                 entropy power
W log((P+N1)/N1) ≤ C ≤ W log((P+N)/N1)
f(t) = ∑ f(n/2W) sinc(2Wt−n)         Theorem 13
R1 = Min I  s.t. E[ρ]=v1
R_white,RMS = W1 log(Q/N)
```

BSC (from Sec 16 symmetric formula): C = 1 − h(p). Hamming (7,4) meets C=4/7 on the 7-bit single-error channel.

## Section index

**Introduction** — information as selection; bit (Tukey); five-part diagram; discrete/continuous/mixed.

**Part I — Discrete noiseless systems**
| File | Sec | Topic |
|------|-----|--------|
| [sec00-introduction.md](sections/sec00-introduction.md) | — | Problem statement |
| [sec01-discrete-noiseless-channel.md](sections/sec01-discrete-noiseless-channel.md) | 1 | C = lim log N(T)/T |
| [sec02-discrete-source-of-information.md](sections/sec02-discrete-source-of-information.md) | 2 | Stochastic sources |
| [sec03-approximations-to-english.md](sections/sec03-approximations-to-english.md) | 3 | n-gram English |
| [sec04-markoff-process.md](sections/sec04-markoff-process.md) | 4 | State graph |
| [sec05-ergodic-and-mixed-sources.md](sections/sec05-ergodic-and-mixed-sources.md) | 5 | Ergodicity |
| [sec06-choice-uncertainty-entropy.md](sections/sec06-choice-uncertainty-entropy.md) | 6 | H = −∑ pi log pi |
| [sec07-entropy-of-information-source.md](sections/sec07-entropy-of-information-source.md) | 7 | AEP, redundancy |
| [sec08-encoding-decoding-operations.md](sections/sec08-encoding-decoding-operations.md) | 8 | Transducers |
| [sec09-noiseless-channel-theorem.md](sections/sec09-noiseless-channel-theorem.md) | 9 | Theorem 9 |
| [sec10-discussion-and-examples.md](sections/sec10-discussion-and-examples.md) | 10 | Matching, codes |

**Part II — Discrete channel with noise**
| File | Sec | Topic |
|------|-----|--------|
| [sec11-noisy-discrete-channel.md](sections/sec11-noisy-discrete-channel.md) | 11 | Noise vs distortion |
| [sec12-equivocation-and-capacity.md](sections/sec12-equivocation-and-capacity.md) | 12 | R, C, Theorem 10 |
| [sec13-noisy-channel-theorem.md](sections/sec13-noisy-channel-theorem.md) | 13 | Theorem 11 |
| [sec14-discussion.md](sections/sec14-discussion.md) | 14 | Existence vs construction; Theorem 12 |
| [sec15-discrete-channel-example.md](sections/sec15-discrete-channel-example.md) | 15 | 3-symbol channel |
| [sec16-capacity-special-cases.md](sections/sec16-capacity-special-cases.md) | 16 | Symmetric / groups |
| [sec17-efficient-coding.md](sections/sec17-efficient-coding.md) | 17 | Hamming (7,4) |

**Part III — Mathematical preliminaries**
| File | Sec | Topic |
|------|-----|--------|
| [sec18-sets-and-ensembles.md](sections/sec18-sets-and-ensembles.md) | 18 | Ensembles, Wiener |
| [sec19-band-limited-ensembles.md](sections/sec19-band-limited-ensembles.md) | 19 | Sampling, 2TW |
| [sec20-entropy-continuous-distribution.md](sections/sec20-entropy-continuous-distribution.md) | 20 | Differential entropy |

**Part IV — Continuous channel**
| File | Sec | Topic |
|------|-----|--------|
| [sec21-entropy-ensemble-of-functions.md](sections/sec21-entropy-ensemble-of-functions.md) | 21 | H′, entropy power |
| [sec22-entropy-loss-linear-filters.md](sections/sec22-entropy-loss-linear-filters.md) | 22 | Theorem 14 |
| [sec23-entropy-sum-of-ensembles.md](sections/sec23-entropy-sum-of-ensembles.md) | 23 | EPI, Theorem 15 |
| [sec24-capacity-continuous-channel.md](sections/sec24-capacity-continuous-channel.md) | 24 | Integral R; Theorem 16 |
| [sec25-average-power-limitation.md](sections/sec25-average-power-limitation.md) | 25 | Theorems 17–19 |
| [sec26-peak-power-limitation.md](sections/sec26-peak-power-limitation.md) | 26 | Theorem 20 |

**Part V — Rate for a continuous source**
| File | Sec | Topic |
|------|-----|--------|
| [sec27-fidelity-evaluation.md](sections/sec27-fidelity-evaluation.md) | 27 | ρ, v = E[ρ] |
| [sec28-rate-relative-to-fidelity.md](sections/sec28-rate-relative-to-fidelity.md) | 28 | Theorem 21 |
| [sec29-calculation-of-rates.md](sections/sec29-calculation-of-rates.md) | 29 | Theorems 22–23 |

**Appendices**
[1 capacity equation](sections/appendix-1-noiseless-capacity.md) · [2 uniqueness](sections/appendix-2-entropy-uniqueness.md) · [3 AEP proofs](sections/appendix-3-source-entropy-proofs.md) · [4 maxent types](sections/appendix-4-maximum-entropy.md) · [5 invariant T](sections/appendix-5-invariant-operators.md) · [6 EPI](sections/appendix-6-entropy-power-inequality.md) · [7 abstract R, dimension rate](sections/appendix-7-abstract-rate.md)

## Topic index

| Need | Go to |
|------|--------|
| Bit, block diagram, semantics | Intro, glossary |
| H = −∑ p log p, axioms | Sec 6, App 2 |
| Typical sets, English redundancy | Sec 7, App 3 |
| Source coding, Shannon–Fano | Sec 9, Theorem 9 |
| Equivocation, I(X;Y) unnamed | Sec 12 |
| Noisy coding, random codes | Sec 13, Theorem 11 |
| BSC / symmetric C | Sec 16, cheatsheet |
| Hamming code | Sec 17 |
| Sampling theorem | Sec 19, Theorem 13 |
| Differential entropy, Gaussian maxent | Sec 20 |
| Entropy power, EPI | Sec 21–23, App 6 |
| AWGN capacity | Sec 25, Theorem 17 |
| Peak power | Sec 26, Theorem 20 |
| Rate-distortion 1948 | Sec 27–29, Theorems 21–23 |
| Data-processing inequality | App 7, Sec 24 |
| Measure-theoretic R | App 7 |

## How to cite Shannon’s wording

- Information is selection among alternatives, not meaning.
- Capacity is Max[H(x)−Hy(x)], also lim log N(T,q)/T.
- “Almost all the systems are arbitrarily close to the ideal.”
- Ideal signals “approximate, in statistical properties, a white noise.”
- Nature takes payment in equivocation for rates above C.
- Justification of H is Theorems 9 and 11, not Theorem 2.
