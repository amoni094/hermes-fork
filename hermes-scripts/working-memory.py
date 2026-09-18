#!/usr/bin/env python3
"""
working-memory.py — Recuris-style Experiential vs Working Memory split for Hermes.

arXiv:2608.24876 (Recuris): long-horizon harnesses fail when full history drives
skill selection. Working Memory (WM) should track *task progress* and guide skill
invocation; Experiential Memory (Hindsight/Graphiti/skills) holds durable lessons.

This script is the session-local WM surface. It does NOT write Hindsight/Graphiti.
Experiential recall stays on unified-recall / hindsight / graphiti.

Store: ~/.hermes/cache/working-memory/<session_id>.json

Usage:
  python3 ~/.hermes/scripts/working-memory.py init --session SID --goal "..."
  python3 ~/.hermes/scripts/working-memory.py set --session SID --key progress --value '["step1 done"]'
  python3 ~/.hermes/scripts/working-memory.py add-constraint --session SID \
      --text "do not push" --binding must --authority user --fallback "ask user" \
      --consequence "remote branch rewritten"
  python3 ~/.hermes/scripts/working-memory.py skill-hint --session SID
  python3 ~/.hermes/scripts/working-memory.py show --session SID
  python3 ~/.hermes/scripts/working-memory.py localize-failure --session SID \
      --component skill|wm|experiential --note "wrong skill X selected"
  python3 ~/.hermes/scripts/working-memory.py lookahead --session SID \
      --action "proposed next action" --steps-ahead 3 [--goal "..."] [--constraints JSON]
  python3 ~/.hermes/scripts/working-memory.py subplan-verify --session SID \
      --subplan '["step1", "step2"]'
  python3 ~/.hermes/scripts/working-memory.py switch-framework --session SID \
      --from-framework causal-check --to-framework hypothesize --trigger "..."
  python3 ~/.hermes/scripts/working-memory.py set-belief --session SID --key KEY \
      --text TEXT [--parent-key PARENT_KEY] [--source user|tool|summary] [--conf 0.9]
  python3 ~/.hermes/scripts/working-memory.py get-belief --session SID --key KEY
  python3 ~/.hermes/scripts/working-memory.py belief-chain --session SID --key KEY
  python3 ~/.hermes/scripts/working-memory.py check-constraints --session SID
  python3 ~/.hermes/scripts/working-memory.py belief-syndrome --session SID
  python3 ~/.hermes/scripts/working-memory.py belief-limit --session SID
  python3 ~/.hermes/scripts/working-memory.py belief-colimit --session SID
  python3 ~/.hermes/scripts/working-memory.py clear --session SID
  python3 ~/.hermes/scripts/working-memory.py update --session SID --active-skills '["github"]'
  python3 ~/.hermes/scripts/working-memory.py bigrams [--min-count 2] [--query QUERY]
  python3 ~/.hermes/scripts/working-memory.py skill-entropy [--session SID | --all]
  python3 ~/.hermes/scripts/working-memory.py skill-mi --skill-a SKILL_A --skill-b SKILL_B

Constraint schema follows arXiv:2608.24569 (Constraint Weakening): binding must
stay action-binding (must/should/info), never collapse must→info on handoff.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac as _hmac_mod
import json
import math
import os
import re
import secrets
import subprocess
import sys
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HERMES_HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
WM_DIR = HERMES_HOME / "cache" / "working-memory"
skill_sequence_log = HERMES_HOME / "cache" / "skill-sequences.jsonl"
VALID_BINDINGS = ("must", "should", "info")
VALID_COMPONENTS = ("skill", "wm", "experiential", "tool", "handoff")

# ── CRYPTO-5: HMAC-SHA256 MAC for WM entries ─────────────────────────────────
_WM_MAC_KEY_PATH = HERMES_HOME / "cache" / "wm-mac.key"


def _wm_mac_key() -> bytes:
    """Load or create the HMAC key for working-memory MAC verification."""
    _WM_MAC_KEY_PATH.parent.mkdir(parents=True, exist_ok=True)
    if _WM_MAC_KEY_PATH.exists():
        raw = _WM_MAC_KEY_PATH.read_bytes()
        if len(raw) == 32:
            return raw
    key = secrets.token_bytes(32)
    _WM_MAC_KEY_PATH.write_bytes(key)
    _WM_MAC_KEY_PATH.chmod(0o600)
    return key


def _wm_compute_mac(doc: dict[str, Any]) -> str:
    """Compute HMAC-SHA256 over the WM doc content (excluding any existing _mac field)."""
    doc_copy = {k: v for k, v in doc.items() if k != "_mac"}
    content = json.dumps(doc_copy, sort_keys=True, ensure_ascii=False).encode("utf-8")
    key = _wm_mac_key()
    return _hmac_mod.new(key, content, hashlib.sha256).hexdigest()


def _wm_verify_mac(doc: dict[str, Any]) -> bool:
    """Return True if the stored _mac matches the recomputed MAC."""
    stored = doc.get("_mac")
    if not stored:
        return False
    expected = _wm_compute_mac(doc)
    return _hmac_mod.compare_digest(expected, stored)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _path(session_id: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in session_id)[:120]
    return WM_DIR / f"{safe}.json"


def _load(session_id: str) -> dict[str, Any]:
    p = _path(session_id)
    if not p.exists():
        return {
            "schema": "hermes-working-memory/v3",
            "session_id": session_id,
            "goal": "",
            "groth_context": "session",  # Grothendieck context: session|skill|hindsight|global|cron
            "progress": [],
            "next": [],
            "open_decisions": [],
            "constraints": [],  # action-binding operational state
            "active_skills": [],
            "skill_combos_recorded": [],  # HyperSkill tracking: combos used in this session
            "failure_localizations": [],
            "latency_tracker": {},
            "framework_switches": [],
            "beliefs": {},
            "variant_history": [],
            "updated_at": None,
        }
    return json.loads(p.read_text())


def _save(doc: dict[str, Any], mac_verify: bool = False) -> Path:
    WM_DIR.mkdir(parents=True, exist_ok=True)
    doc["updated_at"] = _now()
    if mac_verify:
        doc["_mac"] = _wm_compute_mac(doc)
    p = _path(doc["session_id"])
    p.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    return p


def _append_skill_sequence(session_id: str | None, skills: Any) -> None:
    """GALLAGER-4: append one JSONL skill-sequence record. Never raise on I/O failure."""
    if not isinstance(skills, list):
        skills = [skills]
    sid = (str(session_id).strip() if session_id else "") or str(uuid.uuid4())[:8]
    skill_list = [str(s) for s in skills]
    rec = {"ts": _now(), "session": sid, "skills": skill_list, "active_skills": skill_list}
    try:
        skill_sequence_log.parent.mkdir(parents=True, exist_ok=True)
        with skill_sequence_log.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except OSError as exc:
        print(f"warning: skill sequence log unwritable ({skill_sequence_log}): {exc}", file=sys.stderr)


def cmd_init(args: argparse.Namespace) -> int:
    doc = _load(args.session)
    if args.goal:
        doc["goal"] = args.goal
    if args.reset:
        doc["progress"] = []
        doc["next"] = []
        doc["open_decisions"] = []
        doc["failure_localizations"] = []
        # keep constraints unless --wipe-constraints
        if args.wipe_constraints:
            doc["constraints"] = []
    mac_verify = getattr(args, "mac_verify", False)
    p = _save(doc, mac_verify=mac_verify)
    print(json.dumps({"ok": True, "path": str(p), "goal": doc["goal"]}, indent=2))
    return 0


def cmd_set(args: argparse.Namespace) -> int:
    doc = _load(args.session)
    key = args.key
    if key not in ("goal", "progress", "next", "open_decisions", "active_skills"):
        print(f"unsupported key: {key}", file=sys.stderr)
        return 2
    raw = args.value
    if key == "goal":
        doc["goal"] = raw
    else:
        try:
            val = json.loads(raw)
        except json.JSONDecodeError:
            val = [raw]
        if not isinstance(val, list):
            val = [val]
        doc[key] = val
    if key == "active_skills":
        _append_skill_sequence(args.session, doc.get("active_skills") or [])
    p = _save(doc)
    print(json.dumps({"ok": True, "path": str(p), key: doc[key]}, indent=2))
    return 0


def cmd_update(args: argparse.Namespace) -> int:
    """Patch WM fields; log skill sequences when active_skills is present (GALLAGER-4)."""
    session_id = args.session or str(uuid.uuid4())[:8]
    doc = _load(session_id)
    doc["session_id"] = session_id
    patch: dict[str, Any] = {}
    raw_json = getattr(args, "json", None)
    if raw_json:
        try:
            loaded = json.loads(raw_json)
        except json.JSONDecodeError:
            print("update --json must be a JSON object", file=sys.stderr)
            return 2
        if not isinstance(loaded, dict):
            print("update --json must be a JSON object", file=sys.stderr)
            return 2
        patch.update(loaded)
    skills_raw = getattr(args, "active_skills", None)
    if skills_raw is not None:
        try:
            skills_val = json.loads(skills_raw)
        except json.JSONDecodeError:
            skills_val = [skills_raw]
        if not isinstance(skills_val, list):
            skills_val = [skills_val]
        patch["active_skills"] = skills_val
    if not patch:
        print("update requires --json and/or --active-skills", file=sys.stderr)
        return 2
    for k, v in patch.items():
        doc[k] = v
    if "active_skills" in patch:
        _append_skill_sequence(session_id, patch["active_skills"])
    p = _save(doc)
    print(json.dumps({"ok": True, "path": str(p), "session": session_id}, indent=2))
    return 0


def cmd_add_constraint(args: argparse.Namespace) -> int:
    binding = (args.binding or "must").lower()
    if binding not in VALID_BINDINGS:
        print(f"binding must be one of {VALID_BINDINGS}", file=sys.stderr)
        return 2
    session_id = args.session or "default"  # --session is optional; default to "default"
    doc = _load(session_id)
    entry = {
        "text": args.text.strip(),
        "binding": binding,  # must | should | info — NEVER weaken on rewrite
        "authority": (args.authority or "user").strip(),
        "fallback": (args.fallback or "").strip() or None,
        "consequence_if_ignored": (args.consequence or "").strip() or None,
        "added_at": _now(),
        # BCIT (arXiv:2608.26730): bind experience to source context before reuse
        # Populate these when a constraint is learned from a specific model/session context
        "source_context": getattr(args, "source_context", None) or None,  # e.g. "session:abc123" or "skill:hermes-agent"
        "predecessor_model": getattr(args, "predecessor_model", None) or None,  # model that generated this constraint
        # arXiv:2608.25553: stale constraint expiry metadata (required)
        "created_at": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        "expires_at_or_policy": getattr(args, "expires_at", None) or "until_changed",
        "source_turn": getattr(args, "source_turn", None),
        # Zenn JP Aug 2026: card scope
        "scope": getattr(args, "scope", "workflow"),
    }
    # de-dupe by text
    doc["constraints"] = [c for c in doc["constraints"] if c.get("text") != entry["text"]]
    doc["constraints"].append(entry)
    p = _save(doc)
    print(json.dumps({"ok": True, "path": str(p), "constraint": entry}, indent=2))
    return 0


def cmd_skill_hint(args: argparse.Namespace) -> int:
    """Emit a compact WM snapshot for skill selection (not full history)."""
    doc = _load(args.session)
    must = [c for c in doc.get("constraints", []) if c.get("binding") == "must"]
    hint = {
        "goal": doc.get("goal") or "",
        "progress_tail": (doc.get("progress") or [])[-5:],
        "next": (doc.get("next") or [])[:5],
        "must_constraints": [
            {
                "text": c["text"],
                "authority": c.get("authority"),
                "fallback": c.get("fallback"),
                "consequence_if_ignored": c.get("consequence_if_ignored"),
            }
            for c in must
        ],
        "active_skills": doc.get("active_skills") or [],
        "note": (
            "Select skills from current WM needs, not full chat history. "
            "Experiential memory (Hindsight/skills) is separate — retrieve only if WM lacks the lesson."
        ),
    }
    print(json.dumps(hint, indent=2, ensure_ascii=False))
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    doc = _load(args.session)
    mac_verify = getattr(args, "mac_verify", False)
    if mac_verify:
        if doc.get("_mac"):
            ok = _wm_verify_mac(doc)
            if ok:
                print("[MAC_OK] HMAC-SHA256 verified — content unmodified.", file=sys.stderr)
            else:
                print("[MAC_FAIL] HMAC-SHA256 MISMATCH — content may have been tampered with!", file=sys.stderr)
        else:
            print("[MAC_NONE] No MAC stored — save with --mac-verify to create baseline.", file=sys.stderr)
    print(json.dumps(doc, indent=2, ensure_ascii=False))
    return 0


def cmd_localize_failure(args: argparse.Namespace) -> int:
    comp = (args.component or "").lower()
    if comp not in VALID_COMPONENTS:
        print(f"component must be one of {VALID_COMPONENTS}", file=sys.stderr)
        return 2
    doc = _load(args.session)
    entry = {
        "component": comp,
        "note": args.note.strip(),
        "at": _now(),
    }
    doc.setdefault("failure_localizations", []).append(entry)
    p = _save(doc)
    print(json.dumps({"ok": True, "path": str(p), "failure": entry}, indent=2))
    return 0


def cmd_handoff_export(args: argparse.Namespace) -> int:
    """Export action-binding constraints + WM for handoff (Constraint Weakening + Handoff Tax).

    Prefer this structured state over dumping full trajectories when switching
    models/sessions (arXiv:2608.24358 Handoff Tax).
    """
    # Session is optional — fallback to "default" when not specified (plan-from-memory pattern)
    session_id = args.session or "default"
    try:
        doc = _load(session_id)
    except Exception:
        doc = {}
    out = {
        "schema": "hermes-wm-handoff/v1",
        "goal": doc.get("goal"),
        "progress": doc.get("progress"),
        "next": doc.get("next"),
        "open_decisions": doc.get("open_decisions"),
        "constraints": doc.get("constraints"),  # preserve binding field verbatim
        "active_skills": doc.get("active_skills"),
        "failure_localizations": (doc.get("failure_localizations") or [])[-10:],
        "rules": [
            "Do not rewrite binding:must as should/info.",
            "Do not replace structured WM with a prose paraphrase of the chat.",
            "Receiver continues from WM + repo state; full trajectory is optional evidence only.",
        ],
        "skill_state_hint": (
            # arXiv:2608.26263 SKILL.state: for long-horizon tasks (>10 steps),
            # receiver should run: skill-state.py init --session SESSION --skill SKILL --spec GOAL
            # then step-by-step: skill-state.py step --session SESSION --step N --observation OBS
            # This replaces append-only conversation history for state tracking
            f"python3 ~/.hermes/scripts/skill-state.py init "
            f"--session {args.session} --skill <skill-name> --spec \"<from goal above>\""
        ),
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


def cmd_verify_gate(args: argparse.Namespace) -> int:
    # H6 fix: return exit code instead of sys.exit (caller decides); --session is required
    if not args.session:
        print("ERROR: --session is required for verify-gate", file=sys.stderr)
        return 2
    wm = _load(args.session)
    failures = wm.get('failure_localizations', [])
    consecutive = 0
    for fl in reversed(failures):
        if fl.get('component') == 'tool' and 'verify' in (fl.get('note') or '').lower():
            consecutive += 1
        else:
            break
    if consecutive >= 2:
        print(f'ABORT: {consecutive} consecutive verify failures - halting task progression')
        return 1  # H6 fix: was sys.exit(1) — let caller handle
    print(f'OK: verify-gate pass (consecutive_verify_failures={consecutive})')
    return 0


def cmd_record_latency(args: argparse.Namespace) -> int:
    """Kalman-simplified EMA latency tracker (MMSE for linear-Gaussian) plus CUSUM flag."""
    wm = _load(args.session)
    tracker = wm.setdefault("latency_tracker", {})
    tool = args.tool_name
    entry = tracker.setdefault(tool, {"mean": args.elapsed_s, "var": 1.0, "n": 0})
    # Kalman EMA update (alpha = 1/(n+1) clipped to [0.05, 0.5] for stability)
    n = entry["n"] + 1
    alpha = max(0.05, min(0.5, 1.0 / n))
    prev_mean = entry["mean"]
    entry["mean"] = (1 - alpha) * prev_mean + alpha * args.elapsed_s
    entry["var"] = (1 - alpha) * entry["var"] + alpha * (args.elapsed_s - prev_mean) ** 2
    entry["n"] = n
    if args.elapsed_s > entry["mean"] + 3 * (entry["var"] ** 0.5):
        entry["cusum_alert"] = True
        print(f"[CUSUM ALERT] {tool} latency {args.elapsed_s:.1f}s >> {entry['mean']:.1f}s mean")
    else:
        entry["cusum_alert"] = False
    tracker[tool] = entry
    wm["latency_tracker"] = tracker
    _save(wm)
    print(f"latency {tool}: mean={entry['mean']:.2f}s var={entry['var']:.3f} n={n}")
    return 0


def cmd_clear(args: argparse.Namespace) -> int:
    p = _path(args.session)
    if p.exists():
        p.unlink()
        print(json.dumps({"ok": True, "removed": str(p)}))
    else:
        print(json.dumps({"ok": True, "removed": None, "note": "already absent"}))
    return 0


def _plan_steps_from_task(task_summary: str, analog_text: str) -> list[str]:
    """Thin forward plan: analog lines if present, else a 3-step goal skeleton."""
    lines = [
        ln.strip(" -*\t")
        for ln in (analog_text or "").splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]
    forward = [ln for ln in lines if ln][:8]
    goal = (task_summary or "").strip() or "goal"
    if not forward:
        forward = [
            f"init: establish current state for '{goal}'",
            f"work: execute steps toward '{goal}'",
            f"goal: '{goal}' satisfied",
        ]
    return forward


def _backward_plan_from_forward(task_summary: str, forward: list[str]) -> list[str]:
    """Flip goal↔init: list steps from goal back to init (arXiv:2411.01790)."""
    goal = (task_summary or "").strip() or "goal"
    if not forward:
        return [f"goal: '{goal}'", "init: current state"]
    body = list(reversed(forward))
    if body and "goal" not in body[0].lower():
        body = [f"goal: '{goal}'"] + body
    if body and "init" not in body[-1].lower():
        body = body + ["init: current state"]
    return body


def _plans_converge(forward: list[str], backward: list[str]) -> bool:
    """True when forward and reversed-backward share overlapping step tokens."""
    import re
    stop = {"the", "a", "an", "to", "of", "and", "or", "in", "on", "for", "with",
            "is", "be", "this", "that", "it", "at", "by", "from", "as", "if",
            "init", "goal", "work", "current", "state"}

    def toks(steps: list[str]) -> set[str]:
        out: set[str] = set()
        for s in steps:
            for t in re.findall(r"[a-z0-9]+", s.lower()):
                if t not in stop and len(t) > 2:
                    out.add(t)
        return out

    ft, bt = toks(forward), toks(backward)
    if not ft or not bt:
        return False
    overlap = len(ft & bt) / max(1, min(len(ft), len(bt)))
    return overlap >= 0.4


def cmd_plan_from_memory(args: argparse.Namespace) -> int:
    """
    plan-from-memory — retrieve prior analog task trajectories before first tool call.
    Synapse (ACL 2026 Findings:1108): memory-grounded planning.
    Inject 1-3 analog plans, not raw logs. Retrieve by task embedding similarity.
    Optional --backward-plan: Thinking Forward and Backward (arXiv:2411.01790).
    No WM session is required: missing analogs is a graceful no-op, not an error.
    """
    import subprocess
    recall_script = Path(__file__).parent / "unified-recall.py"
    result = subprocess.run(
        ["python3", str(recall_script),
         "--query", f"task plan {args.task_summary}", "--top", "3"],
        capture_output=True, text=True
    )
    analog = result.stdout.strip() if result.returncode == 0 and result.stdout.strip() else ""
    session = getattr(args, "session", None)
    wm_note = "no WM session — analog recall only (graceful)"
    if session:
        _load(session)  # initialise empty WM shell if missing; do not require prior init
        wm_note = f"WM session={session}"
    if not getattr(args, "backward_plan", False):
        if analog:
            print("# plan-from-memory: prior analog task trajectories")
            print(analog[:800])
        else:
            print("# plan-from-memory: no prior analogs found — proceed without memory priming")
            print(f"# {wm_note}")
        return 0

    forward_plan = _plan_steps_from_task(args.task_summary, analog)
    backward_plan = _backward_plan_from_forward(args.task_summary, forward_plan)
    print(json.dumps({
        "task_summary": args.task_summary,
        "forward_plan": forward_plan,
        "backward_plan": backward_plan,
        "consistency_check": _plans_converge(forward_plan, backward_plan),
        "analog_excerpt": analog[:800] if analog else "",
        "wm_note": wm_note,
    }, indent=2, ensure_ascii=False))
    return 0



def cmd_record_skill_combo(args: argparse.Namespace) -> int:
    """Record a skill combination for HyperSkill hyperedge tracking (arXiv:2608.16114)."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    try:
        # Dynamic import to avoid circular deps
        import importlib.util, types as _types
        _spec = importlib.util.spec_from_file_location(
            "memory_monad", Path(__file__).parent / "memory-monad.py"
        )
        _mod = _types.ModuleType("memory_monad")
        _mod.__file__ = str(Path(__file__).parent / "memory-monad.py")
        _mod.__spec__ = _spec
        import sys as _sys; _sys.modules.setdefault("memory_monad", _mod)
        _spec.loader.exec_module(_mod)
        tracker = _mod.HyperSkillTracker()
        tracker.record_combo(args.skills, task_type=args.task_type)
        candidates = tracker.get_hyperedge_candidates(min_count=3)
        doc = _load(args.session) if args.session else {}
        if doc:
            doc.setdefault("skill_combos_recorded", []).append({
                "skills": sorted(args.skills), "task_type": args.task_type, "ts": _now()
            })
            _save(doc)
        print(json.dumps({
            "recorded": True, "skills": args.skills, "task_type": args.task_type,
            "hyperedge_candidates": len(candidates),
            "note": tracker.report() if candidates else "no candidates yet (need 3+ uses)",
        }, indent=2))
    except Exception as e:
        print(json.dumps({"recorded": False, "error": str(e)}))
        return 1
    return 0


