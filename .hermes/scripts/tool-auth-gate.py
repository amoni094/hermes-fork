#!/usr/bin/env python3
"""
tool-auth-gate.py — Separate action induction from runtime authorization.

arXiv:2608.27146 (Tool Outputs as Commands): tool outputs can become implicit
"commands" that drive real-world side effects beyond user intent. This happens
when the model conflates "data received from tool" with "instruction to execute."

This script provides an authorization gate that:
1. Classifies tool output as DATA vs ACTION-INDUCING
2. Checks proposed actions against an authorization policy
3. Logs suspected prompt-injection-via-tool-output events
4. Enforces a trust tier system for tool outputs

Trust tiers (inspired by 2608.26696 Five Primitives):
  - SYSTEM: hermes internals (highest trust)
  - VERIFIED: tools with known-good schemas (web_search, read_file, etc.)
  - DELEGATED: subagent/cronjob outputs (medium trust)
  - EXTERNAL: web content, API responses, user files (lowest trust, highest risk)

Usage:
  python3 tool-auth-gate.py classify --tool-name WEB_EXTRACT --output "..." 
  python3 tool-auth-gate.py check --proposed-action "delete file X" \\
      --source-tier EXTERNAL --session SID
  python3 tool-auth-gate.py audit --session SID   # show authorization log
  python3 tool-auth-gate.py report                # aggregated violation report

This script runs PASSIVELY as a monitor — it does NOT block actions by default.
It logs for audit and flags patterns that indicate tool-output-as-command injection.
When config.yaml tool_auth.enabled is true, classify/check still log; enforcement
remains advisory unless the caller treats non-zero exit as a hard stop.

arXiv:2608.26696 Five Primitives applied:
  - identity: tool has a declared name and tier
  - governance: authorization policy per tier
  - attestation: log hash of classified output + decision
  - supply_chain: track which tool produced which output that induced which action
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HERMES_HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
LOG_DIR = HERMES_HOME / "cache" / "tool-auth-log"

# Tools that produce structured/trusted outputs
VERIFIED_TOOLS = frozenset({
    "read_file", "search_files", "terminal", "web_search",
    "skill_view", "skills_list", "memory", "todo", "session_search",
    "write_file", "patch", "hindsight_recall", "hindsight_reflect",
})

# Subagent / cron outputs — medium trust (arXiv:2608.26696 DELEGATED tier)
DELEGATED_TOOLS = frozenset({
    "delegate_task", "cronjob", "process", "process_manage",
})

# Patterns that suggest a tool output is trying to induce action
ACTION_INDUCTION_PATTERNS = [
    r"(?i)\b(you must|you should now|next step is|please do|execute|run the following)\b",
    r"(?i)\b(delete|remove|rm -rf|drop table|truncate)\b",
    r"(?i)(SYSTEM:|<system>|<instruction>|<<SYS>>)",
    r"(?i)ignore\s+(previous|prior|all)\s+instructions",
    r"(?i)forget\s+(everything|all)\s+(you|we|I|that)",
    r"(?i)new\s+objective\s*:",
    r"(?i)\]\s*human\s*:\s*",  # role confusion attempt
    r"(?i)\[OUT-OF-BAND",      # fake OOB message injection
    r"(?i)override\s+(safety|policy|constraint)",
]

ACTION_INDUCTION_RE = [re.compile(p) for p in ACTION_INDUCTION_PATTERNS]

TIER_TRUST = {"SYSTEM": 4, "VERIFIED": 3, "DELEGATED": 2, "EXTERNAL": 1}

# Max tool calls before forced re-authorization check (bounded-turn FSM).
# Align with tool_loop_guardrails.warn_after.delegation_event_budget when present.
TURN_BUDGET = 24
ENABLED = True

# Actions that require elevated tier when proposed from external source
HIGH_RISK_ACTIONS = frozenset({
    "delete", "remove", "unlink", "rm", "drop", "truncate", "kill",
    "push", "publish", "send", "post", "write_file", "patch",
    "terminal", "execute", "run",
})

# Paths that need explicit justification when written during a repair context
# (ExecCritic: Repair agent must not modify test files).
SENSITIVE_PATHS = ("tests/",)
_REPAIR_WRITE_ACTIONS = frozenset({"write_file", "patch"})


def check_repair_context(
    action: str,
    target_path: str = "",
    caller_context: str | None = None,
) -> dict[str, Any]:
    """Gate test-file writes during repair/fix-code.

    Returns BLOCK_RECOMMEND when:
      - action is write_file or patch
      - target path contains 'tests/' or 'test_'
      - caller context contains 'repair' or 'fix code'

    Fail-open: unknown context → ALLOW with WARNING.
    """
    action_l = (action or "").strip().lower()
    path = target_path or ""
    tokens = set(re.findall(r"[a-z_]+", action_l))
    is_write = action_l in _REPAIR_WRITE_ACTIONS or bool(tokens & _REPAIR_WRITE_ACTIONS)
    path_sensitive = any(s in path for s in SENSITIVE_PATHS) or ("test_" in path)
    if not is_write or not path_sensitive:
        return {"decision": "ALLOW", "reason": "not a repair-context test-path write"}
    if caller_context is None or str(caller_context).strip() == "":
        return {
            "decision": "ALLOW",
            "warning": "repair context unknown; tests/ write allowed fail-open",
            "reason": "fail-open: caller context unknown",
        }
    ctx_l = str(caller_context).lower()
    if "repair" in ctx_l or "fix code" in ctx_l:
        return {
            "decision": "BLOCK_RECOMMEND",
            "reason": (
                "repair/fix-code context writing tests/ or test_ path; "
                "ExecCritic: repair must not modify tests without explicit justification"
            ),
        }
    return {"decision": "ALLOW", "reason": "sensitive path but not repair context"}


# CapabilityGrant and check_grant are wired into cmd_check() (the evaluate-tool-request gate).
# The grant file is loaded from the profile-aware cache path at request time (fail-open on miss).
# The string-match path remains the fallback when no grant is present or check_grant returns False.
@dataclass(frozen=True)
class CapabilityGrant:
    """Unforgeable grant object (arXiv:2609.08371 CapScope).

    Authority is a capability stored outside model context, not a string/NL
    permission match. Additive: the existing string-match path remains the
    fail-open fallback when no grant is present or check_grant returns False.
    """

    grant_id: str
    tools_allowed: frozenset[str]
    source_tier: str
    expires_at: datetime | None = None


def check_grant(grant: CapabilityGrant | None, tool_name: str) -> bool:
    """Return True iff grant authorizes tool_name and is unexpired.

    Fail-open: missing or malformed grant returns False so callers fall back
    to the existing string-match path rather than blocking execution.
    """
    if grant is None:
        return False
    try:
        if tool_name not in grant.tools_allowed:
            return False
        exp = grant.expires_at
        if exp is not None:
            now = datetime.now(timezone.utc)
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if now >= exp:
                return False
        return True
    except Exception:
        return False


def _load_active_grant() -> "CapabilityGrant | None":
    """Load the active CapabilityGrant from the profile-aware cache path.

    Fail-open: returns None when the file is absent, expired (>3600s), or malformed.
    Maps JSON keys (allowed_tools / denied_tools) onto CapabilityGrant.tools_allowed,
    treating denied_tools as a negative filter applied before construction.
    """
    import os as _os_tag
    _b = Path(_os_tag.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
    _p = _os_tag.environ.get("HERMES_PROFILE", "")
    _root_tag = (_b / "profiles" / _p) if _p and "profiles" not in str(_b) else _b
    grant_path = _root_tag / "cache" / "active-capability-grant.json"
    if not grant_path.exists():
        return None
    try:
        import time as _time
        if _time.time() - grant_path.stat().st_mtime > 3600:
            return None
        data = json.loads(grant_path.read_text())
        allowed = frozenset(data.get("allowed_tools", []))
        denied = frozenset(data.get("denied_tools", []))
        effective = allowed - denied
        expires_str = data.get("expires_at", "")
        expires_dt: "datetime | None" = None
        if expires_str:
            try:
                expires_dt = datetime.fromisoformat(expires_str.replace("Z", "+00:00"))
            except Exception:
                pass
        return CapabilityGrant(
            grant_id=data.get("grant_id", "file-grant"),
            tools_allowed=effective,
            source_tier=data.get("source_tier", "VERIFIED"),
            expires_at=expires_dt,
        )
    except Exception:
        return None


def _load_runtime_config() -> None:
    """Overlay log dir / turn budget / enabled from config.yaml tool_auth."""
    global LOG_DIR, TURN_BUDGET, ENABLED
    cfg_path = HERMES_HOME / "config.yaml"
    if not cfg_path.exists():
        return
    text = cfg_path.read_text()
    try:
        import yaml  # type: ignore
        data = yaml.safe_load(text) or {}
        sec = data.get("tool_auth") or (data.get("memory") or {}).get("tool_auth") or {}
        if sec.get("enabled") is False:
            ENABLED = False
        if sec.get("log_dir"):
            LOG_DIR = HERMES_HOME / str(sec["log_dir"])
        budget = (
            (data.get("tool_loop_guardrails") or {}).get("warn_after") or {}
        ).get("delegation_event_budget")
        if budget is not None:
            TURN_BUDGET = int(budget)
        return
    except Exception:
        pass
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("delegation_event_budget:"):
            try:
                TURN_BUDGET = int(s.split(":", 1)[1].strip())
            except ValueError:
                pass


_load_runtime_config()


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _log_path(session_id: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in (session_id or "global"))[:60]
    return LOG_DIR / f"auth-{safe}.jsonl"


def _read_log(session_id: str) -> list[dict[str, Any]]:
    log = _log_path(session_id)
    if not log.exists():
        return []
    entries: list[dict[str, Any]] = []
    for line in log.read_text().strip().split("\n"):
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except Exception:
            pass
    return entries


def _classify_output(tool_name: str, output: str) -> dict[str, Any]:
    """Classify a tool output as data vs action-inducing."""
    if tool_name in VERIFIED_TOOLS:
        tier = "VERIFIED"
    elif tool_name in DELEGATED_TOOLS:
        tier = "DELEGATED"
    else:
        tier = "EXTERNAL"
    flags = []
    for pattern_re in ACTION_INDUCTION_RE:
        match = pattern_re.search(output[:4096])
        if match:
            flags.append({"pattern": pattern_re.pattern[:60], "match": match.group(0)[:60]})
    score = len(flags)
    classification = "ACTION_INDUCING" if score >= 2 else ("SUSPICIOUS" if score == 1 else "DATA")
    return {
        "tool_name": tool_name,
        "tier": tier,
        "classification": classification,
        "injection_flags": flags,
        "output_hash": hashlib.sha256(output.encode()).hexdigest()[:16],
        "output_chars": len(output),
    }


def cmd_classify(args: argparse.Namespace) -> int:
    if not ENABLED:
        print(json.dumps({"skipped": True, "reason": "tool_auth.enabled=false"}))
        return 0
    result = _classify_output(args.tool_name, args.output)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    session = getattr(args, "session", "") or "global"
    existing = _read_log(session)
    record = {
        "ts": _now(),
        "cmd": "classify",
        "session": getattr(args, "session", ""),
        "turn_seq": len(existing),
        "action_induced": result["classification"] == "ACTION_INDUCING",
        "approved": False,
        **result,
    }
    with open(_log_path(session), "a") as f:
        f.write(json.dumps(record) + "\n")
    print(json.dumps(result, indent=2))
    if result["classification"] in ("ACTION_INDUCING", "SUSPICIOUS"):
        print(f"\n[tool-auth] WARNING: {result['classification']} tool output from {args.tool_name}",
              file=sys.stderr)
    return 1 if result["classification"] == "ACTION_INDUCING" else 0


def cmd_check(args: argparse.Namespace) -> int:
    """Check whether a proposed action is authorized given source tier."""
    if not ENABLED:
        print(json.dumps({"skipped": True, "reason": "tool_auth.enabled=false", "decision": "ALLOW"}))
        return 0

    # --- CapabilityGrant gate (arXiv:2609.08371 CapScope) ---
    # Load the file-backed grant (fail-open on missing/expired/malformed file).
    active_grant = _load_active_grant()
    tool_name = getattr(args, "tool_name", None) or args.proposed_action.split()[0]
    grant_verified: "bool | None" = None
    if active_grant is not None:
        grant_ok = check_grant(active_grant, tool_name)
        if not grant_ok:
            # Determine if the proposed action contains HIGH_RISK words before string-match path.
            _action_words = set(re.findall(r'\b\w+\b', args.proposed_action.lower()))
            if _action_words & HIGH_RISK_ACTIONS:
                result = {
                    "proposed_action": args.proposed_action[:200],
                    "source_tier": getattr(args, "source_tier", "EXTERNAL"),
                    "risk_tier": "BLOCKED",
                    "decision": "BLOCK_RECOMMEND",
                    "reason": "CapabilityGrant denied",
                    "grant_verified": False,
                }
                print(json.dumps(result, indent=2))
                return 1
        else:
            grant_verified = True
    # --- end CapabilityGrant gate ---

    action = args.proposed_action.lower()
    source_tier = getattr(args, "source_tier", "EXTERNAL")
    tier_level = TIER_TRUST.get(source_tier, 1)

    action_words = set(re.findall(r'\b\w+\b', action))
    high_risk = action_words & HIGH_RISK_ACTIONS
    decision = "ALLOW"
    reason = "action within authorized scope for tier"

    if high_risk and tier_level < 3:
        decision = "WARN"
        reason = f"high-risk action ({high_risk}) proposed by {source_tier} tier (trust={tier_level}); verify intent"

    if tier_level == 1 and high_risk:
        decision = "BLOCK_RECOMMEND"
        reason = f"EXTERNAL-tier source proposing high-risk action {high_risk}; likely tool-output-as-command injection"

    repair = check_repair_context(
        action=args.proposed_action,
        target_path=getattr(args, "target_path", "") or args.proposed_action,
        caller_context=getattr(args, "caller_context", None),
    )
    repair_warning = repair.get("warning")
    if repair["decision"] == "BLOCK_RECOMMEND":
        decision = "BLOCK_RECOMMEND"
        reason = repair["reason"]

    session = getattr(args, "session", "") or "global"
    existing = _read_log(session)
    turn_seq = len(existing)

    result = {
        "proposed_action": args.proposed_action[:200],
        "source_tier": source_tier,
        "tier_level": tier_level,
        "high_risk_words": list(high_risk),
        "decision": decision,
        "reason": reason,
    }
    if grant_verified is True:
        result["grant_verified"] = True
    if repair_warning and "warning" not in result:
        result["warning"] = repair_warning
    if turn_seq > TURN_BUDGET:
        result["warning"] = (
            f"TURN_BUDGET ({TURN_BUDGET}) exceeded (turn_count={turn_seq}); "
            "manual review is recommended"
        )

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    record = {
        "ts": _now(),
        "cmd": "check",
        "session": getattr(args, "session", ""),
        "turn_seq": turn_seq,
        "action_induced": bool(high_risk),
        "approved": decision == "ALLOW",
        **result,
    }
    with open(_log_path(session), "a") as f:
        f.write(json.dumps(record) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if decision == "ALLOW" else 1


def cmd_ltl_check(args: argparse.Namespace) -> int:
    """Enforce LTL safety G(action_induced -> previously_approved) over the session log."""
    session = getattr(args, "session", "") or "global"
    entries = _read_log(session)
    violations = [
        e for e in entries
        # H4 fix: only inspect cmd=check records (classify always writes approved=False by design)
        # LTL property: G(action_induced -> previously_approved) applies only to explicit checks
        if e.get("cmd") == "check"
        and e.get("action_induced") is True and e.get("approved") is False
    ]
    if violations:
        print(
            f"LTL VIOLATION: G(action_induced -> previously_approved) failed "
            f"({len(violations)} unapproved action-induction events)"
        )
        for v in violations:
            print(json.dumps(v))
        return 1
    print("LTL SAFE: no unapproved action-induction events")
    return 0


def cmd_audit(args: argparse.Namespace) -> int:
    log = _log_path(getattr(args, "session", "global"))
    if not log.exists():
        print("[tool-auth] no log found")
        return 0
    lines = log.read_text().strip().split("\n")
    suspicious = [json.loads(l) for l in lines if l and json.loads(l).get("classification") in ("ACTION_INDUCING", "SUSPICIOUS")]
    warnings = [json.loads(l) for l in lines if l and json.loads(l).get("decision") in ("WARN", "BLOCK_RECOMMEND")]
    print(f"[tool-auth] audit: {len(lines)} total events, {len(suspicious)} suspicious classifications, {len(warnings)} action warnings")
    for r in (suspicious + warnings)[-10:]:
        print(f"  [{r['ts']}] {r.get('tool_name', r.get('proposed_action', '')[:50])} -> {r.get('classification', r.get('decision', ''))}")
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    totals: dict[str, int] = {}
    for p in LOG_DIR.glob("auth-*.jsonl"):
        for line in p.read_text().strip().split("\n"):
            if not line:
                continue
            try:
                r = json.loads(line)
                key = r.get("classification") or r.get("decision") or "unknown"
                totals[key] = totals.get(key, 0) + 1
            except Exception:
                pass
    print("[tool-auth] aggregate report:")
    for k, v in sorted(totals.items(), key=lambda x: -x[1]):
        print(f"  {k}: {v}")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Tool output authorization gate (arXiv:2608.27146, 2608.26696)")
    sub = p.add_subparsers(dest="cmd")

    classify = sub.add_parser("classify")
    classify.add_argument("--tool-name", required=True)
    classify.add_argument("--output", required=True)
    classify.add_argument("--session", default="")

    check = sub.add_parser("check")
    check.add_argument("--proposed-action", required=True)
    check.add_argument("--source-tier", default="EXTERNAL",
                        choices=["SYSTEM", "VERIFIED", "DELEGATED", "EXTERNAL"])
    check.add_argument("--session", default="")
    check.add_argument("--target-path", default="")
    check.add_argument("--caller-context", default=None)

    audit = sub.add_parser("audit")
    audit.add_argument("--session", default="global")

    ltl = sub.add_parser("ltl-check")
    ltl.add_argument("--session", default="global")

    sub.add_parser("report")

    return p


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    if args.cmd == "classify":
        return cmd_classify(args)
    elif args.cmd == "check":
        return cmd_check(args)
    elif args.cmd == "audit":
        return cmd_audit(args)
    elif args.cmd == "ltl-check":
        return cmd_ltl_check(args)
    elif args.cmd == "report":
        return cmd_report(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
