# Chapter 1: Introduction

## Core Idea
Modern cryptography is distinguished from classical cryptography by three principles: formal security definitions, explicit computational hardness assumptions, and mathematical proofs of security — replacing ad-hoc design and intuitive notions of secrecy.

## Frameworks Introduced
- **Kerckhoffs' Principle**: The cipher method must not be required to be secret; security relies solely on key secrecy.
  - When to use: Always — design schemes as if the adversary knows the algorithm
  - How: Make algorithm public; derive security only from key entropy
- **Three Principles of Modern Cryptography**: Formal definitions → Precise assumptions → Proofs of security
  - When to use: Before designing or evaluating any cryptographic scheme
  - How: Define the security experiment first; state hardness assumption explicitly; prove reduction

## Key Concepts
- **Plaintext (m)**: the original message being protected
- **Ciphertext (c)**: encrypted output transmitted over insecure channel
- **Key (k)**: secret shared between communicating parties; all security flows from this
- **Key space (K)**: set of all possible keys; size determines brute-force resistance
- **Encryption scheme**: triple (Gen, Enc, Dec) with correctness Dec_k(Enc_k(m)) = m
- **Private-key (symmetric) setting**: both parties share the same secret key
- **Eavesdropper**: passive adversary monitoring the channel
- **Classical cryptography**: pre-1980s; security by obscurity, no formal definitions

## Mental Models
- Use "What is the attacker's goal?" to define the security experiment before building
- Think of an encryption scheme as (Gen, Enc, Dec) — never elide Gen, which determines key distribution
- The adversary knows the scheme; security comes only from the key

## Anti-patterns
- **Security by obscurity**: hiding the algorithm instead of the key; fails when algorithm is reverse-engineered or leaked
- **Informal security arguments**: "this looks random" without a proof; allows systematic attacks to go undetected
- **Assuming encryption provides integrity**: secrecy and authentication are orthogonal properties

## Worked Example
The Caesar cipher shifts each letter by a fixed amount (key). Breaking it requires only 26 trials — the key space is too small. A Vigenère cipher uses a longer key but is still breakable via Kasiski examination. Modern cryptography's response: define security formally (no PPT adversary learns anything), state an assumption (AES is a PRP), prove the mode of operation achieves the definition.

## Key Takeaways
1. Security = formal definition + proof of reduction to hard problem; intuition alone is insufficient
2. Kerckhoffs' principle is non-negotiable: assume the adversary knows the algorithm
3. Historical ciphers fail because their key spaces are small and their designs are not proved secure
4. The move from classical to modern cryptography was driven by the need for provable security guarantees

## Connects To
- **Ch 2**: Formalizes the "perfect secrecy" definition first raised here
- **Ch 3**: Extends to computational secrecy using PPT model
- **Shannon 1948**: Mathematical foundations of information-theoretic security