# Irreversible-external vs hard-to-reverse-local cues (FLARE / HORIZON lookahead).
_IRREVERSIBLE_EXTERNAL = (
    "git push", "force push", "--force", "push --force", "deploy", "publish",
    "drop table", "drop database", "rm -rf", "rm -r", "send email", "send mail",
    "transfer", "wipe", "format disk", "destroy", "rewrite history",
    "delete remote", "production", "public gist", "aws s3 rm", "terraform apply",
    "kubectl delete", "drop schema", "force-with-lease",
)
_HARD_TO_REVERSE_LOCAL = (
    "write_file", "write ", "overwrite", "patch", "install", "migrate",
    "chmod", "chown", "merge", "rebase", "commit", "unlink", "truncate",
    "rm ", "delete ", "edit ", "mv ", "sed -i",
)


def _parse_constraints_json(raw: str | None) -> list[dict[str, Any]]:
    if not raw or not str(raw).strip():
        return []
    try:
        val = json.loads(raw)
    except json.JSONDecodeError:
        return [{"text": str(raw).strip(), "binding": "must"}]
    if isinstance(val, dict):
        val = [val]
    if not isinstance(val, list):
        val = [val]
    out: list[dict[str, Any]] = []
    for item in val:
        if isinstance(item, str):
            out.append({"text": item.strip(), "binding": "must"})
        elif isinstance(item, dict):
            text = str(item.get("text") or item.get("constraint") or "").strip()
            if text:
                out.append({
                    "text": text,
                    "binding": str(item.get("binding") or "must").lower(),
                })
        else:
            out.append({"text": str(item).strip(), "binding": "must"})
    return out


