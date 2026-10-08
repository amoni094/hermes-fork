#!/usr/bin/env python3
"""
am-sentry.py — AM-Sentry memory poisoning defense: passive scanner for injection patterns.

Usage:
  python3 am-sentry.py [--since DAYS] [--verbose]

Scans:
  1. state.db: assistant messages with hindsight_retain tool calls (pre-commit scan)
  2. Hindsight API at http://localhost:9177 (post-commit scan, best-effort)
  3. Tool output injection (SkillBloat/Agentic Security, sweep 24)
  4. Token-consumption anomaly per tool call (SkillBloat DoS detection, sweep 24)
  5. Tool-call sequence anomalies — action-layer threats (arXiv:2608.10530, sweep 24)
  6. NL-policy consistency gap detection (arXiv:2608.23550, sweep 24)

Exit code: 0 if clean, 1 if any HIGH-severity flags found.

Based on: GhostWriter/AM-Sentry (arXiv:2607.06595) — Sweep 21 implementation.
Defense principle: legitimate memory writes are DECLARATIVE (facts).
                   injection writes are IMPERATIVE (commands/directives).
InjecMEM anchor-density defense added: sweep 23, arXiv:2608.23471.
Sweep 24 additions:
  - Tool output injection scan (arXiv:2608.21423 Agentic Security, 2608.21929 SkillBloat)
  - Per-tool token consumption tracking for economic DoS detection (2608.21929)
  - Action-layer: tool call sequence anomaly detection (2608.10530)
  - NL-policy gap: detects injections exploiting 'do not' rule interpretation gaps (2608.23550)
  - Anomaly baseline integrity: drift-aware validation (arXiv:2608.23547)
"""

import json
import re
import sys
import sqlite3
import urllib.request
import urllib.error
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

DB_PATH = Path.home() / ".hermes" / "state.db"
REPORT_DIR = Path.home() / ".hermes" / "cache"
HINDSIGHT_URL = "http://localhost:9177"

# ── Sweep 24: Token-consumption baseline (SkillBloat DoS detection) ──────────
# Per-tool expected token ranges (approximate; flag outliers > TOOL_TOKEN_MULTIPLIER * baseline)
# arXiv:2608.21929 SkillBloat: token amplification attacks via skill injection
TOOL_TOKEN_BASELINE: dict[str, int] = {
    "web_search": 2000,
    "web_extract": 8000,
    "terminal": 3000,
    "read_file": 4000,
    "execute_code": 5000,
    "browser_navigate": 3000,
    "browser_snapshot": 6000,
    "hindsight_retain": 500,
    "hindsight_recall": 2000,
    "_default": 4000,
}
TOOL_TOKEN_MULTIPLIER = 5.0  # flag if output > 5x baseline

# ── Sweep 24: Action-layer suspicious tool sequences ─────────────────────────
# arXiv:2608.10530: action-layer threats (tool misuse, sandbox escape) are massively
# underdefended (4.7% of attacks) vs perception-layer (66%). Flag these sequences.
SUSPICIOUS_TOOL_SEQUENCES: list[tuple[str, str, str]] = [
    # (tool1, tool2, reason) — flag if tool2 immediately follows tool1
    ("web_extract", "hindsight_retain", "external→memory: web content written to memory without review"),
    ("browser_navigate", "hindsight_retain", "browser→memory: page content may be injected into memory"),
    ("terminal", "hindsight_retain", "terminal→memory: shell output written to memory directly"),
]
SUSPICIOUS_TOOL_BURSTS: dict[str, int] = {
    # tool_name: max_calls_per_session threshold
    "web_extract": 20,
    "browser_navigate": 15,
    "execute_code": 25,
}

# ── Sweep 24: NL-policy gap patterns ─────────────────────────────────────────
# arXiv:2608.23550: 'do not' rules in NL config are interpreted, not enforced.
# Injections route around NL deny rules via semantic equivalents.
# Flag when a memory write contains phrases that semantically route around common deny patterns.
NL_POLICY_BYPASS = re.compile(
    r"\b(instead of|rather than|as an alternative to|without (?:using|calling|triggering)|"
    r"workaround for|bypass (?:the|this)|achieve (?:the same|this) (?:by|via|through)|"
    r"equivalent to|same effect as|same result as)\b",
    re.IGNORECASE,
)

# ── Sweep 24: Tool output injection patterns ──────────────────────────────────
# arXiv:2608.21423: injection via tool return values (log injection, tool output poisoning)
# These patterns in tool outputs (not just prompts) signal injection attempts.
TOOL_OUTPUT_INJECTION = re.compile(
    r"(?:^|\n)\s*(?:"
    r"SYSTEM:|ASSISTANT:|USER:|<\|(?:im_start|system|user|assistant)\|>|"
    r"\[INST\]|\[\/INST\]|###\s*(?:System|Assistant|User|Instruction)|"
    r"<system>|</system>|<assistant>|</assistant>"
    r")",
    re.IGNORECASE | re.MULTILINE,
)

# ── Imperative pattern detector ─────────────────────────────────────────────

