# Glossary — Introduction to Modern Cryptography (Katz & Lindell)

**AES (Advanced Encryption Standard)** — 128-bit block cipher; Rijndael SPN; 10/14 rounds for 128/256-bit keys; hardware-accelerated; industry standard (Ch 7)

**Adversary** — an entity trying to break a cryptographic scheme; modeled as PPT (probabilistic polynomial-time) algorithm (Ch 1, Ch 3)

**Asymptotic security** — security defined for all sufficiently large security parameter n; adversary success ≤ negl(n) (Ch 3)

**Authenticated Encryption (AE)** — scheme achieving both CPA-security (confidentiality) and EUF-CMA (integrity); equivalent to CCA-security (Ch 5)

**Birthday bound** — expected collision after O(2^{n/2}) evaluations of an n-bit function; use n=256 for 128-bit collision security (Ch 6)

**Blinding** — technique to prevent timing/side-channel attacks by randomizing intermediate computations (Ch 12)

**Block cipher** — keyed pseudorandom permutation on fixed-size blocks; AES, 3DES, DES (Ch 7)

**CBC-MAC** — chained block cipher MAC; iterates F_k over message blocks; secure for fixed-length messages (Ch 4)

**CBC mode** — cipher block chaining; c_i = F_k(m_i ⊕ c_{i-1}); IND-CPA with random IV; not CCA-secure (Ch 3)

**CCA-security (IND-CCA2)** — security against chosen-ciphertext attacks; adversary has decryption oracle; cannot decrypt challenge ciphertext (Ch 5)

**CDH (Computational Diffie-Hellman)** — given (g, g^a, g^b), compute g^{ab}; believed hard (Ch 9, Ch 11)

**ChaCha20** — stream cipher based on ARX; no S-boxes; used with Poly1305 in TLS 1.3 (Ch 7)

**Chosen-plaintext attack (CPA)** — adversary has encryption oracle; IND-CPA requires randomized encryption (Ch 3)

**Ciphertext** — encrypted output of Enc_k(m); transmitted over insecure channel (Ch 1)

**Collision resistance** — infeasible to find x ≠ x' with H(x) = H(x') for any PPT adversary (Ch 6)

**Commitment scheme** — com = H(r || m); binding (collision resistance) + hiding (preimage resistance); revealed by (com, r, m) (Ch 6)

**Computational indistinguishability** — two distributions D₀, D₁ are computationally indistinguishable if no PPT distinguisher has non-negligible advantage (Ch 8)

**Concrete security** — (t, ε)-security: no adversary running time t succeeds with probability > ε (Ch 3)

**CPA-security (IND-CPA)** — indistinguishability under chosen-plaintext attacks; the minimum practical security notion (Ch 3)

**CTR mode** — counter mode; Enc_k(m) = (ctr, F_k(ctr) ⊕ m₁ || F_k(ctr+1) ⊕ m₂ || ...); parallelizable; IND-CPA (Ch 3)

**DDH (Decisional Diffie-Hellman)** — distinguish (g^a, g^b, g^{ab}) from (g^a, g^b, g^c); strictly stronger than CDH (Ch 9)

**Decrypt** — Dec_k(c) → m; recover plaintext from ciphertext using key k (Ch 1)

**DES (Data Encryption Standard)** — 56-bit key; effectively broken; Feistel network (Ch 7)

**Diffie-Hellman key exchange** — A = g^a, B = g^b; shared secret S = g^{ab}; secure under CDH; needs authentication (Ch 11)

**Digital signature** — (Gen, Sign, Vrfy); Sign_sk(m) → σ; Vrfy_pk(m, σ) → 0/1; public-key analogue of MAC (Ch 13)

**Discrete logarithm (DLP)** — given g^a in cyclic group, find a; believed hard; basis of DH/DSA/ECDSA (Ch 9)

**Domain extension** — technique to apply fixed-length primitive (PRF, MAC) to arbitrary-length inputs; Merkle-Damgård, CBC-MAC (Ch 4, Ch 6)

**ECDH / ECDSA** — elliptic curve versions of DH and DSA; P-256, Curve25519; 256-bit key → 128-bit security (Ch 9, Ch 13)

**EAV-security** — eavesdropper security; passive adversary; indistinguishability of single encryption; equivalent to semantic security (Ch 3)

**El Gamal encryption** — pk = g^x; Enc(m) = (g^r, g^{xr} · m); IND-CPA under DDH (Ch 12)

**Encrypt-then-MAC (EtM)** — encrypt first, MAC the ciphertext; provably achieves authenticated encryption (Ch 5)

**EUF-CMA** — existential unforgeability under chosen-message attack; MAC/signature security notion (Ch 4, Ch 13)

**Factoring assumption** — given N = pq for large primes p, q; hard to factor N (Ch 9)

**Fiat-Shamir heuristic** — converts interactive ZK proof to non-interactive signature; replace verifier challenge with H(commitment || message) (Ch 13)

**Forward secrecy (PFS)** — use ephemeral DH per session; past sessions safe even if long-term key compromised (Ch 11)

**GCM (Galois/Counter Mode)** — AES-CTR + GHASH polynomial MAC; authenticated encryption standard (Ch 5)

**Goldreich-Levin theorem** — for any OWF f, ⟨x, r⟩ mod 2 is a hardcore predicate of f'(x,r) = (f(x), r) (Ch 8)

**Hard-core predicate** — B(x) is hard to predict given f(x) alone; used to build PRG from OWF (Ch 8)

**Hash function** — H: {0,1}* → {0,1}^n; deterministic; collision-resistant in practice; SHA-256, SHA-3 (Ch 6, Ch 7)