def _step_text(step: Any) -> str:
    if isinstance(step, dict):
        return str(step.get("text") or step.get("action") or step.get("step") or json.dumps(step))
    return str(step)


def _commitment_level(action: str) -> str:
    a = action.lower()
    if any(cue in a for cue in _IRREVERSIBLE_EXTERNAL):
        return "HIGH"
    if any(cue in a for cue in _HARD_TO_REVERSE_LOCAL):
        return "MEDIUM"
    return "LOW"


def _forbidden_phrases(constraint_text: str) -> list[str]:
    """Extract phrases banned by do-not / never / must-not constraints."""
    t = constraint_text.lower().strip()
    phrases: list[str] = []
    for prefix in ("do not ", "don't ", "dont ", "never ", "must not ", "must-not "):
        if prefix in t:
            rest = t.split(prefix, 1)[1]
            rest = rest.split(";")[0].split(".")[0].strip(" .,;:\"'")
            if rest:
                phrases.append(rest)
    return phrases


def _violates_constraint(action: str, constraint: dict[str, Any]) -> bool:
    text = (constraint.get("text") or "").strip()
    if not text:
        return False
    a = action.lower()
    for phrase in _forbidden_phrases(text):
        if phrase and phrase in a:
            return True
    return False


def _merge_constraints(doc: dict[str, Any], extra_json: str | None) -> list[dict[str, Any]]:
    merged = list(doc.get("constraints") or [])
    seen = {(c.get("text") or "").strip() for c in merged}
    for c in _parse_constraints_json(extra_json):
        t = (c.get("text") or "").strip()
        if t and t not in seen:
            merged.append(c)
            seen.add(t)
    return merged


def cmd_lookahead(args: argparse.Namespace) -> int:
    """FLARE-style explicit lookahead: evaluate counterfactual future trajectories."""
    session = (args.session or os.environ.get("HERMES_SESSION") or "ephemeral").strip()
    action = (args.action or getattr(args, "next_action", "") or "").strip()
    if getattr(args, "task", None):
        args.goal = args.goal or args.task
    if not action:
        print(json.dumps({"error": "--action/--next-action is required", "lookahead_verdict": "BLOCK"}))
        return 2
    n = int(args.steps_ahead)
    if getattr(args, "steps_remaining", None) is not None:
        n = int(args.steps_remaining)
    n = max(1, n)
    doc = _load(session)
    if not args.session:
        doc["session_id"] = session
        # ephemeral: do not persist unless the caller named a session
    goal = (args.goal or "").strip() or (doc.get("goal") or "")
    constraints = _merge_constraints(doc, getattr(args, "constraints", None))
    must = [c for c in constraints if (c.get("binding") or "").lower() == "must"]
    should = [c for c in constraints if (c.get("binding") or "").lower() == "should"]
    progress = list(doc.get("progress") or [])
    next_items = list(doc.get("next") or [])

    commitment = _commitment_level(action)
    must_hits = [c for c in must if _violates_constraint(action, c)]
    should_hits = [c for c in should if _violates_constraint(action, c)]

    if commitment == "HIGH":
        terminal_risk = 0.72
    elif commitment == "MEDIUM":
        terminal_risk = 0.38
    else:
        terminal_risk = 0.08
    if should_hits:
        terminal_risk = min(1.0, terminal_risk + 0.12)
    if must_hits:
        terminal_risk = min(1.0, max(terminal_risk, 0.88) + 0.05 * (len(must_hits) - 1))

    if must_hits or (commitment == "HIGH" and terminal_risk >= 0.8):
        verdict = "BLOCK"
    elif commitment in ("HIGH", "MEDIUM") or should_hits or terminal_risk >= 0.35:
        verdict = "CAUTION"
    else:
        verdict = "PROCEED"

    projected_states: list[str] = []
    for i in range(1, n + 1):
        if i == 1:
            projected_states.append(
                f"t+1 after '{action}': WM progress records the action; "
                f"goal={goal or 'unspecified'}; "
                f"commitment={commitment}; receding-horizon replan if observations diverge."
            )
        else:
            follow = next_items[i - 2] if i - 2 < len(next_items) else (
                f"continue toward goal ({goal or 'unspecified'})"
            )
            projected_states.append(
                f"t+{i}: {follow}. Prior action '{action}' is sunk; "
                f"backward value from this step informs whether t+1 should have been taken."
            )

    if commitment == "HIGH":
        recovery_options = [
            "halt and escalate before further external writes",
            "compensate only if a documented inverse exists",
            "record the irreversible change in WM progress and replan remaining horizon",
        ]
    elif commitment == "MEDIUM":
        recovery_options = [
            "revert local change (git checkout / restore backup)",
            "replan remaining sub-steps under must-constraints",
            "verify expected state before committing further",
        ]
    else:
        recovery_options = [
            "choose an alternative action with no state change",
            "skip / no-op and replan freely",
            "continue; limited commitment leaves the trajectory open",
        ]
    if must_hits:
        recovery_options = [
            f"do not take the action; honor must-constraint: {must_hits[0].get('text')}",
            must_hits[0].get("fallback") or "ask the user / apply stated fallback",
        ] + recovery_options

    ebp_note = (
        f"Done for this action means: '{action}' completed, WM progress "
        f"{progress[-1:] or ['(empty)']} is updated, goal '{goal or 'unspecified'}' "
        "is not violated, and must-constraints still hold. Verify before treating as terminal."
    )

    out = {
        "projected_states": projected_states,
        "terminal_risk": round(terminal_risk, 3),
        "lookahead_verdict": verdict,
        "recovery_options": recovery_options,
        "commitment_level": commitment,
        "ebp_note": ebp_note,
        "must_constraint_hits": [c.get("text") for c in must_hits],
        "should_constraint_hits": [c.get("text") for c in should_hits],
        "goal": goal,
        "steps_ahead": n,
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))
    if verdict == "BLOCK":
        return 2
    if verdict == "CAUTION":
        return 1
    return 0


def cmd_subplan_verify(args: argparse.Namespace) -> int:
    """HORIZON-style subplan check against active must-constraints before execution.

    --subplan / --plan JSON format:
      ["step 1 text", "step 2 text", ...]
    or
      [{"step": "text", "id": "S1"}, ...]
    Optional --current-step names the phase that must appear in the plan.
    Session is optional: missing WM means no must-constraints (plan still parsed).
    """
    session = args.session or os.environ.get("HERMES_SESSION") or "ephemeral"
    raw = getattr(args, "subplan", None) or getattr(args, "plan", None) or ""
    try:
        steps = json.loads(raw)
    except json.JSONDecodeError:
        print(json.dumps({
            "error": "--subplan must be a JSON list of planned sub-steps",
            "verdict": "BLOCK",
            "verified_steps": [],
            "constraint_violations": [],
            "blocking_violations": [],
        }))
        return 2
    if not isinstance(steps, list):
        steps = [steps]

    doc = _load(session)
    constraints = list(doc.get("constraints") or [])
    must = [c for c in constraints if (c.get("binding") or "").lower() == "must"]
    should = [c for c in constraints if (c.get("binding") or "").lower() == "should"]

    verified_steps: list[dict[str, Any]] = []
    constraint_violations: list[dict[str, Any]] = []
    blocking_violations: list[dict[str, Any]] = []

    for idx, step in enumerate(steps):
        text = _step_text(step).strip()
        step_must = [c for c in must if _violates_constraint(text, c)]
        step_should = [c for c in should if _violates_constraint(text, c)]
        ok = not step_must
        entry = {
            "index": idx,
            "step": text,
            "ok": ok,
            "must_hits": [c.get("text") for c in step_must],
            "should_hits": [c.get("text") for c in step_should],
        }
        verified_steps.append(entry)
        for c in step_must:
            v = {
                "index": idx,
                "step": text,
                "binding": "must",
                "constraint": c.get("text"),
                "blocking": True,
            }
            constraint_violations.append(v)
            blocking_violations.append(v)
        for c in step_should:
            constraint_violations.append({
                "index": idx,
                "step": text,
                "binding": "should",
                "constraint": c.get("text"),
                "blocking": False,
            })

    if blocking_violations:
        verdict = "BLOCK"
        rc = 2
    elif constraint_violations:
        verdict = "WARN"
        rc = 1
    else:
        verdict = "OK"
        rc = 0

    current = (getattr(args, "current_step", None) or "").strip()
    if current:
        hay = " ".join(_step_text(s) for s in steps).lower()
        if current.lower() not in hay and not any(current.lower() in _step_text(s).lower() for s in steps):
            verdict = "BLOCK"
            rc = 2
            blocking_violations.append({
                "index": -1,
                "step": current,
                "binding": "must",
                "constraint": "--current-step not found in --plan/--subplan",
                "blocking": True,
            })

    print(json.dumps({
        "verified_steps": verified_steps,
        "constraint_violations": constraint_violations,
        "blocking_violations": blocking_violations,
        "verdict": verdict,
        "current_step": current or None,
        "session": session,
    }, indent=2, ensure_ascii=False))
    return rc


_INCONCLUSIVE_VERDICTS = {
    "unknown", "uncertain", "insufficient", "inconclusive", "n/a", "na",
    "none", "correlated", "probable", "probable_alternative", "",
}
MAX_SWITCHES_PER_SESSION = 3
# Åström hysteresis (Schmitt): θ_high to enter a switch, θ_low to reverse it.
THETA_HIGH = 0.65
THETA_LOW = 0.35
PROGRESS_DEAD_ZONE = 0.05


_FRAMEWORK_CLASS = {
    "causal-check": "causal",
    "hypothesize": "abductive",
    "lookahead": "planning",
    "subplan-verify": "planning",
    "boundary-check": "boundary",
    "abstain-check": "uncertainty",
    "kapro-check": "knowledge",
}


