"""Compaction policy matrix.

Each policy is a name -> spec mapping. A spec has:
  ctor:  extra kwargs for ContextCompressor(...)
  attrs: attribute overrides applied after construction (lets us pin
         tail_token_budget and other derived values without touching the
         class)
The runner constructs one compressor per policy and calls
compress(force=True) with the transcript's estimated tokens.
"""
from __future__ import annotations

from typing import Any, Dict

# Window we evaluate against (fable-5 class model).
EVAL_MODEL = "anthropic/claude-fable-5"
EVAL_WINDOW = 1_000_000

POLICIES: Dict[str, Dict[str, Any]] = {
    # Shipping behavior, untouched.
    "current": {
        "ctor": {},
        "attrs": {},
    },
    # Proposed: tail = max(10K, 0.025% ... interpreted as 2.5% of window)
    # capped hard at 25K on a 1M model. protect_last_n stays for message-count
    # floor semantics.
    "tail25k": {
        "ctor": {},
        "attrs": {"tail_token_budget": 25_000},
    },
    # Hard floor variant: minimum viable tail.
    "tail10k": {
        "ctor": {},
        "attrs": {"tail_token_budget": 10_000},
    },
    # Codex posture: nearly no tail; summary carries everything.
    "codex_style": {
        "ctor": {"protect_last_n": 3},
        "attrs": {"tail_token_budget": 2_000},
    },
    # Compaction-v2 lean mode: clamped 2.5% tail + tail tool demotion +
    # verbatim user messages in summary + session_search recovery pointers.
    "lean": {
        "ctor": {"tail_mode": "lean"},
        "attrs": {"_session_id": "eval-session"},
    },
    # Fork: research profile — compress sooner (0.45), smaller tail (22 msgs).
    "fork_research": {
        "ctor": {"threshold_percent": 0.45, "protect_last_n": 22},
        "attrs": {
            "proactive_prune_tokens": 40_000,
            "session_type": "research",
            "importance_biased_prune_enabled": True,
        },
    },
    # Fork: code profile — compress later (0.55), larger tail (28 msgs).
    "fork_code": {
        "ctor": {"threshold_percent": 0.55, "protect_last_n": 28},
        "attrs": {
            "proactive_prune_tokens": 28_000,
            "session_type": "code",
            "importance_biased_prune_enabled": True,
        },
    },
    # Fork: mixed profile — midpoint (0.50, 20 msgs).
    "fork_mixed": {
        "ctor": {"threshold_percent": 0.50, "protect_last_n": 20},
        "attrs": {
            "proactive_prune_tokens": 32_000,
            "session_type": "mixed",
            "importance_biased_prune_enabled": True,
        },
    },
    # Classifier-routed arm: starts from lean baseline, then auto-selects fork profile
    # based on session_classifier heuristic. Tests end-to-end classifier routing benefit.
    "classified": {
        "ctor": {"threshold_percent": 0.50, "protect_last_n": 20},
        "attrs": {
            "_session_id": "eval-session",
            "proactive_prune_tokens": 32_000,
            "importance_biased_prune_enabled": True,
            "use_classifier": True,
        },
    },
    # Lean + research threshold compound arm.
    "lean_fork_research": {
        "ctor": {"threshold_percent": 0.45, "protect_last_n": 22},
        "attrs": {
            "_session_id": "eval-session",
            "proactive_prune_tokens": 40_000,
            "session_type": "research",
            "importance_biased_prune_enabled": True,
        },
    },
}

# Runtime attrs the runner must setattr onto the compressor when present.
FORK_RUNTIME_ATTRS = ("session_type", "importance_biased_prune_enabled")


def apply_policy(compressor, spec: Dict[str, Any]):
    for key, value in (spec.get("attrs") or {}).items():
        setattr(compressor, key, value)
    return compressor
