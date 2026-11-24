#!/usr/bin/env python3
"""RIF (retrieval-induced forgetting) compaction probe fixture.

Anderson/Bjork-style Rp+/Nrp-/Ctrl planting for compaction recall evals.
Stdlib only. No network. No LLM calls.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from typing import Any, Optional

# Four categories, four distinctive tokens each (study + practice + probe).
BANK: dict[str, list[str]] = {
    "FRUIT": ["MANGO-K7", "PAPAYA-Q2", "GUAVA-R9", "LYCHEE-M1"],
    "METAL": ["COBALT-A3", "TUNGSTEN-B4", "NICKEL-C8", "TITANIUM-D5"],
    "BIRD": ["KESTREL-E6", "OSPREY-F1", "HERON-G2", "IBIS-H9"],
    "CODE": ["LAMBDA-J3", "MUTEX-K8", "SOCKET-L4", "FUTURE-N7"],
}
CATS = ("FRUIT", "METAL", "BIRD", "CODE")
FILLER_N = 40


def _item_q(token: str, cat: str) -> str:
    return f"What is the planted {cat} probe token that looks like {token.split('-')[0]}-???"


def plant_rif_transcript(
    seed: int = 7, practise_n: int = 3
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Study all items, retrieve-practise Rp+ only, then 40 fillers.

    Two categories are practised (Rp+/Nrp-); the other two are Ctrl.
    practise_n items per practised category become Rp+; the rest are Nrp-.
    Questions cover Nrp- and Ctrl only (no Rp+).
    """
    rng = random.Random(seed)
    practise_n = max(1, min(int(practise_n), 3))
    cats = list(CATS)
    rng.shuffle(cats)
    practised = cats[:2]
    control = cats[2:]

    roles: list[tuple[str, str, str]] = []  # token, cat, role
    rp_plus: list[tuple[str, str]] = []
    for cat in practised:
        items = list(BANK[cat])
        rng.shuffle(items)
        for tok in items[:practise_n]:
            roles.append((tok, cat, "Rp+"))
            rp_plus.append((tok, cat))
        for tok in items[practise_n:]:
            roles.append((tok, cat, "Nrp-"))
    for cat in control:
        for tok in BANK[cat]:
            roles.append((tok, cat, "Ctrl"))

    msgs: list[dict[str, Any]] = [
        {"role": "system", "content": "You are a test agent in a memory study."},
        {
            "role": "user",
            "content": "Study these category tokens. You will be asked about them later.",
        },
    ]
    # Study phase: every item once.
    for tok, cat, role in roles:
        msgs.append(
            {
                "role": "assistant",
                "content": f"Study item [{cat}/{role}]: the token is {tok}.",
            }
        )
        msgs.append(
            {
                "role": "user",
                "content": f"Acknowledged study of {cat} item {tok}.",
            }
        )
    # Retrieval practice: Rp+ only, repeated.
    for tok, cat in rp_plus:
        msgs.append(
            {
                "role": "user",
                "content": f"Retrieval practice: recall the {cat} token starting "
                f"{tok.split('-')[0]}- . The answer is {tok}.",
            }
        )
        msgs.append(
            {
                "role": "assistant",
                "content": f"Practised Rp+ {cat} token {tok}.",
            }
        )
    for i in range(FILLER_N):
        msgs.append(
            {
                "role": "user" if i % 2 == 0 else "assistant",
                "content": f"Filler turn {i}: unrelated checklist step {i} with padding.",
            }
        )

    questions: list[dict[str, Any]] = []
    for tok, cat, role in roles:
        if role == "Rp+":
            continue
        questions.append(
            {
                "q": _item_q(tok, cat),
                "gold": tok,
                "where": "either",
                "difficulty": "medium",
                "required_in": "either",
                "rif_role": role,
                "rif_cat": cat,
            }
        )
    return msgs, questions


def rif_index(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Recall is mean(score/2) for score in {0,1,2}. RIF_index = recall_Nrp- - recall_Ctrl.

    Kill-test (not asserted in --self-test): shuffle rif_role labels → RIF_index near 0.
    """
    buckets: dict[str, list[float]] = {"Nrp-": [], "Ctrl": []}
    n = 0
    for row in results or []:
        role = str(row.get("rif_role") or "")
        if role not in buckets:
            continue
        try:
            sc = float(row.get("score", 0))
        except (TypeError, ValueError):
            sc = 0.0
        if sc < 0:
            sc = 0.0
        if sc > 2:
            sc = 2.0
        buckets[role].append(sc / 2.0)
        n += 1

    def _mean(xs: list[float]) -> float:
        return (sum(xs) / len(xs)) if xs else 0.0

    rec_nrp = _mean(buckets["Nrp-"])
    rec_ctrl = _mean(buckets["Ctrl"])
    return {
        "recall_Nrp-": rec_nrp,
        "recall_Ctrl": rec_ctrl,
        "RIF_index": rec_nrp - rec_ctrl,
        "n": n,
    }


def _self_test() -> int:
    msgs, questions = plant_rif_transcript()
    blob = "\n".join(str(m.get("content") or "") for m in msgs)
    assert any("Rp+" in str(m.get("content") or "") for m in msgs), "Rp+ not visible"
    # Practised tokens (Rp+) appear as the concrete BANK tokens in text.
    assert "MANGO-K7" in blob or "COBALT-A3" in blob or "KESTREL-E6" in blob or "LAMBDA-J3" in blob
    roles = {q["rif_role"] for q in questions}
    assert roles <= {"Nrp-", "Ctrl"}, roles
    assert "Rp+" not in roles
    assert all(q.get("difficulty") == "medium" for q in questions)
    assert all(q.get("required_in") == "either" for q in questions)
    idx = rif_index([{"rif_role": "Nrp-", "score": 2}, {"rif_role": "Ctrl", "score": 0}])
    assert idx["RIF_index"] == 1.0, idx
    assert idx["recall_Nrp-"] == 1.0 and idx["recall_Ctrl"] == 0.0
    assert idx["n"] == 2
    empty = rif_index([])
    assert empty["n"] == 0 and empty["RIF_index"] == 0.0
    print("self-test ok")
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="RIF compaction probe fixture")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--practise-n", type=int, default=3)
    ap.add_argument("--dump", action="store_true", help="print planted msgs+questions JSON")
    args = ap.parse_args(argv)
    if args.self_test:
        return _self_test()
    msgs, questions = plant_rif_transcript(seed=args.seed, practise_n=args.practise_n)
    if args.dump:
        print(json.dumps({"messages": msgs, "questions": questions}, ensure_ascii=False))
        return 0
    print(json.dumps({"n_msgs": len(msgs), "n_questions": len(questions)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