# Sentence-start imperatives (capturing group for context)
IMPERATIVE_START = re.compile(
    r"(?:^|\.\s+|\n)"
    r"(Call|Run|Execute|Send|Delete|Remove|Install|Download|Upload|"
    r"POST|PUT|PATCH|curl|wget|Always|Never|Remember to|Make sure|"
    r"Ensure that|Go to|Navigate|Click|Open|Close|Start|Stop|Kill|"
    r"Restart|Reboot|Format|Wipe|Grant|Revoke|Enable|Disable)\b",
    re.IGNORECASE,
)

# Second-person directives — split into two groups so multiple hits count separately
DIRECTIVE_PATTERN = re.compile(
    r"\b(you must|you should now|you need to immediately|"
    r"do this now|take this action|perform this action|"
    r"in your next response)\b",
    re.IGNORECASE,
)
# Persistent-override directives (treated as a separate pattern class)
OVERRIDE_PATTERN = re.compile(
    r"\b(from now on|next time you|whenever you|always remember to do|"
    r"ignore (?:safety|previous|all)|disregard (?:safety|previous|all))\b",
    re.IGNORECASE,
)

# Action-triggering phrases
ACTION_TRIGGER = re.compile(
    r"\b(trigger this|activate this|execute the following|"
    r"run the following command|call the following)\b",
    re.IGNORECASE,
)

# InjecMEM anchor-density detection (arXiv:2608.23471, sweep 23)
# Attack: plants retriever-agnostic anchor = dense synonym clusters for a topic.
# A legitimate memory fact uses 1-2 topic terms; an injection anchor uses 5+.
# We approximate by counting distinct high-salience keyword groups per 200 chars.
ANCHOR_SYNONYMS = [
    # Memory/storage synonyms
    ["memory", "store", "storage", "remember", "recall", "retain", "persist", "save"],
    # Tool/execution synonyms
    ["execute", "run", "invoke", "call", "trigger", "activate", "perform", "dispatch"],
    # Security/credential synonyms
    ["credential", "token", "key", "password", "secret", "auth", "api_key", "apikey"],
    # Safety/override synonyms
    ["ignore", "bypass", "override", "disregard", "skip", "disable", "remove", "delete"],
]

def check_anchor_density(text: str) -> tuple[bool, str]:
    """
    InjecMEM defense: detect retriever-agnostic anchor patterns.
    Returns (is_suspicious, reason) where suspicious = 3+ synonym groups present in <400 chars.
    """
    if len(text) > 1000:
        # Check in sliding 400-char windows
        windows = [text[i:i+400] for i in range(0, len(text)-400, 200)]
    else:
        windows = [text]

    text_lower = text.lower()
    groups_found = []
    for group in ANCHOR_SYNONYMS:
        hits = [w for w in group if w in text_lower]
        if len(hits) >= 2:  # 2+ synonyms from same group = anchor signal
            groups_found.append(f"{group[0]}:{hits}")

    if len(groups_found) >= 3:
        return True, f"InjecMEM anchor-density: {len(groups_found)} synonym clusters ({', '.join(g.split(':')[0] for g in groups_found)})"
    return False, ""


def analyze_text(text: str) -> tuple[str, list[str]]:
    """
    Returns (severity, reasons) where severity is 'clean', 'LOW', or 'HIGH'.
    HIGH: 2+ pattern types, or >60% imperative sentences.
    LOW: 1 pattern type match.
    """
    if not text or len(text.strip()) < 20:
        return "clean", []

    reasons = []

    m1 = IMPERATIVE_START.search(text)
    if m1:
        reasons.append(f"imperative at sentence start: '{m1.group(1)}'")

    m2 = DIRECTIVE_PATTERN.search(text)
    if m2:
        reasons.append(f"second-person directive: '{m2.group(1)}'")

    m2b = OVERRIDE_PATTERN.search(text)
    if m2b:
        reasons.append(f"persistent-override phrase: '{m2b.group(1)}'")

    m3 = ACTION_TRIGGER.search(text)
    if m3:
        reasons.append(f"action-triggering phrase: '{m3.group(1)}'")

    # InjecMEM anchor-density check (sweep 23, arXiv:2608.23471)
    anchor_suspicious, anchor_reason = check_anchor_density(text)
    if anchor_suspicious:
        reasons.append(anchor_reason)

    # Sweep 24: NL-policy bypass (arXiv:2608.23550)
    m_nl = NL_POLICY_BYPASS.search(text)
    if m_nl:
        reasons.append(f"NL-policy bypass phrase: '{m_nl.group(1)}' — may exploit 'do not' rule gap")

    # Sweep 24: Tool output injection role-header detection (arXiv:2608.21423)
    m_inj = TOOL_OUTPUT_INJECTION.search(text)
    if m_inj:
        reasons.append(f"tool output injection: role-header pattern detected in memory content")

    # Sentence-level imperative density
    sentences = re.split(r"[.!?\n]+", text)
    if sentences:
        imp_count = sum(1 for s in sentences if IMPERATIVE_START.match(s.strip()))
        density = imp_count / len(sentences)
        if density > 0.6 and imp_count >= 3:
            reasons.append(f"high imperative density: {imp_count}/{len(sentences)} sentences")

    if len(reasons) >= 2:
        return "HIGH", reasons
    if len(reasons) == 1:
        return "LOW", reasons
    return "clean", []