def cmd_switch_framework(args: argparse.Namespace) -> int:
    """Mid-task reasoning-framework switch (MixReasoning / Meta-Reasoner).

    Carry still-valid conclusions; discard those the switch invalidates.
    Same from/to is a no-op (does not mutate WM).
    """
    session_id = args.session
    if not session_id:
        print(json.dumps({
            "error": "--session is required for switch-framework",
            "switch_recorded": False,
        }))
        return 2
    from_fw = (args.from_framework or "").strip()
    to_fw = (args.to_framework or "").strip()
    trigger = (args.trigger or "").strip()
    prior = (getattr(args, "prior_verdict", None) or "").strip()

    if not from_fw or not to_fw:
        print(json.dumps({
            "error": "--from-framework and --to-framework are required",
            "switch_recorded": False,
        }))
        return 2

    known = set(_FRAMEWORK_CLASS)
    unknown = [n for n in (from_fw, to_fw) if n not in known]
    if unknown:
        print(json.dumps({
            "error": (
                f"unknown framework(s) {unknown}; expected one of {sorted(known)}"
            ),
            "switch_recorded": False,
            "from": from_fw,
            "to": to_fw,
        }))
        return 2

    if from_fw == to_fw:
        print(json.dumps({
            "warning": "from-framework equals to-framework; no-op (WM not mutated)",
            "switch_recorded": False,
            "from": from_fw,
            "to": to_fw,
            "carry_over": [],
            "discard": [],
        }, indent=2))
        return 0

    # Guard condition check (arXiv:2603.10779 Lyapunov guard conditions for agentic systems).
    # Prevents oscillation between frameworks without semantic justification.
    # Guard = "current state satisfies preconditions of the target framework."
    GUARD_CONDITIONS: dict[tuple[str, str], str] = {
        ("causal-check", "hypothesize"):
            "Guard: causal-check should have returned exit 2 (unknown/insufficient) "
            "before switching to hypothesize. If causal-check returned 0 or 1 (causal confirmed "
            "or correlation), switching to hypothesize is premature.",
        ("hypothesize", "causal-check"):
            "Guard: hypothesize should have produced at least one testable hypothesis "
            "before switching to causal-check. If hypothesize found no candidate causes, "
            "causal-check has nothing to test.",
        ("abstain-check", "causal-check"):
            "Guard: abstain-check should have returned proceed (exit 0) before switching "
            "to causal-check. If abstain-check returned abstain (exit 4), causal reasoning "
            "on an action that should be abstained from is wasteful.",
    }
    guard_key = (from_fw, to_fw)
    guard_note = GUARD_CONDITIONS.get(guard_key)
    # Guard is advisory (not blocking) — log it but do not prevent the switch.
    # Blocking would require runtime state access not available here.

    doc = _load(session_id)
    switches = doc.setdefault("framework_switches", [])

    # Åström-03: hysteresis + dead zone on framework switching.
    trigger_score = getattr(args, "score", None)
    if trigger_score is None:
        trigger_score = THETA_HIGH
    progress_delta = getattr(args, "progress_delta", None)

    if progress_delta is not None and abs(progress_delta) < PROGRESS_DEAD_ZONE:
        print(json.dumps({
            "switch_recorded": False,
            "hysteresis_blocked": True,
            "reason": "dead_zone",
            "progress_delta": progress_delta,
            "dead_zone": PROGRESS_DEAD_ZONE,
            "from": from_fw,
            "to": to_fw,
            "score": trigger_score,
        }, indent=2, ensure_ascii=False))
        return 0

    is_reverse = any(
        (sw.get("from") == to_fw and sw.get("to") == from_fw) for sw in switches
    )
    if is_reverse and trigger_score < THETA_LOW:
        print(json.dumps({
            "switch_recorded": False,
            "hysteresis_blocked": True,
            "reason": "reverse_below_theta_low",
            "theta_low": THETA_LOW,
            "from": from_fw,
            "to": to_fw,
            "score": trigger_score,
        }, indent=2, ensure_ascii=False))
        return 0
    if (not is_reverse) and trigger_score < THETA_HIGH:
        print(json.dumps({
            "switch_recorded": False,
            "hysteresis_blocked": True,
            "reason": "initial_below_theta_high",
            "theta_high": THETA_HIGH,
            "from": from_fw,
            "to": to_fw,
            "score": trigger_score,
        }, indent=2, ensure_ascii=False))
        return 0

    if len(switches) >= MAX_SWITCHES_PER_SESSION:
        print(json.dumps({
            "error": (
                f"max_switches_per_session={MAX_SWITCHES_PER_SESSION} already reached; "
                "refusing further switch (overthinking risk)"
            ),
            "switch_recorded": False,
            "from": from_fw,
            "to": to_fw,
            "trigger": trigger,
            "switch_count": len(switches),
            "max_switches_per_session": MAX_SWITCHES_PER_SESSION,
        }, indent=2, ensure_ascii=False))
        return 1
    prior_lower = prior.lower()
    inconclusive = (not prior) or prior_lower in _INCONCLUSIVE_VERDICTS
    same_class = _FRAMEWORK_CLASS.get(from_fw, from_fw) == _FRAMEWORK_CLASS.get(to_fw, to_fw)

    if inconclusive or not same_class:
        carry_over: list[str] = []
        discard = [
            f"{from_fw} conclusions discarded"
            + ("" if same_class else f" (class {_FRAMEWORK_CLASS.get(from_fw, 'other')} "
               f"≠ {_FRAMEWORK_CLASS.get(to_fw, 'other')})")
            + (f" (prior_verdict={prior})" if prior else ""),
        ]
        if prior and not inconclusive and not same_class:
            carry_over = [f"prior note only (not a {to_fw} conclusion): {from_fw}={prior}"]
            discard = [
                f"{from_fw} verdict is not valid as a {to_fw} conclusion (orthogonal class)",
            ]
    else:
        carry_over = [f"{from_fw} verdict still valid: {prior}"]
        discard = [
            f"Do not treat {from_fw} as the active primary framework after this switch",
        ]

    new_constraints = [
        f"use {to_fw} for remaining reasoning",
        f"do not treat {from_fw} as the active primary framework",
    ]
    if trigger:
        new_constraints.append(f"switch trigger: {trigger}")

    now_ts = _now()
    entry = {
        "from": from_fw,
        "to": to_fw,
        "score": trigger_score,
        "ts": now_ts,
        "trigger": trigger,
        "prior_verdict": prior or None,
        "guard_note": guard_note,
        "at": now_ts,
    }
    switches.append(entry)

    skills = list(doc.get("active_skills") or [])
    if from_fw in skills:
        skills = [s for s in skills if s != from_fw]
    if to_fw not in skills:
        skills.append(to_fw)
    doc["active_skills"] = skills

    # Persist switch-implied must-constraint without collapsing binding
    constraints = list(doc.get("constraints") or [])
    switch_text = f"active reasoning framework is {to_fw} (switched from {from_fw})"
    constraints = [c for c in constraints if c.get("text") != switch_text]
    constraints.append({
        "text": switch_text,
        "binding": "should",
        "authority": "switch-framework",
        "fallback": f"re-run select-frameworks if {to_fw} also fails",
        "consequence_if_ignored": "stale framework continues after type shift",
        "added_at": _now(),
    })
    doc["constraints"] = constraints

    p = _save(doc)
    print(json.dumps({
        "switch_recorded": True,
        "hysteresis_blocked": False,
        "from": from_fw,
        "to": to_fw,
        "score": trigger_score,
        "ts": now_ts,
        "trigger": trigger,
        "carry_over": carry_over,
        "discard": discard,
        "new_constraints": new_constraints,
        "path": str(p),
        "switch_count": len(switches),
    }, indent=2, ensure_ascii=False))
    return 0


def cmd_belief_update(args: argparse.Namespace) -> int:
    """Complementary-filter belief state (Åström-05).

    xhat = alpha * slow + (1-alpha) * fast
    P_approx = abs(slow - fast) * (1 - alpha)
    """
    session_id = args.session or "default"
    name = (args.name or "").strip()
    if not name:
        print(json.dumps({"error": "--name is required"}), file=sys.stderr)
        return 2
    slow = float(args.slow)
    fast = float(args.fast)
    alpha = float(args.alpha) if args.alpha is not None else 0.8
    xhat = alpha * slow + (1.0 - alpha) * fast
    p_approx = abs(slow - fast) * (1.0 - alpha)
    stale = abs(fast - xhat) > 3.0 * math.sqrt(p_approx + 1e-6)
    doc = _load(session_id)
    beliefs = doc.setdefault("beliefs", {})
    beliefs[name] = {
        "xhat": xhat,
        "slow": slow,
        "fast": fast,
        "alpha": alpha,
        "ts": _now(),
        "P_approx": p_approx,
    }
    _save(doc)
    print(json.dumps({
        "name": name,
        "xhat": xhat,
        "P_approx": p_approx,
        "stale": stale,
        "action": "REMEASURE" if stale else "OK",
    }))
    return 0


VALID_BELIEF_SOURCES = ("user", "tool", "summary")


def _belief_tokens(text: str) -> set[str]:
    """Simple whitespace tokens for DPI overlap (COVSHA-4)."""
    return {t for t in str(text or "").lower().split() if t}


def cmd_set_belief(args: argparse.Namespace) -> int:
    """COVSHA-4: store a provenance-tracked belief (diagnostic DPI cap, never refuse)."""
    session_id = args.session
    if not session_id:
        print(json.dumps({"error": "--session is required"}), file=sys.stderr)
        return 2
    key = (args.key or "").strip()
    if not key:
        print(json.dumps({"error": "--key is required"}), file=sys.stderr)
        return 2
    text = args.text if args.text is not None else ""
    source = (args.source or "tool").strip().lower()
    if source not in VALID_BELIEF_SOURCES:
        print(json.dumps({
            "error": f"source must be one of {list(VALID_BELIEF_SOURCES)}",
            "source": source,
        }), file=sys.stderr)
        return 2
    conf_arg = float(args.conf) if args.conf is not None else 0.9
    parent_key = (getattr(args, "parent_key", None) or "").strip() or None

    doc = _load(session_id)
    beliefs = doc.get("beliefs")
    if not isinstance(beliefs, dict):
        beliefs = {}
        doc["beliefs"] = beliefs

    parent = beliefs.get(parent_key) if parent_key else None
    if not isinstance(parent, dict):
        parent = None

    if source == "user":
        hops = 0
    elif parent_key and parent is not None:
        try:
            hops = int(parent.get("hops", 0)) + 1
        except (TypeError, ValueError):
            hops = 1
    else:
        hops = 1

    parent_conf: float | None = None
    if parent is not None and parent.get("conf") is not None:
        try:
            parent_conf = float(parent["conf"])
        except (TypeError, ValueError):
            parent_conf = None
    conf = min(conf_arg, parent_conf) if parent_conf is not None else conf_arg

    dpi_violation = False
    if hops >= 2 and parent_key and parent is not None:
        goal = doc.get("goal")
        goal_tokens = _belief_tokens(goal) if goal else set()
        overlap_self = len(_belief_tokens(text) & goal_tokens) / max(1, len(goal_tokens))
        overlap_parent = (
            len(_belief_tokens(parent.get("text") or "") & goal_tokens)
            / max(1, len(goal_tokens))
        )
        dpi_violation = overlap_self > overlap_parent + 0.05
        if dpi_violation and parent_conf is not None:
            conf = min(conf, parent_conf)  # cap, don't raise; still store

    entry = {
        "text": text,
        "source": source,
        "hops": hops,
        "conf": conf,
        "parent_key": parent_key,
        "ts": _now(),
        "dpi_violation": dpi_violation,
    }
    beliefs[key] = entry
    p = _save(doc)
    print(json.dumps({"ok": True, "path": str(p), "key": key, "belief": entry}, indent=2))
    return 0


