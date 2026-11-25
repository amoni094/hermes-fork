#!/usr/bin/env python3
"""Classify a single agent turn as fast|math|longctx|tooluse|elite|reason (stdlib only).

Used as a library (`classify`, `classify_with_model`) and as a CLI.

  python3 model-tier-classifier.py --json '{...}'
  python3 model-tier-classifier.py --self-test
"""
from __future__ import annotations

import os
from pathlib import Path


def _hermes_home() -> Path:
    """Resolve ~/.hermes even when HERMES_HOME is a profile dir.

    hermes-scripts lives under ~/.hermes/, not ~/.hermes/profiles/<name>/.
    If HERMES_HOME ends with /profiles/<name>, strip that suffix. Otherwise
    walk up a few parents looking for hermes-scripts/.
    """
    env = os.environ.get("HERMES_HOME", "").strip()
    p = Path(env) if env else Path.home() / ".hermes"
    if p.name != ".hermes" and p.parent.name == "profiles":
        return p.parent.parent
    cur = p
    for _ in range(4):
        if (cur / "hermes-scripts").is_dir():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    return p


_hermes_base = _hermes_home()
_hermes_profile = os.environ.get("HERMES_PROFILE", "")
_hermes_root = (
    (_hermes_base / "profiles" / _hermes_profile)
    if _hermes_profile and "profiles" not in str(_hermes_base)
    else _hermes_base
)

import argparse
import json
import math
import re
import sys
import time


def _normalize_skill_name(name: str) -> str:
    """Lowercase, strip plugin: prefix, hyphens -> underscores."""
    s = (name or "").strip().lower().removeprefix("plugin:")
    return s.replace("-", "_")


# Precedence: ELITE_TAGS is checked first. 'adversarial' is an elite signal
# (security-critical work), so it lives only in ELITE_TAGS — not here.
# Remaining ADVERSARIAL_TAGS map to reason only when elite did not match.
# github-pr-review is adversarial review -> ELITE_NAMES (elite, not reason).
ADVERSARIAL_TAGS = frozenset({
    "security", "audit", "legal", "review", "critique", "analysis",
})
ADVERSARIAL_NAMES = frozenset({
    _normalize_skill_name(n) for n in (
        "github-pr-adversarial-review",
        "coverage-led-security-audit",
        "github-pr-review",
        "recursive-adversarial-hardening",
    )
})
PROCEDURE_TAGS = frozenset({
    "procedure", "mechanical", "homelab", "dns", "vpn", "devops", "config",
})
MATH_TAGS = frozenset({
    "math", "algorithm", "formula", "proof", "numerical", "statistics",
})
LONGCTX_TAGS = frozenset({
    "longctx", "large-context", "big-file", "codebase-wide",
})
TOOLUSE_TAGS = frozenset({
    "schema", "structured", "tool-use", "json-output",
})
ELITE_TAGS = frozenset({
    "adversarial", "security-critical", "architecture", "compliance",
    "legal-review", "pen-test",
})
ELITE_NAMES = frozenset({
    _normalize_skill_name(n) for n in (
        "coverage-led-security-audit",
        "recursive-adversarial-hardening",
        "github-pr-adversarial-review",
        "github-pr-review",
        "saltzer-schroeder",
        "miller-capabilities",
    )
})
ELITE_SECURITY_NEEDLES = (
    "vulnerability", "exploit", "bypass", "privilege escalation",
    "injection", "cve", "threat model", "attack surface", "zero-day",
    "pen test", "pentest",
)
_ELITE_SEC_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(n) for n in ELITE_SECURITY_NEEDLES) + r")\b",
    re.IGNORECASE,
)
ELITE_ARCH_NEEDLES = (
    "architect the", "design decision", "fundamental tradeoff",
    "system design", "scalability concern",
)
REASONING_RE = re.compile(
    r'\b(why|tradeoff|trade-off|should i|is it safe|risks?|implications?|implications|'
    r'architect|design decision|compare|versus|vs\.|which is better|pros and cons|'
    r'evaluate|assess)\b',
    re.IGNORECASE,
)
CODEISH_RE = re.compile(r'[`\{\[]|def |class |import ')
MATH_RE = re.compile(
    r'\b(calculat|formula|proof|prove|algorithm|arithmetic|correct answer|math|'
    r'equation|sum|product|integral|derivative|eigenvalue|matrix|linear algebra|'
    r'combinatoric|permutation|'
    r'add up the first|first \d+\s+squares)\b',
    re.IGNORECASE,
)
# Patterns that look like math but are subject-area references, not computation requests
MATH_FP_RE = re.compile(
    r"\bmath(?:/cs|\s+corpus|\s+book|\s+research|\s+and\s+cs)\b"
    r"|\b(?:change|alter|shift)\s+the\s+equation\b",  # idiom
    re.IGNORECASE,
)
TOOL_SCHEMA_RE = re.compile(
    r'\b(json schema|tool call|function call|structured output|patch tool|'
    r'write_file|exact format|strict format)\b',
    re.IGNORECASE,
)

# Verbs that start imperative task queries — these should NOT be routed fast
# even if the query is short and has no question mark.
IMPERATIVE_TASK_VERBS: frozenset[str] = frozenset({
    "fix", "wire", "build", "implement", "reconcile", "audit", "refactor",
    "design", "analyse", "analyze", "consider", "review", "write", "create",
    "update", "migrate", "deploy", "configure", "debug", "investigate",
    "optimise", "optimize", "benchmark", "profile", "secure",
    "activate", "integrate", "convert", "extract", "verify",
})

_ELITE_AUDIT_NEEDLES = ('adversarial pass', 'wiring audit', 'recursive adversarial')
_ELITE_AUDIT_RE = re.compile(
    r'\b(?:' + '|'.join(re.escape(n) for n in _ELITE_AUDIT_NEEDLES) + r')\b',
    re.IGNORECASE,
)
PAST_TENSE_STATUS_RE = re.compile(
    r'^(?:did\s+(?:you|it|that|they|we)|have\s+you|has\s+it|was\s+it|were\s+(?:they|we|you)|is\s+it\s+(?:done|finished|complete))\b',
    re.IGNORECASE,
)