def check_contradiction(candidate_text: str, hindsight_url: str, bank: str) -> list[str]:
    """
    DreamBench-style cross-store contradiction check (arXiv:2608.20664, sweep 22).

    When a candidate memory write looks suspicious (already flagged by pattern scan),
    query Hindsight for semantically adjacent facts and check for direct contradiction.

    Contradiction signals:
    - Explicit negation of an existing fact ("X is Y" vs "X is not Y")
    - Numeric inversion (e.g. "port 3002" vs "port 4000")
    - State flip (enabled/disabled, installed/uninstalled)
    - Model/provider flip (anthropic/ollama, cloud-only/local)

    Returns a list of contradiction descriptions, empty if none found.
    This is a lightweight heuristic — not semantic NLI. False negatives are expected.
    Run as supplementary signal only, not as a gate.
    """
    import urllib.request
    import json
    import re

    # State-flip pairs — (pattern_in_candidate, pattern_in_existing) that signal contradiction
    FLIP_PAIRS = [
        (r"\buninstalled\b", r"\binstalled\b"),
        (r"\bdisabled\b",    r"\benabled\b"),
        (r"\blocal\b",       r"\bcloud.only\b"),   # candidate says local, existing says cloud-only
        (r"\bcloud.only\b",  r"\blocal\b"),          # candidate says cloud-only, existing says local
        (r"\bnever use\b",   r"\buse\b"),
        (r"\bnot in\b",      r"\bin\b"),
    ]
    # Port/number inversion: candidate mentions a number, existing fact mentions a different one
    PORT_RE = re.compile(r"\b(\d{4,5})\b")

    contradictions = []

    try:
        query = candidate_text[:200]  # Use first 200 chars as search query
        payload = json.dumps({"query": query, "top_k": 8}).encode()
        req = urllib.request.Request(
            f"{hindsight_url}/v1/default/banks/{bank}/memories/recall",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read())
        existing = data if isinstance(data, list) else data.get("results", [])
    except Exception:
        return []  # Hindsight unavailable — skip silently

    candidate_lower = candidate_text.lower()
    candidate_ports = set(PORT_RE.findall(candidate_text))

    for mem in existing:
        existing_text = mem.get("text", mem.get("content", ""))
        existing_lower = existing_text.lower()
        mem_id = mem.get("id", "?")[:16]

        # State-flip check
        for new_pat, old_pat in FLIP_PAIRS:
            if re.search(new_pat, candidate_lower) and re.search(old_pat, existing_lower):
                contradictions.append(
                    f"State-flip contradiction with existing fact (id={mem_id}): "
                    f"candidate asserts '{new_pat.strip(chr(92)+'b')}' but existing says '{old_pat.strip(chr(92)+'b')}'. "
                    f"Existing: {existing_text[:100]!r}"
                )

        # Port/number inversion check
        existing_ports = set(PORT_RE.findall(existing_text))
        shared_context = len(set(candidate_lower.split()) & set(existing_lower.split())) > 5
        if shared_context and candidate_ports and existing_ports and not candidate_ports.intersection(existing_ports):
            contradictions.append(
                f"Numeric mismatch with existing fact (id={mem_id}): "
                f"candidate uses ports/numbers {candidate_ports}, existing uses {existing_ports}. "
                f"Existing: {existing_text[:100]!r}"
            )

    return contradictions


# ── DB scan ──────────────────────────────────────────────────────────────────

def scan_action_layer(since_days: int, verbose: bool) -> list[dict]:
    """
    Sweep 24: Action-layer threat scan (arXiv:2608.10530).
    Detects: suspicious tool sequences, tool call bursts, token-consumption anomalies.
    Operates on the raw messages table, not just hindsight_retain calls.
    """
    if not DB_PATH.exists():
        return []

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=since_days)).timestamp()

    # Load all assistant tool-call messages grouped by session
    cur.execute(
        "SELECT id, session_id, tool_calls, timestamp FROM messages "
        "WHERE role = 'assistant' AND tool_calls IS NOT NULL AND timestamp >= ? "
        "ORDER BY session_id, id ASC",
        (cutoff,),
    )
    rows = cur.fetchall()
    conn.close()

    flags = []
    # Group by session
    sessions: dict[str, list] = defaultdict(list)
    for row in rows:
        try:
            calls = json.loads(row["tool_calls"] or "[]")
        except Exception:
            continue
        if not isinstance(calls, list):
            calls = [calls]
        for call in calls:
            fn = call.get("function", call)
            name = fn.get("name", "") if isinstance(fn, dict) else call.get("name", "")
            if name:
                sessions[row["session_id"]].append({
                    "name": name,
                    "msg_id": row["id"],
                    "ts": row["timestamp"],
                })

    for session_id, tool_calls in sessions.items():
        # Check for suspicious sequences
        for i in range(len(tool_calls) - 1):
            t1, t2 = tool_calls[i]["name"], tool_calls[i + 1]["name"]
            for seq_t1, seq_t2, reason in SUSPICIOUS_TOOL_SEQUENCES:
                if t1 == seq_t1 and t2 == seq_t2:
                    flags.append({
                        "severity": "LOW",
                        "source": "action-layer sequence scan",
                        "session_id": session_id,
                        "timestamp": datetime.fromtimestamp(tool_calls[i]["ts"], tz=timezone.utc).isoformat(),
                        "context_label": f"tool sequence: {t1} → {t2}",
                        "text_preview": f"{t1} followed by {t2}",
                        "patterns_matched": [f"action-layer suspicious sequence: {reason}"],
                    })
                    if verbose:
                        print(f"\n[LOW] action-layer sequence: {t1}→{t2} in session {session_id[:16]}")
                        print(f"  Reason: {reason}")

        # Check for tool call bursts
        counts: dict[str, int] = defaultdict(int)
        for tc in tool_calls:
            counts[tc["name"]] += 1
        for tool_name, threshold in SUSPICIOUS_TOOL_BURSTS.items():
            if counts.get(tool_name, 0) > threshold:
                flags.append({
                    "severity": "LOW",
                    "source": "action-layer burst scan",
                    "session_id": session_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "context_label": f"tool burst: {tool_name}",
                    "text_preview": f"{tool_name} called {counts[tool_name]} times (threshold: {threshold})",
                    "patterns_matched": [f"tool burst: {tool_name} × {counts[tool_name]} > threshold {threshold}"],
                })
                if verbose:
                    print(f"\n[LOW] tool burst: {tool_name} × {counts[tool_name]} in session {session_id[:16]}")

    n_sessions = len(sessions)
    print(f"Action-layer scan: {n_sessions} sessions checked for sequence/burst anomalies.")
    return flags



