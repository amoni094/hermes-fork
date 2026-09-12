"""Heuristic session-type classifier for compression-profile routing.

Fast, no-LLM: score research vs code signals over a sliding window of the
last 20 messages and return argmax with a confidence score. Low-confidence
or tied verdicts fall back to ``mixed``.
"""
from __future__ import annotations

import re
from typing import Any, Iterable, List, Sequence, Tuple

SESSION_TYPES = ("research", "code", "mixed")

WINDOW_SIZE = 20
CONFIDENCE_FLOOR = 0.4
# Weighted hits needed to saturate the strength term of confidence.
_SATURATION = 4.0

# v4 eval finding: fork_mixed wins or ties on all three content domains.
# Domain-specific policies (fork_research, fork_code) over-prune the "other"
# content type and lose even on their home domain. Route all sessions to
# fork_mixed by default; override explicitly via set_compression_profile().
_FORK_PROFILE = {
    "research": "fork_mixed",
    "code": "fork_mixed",
    "mixed": "fork_mixed",
}
# Legacy mappings preserved for reference / explicit override use.
_FORK_PROFILE_DOMAIN_SPECIFIC = {
    "research": "fork_research",
    "code": "fork_code",
    "mixed": "fork_mixed",
}
_REASONING_BIAS = {
    "research": "high",
    "code": "medium",
    "mixed": "default",
}
_MODEL_TIER = {
    "research": "frontier",
    "code": "balanced",
    "mixed": "fast",
}

# --- Research ----------------------------------------------------------------
_ARXIV_RE = re.compile(
    r"(?i)\barxiv(?:\.org/(?:abs|pdf)/|:\s*|\s+id(?:entifier)?\s*[:=]?\s*|\s+)"
    r"\d{4}\.\d{4,5}(?:v\d+)?"
    r"|\b\d{4}\.\d{4,5}(?:v\d+)?\b"
)
_DOI_RE = re.compile(r"(?i)\b(?:doi:\s*)?10\.\d{4,9}/[-._;()/:A-Z0-9]+")
_SPIKE_RE = re.compile(
    r"(?i)\b(?:LIVITANYI|LI[\s\-]?VITANYI|GALLAGER|COVSHA|COVER[\s\-]?THOMAS)\b"
)
_RESEARCH_LEX_RE = re.compile(
    r"(?i)\b("
    r"papers?|abstracts?|cite|citation|citations|cited|citing"
    r"|findings?|sweep(?:s|ing)?"
    r"|pre-?prints?|literature|bibliography"
    r"|semantic\s+scholar|pubmed"
    r")\b"
)

# --- Code --------------------------------------------------------------------
_FILE_EXT_RE = re.compile(
    r"(?i)(?:^|[\s`'\"(/])[\w./-]+\.(?:py|js|ts|tsx|jsx|go|rs|java|cpp|c|h|rb|php)\b"
)
_DEF_RE = re.compile(
    r"(?i)\b(?:def|class|function|async\s+def|fn)\s+[A-Za-z_]\w*"
    r"|^\s*(?:export\s+)?(?:class|function)\s+"
    r"|::\s*\w+\s*\(",
    re.MULTILINE,
)
_STACK_RE = re.compile(
    r"(?i)\b(?:traceback(?:\s+\(most\s+recent\s+call\s+last\))?|stack\s*trace"
    r"|segfault|assertion(?:error)?)\b"
    r"|File\s+\"[^\"]+\",\s+line\s+\d+"
    r"|\bat\s+\S+\.\S+\("
)
_GIT_RE = re.compile(
    r"(?i)\bgit\s+(?:commit|push|pull|merge|branch|diff|log|rebase|stash|status|checkout|add|clone)\b"
)
_TEST_RE = re.compile(
    r"(?i)\b(?:passed|failed|failure|assert(?:ion|Equal|True|False)?|pytest|jest"
    r"|\d+\s+passed|\d+\s+failed|FAILED|PASSED|ERROR)\b"
)

_RESEARCH_SIGNALS: Sequence[tuple[re.Pattern[str], float]] = (
    (_ARXIV_RE, 3.0),
    (_DOI_RE, 3.0),
    (_SPIKE_RE, 3.0),
    (_RESEARCH_LEX_RE, 1.0),
)
_CODE_SIGNALS: Sequence[tuple[re.Pattern[str], float]] = (
    (_FILE_EXT_RE, 2.0),
    (_DEF_RE, 2.0),
    (_STACK_RE, 3.0),
    (_GIT_RE, 2.0),
    (_TEST_RE, 2.0),
)


def _content_text(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: List[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                text = block.get("text")
                if text:
                    parts.append(str(text))
        return " ".join(parts)
    return str(content)


def _window_text(messages: Iterable[dict]) -> str:
    parts: List[str] = []
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        parts.append(_content_text(msg.get("content")))
    return "\n".join(parts)


def _score(text: str, signals: Sequence[tuple[re.Pattern[str], float]]) -> float:
    total = 0.0
    for pattern, weight in signals:
        hits = pattern.findall(text)
        if hits:
            total += weight * len(hits)
    return total


def _confidence(winner: float, loser: float) -> float:
    """Map hit counts to [0, 1]: strength (absolute hits) × purity (dominance)."""
    if winner <= 0:
        return 0.0
    strength = min(1.0, winner / _SATURATION)
    purity = (winner - loser) / winner
    return max(0.0, min(1.0, strength * (0.45 + 0.55 * purity)))


def classify(messages: list[dict]) -> tuple[str, float]:
    """Classify recent messages as ``research``, ``code``, or ``mixed``.

    Uses the last :data:`WINDOW_SIZE` messages. Returns ``(session_type, confidence)``.
    Confidence below :data:`CONFIDENCE_FLOOR` yields ``mixed``.
    """
    if not messages:
        return "mixed", 0.0

    window = messages[-WINDOW_SIZE:]
    text = _window_text(window)
    if not text.strip():
        return "mixed", 0.0

    research = _score(text, _RESEARCH_SIGNALS)
    code = _score(text, _CODE_SIGNALS)

    if research > code:
        label, conf = "research", _confidence(research, code)
    elif code > research:
        label, conf = "code", _confidence(code, research)
    else:
        residual = _confidence(research, 0.0) * 0.5 if research else 0.0
        return "mixed", residual

    if conf < CONFIDENCE_FLOOR:
        return "mixed", conf
    return label, conf


def classify_with_scores(messages: list[dict]) -> Tuple[str, float, dict[str, float]]:
    """Like :func:`classify` but also returns raw research/code scores (tests/debug)."""
    window = (messages or [])[-WINDOW_SIZE:]
    text = _window_text(window)
    scores = {
        "research": _score(text, _RESEARCH_SIGNALS),
        "code": _score(text, _CODE_SIGNALS),
    }
    label, conf = classify(messages)
    return label, conf, scores


def get_routing_hint(messages: list[dict]) -> dict[str, Any]:
    """LLM-routing + compression-profile hint derived from :func:`classify`."""
    session_type, confidence = classify(messages)
    if session_type not in SESSION_TYPES:
        session_type = "mixed"
    return {
        "session_type": session_type,
        "confidence": float(confidence),
        "compression_profile": _FORK_PROFILE[session_type],
        "reasoning_effort_bias": _REASONING_BIAS[session_type],
        "model_tier_hint": _MODEL_TIER[session_type],
    }
