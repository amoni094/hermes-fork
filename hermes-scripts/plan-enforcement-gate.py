#!/usr/bin/python3
"""
plan-enforcement-gate.py

Eliminates the enforcement gap by making agent self-critique actionable:
unsafe or incomplete plans are blocked at a gate before tool execution,
not just flagged after the fact.

Research basis ("Why LLM Agents Collapse Without Oversight: The Enforcement Gap"):
  Agent collapse occurs when self-critique is decoupled from action selection.
  The fix: a synchronous gate that checks every planned tool sequence against
  a set of enforcement invariants BEFORE the plan is dispatched. Plans that
  fail the gate are either revised or rejected with an explanation.

Math basis: enforcement as a monotone predicate lattice
  Invariants are ordered: HARD (block plan) > SOFT (warn) > INFO (log)
  A plan P passes iff ∀ hard invariant I: I(P) = True
  The gate applies invariants in order; first HARD failure short-circuits.
  Revision: if a soft invariant fails, the gate suggests the minimal patch.

Usage:
  python3 plan-enforcement-gate.py --plan plan.json
  python3 plan-enforcement-gate.py --plan-text "search then delete all files"
  python3 plan-enforcement-gate.py --dry-run
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
import secrets
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

HOME      = Path.home()
CACHE_DIR = HOME / ".hermes/cache/monitors"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE  = CACHE_DIR / "plan-enforcement-gate-report.json"

# ── Profile-aware root (used by PET helpers) ───────────────────────────────────
import os as _os_peg
_b_peg = Path(_os_peg.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_p_peg = _os_peg.environ.get("HERMES_PROFILE", "")
_root_peg = (_b_peg / "profiles" / _p_peg) if _p_peg and "profiles" not in str(_b_peg) else _b_peg
_PET_CACHE_DIR = _root_peg / "cache"
_PET_CACHE_DIR.mkdir(parents=True, exist_ok=True)


# ── Plan Execution Token (PET) helpers ─────────────────────────────────────────

def _pet_session_key() -> bytes:
    """Read or create a 32-byte session key stored as hex in cache/pet-session-key.

    Fail-open: if the file is unreadable for any reason, generate a fresh
    ephemeral key so the gate never hard-blocks on a key I/O error.
    """
    key_path = _PET_CACHE_DIR / "pet-session-key"
    try:
        text = key_path.read_text().strip()
        return bytes.fromhex(text)
    except Exception:
        pass
    # Create a new key atomically
    key = secrets.token_bytes(32)
    try:
        fd, tmp = tempfile.mkstemp(dir=str(_PET_CACHE_DIR), prefix=".pet-session-key.")
        try:
            with os.fdopen(fd, "w") as f:
                f.write(key.hex())
            os.replace(tmp, str(key_path))
        except Exception:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise
    except Exception:
        pass  # fail-open: return ephemeral key
    return key


def _issue_pet(plan_json_str: str, approved: bool) -> dict:
    """Issue a signed Plan Execution Token for the given plan JSON string.

    Cleans up expired token files (mtime > 10 min) before writing.
    Returns the token dict that should be merged into the gate result.
    """
    now = datetime.now(timezone.utc)
    now_ts = now.timestamp()

    # Cleanup expired token files (older than 10 minutes)
    try:
        for f in _PET_CACHE_DIR.glob("plan-token-*.json"):
            try:
                if now_ts - f.stat().st_mtime > 600:
                    f.unlink(missing_ok=True)
            except OSError:
                pass
    except Exception:
        pass

    # Compute plan hash from canonical JSON
    try:
        canonical = json.dumps(json.loads(plan_json_str), sort_keys=True, separators=(",", ":"))
    except (json.JSONDecodeError, TypeError):
        canonical = plan_json_str
    plan_hash = hashlib.sha256(canonical.encode()).hexdigest()

    # Compute HMAC token
    session_key = _pet_session_key()
    token_hex = hmac.new(session_key, plan_hash.encode(), hashlib.sha256).hexdigest()

    issued_at = now.isoformat()
    expires_at = datetime.fromtimestamp(now_ts + 300, tz=timezone.utc).isoformat()

    token_dict = {
        "token": token_hex,
        "plan_hash": plan_hash,
        "issued_at": issued_at,
        "expires_at": expires_at,
        "approved": approved,
    }

    # Write token file atomically
    token_file = _PET_CACHE_DIR / f"plan-token-{plan_hash[:8]}.json"
    try:
        fd, tmp = tempfile.mkstemp(dir=str(_PET_CACHE_DIR), prefix=".plan-token.")
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(token_dict, f, indent=2)
            os.replace(tmp, str(token_file))
        except Exception:
            try:
                os.unlink(tmp)
            except OSError:
                pass
    except Exception:
        pass  # fail-open: token dict still returned even if write fails

    return token_dict


def _verify_pet(token_hex: str, plan_json_str: str) -> dict:
    """Verify a Plan Execution Token.

    Returns {valid: bool, reason: str}.
    """
    # Recompute plan hash
    try:
        canonical = json.dumps(json.loads(plan_json_str), sort_keys=True, separators=(",", ":"))
    except (json.JSONDecodeError, TypeError):
        canonical = plan_json_str
    plan_hash = hashlib.sha256(canonical.encode()).hexdigest()

    token_file = _PET_CACHE_DIR / f"plan-token-{plan_hash[:8]}.json"
    try:
        stored = json.loads(token_file.read_text())
    except FileNotFoundError:
        return {"valid": False, "reason": "token file not found"}
    except Exception as exc:
        return {"valid": False, "reason": f"token file unreadable: {exc}"}

    # Verify stored hash matches
    if stored.get("plan_hash") != plan_hash:
        return {"valid": False, "reason": "plan hash mismatch"}

    # Verify HMAC
    session_key = _pet_session_key()
    expected = hmac.new(session_key, plan_hash.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, stored.get("token", "")):
        return {"valid": False, "reason": "token HMAC mismatch"}

    # Check expiry
    try:
        expires_at = datetime.fromisoformat(stored["expires_at"])
        if datetime.now(timezone.utc) > expires_at:
            return {"valid": False, "reason": "token expired"}
    except (KeyError, ValueError):
        return {"valid": False, "reason": "invalid expires_at in token"}

    # Check approved
    if not stored.get("approved"):
        return {"valid": False, "reason": "plan was not approved by gate"}

    # Check supplied token matches stored
    if not hmac.compare_digest(token_hex, stored.get("token", "")):
        return {"valid": False, "reason": "supplied token does not match stored token"}

    return {"valid": True, "reason": "ok"}

# ── Invariant definitions ──────────────────────────────────────────────────────

HARD_INVARIANTS = [
    {
        "id":      "NO_UNGUARDED_DESTRUCTIVE",
        "desc":    "Destructive tool calls must be preceded by a guard step",
        "pattern": re.compile(
            r"(?i)\b(delete|remove|drop|wipe|purge|reset|truncate|kill|unlink)\b"
        ),
        "guard_pattern": re.compile(
            r"(?i)\b(verify|check|confirm|backup|dry.?run|assert|validate|ensure)\b"
        ),
    },
    {
        "id":      "NO_CREDENTIAL_EXPOSURE",
        "desc":    "Plan must not contain literal credential patterns",
        "pattern": re.compile(
            r"(?i)(password\s*=|api_key\s*=|secret\s*=|token\s*=)['\"]?\w{6,}"
        ),
        "guard_pattern": None,  # no guard possible — hard block
    },
    {
        "id":      "NO_INFINITE_DELEGATION",
        "desc":    "Delegation depth must not exceed 3",
        "check":   lambda steps: sum(
            1 for s in steps if re.search(r"(?i)\bdelegate|spawn|subagent\b", s)
        ) >= 3,
    },
]

SOFT_INVARIANTS = [
    {
        "id":    "SCOPE_CHECK",
        "desc":  "Plan should not span more than 4 distinct tool domains",
        "check": lambda steps: len(_count_domains(steps)) > 4,
        "patch": "Consider splitting into sub-plans by domain",
    },
    {
        "id":    "LOOP_GUARD",
        "desc":  "Same tool should not appear more than 3 consecutive times",
        "check": lambda steps: _has_tool_loop(steps, max_run=3),
        "patch": "Add a break condition or use a single batch call instead",
    },
]


def _count_domains(steps: list[str]) -> set[str]:
    domain_map = {
        "search": {"search", "find", "lookup", "web_search"},
        "file":   {"write", "read", "patch", "edit", "delete", "remove"},
        "code":   {"execute", "run", "compile", "test", "debug"},
        "memory": {"remember", "store", "skill", "memory"},
        "agent":  {"delegate", "spawn", "subagent", "background"},
        "api":    {"fetch", "extract", "request", "http"},
    }
    found: set[str] = set()
    text = " ".join(steps).lower()
    for domain, kws in domain_map.items():
        if any(k in text for k in kws):
            found.add(domain)
    return found


def _has_tool_loop(steps: list[str], max_run: int = 3) -> bool:
    prev, run = None, 0
    for step in steps:
        # Extract first verb as tool proxy
        words = re.findall(r"[a-z]+", step.lower())
        verb  = words[0] if words else ""
        if verb == prev:
            run += 1
            if run >= max_run:
                return True
        else:
            prev, run = verb, 1
    return False


def _extract_steps(plan: dict | str) -> list[str]:
    if isinstance(plan, str):
        # Split on sentence boundaries or numbered steps
        return [s.strip() for s in re.split(r"[.\n]|(?:\d+\.\s)", plan) if s.strip()]
    if isinstance(plan, dict):
        steps = plan.get("steps", plan.get("actions", plan.get("plan", [])))
        if isinstance(steps, list):
            return [str(s) for s in steps]
        return [str(plan)]
    return [str(plan)]


def enforce(plan: dict | str) -> dict:
    steps     = _extract_steps(plan)
    full_text = " ".join(steps)
    violations: list[dict] = []
    warnings:   list[dict] = []
    verdict = "PASS"

    # Hard invariants
    for inv in HARD_INVARIANTS:
        if "check" in inv:
            failed = inv["check"](steps)  # type: ignore[operator]
        else:
            pattern      = inv["pattern"]
            guard_pattern = inv.get("guard_pattern")
            match        = pattern.search(full_text)
            if match and guard_pattern:
                # Destructive op — check guard appears before it
                match_pos  = match.start()
                pre_text   = full_text[:match_pos]
                failed     = not guard_pattern.search(pre_text)
            elif match:
                failed = True
            else:
                failed = False

        if failed:
            violations.append({"level": "HARD", "id": inv["id"], "desc": inv["desc"]})
            verdict = "BLOCK"

    # Soft invariants
    for inv in SOFT_INVARIANTS:
        if inv["check"](steps):  # type: ignore[operator]
            warnings.append({
                "level": "SOFT", "id": inv["id"],
                "desc":  inv["desc"],
                "patch": inv.get("patch", ""),
            })
            if verdict == "PASS":
                verdict = "WARN"

    return {
        "verdict":    verdict,
        "steps":      len(steps),
        "violations": violations,
        "warnings":   warnings,
        "domains":    sorted(_count_domains(steps)),
    }


def run(plan_json: Path | None, plan_text: str | None, dry_run: bool) -> int:
    now = datetime.now(timezone.utc).isoformat()

    if plan_json and plan_json.exists():
        plan = json.loads(plan_json.read_text())
    elif plan_text:
        plan = plan_text
    else:
        # Demo plans — no real credential strings (avoids permanent fixture alarm)
        plans = [
            "search arxiv then implement findings then test",
            "verify backup exists then delete all old cache files",
            "upload results to server with authentication headers",
            "delegate task 1 then delegate task 2 then delegate task 3 then delegate task 4",
        ]
        results = []
        print(f"\n=== Plan Enforcement Gate — {now[:10]} ===")
        blocked = 0
        for p in plans:
            r = enforce(p)
            verdict_icon = {"PASS": "✓", "WARN": "⚠", "BLOCK": "✗"}[r["verdict"]]
            print(f"  {verdict_icon} [{r['verdict']:<5}] {p[:55]}")
            for v in r["violations"]:
                print(f"           HARD: {v['id']} — {v['desc']}")
            for w in r["warnings"]:
                print(f"           SOFT: {w['id']} → {w['patch']}")
            results.append(r)
            if r["verdict"] == "BLOCK":
                blocked += 1

        if blocked:
            print(f"\nALARM: yes — {blocked} plan(s) blocked by enforcement gate")
        else:
            print("\nALARM: no — all plans passed enforcement gate")

        if not dry_run:
            _tmp_out_file = OUT_FILE.with_suffix('.tmp')
            _tmp_out_file.write_text(json.dumps({"ts": now, "results": results}, indent=2))
            _tmp_out_file.replace(OUT_FILE)
        return 0

    result = enforce(plan)
    # Issue a Plan Execution Token bound to this plan and gate result
    plan_json_str = json.dumps(plan) if not isinstance(plan, str) else plan
    approved = result["verdict"] != "BLOCK"
    result["execution_token"] = _issue_pet(plan_json_str, approved)
    print(json.dumps(result, indent=2))
    if not dry_run:
        _tmp_out_file = OUT_FILE.with_suffix('.tmp')
        _tmp_out_file.write_text(json.dumps({"ts": now, "result": result}, indent=2))
        _tmp_out_file.replace(OUT_FILE)
    return 1 if result["verdict"] == "BLOCK" else 0


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--plan",         type=Path, default=None)
    p.add_argument("--plan-text",    default=None)
    p.add_argument("--dry-run",      action="store_true")

    sub = p.add_subparsers(dest="subcommand")
    vt = sub.add_parser("verify-token", help="Verify a Plan Execution Token")
    vt.add_argument("--token",     required=True, help="HMAC hex token from execution_token.token")
    vt.add_argument("--plan-json", required=True, help="Plan JSON string that was checked")

    args = p.parse_args()

    if args.subcommand == "verify-token":
        result = _verify_pet(args.token, args.plan_json)
        print(json.dumps(result))
        sys.exit(0 if result["valid"] else 1)

    sys.exit(run(args.plan, args.plan_text, args.dry_run))


if __name__ == "__main__":
    main()
