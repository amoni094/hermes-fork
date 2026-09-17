# Introduction

## Core Idea
Shannon states the engineering problem of communication as reproducing at one point either exactly or approximately a message selected at another point. Semantic meaning is declared irrelevant; what matters is that the actual message is one selected from a set of possible messages, and the system must be designed for every possible selection.

## Key Concepts
- **Fundamental problem of communication**: “reproducing at one point either exactly or approximately a message selected at another point.”
- **Semantic irrelevance**: “These semantic aspects of communication are irrelevant to the engineering problem.”
- **Information as selection**: if the set of messages is finite and equally likely, the information produced by choosing one is any monotonic function of the size of the set; Hartley already chose the logarithm.
- **Logarithmic measure**: used throughout, including when statistics of the message and continuous ranges of messages force a generalization of Hartley’s definition.
- **Bit**: if the log base is 2, units are binary digits, “or more briefly bits, a word suggested by J. W. Tukey.” Base 10 gives decimal digits (~3.32 bits); base e gives natural units. Change of base is multiplication by log_b a.
- **Five-part system** (Fig. 1): information source, transmitter, channel, receiver, destination. Noise source is shown acting on the signal in the channel.
- **Discrete / continuous / mixed**: discrete = message and signal are sequences of discrete symbols (telegraphy); continuous = both treated as continuous functions (radio, television); mixed = both appear (PCM speech).

## Key Results
- Reasons for the logarithm: (1) engineering parameters (time, bandwidth, number of relays) vary linearly with log of the number of possibilities; (2) it matches intuition (two punched cards have twice the storage of one); (3) limiting operations are simple in log form.
- A device with two stable positions stores one bit; N such devices store N bits because 2^N states give log2(2^N) = N.
- Discrete case is treated first: it applies to computing machines and telephone exchanges, and “forms a foundation for the continuous and mixed cases.”
- The paper extends Nyquist and Hartley by including noise in the channel, savings from the statistical structure of the original message, and the nature of the final destination.

## Key Equations
- log2 M = log10 M / log10 2 ≈ 3.32 log10 M
- N two-state devices store N bits: log2 2^N = N

## Significance
This introduction separates information from meaning, fixes the bit as the unit, and draws the canonical block diagram that later work still uses. Everything that follows — entropy, capacity, coding theorems — is a quantitative theory of selection among alternatives under statistical structure and noise.

## Connects To
- Sec 1: first quantitative object is noiseless discrete channel capacity.
- Sec 6: entropy axiomatizes the logarithmic measure of choice.
- Sec 11–13: noise, previously postponed, becomes the central discrete problem.
- Sec 18–29: continuous and mixed systems via ensembles of functions.