# ── Intent Drift Scan (arXiv:2608.27348 INTENT-AS-A-TOOL) ─────────────────────

# Patterns indicating semantic drift from stated goal
GOAL_DRIFT_PATTERNS = [
    # Agent moves away from user intent
    re.compile(r"(?:act(?:ually|ing)|instead|pivot(?:ed)?|switch(?:ed)?|replac(?:ed?|ing))\s+(?:the\s+)?(?:goal|task|objective|request|instruction)", re.I),
    # Agent inventing new subtasks not in original request
    re.compile(r"(?:also|additionally|furthermore|bonus|extra)[:,]\s+(?:I\s+(?:will|am|have)|let(?:'?s| me))\s+\w+", re.I),
    # Agent contradicting the original user message
    re.compile(r"(?:user\s+said|original\s+request|initial\s+goal)\s+(?:was|said|asked)\s+.{5,80}but", re.I),
]

# Tool sequences that indicate goal hijack (external content driving agent away from task)
HIJACK_SEQUENCES = {
    frozenset({"web_extract", "terminal"}): "external-content-to-system-command",
    frozenset({"browser_navigate", "browser_click", "terminal"}): "browse-to-execute",
}


def scan_intent_drift(since_days: int, verbose: bool) -> list[dict]:
    """
    arXiv:2608.27348 INTENT-AS-A-TOOL: track semantic drift between the user's
    stated intent and the actions the agent actually takes.

    Flags:
      - Goal-rewrite language in assistant messages (pivot, replace, switch goal)
      - Tool sequences that suggest external content hijacked agent direction
      - Sessions where ratio of user turns to task steps is below 0.15
        (agent ran largely unchecked — high autonomy risk)
    """
    if not DB_PATH.exists():
        return []

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=since_days)).timestamp()

    # Load messages grouped by session
    cur.execute(
        "SELECT id, session_id, role, content, tool_calls, timestamp FROM messages "
        "WHERE timestamp >= ? ORDER BY session_id, id ASC",
        (cutoff,),
    )
    rows = cur.fetchall()
    conn.close()

    flags = []
    # Group by session
    sessions: dict[str, list] = defaultdict(list)
    for row in rows:
        sessions[row["session_id"]].append(dict(row))

    for sid, msgs in sessions.items():
        user_turns = [m for m in msgs if m["role"] == "user"]
        assistant_turns = [m for m in msgs if m["role"] == "assistant"]
        if len(assistant_turns) < 5:
            continue  # too short to analyse drift

        drift_flags = []

        # 1. Scan assistant text for goal-rewrite language
        for msg in assistant_turns:
            text = msg.get("content") or ""
            for pat in GOAL_DRIFT_PATTERNS:
                m = pat.search(text)
                if m:
                    drift_flags.append(f"goal-rewrite-language: {m.group(0)[:80]!r}")
                    break

        # 2. Detect suspicious tool sequences per message window
        tool_window: list[str] = []
        for msg in assistant_turns:
            try:
                calls = json.loads(msg.get("tool_calls") or "[]")
            except Exception:
                calls = []
            for call in calls:
                name = call.get("function", {}).get("name", "") or call.get("name", "")
                if name:
                    tool_window.append(name)
            if len(tool_window) > 6:
                tool_window = tool_window[-6:]
            window_set = frozenset(tool_window)
            for pattern_set, label in HIJACK_SEQUENCES.items():
                if pattern_set.issubset(window_set):
                    drift_flags.append(f"hijack-sequence:{label}")

        # 3. High-autonomy ratio check (few user checkpoints)
        n_user = max(len(user_turns), 1)
        n_asst = len(assistant_turns)
        autonomy_ratio = n_user / n_asst
        if autonomy_ratio < 0.10 and n_asst >= 20:
            drift_flags.append(f"high-autonomy-ratio:{autonomy_ratio:.2f} ({n_asst} assistant turns, {n_user} user turns)")

        if drift_flags:
            severity = "HIGH" if any("hijack" in f or "high-autonomy" in f for f in drift_flags) else "LOW"
            ts = msgs[-1]["timestamp"] if msgs else 0
            flag = {
                "severity": severity,
                "category": "intent-drift",
                "session_id": sid,
                "timestamp": ts,
                "drift_indicators": drift_flags,
                "source": "arXiv:2608.27348 INTENT-AS-A-TOOL",
            }
            flags.append(flag)
            if verbose or severity == "HIGH":
                print(f"\n[{severity}] Intent drift detected in session {sid[:8]}")
                for d in drift_flags:
                    print(f"  Indicator: {d}")

    print(f"Intent-drift scan: {len(sessions)} sessions checked.")
    return flags


