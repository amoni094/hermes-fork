#!/usr/bin/env python3
"""
RR Compaction Spike — Relevance Realization two-signal scorer
==============================================================
Implements the cognitive-scope opponent-process from Vervaeke, Lillicrap & Richards (2012)
Table 1 as a compaction-time scoring function:

    score(msg) = particularization_pressure(msg) - lambda * compression_pressure(msg)

compression_pressure (cp):  tokens(msg) / max_tokens_in_window  (0..1; 1 = largest message)
particularization_pressure (pp): 0.5*density + 0.3*recency + 0.2*proximity  (0..1)

High score = KEEP. Low score = DEMOTE FIRST. (Ascending sort; lowest score demoted first.)

IMPORTANT — lambda math: to protect large high-density tool results over small low-density ones,
you need lambda < 0.235. At lambda >= 0.4 a large execute_code (density=0.85, cp~1.0) scores
lower than a small skill_view (density=0.40, cp~0.05) and would be demoted first.

IMPORTANT — simulation vs production: this script simulates budget-limited top-k selection,
which does NOT match the current runtime. The runtime (_prune_old_tool_results) demotes ALL
eligible tool results regardless of score — the sort is order-only, with no budget cap.
Enable use_rr_scorer only after adding a demotion budget limit to the runtime.

INVARIANT (Billingsley stopping-time / F_n-measurability): The compaction trigger decision
MUST be based only on current observable quantities (token count, NCD score, session state)
available BEFORE compaction runs. compaction_quality_report() is POST-HOC — it must NEVER
be used to decide whether to trigger compaction, only to log quality after the fact. Wiring
quality_report into the go/no-go trigger would make the stopping time non-adapted and would
allow the compaction decision to depend on its own outcome.

Usage:
    python rr_compaction_spike.py --session <session_id> [--lambda 0.5] [--top-k 20]
    python rr_compaction_spike.py --latest [--lambda 0.5] [--top-k 20]
    python rr_compaction_spike.py quality-report <original.txt> <kept.txt>

Output: comparison table of RR ranking vs current positional (oldest-first) pruning order,
        plus an estimated token reclaim delta.
"""

import argparse
import json
import math
import re
import sqlite3
import sys
import zlib
from pathlib import Path
from typing import Any

# OT utilities (shared; OT-9)
_OT_UTILS_PATH = Path(__file__).parent / "ot_utils.py"
if _OT_UTILS_PATH.exists():
    import importlib.util as _ilu
    _spec = _ilu.spec_from_file_location("ot_utils", _OT_UTILS_PATH)
    _ot_utils = _ilu.module_from_spec(_spec)  # type: ignore[arg-type]
    _spec.loader.exec_module(_ot_utils)  # type: ignore[union-attr]
else:
    _ot_utils = None  # type: ignore[assignment]

HERMES_HOME = Path.home() / ".hermes"
SESSION_DB = HERMES_HOME / "memory-facts" / "lifecycle.db"
LAMBDA_LOG_PATH = HERMES_HOME / "logs" / "rr-lambda-history.jsonl"


def _log_lambda(lam: float, session_id: str = "") -> None:
    """KHALIL-5: append lambda value to rr-lambda-history.jsonl for Lyapunov analysis."""
    import time as _time
    record = {
        "ts": _time.strftime("%Y-%m-%dT%H:%M:%SZ", _time.gmtime()),
        "lambda": lam,
        "session": session_id,
    }
    try:
        LAMBDA_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LAMBDA_LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except OSError:
        pass

