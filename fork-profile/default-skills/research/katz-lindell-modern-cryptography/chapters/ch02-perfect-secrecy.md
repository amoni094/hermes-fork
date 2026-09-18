# Chapter 2: Perfectly Secret Encryption

## Core Idea
Perfect secrecy — where ciphertext reveals zero information even to an unbounded adversary — is achievable only when the key is at least as long as the message, making it impractical for most applications. This motivates the computational relaxation in Chapter 3.

## Frameworks Introduced
- **Perfect Secrecy (Shannon)**: For all m₀, m₁, c: Pr[Enc_k(m₀) = c] = Pr[Enc_k(m₁) = c]
  - When to use: Absolute secrecy requirements (cryptographic protocols, OTP streams) where key length is not a constraint
  - How: XOR message with truly random key of equal length (One-Time Pad)
- **The Adversarial Indistinguishability Experiment**: Adversary chooses m₀, m₁; receives Enc_k(m_b) for unknown b; outputs b'. Scheme is secure if Pr[b' = b] ≤ 1/2
  - When to use: As a template for defining any encryption security notion
  - How: Identify the adversary's capability, define the experiment, bound advantage

## Key Concepts
- **Perfect secrecy**: No information about plaintext is leaked by ciphertext, unconditionally
- **One-Time Pad (OTP)**: c = m ⊕ k where |k| = |m| and k is truly uniform; perfectly secret
- **Shannon's theorem**: Encryption scheme is perfectly secret iff |K| ≥ |M|
- **Key reuse vulnerability**: Using OTP key twice: c₁ ⊕ c₂ = m₁ ⊕ m₂; reveals XOR of plaintexts
- **Indistinguishability**: Formal game-based definition of security; adversary cannot distinguish encryptions
- **Information-theoretic security**: Secure even against computationally unbounded adversary

## Mental Models
- Think of the OTP as the upper bound: any computationally secure scheme with short keys is a relaxation
- The indistinguishability game is the canonical template — every security notion in modern crypto is a variant
- "Perfect secrecy" ≠ "practical secrecy": OTP requires secure key distribution of equal size to the message

## Anti-patterns
- **Reusing OTP keys**: Catastrophic; reveals XOR of plaintexts. Never reuse a stream cipher key with the same IV
- **Mistaking semantic security for OTP**: Computational security schemes are not information-theoretically secure

## Worked Example
Adversary's attack on two-time OTP:
- Sender encrypts m₁ and m₂ with the same key k: c₁ = m₁ ⊕ k, c₂ = m₂ ⊕ k
- Adversary computes c₁ ⊕ c₂ = m₁ ⊕ m₂
- If m₁ is English text, m₁ ⊕ m₂ has enough structure to recover both messages via frequency analysis
- Defense: never reuse a key — use a fresh key or a nonce-based scheme (Ch 3.6.4)

## Key Takeaways
1. OTP is the only practically deployed perfectly secret scheme; its main limitation is key length
2. Shannon's theorem shows perfect secrecy requires |K| ≥ |M|; this is the lower bound on key material
3. Key reuse completely breaks OTP security; this flaw recurs in stream ciphers
4. The indistinguishability game defined here becomes the template for EAV, CPA, CCA security in Ch 3

## Connects To
- **Ch 3**: Relaxes to computational security to overcome the key-length limitation
- **Ch 4**: HMAC provides integrity that OTP lacks (OTP is malleable)
- **Shannon 1948**: Shannon proved the OTP lower bound in his foundational paper