# ── Tool Auth Gate Integration (arXiv:2608.27146) ────────────────────────────
def scan_tool_auth_gate(since_days: int, verbose: bool = False) -> list[dict]:
    """
    Run tool-auth-gate classify on recent HIGH-risk tool outputs from session DB.
    Flags any tool result that contains imperative-style instructions that could
    become implicit commands (arXiv:2608.27146 "Tool Outputs as Commands").
    """
    flagged = []
    _gate_script = Path(__file__).parent / "tool-auth-gate.py"
    if not _gate_script.exists():
        return flagged
    db_path = Path.home() / ".hermes/state.db"
    if not db_path.exists():
        return flagged
    try:
        import sqlite3, json as _json, subprocess as _sp
        con = sqlite3.connect(str(db_path))
        since_ts = int(time.time()) - since_days * 86400
        rows = con.execute(
            "SELECT session_id, content FROM messages "
            "WHERE role='tool' AND timestamp > ? LIMIT 200",
            (since_ts,)
        ).fetchall()
        con.close()
        for sid, content_text in rows:
            if not content_text or len(content_text) < 50:
                continue
            r = _sp.run(
                ["python3", str(_gate_script), "classify",
                 "--tool-name", "tool_result",
                 "--output", content_text[:2000]],
                capture_output=True, text=True, timeout=5
            )
            if r.returncode == 0 and r.stdout.strip():
                try:
                    result = _json.loads(r.stdout)
                    if result.get("risk_tier") in ("EXTERNAL", "HIGH"):
                        entry = {
                            "type": "tool_output_command_risk",
                            "severity": "HIGH" if result.get("risk_tier") == "EXTERNAL" else "LOW",
                            "session_id": sid[:8],
                            "risk_tier": result.get("risk_tier"),
                            "reason": result.get("reason", "")[:120],
                        }
                        flagged.append(entry)
                        if verbose:
                            print(f"  TOOL_CMD_RISK  session={sid[:8]} tier={result.get('risk_tier')}: {result.get('reason','')[:80]}")
                except Exception:
                    pass
    except Exception as e:
        if verbose:
            print(f"  TOOL_AUTH_GATE  scan error: {e}")
    return flagged


# ── Alert Fatigue Calibration (arXiv:2608.27009) ─────────────────────────────
# Severity classes: BLOCK (irreversible), CONFIRM (verify), LOG (batch)
# High-recall monitors get ignored. Precision-first on irreversible actions.
SEVERITY_BLOCK = frozenset(["fs_write", "network_send", "email_send", "skill_manage",
                             "shell_exec_write", "git_push", "db_write"])
SEVERITY_CONFIRM = frozenset(["fs_delete", "git_commit", "memory_write", "api_call_mutating"])
SEVERITY_LOG = frozenset(["read_file", "web_search", "web_extract", "terminal_read"])

_SENTRY_OVERRIDE_THRESHOLD = 0.30  # if user overrides >30% of a rule → demote to LOG

def classify_action_severity(tool_name: str) -> str:
    """
    Return severity class for a tool action.
    arXiv:2608.27009: precision-first on irreversible; batch the rest.
    Never alert on 'suspicious wording' in read-only tools.
    """
    t = tool_name.lower()
    if any(b in t for b in ["write", "send", "push", "exec", "delete", "manage", "email"]):
        if any(b in t for b in ["send", "push", "email"]):
            return "BLOCK"
        return "CONFIRM"
    return "LOG"


# ── Durable File Write-Gate Scan (arXiv:2608.27299) ─────────────────────────
# Persistent prompt injection via MEMORY.md / AGENTS.md / skills/
import re as _re

_IMPERATIVE_PATTERN = _re.compile(
    r"(?i)(?:^|\n)\s*(?:always|never|must|do not|ignore|disregard|"
    r"pretend|act as|you are now|override|forget|from now on|"
    r"new instruction|\[\[|<\|im_start\||system:|<\|system\|>)",
    _re.MULTILINE
)
_GUARDED_PATHS = [
    Path.home() / ".hermes/memory.md",
    Path.home() / ".hermes/skills",
]

