# Section 3: The Series of Approximations to English

## Core Idea
Shannon constructs sample texts from successively richer stochastic models of English (27-symbol alphabet: 26 letters + space) to show that “a sufficiently complex stochastic process will give a satisfactory representation of a discrete source.”

## Key Concepts
- **Zero-order**: symbols independent and equiprobable. Sample begins: XFOML RXKHRJFFJUJ ZLPWCFWKCYJ…
- **First-order**: independent symbols with English letter frequencies. Sample: OCRO HLI RGWR NMIELWIS…
- **Second-order**: digram structure as in English. Sample: ON IE ANTSOUTINYS ARE T INCTORE ST BE S DEAMY…
- **Third-order**: trigram structure. Sample: IN NO IST LAT WHEY CRATICT FROURE BIRS GROCID…
- **First-order word approximation**: jump to word units rather than tetragrams; words independent with English frequencies. Sample: REPRESENTING AND SPEEDILY IS AN GOOD APT OR COME…
- **Second-order word approximation**: correct word-transition probabilities, no further structure. Sample: THE HEAD AND IN FRONTAL ATTACK ON AN ENGLISH WRITER THAT THE CHARACTER OF THIS POINT IS THEREFORE ANOTHER METHOD…

## Key Results
Resemblance to ordinary English increases at each step. Structure is “reasonably good out to about twice the range that is taken into account in their construction.” Four-letter sequences from a digram process can usually be fitted into good sentences; in the second-order word sample, sequences of four or more words can be placed in sentences without strained constructions. The ten-word fragment “attack on an English writer that the character of this” is “not at all unreasonable.”

**Construction method.** First two samples used random-number tables plus frequency tables. For (3)–(6) Shannon uses a book-sampling trick: open a book at random, pick a letter; open another page, scan until that letter appears, record the next letter; repeat. Analogous for trigrams and words. “It would be interesting if further approximations could be constructed, but the labor involved becomes enormous at the next stage.”

Letter/digram/trigram frequencies: Fletcher Pratt, *Secret and Urgent* (1939). Word frequencies: G. Dewey, *Relative Frequency of English Speech Sounds* (1923).

## Key Equations
None new; the models are the n-gram processes of Sec 2.

## Significance
This is the first explicit demonstration that language is a stochastic process with long-range statistical structure, and that entropy (later) should be estimated from successively longer blocks. It is the ancestor of n-gram language models. Shannon later (Sec 7) uses these approximations to estimate English redundancy at roughly 50%.

## Connects To
- Sec 2: formal n-gram hierarchy.
- Sec 7: FN is the entropy of the N-th order approximation; English redundancy ≈ 50% from these approximations plus deletion and cryptographic methods.
- Sec 10: if one uses only letter frequencies, the relevant source is the first-order approximation; its entropy sets the required C.
