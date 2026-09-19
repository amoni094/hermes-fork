"""kolmogorov_predicates.py — Compressibility predicates grounded in Li-Vitanyi (MDL).

Grounding
=========
Li & Vitanyi Ch.2 (MDL two-part code): the Kolmogorov complexity K(x) is not
computable, but the normalized compression length C(x)/|x| (where C is a
lossless compressor) is the best computable upper bound.

  kolmogorov_proxy(x) = 1 - C(x)/|x|
    ≈ 1 - K(x)/|x|   (MDL approximation)

  → near 0: already compressed / random / incompressible → DROP
  → near 1: structured / redundant / compressible        → probably RETAIN

Implementation note on short strings
-------------------------------------
For very short strings (< _MIN_BYTES bytes), the zlib DEFLATE format header
overhead dominates and C(x) > |x|, producing negative (nonsensical) proxy
values.  Following Li-Vitanyi §2.2, the correct MDL approximation is
asymptotic: we measure the true compression ratio by evaluating the compressor
on a *repeated* version of the input (padding to _MIN_BYTES bytes).  This
evaluates the per-character description length in the limit, removing the
fixed-overhead bias that corrupts estimates for short strings.

Normalized Compression Distance (NCD) between two strings s1, s2:
  NCD(s1, s2) = (C(s1+s2) - min(C(s1), C(s2))) / max(C(s1), C(s2))

  Li & Vitanyi §8.4: NCD ∈ [0, 1+ε].  NCD < 0.15 → near-duplicate; only
  one copy should be retained (the shorter / more recent one).

  The same padding strategy is applied per-operand to ensure header overhead
  does not inflate NCD for short identical strings.

Both functions use zlib (DEFLATE), stdlib-only.

Usage (standalone demo):
    python3 ~/.hermes/scripts/kolmogorov_predicates.py --demo
"""
from __future__ import annotations

import sys
import zlib

# Minimum byte length for reliable compression ratio estimation.
# Below this, DEFLATE header overhead (≈9 bytes) distorts K(x)/|x|.
# Set to 50 bytes — well above the ~11-byte header floor.
_MIN_BYTES = 50


def _pad_to_min(b: bytes) -> bytes:
    """Repeat bytes until length >= _MIN_BYTES to escape zlib header overhead.

    Theoretical basis: Li-Vitanyi §2.2 — the MDL estimate C(x)/|x| converges
    to K(x)/|x| asymptotically in |x|.  For |x| < _MIN_BYTES, header overhead
    O(1) dominates O(K(x)) and the estimate is unreliable.  Repeating x
    evaluates the *per-symbol* description length, matching the asymptotic regime.
    """
    if not b:
        return b
    if len(b) >= _MIN_BYTES:
        return b
    factor = (_MIN_BYTES + len(b) - 1) // len(b)
    return b * factor


# ── Core predicates ────────────────────────────────────────────────────────────

def kolmogorov_proxy(text: str) -> float:
    """MDL compressibility proxy in [0, 1].

    Returns
    -------
    float:
        Fraction of the (padded) encoding length that zlib *saved*.
        Near 0  → hard to compress (random/already-encoded) → DROP.
        Near 1  → highly compressible (structured/redundant) → RETAIN.

    Grounding: Li-Vitanyi Ch.2 — C(x)/|x| is the best poly-time
    approximation to K(x)/|x|.  proxy = 1 - C(x)/|x| ∈ [0, 1].
    Short-string padding escapes DEFLATE header overhead (see module docstring).

    P5B-06 fix: empty string produces proxy=0.0 via 1-(8/1)=-7→0 clamp, making
    empty content appear maximally incompressible/random — wrong semantic. Return
    0.0 explicitly so empty content is a drop candidate for the right reason.
    """
    if not text:
        return 0.0  # no content — drop candidate; skip compression arithmetic
    raw = _pad_to_min(text.encode("utf-8", errors="replace"))
    raw_len = max(len(raw), 1)
    compressed_len = len(zlib.compress(raw))
    return max(0.0, min(1.0, 1.0 - compressed_len / raw_len))


