# Chapter 11: Key Management and the Public-Key Revolution

## Core Idea
Private-key cryptography requires a secure channel to exchange keys — a circular dependency. Diffie-Hellman key exchange breaks this by enabling two parties to agree on a shared secret over a public channel. This led to the public-key revolution (Diffie, Hellman, RSA, 1976-1978).

## Key Concepts
- **Key distribution problem**: secure channel needed to share key; but key is needed for secure channel
- **Key Distribution Center (KDC)**: trusted third party issues session keys; single point of failure; Kerberos uses this
- **Diffie-Hellman (DH) key exchange**: public parameters (g, p); Alice sends A = g^a mod p; Bob sends B = g^b mod p; shared secret S = g^{ab} mod p
  - Security: CDH assumption (computing g^{ab} from g^a, g^b is hard)
  - Not authenticated: vulnerable to man-in-the-middle; authentication needed (certificates or pre-shared keys)
- **Authenticated DH**: include signatures or MACs on DH values using long-term keys to prevent MITM
- **ECDH (Elliptic Curve DH)**: same protocol on elliptic curve group; P-256, Curve25519 are standard curves
- **Public-key cryptography paradigm**: encryption key (public) ≠ decryption key (private); no pre-shared secret needed
- **Forward secrecy (PFS)**: use ephemeral DH keys per session; compromise of long-term key doesn't expose past sessions; TLS 1.3 mandates this

## Mental Models
- DH is "shared secret from public values": both sides derive the same secret without ever transmitting it
- KDC centralizes trust; public-key distributes trust via mathematics
- Forward secrecy: "burn the key after use"; past sessions protected even after long-term key compromise

## Key Takeaways
1. DH solves the key distribution problem without a pre-shared secret channel
2. DH is not authenticated; always authenticate DH exchanges with signatures (TLS) or PKI
3. ECDH on Curve25519 is the modern default; provides 128-bit security with 256-bit keys
4. Forward secrecy (ephemeral DH) should be mandatory in new protocols

## Connects To
- **Ch 9**: CDH/DDH assumptions underlie DH security
- **Ch 12**: Public-key encryption as an alternative to DH key exchange
- **Ch 13**: Digital signatures authenticate DH; TLS 1.3 uses both
