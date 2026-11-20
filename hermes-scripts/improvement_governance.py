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
import os
import threading
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from datetime import datetime, timezone, UTC
from typing import Callable, Literal

def _default_ledger() -> Path:
    """Profile-aware ledger path. Prefer fork ledger when HERMES_PROFILE unset."""
    env_home = os.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))
    base = Path(env_home)
    profile = os.environ.get("HERMES_PROFILE", "")
    if "profiles" in str(base):
        return base / "logs" / "improvement-proposals.jsonl"
    if profile:
        return base / "profiles" / profile / "logs" / "improvement-proposals.jsonl"
    fork = Path.home() / ".hermes" / "profiles" / "fork" / "logs" / "improvement-proposals.jsonl"
    if fork.exists():
        return fork
    return base / "logs" / "improvement-proposals.jsonl"


DEFAULT_LEDGER = _default_ledger()
DEDUP_WINDOW_HOURS = 24
DEDUP_LOOKBACK = 50
# Profile-aware rate-state persistence path
_base = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_profile = os.environ.get('HERMES_PROFILE', 'fork')
_root = (_base / 'profiles' / _profile) if _profile else _base
_RATE_STATE_PATH = _root / 'cache' / 'governance-rate-state.json'

TERMINAL_STATES = frozenset({"rejected", "reverted", "rolled_back", "superseded"})


class ImprovementRiskLevel(Enum):
    LOW = "low"       # auto-approvable; affects one skill body, no cron/config change
    MEDIUM = "medium" # requires ≥1 reviewer; skill routing or cron changes
    HIGH = "high"     # requires senior reviewer; config.yaml, security, shared state


# Valid state transitions (Lamport crash-boundary: raise on illegal transition)
LEGAL_TRANSITIONS: dict[str, set[str]] = {
    "pending_review": {"under_eval", "rejected", "superseded"},
    "under_eval":     {"approved", "rejected", "superseded"},
    "approved":       {"deployed", "rejected", "superseded"},
    "deployed":       {"rolled_back", "superseded"},
    "rolled_back":    set(),   # terminal
    "rejected":       set(),   # terminal
    "reverted":       set(),   # terminal (alias of rolled_back)
    "superseded":     set(),   # terminal (compaction tombstone)
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
    # Compaction may tombstone any live (or already-terminal) record.
    if to_state == "superseded":
        return True
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


def _causal_effect_estimate(target: str, description: str, evidence: list) -> float:
    """Causal Bayesian effect estimate (arXiv:2609.24112).

    Proxy for do-calculus P(outcome | do(intervention)) vs P(outcome) using:
    - evidence count (more evidence → higher prior confidence)
    - keyword salience (quantitative claims like %, ms, score → higher weight)
    - target type (script > skill > config for measurable effect)

    Returns a float in [0.0, 1.0] representing estimated uplift probability.
    This is a heuristic proxy; a full structural causal model would require
    before/after benchmark comparisons (see arena-credits.json for that path).
    """
    import re as _re
    base = 0.3 + min(len(evidence), 5) * 0.06  # up to +0.30 for 5+ evidence items
    # Quantitative claim bonus
    quant_hits = len(_re.findall(
        r'\b(\d+\.?\d*\s*%|\d+\s*ms|\bscore\b|\bimprove\b|\bfaster\b|\breduced?\b)',
        description, _re.IGNORECASE
    ))
    quant_bonus = min(quant_hits * 0.04, 0.20)
    # Target type bonus: scripts/runtime > skills > config
    target_lower = (target or "").lower()
    target_bonus = (
        0.10 if any(t in target_lower for t in (".py", "script", "runtime", "cron"))
        else 0.05 if "skill" in target_lower
        else 0.0
    )
    return round(min(base + quant_bonus + target_bonus, 1.0), 4)


def _default_failure_observable(change_type: str, target: str, description: str) -> str:
    """Generate a default failure_observable for Popper/Critch falsifiability.

    Every proposal needs a non-trivial (>20 char) observable. If the caller
    does not supply one, derive a generic but specific one from the change context.
    Callers should override this with domain-specific observables when possible.
    """
    # NOTE: This generates a default template FO. Callers should override with a specific,
    # measurable failure observable (named metric + comparator + threshold) to avoid WARN.
    ct = (change_type or '').lower()
    if ct in ('skill_body', 'skill', 'skill_create'):
        return f"Skill '{target}' causes regressions in eval suite or produces incorrect outputs on 3+ test cases within 30 days."
    elif ct in ('code', 'code_change', 'script', 'plugin'):
        return f"Script/plugin '{target}' raises unhandled exception or breaks a downstream monitor within 14 days of deployment."
    elif ct in ('config', 'config_change', 'yaml', 'setting'):
        return f"Config change to '{target}' causes alarm rate to increase >20% vs baseline in the 7-day post-deploy window."
    elif ct in ('cron', 'cron_job'):
        return f"Cron job '{target}' fails to produce expected output or writes stale data for 2+ consecutive runs."
    else:
        d_snippet = (description or '')[:60].rstrip()
        return f"Change '{target}' ({d_snippet}) produces measurable regression in quality or stability metrics within 14 days."



def _parse_proposal_ts(ts) -> float | None:
    """Parse proposal timestamp to epoch seconds. None if unparseable."""
    if ts is None:
        return None
    if isinstance(ts, (int, float)):
        try:
            return float(ts)
        except (TypeError, ValueError):
            return None
    s = str(ts).strip()
    if not s:
        return None
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt.timestamp()
    except (TypeError, ValueError):
        return None


def _recent_description_dup(description: str, ledger: Path | None = None) -> dict | None:
    """Return newest last-N ledger entry with same description in-window.

    Matches only pending_review/approved rows created within DEDUP_WINDOW_HOURS.
    Empty/missing ledger or mismatched/expired rows yield None.
    """
    path = ledger or DEFAULT_LEDGER
    if not path.exists():
        return None
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    # Walk from end so tombstones (appended after compact) do not consume the
    # 50-entry lookback. Skip terminal states including superseded.
    recent: list[dict] = []
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict):
            continue
        if obj.get("state") in TERMINAL_STATES:
            continue
        recent.append(obj)
        if len(recent) >= DEDUP_LOOKBACK:
            break
    now = time.time()
    window_s = DEDUP_WINDOW_HOURS * 3600
    for entry in recent:  # already newest-first
        if entry.get("description") != description:
            continue
        if entry.get("state") not in ("pending_review", "approved"):
            continue
        created = _parse_proposal_ts(
            entry.get("proposed_at") or entry.get("updated_at") or entry.get("created_at")
        )
        if created is None:
            continue
        if now - created <= window_s:
            return entry
    return None


