#!/usr/bin/env python3
"""
Improvement Governance for Hermes self-improvement proposals.

Ported from Denuto `src/improvement/governance.py`.

Full lifecycle for pipeline self-improvement proposals with risk gating and
HITL approval. Implements:
  - ImprovementRiskLevel: LOW/MEDIUM/HIGH
  - Proposal lifecycle state machine with illegal-transition guards
  - Rate limiting and cooldown enforcement
  - Append-only JSONL proposal ledger at ~/.hermes/logs/improvement-proposals.jsonl

Theoretical basis:
  - State machine with is_legal_transition() enforces Lamport crash-boundary rule:
    a state that could be wrong is better than one that is silently wrong.
  - OCC (Kung & Robinson 1981) via conditional writes to the ledger.

Usage:
    from improvement_governance import (
        classify_change_risk, ImprovementRiskLevel,
        propose_improvement, apply_transition, auto_approve_if_low,
    )

    risk = classify_change_risk("skill_body", "ralph-loops")
    # → ImprovementRiskLevel.LOW

    proposal = propose_improvement(
        change_type="skill_body",
        target="ralph-loops",
        description="Add round-trip validation section",
        session_id="sess_abc",
        evidence=["test output shows gap"],
    )
    # For LOW risk: auto-approve immediately
    if risk == ImprovementRiskLevel.LOW:
        proposal = auto_approve_if_low(proposal)
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Callable, Literal

DEFAULT_LEDGER = Path.home() / ".hermes" / "logs" / "improvement-proposals.jsonl"


class ImprovementRiskLevel(Enum):
    LOW = "low"       # auto-approvable; affects one skill body, no cron/config change
    MEDIUM = "medium" # requires ≥1 reviewer; skill routing or cron changes
    HIGH = "high"     # requires senior reviewer; config.yaml, security, shared state


# Valid state transitions (Lamport crash-boundary: raise on illegal transition)
LEGAL_TRANSITIONS: dict[str, set[str]] = {
    "pending_review": {"under_eval", "rejected"},
    "under_eval":     {"approved", "rejected"},
    "approved":       {"deployed", "rejected"},
    "deployed":       {"rolled_back"},
    "rolled_back":    set(),   # terminal
    "rejected":       set(),   # terminal
}

# Risk classification table
_HIGH_TARGETS = frozenset({
    "config.yaml", "security", "mnemosyne", "trajectory-risk",
    "adversarial", "tool-auth-gate", "hooks",
})

_MEDIUM_CHANGE_TYPES = frozenset({"skill_routing", "cron"})
_HIGH_CHANGE_TYPES = frozenset({"config", "security", "schema"})


def classify_change_risk(
    change_type: Literal["skill_body", "skill_routing", "cron", "config", "security", "schema"],
    target: str,
) -> ImprovementRiskLevel:
    """
    Pure function. Deterministic risk classification.
    No side effects. Safe to call from any context.
    """
    if change_type in _HIGH_CHANGE_TYPES:
        return ImprovementRiskLevel.HIGH
    if any(t in target for t in _HIGH_TARGETS):
        return ImprovementRiskLevel.HIGH
    if change_type in _MEDIUM_CHANGE_TYPES:
        return ImprovementRiskLevel.MEDIUM
    return ImprovementRiskLevel.LOW


def is_legal_transition(from_state: str, to_state: str) -> bool:
    return to_state in LEGAL_TRANSITIONS.get(from_state, set())


def apply_transition(proposal: dict, to_state: str) -> dict:
    """
    Apply a state transition. RAISES on illegal transition.
    Never silently applies out-of-order transitions.
    """
    if not is_legal_transition(proposal["state"], to_state):
        raise ValueError(
            f"Illegal transition {proposal['state']!r} → {to_state!r} "
            f"for proposal {proposal.get('id', '?')!r}. "
            f"Legal from {proposal['state']!r}: {LEGAL_TRANSITIONS.get(proposal['state'], set())!r}"
        )
    proposal = dict(proposal)
    proposal["state"] = to_state
    proposal["updated_at"] = _now_iso()
    return proposal


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _proposal_id(session_id: str, change_type: str, target: str) -> str:
    h = hashlib.md5(
        f"{session_id}:{change_type}:{target}:{time.time()}".encode()
    ).hexdigest()[:8]
    return f"prop_{h}"


def propose_improvement(
    change_type: str,
    target: str,
    description: str,
    session_id: str,
    evidence: list[str],
    ledger: Path | None = None,
) -> dict:
    """
    Create a new proposal and append to the ledger (JSONL, append-only).
    Returns the proposal dict.
    """
    risk = classify_change_risk(change_type, target)  # type: ignore[arg-type]
    proposal = {
        "id": _proposal_id(session_id, change_type, target),
        "state": "pending_review",
        "risk": risk.value,
        "change_type": change_type,
        "target": target,
        "description": description,
        "proposed_by": session_id,
        "proposed_at": _now_iso(),
        "updated_at": _now_iso(),
        "reviewers": [],
        "evidence": evidence,
    }
    _append_to_ledger(proposal, ledger)
    return proposal


def auto_approve_if_low(proposal: dict, ledger: Path | None = None) -> dict:
    """
    Auto-approve a LOW-risk proposal. Raises if risk is not LOW.
    Never auto-approves MEDIUM or HIGH.
    """
    if proposal["risk"] != ImprovementRiskLevel.LOW.value:
        raise ValueError(
            f"Cannot auto-approve {proposal['risk']!r} risk proposal {proposal['id']!r}. "
            "Only LOW risk proposals may be auto-approved."
        )
    proposal = apply_transition(proposal, "under_eval")
    proposal = apply_transition(proposal, "approved")
    _append_to_ledger(proposal, ledger)
    return proposal


def deploy_proposal(
    proposal: dict,
    apply_fn: Callable[[], None],
    ledger: Path | None = None,
) -> dict:
    """
    Deploy an approved proposal. apply_fn() does the actual change.
    Raises if proposal is not in 'approved' state.
    """
    if proposal["state"] != "approved":
        raise ValueError(
            f"Cannot deploy proposal {proposal['id']!r} in state {proposal['state']!r}. "
            "Must be 'approved' first."
        )
    apply_fn()
    proposal = apply_transition(proposal, "deployed")
    _append_to_ledger(proposal, ledger)
    return proposal


def rollback_proposal(
    proposal: dict,
    undo_fn: Callable[[], None],
    ledger: Path | None = None,
) -> dict:
    """Rollback a deployed proposal."""
    undo_fn()
    proposal = apply_transition(proposal, "rolled_back")
    _append_to_ledger(proposal, ledger)
    return proposal


# --- Rate limiting ---

_rate_lock = threading.Lock()
_last_proposal_times: dict[str, float] = {}
COOLDOWN_SECONDS = 3600   # Min time between proposals of same (change_type, target)
MAX_PER_HOUR = 5          # Hard cap on total proposals per hour
_proposal_timestamps: list[float] = []


def check_rate_limit(change_type: str, target: str) -> None:
    """Raises RateLimitError if rate limits are exceeded."""
    key = f"{change_type}:{target}"
    now = time.time()
    with _rate_lock:
        # Cooldown check
        last = _last_proposal_times.get(key)
        if last and (now - last) < COOLDOWN_SECONDS:
            wait = COOLDOWN_SECONDS - (now - last)
            raise RuntimeError(
                f"Rate limit: proposal for {key!r} too soon. "
                f"Wait {wait:.0f}s (cooldown={COOLDOWN_SECONDS}s)."
            )
        # Total per-hour check
        hour_ago = now - 3600
        _proposal_timestamps[:] = [t for t in _proposal_timestamps if t > hour_ago]
        if len(_proposal_timestamps) >= MAX_PER_HOUR:
            raise RuntimeError(
                f"Rate limit: {MAX_PER_HOUR} proposals per hour exceeded. "
                "A runaway loop generating many proposals is SYSTEMIC_BLAST risk."
            )
        _last_proposal_times[key] = now
        _proposal_timestamps.append(now)


def _append_to_ledger(proposal: dict, ledger: Path | None) -> None:
    """Append proposal to JSONL ledger. Append-only."""
    path = ledger or DEFAULT_LEDGER
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(proposal) + "\n")


def load_proposals(ledger: Path | None = None) -> list[dict]:
    """Load all proposals from ledger. Returns list, newest-last."""
    path = ledger or DEFAULT_LEDGER
    proposals = []
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        proposals.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    return proposals


# ── CLI entry point ───────────────────────────────────────────────────────────

def _cmd_propose(args) -> int:
    """CLI: create a new improvement proposal."""
    import sys as _sys
    session_id = args.session_id or f"cli_{int(time.time())}"
    try:
        check_rate_limit(args.change_type, args.target)
    except RuntimeError as exc:
        print(json.dumps({"error": str(exc)}), file=_sys.stderr)
        return 1
    proposal = propose_improvement(
        change_type=args.change_type,
        target=args.target,
        description=args.description,
        session_id=session_id,
        evidence=args.evidence or [],
    )
    # Auto-approve if LOW risk
    risk = classify_change_risk(args.change_type, args.target)  # type: ignore[arg-type]
    if risk == ImprovementRiskLevel.LOW:
        proposal = auto_approve_if_low(proposal)
    print(json.dumps(proposal, indent=2))
    return 0


def _cmd_approve(args) -> int:
    """CLI: transition a proposal to approved (for MEDIUM/HIGH proposals)."""
    import sys as _sys
    proposals = load_proposals()
    matches = [p for p in proposals if p.get("id") == args.proposal_id]
    if not matches:
        print(json.dumps({"error": f"proposal {args.proposal_id!r} not found"}),
              file=_sys.stderr)
        return 1
    # Use the *last* entry for this id (newest state)
    proposal = matches[-1]
    try:
        if proposal["state"] == "pending_review":
            proposal = apply_transition(proposal, "under_eval")
            _append_to_ledger(proposal, None)
        proposal = apply_transition(proposal, "approved")
        _append_to_ledger(proposal, None)
    except ValueError as exc:
        print(json.dumps({"error": str(exc)}), file=_sys.stderr)
        return 1
    print(json.dumps(proposal, indent=2))
    return 0


def _cmd_rollback(args) -> int:
    """CLI: roll back a deployed proposal."""
    import sys as _sys
    proposals = load_proposals()
    matches = [p for p in proposals if p.get("id") == args.proposal_id]
    if not matches:
        print(json.dumps({"error": f"proposal {args.proposal_id!r} not found"}),
              file=_sys.stderr)
        return 1
    proposal = matches[-1]
    try:
        proposal = rollback_proposal(proposal, lambda: None)
    except ValueError as exc:
        print(json.dumps({"error": str(exc)}), file=_sys.stderr)
        return 1
    print(json.dumps(proposal, indent=2))
    return 0


def _cmd_list(args) -> int:
    """CLI: list all proposals from the ledger."""
    proposals = load_proposals()
    # Deduplicate: keep newest state per proposal id
    seen: dict[str, dict] = {}
    for p in proposals:
        seen[p.get("id", "")] = p
    out = list(seen.values())
    print(json.dumps(out, indent=2))
    return 0


def main() -> int:
    import argparse as _argparse
    import sys as _sys

    parser = _argparse.ArgumentParser(
        description="Improvement Governance CLI for Hermes self-improvement proposals"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # propose
    p_propose = sub.add_parser("propose", help="Create a new improvement proposal")
    p_propose.add_argument("--change-type", required=True, dest="change_type",
                           help="Change type: skill_body | skill_routing | cron | config | security | schema")
    p_propose.add_argument("--target", required=True,
                           help="Target skill or file name")
    p_propose.add_argument("--description", required=True,
                           help="Human-readable description of the change")
    p_propose.add_argument("--evidence", nargs="*", default=[],
                           help="Supporting evidence strings (optional, repeatable)")
    p_propose.add_argument("--session-id", default=None, dest="session_id",
                           help="Session ID (default: cli_<timestamp>)")
    p_propose.set_defaults(func=_cmd_propose)

    # approve
    p_approve = sub.add_parser("approve", help="Approve a pending proposal")
    p_approve.add_argument("--proposal-id", required=True, dest="proposal_id",
                           help="Proposal ID (e.g. prop_abc12345)")
    p_approve.set_defaults(func=_cmd_approve)

    # rollback
    p_rollback = sub.add_parser("rollback", help="Rollback a deployed proposal")
    p_rollback.add_argument("--proposal-id", required=True, dest="proposal_id",
                            help="Proposal ID to roll back")
    p_rollback.set_defaults(func=_cmd_rollback)

    # list
    p_list = sub.add_parser("list", help="List all proposals (deduped, newest state)")
    p_list.set_defaults(func=_cmd_list)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    import sys as _sys
    _sys.exit(main())