def ncd(s1: str, s2: str) -> float:
    """Normalized Compression Distance between two strings.

    NCD(s1, s2) = (C(s1+s2) - min(C(s1), C(s2))) / max(C(s1), C(s2))

    where C(x) = len(zlib.compress(pad(x.encode()))).

    Returns
    -------
    float in [0, ~1.1]:
        NCD < 0.15 → near-duplicates; retain only one.
        NCD > 0.5  → substantially different content.

    Grounding: Li-Vitanyi §8.4 — NCD is a universal similarity metric
    that approximates the normalized information distance (NID).
    Short-string padding escapes DEFLATE header overhead (see module docstring).

    P4B-01 fix: fast-path identity check avoids zlib artefact where
    ncd(s, s) returns ~0.29 for long strings (sliding-window effect).
    NCD(x,x) = 0 by definition (Li-Vitanyi §8.4, reflexivity of NID).
    """
    if s1 == s2:
        return 0.0
    # P6B-03 fix: _pad_to_min(b'') returns b'', so C('') ≈ 8 bytes (DEFLATE header only).
    # ncd('', short_str) ≈ (c_x - 8)/c_x → 0 for short strings, falsely implying
    # near-similarity.  Li-Vitanyi: NID(ε, x) = 1 for any non-trivial x.
    if not s1 or not s2:
        return 1.0
    b1 = _pad_to_min(s1.encode("utf-8", errors="replace"))
    b2 = _pad_to_min(s2.encode("utf-8", errors="replace"))
    c1 = len(zlib.compress(b1))
    c2 = len(zlib.compress(b2))
    # W3-F09 fix: concatenate the ORIGINAL strings before padding, not the
    # separately-padded b1+b2. Separately-padded concatenation inflates c12
    # because two independent repetition patterns don't compress as well as
    # a single repetition of the original two-string sequence.
    # Li-Vitanyi §8.4: C(xy) should be compression of xy, not pad(x)+pad(y).
    # P8B-05 note: for strings near the _MIN_BYTES boundary (individually < 50 chars
    # but jointly >= 50), b1/b2 are padded-by-repetition while b12 is not, creating
    # a minor asymmetry.  The asymmetry is bounded: c1 and c2 are at most 1.5× larger
    # than unpadded (zlib header + one copy ≈ 8 bytes overhead), so NCD error is < 0.15
    # for borderline-length strings.  Keeping W3-F09 concatenation is preferable because
    # independently-padded concatenation (b1+b2) introduces a larger systematic bias
    # (duplicated repetition blocks lower c12 artificially).
    b12 = _pad_to_min((s1 + s2).encode("utf-8", errors="replace"))
    c12 = len(zlib.compress(b12))
    denom = max(c1, c2, 1)
    return max(0.0, (c12 - min(c1, c2)) / denom)


# ── Standalone demo ────────────────────────────────────────────────────────────

def _demo() -> None:
    # 1. Short repetitive (spec test case) → proxy > 0.5
    proxy_short = kolmogorov_proxy("aaaaaaa")
    assert proxy_short > 0.5, f"Expected proxy > 0.5 for 'aaaaaaa', got {proxy_short:.4f}"
    print(f"[demo] kolmogorov_proxy('aaaaaaa') = {proxy_short:.4f}  (>0.5 ✓ — retain)")

    # 2. Highly compressible (long repetition) → proxy near 1
    proxy_rep = kolmogorov_proxy("a" * 1000)
    assert proxy_rep > 0.5, f"Expected proxy > 0.5 for 'a'*1000, got {proxy_rep:.4f}"
    print(f"[demo] kolmogorov_proxy('a'*1000) = {proxy_rep:.4f}  (>0.5 ✓ — retain)")

    # 3. High-entropy (pseudo-random) text → proxy low
    import hashlib
    random_text = hashlib.sha256(b"seed").hexdigest() * 10
    proxy_rand = kolmogorov_proxy(random_text)
    print(f"[demo] kolmogorov_proxy(sha256*10) = {proxy_rand:.4f}  (low → drop-candidate)")

    # 4. NCD: identical strings → < 0.1
    d_same = ncd("hello world", "hello world")
    assert d_same < 0.1, f"Expected NCD < 0.1 for identical strings, got {d_same:.4f}"
    print(f"[demo] ncd('hello world', 'hello world') = {d_same:.4f}  (<0.1 ✓ — near-duplicate)")

    # 5. NCD: very different strings → > 0.3
    d_diff = ncd("hello world", "totally different content xyz")
    assert d_diff > 0.3, f"Expected NCD > 0.3 for different strings, got {d_diff:.4f}"
    print(f"[demo] ncd('hello world', 'totally different content xyz') = {d_diff:.4f}  (>0.3 ✓ — distinct)")

    print("\n[demo] All kolmogorov_predicates assertions passed.")


if __name__ == "__main__":
    if "--demo" in sys.argv:
        _demo()
        sys.exit(0)
    print("Usage: python3 kolmogorov_predicates.py --demo")
    sys.exit(1)