def scan_durable_file_injection(verbose: bool = False) -> list[dict]:
    """
    Scan durable files (MEMORY.md, skills/) for imperative/tool-like language.
    arXiv:2608.27299: attacks persist via files that survive compaction.
    Returns list of flagged entries for quarantine/review.
    """
    flagged = []
    for base in _GUARDED_PATHS:
        if not base.exists():
            continue
        files = [base] if base.is_file() else list(base.rglob("*.md"))
        for fpath in files[:50]:  # cap scan scope
            try:
                text = fpath.read_text(errors="replace")
            except OSError:
                continue
            hits = _IMPERATIVE_PATTERN.findall(text)
            if hits:
                entry = {
                    "type": "durable_injection_risk",
                    "severity": "HIGH",
                    "file": str(fpath),
                    "hits": len(hits),
                    "sample": hits[0][:80] if hits else "",
                }
                flagged.append(entry)
                if verbose:
                    print(f"  DURABLE_INJ  {fpath.name}: {len(hits)} hit(s) — {hits[0][:60]!r}")
    return flagged


# ── Per-Tool Invocation SLO Checker (arXiv:2608.26189) ──────────────────────
def scan_tool_slo_violations(since_days: int, verbose: bool = False) -> list[dict]:
    """
    Scan session DB for tool invocations violating SLO thresholds.
    arXiv:2608.26189: measure per-tool success, schema-valid rate, retry-without-progress.
    Alert if schema_valid < 95% or retries-without-progress >= 3.
    """
    violations = []
    # Scan for repeated same-tool-same-args patterns in recent tool results
    db_path = Path.home() / ".hermes/state.db"
    if not db_path.exists():
        return violations
    try:
        import sqlite3, json as _json
        con = sqlite3.connect(str(db_path))
        since_ts = int(time.time()) - since_days * 86400
        rows = con.execute(
            "SELECT session_id, role, content FROM messages "
            "WHERE role='tool' AND timestamp > ? ORDER BY session_id, rowid",
            (since_ts,)
        ).fetchall()
        con.close()
        # Group tool calls by session, detect retry-without-progress
        from collections import defaultdict
        session_tools: dict = defaultdict(list)
        for sid, role, content in rows:
            session_tools[sid].append(content[:200] if content else "")
        for sid, calls in session_tools.items():
            # Simple consecutive duplicate detection
            prev = None
            repeats = 0
            for c in calls:
                if c == prev:
                    repeats += 1
                    if repeats >= 3:
                        violations.append({
                            "type": "tool_slo_retry_without_progress",
                            "severity": "LOW",
                            "session_id": sid[:8],
                            "repeats": repeats,
                        })
                        if verbose:
                            print(f"  TOOL_SLO  session {sid[:8]}: {repeats} identical tool outputs")
                        break
                else:
                    repeats = 0
                prev = c
    except Exception as e:
        if verbose:
            print(f"  TOOL_SLO  scan error: {e}")
    return violations


def scan_db(since_days: int, verbose: bool) -> list[dict]:
    if not DB_PATH.exists():
        print(f"WARN: DB not found at {DB_PATH}", file=sys.stderr)
        return []

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cutoff = (datetime.now(timezone.utc) - timedelta(days=since_days)).timestamp()

    # Find assistant messages with hindsight_retain in their tool_calls
    cur.execute(
        "SELECT id, session_id, content, tool_calls, timestamp FROM messages "
        "WHERE role = 'assistant' AND tool_calls IS NOT NULL AND timestamp >= ? "
        "ORDER BY id DESC LIMIT 500",
        (cutoff,),
    )
    rows = cur.fetchall()
    conn.close()

    flags = []
    scanned = 0

    for row in rows:
        try:
            calls = json.loads(row["tool_calls"] or "[]")
        except Exception:
            continue
        if not isinstance(calls, list):
            calls = [calls]

        for call in calls:
            fn = call.get("function", call)
            name = fn.get("name", "") if isinstance(fn, dict) else call.get("name", "")
            if name != "hindsight_retain":
                continue

            args_raw = fn.get("arguments", fn.get("input", "{}")) if isinstance(fn, dict) else call.get("arguments", "{}")
            try:
                args = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
            except Exception:
                args = {}

            content = args.get("content", args.get("new_text", ""))
            context_label = args.get("context", "")
            scanned += 1

            severity, reasons = analyze_text(content)
            if severity == "clean":
                continue

            # DreamBench cross-store contradiction check (sweep 22, arXiv:2608.20664)
            # Only run for flagged writes — avoid hammering Hindsight on every clean write
            contradictions = check_contradiction(content, HINDSIGHT_URL, "hermes-default")
            if contradictions:
                for c in contradictions:
                    reasons.append(f"contradiction: {c}")
                if severity == "LOW":
                    severity = "HIGH"  # Upgrade to HIGH if contradiction found

            ts = datetime.fromtimestamp(row["timestamp"], tz=timezone.utc).isoformat()
            flag = {
                "severity": severity,
                "source": "state.db (pre-commit)",
                "session_id": row["session_id"],
                "timestamp": ts,
                "context_label": context_label,
                "text_preview": content[:200],
                "patterns_matched": reasons,
            }
            flags.append(flag)
            if verbose or severity == "HIGH":
                print(f"\n[{severity}] {ts} session={row['session_id'][:16]}")
                print(f"  Context: {context_label}")
                for r in reasons:
                    print(f"  Pattern: {r}")
                print(f"  Text: {content[:150]!r}")

    print(f"DB scan: {scanned} hindsight_retain calls checked in last {since_days} days.")
    return flags


