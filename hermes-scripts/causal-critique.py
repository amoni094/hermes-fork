#!/usr/bin/env python3
"""Causal-critique library for post_tool_call hooks.

Import: critique_causal_structure(trace, skill_id) -> {confounds, backdoors, interventions}.
Cron accumulation lives in causal-critique-accumulate.py (not this file).
"""
from __future__ import annotations

import json
import sys
from typing import Any

_CONFOUND = ("because", "if", "only if", "correlation", "confound", "spurious")
_BACKDOOR = ("back-door", "backdoor", "collider", "common cause", "d-separation")
_INTERVENTION = ("intervention", "interventional", "do(", "randomized", "controlled", "rct")


def _hits(text: str, needles: tuple) -> list:
    low = (text or "").lower()
    return [n for n in needles if n in low]


def critique_causal_structure(trace: Any, skill_id: str = "") -> dict:
    """Inspect a CoT/tool trace. Outcome-only traces score 0 on interventions."""
    if isinstance(trace, dict):
        parts = [
            str(trace.get("reasoning") or ""),
            str(trace.get("content") or ""),
            json.dumps(trace.get("tool_calls") or [], default=str),
            str(trace.get("tool_name") or ""),
        ]
        text = "\n".join(parts)
    else:
        text = str(trace or "")
    conf = _hits(text, _CONFOUND)
    back = _hits(text, _BACKDOOR)
    inter = _hits(text, _INTERVENTION)
    return {
        "skill_id": str(skill_id or ""),
        "confounds": conf,
        "backdoors": back,
        "interventions": inter,
        "confound_detected": bool(conf),
        "backdoor_detected": bool(back),
        "intervention_valid": bool(inter),
    }


def _self_test() -> None:
    a = critique_causal_structure(
        "We randomized assignment and ran a controlled intervention; no back-door.",
        "demo",
    )
    b = critique_causal_structure("The model scored 0.9 accuracy.", "demo")
    assert a["intervention_valid"] and not b["intervention_valid"]
    assert a["interventions"]
    print("[causal-critique] --self-test PASS")


def main(argv: list | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--self-test" in argv:
        _self_test()
        return 0
    print("library only; use causal-critique-accumulate.py for cron", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