# Contractions / tag questions that count as a '?' for short_simple_query.
INTERROGATIVE_RE = re.compile(
    r"\b(?:"
    r"what(?:re|s|ve|'re|'s|'ve)\b"  # whatre, whats, whatve
    r"|how(?:re|s|ve|'re|'s|'ve)\b"  # howre, hows
    r"|where(?:re|s|'re|'s)\b"       # wheres
    r"|who(?:re|s|ve|'re|'s|'ve)\b"  # whos, whove
    r"|why(?:re|s|'re|'s)\b"         # whyre
    r"|when(?:re|s|'re|'s)\b"        # whens
    r"|isn't\s+it\b|isnt\s+it\b"     # tag questions
    r"|wasn't\s+it\b|wasnt\s+it\b"
    r"|weren't\s+(?:they|we|you)\b|werent\s+(?:they|we|you)\b"
    r"|didn't\s+(?:you|it|that)\b|didnt\s+(?:you|it|that)\b"
    r"|hasn't\s+it\b|hasnt\s+it\b"
    r")",
    re.IGNORECASE,
)

# Recommendation / research asks — not fast even without '?'.
RECOMMENDATION_RE = re.compile(
    r"\b(?:"
    r"what(?:'?s)?\s+the\s+best\b"     # whats the best, what's the best
    r"|which\s+(?:is|would|should|one)\b"  # which is better, which should I
    r"|(?:should|would)\s+(?:i|we|you)\b"  # should I, would you
    r"|(?:is|are)\s+it\s+worth\b"      # is it worth
    r"|(?:worth|better|worse)\s+(?:buying|getting|using|doing|waiting)\b"
    r")",
    re.IGNORECASE,
)

# P7: confirmations / status checks that are always fast in-session (turn_index > 0).
_FAST_WHITELIST_EXACT = frozenset({
    "y", "yes", "no", "ok", "done", "sure", "yep",
    "do it", "run it", "try it", "go ahead", "proceed",
})
FAST_STATUS_RE = re.compile(
    r"^(?:did|does|is|are|was|were)\s+"
    r"(?:it|that|this|they|you|he|she)\s+"
    r"(?:done|finished|complete|synced|working|up|running|pass|fail)\b",
    re.IGNORECASE,
)

# P3: epistemic hedges — user wants judgment/validation, not a lookup.
HEDGE_RE = re.compile(
    r"\b(?:"
    r"i\s+always\s+thought|i\s+thought|i\s+think|i\s+assumed|"
    r"am\s+i\s+wrong|is\s+that\s+right|is\s+that\s+correct|"
    r"right\?|correct\?|"
    r"isnt\s+it|isn't\s+it|shouldnt\s+it|shouldn't\s+it|"
    r"wouldnt\s+it|wouldn't\s+it"
    r")\b",
    re.IGNORECASE,
)

# P4: explicit comparison/ranking. Bare '\bor\b' is too broad (skipped on purpose).
COMPARISON_RE = re.compile(
    r"\b(?:"
    r"vs\.?|versus|better\s+than|worse\s+than|compared\s+to|"
    r"difference\s+between|pros\s+and\s+cons|trade-?off"
    r")\b",
    re.IGNORECASE,
)

# P5: continuation even without prior_tier.
CONTINUATION_MARKER_RE = re.compile(
    r"\b(?:"
    r"what\s+about|how\s+about|and\s+also|as\s+well|"
    r"but\s+what\s+if|and\s+if|in\s+that\s+case|"
    r"given\s+that|considering\s+that|then\s+what|then\s+how|and\s+then|"
    r"\balso\b|\btoo\b"
    r")\b",
    re.IGNORECASE,
)

# Clarifications that omit '?'. Complementary to INTERROGATIVE_RE (contractions).
IMPLICIT_QUESTION_RE = re.compile(
    r"\b(?:do\s+you\s+mean|does\s+that\s+mean|when\s+you\s+say|"
    r"are\s+you\s+saying|dont\s+you\s+think|don't\s+you\s+think)\b",
    re.IGNORECASE,
)

# Memory/research retrieval — not a mechanical one-liner.
RESEARCH_VERB_RE = re.compile(
    r"^(?:please\s+)?(?:recall|remember|summarise|summarize)\b",
    re.IGNORECASE,
)

# P1 syntactic features (clause / subordinate / negation / modal).
_CLAUSE_RE = re.compile(r"[,;]|\b(?:and|but|because|however|although)\b", re.IGNORECASE)
_SUBORD_RE = re.compile(r"\b(?:if|when|while|unless|since|because)\b", re.IGNORECASE)
_NEGATION_RE = re.compile(r"\b(?:not|never|no)\b|n't", re.IGNORECASE)
_CONDITIONAL_RE = re.compile(r"\b(?:would|could|should|might|may)\b", re.IGNORECASE)

# P2 named-entity pieces.
_NE_VERSION_RE = re.compile(r"\b\d+\.\d+\b")
_NE_IDENT_RE = re.compile(r"\b[A-Za-z][\w]*-[\w-]+")
_NE_MODEL_RE = re.compile(
    r"\b(?:gpt|claude|sonnet|opus|grok|haiku|deepseek|o3|o4|gemini|mistral)\b",
    re.IGNORECASE,
)

# P6 default_safe calibration.
_DOMAIN_KW_RE = re.compile(
    r"\b(?:hermes|compaction|classifier|router|cron|orchestrat|"
    r"hindsight|wiring|adversarial)\b",
    re.IGNORECASE,
)
_TECH_TOKEN_RE = re.compile(
    r"[A-Z][a-z]+[A-Z][A-Za-z0-9]*|[a-z]+_[a-z0-9_]+|\b\d+\.\d+\b"
)

TIERS = ("fast", "math", "longctx", "tooluse", "elite", "reason")

DEFAULT_TIER_MODELS = {
    # Calibrated 2026-11-24 via toolperf benchmark rounds 1+2+3:
    # fast:    deepseek-flash 100% all 5 mechanical tasks vs haiku 70%; cheaper.
    # math:    grok-4.6 100% math tasks; magistral-small rate-limited (untested).
    # longctx: haiku 100% ctx/search; cheaper than grok for these task sizes.
    # tooluse: sonnet-4-6 only passer on err_tool_format; o3 needs retest (n=2).
    # reason:  gpt-5.5 100% all 4 elite tasks; cheaper than sonnet-5 (also 100%).
    #          sonnet-4-6 and o3 both 0% on err_ambiguous_refactor — below 90% bar.
    #          Round 4 n=3 fixed puzzle confirmed: all 6 models pass logic_proof now.
    # elite:   sonnet-5-5 (pending harder tasks; current 4-task suite at ceiling for
    #          all strong models — opus-4-8/gpt-5.6-sol also 100%, no discrimination).
    "fast":    {"provider": "deepseek",  "model": "deepseek-flash"},
    "math":    {"provider": "xai",       "model": "grok-4.6"},
    "longctx": {"provider": "anthropic", "model": "claude-haiku-4-5"},
    "tooluse": {"provider": "anthropic", "model": "claude-sonnet-4-6"},
    "reason":  {"provider": "openai",    "model": "gpt-5.5"},
    "elite":   {"provider": "anthropic", "model": "claude-sonnet-5-5"},
}


