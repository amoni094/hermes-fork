# Chapter 12: Public-Key Encryption

## Core Idea
Public-key encryption enables confidential communication without a pre-shared key: any party can encrypt to a public key, but only the private key holder can decrypt. El Gamal (CDH/DDH-based) and RSA-OAEP are the canonical schemes; hybrid encryption (KEM/DEM) is the practical standard.

## Key Concepts
- **Public-key encryption = (Gen, Enc, Dec)**: Gen produces (pk, sk); Enc_pk(m) → c; Dec_sk(c) → m
- **IND-CPA (public-key)**: adversary sees pk; cannot distinguish Enc_pk(m₀) from Enc_pk(m₁)
- **IND-CCA (public-key)**: adversary gets decryption oracle (except challenge); much stronger; required for real protocols
- **El Gamal encryption**: pk = (G, g, q, h = g^x); sk = x; Enc(m) = (g^r, h^r · m); Dec: divide by (g^r)^x
  - IND-CPA under DDH assumption; not CCA-secure
- **RSA-OAEP**: RSA encryption with Optimal Asymmetric Encryption Padding; IND-CCA in ROM; PKCS #1 v2 standard
- **Plain RSA (textbook RSA)**: m^e mod N; deterministic; not IND-CPA; vulnerable to many attacks; never use directly
- **Hybrid encryption (KEM/DEM)**: use PKE to encapsulate symmetric key (KEM); use symmetric cipher for data (DEM)
  - Efficient: only small KEM ciphertext is public-key encrypted; bulk data uses fast symmetric encryption
  - KEM: Gen(1^n) → (pk, sk); Encaps(pk) → (k, c); Decaps(sk, c) → k
- **DHIES/ECIES**: integrated DH encryption scheme; Encaps using DH; DEM using AES-GCM; provides CCA security in ROM

## Reference Table: Public-Key Encryption Schemes

| Scheme | Assumption | CPA? | CCA? | Notes |
|---|---|---|---|---|
| Plain RSA | RSA | No | No | Never use directly |
| El Gamal | DDH | Yes | No | Use with KEM/DEM |
| RSA-OAEP | RSA + ROM | Yes | Yes | PKCS #1 v2; industry standard |
| ECIES | CDH/DDH + ROM | Yes | Yes | Elliptic curve; compact keys |

## Key Takeaways
1. Never use plain (textbook) RSA; always use OAEP padding or a KEM
2. Hybrid encryption (KEM+DEM) is the practical standard; PKE encrypts only the key
3. El Gamal is CPA but not CCA; combine with authenticated symmetric encryption for CCA
4. RSA-2048 or ECDH P-256 for KEM; AES-256-GCM for DEM

## Connects To
- **Ch 5**: AES-GCM as DEM component in hybrid encryption
- **Ch 9**: RSA and DDH assumptions
- **Ch 13**: Signatures authenticate who sent the public-key encrypted message