**HMAC** — H((k ⊕ opad) || H((k ⊕ ipad) || m)); EUF-CMA MAC; immune to length-extension; RFC 2104 (Ch 4, Ch 6)

**Homomorphic encryption** — Enc(m₁) ○ Enc(m₂) = Enc(m₁ ⊕ m₂); compute over encrypted data; Paillier (additive) (Ch 15)

**Hybrid encryption (KEM/DEM)** — PKE encapsulates symmetric key (KEM); symmetric cipher encrypts data (DEM); efficient (Ch 12)

**Information-theoretic security** — secure against unbounded adversaries; perfect secrecy is information-theoretic (Ch 2)

**IV (Initialization Vector)** — random nonce prepended to ciphertext in CBC/CTR mode; never reuse with same key (Ch 3)

**KEM (Key Encapsulation Mechanism)** — public-key primitive that outputs a symmetric key and its encapsulation; used in hybrid encryption (Ch 12)

**Kerckhoffs' principle** — security relies only on key secrecy, not algorithm secrecy (Ch 1)

**Key derivation (HKDF)** — HMAC-based key derivation; extract randomness from source then expand to desired length (Ch 6)

**Key space (K)** — set of all possible keys; size 2^n for n-bit keys (Ch 1)

**Length-extension attack** — Merkle-Damgård vulnerability: given H(m), can compute H(m || pad || m'); use HMAC or SHA-3 to avoid (Ch 6)

**MAC (Message Authentication Code)** — (Gen, Mac, Vrfy); provides message integrity; EUF-CMA secure (Ch 4)

**Malleable encryption** — ciphertexts can be modified to predictably change plaintext; stream ciphers are malleable; AE prevents this (Ch 4, Ch 5)

**Merkle tree** — binary tree of hashes; root authenticates all leaves; O(log t) proof of inclusion (Ch 6)

**Merkle-Damgård transform** — iterative compression function extension; SHA-1, SHA-2 use this; vulnerable to length extension (Ch 6)

**Negligible function** — negl(n); decays faster than any inverse polynomial; models "practically zero" probability (Ch 3)

**One-time pad (OTP)** — c = m ⊕ k; |k| = |m|; k uniform; perfectly secret; impractical (Ch 2)

**One-way function (OWF)** — easy to compute, hard to invert; minimal assumption for private-key crypto (Ch 8)

**Padding-oracle attack** — attacker queries decryption oracle for padding validity; recovers plaintext byte-by-byte; breaks CBC + MAC-then-Encrypt (Ch 5)

**Paillier encryption** — additively homomorphic PKE; composite residuosity assumption (Ch 15)

**Perfectly secret** — Pr[Enc_k(m₀) = c] = Pr[Enc_k(m₁) = c] for all m₀, m₁, c; OTP achieves this (Ch 2)

**Plaintext** — original message m; input to encryption (Ch 1)

**Poly1305** — Carter-Wegman polynomial MAC over GF(2^130 - 5); used with ChaCha20 in TLS 1.3 (Ch 4)

**PPT (probabilistic polynomial-time)** — efficient computation model; honest parties and adversaries modeled as PPT (Ch 3)

**Preimage resistance** — given h, hard to find x with H(x) = h; weaker than collision resistance (Ch 6)

**PRF (pseudorandom function)** — F_k: {0,1}^n → {0,1}^n; indistinguishable from truly random function (Ch 3, Ch 8)

**PRG (pseudorandom generator)** — G: {0,1}^n → {0,1}^{l(n)}; output indistinguishable from uniform; l(n) > n (Ch 3, Ch 8)

**PRP (pseudorandom permutation)** — PRF that is also a bijection; AES is a PRP (Ch 3, Ch 8)

**Proof by reduction** — show security of Π by reducing hardness of P to breaking Π; P hard → Π secure (Ch 3)

**RSA assumption** — given (N, e, y), hard to find x with x^e ≡ y (mod N) (Ch 9)

**RSA-OAEP** — RSA with Optimal Asymmetric Encryption Padding; IND-CCA in ROM; PKCS #1 v2 (Ch 12)

**Schnorr signature** — (R, s) where R = g^r, s = r + H(R||m)·x; EUF-CMA in ROM under DLP (Ch 13)

**Secret sharing (Shamir)** — split secret into n shares via polynomial; any k shares reconstruct; <k shares: nothing revealed (Ch 15)

**Security parameter (n)** — integer controlling security level; key length typically n bits (Ch 3)

**Semantic security** — no partial information about plaintext leaks to PPT adversary; equivalent to EAV-security (Ch 3)

**SHA-3 (Keccak)** — sponge construction; immune to length-extension; NIST standard (Ch 7)

**SHA-256** — Merkle-Damgård + Davies-Meyer; 256-bit output; 128-bit collision security; most widely deployed (Ch 7)

**Shor's algorithm** — quantum algorithm; factors N and computes DLP in poly(log N) time; breaks RSA, DH, ECDSA (Ch 14)

**Sigma protocol** — 3-round ZK protocol: commit → challenge → respond; Schnorr ID is canonical example (Ch 13)

**Stream cipher** — keystream generator XORed with message; ChaCha20, RC4 (deprecated); stateful PRG (Ch 3, Ch 7)

**Tag (t)** — short authenticator output by MAC_k(m); typically 256 bits for HMAC-SHA256 (Ch 4)

**Threshold encryption** — decrypt only when k-of-n parties cooperate; based on secret sharing (Ch 15)

**TLS (Transport Layer Security)** — uses ECDH key exchange + ECDSA certificates + AES-GCM; TLS 1.3 mandates PFS (Ch 13)

**Zero-knowledge proof (ZK)** — prove knowledge of witness without revealing it; Schnorr ID is ZK proof of DLP knowledge (Ch 13)