def _as_int(value, default: int) -> int:
    if value is None or value is False:
        return default
    if value is True:
        return 1
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_str(value, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _as_bool(value, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value) and value != 0
    s = str(value).strip().lower()
    if s in ("1", "true", "yes", "on"):
        return True
    if s in ("0", "false", "no", "off", ""):
        return False
    return default


def _as_tags(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, (list, tuple, set)):
        return []
    out = []
    for item in value:
        s = str(item).strip()
        if s:
            out.append(s)
    return out


def _starts_code_block(query: str) -> bool:
    s = query.lstrip()
    return s.startswith("```") or s.startswith("`")


def _syntactic_complexity(query: str) -> float:
    """P1: lightweight clause/subordinate/negation/modal score."""
    if not query:
        return 0.0
    clause = len(_CLAUSE_RE.findall(query))
    sub = len(_SUBORD_RE.findall(query))
    neg = len(_NEGATION_RE.findall(query))
    cond = len(_CONDITIONAL_RE.findall(query))
    return clause * 0.3 + sub * 0.4 + neg * 0.2 + cond * 0.3


def _named_entity_density(query: str, words: list[str]) -> float:
    """P2: fraction of tokens that look like names, versions, or model ids."""
    if not words:
        return 0.0
    hits = 0
    for i, w in enumerate(words):
        raw = w.strip(".,!?;:()[]\"'`")
        if not raw:
            continue
        if _NE_VERSION_RE.search(raw) or _NE_IDENT_RE.search(raw):
            hits += 1
            continue
        if _NE_MODEL_RE.fullmatch(raw):
            hits += 1
            continue
        if len(raw) >= 2 and raw.isupper() and raw.isalpha():
            hits += 1
            continue
        if i > 0 and raw[0].isupper() and raw[1:].islower() and raw.isalpha():
            hits += 1
    return hits / len(words)


def _fast_whitelist_match(query: str, turn_index: int) -> bool:
    """P7: in-session confirmations / binary status checks."""
    if turn_index <= 0:
        return False
    q = query.strip().rstrip(".!").strip().lower()
    if q in _FAST_WHITELIST_EXACT:
        return True
    stripped = query.strip()
    if FAST_STATUS_RE.search(stripped) or PAST_TENSE_STATUS_RE.search(stripped):
        return True
    return False


def _calibrate_default_safe(query: str, n_words: int) -> float:
    """P6: lift default_safe confidence when the query is clearly non-trivial."""
    conf = 0.60
    if any(ch in query for ch in ".!?"):
        conf += 0.05
    if query and _TECH_TOKEN_RE.search(query):
        conf += 0.05
    if n_words > 20:
        conf += 0.05
    if query and _DOMAIN_KW_RE.search(query):
        conf += 0.05
    return min(conf, 0.85)


def _strong_directional_signal(query: str, words: list[str], context_tokens: int) -> bool:
    """True if this query has a signal that must override continuation_bias."""
    if query and _ELITE_SEC_RE.search(query):
        return True
    if query and _ELITE_AUDIT_RE.search(query):
        return True
    if query and MATH_RE.search(query) and not MATH_FP_RE.search(query):
        return True
    if query and TOOL_SCHEMA_RE.search(query):
        return True
    first3 = {w.lower().rstrip(".,!?") for w in words[:3]}
    if IMPERATIVE_TASK_VERBS & first3:
        return True
    if context_tokens >= 80000:
        return True
    if _starts_code_block(query):
        return True
    return False


HOMELAB_MECH_RE = re.compile(
    r"\b(crons?|readme|sandbox\s+errors?|acp\s+retr\w*)\b",
    re.IGNORECASE,
)
HOMELAB_MECH_BLOCK_RE = re.compile(
    r"\b(adversarial|recursive|security|exploit|cve-?\d|audit pass|wiring audit)\b",
    re.IGNORECASE,
)
SHORT_CORRECTION_RE = re.compile(
    r"^[A-Za-z0-9][\w .'\-]{0,40}\bnot\b[\w .'\-]{1,40}$",
    re.IGNORECASE,
)
_CORRECTION_BLOCK_START = frozenset({
    "do", "don't", "dont", "never", "not", "please", "deploy", "delete",
    "drop", "sudo", "rm",
})


def _homelab_mechanical(query: str, n_words: int) -> bool:
    """Harchol-Balter SITA: short homelab ops are small jobs → fast."""
    if n_words < 2 or n_words > 12:
        return False
    if not query or not HOMELAB_MECH_RE.search(query):
        return False
    if HOMELAB_MECH_BLOCK_RE.search(query):
        return False
    stripped = query.strip()
    # Planning/recommendation questions stay reason ("can you stagger the crons").
    if re.match(r"^(can|could|should|would|why|how|what|is|are|when)\b", stripped, re.IGNORECASE):
        return False
    return True


def _short_correction(query: str, n_words: int) -> bool:
    """Raaijmakers-Shiffrin: short distinctive 'X not Y' probes are retrieval."""
    q = (query or "").strip()
    if n_words < 2 or n_words > 6 or "?" in q:
        return False
    if not SHORT_CORRECTION_RE.match(q):
        return False
    first = q.split()[0].lower().rstrip(".,!?")
    if first in _CORRECTION_BLOCK_START:
        return False
    if re.search(r"\b(deploy|delete|drop|sudo|production|exploit|credential|secret|password)\b", q, re.IGNORECASE):
        return False
    return True


def pac_confidence_bound(n: int, delta: float = 0.05) -> float:
    """Hoeffding PAC bound: 1 - sqrt(log(1/delta)/(2n)). n=60,δ=0.05 → ~0.84."""
    try:
        nn = int(n)
        dd = float(delta)
    except (TypeError, ValueError):
        return 0.65
    if nn <= 0 or not (0.0 < dd < 1.0):
        return 0.65
    return max(0.0, min(1.0, 1.0 - math.sqrt(math.log(1.0 / dd) / (2.0 * nn))))


def calibration_check(n: int = 60, delta: float = 0.05) -> dict:
    """Classifier-level PAC check. Does not rewrite live rule constants."""
    try:
        from pathlib import Path as _P
        import importlib.util as _ilu
        path = _P(__file__).resolve().parent / "routing-tier-signals.py"
        spec = _ilu.spec_from_file_location("_rts_cal", path)
        if spec is None or spec.loader is None:
            raise ImportError("no signals module")
        mod = _ilu.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.calibration_check(n, delta)
    except Exception:
        bound = pac_confidence_bound(n, delta)
        return {"n": n, "delta": delta, "pac_bound": bound, "n_below_bound": None}


_RTS_MOD = None
_RTS_LABELLED: list | None = None
_RTS_LOAD_FAILED = False


def _load_routing_signals():
    """Load routing-tier-signals + audit labels once. Fail-closed."""
    global _RTS_MOD, _RTS_LABELLED, _RTS_LOAD_FAILED
    if _RTS_LOAD_FAILED:
        return None, []
    if _RTS_MOD is not None:
        return _RTS_MOD, _RTS_LABELLED or []
    try:
        from pathlib import Path as _P
        import importlib.util as _ilu
        path = _P(__file__).resolve().parent / "routing-tier-signals.py"
        if not path.is_file():
            _RTS_LOAD_FAILED = True
            return None, []
        spec = _ilu.spec_from_file_location("_rts_pp", path)
        if spec is None or spec.loader is None:
            _RTS_LOAD_FAILED = True
            return None, []
        mod = _ilu.module_from_spec(spec)
        spec.loader.exec_module(mod)
        labelled: list = []
        try:
            prec_path = path.with_name("routing-precision-cron.py")
            pspec = _ilu.spec_from_file_location("_rts_prec", prec_path)
            if pspec is not None and pspec.loader is not None:
                pmod = _ilu.module_from_spec(pspec)
                pspec.loader.exec_module(pmod)
                labelled = [(q, lab) for (q, lab, *_r) in getattr(pmod, "CANONICAL_AUDIT", [])]
        except Exception:
            labelled = []
        _RTS_MOD = mod
        _RTS_LABELLED = labelled
        return mod, labelled
    except Exception:
        _RTS_LOAD_FAILED = True
        return None, []


def _postprocess_decision(decision: dict, data: dict) -> dict:
    """Fail-closed corpus signals. Import errors → original decision."""
    if not isinstance(decision, dict):
        return decision
    try:
        mod, labelled = _load_routing_signals()
        if mod is None:
            return decision
        return mod.apply_signals(decision, data, labelled or [])
    except Exception:
        return decision


def classify(payload: dict | None = None, **kwargs) -> dict:
    """Return {tier, reason, confidence} for one turn. Missing keys use defaults.

    ctx keys: query, skill_tags, skill_name, context_tokens, turn_index, prior_tier,
              prev_tool_error, prev_exit_code, prev_tier, ...
    prior_tier and turn_index default to None and 0 if absent.
    """
    data = dict(payload or {})
    data.update(kwargs)
    decision = _classify_body(data)
    try:
        return _postprocess_decision(decision, data)
    except Exception:
        return decision


def _classify_body(data: dict) -> dict:
    query = _as_str(data.get("query", ""))
    skill_tags = _as_tags(data.get("skill_tags", []))
    skill_name = _as_str(data.get("skill_name", "")).strip()
    prev_tool_calls = _as_int(data.get("prev_tool_calls"), 0)
    prev_exit_code = _as_int(data.get("prev_exit_code"), 0)
    context_tokens = _as_int(data.get("context_tokens"), 0)
    turn_index = _as_int(data.get("turn_index"), 0)
    prev_large_read = _as_bool(data.get("prev_large_read"), False)
    prev_tool_error_type = _as_str(data.get("prev_tool_error_type"), "").strip()
    prev_tier = _as_str(data.get("prev_tier"), "").strip()
    prior_raw = data.get("prior_tier")
    prior_tier = None
    if prior_raw is not None:
        pt = str(prior_raw).strip().lower()
        if pt in TIERS:
            prior_tier = pt

    tags_l = {t.lower() for t in skill_tags}
    skill_name_n = _normalize_skill_name(skill_name)
    words = query.split()
    n_words = len(words)
    qlow = query.lower()

    # Signal priority (first match wins):
    # 1. skill_tags elite (adversarial/security-critical/...)
    # 2. skill_name elite (normalized: plugin: prefix, case, hyphens)
    # 3. query elite keywords (word-boundary; before longctx)
    # 4. prev-turn error -> escalate
    # 5. context > 80k -> longctx
    # 6. tool_schema -> tooluse
    # 7+. math / reason / fast / default
    if tags_l & ELITE_TAGS:
        return {"tier": "elite", "reason": "adversarial_critical_skill", "confidence": 0.98}
    if skill_name_n and skill_name_n in ELITE_NAMES:
        return {"tier": "elite", "reason": "critical_skill_name", "confidence": 0.98}

    # 3. elite query needles BEFORE longctx (CVE + large ctx must be elite, not haiku)
    if query and _ELITE_SEC_RE.search(query):
        return {"tier": "elite", "reason": "security_query", "confidence": 0.90}
    if query and any(p in qlow for p in ELITE_ARCH_NEEDLES):
        return {"tier": "elite", "reason": "architecture_query", "confidence": 0.85}
    if query and _ELITE_AUDIT_RE.search(query) and not PAST_TENSE_STATUS_RE.search(query):
        return {"tier": "elite", "reason": "adversarial_audit_query", "confidence": 0.95}

    # reason: remaining adversarial tags/names (elite already excluded 'adversarial')
    if tags_l & ADVERSARIAL_TAGS:
        return {"tier": "reason", "reason": "adversarial_skill", "confidence": 0.95}
    if skill_name_n and skill_name_n in ADVERSARIAL_NAMES:
        return {"tier": "reason", "reason": "adversarial_skill_name", "confidence": 0.95}

    # 4. error recovery: format_error -> tooluse; reason-tier fail -> elite; otherwise reason
    if prev_exit_code != 0 and turn_index > 0:
        if prev_tool_error_type == "format_error":
            return {"tier": "tooluse", "reason": "tool_format_error", "confidence": 0.90}
        if prev_tier == "reason":
            return {"tier": "elite", "reason": "reason_escalation", "confidence": 0.95}
        return {"tier": "reason", "reason": "prev_error_recovery", "confidence": 0.90}

    # 5. longctx (after elite tags/names/needles)
    if context_tokens > 80000:
        return {"tier": "longctx", "reason": "very_large_context", "confidence": 0.90}
    if tags_l & LONGCTX_TAGS:
        return {"tier": "longctx", "reason": "longctx_skill", "confidence": 0.85}
    if prev_large_read:
        return {"tier": "longctx", "reason": "large_file_read", "confidence": 0.80}

    # 6. tooluse (after longctx, before math)
    if query and TOOL_SCHEMA_RE.search(query):
        return {"tier": "tooluse", "reason": "tool_schema_query", "confidence": 0.80}
    if tags_l & TOOLUSE_TAGS:
        return {"tier": "tooluse", "reason": "tooluse_skill", "confidence": 0.85}

    # math (before remaining reason checks; adversarial already excluded)
    if query and MATH_RE.search(query) and not MATH_FP_RE.search(query):
        return {"tier": "math", "reason": "math_query", "confidence": 0.85}
    if tags_l & MATH_TAGS:
        return {"tier": "math", "reason": "math_skill", "confidence": 0.90}

    # remaining reason checks
    if context_tokens > 40000:
        return {"tier": "reason", "reason": "large_context", "confidence": 0.85}
    if query and REASONING_RE.search(query):
        return {"tier": "reason", "reason": "reasoning_query", "confidence": 0.85}
    if "?" in query and n_words > 20:
        return {"tier": "reason", "reason": "complex_question", "confidence": 0.70}

    # P4 comparison/ranking — never fast for short explicit comparisons.
    if query and n_words < 20 and COMPARISON_RE.search(query):
        return {"tier": "reason", "reason": "comparison_query", "confidence": 0.80}
    # P3 hedges / implicit questions / research verbs: judgment, not lookup.
    if query and HEDGE_RE.search(query):
        return {"tier": "reason", "reason": "hedge_query", "confidence": 0.80}
    if query and IMPLICIT_QUESTION_RE.search(query):
        return {"tier": "reason", "reason": "implicit_question", "confidence": 0.75}
    if query.strip() and RESEARCH_VERB_RE.search(query.strip()):
        return {"tier": "reason", "reason": "research_recall", "confidence": 0.80}
    # P5 implicit continuation markers (even without prior_tier).
    if query and n_words < 12 and CONTINUATION_MARKER_RE.search(query):
        return {"tier": "reason", "reason": "implicit_continuation", "confidence": 0.75}
    # P1/P2: short queries that are syntactically dense or NE-dense are not simple.
    if query.strip() and n_words < 15:
        if _syntactic_complexity(query) >= 2.0:
            return {"tier": "reason", "reason": "syntactic_complexity", "confidence": 0.75}
        if _named_entity_density(query, words) > 0.3:
            return {"tier": "reason", "reason": "named_entity_density", "confidence": 0.75}

    # FORCE FAST
    # P7 whitelist is the highest-priority FAST rule (confirmations only in-session).
    # Capability constraints above (elite/math/longctx/error) still win.
    if _fast_whitelist_match(query, turn_index):
        return {"tier": "fast", "reason": "fast_whitelist", "confidence": 0.90}
    if tags_l & PROCEDURE_TAGS:
        return {"tier": "fast", "reason": "procedure_skill", "confidence": 0.80}
    if prev_tool_calls >= 2 and prev_exit_code == 0 and turn_index > 0:
        return {"tier": "fast", "reason": "mechanical_continuation", "confidence": 0.75}

    # Homelab mechanical ops (SITA): short cron/readme/acp/sandbox jobs → fast.
    if _homelab_mechanical(query, n_words):
        return {"tier": "fast", "reason": "homelab_mechanical", "confidence": 0.78}

    # SAM short 'X not Y' correction overrides continuation_bias.
    if turn_index > 0 and _short_correction(query, n_words):
        return {"tier": "fast", "reason": "short_correction", "confidence": 0.78}

    # Fast-thread short imperative stays fast (does not override elite/security above).
    if (
        turn_index > 0
        and prior_tier == "fast"
        and 2 <= n_words < 10
        and "?" not in query
        and not HOMELAB_MECH_BLOCK_RE.search(query)
    ):
        first3 = {w.lower().rstrip(".,!?") for w in words[:3]}
        if IMPERATIVE_TASK_VERBS & first3:
            return {"tier": "fast", "reason": "fast_thread_imperative", "confidence": 0.72}

    # Continuation bias: short ambiguous follow-ups inherit the previous turn's tier.
    # Runs after elite/math/tooluse/longctx (already returned) and after explicit
    # reason/procedure/mechanical signals. Only truly ambiguous shorts inherit.
    if (
        turn_index > 0
        and n_words < 12
        and prior_tier is not None
        and not _strong_directional_signal(query, words, context_tokens)
    ):
        return {"tier": prior_tier, "reason": "continuation_bias", "confidence": 0.65}

    # Empty/whitespace is not a short simple query — fall through to default_safe.
    has_question = ("?" in query) or bool(INTERROGATIVE_RE.search(query))
    has_recommendation = bool(RECOMMENDATION_RE.search(query))
    first3 = {w.lower().rstrip(".,!?") for w in words[:3]}
    has_imperative = bool(IMPERATIVE_TASK_VERBS & first3)
    code_block = bool(CODEISH_RE.search(query)) or _starts_code_block(query)
    # Reasoning-thread hold: do not drop a reason/elite conversation to fast
    # just because the follow-up is short and has no '?'. Continuation_bias
    # already covers n_words < 12; this covers the 12-14 word remainder.
    reasoning_thread = prior_tier in ("reason", "elite")
    if (
        query.strip()
        and n_words < 15
        and not has_question
        and not has_recommendation
        and not has_imperative
        and not code_block
        and not reasoning_thread
    ):
        return {"tier": "fast", "reason": "short_simple_query", "confidence": 0.70}

    return {
        "tier": "reason",
        "reason": "default_safe",
        "confidence": _calibrate_default_safe(query, n_words),
    }


def classify_with_model(payload: dict, tier_models: dict | None = None) -> dict:
    """Like classify() but adds 'provider' and 'model' to the result."""
    result = classify(payload)
    models = tier_models or DEFAULT_TIER_MODELS
    tier_entry = models.get(result["tier"], models.get("reason", {}))
    return {
        **result,
        "provider": tier_entry.get("provider", ""),
        "model": tier_entry.get("model", ""),
    }


def classify_json(raw: str) -> dict:
    raw = (raw or "").strip()
    if not raw:
        return classify({})
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError:
        return classify({})
    if not isinstance(obj, dict):
        return classify({})
    return classify(obj)


def _emit(decision: dict) -> None:
    sys.stdout.write(json.dumps(decision, ensure_ascii=False) + "\n")


def _check(cond: bool, msg: str, failures: list) -> None:
    if not cond:
        failures.append(msg)


def self_test() -> int:
    failures: list[str] = []

    d = classify({"query": "do the thing", "skill_tags": ["adversarial"]})
    _check(d["tier"] == "elite" and d["reason"] == "adversarial_critical_skill", "adversarial skill -> elite", failures)

    d = classify({
        "query": "restart unbound on the pi",
        "skill_tags": ["procedure"],
        "prev_exit_code": 0,
        "turn_index": 0,
    })
    _check(d["tier"] == "fast" and d["reason"] == "procedure_skill", "procedure skill -> fast", failures)

    d = classify({"query": "continue", "prev_exit_code": 1, "turn_index": 1})
    _check(d["tier"] == "reason" and d["reason"] == "prev_error_recovery", "prev error (no format_error) -> reason", failures)

    d = classify({"query": "restart the vpn please", "turn_index": 0})
    _check(d["tier"] == "fast" and d["reason"] == "short_simple_query", "short simple query -> fast", failures)

    d = classify({"query": "ok", "context_tokens": 90000})
    _check(d["tier"] == "longctx" and d["reason"] == "very_large_context", "very large context (>80k) -> longctx", failures)

    d = classify({"query": "ok", "context_tokens": 50000})
    _check(d["tier"] == "reason" and d["reason"] == "large_context", "medium context (50k) -> reason", failures)

    d = classify({"query": "calculate the eigenvalue of this matrix"})
    _check(d["tier"] == "math" and d["reason"] == "math_query", "math query -> math", failures)

    d = classify({"query": "please continue with remaining steps", "skill_tags": ["algorithm"]})
    _check(d["tier"] == "math" and d["reason"] == "math_skill", "math skill tag -> math", failures)

    d = classify({"query": "use the json schema for this tool call"})
    _check(d["tier"] == "tooluse" and d["reason"] == "tool_schema_query", "tool schema query -> tooluse", failures)

    d = classify({
        "query": "continue",
        "prev_exit_code": 1,
        "turn_index": 1,
        "prev_tool_error_type": "format_error",
    })
    _check(d["tier"] == "tooluse" and d["reason"] == "tool_format_error", "tool format error type -> tooluse", failures)

    d = classify({"query": "ok", "prev_large_read": True})
    _check(d["tier"] == "longctx" and d["reason"] == "large_file_read", "prev large read -> longctx", failures)

    d = classify({
        "query": "please continue with the remaining mechanical steps in this session now and then report done",
        "turn_index": 0,
    })
    _check(d["tier"] == "reason" and d["reason"] == "default_safe", "default no signals -> reason", failures)

    # JSON round-trip / schema for all 6 tiers
    samples = (
        {},
        {"query": ""},
        {"skill_tags": []},
        {"query": "why is this safer than the alternative approach today"},
        {"query": "restart the vpn please", "turn_index": 0},
        {"query": "calculate the eigenvalue"},
        {"query": "ok", "context_tokens": 90000},
        {"query": "use the json schema for this tool call"},
        {"query": "do the thing", "skill_tags": ["adversarial"]},
        {"query": "CVE exploit bypass privilege escalation", "skill_tags": []},
    )
    seen_tiers = set()
    for sample in samples:
        out = classify(sample)
        dumped = json.dumps(out)
        parsed = json.loads(dumped)
        seen_tiers.add(parsed["tier"])
        _check(parsed["tier"] in TIERS, "tier enum", failures)
        _check(isinstance(parsed["reason"], str) and parsed["reason"], "reason non-empty", failures)
        _check(isinstance(parsed["confidence"], (int, float)) and 0.0 <= float(parsed["confidence"]) <= 1.0,
               "confidence in [0,1]", failures)
    _check(set(TIERS) <= seen_tiers, "JSON round-trip valid for all 6 tiers", failures)

    # Missing keys
    d = classify({"query": "hello world today"})
    _check(d["tier"] in TIERS and d["reason"], "missing keys graceful", failures)

    # Empty query -> default reason (not short_simple)
    d = classify({"query": ""})
    _check(d["tier"] == "reason" and d["reason"] == "default_safe", "empty query default reason", failures)

    # First-match wins when every slow+fast signal is present
    d = classify({
        "query": "Why is this design decision risky versus the alternative, and which is better? " + ("word " * 30),
        "skill_tags": ["adversarial", "procedure"],
        "skill_name": "github-pr-review",
        "prev_exit_code": 1,
        "prev_tool_calls": 9,
        "context_tokens": 90000,
        "turn_index": 3,
    })
    _check(d["tier"] == "elite" and d["reason"] == "adversarial_critical_skill", "first matching rule wins", failures)

    # Long query timing
    long_q = ("please continue with the remaining mechanical steps in this session now. " * 200)[:10000]
    t0 = time.perf_counter()
    d = classify({"query": long_q, "turn_index": 0})
    elapsed = time.perf_counter() - t0
    _check(elapsed < 2.0, f"10k query <2s (was {elapsed:.3f}s)", failures)
    _check(d["tier"] in TIERS, "long query no crash", failures)
    json.loads(json.dumps(d))

    # adversarial skill_name
    d = classify({"query": "ok", "skill_name": "coverage-led-security-audit"})
    _check(d["reason"] == "critical_skill_name" and d["tier"] == "elite", "elite skill_name", failures)

    # mechanical continuation
    d = classify({
        "query": "keep going with the rest of these remaining setup steps now please",
        "prev_tool_calls": 2,
        "prev_exit_code": 0,
        "turn_index": 1,
    })
    _check(d["reason"] == "mechanical_continuation", "mechanical continuation", failures)

    # complex question
    d = classify({
        "query": "can you help me finish this remaining setup for the home lab cluster tonight please and also check the logs after?",
        "turn_index": 0,
    })
    _check(d["reason"] == "complex_question", "complex question", failures)

    # classify_with_model returns provider+model
    m = classify_with_model({"query": "calculate the eigenvalue", "skill_tags": []})
    _check(m["tier"] == "math", "classify_with_model math tier", failures)
    _check(isinstance(m.get("provider"), str) and isinstance(m.get("model"), str),
           "classify_with_model provider+model", failures)
    _check("confidence" in m and "reason" in m, "classify_with_model keeps classify fields", failures)

    _check(set(DEFAULT_TIER_MODELS.keys()) == set(TIERS), "DEFAULT_TIER_MODELS has all 6 keys", failures)
    for t in TIERS:
        entry = DEFAULT_TIER_MODELS[t]
        _check(isinstance(entry.get("provider"), str) and entry["provider"], f"DEFAULT_TIER_MODELS[{t}].provider", failures)
        _check(isinstance(entry.get("model"), str) and entry["model"], f"DEFAULT_TIER_MODELS[{t}].model", failures)

    # Adversarial probes
    d = classify({
        "query": "calculate the eigenvalue of this matrix",
        "skill_tags": ["adversarial", "math"],
    })
    _check(d["tier"] == "elite" and d["reason"] == "adversarial_critical_skill",
           "math + adversarial -> elite wins", failures)

    d = classify({
        "query": "use the json schema for this tool call",
        "prev_exit_code": 1,
        "turn_index": 1,
    })
    _check(d["tier"] == "reason" and d["reason"] == "prev_error_recovery",
           "tooluse + prev_exit_code=1 without format_error -> reason wins", failures)

    d = classify({
        "query": "ok",
        "skill_tags": ["adversarial"],
        "context_tokens": 90000,
    })
    _check(d["tier"] == "elite" and d["reason"] == "adversarial_critical_skill",
           "longctx + adversarial -> elite wins", failures)

    d = classify({"query": ""})
    _check(d["tier"] == "reason", "empty query -> reason (default)", failures)

    d = classify({
        "query": "ok",
        "prev_large_read": True,
        "skill_tags": ["adversarial"],
    })
    _check(d["tier"] == "elite" and d["reason"] == "adversarial_critical_skill",
           "prev_large_read=True + adversarial -> elite wins", failures)

    d = classify({"query": "CVE exploit bypass privilege escalation", "skill_tags": []})
    _check(d["tier"] == "elite" and d["reason"] == "security_query",
           "CVE/exploit query -> elite", failures)

    d = classify({"query": "pen test the login flow"})
    _check(d["tier"] == "elite" and d["reason"] == "security_query",
           "pen test query -> elite", failures)

    d = classify({
        "query": "architect the data pipeline with fundamental tradeoff between latency and consistency in distributed system design",
        "skill_tags": [],
    })
    _check(d["tier"] == "elite" and d["reason"] == "architecture_query",
           "architecture query -> elite", failures)

    d = classify({"query": "review code", "skill_tags": ["adversarial", "security-critical"]})
    _check(d["tier"] == "elite" and d["reason"] == "adversarial_critical_skill",
           "elite skill_tags -> elite", failures)

    d = classify({"query": "CVE exploit bypass privilege escalation", "context_tokens": 90000})
    _check(d["tier"] == "elite" and d["reason"] == "security_query",
           "CVE + 90k ctx -> elite not longctx", failures)

    d = classify({'query': 'compute eigenvalue of matrix'})
    _check(d['tier'] == 'math', 'compute eigenvalue -> math', failures)

    d = classify({'query': 'can you just add up the first 4000 squares for me'})
    _check(d['tier'] == 'math', 'conversational add-up squares -> math', failures)

    d = classify({"query": "report the value", "skill_tags": ["procedure"]})
    _check(d["tier"] == "fast" and d["reason"] == "procedure_skill",
           "procedure tag -> fast", failures)

    d = classify({
        "query": "audit this smart contract for vulnerabilities",
        "skill_name": "coverage-led-security-audit",
    })
    _check(d["tier"] == "elite" and d["reason"] == "critical_skill_name",
           "coverage-led-security-audit -> elite", failures)

    d = classify({"query": "ok", "skill_name": "plugin:coverage-led-security-audit"})
    _check(d["tier"] == "elite" and d["reason"] == "critical_skill_name",
           "plugin: prefix skill_name -> elite", failures)

    d = classify({"query": "ok", "skill_name": "Coverage-Led-Security-Audit"})
    _check(d["tier"] == "elite" and d["reason"] == "critical_skill_name",
           "mixed-case skill_name -> elite", failures)

    d = classify({"query": "dependency injection vulnerability in auth flow"})
    _check(d["tier"] == "elite" and d["reason"] == "security_query",
           "dependency injection + vulnerability -> elite (word boundary)", failures)

    d = classify({"query": "ok", "skill_name": "github-pr-review"})
    _check(d["tier"] == "elite" and d["reason"] == "critical_skill_name",
           "github-pr-review skill_name -> elite (not reason)", failures)

    # FIX 1: imperative verb blocks short_simple_query
    d = classify({'query': 'fix all gaps and then do a recursive adversarial pass and wiring audit'})
    _check(d['tier'] == 'elite', 'imperative fix + adversarial pass -> elite', failures)  # FIX 1 + FIX 3

    d = classify({'query': 'wire relay_compaction and activate the HHR branch'})
    _check(d['tier'] == 'reason', 'wire imperative -> reason not fast', failures)  # FIX 1

    d = classify({'query': 'build both the orchestrator layer and the routing layer'})
    _check(d['tier'] == 'reason', 'build imperative -> reason not fast', failures)  # FIX 1

    # FIX 2: math subject-area reference
    d = classify({'query': 'in parallel, recursively survey the math/cs corpus for improvements'})
    _check(d['tier'] != 'math', 'math/cs corpus is not a math task', failures)  # FIX 2

    d = classify({'query': 'does that change the equation for investing here?'})
    _check(d['tier'] != 'math', 'change the equation idiom is not math', failures)  # FIX 2

    # FIX 3: audit needles
    d = classify({'query': 'do a recursive adversarial pass and wiring audit'})
    _check(d['tier'] == 'elite', 'adversarial pass + wiring audit -> elite', failures)  # FIX 3

    d = classify({'query': 'did you do a recursive adversarial pass'})
    _check(d['tier'] != 'elite', 'past-tense status check not elite', failures)  # FIX 3 guard

    # FIX A: continuation bias
    d = classify({'query': 'what about 3 grey st eltham', 'turn_index': 2, 'prior_tier': 'reason'})
    _check(d['tier'] == 'reason', 'short follow-up inherits prior reason tier', failures)

    d = classify({'query': 'hmm but theres no public transport there', 'turn_index': 3, 'prior_tier': 'reason'})
    _check(d['tier'] == 'reason', 'continuation follow-up inherits reason', failures)

    d = classify({'query': 'is it synced with local?', 'turn_index': 1, 'prior_tier': 'fast'})
    _check(d['tier'] == 'fast', 'fast follow-up stays fast', failures)

    # FIX B: interrogative contractions
    d = classify({'query': 'whatre the key eval metrics for AI harnesses like hermes-fork'})
    _check(d['tier'] != 'fast', 'whatre is interrogative, not fast', failures)

    d = classify({'query': 'governance hardblock was deliberately switched off wasnt it'})
    _check(d['tier'] != 'fast', 'wasnt it tag question is interrogative', failures)

    # FIX C: recommendation queries
    d = classify({'query': 'whats the best rear sway bar to get for this'})
    _check(d['tier'] != 'fast', 'whats the best is recommendation not fast', failures)

    d = classify({'query': 'is it worth buying into now or should I wait'})
    _check(d['tier'] != 'fast', 'is it worth is recommendation not fast', failures)

    # P1 syntactic complexity (short + subordinate/modal/negation stack)
    d = classify({'query': 'if I should not go when it might fail because it could not work'})
    _check(d['tier'] != 'fast', 'P1 complex syntax not short_simple', failures)
    _check(d['reason'] == 'syntactic_complexity', 'P1 reason tag', failures)

    # P2 named-entity density
    d = classify({'query': 'sonnet-5-5 gpt-5.5 grok-4.6 claude-opus'})
    _check(d['tier'] != 'fast', 'P2 NE-dense short query not fast', failures)
    _check(d['reason'] == 'named_entity_density', 'P2 reason tag', failures)

    # P3 hedging
    d = classify({'query': 'I always thought frankston north was a nicer area'})
    _check(d['tier'] == 'reason', 'P3 hedge I always thought -> reason', failures)
    _check(d['reason'] == 'hedge_query', 'P3 reason tag', failures)

    # P4 comparison
    d = classify({'query': 'hermes-fork compared to hermes-main'})
    _check(d['tier'] == 'reason', 'P4 comparison -> reason', failures)
    _check(d['reason'] == 'comparison_query', 'P4 reason tag', failures)

    # P5 implicit continuation markers
    d = classify({'query': 'what about the other option'})
    _check(d['tier'] == 'reason', 'P5 what about -> reason', failures)
    _check(d['reason'] == 'implicit_continuation', 'P5 reason tag', failures)

    # implicit question without '?'
    d = classify({'query': 'when you say frankston, do you mean frankston north'})
    _check(d['tier'] == 'reason', 'implicit do you mean -> reason', failures)

    # research recall verb
    d = classify({'query': 'recall the research you did on house buying recently'})
    _check(d['tier'] == 'reason', 'recall research -> reason', failures)

    # P6 calibration: empty stays 0.60; non-trivial default_safe is in [0.60, 0.85]
    d = classify({'query': ''})
    _check(d['reason'] == 'default_safe' and d['confidence'] == 0.60, 'P6 empty stays 0.60', failures)
    d = classify({
        'query': 'please continue with the remaining mechanical steps in this session now and then report done',
        'turn_index': 0,
    })
    _check(d['reason'] == 'default_safe', 'P6 still default_safe', failures)
    _check(0.60 <= float(d['confidence']) <= 0.85, 'P6 confidence calibrated', failures)

    # P7 whitelist (turn_index > 0 only)
    d = classify({'query': 'yes', 'turn_index': 1})
    _check(d['tier'] == 'fast' and d['reason'] == 'fast_whitelist', 'P7 yes continuation -> fast', failures)
    d = classify({'query': 'yes', 'turn_index': 0})
    _check(d['reason'] != 'fast_whitelist', 'P7 yes on turn 0 not whitelist', failures)
    d = classify({'query': 'is it synced', 'turn_index': 2})
    _check(d['tier'] == 'fast' and d['reason'] == 'fast_whitelist', 'P7 status check -> fast', failures)
    d = classify({'query': 'did you do a recursive adversarial pass', 'turn_index': 1, 'prior_tier': 'elite'})
    _check(d['tier'] == 'fast' and d['reason'] == 'fast_whitelist', 'P7 past-tense status not elite thread', failures)

    # reasoning-thread hold: 12-14 word follow-up stays reason
    d = classify({
        'query': 'there are 3-4 trees in the yard theyre not tall (no more than 2m)',
        'turn_index': 1,
        'prior_tier': 'reason',
    })
    _check(d['tier'] == 'reason', 'reasoning thread hold skips short_simple', failures)

    # corpus-mined predicates
    d = classify({'query': 'bible street not court', 'turn_index': 3, 'prior_tier': 'reason'})
    _check(d['tier'] == 'fast' and d['reason'] == 'short_correction', 'SAM X-not-Y correction', failures)
    d = classify({'query': 'do not deploy this', 'turn_index': 2, 'prior_tier': 'reason'})
    _check(d['reason'] != 'short_correction', 'do-not-deploy is not a short correction', failures)
    d = classify({'query': 'fix the acp retreive tool error'})
    _check(d['tier'] == 'fast' and d['reason'] == 'homelab_mechanical', 'acp retrieve -> fast', failures)
    d = classify({'query': 'fix all crons with sandbox errors'})
    _check(d['tier'] == 'fast' and d['reason'] == 'homelab_mechanical', 'cron sandbox -> fast', failures)
    d = classify({'query': 'update the hermes-fork readme on git'})
    _check(d['tier'] == 'fast' and d['reason'] == 'homelab_mechanical', 'readme -> fast', failures)
    d = classify({'query': 'fix all gaps and then do a recursive adversarial pass and wiring audit'})
    _check(d['tier'] == 'elite', 'homelab must not steal elite audit', failures)
    d = classify({'query': 'fix all whichever way is best', 'turn_index': 1, 'prior_tier': 'fast'})
    _check(d['tier'] == 'fast' and d['reason'] == 'fast_thread_imperative', 'fast-thread imperative', failures)
    d = classify({'query': 'fix the hindsight gate issue'})
    _check(d['tier'] == 'reason', 'hindsight gate stays reason', failures)
    bound = pac_confidence_bound(60, 0.05)
    _check(0.83 < bound < 0.86, 'PAC bound ~0.84', failures)

    if failures:
        print("SELF-TEST FAIL: " + "; ".join(failures), file=sys.stderr)
        return 1
    print("SELF-TEST PASS")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Classify an agent turn as fast|math|longctx|tooluse|elite|reason")
    parser.add_argument("--json", dest="json_arg", default=None, help="Turn payload as JSON object")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--calibration-check", action="store_true")
    args, _unknown = parser.parse_known_args(argv)

    if args.self_test:
        return self_test()
    if args.calibration_check:
        print(json.dumps(calibration_check(), indent=2))
        return 0

    raw = args.json_arg
    if raw is None:
        if sys.stdin.isatty():
            raw = "{}"
        else:
            raw = sys.stdin.read()
    decision = classify_json(raw)
    _emit(decision)
    return 0


if __name__ == "__main__":
    sys.exit(main())