def cmd_get_belief(args: argparse.Namespace) -> int:
    """Return the stored belief dict for KEY."""
    session_id = args.session
    if not session_id:
        print(json.dumps({"error": "--session is required"}), file=sys.stderr)
        return 2
    key = (args.key or "").strip()
    if not key:
        print(json.dumps({"error": "--key is required"}), file=sys.stderr)
        return 2
    doc = _load(session_id)
    raw_beliefs = doc.get("beliefs")
    beliefs: dict[str, Any] = raw_beliefs if isinstance(raw_beliefs, dict) else {}
    if key not in beliefs:
        print(json.dumps({"error": f"belief not found: {key}", "key": key}))
        return 1
    print(json.dumps(beliefs[key], indent=2, ensure_ascii=False))
    return 0


def cmd_belief_chain(args: argparse.Namespace) -> int:
    """Walk parent_key links; emit provenance list from root to KEY."""
    session_id = args.session
    if not session_id:
        print(json.dumps({"error": "--session is required"}), file=sys.stderr)
        return 2
    key = (args.key or "").strip()
    if not key:
        print(json.dumps({"error": "--key is required"}), file=sys.stderr)
        return 2
    doc = _load(session_id)
    raw_beliefs = doc.get("beliefs")
    beliefs: dict[str, Any] = raw_beliefs if isinstance(raw_beliefs, dict) else {}
    if key not in beliefs:
        print(json.dumps({"error": f"belief not found: {key}", "key": key, "chain": []}))
        return 1

    chain_rev: list[dict[str, Any]] = []
    seen: set[str] = set()
    cur: str | None = key
    while cur:
        if cur in seen:
            break
        seen.add(cur)
        bel = beliefs.get(cur)
        if not isinstance(bel, dict):
            break
        item = dict(bel)
        item["key"] = cur
        chain_rev.append(item)
        nxt = bel.get("parent_key")
        cur = str(nxt).strip() if nxt else None

    chain_rev.reverse()
    print(json.dumps(chain_rev, indent=2, ensure_ascii=False))
    return 0


def _constraint_text(item: Any) -> str | None:
    """Extract a parseable constraint string (dict.text or raw str). Diagnostic only."""
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        text = item.get("text")
        if text is None:
            return None
        return str(text)
    if item is None:
        return None
    return str(item)


def _parse_constraint_kv(text: str) -> tuple[str, str] | None:
    """Split on first ':' or '=' or whitespace-padded '='. None if unclean."""
    s = str(text).strip()
    if not s:
        return None
    m = re.search(r"\s*=\s*|[=:]", s)
    if not m:
        return None
    key = s[: m.start()].strip()
    value = s[m.end() :].strip()
    if not key or not value:
        return None
    return key, value


def cmd_check_constraints(args: argparse.Namespace) -> int:
    """DPLL-WM: diagnostic-only contradiction check on WM constraints (Harrison)."""
    empty = {
        "constraints_consistent": True,
        "total_constraints": 0,
        "parsed": 0,
        "unparseable": 0,
        "contradictions": [],
        "diagnostic_only": True,
    }
    session_id = args.session
    if not session_id:
        print(json.dumps(empty))
        return 0
    doc = _load(session_id)
    raw = doc.get("constraints")
    if not raw:
        print(json.dumps(empty))
        return 0
    if not isinstance(raw, list):
        raw = [raw]

    grouped: dict[str, dict[str, list[str]]] = {}
    parsed = 0
    unparseable = 0
    for item in raw:
        text = _constraint_text(item)
        if text is None:
            unparseable += 1
            continue
        kv = _parse_constraint_kv(text)
        if kv is None:
            unparseable += 1
            continue
        parsed += 1
        key, value = kv
        slot = grouped.setdefault(key, {"values": [], "constraint_texts": []})
        if value not in slot["values"]:
            slot["values"].append(value)
        slot["constraint_texts"].append(text)

    contradictions = [
        {
            "key": key,
            "values": slot["values"],
            "constraint_texts": slot["constraint_texts"],
        }
        for key, slot in grouped.items()
        if len(slot["values"]) > 1
    ]
    print(json.dumps({
        "constraints_consistent": len(contradictions) == 0,
        "total_constraints": len(raw),
        "parsed": parsed,
        "unparseable": unparseable,
        "contradictions": contradictions,
        "diagnostic_only": True,
    }))
    return 0


def cmd_belief_syndrome(args: argparse.Namespace) -> int:
    """Scan beliefs for conf > parent.conf (Lin-Costello syndrome). Diagnostic only."""
    session_id = args.session or ""
    empty = {
        "session": session_id,
        "n_beliefs": 0,
        "syndrome_count": 0,
        "syndrome": [],
        "clean": True,
    }
    if not session_id:
        print(json.dumps(empty))
        return 0
    doc = _load(session_id)
    beliefs = doc.get("beliefs")
    if not isinstance(beliefs, dict) or not beliefs:
        print(json.dumps(empty))
        return 0

    syndrome: list[dict[str, Any]] = []
    for key, bel in beliefs.items():
        if not isinstance(bel, dict):
            continue
        parent_key = bel.get("parent_key")
        if not parent_key:
            continue
        parent_key_s = str(parent_key).strip()
        parent = beliefs.get(parent_key_s)
        if not isinstance(parent, dict):
            continue
        try:
            conf = float(bel["conf"])
            parent_conf = float(parent["conf"])
        except (KeyError, TypeError, ValueError):
            continue
        violation_magnitude = conf - parent_conf
        if violation_magnitude > 0:
            syndrome.append({
                "key": key,
                "conf": conf,
                "parent_key": parent_key_s,
                "parent_conf": parent_conf,
                "violation_magnitude": violation_magnitude,
            })

    print(json.dumps({
        "session": session_id,
        "n_beliefs": len(beliefs),
        "syndrome_count": len(syndrome),
        "syndrome": syndrome,
        "clean": len(syndrome) == 0,
    }))
    return 0


def _wm_beliefs(doc: dict[str, Any]) -> dict[str, dict[str, Any]]:
    raw = doc.get("beliefs")
    if not isinstance(raw, dict):
        return {}
    return {str(k): v for k, v in raw.items() if isinstance(v, dict)}


def _belief_conf_hops(bel: dict[str, Any]) -> tuple[float, int]:
    try:
        conf = float(bel["conf"]) if bel.get("conf") is not None else float("inf")
    except (TypeError, ValueError):
        conf = float("inf")
    try:
        hops = int(bel.get("hops", 0) or 0)
    except (TypeError, ValueError):
        hops = 0
    return conf, hops


def cmd_belief_limit(args: argparse.Namespace) -> int:
    """Most conservative belief: lowest conf, then highest hops, then key. Read-only."""
    session_id = args.session
    if not session_id:
        print(json.dumps({"error": "--session is required"}), file=sys.stderr)
        return 2
    doc = _load(session_id)
    beliefs = _wm_beliefs(doc)
    n = len(beliefs)
    if n == 0:
        print(json.dumps({
            "session": session_id,
            "n_beliefs": 0,
            "result": None,
            "diagnostic_only": True,
        }))
        return 0
    ranked: list[tuple[float, int, str, dict[str, Any]]] = []
    for key, bel in beliefs.items():
        conf, hops = _belief_conf_hops(bel)
        ranked.append((conf, -hops, key, bel))
    ranked.sort(key=lambda t: (t[0], t[1], t[2]))
    conf, neg_hops, key, bel = ranked[0]
    print(json.dumps({
        "session": session_id,
        "key": key,
        "conf": conf if math.isfinite(conf) else None,
        "hops": -neg_hops,
        "text": bel.get("text"),
        "n_beliefs": n,
        "diagnostic_only": True,
    }))
    return 0


def cmd_belief_colimit(args: argparse.Namespace) -> int:
    """Union token coverage of all belief texts. Read-only."""
    import re

    def _colimit_tokens(text: str) -> list[str]:
        return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if len(t) >= 2]

    session_id = args.session
    if not session_id:
        print(json.dumps({"error": "--session is required"}), file=sys.stderr)
        return 2
    doc = _load(session_id)
    beliefs = _wm_beliefs(doc)
    n = len(beliefs)
    if n == 0:
        print(json.dumps({
            "session": session_id,
            "n_beliefs": 0,
            "union_tokens": 0,
            "total_tokens_with_repetition": 0,
            "vocab_coverage_pct": 0.0,
            "diagnostic_only": True,
        }))
        return 0
    union: set[str] = set()
    total_token_count = 0
    for bel in beliefs.values():
        text = str(bel.get("text") or "")
        tokens = _colimit_tokens(text)
        total_token_count += len(tokens)
        union.update(tokens)
    unique_token_count = len(union)
    ratio = unique_token_count / max(1, total_token_count)
    print(json.dumps({
        "session": session_id,
        "n_beliefs": n,
        "union_tokens": unique_token_count,
        "total_tokens_with_repetition": total_token_count,
        "vocab_coverage_pct": ratio,
        "diagnostic_only": True,
    }))
    return 0


def cmd_norm(args: argparse.Namespace) -> int:
    """ROY-7: Lp norms of the belief/confidence vector.

    (1) L2 norm: sqrt(sum(conf^2))
    (2) L-infinity norm: max(conf)
    (3) Count of entries with conf > threshold (default 0.5)
    Reads 'conf' field from each belief entry in the session WM.
    """
    session_id = args.session
    if not session_id:
        print(json.dumps({"error": "--session is required"}, file=sys.stderr))
        return 2
    threshold = float(getattr(args, "threshold", 0.5))
    doc = _load(session_id)
    beliefs = _wm_beliefs(doc)

    if not beliefs:
        print(json.dumps({
            "session": session_id,
            "n_beliefs": 0,
            "l2_norm": 0.0,
            "linf_norm": 0.0,
            "count_above_threshold": 0,
            "threshold": threshold,
            "diagnostic_only": True,
            "note": "No beliefs found in this session.",
        }, indent=2))
        return 0

    conf_values: list[float] = []
    for key, bel in beliefs.items():
        if not isinstance(bel, dict):
            continue
        raw_conf = bel.get("conf")
        if raw_conf is None:
            continue
        try:
            conf_values.append(float(raw_conf))
        except (TypeError, ValueError):
            continue

    if not conf_values:
        print(json.dumps({
            "session": session_id,
            "n_beliefs": len(beliefs),
            "l2_norm": 0.0,
            "linf_norm": 0.0,
            "count_above_threshold": 0,
            "threshold": threshold,
            "diagnostic_only": True,
            "note": "No numeric conf values found in beliefs.",
        }, indent=2))
        return 0

    l2_norm = math.sqrt(sum(c * c for c in conf_values))
    linf_norm = max(conf_values)
    count_above = sum(1 for c in conf_values if c > threshold)

    print(json.dumps({
        "session": session_id,
        "n_beliefs": len(beliefs),
        "n_conf_values": len(conf_values),
        "l2_norm": round(l2_norm, 6),
        "linf_norm": round(linf_norm, 6),
        "count_above_threshold": count_above,
        "threshold": threshold,
        "mean_conf": round(sum(conf_values) / len(conf_values), 6),
        "diagnostic_only": True,
        "note": (
            "L2 = sqrt(sum(conf^2)); Linf = max(conf); count = |{k: conf_k > threshold}|. "
            "ROY-7 Royden-Fitzpatrick Lp norm diagnostics on WM belief vector."
        ),
    }, indent=2))
    return 0


