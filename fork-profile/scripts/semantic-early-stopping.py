#!/usr/bin/env python3
"""Convergence detector for iterative LLM agent loops.

Cosine similarity of consecutive iteration outputs (TF bag-of-words).
Mean of the last 3 pair similarities above 0.92 -> CONVERGED.
Stable similarity deltas (< 0.02 for 3 consecutive pair-gaps) after a
high similarity -> CYCLING. Otherwise CONTINUING.

Kill test:
    result = check_convergence([s]*5)
    assert result['status'] == 'CONVERGED'
"""

from __future__ import annotations

import json
import math
import re
import sys
from collections import Counter
from typing import Any

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

CONVERGENCE_THRESHOLD = 0.92
CYCLING_DELTA = 0.02
HIGH_SIM = 0.50
TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall((text or "").lower())


def _vocab(*token_lists: list[str]) -> list[str]:
    seen: dict[str, None] = {}
    for tokens in token_lists:
        for tok in tokens:
            seen.setdefault(tok, None)
    return list(seen)


def _tf(tokens: list[str], vocab: list[str]) -> list[float]:
    counts = Counter(tokens)
    return [float(counts.get(w, 0.0)) for w in vocab]


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    if HAS_NUMPY:
        va = np.asarray(a, dtype=float)
        vb = np.asarray(b, dtype=float)
        na = float(np.linalg.norm(va))
        nb = float(np.linalg.norm(vb))
        if na == 0.0 or nb == 0.0:
            return 0.0
        return float(np.clip(np.dot(va, vb) / (na * nb), 0.0, 1.0))
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return max(0.0, min(1.0, dot / (na * nb)))


def _pair_similarity(a: str, b: str) -> float:
    ta, tb = _tokenize(a), _tokenize(b)
    vocab = _vocab(ta, tb)
    if not vocab:
        return 1.0 if (not (a or "").strip() and not (b or "").strip()) else 0.0
    return _cosine(_tf(ta, vocab), _tf(tb, vocab))


def check_convergence(
    outputs: list[str],
    convergence_threshold: float = CONVERGENCE_THRESHOLD,
) -> dict[str, Any]:
    """Return CONVERGED | CYCLING | CONTINUING for a sequence of loop outputs."""
    texts = [str(x) if x is not None else "" for x in (outputs or [])]
    n = len(texts)
    sims: list[float] = []
    for i in range(1, n):
        sims.append(_pair_similarity(texts[i - 1], texts[i]))

    status = "CONTINUING"
    last_sim = sims[-1] if sims else 0.0

    if len(sims) >= 3:
        mean_last3 = sum(sims[-3:]) / 3.0
        if mean_last3 > convergence_threshold:
            status = "CONVERGED"
        elif len(sims) >= 4 and max(sims) >= HIGH_SIM:
            deltas = [abs(sims[i] - sims[i - 1]) for i in range(len(sims) - 3, len(sims))]
            if len(deltas) == 3 and all(d < CYCLING_DELTA for d in deltas):
                status = "CYCLING"

    return {
        "status": status,
        "similarity_history": [round(s, 6) for s in sims],
        "last_similarity": round(last_sim, 6),
        "n_iterations": n,
    }


def layer1_demo() -> None:
    identical = ["the same loop output about routing weights"] * 5
    conv = check_convergence(identical)
    assert conv["status"] == "CONVERGED", conv
    assert conv["n_iterations"] == 5
    assert all(s >= 0.99 for s in conv["similarity_history"])

    diverse = [
        "alpha wolf hunts in the snowy forest at dawn",
        "banana bread recipe needs extra ripe fruit",
        "quantum chromodynamics lattice gauge theory notes",
        "municipal parking ordinance section fourteen b",
        "ukulele chord chart for beginners in c major",
    ]
    cont = check_convergence(diverse)
    assert cont["status"] == "CONTINUING", cont
    assert all(0.0 <= s <= 1.0 for s in cont["similarity_history"])

    # Controlled overlap: cosine(a,b)=0.5, stable across A-B-A-B so deltas=0.
    a = "alpha beta gamma delta epsilon zeta"
    b = "alpha beta gamma one two three"
    cycling_outputs = [a, b, a, b, a]
    cyc = check_convergence(cycling_outputs)
    assert cyc["status"] == "CYCLING", cyc
    assert len(cyc["similarity_history"]) == 4

    empty = check_convergence([])
    assert empty["status"] == "CONTINUING"
    assert empty["n_iterations"] == 0

    one = check_convergence(["only one"])
    assert one["status"] == "CONTINUING"

    print(
        f"[layer1] PASS — identical={conv['status']} diverse={cont['status']} "
        f"cycling={cyc['status']} last_cyc={cyc['last_similarity']}"
    )


def main() -> None:
    if "--layer1" in sys.argv:
        layer1_demo()
        return
    demo = ["step one draft", "step one draft refined", "step one draft refined"]
    print(json.dumps(check_convergence(demo), indent=2))


if __name__ == "__main__":
    main()