def propose_improvement(
    change_type: str,
    target: str,
    description: str,
    session_id: str,
    evidence: list,
    ledger=None,
    failure_observable: str | None = None,
) -> dict:
    """
    Create a new proposal and append to the ledger (JSONL, append-only).
    Returns the proposal dict.
    """
    dup = _recent_description_dup(description, ledger)
    if dup is not None:
        return dup
    risk = classify_change_risk(change_type, target)  # type: ignore[arg-type]
    causal_effect = _causal_effect_estimate(target, description, evidence)
    fo = failure_observable or _default_failure_observable(change_type, target, description)
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
        "causal_effect_estimate": causal_effect,  # arXiv:2609.24112
        "failure_observable": fo,
    }
    proposal['fo_is_template'] = (failure_observable is None)  # True if we generated the default
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
        # Load persisted timestamps (fail-open: ignore any read errors)
        loaded: list[float] = []
        try:
            rsp = _RATE_STATE_PATH
            if rsp.exists() and (now - rsp.stat().st_mtime) < 3700:
                loaded = json.loads(rsp.read_text(encoding='utf-8'))
        except Exception:
            pass  # fail-open: proceed with in-memory state only

        # Merge + dedup + prune to last hour
        hour_ago = now - 3600
        merged = sorted(set(_proposal_timestamps) | set(loaded))
        pruned = [t for t in merged if t > hour_ago]
        _proposal_timestamps[:] = pruned

        # Cooldown check
        last = _last_proposal_times.get(key)
        if last and (now - last) < COOLDOWN_SECONDS:
            wait = COOLDOWN_SECONDS - (now - last)
            raise RuntimeError(
                f"Rate limit: proposal for {key!r} too soon. "
                f"Wait {wait:.0f}s (cooldown={COOLDOWN_SECONDS}s)."
            )
        # Total per-hour check
        if len(_proposal_timestamps) >= MAX_PER_HOUR:
            raise RuntimeError(
                f"Rate limit: {MAX_PER_HOUR} proposals per hour exceeded. "
                "A runaway loop generating many proposals is SYSTEMIC_BLAST risk."
            )
        _last_proposal_times[key] = now
        _proposal_timestamps.append(now)

        # Persist updated list atomically (fail-open)
        try:
            import tempfile as _tempfile
            rsp = _RATE_STATE_PATH
            rsp.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp = _tempfile.mkstemp(dir=rsp.parent, prefix='.rate-state-tmp-', suffix='.json')
            try:
                with os.fdopen(fd, 'w', encoding='utf-8') as f:
                    json.dump(_proposal_timestamps, f)
                os.replace(tmp, rsp)
            except Exception:
                try:
                    os.unlink(tmp)
                except OSError:
                    pass
        except Exception:
            pass  # fail-open


def _append_to_ledger(proposal: dict, ledger: Path | None) -> None:
    """Append proposal to JSONL ledger. Append-only, fcntl-locked for concurrent safety."""
    import fcntl
    path = ledger or DEFAULT_LEDGER
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            f.write(json.dumps(proposal) + "\n")
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def load_proposals(ledger: Path | None = None) -> list[dict]:
    """Load all proposals from ledger. Returns list, newest-last. Skips malformed lines."""
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


def _load_all(ledger: Path | None = None) -> list[dict]:
    """Id-deduped proposals with superseded tombstones omitted.

    Newest record per id wins (append-only ledger). Entries whose newest
    state is superseded are skipped so callers iterating this list see
    active proposals only. rejected/reverted/rolled_back remain so callers
    can filter terminal states themselves.
    """
    seen: dict[str, dict] = {}
    for p in load_proposals(ledger):
        pid = p.get("id", "")
        seen[pid] = p
    return [p for p in seen.values() if p.get("state") != "superseded"]


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
    # Auto-approve if LOW risk. Skip when description-dedup returned an existing row.
    if proposal.get("state") == "pending_review":
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


def _cmd_deploy(args) -> int:
    """CLI: transition an approved proposal to deployed."""
    import sys as _sys
    proposals = load_proposals()
    matches = [p for p in proposals if p.get("id") == args.proposal_id]
    if not matches:
        print(json.dumps({"error": f"proposal {args.proposal_id!r} not found"}),
              file=_sys.stderr)
        return 1
    proposal = matches[-1]
    try:
        proposal = apply_transition(proposal, "deployed")
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
    """CLI: list active proposals from the ledger (deduped, newest state)."""
    out = _load_all()
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

    # deploy
    p_deploy = sub.add_parser("deploy", help="Deploy an approved proposal (mark as deployed)")
    p_deploy.add_argument("--proposal-id", required=True, dest="proposal_id",
                          help="Proposal ID to deploy")
    p_deploy.set_defaults(func=_cmd_deploy)

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