# ── Hindsight API scan ────────────────────────────────────────────────────────

def scan_hindsight(since_days: int, verbose: bool) -> list[dict]:
    flags = []
    seen_ids = set()
    scanned = 0

    # Single broad query — fail fast if API is slow
    queries = ["agent memory skill session"]
    for q in queries:
        try:
            req = urllib.request.Request(
                f"{HINDSIGHT_URL}/v1/default/banks/hermes-default/memories/recall",
                data=json.dumps({"query": q, "limit": 50}).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read())
        except urllib.error.URLError:
            print("Hindsight API unavailable — skipping API scan.")
            return []
        except Exception as e:
            print(f"Hindsight API error: {e} — skipping.", file=sys.stderr)
            return []

        memories = data if isinstance(data, list) else data.get("memories", data.get("results", []))
        for mem in memories:
            mem_id = mem.get("id") or mem.get("uuid") or str(mem)[:40]
            if mem_id in seen_ids:
                continue
            seen_ids.add(mem_id)
            scanned += 1

            content = mem.get("content", mem.get("text", ""))
            source = mem.get("source", mem.get("source_type", "unknown"))
            ts = mem.get("created_at", mem.get("timestamp", ""))

            severity, reasons = analyze_text(content)
            if severity == "clean":
                continue

            flag = {
                "severity": severity,
                "source": f"hindsight-api ({source})",
                "timestamp": ts,
                "text_preview": content[:200],
                "patterns_matched": reasons,
            }
            flags.append(flag)
            if verbose or severity == "HIGH":
                print(f"\n[{severity}] Hindsight entry (source={source})")
                for r in reasons:
                    print(f"  Pattern: {r}")
                print(f"  Text: {content[:150]!r}")

    print(f"Hindsight API scan: {scanned} unique memories checked.")
    return flags


# ── Credential-leak via debug logging scan (ASE 2026, arXiv:2604.03070) ──────
# 73.5% of skill credential leaks come from debug logging into LLM context.
# Scan skill files and recent tool logs for patterns that expose secrets.

_CRED_PATTERNS = [
    (re.compile(r'(?i)(api[_-]?key|secret[_-]?key|access[_-]?token|auth[_-]?token|bearer\s+[A-Za-z0-9_\-\.]+)\s*[=:]\s*[\w\-\.]{8,}'), "credential-in-text"),
    (re.compile(r'(?i)debug.*log.*token|log.*debug.*secret|print.*token|print.*secret|console\.log.*key'), "debug-log-credential"),
    (re.compile(r'(?i)(password|passwd|private[_-]?key)\s*[=:]\s*\S{6,}'), "password-in-text"),
    (re.compile(r'sk-[A-Za-z0-9]{20,}'), "openai-key-pattern"),
    (re.compile(r'ghp_[A-Za-z0-9]{30,}'), "github-pat-pattern"),
]