# Tool types by expected information density (particularization weight)
# High = result is highly task-specific and irreplaceable
# Low = generic, easily re-run or re-derived
TOOL_INFO_DENSITY = {
    # High density — replacing these loses real work
    "delegate_task": 0.95,
    "execute_code": 0.85,
    "web_extract": 0.80,
    "web_search": 0.70,
    "read_file": 0.65,
    "browser_navigate": 0.65,
    "browser_snapshot": 0.60,
    # Medium
    "terminal": 0.55,
    "patch": 0.75,
    "write_file": 0.80,
    "search_files": 0.50,
    # Low density — cheap to re-retrieve
    "skill_view": 0.40,  # skill_view body is reloadable
    "hindsight_recall": 0.45,
    "hindsight_reflect": 0.40,
    "memory": 0.35,
    "clarify": 0.90,  # user answers are irreplaceable
    "browser_vision": 0.60,
    "vision_analyze": 0.60,
}
DEFAULT_DENSITY = 0.55
NCD_DEMOTION_THRESHOLD = 0.7
NCD_VOTE_PENALTY = 0.15  # additive; RR score remains the primary ranking key
NCD_PROTECT_TAIL = 32
NCD_MIN_BYTES = 64


def _message_text(msg: dict) -> str:
    content = msg.get("content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(str(p) for p in content)
    return str(content) if content is not None else ""


def _ncd_redundancy(message: str, kept_prefix: str) -> float:
    """Estimate redundancy of message given kept_prefix using zlib delta compression.
    Based on Li-Vitanyi 4ed Ch.8 NCD and incompressibility method.
    Returns 0.0 (novel) to 1.0 (fully redundant).
    Skip messages < 64 bytes (too small for zlib to be meaningful).
    """
    if len(message.encode()) < NCD_MIN_BYTES:
        return 0.0  # do not demote short messages
    z_msg = len(zlib.compress(message.encode(), level=6))
    combined = kept_prefix[-4000:] + '\n---\n' + message  # cap prefix to avoid OOM
    z_combined = len(zlib.compress(combined.encode(), level=6))
    z_prefix = len(zlib.compress(kept_prefix[-4000:].encode(), level=6)) if kept_prefix else 1
    delta = z_combined - z_prefix
    delta = max(0, delta)  # zlib can sometimes compress the combined slightly smaller
    redundancy = 1.0 - delta / max(z_msg, 1)
    return round(min(1.0, max(0.0, redundancy)), 4)


def compaction_quality_report(original: str, kept: str) -> dict:
    """Quality metrics for a compaction pass (Li-Vitanyi 4ed Ch.8).
    Good compaction: low token_ratio, ncd not near 1, z_ratio > token_ratio.
    'truncation-not-compression' flag: z_ratio ≈ token_ratio (within 0.05).
    """
    tok_orig = len(original.split())
    tok_kept = len(kept.split())
    token_ratio = tok_kept / max(tok_orig, 1)
    z_orig = len(zlib.compress(original.encode(), level=6))
    z_kept = len(zlib.compress(kept.encode(), level=6))
    z_ratio = z_kept / max(z_orig, 1)
    z_orig2 = len(zlib.compress(original.encode(), level=6))
    combined = original + '\n===\n' + kept
    z_combined = len(zlib.compress(combined.encode(), level=6))
    ncd = (z_combined - min(z_orig2, z_kept)) / max(z_orig2, z_kept)
    truncation_flag = abs(z_ratio - token_ratio) < 0.05
    return {
        'token_ratio': round(token_ratio, 4),
        'z_ratio': round(z_ratio, 4),
        'ncd': round(max(0.0, ncd), 4),
        'truncation_not_compression': truncation_flag,
        'quality': 'good' if token_ratio < 0.6 and ncd < 0.8 and z_ratio > token_ratio else 'poor'
    }


def estimate_tokens(content: Any) -> int:
    """Rough token estimate: chars / 4."""
    if isinstance(content, str):
        return max(1, len(content) // 4)
    if isinstance(content, list):
        return max(1, sum(len(str(p)) for p in content) // 4)
    return max(1, len(str(content)) // 4)


def msg_tokens(msg: dict) -> int:
    role = msg.get("role", "")
    content = msg.get("content", "")
    base = estimate_tokens(content)
    # Tool calls in assistant messages add overhead
    if role == "assistant" and msg.get("tool_calls"):
        for tc in msg.get("tool_calls", []):
            args = tc.get("function", {}).get("arguments", "") if isinstance(tc, dict) else ""
            base += estimate_tokens(args)
    return base


def tool_name_from_msg(msg: dict, call_id_map: dict) -> str | None:
    """Extract the tool name from a tool-result message via the call_id_map."""
    if msg.get("role") != "tool":
        return None
    call_id = msg.get("tool_call_id", "")
    return call_id_map.get(call_id)


def build_call_id_map(messages: list[dict]) -> dict:
    """tool_call_id -> tool_name lookup."""
    out = {}
    for msg in messages:
        if msg.get("role") == "assistant":
            for tc in msg.get("tool_calls", []):
                if isinstance(tc, dict):
                    cid = tc.get("id", "")
                    name = tc.get("function", {}).get("name", "unknown")
                    if cid:
                        out[cid] = name
    return out


def is_already_demoted(msg: dict) -> bool:
    content = msg.get("content", "")
    if not isinstance(content, str):
        return False
    return (
        content.startswith("[")
        and any(
            content.startswith(p)
            for p in ("[Duplicate", "[screenshot removed", "[terminal] ran", "[web_extract]",
                      "[search_files]", "[skill_view]", "[delegate_task]", "[execute_code]",
                      "[write_file]", "[patch]", "[browser_", "[read_file]")
        )
    )


def score_messages(
    messages: list[dict],
    lam: float = 0.5,
    protect_ncd_tail: int = 0,
    must_constraint_texts: list[str] | None = None,
) -> list[dict]:
    """
    Score each message in the prune-candidate region.

    Returns list of dicts with:
        idx, role, tokens, tool_name, compression_pressure, particularization_pressure, score,
        already_demoted, content_preview, ncd_redundancy, ncd_demotion_vote
    """
    call_id_map = build_call_id_map(messages)

    # Find user-turn positions (proximity to user turn = higher particularization)
    user_indices = [i for i, m in enumerate(messages) if m.get("role") == "user"]

    # Token distribution for normalisation
    all_tokens = [msg_tokens(m) for m in messages]
    max_tokens = max(all_tokens) if all_tokens else 1
    n_msgs = len(messages)

    scored = []
    kept_prefix_parts: list[str] = []
    for i, msg in enumerate(messages):
        role = msg.get("role", "")
        tokens = all_tokens[i]
        tool_name = tool_name_from_msg(msg, call_id_map)
        already_demoted = is_already_demoted(msg)

        # --- Compression pressure: how much space freed by demoting ---
        # Already demoted messages have near-zero compression value
        if already_demoted:
            cp = 0.0
        else:
            cp = tokens / max_tokens  # 0..1, higher = more tokens freed

        # --- Particularization pressure: how irreplaceable ---
        # Components:
        # 1. Tool info density (task-specific knowledge)
        if role == "tool" and tool_name:
            density = TOOL_INFO_DENSITY.get(tool_name, DEFAULT_DENSITY)
        elif role == "user":
            density = 1.0   # user turns are irreplaceable
        elif role == "assistant":
            # Assistant reasoning: moderate (reconstructable from context)
            density = 0.45
        else:
            density = 0.30

        # 2. Recency signal: exponential decay — recent = more relevant
        # Position 0 = oldest; position n-1 = newest
        n = len(messages)
        recency = math.exp(-3.0 * (1.0 - (i / max(n - 1, 1))))  # 0..1, 1=newest

        # 3. Proximity to user turn: within 3 messages of a user turn = higher value
        dist_to_nearest_user = min(
            (abs(i - u) for u in user_indices), default=n
        )
        proximity = math.exp(-0.3 * dist_to_nearest_user)  # 0..1

        # Combine: weighted average of density, recency, proximity
        pp = 0.5 * density + 0.3 * recency + 0.2 * proximity

        # --- RR Score: opponent-process balance ---
        # High score = KEEP (high particularization wins)
        # Low score = DEMOTE (high compression wins relative to particularization)
        # retention_value = pp - lam * cp
        # (when compression pressure >> particularization pressure, demote first)
        retention_value = pp - lam * cp

        content = msg.get("content", "")
        preview = ""
        if isinstance(content, str):
            preview = content[:80].replace("\n", " ")
        elif isinstance(content, list):
            preview = str(content[0])[:80]

        msg_text = _message_text(msg)
        ncd_protected = protect_ncd_tail > 0 and i >= n_msgs - protect_ncd_tail
        # LUENBERGER-002 / must-constraint veto: never NCD-demote messages that contain
        # active must-constraint identifiers. These are passed as must_constraint_texts
        # (list of strings loaded from WM). Phrase overlap is literal substring match.
        must_protected = any(
            ct and ct in msg_text
            for ct in (must_constraint_texts or [])
        )
        if ncd_protected or must_protected or already_demoted:
            ncd = 0.0
            ncd_vote = 0
        else:
            kept_prefix_text = "\n".join(kept_prefix_parts)
            ncd = _ncd_redundancy(msg_text, kept_prefix_text)
            ncd_vote = 1 if ncd >= NCD_DEMOTION_THRESHOLD else 0

        scored.append({
            "idx": i,
            "role": role,
            "tokens": tokens,
            "tool_name": tool_name or "",
            "compression_pressure": round(cp, 3),
            "particularization_pressure": round(pp, 3),
            "score": round(retention_value, 3),
            "already_demoted": already_demoted,
            "content_preview": preview,
            "ncd_redundancy": ncd,
            "ncd_demotion_vote": ncd_vote,
            "demotion_votes": ncd_vote,
        })
        if not already_demoted:
            kept_prefix_parts.append(msg_text)

    return scored


def positional_order(scored: list[dict]) -> list[int]:
    """Current compressor: oldest first (ascending idx), skip already-demoted."""
    return [s["idx"] for s in scored if not s["already_demoted"]]


def rr_order(scored: list[dict]) -> list[int]:
    """RR scorer: lowest retention_value first (demote these first).

    NCD redundancy >= 0.7 adds an additive demotion vote (does not replace RR).
    """
    candidates = [s for s in scored if not s["already_demoted"]]
    return [
        s["idx"]
        for s in sorted(
            candidates,
            key=lambda x: x["score"] - NCD_VOTE_PENALTY * int(x.get("ncd_demotion_vote") or 0),
        )
    ]


def load_session_messages(session_id: str) -> list[dict]:
    """Load conversation messages from session storage."""
    # Try session file in logs/sessions/
    session_dirs = [
        HERMES_HOME / "logs" / "sessions",
        HERMES_HOME / "sessions",
    ]
    for d in session_dirs:
        if d.exists():
            for f in d.glob(f"*{session_id}*.json"):
                try:
                    data = json.loads(f.read_text())
                    if isinstance(data, list):
                        return data
                    if isinstance(data, dict):
                        return data.get("messages", data.get("conversation", []))
                except Exception:
                    pass

    # Try session_db lookup
    if SESSION_DB.exists():
        try:
            conn = sqlite3.connect(SESSION_DB)
            cur = conn.execute(
                "SELECT messages FROM sessions WHERE session_id = ? ORDER BY created_at DESC LIMIT 1",
                (session_id,)
            )
            row = cur.fetchone()
            conn.close()
            if row:
                return json.loads(row[0])
        except Exception:
            pass

    return []


def find_latest_session_file() -> Path | None:
    for d in [HERMES_HOME / "logs" / "sessions", HERMES_HOME / "sessions"]:
        if d.exists():
            files = sorted(d.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
            if files:
                return files[0]
    return None


def load_latest_session() -> tuple[str, list[dict]]:
    f = find_latest_session_file()
    if not f:
        return "", []
    try:
        data = json.loads(f.read_text())
        msgs = data if isinstance(data, list) else data.get("messages", [])
        return f.stem, msgs
    except Exception:
        return "", []


def print_comparison(scored: list[dict], top_k: int, lam: float) -> None:
    pos_order = positional_order(scored)
    rr_ord = rr_order(scored)

    n = min(top_k, len(pos_order))

    pos_set = set(pos_order[:n])
    rr_set = set(rr_ord[:n])
    agreement = len(pos_set & rr_set)
    disagreement = len(pos_set ^ rr_set)

    # Token reclaim comparison
    pos_reclaim = sum(scored[i]["tokens"] for i in pos_order[:n])
    rr_reclaim = sum(scored[i]["tokens"] for i in rr_ord[:n])

    # Information-weighted loss (sum of particularization_pressure for demoted messages)
    pos_pp_loss = sum(scored[i]["particularization_pressure"] for i in pos_order[:n])
    rr_pp_loss = sum(scored[i]["particularization_pressure"] for i in rr_ord[:n])

    print(f"\n{'='*72}")
    print(f"RR Compaction Spike  |  lambda={lam}  |  top-k={n}")
    print(f"{'='*72}")
    print(f"\nWindow: {len(scored)} messages, {sum(s['tokens'] for s in scored):,} est. tokens")
    print(f"Already demoted: {sum(1 for s in scored if s['already_demoted'])}")
    print(f"Prune candidates: {len([s for s in scored if not s['already_demoted']])}")

    print(f"\n--- Agreement in top-{n} demotion targets ---")
    print(f"  Positional and RR agree:    {agreement}/{n} messages")
    print(f"  Disagree (different picks): {disagreement} messages swapped")

    print(f"\n--- Token reclaim (top-{n} demotions) ---")
    print(f"  Positional (oldest-first):  {pos_reclaim:,} tokens freed")
    print(f"  RR scorer:                  {rr_reclaim:,} tokens freed")
    delta = rr_reclaim - pos_reclaim
    print(f"  Delta:                      {'+' if delta >= 0 else ''}{delta:,} tokens")

    print(f"\n--- Information preservation (lower = less loss) ---")
    print(f"  Positional pp-loss sum:     {pos_pp_loss:.2f}")
    print(f"  RR pp-loss sum:             {rr_pp_loss:.2f}")
    pp_delta = rr_pp_loss - pos_pp_loss
    print(f"  Delta:                      {'+' if pp_delta >= 0 else ''}{pp_delta:.2f}  "
          f"({'more loss' if pp_delta > 0 else 'less loss' if pp_delta < 0 else 'same'})")

    # Efficiency: tokens freed per unit of information lost
    pos_efficiency = pos_reclaim / max(pos_pp_loss, 0.001)
    rr_efficiency = rr_reclaim / max(rr_pp_loss, 0.001)
    print(f"\n--- Compression efficiency (tokens/pp-unit, higher=better) ---")
    print(f"  Positional:  {pos_efficiency:.0f}")
    print(f"  RR scorer:   {rr_efficiency:.0f}")

    print(f"\n--- Top-{n} RR demotion candidates (lowest retention value first) ---")
    print(f"  {'idx':>4}  {'role':>10}  {'tool':>18}  {'tokens':>6}  {'cp':>5}  {'pp':>5}  {'score':>6}  {'ncd':>6}  preview")
    print(f"  {'-'*4}  {'-'*10}  {'-'*18}  {'-'*6}  {'-'*5}  {'-'*5}  {'-'*6}  {'-'*6}  -------")
    for i in rr_ord[:n]:
        s = scored[i]
        in_pos = "  " if i in pos_set else "* "  # * = RR disagrees (would demote something positional would keep)
        print(
            f"  {in_pos}{s['idx']:>4}  {s['role']:>10}  {s['tool_name']:>18}  "
            f"{s['tokens']:>6}  {s['compression_pressure']:>5.2f}  {s['particularization_pressure']:>5.2f}  "
            f"{s['score']:>6.3f}  {s.get('ncd_redundancy', 0):>6.3f}  {s['content_preview'][:50]}"
        )

    print(f"\n  (* = in RR but NOT in positional top-{n}; these are the interesting disagreements)")

    print(f"\n--- Positional-only demotion candidates (would demote but RR wouldn't) ---")
    pos_only = pos_set - rr_set
    if pos_only:
        for i in sorted(pos_only):
            s = scored[i]
            print(
                f"    idx={i}  {s['role']:>10}  {s['tool_name']:>18}  "
                f"tokens={s['tokens']:>5}  score={s['score']:.3f}  {s['content_preview'][:55]}"
            )
    else:
        print("    (perfect agreement — RR would demote the same messages)")

    print(f"\n{'='*72}")
    print("Interpretation:")
    if rr_efficiency > pos_efficiency * 1.05:
        print("  RR scorer is MORE efficient (frees more tokens per unit of info lost).")
    elif rr_efficiency < pos_efficiency * 0.95:
        print("  Positional is MORE efficient. RR is preserving more at cost of fewer tokens freed.")
    else:
        print("  Roughly equivalent efficiency. RR provides different ordering, not more.")

    if disagreement == 0:
        print("  Perfect agreement: position-based and RR-based pruning select identical targets.")
        print("  => The current positional strategy is already RR-optimal for this session.")
    elif disagreement <= n // 4:
        print(f"  Minor disagreement ({disagreement} swaps): RR would reorder within similar territory.")
    else:
        print(f"  Significant disagreement ({disagreement} swaps): RR finds structurally different targets.")
        print("  => Worth investigating the disagreement messages for genuine quality difference.")
    print()


def cmd_lyapunov_check(argv: list[str]) -> None:
    """KHALIL-5: Lyapunov stability check on historical lambda values.

    Reads rr-lambda-history.jsonl (or a custom log file).
    V(k) = (lambda(k) - lambda_target)^2 where lambda_target = 0.5.
    Computes DeltaV = V(k+1) - V(k) at each step.
    Reports fraction of steps with DeltaV < 0 (Lyapunov stability condition).
    """
    parser = argparse.ArgumentParser(prog="rr_compaction_spike.py lyapunov-check")
    parser.add_argument(
        "--log-file", default=str(LAMBDA_LOG_PATH), dest="log_file",
        help=f"Path to lambda log JSONL (default: {LAMBDA_LOG_PATH})",
    )
    parser.add_argument(
        "--lambda-target", type=float, default=0.5, dest="lambda_target",
        help="Target lambda for stability analysis (default 0.5)",
    )
    args = parser.parse_args(argv)

    log_path = Path(args.log_file).expanduser()
    if not log_path.exists():
        print(json.dumps({
            "error": "Lambda log not found",
            "path": str(log_path),
            "hint": "Run rr_compaction_spike.py with --session or --latest to generate lambda history.",
        }, indent=2))
        return

    lambdas: list[float] = []
    timestamps: list[str] = []
    try:
        for line in log_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                if isinstance(rec, dict) and "lambda" in rec:
                    lambdas.append(float(rec["lambda"]))
                    timestamps.append(str(rec.get("ts", "")))
            except (json.JSONDecodeError, ValueError, TypeError):
                continue
    except OSError as exc:
        print(json.dumps({"error": str(exc)}))
        return

    if len(lambdas) < 2:
        print(json.dumps({
            "n_lambda_steps": len(lambdas),
            "lyapunov_stable": None,
            "note": "Need at least 2 lambda values to compute DeltaV.",
            "lambdas": lambdas,
        }, indent=2))
        return

    lam_t = args.lambda_target
    # V(k) = (lambda(k) - lambda_target)^2
    V = [(lam - lam_t) ** 2 for lam in lambdas]
    # DeltaV = V(k+1) - V(k)
    delta_V = [V[i + 1] - V[i] for i in range(len(V) - 1)]

    n_steps = len(delta_V)
    n_stable = sum(1 for dv in delta_V if dv < 0)
    stability_fraction = n_stable / n_steps if n_steps > 0 else 0.0

    steps_detail = [
        {
            "k": i,
            "lambda_k": round(lambdas[i], 6),
            "lambda_k1": round(lambdas[i + 1], 6),
            "V_k": round(V[i], 6),
            "V_k1": round(V[i + 1], 6),
            "delta_V": round(delta_V[i], 6),
            "stable": delta_V[i] < 0,
        }
        for i in range(n_steps)
    ]

    print(json.dumps({
        "lambda_target": lam_t,
        "n_lambda_steps": len(lambdas),
        "n_delta_steps": n_steps,
        "n_stable_steps": n_stable,
        "stability_fraction": round(stability_fraction, 4),
        "lyapunov_stable": stability_fraction >= 0.5,
        "mean_V": round(sum(V) / len(V), 6),
        "max_V": round(max(V), 6),
        "min_V": round(min(V), 6),
        "steps": steps_detail,
        "log_path": str(log_path),
        "note": (
            "V(k) = (lambda(k) - lambda_target)^2. "
            "Lyapunov condition: DeltaV < 0 (V decreasing). "
            "stability_fraction = fraction of steps with DeltaV < 0. "
            "KHALIL-5 nonlinear stability diagnostic (heuristic)."
        ),
    }, indent=2))


def main():
    if len(sys.argv) >= 2 and sys.argv[1] == "quality-report":
        qr = argparse.ArgumentParser(prog="rr_compaction_spike.py quality-report")
        qr.add_argument("original", help="Path to original (pre-compaction) text")
        qr.add_argument("kept", help="Path to kept (post-compaction) text")
        qargs = qr.parse_args(sys.argv[2:])
        original = Path(qargs.original).read_text(encoding="utf-8", errors="replace")
        kept = Path(qargs.kept).read_text(encoding="utf-8", errors="replace")
        print(json.dumps(compaction_quality_report(original, kept), indent=2))
        return

    if len(sys.argv) >= 2 and sys.argv[1] == "lyapunov-check":
        cmd_lyapunov_check(sys.argv[2:])
        return

    parser = argparse.ArgumentParser(description="RR Compaction Spike")
    parser.add_argument("--session", help="Session ID to analyse")
    parser.add_argument("--latest", action="store_true", help="Use most recent session file")
    parser.add_argument("--lambda", dest="lam", type=float, default=0.2,
                        help="Lambda: weight on compression pressure (0=keep everything, 1=pure compression). "
                             "Use < 0.235 to protect large high-density results; >= 0.4 inverts the intended ranking.")
    parser.add_argument("--top-k", type=int, default=20,
                        help="How many demotion candidates to compare")
    parser.add_argument("--protect-tail", type=int, default=32,
                        help="Number of tail messages to exclude from scoring (match Hermes protect_last_n=32)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON scores")
    parser.add_argument(
        "--ot-quality", action="store_true", dest="ot_quality",
        help="OT-9: after scoring, build TF histograms of full vs kept context tokens "
             "and output OT_quality_loss = W1_distance (lower = better preservation)",
    )
    args = parser.parse_args()

    if args.latest:
        session_id, messages = load_latest_session()
        if not messages:
            print("No session files found.", file=sys.stderr)
            sys.exit(1)
        print(f"Session: {session_id}  ({len(messages)} messages)")
    elif args.session:
        messages = load_session_messages(args.session)
        if not messages:
            print(f"Session {args.session!r} not found or empty.", file=sys.stderr)
            sys.exit(1)
        print(f"Session: {args.session}  ({len(messages)} messages)")
    else:
        # Demo mode: synthetic messages
        print("No session specified. Running on synthetic demo data.")
        messages = _synthetic_demo()

    # Apply tail protection (same as Hermes protect_last_n)
    if len(messages) <= args.protect_tail + 4:
        print(f"Session too short ({len(messages)} msgs) to have a prune region. Need > {args.protect_tail + 4}.")
        sys.exit(0)

    prune_window = messages[:-args.protect_tail] if args.protect_tail else messages

    # Last 32 (protect_tail) are excluded from the prune window, so they cannot
    # receive NCD demotion. protect_ncd_tail=0 here because the slice already
    # applied NCD_PROTECT_TAIL protection.
    scored = score_messages(prune_window, lam=args.lam, protect_ncd_tail=0)

    if args.json:
        print(json.dumps(scored, indent=2))
        return

    print_comparison(scored, top_k=args.top_k, lam=args.lam)
    _log_lambda(args.lam, session_id=getattr(args, "session", "") or "")

    # === OT-9: --ot-quality ===
    if args.ot_quality:
        if _ot_utils is None:
            print("\n[OT-9] ot_utils not available — skipping OT quality diagnostic.")
        else:
            # Full context: all messages in prune_window
            full_text = " ".join(
                _message_text(m) for m in prune_window
            )
            # Kept context: messages NOT in the top-k RR demotion set
            rr_ord = rr_order(scored)
            demote_idxs = set(rr_ord[:args.top_k])
            kept_text = " ".join(
                _message_text(prune_window[s["idx"]])
                for s in scored
                if s["idx"] not in demote_idxs and not s["already_demoted"]
            )
            tf_full = _ot_utils.build_tf(full_text)
            tf_kept = _ot_utils.build_tf(kept_text)
            w1 = _ot_utils.w1_distance(tf_full, tf_kept)
            print(f"\n--- OT-9 Quality Diagnostic ---")
            print(f"  OT_quality_loss = {w1:.6f}  (W1 distance; lower = better vocabulary preservation)")
            if w1 < 0.05:
                print("  Interpretation: excellent — kept context closely mirrors full vocabulary.")
            elif w1 < 0.15:
                print("  Interpretation: good — minor vocabulary shift after compaction.")
            elif w1 < 0.30:
                print("  Interpretation: moderate — some vocabulary loss; review demotion targets.")
            else:
                print("  Interpretation: high — significant vocabulary shift; compaction may lose key concepts.")
            print()


def _synthetic_demo() -> list[dict]:
    """Minimal synthetic session with varied tool types for demo mode."""
    msgs = []
    # System
    msgs.append({"role": "system", "content": "You are Hermes."})
    # Turn 1
    msgs.append({"role": "user", "content": "Research relevance realization and summarise."})
    msgs.append({"role": "assistant", "content": "I'll research this.", "tool_calls": [
        {"id": "c1", "function": {"name": "web_search", "arguments": '{"query":"relevance realization"}'}}
    ]})
    msgs.append({"role": "tool", "tool_call_id": "c1", "content": "Vervaeke 2012 " * 200})
    msgs.append({"role": "assistant", "content": None, "tool_calls": [
        {"id": "c2", "function": {"name": "web_extract", "arguments": '{"urls":["https://example.com"]}'}}
    ]})
    msgs.append({"role": "tool", "tool_call_id": "c2", "content": "Full paper text " * 500})
    # Turn 2
    msgs.append({"role": "user", "content": "Now write the skill."})
    msgs.append({"role": "assistant", "content": None, "tool_calls": [
        {"id": "c3", "function": {"name": "skill_view", "arguments": '{"name":"spike"}'}}
    ]})
    msgs.append({"role": "tool", "tool_call_id": "c3", "content": "Skill instructions " * 300})
    msgs.append({"role": "assistant", "content": None, "tool_calls": [
        {"id": "c4", "function": {"name": "write_file", "arguments": '{"path":"/tmp/skill.md","content":"# Skill"}'}}
    ]})
    msgs.append({"role": "tool", "tool_call_id": "c4", "content": '{"verified": true}'})
    msgs.append({"role": "assistant", "content": "Done. Skill written."})
    # Turn 3 (many tool results — mix of high/low value)
    msgs.append({"role": "user", "content": "Check the compressor source."})
    for i, (name, cid, content) in enumerate([
        ("terminal", "c5", "grep output " * 100),
        ("search_files", "c6", "match results " * 50),
        ("read_file", "c7", "source code " * 400),
        ("hindsight_recall", "c8", "memory results " * 30),
        ("execute_code", "c9", "analysis output " * 250),
    ]):
        msgs.append({"role": "assistant", "content": None, "tool_calls": [
            {"id": cid, "function": {"name": name, "arguments": "{}"}}
        ]})
        msgs.append({"role": "tool", "tool_call_id": cid, "content": content})
    msgs.append({"role": "assistant", "content": "Analysis complete."})
    # Pad tail (these are protected)
    for i in range(35):
        msgs.append({"role": "user" if i % 4 == 0 else "assistant", "content": f"tail message {i}"})
    return msgs


if __name__ == "__main__":
    main()