RISK_FLOOR_PATH = HERMES_HOME / "cache" / "loop-harness" / "risk-floor.json"
VALID_VARIANT_ORDERS = ("nat_lt", "lex_nat", "finset_card")


def cmd_risk_floor(args: argparse.Namespace) -> int:
    """Loop risk floor management — monotonically increasing risk floor.

    The risk floor tracks the maximum risk score seen so far in a loop harness.
    It can only be raised (never lowered) via --update; --clear is an explicit user reset.

    Floor file: ~/.hermes/cache/loop-harness/risk-floor.json
    Schema: {floor: float, updated_at: ISO timestamp}
    """
    floor_path = RISK_FLOOR_PATH

    def _load_floor() -> dict[str, Any]:
        if floor_path.exists():
            try:
                data = json.loads(floor_path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return data
            except (OSError, json.JSONDecodeError):
                pass
        return {"floor": 0.0, "updated_at": _now()}

    def _save_floor(floor: float) -> None:
        floor_path.parent.mkdir(parents=True, exist_ok=True)
        floor_path.write_text(
            json.dumps({"floor": floor, "updated_at": _now()}, indent=2) + "\n",
            encoding="utf-8",
        )
        # Sync to config.yaml loop_harness.loop_risk_floor so the canonical config key
        # stays current with the runtime floor (F-TRG-01 implementation).
        # Always target the default profile config (not fork override) since loop_harness
        # is defined there; fork config.yaml is a thin override with no loop_harness section.
        try:
            import re as _re
            from pathlib import Path as _Path
            # Try HERMES_HOME first, fall back to ~/.hermes (canonical)
            for _cfg_path in [HERMES_HOME / "config.yaml", _Path.home() / ".hermes" / "config.yaml"]:
                if _cfg_path.exists():
                    txt = _cfg_path.read_text(encoding="utf-8")
                    if "loop_risk_floor:" in txt:
                        txt2 = _re.sub(
                            r"(loop_risk_floor:\s*)[\d.]+([^\n]*)",
                            lambda m: m.group(1) + str(floor) + m.group(2),
                            txt,
                        )
                        if txt2 != txt:
                            _cfg_path.write_text(txt2, encoding="utf-8")
                        break  # stop at first config that has the key
        except Exception:
            pass  # config sync is best-effort; floor file is authoritative

    update_val = getattr(args, "update", None)
    do_get    = getattr(args, "get", False)
    do_clear  = getattr(args, "clear", False)

    if update_val is not None:
        new_floor = float(update_val)
        current = _load_floor()
        current_floor = float(current.get("floor", 0.0))
        if new_floor < current_floor:
            print(json.dumps({
                "ok": False,
                "message": f"Ignored: new floor {new_floor} < current floor {current_floor} (floor only raises)",
                "floor": current_floor,
                "updated_at": current.get("updated_at"),
            }))
        else:
            _save_floor(new_floor)
            print(json.dumps({
                "ok": True,
                "floor": new_floor,
                "previous_floor": current_floor,
                "updated_at": _now(),
            }))
    elif do_get:
        data = _load_floor()
        print(json.dumps({"floor": data.get("floor", 0.0), "updated_at": data.get("updated_at")}))
    elif do_clear:
        _save_floor(0.0)
        print(json.dumps({"ok": True, "floor": 0.0, "updated_at": _now(),
                          "note": "Explicit user reset — floor cleared to 0.0"}))
    else:
        data = _load_floor()
        print(json.dumps({"floor": data.get("floor", 0.0), "updated_at": data.get("updated_at"),
                          "note": "Use --update FLOAT to raise, --get to read, --clear to reset"}))
    return 0





def _jsonable_variant(value: Any) -> Any:
    if isinstance(value, tuple):
        return list(value)
    return value


def _parse_variant_value(raw: Any, order: str) -> Any:
    """Parse a variant against a declared well-founded order (THOMPSON-4)."""
    text = str(raw).strip()
    if order == "nat_lt":
        return int(text, 10)
    if order == "finset_card":
        return int(text, 10)
    if order == "lex_nat":
        parts = [p.strip() for p in text.split(",")]
        if not parts or any(p == "" for p in parts):
            raise ValueError("lex_nat requires a comma-separated tuple of ints")
        return tuple(int(p, 10) for p in parts)
    raise ValueError(f"unknown order {order!r}")


def _coerce_stored_variant(stored: Any, order: str) -> Any:
    if stored is None:
        return None
    if order == "lex_nat":
        if isinstance(stored, (list, tuple)):
            return tuple(int(x) for x in stored)
        return _parse_variant_value(stored, order)
    if isinstance(stored, bool) or not isinstance(stored, int):
        return _parse_variant_value(stored, order)
    return int(stored)


def _strictly_decreases(current: Any, prev: Any, order: str) -> bool:
    """Strict decrease: nat_lt/finset_card use int <; lex_nat is lexicographic."""
    if order == "lex_nat":
        return tuple(current) < tuple(prev)
    return current < prev


def cmd_variant_declare(args: argparse.Namespace) -> int:
    """THOMPSON-4: declare a well-founded loop variant (name + order)."""
    session_id = args.session or "default"
    name = (args.name or "").strip()
    order = (args.order or "").strip()
    if not name:
        print(json.dumps({"ok": False, "error": "--name is required"}))
        return 2
    if order not in VALID_VARIANT_ORDERS:
        print(json.dumps({
            "ok": False,
            "error": f"order must be one of {list(VALID_VARIANT_ORDERS)}",
            "order": order,
        }))
        return 2
    doc = _load(session_id)
    decl = {"name": name, "order": order, "prev": None}
    doc["variant_decl"] = decl
    doc["variant_history"] = []
    p = _save(doc)
    print(json.dumps({"ok": True, "path": str(p), "variant_decl": decl}, indent=2))
    return 0


def cmd_variant_check(args: argparse.Namespace) -> int:
    """Huth-Ryan §4.5 total-correctness loop variant (lower is better).

    THOMPSON-4: require a prior variant-declare; compare under the named
    well-founded order. Existing 3-step stall remains as fallback when a
    declaration is present and the order check passes.
    """
    session_id = args.session or "default"
    doc = _load(session_id)
    decl = doc.get("variant_decl")
    if not isinstance(decl, dict) or not decl.get("order"):
        # No variant-declare: fall back to the existing 3-step stall heuristic.
        # WARN only — do not HALT; undeclared variants are common in existing loops.
        print(json.dumps({
            "stalled": False,
            "action": "CONTINUE",
            "warning": "undeclared_variant; no variant-declare found; falling back to stall heuristic",
        }))
        return 0

    order = str(decl.get("order") or "").strip()
    if order not in VALID_VARIANT_ORDERS:
        # Unknown order is a misconfiguration — WARN but still continue via stall path.
        print(json.dumps({
            "stalled": False,
            "action": "CONTINUE",
            "warning": f"unknown variant order {order!r}; falling back to stall heuristic",
        }))
        return 0

    try:
        current = _parse_variant_value(args.variant, order)
    except (TypeError, ValueError) as exc:
        print(json.dumps({
            "stalled": False,
            "action": "HALT",
            "reason": "variant_parse_error",
            "order": order,
            "error": str(exc),
        }))
        return 1

    prev_raw = decl.get("prev")
    prev = _coerce_stored_variant(prev_raw, order) if prev_raw is not None else None
    decreased = True
    if prev is not None:
        decreased = _strictly_decreases(current, prev, order)

    hist = doc.setdefault("variant_history", [])
    hist.append(_jsonable_variant(current))
    decl["prev"] = _jsonable_variant(current)
    doc["variant_decl"] = decl
    _save(doc)

    if prev is not None and not decreased:
        print(json.dumps({
            "stalled": False,
            "action": "HALT",
            "reason": "variant_not_decreasing",
            "order": order,
            "prev": _jsonable_variant(prev),
            "variant": _jsonable_variant(current),
        }))
        return 1

    # Fallback: existing 3-step non-decreasing stall (order check passed).
    try:
        if len(hist) >= 3 and hist[-3] <= hist[-2] <= hist[-1]:
            print(json.dumps({
                "stalled": True,
                "action": "HALT_TOTAL_INCORRECT",
                "variant": _jsonable_variant(current),
                "variant_history": hist[-3:],
                "order": order,
            }))
            return 0
    except TypeError:
        pass

    suffix = 1 if hist else 0
    try:
        for i in range(len(hist) - 1, 0, -1):
            if hist[i] >= hist[i - 1]:
                suffix += 1
            else:
                break
    except TypeError:
        suffix = 1
    steps_until_stall = max(0, 3 - suffix)
    print(json.dumps({
        "stalled": False,
        "action": "CONTINUE",
        "steps_until_stall": steps_until_stall,
        "variant": _jsonable_variant(current),
        "order": order,
    }))
    return 0


def cmd_cauchy_check(args: argparse.Namespace) -> int:
    """KREYSZIG-5: pairwise Jaccard Cauchy check on WM progress token sets."""
    import re
    session_id = args.session
    if not session_id:
        print(json.dumps({"error": "--session is required", "cauchy": "INCONCLUSIVE", "action": "WAIT"}))
        return 2
    m = int(getattr(args, "m", 6) or 6)
    doc = _load(session_id)
    progress = list(doc.get("progress") or [])
    window = progress[-m:] if m > 0 else []

    def toks(item: Any) -> set[str]:
        if isinstance(item, dict):
            text = str(item.get("text") or item.get("note") or json.dumps(item))
        else:
            text = str(item)
        return set(re.findall(r"[a-z0-9]+", text.lower()))

    second = window[len(window) // 2 :]
    token_sets = [toks(x) for x in second]
    dists: list[float] = []
    for i in range(len(token_sets)):
        for j in range(i + 1, len(token_sets)):
            a, b = token_sets[i], token_sets[j]
            union = a | b
            if not union:
                dists.append(0.0)
            else:
                dists.append(1.0 - len(a & b) / len(union))
    cauchy_eps = max(dists) if dists else None
    note = None
    if len(progress) >= m and cauchy_eps is not None and cauchy_eps > 0.5:
        cauchy, action = "NOT_CAUCHY", "INCONCLUSIVE"
        note = "progress is diverse; may indicate branching work or stalled loop"
    elif cauchy_eps is not None and cauchy_eps < 0.15:
        cauchy, action = "CAUCHY", "CONTINUE"
    else:
        cauchy, action = "INCONCLUSIVE", "WAIT"
    out = {
        "cauchy": cauchy,
        "action": action,
        "cauchy_eps": cauchy_eps,
        "warning": "cauchy_replan removed: diverse progress is not stalling evidence",
    }
    if note:
        out["note"] = note
    print(json.dumps(out))
    return 0


def _record_skills(rec: dict[str, Any]) -> list[str]:
    skills = rec.get("active_skills")
    if skills is None:
        skills = rec.get("skills") or []
    if not isinstance(skills, list):
        skills = [skills]
    return [str(s) for s in skills if s is not None and str(s) != ""]


def _shannon_entropy(skills: list[str]) -> float:
    total = max(1, len(skills))
    counts = Counter(skills)
    h = 0.0
    for c in counts.values():
        p = c / total
        if p > 0.0:
            h -= p * math.log2(p)
    return h


def _mean_std(values: list[float]) -> tuple[float, float]:
    n = len(values)
    if n == 0:
        return 0.0, 0.0
    mean = sum(values) / n
    if n < 2:
        return mean, 0.0
    var = sum((x - mean) ** 2 for x in values) / (n - 1)
    return mean, math.sqrt(var)


def cmd_skill_entropy(args: argparse.Namespace) -> int:
    """Per-session skill Shannon entropy vs cross-session mean/std (diagnostic)."""
    records = _read_skill_sequences()
    empty = {"n_sessions": 0, "H": None, "diagnostic_only": True}
    if not records:
        print(json.dumps(empty))
        return 0

    sid = getattr(args, "session", None)
    use_all = bool(getattr(args, "all_sessions", False))
    if sid and not use_all:
        records = [r for r in records if str(r.get("session", "")) == str(sid)]
        if not records:
            print(json.dumps(empty))
            return 0

    grouped: dict[str, list[str]] = {}
    order: list[str] = []
    for rec in records:
        sess = str(rec.get("session", "") or "")
        if sess not in grouped:
            grouped[sess] = []
            order.append(sess)
        grouped[sess].extend(_record_skills(rec))

    if not grouped:
        print(json.dumps(empty))
        return 0

    entropies: dict[str, float] = {s: _shannon_entropy(sk) for s, sk in grouped.items()}
    hs = [entropies[s] for s in order]
    mean_h, std_h = _mean_std(hs)
    current = str(sid) if (sid and not use_all) else order[-1]
    h = entropies.get(current, _shannon_entropy([]))
    low_diversity = bool(std_h > 0.0 and h < (mean_h - 2.0 * std_h))
    print(json.dumps({
        "session": current,
        "H": h,
        "mean_H": mean_h,
        "std_H": std_h,
        "n_sessions": len(grouped),
        "low_diversity": low_diversity,
        "diagnostic_only": True,
    }))
    return 0


def cmd_skill_mi(args: argparse.Namespace) -> int:
    """Pairwise skill co-occurrence mutual information (4-cell Bernoulli MI)."""
    skill_a = str(args.skill_a)
    skill_b = str(args.skill_b)
    records = _read_skill_sequences()
    n = len(records)

    def _insufficient(n_sessions: int) -> int:
        print(json.dumps({
            "n_sessions": n_sessions,
            "MI": None,
            "reason": "insufficient_data",
            "diagnostic_only": True,
        }))
        return 0

    if n < 2:
        return _insufficient(n)

    n_a = 0
    n_b = 0
    n_ab = 0
    for rec in records:
        skills = set(_record_skills(rec))
        has_a = skill_a in skills
        has_b = skill_b in skills
        if has_a:
            n_a += 1
        if has_b:
            n_b += 1
        if has_a and has_b:
            n_ab += 1

    if n_a == 0 or n_b == 0:
        return _insufficient(n)

    # 4-cell counts
    n11 = n_ab
    n10 = n_a - n_ab
    n01 = n_b - n_ab
    n00 = n - n_a - n_b + n_ab

    # 4-cell probabilities
    p11 = n11 / n
    p10 = n10 / n
    p01 = n01 / n
    p00 = n00 / n

    # marginals
    p_a_marg = n_a / n    # = p11 + p10
    p_b_marg = n_b / n    # = p11 + p01
    p_na = 1.0 - p_a_marg
    p_nb = 1.0 - p_b_marg

    # MI = sum over 4 cells of p_ij * log2(p_ij / (p_i * p_j))
    mi = 0.0
    cells = [
        (p11, p_a_marg, p_b_marg),
        (p10, p_a_marg, p_nb),
        (p01, p_na,     p_b_marg),
        (p00, p_na,     p_nb),
    ]
    for (p_joint, p_row, p_col) in cells:
        if p_joint > 0 and p_row > 0 and p_col > 0:
            mi += p_joint * math.log2(p_joint / (p_row * p_col))

    # MI >= 0 always for Bernoulli variables; competitive is structurally impossible
    # Keep the field for API stability but document it
    synergistic = (mi > 0.01)
    competitive = False  # MI >= 0 always; field kept for API stability

    print(json.dumps({
        "skill_a": skill_a,
        "skill_b": skill_b,
        "MI": mi,
        "p_a": p_a_marg,
        "p_b": p_b_marg,
        "p_ab": p11,
        "n_a": n_a,
        "n_b": n_b,
        "n_ab": n_ab,
        "n_sessions": n,
        "synergistic": synergistic,
        "competitive": competitive,
        "diagnostic_only": True,
    }))
    return 0


def _read_skill_sequences() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if not skill_sequence_log.exists():
        return records
    try:
        text = skill_sequence_log.read_text(encoding="utf-8")
    except OSError:
        return records
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(rec, dict):
            records.append(rec)
    return records


def _bigram_counts(
    records: list[dict[str, Any]],
) -> tuple[dict[str, dict[str, int]], list[tuple[str, str]], set[str]]:
    table: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    pairs: list[tuple[str, str]] = []
    vocab: set[str] = set()
    for rec in records:
        skills = rec.get("skills") or []
        if not isinstance(skills, list):
            continue
        seq = [str(s) for s in skills if s is not None and str(s) != ""]
        vocab.update(seq)
        for a, b in zip(seq, seq[1:]):
            table[a][b] += 1
            pairs.append((a, b))
    return {cur: dict(row) for cur, row in table.items()}, pairs, vocab


def _laplace_cond(
    table: dict[str, dict[str, int]],
    current: str,
    nxt: str,
    vocab_size: int,
    alpha: float = 1.0,
) -> float:
    row = table.get(current) or {}
    cx = sum(row.values())
    cxy = int(row.get(nxt, 0))
    denom = cx + alpha * max(int(vocab_size), 1)
    return (cxy + alpha) / denom


def _occam_rank(query: str) -> list[dict[str, Any]]:
    script = Path(__file__).parent / "occam-skill-ranker.py"
    try:
        proc = subprocess.run(
            ["python3", str(script), query],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"warning: occam-skill-ranker failed: {exc}", file=sys.stderr)
        return []
    raw = (proc.stdout or "").strip()
    if not raw:
        return []
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict):
        results = payload.get("results")
        if isinstance(results, list):
            return [x for x in results if isinstance(x, dict)]
    return []


def cmd_bigrams(args: argparse.Namespace) -> int:
    """GALLAGER-4: P(next|current) bigrams with Laplace α=1; optional Occam re-rank."""
    records = _read_skill_sequences()
    n_sequences = len(records)
    if n_sequences < 10:
        print(json.dumps({
            "status": "cold_start",
            "n_sequences": n_sequences,
            "note": "need ~50 sessions for meaningful bigrams",
        }))
        return 0

    min_count = int(getattr(args, "min_count", 2) or 2)
    table, pairs, vocab = _bigram_counts(records)
    v = len(vocab)
    mi = 0.0
    if pairs:
        n = len(pairs)
        joint = Counter(pairs)
        px = Counter(a for a, _ in pairs)
        py = Counter(b for _, b in pairs)
        for (x, y), c in joint.items():
            pxy = c / n
            den = (px[x] / n) * (py[y] / n)
            if pxy > 0.0 and den > 0.0:
                mi += pxy * math.log2(pxy / den)

    transitions: list[dict[str, Any]] = []
    for cur, row in table.items():
        for nxt in row:
            p = _laplace_cond(table, cur, nxt, v, alpha=1.0)
            transitions.append({"from": cur, "to": nxt, "prob": round(p, 6)})
    transitions.sort(key=lambda t: (-t["prob"], t["from"], t["to"]))

    out: dict[str, Any] = {
        "bigram_table": table,
        "mutual_info": round(mi, 6),
        "n_sequences": n_sequences,
        "top_transitions": transitions[:20],
    }

    query = (getattr(args, "query", None) or "").strip()
    if query:
        ranked = _occam_rank(query)
        current = None
        if records:
            last_skills = records[-1].get("skills") or []
            if isinstance(last_skills, list) and last_skills:
                current = str(last_skills[-1])
        reranked: list[dict[str, Any]] = []
        for item in ranked:
            name = str(item.get("name") or "")
            try:
                occam_score = float(item.get("score") or 0.0)
            except (TypeError, ValueError):
                occam_score = 0.0
            bonus = 0.0
            if current and name:
                cnt = int((table.get(current) or {}).get(name, 0))
                if cnt >= min_count:
                    p = max(_laplace_cond(table, current, name, v, alpha=1.0), 1e-12)
                    bonus = -math.log(p)
            combined = 0.7 * occam_score + 0.3 * bonus
            reranked.append({**item, "bigram_bonus": bonus, "combined_score": combined})
        reranked.sort(key=lambda x: -float(x.get("combined_score") or 0.0))
        out["query"] = query
        out["current"] = current
        out["ranked"] = reranked

    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--session", "-s", required=False, default=None, help="Session id (not required for plan-from-memory, handoff-export)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_pfm = sub.add_parser("plan-from-memory", help="Retrieve prior analog task plans (Synapse/ACL 2026)")
    p_pfm.add_argument("--task-summary", required=True, help="Brief description of current task")
    p_pfm.add_argument("--backward-plan", action="store_true", dest="backward_plan",
                       help="Also plan goal→init and check forward/backward consistency (arXiv:2411.01790)")
    p_pfm.set_defaults(func=cmd_plan_from_memory)

    p_init = sub.add_parser("init", help="Create/update WM shell")
    p_init.add_argument("--session", required=False, help="Session id")
    p_init.add_argument("--goal", default="")
    p_init.add_argument("--reset", action="store_true")
    p_init.add_argument("--wipe-constraints", action="store_true")
    p_init.add_argument("--mac-verify", dest="mac_verify", action="store_true",
                        help="CRYPTO-5: append HMAC-SHA256 MAC field to stored document")
    p_init.set_defaults(func=cmd_init)

    p_set = sub.add_parser("set", help="Set goal/progress/next/open_decisions/active_skills")
    p_set.add_argument("--session", required=False, help="Session id")
    p_set.add_argument("--key", required=True)
    p_set.add_argument("--value", required=True, help="JSON list or plain string")
    p_set.set_defaults(func=cmd_set)

    p_upd = sub.add_parser("update", help="Patch WM JSON; log active_skills sequences")
    p_upd.add_argument("--session", required=False, help="Session id")
    p_upd.add_argument("--json", dest="json", default="", help="JSON object of fields to merge")
    p_upd.add_argument(
        "--active-skills", dest="active_skills", default=None,
        help="JSON list of active skills (GALLAGER-4 sequence log)",
    )
    p_upd.set_defaults(func=cmd_update)

    p_bg = sub.add_parser("bigrams", help="GALLAGER-4 skill-sequence bigrams P(next|current)")
    p_bg.add_argument("--min-count", dest="min_count", type=int, default=2,
                      help="Min bigram count to apply -log P bonus (default 2)")
    p_bg.add_argument("--query", default="", help="Re-rank occam-skill-ranker output with bigram bonus")
    p_bg.set_defaults(func=cmd_bigrams)

    p_se = sub.add_parser("skill-entropy", help="Per-session skill Shannon entropy diagnostic")
    se_group = p_se.add_mutually_exclusive_group()
    se_group.add_argument("--session", dest="session", default=None, help="Filter to this session id")
    se_group.add_argument("--all", dest="all_sessions", action="store_true",
                          help="Use all skill-sequence sessions")
    p_se.set_defaults(func=cmd_skill_entropy)

    p_smi = sub.add_parser("skill-mi", help="Pairwise skill co-occurrence MI diagnostic")
    p_smi.add_argument("--skill-a", dest="skill_a", required=True)
    p_smi.add_argument("--skill-b", dest="skill_b", required=True)
    p_smi.set_defaults(func=cmd_skill_mi)

    p_ac = sub.add_parser("add-constraint", help="Add action-binding constraint")
    p_ac.add_argument("--session", required=False, help="Session id")
    p_ac.add_argument("--text", required=True)
    p_ac.add_argument("--binding", default="must", choices=VALID_BINDINGS)
    p_ac.add_argument("--authority", default="user")
    p_ac.add_argument("--fallback", default="")
    p_ac.add_argument("--consequence", default="")
    p_ac.add_argument("--source-context", default=None, dest="source_context",
                      help="BCIT: source context where this constraint was learned (e.g. 'session:abc' or 'skill:name')")
    p_ac.add_argument("--predecessor-model", default=None, dest="predecessor_model",
                      help="BCIT: model that generated this constraint")
    p_ac.set_defaults(func=cmd_add_constraint)

    p_sh = sub.add_parser("skill-hint", help="Compact WM for skill selection")
    p_sh.set_defaults(func=cmd_skill_hint)

    # HyperSkill: record skill combination for hyperedge tracking (arXiv:2608.16114)
    p_rsc = sub.add_parser("record-skill-combo", help="Record skill combo for HyperSkill hyperedge tracking")
    p_rsc.add_argument("--skills", nargs="+", required=True, help="Space-separated skill names loaded for this task")
    p_rsc.add_argument("--task-type", default="general", help="Task type category")
    p_rsc.set_defaults(func=cmd_record_skill_combo)

    p_show = sub.add_parser("show", help="Dump full WM JSON")
    p_show.add_argument("--mac-verify", dest="mac_verify", action="store_true",
                        help="CRYPTO-5: recompute HMAC-SHA256 and flag any mismatch")
    p_show.set_defaults(func=cmd_show)

    p_lf = sub.add_parser("localize-failure", help="Record failure component (Recuris evidence)")
    p_lf.add_argument("--component", required=True, choices=VALID_COMPONENTS)
    p_lf.add_argument("--note", required=True)
    p_lf.set_defaults(func=cmd_localize_failure)

    p_he = sub.add_parser("handoff-export", help="Structured WM export for session/model handoff")
    p_he.set_defaults(func=cmd_handoff_export)

    p_cl = sub.add_parser("clear", help="Delete WM file")
    p_cl.set_defaults(func=cmd_clear)

    p_vg = sub.add_parser("verify-gate", help="Abort if consecutive verify failures")
    p_vg.add_argument("--session", required=False, help="Session id")
    p_vg.set_defaults(func=cmd_verify_gate)

    p_rl = sub.add_parser("record-latency", help="Kalman EMA per-tool latency tracker")
    p_rl.add_argument("--session", required=True)
    p_rl.add_argument("--tool-name", required=True)
    p_rl.add_argument("--elapsed-s", required=True, type=float)
    p_rl.set_defaults(func=cmd_record_latency)

    p_la = sub.add_parser("lookahead", help="FLARE-style lookahead over counterfactual future trajectories")
    p_la.add_argument("--session", required=False, default=None, help="Session id (optional; ephemeral if omitted)")
    p_la.add_argument("--action", required=False, default="", help="Proposed next action")
    p_la.add_argument("--next-action", dest="next_action", default="", help="Alias for --action")
    p_la.add_argument("--task", default="", help="Alias for --goal when WM has no goal")
    p_la.add_argument("--steps-ahead", type=int, default=3, dest="steps_ahead",
                      help="Number of projected states to emit (default 3)")
    p_la.add_argument("--steps-remaining", type=int, default=None, dest="steps_remaining",
                      help="Alias for --steps-ahead")
    p_la.add_argument("--goal", default="", help="Goal text if not already in WM")
    p_la.add_argument("--constraints", default="", help="Optional extra constraints as JSON")
    p_la.set_defaults(func=cmd_lookahead)

    p_sv = sub.add_parser("subplan-verify", help="Check planned sub-steps against WM must-constraints")
    p_sv.add_argument("--session", required=False, default=None, help="Session id (optional)")
    p_sv.add_argument("--subplan", required=False, default="", help='JSON list of planned sub-steps, e.g. ["step1","step2"]')
    p_sv.add_argument("--plan", dest="plan", default="", help="Alias for --subplan")
    p_sv.add_argument("--current-step", dest="current_step", default="", help="Phase name that must appear in the plan")
    p_sv.set_defaults(func=cmd_subplan_verify)

    p_sw = sub.add_parser("switch-framework", help="Mid-task switch of active reasoning framework")
    p_sw.add_argument("--session", required=True, help="Session id")
    p_sw.add_argument("--from-framework", required=True, dest="from_framework")
    p_sw.add_argument("--to-framework", required=True, dest="to_framework")
    p_sw.add_argument("--trigger", required=True, help="Why the type shifted")
    p_sw.add_argument("--prior-verdict", default="", dest="prior_verdict")
    p_sw.add_argument(
        "--score", type=float, default=None,
        help="Trigger score for hysteresis (θ_high=0.65, θ_low=0.35)",
    )
    p_sw.add_argument(
        "--progress-delta", type=float, default=None, dest="progress_delta",
        help="Progress change; |delta|<0.05 is dead-zone ignored",
    )
    p_sw.set_defaults(func=cmd_switch_framework)

    p_bu = sub.add_parser("belief-update", help="Complementary-filter belief update (Åström-05)")
    p_bu.add_argument("--session", required=False, default=None, help="Session id")
    p_bu.add_argument("--name", required=True, help="Belief key")
    p_bu.add_argument("--slow", type=float, required=True, help="Accurate but stale measurement")
    p_bu.add_argument("--fast", type=float, required=True, help="Recent but drifting measurement")
    p_bu.add_argument("--alpha", type=float, default=0.8, help="Complementary-filter weight on slow (default 0.8)")
    p_bu.set_defaults(func=cmd_belief_update)

    p_vd = sub.add_parser("variant-declare", help="THOMPSON-4 well-founded variant declaration")
    p_vd.add_argument("--session", required=False, default=None, help="Session id")
    p_vd.add_argument("--name", required=True, help="Variant name (e.g. loop_var)")
    p_vd.add_argument(
        "--order", required=True, choices=VALID_VARIANT_ORDERS,
        help="Well-founded order: nat_lt | lex_nat | finset_card",
    )
    p_vd.set_defaults(func=cmd_variant_declare)

    p_vc = sub.add_parser("variant-check", help="Huth-Ryan §4.5 loop variant (total correctness)")
    p_vc.add_argument("--session", required=False, default=None, help="Session id")
    p_vc.add_argument(
        "--variant", required=True,
        help="Current loop variant: int (nat_lt/finset_card) or comma-separated ints (lex_nat)",
    )
    p_vc.set_defaults(func=cmd_variant_check)

    p_cc = sub.add_parser("cauchy-check", help="KREYSZIG-5 Cauchy check on progress token sets")
    p_cc.add_argument("--session", required=False, default=None, help="Session id")
    p_cc.add_argument("--m", type=int, default=6, help="Window length (default 6)")
    p_cc.set_defaults(func=cmd_cauchy_check)

    p_sb = sub.add_parser("set-belief", help="COVSHA-4 store provenance-tracked belief")
    p_sb.add_argument("--session", required=True, help="Session id")
    p_sb.add_argument("--key", required=True, help="Belief key")
    p_sb.add_argument("--text", required=True, help="Belief text")
    p_sb.add_argument("--parent-key", dest="parent_key", default=None, help="Parent belief key")
    p_sb.add_argument(
        "--source", default="tool", choices=VALID_BELIEF_SOURCES,
        help="Provenance source: user | tool | summary (default tool)",
    )
    p_sb.add_argument("--conf", type=float, default=0.9, help="Confidence (capped by parent)")
    p_sb.set_defaults(func=cmd_set_belief)

    p_gb = sub.add_parser("get-belief", help="Get a provenance belief by key")
    p_gb.add_argument("--session", required=True, help="Session id")
    p_gb.add_argument("--key", required=True, help="Belief key")
    p_gb.set_defaults(func=cmd_get_belief)

    p_bch = sub.add_parser("belief-chain", help="Walk parent_key provenance chain root→KEY")
    p_bch.add_argument("--session", required=True, help="Session id")
    p_bch.add_argument("--key", required=True, help="Belief key")
    p_bch.set_defaults(func=cmd_belief_chain)

    p_ck = sub.add_parser("check-constraints", help="DPLL-WM diagnostic constraint contradiction check")
    p_ck.add_argument("--session", required=True, help="Session id")
    p_ck.set_defaults(func=cmd_check_constraints)

    p_bsyn = sub.add_parser("belief-syndrome", help="Diagnostic DPI conf>parent syndrome scan")
    p_bsyn.add_argument("--session", required=True, help="Session id")
    p_bsyn.set_defaults(func=cmd_belief_syndrome)

    p_blim = sub.add_parser("belief-limit", help="Most conservative belief (lowest conf)")
    p_blim.add_argument("--session", required=True, help="Session id")
    p_blim.set_defaults(func=cmd_belief_limit)

    p_bcol = sub.add_parser("belief-colimit", help="Union token coverage of belief texts")
    p_bcol.add_argument("--session", required=True, help="Session id")
    p_bcol.set_defaults(func=cmd_belief_colimit)

    p_rf = sub.add_parser("risk-floor", help="Monotonically increasing loop risk floor management")
    p_rf.add_argument("--update", type=float, default=None, metavar="FLOAT",
                      help="Raise the floor to FLOAT (ignored if lower than current floor)")
    p_rf.add_argument("--get", action="store_true",
                      help="Return {floor: float, updated_at: str}")
    p_rf.add_argument("--clear", action="store_true",
                      help="Reset floor to 0.0 (explicit user reset only)")
    p_rf.set_defaults(func=cmd_risk_floor)

    # ROY-7: norm subcommand — Lp norms of the belief/confidence vector
    p_norm = sub.add_parser(
        "norm",
        help="ROY-7: Lp norms of the belief confidence vector (L2, L-inf, count > threshold)",
    )
    p_norm.add_argument("--session", required=True, help="Session id")
    p_norm.add_argument(
        "--threshold", type=float, default=0.5,
        help="Confidence threshold for count (default 0.5)",
    )
    p_norm.set_defaults(func=cmd_norm)

    args = ap.parse_args()
    return int(args.func(args) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