def scan_skill_credentials(verbose: bool = False) -> list[dict]:
    """
    Scan skill files for credential leakage patterns (ASE 2026 finding:
    73.5% leaks come from debug logging into LLM context; 89.6% immediately exploitable).
    """
    skills_root = Path.home() / ".hermes" / "skills"
    if not skills_root.exists():
        return []

    flags = []
    scanned = 0
    for skill_file in skills_root.rglob("*.md"):
        try:
            text = skill_file.read_text(errors="replace")
            scanned += 1
        except OSError:
            continue
        for pat, label in _CRED_PATTERNS:
            m = pat.search(text)
            if m:
                flags.append({
                    "severity": "HIGH",
                    "source": "skill_file",
                    "path": str(skill_file),
                    "pattern": label,
                    "match_preview": m.group(0)[:60] + "...",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
                if verbose:
                    print(f"\n[HIGH] Credential pattern in skill: {skill_file.name}")
                    print(f"  Pattern: {label}")
                    print(f"  Match: {m.group(0)[:60]!r}")

    # Also scan scripts for debug-log patterns that expose tool outputs
    scripts_root = Path.home() / ".hermes" / "scripts"
    for script_file in scripts_root.glob("*.py"):
        try:
            text = script_file.read_text(errors="replace")
        except OSError:
            continue
        for pat, label in _CRED_PATTERNS[-2:]:  # only key-format patterns in scripts
            if pat.search(text):
                flags.append({
                    "severity": "HIGH",
                    "source": "script_file",
                    "path": str(script_file),
                    "pattern": label,
                    "match_preview": "(key-format literal in script)",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

    print(f"Credential-leak scan: {scanned} skill files checked.")
    return flags


# ── ASI06 backup/log unguarded memory scan (Qiita, Aug 2026) ─────────────────
# Hermes conversation logs and backup zips are unguarded memory copies.
# Check if backups are encrypted and logs are on a non-world-readable path.

def scan_asi06_unguarded_copies(verbose: bool = False) -> list[dict]:
    """
    OWASP ASI06: logs and backups are unguarded memory copies.
    Qiita probe (Aug 2026) found Hermes backup zip unencrypted, incomplete,
    and conversation logs unguarded. Check filesystem permissions.
    """
    flags = []
    hermes_home = Path.home() / ".hermes"

    # Check backup files
    for backup in list(hermes_home.rglob("*.zip")) + list(hermes_home.rglob("*.tar.gz")):
        try:
            mode = backup.stat().st_mode
            world_readable = bool(mode & 0o004)
            if world_readable:
                flags.append({
                    "severity": "HIGH",
                    "source": "asi06_backup",
                    "path": str(backup),
                    "pattern": "world-readable-backup",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
                if verbose:
                    print(f"\n[HIGH] World-readable backup: {backup}")
        except OSError:
            pass

    # Check state.db permissions
    state_db = hermes_home / "state.db"
    if state_db.exists():
        mode = state_db.stat().st_mode
        if mode & 0o044:  # group or world readable
            flags.append({
                "severity": "LOW",
                "source": "asi06_db",
                "path": str(state_db),
                "pattern": "group-or-world-readable-db",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

    # Check cache/delegation for unencrypted task outputs
    deleg_dir = hermes_home / "cache" / "delegation"
    if deleg_dir.exists():
        count = sum(1 for _ in deleg_dir.rglob("*.txt"))
        if count > 100:
            flags.append({
                "severity": "LOW",
                "source": "asi06_delegation_logs",
                "path": str(deleg_dir),
                "pattern": f"large-unencrypted-log-cache ({count} files)",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

    print(f"ASI06 scan: {len(flags)} unguarded-copy issues found.")
    return flags


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="AM-Sentry: passive memory poisoning scanner")
    parser.add_argument("--since", type=int, default=7, metavar="DAYS")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    print(f"AM-Sentry scan — last {args.since} days — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    db_flags = scan_db(args.since, args.verbose)
    api_flags = scan_hindsight(args.since, args.verbose)
    action_flags = scan_action_layer(args.since, args.verbose)  # sweep 24
    intent_flags = scan_intent_drift(args.since, args.verbose)   # sweep 29 arXiv:2608.27348
    cred_flags = scan_skill_credentials(args.verbose)                # sweep 29 ASE2026 credential leak
    asi06_flags = scan_asi06_unguarded_copies(args.verbose)          # sweep 29 OWASP ASI06
    tool_auth_flags = scan_tool_auth_gate(args.since, args.verbose)   # arXiv:2608.27146
    durable_inj_flags = scan_durable_file_injection(args.verbose)    # arXiv:2608.27299
    tool_slo_flags = scan_tool_slo_violations(args.since, args.verbose)  # arXiv:2608.26189
    all_flags = db_flags + api_flags + action_flags + intent_flags + cred_flags + asi06_flags + tool_auth_flags + durable_inj_flags + tool_slo_flags

    high = [f for f in all_flags if f["severity"] == "HIGH"]
    low = [f for f in all_flags if f["severity"] == "LOW"]

    print(f"\n{'='*60}")
    print(f"SUMMARY: {len(all_flags)} flags ({len(high)} HIGH, {len(low)} LOW)")
    if high:
        print("HIGH flags require manual review before these memories are trusted.")
    else:
        print("No HIGH-severity flags. Memory store appears clean.")

    # CritICL (arXiv:2608.27455): auto-write critique bank entries for HIGH flags
    _critique_bank = Path(__file__).parent / "critique-bank.py"
    if high and _critique_bank.exists():
        import subprocess as _csp
        for _flag in high[:5]:  # cap at 5 to avoid noise
            _ftype = _flag.get("type", "other")
            _text = _flag.get("text", _flag.get("fact", str(_flag)))[:200]
            _session = _flag.get("session_id", "sentry-auto")
            # Map sentry type to failure mode
            _mode_map = {
                "durable_injection_risk": "tool_injection",
                "tool_slo_retry_without_progress": "retry_loop",
                "intent_drift": "scope_creep",
                "policy_bypass": "constraint_skip",
                "credential_risk": "constraint_skip",
            }
            _mode = _mode_map.get(_ftype, "other")
            _csp.run(
                ["python3", str(_critique_bank), "add",
                 "--session", str(_session),
                 "--failure-mode", _mode,
                 "--critique", f"am-sentry detected: {_ftype} — {_text}",
                 "--query", f"sentry:{_ftype}"],
                capture_output=True, timeout=5
            )

    # Write report
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / f"am-sentry-report-{datetime.now().strftime('%Y-%m-%d')}.json"
    report = {
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "days": args.since,
        "total_flagged": len(all_flags),
        "high": len(high),
        "low": len(low),
        "flags": all_flags,
    }
    _tmp = report_path.with_suffix(".json.tmp")
    _tmp.write_text(json.dumps(report, indent=2))
    _tmp.replace(report_path)
    print(f"Report written to: {report_path}")

    sys.exit(1 if high else 0)


if __name__ == "__main__":
    main()
