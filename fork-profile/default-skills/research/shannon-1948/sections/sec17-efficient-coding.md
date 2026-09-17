# Section 17: An Example of Efficient Coding

## Core Idea
A block-noise binary channel admits an exact match to capacity: Hamming’s (7,4) parity-check code corrects every single error in a block of seven and transmits at rate C.

## Key Concepts
- **Channel**: two symbols 0,1; noise acts in blocks of seven. A block is either error-free or has exactly one of the seven positions wrong. These eight possibilities are equally likely.
- **Hamming construction** (credited to R. Hamming): four message bits, three parity bits, syndrome = error location.

## Key Results
C = Max [H(y) − Hx(y)]

= (1/7) [ 7 + (1/8) log(1/8) wait — extraction:

C = (1/7) [ log(2^7) something ]

Paper:
```
C = Max H(y) − Hx(y)
  = (1/7) [ 7 + (1/8)? ]
  = 4/7 bits/symbol
```

Reasoning: each 7-block has 8 equally likely received versions per transmitted word (no error + 7 single errors). Hx(y) per block = log 8 = 3 bits, so per symbol 3/7. If inputs equiprobable among all 2^7 sequences, H(y) is... Actually the channel maps each input to 8 outputs. The output entropy if we use all 2^7 inputs: each output can come from 8 inputs (flip none or one of 7 bits - wait that's the noise model from the input side).

From input x, y is uniform on the Hamming ball of radius 1, size 8. Hx(y) = log 8 = 3 bits/block = 3/7 bits/symbol.

If we use all 128 sequences equally, H(x)=7 bits/block. Need H(y).

Shannon writes:
C = (1/7)[7 − 3]? = 4/7. Yes: if H(y)=H(x) because the map is... not quite.

R = H(y) − Hx(y). If we take equiprobable inputs on all 128, Hx(y)=3 bits/block. The noise is a permutation of a group (add an error vector of weight 0 or 1). Output is uniform on 128 if input is, so H(y)=7, R=7−3=4 bits/block = 4/7 bits/symbol. And Shannon says this is C (the maximum).

**The code.** Block X1…X7. Message symbols X3, X5, X6, X7 chosen freely. Parities:

X4 chosen so α = X4+X5+X6+X7 is even

X2 chosen so β = X2+X3+X6+X7 is even

X1 chosen so γ = X1+X3+X5+X7 is even

On reception compute α,β,γ; even→0, odd→1. The binary number γβα is the subscript of the incorrect Xi (0 means no error).

This corrects all errors the channel can produce, and sends 4 message bits per 7 symbols = 4/7 = C. “Exact matching to a noisy channel is possible.”

## Key Equations
- C = 4/7 bits/symbol
- Hx(y) = (log 8)/7 = 3/7
- rate of the Hamming code = 4/7 = C

## Significance
The first published Hamming code, used by Shannon as the rare case where an explicit, perfect code achieves capacity (because the noise model is exactly the Hamming bound with equality: 2^7 / 8 = 2^4). It is the constructive counterpart to the random-coding existence proof.

## Connects To
- Sec 13–14: existence vs explicit construction; this is one of the “rather trivial cases and certain limiting situations.”
- Sec 12: R = H(y) − Hx(y).
- Later coding theory: perfect codes, Hamming bound, parity-check matrices.
