"""Task complexity scorer — 8-signal inverse-entropy weighted mean in [0, 1]. Stdlib only."""
from __future__ import annotations

import re
from typing import Optional


# Inverse-entropy prior weights (higher = more type-discriminative).
# Requested names mapped onto the 8 live signals in this scorer:
#   code_fraction           → code_density
#   question_density        → question_count
#   tool_diversity          → tool_hints
#   message_length_variance → length_score
#   url_density             → novelty (no URL extractor; novelty is the leftover I-content signal)
#   nested_depth            → constraints
#   iteration_count         → multistep
#   error_rate              → ambiguity (least discriminative)
# Raw priors sum to 9.0; scale so sum(weights) == 8.0, then
# weighted mean sum(s_i * w_i) / sum(w) stays in [0, 1].
_RAW_SIGNAL_WEIGHTS = {
    "code_density": 1.5,
    "question_count": 1.3,
    "tool_hints": 1.4,
    "length_score": 1.2,
    "novelty": 1.2,
    "constraints": 0.8,
    "multistep": 0.9,
    "ambiguity": 0.7,
}
_RAW_WEIGHT_SUM = sum(_RAW_SIGNAL_WEIGHTS.values())
SIGNAL_WEIGHTS = {
    name: raw * (8.0 / _RAW_WEIGHT_SUM) for name, raw in _RAW_SIGNAL_WEIGHTS.items()
}
WEIGHT_SUM = sum(SIGNAL_WEIGHTS.values())


class TaskComplexityScorer:
    AMBIGUITY_RE = re.compile(r"(maybe|could|unclear|possibly|not sure|might)", re.IGNORECASE)
    CONSTRAINT_RE = re.compile(r"(must|never|always|only|required|forbidden)", re.IGNORECASE)
    MULTISTEP_RE = re.compile(r"(then|after that|next|finally|step [0-9]|first.*then)", re.IGNORECASE)
    TOOL_RE = re.compile(r"(terminal|file|search|deploy|build|install|run|execute)", re.IGNORECASE)
    _CODE_CHARS_RE = re.compile(r"[`{}[\]();=<>#\\]")

    def __init__(self) -> None:
        self._recent_tokens: set[str] = set()

    def score(self, text: str, recent_tokens: Optional[set] = None) -> float:
        """Inverse-entropy weighted mean of 8 sub-scores in [0, 1]. Empty text → 0.0."""
        if not text:
            return 0.0
        n = len(text)
        tokens = text.split()
        tok_n = max(len(tokens), 1)

        length_score = min(n / 2000.0, 1.0)
        code_chars = len(self._CODE_CHARS_RE.findall(text))
        code_density = min(code_chars / n, 1.0)
        ambiguity = min(len(self.AMBIGUITY_RE.findall(text)) / tok_n, 1.0)
        constraints = min(len(self.CONSTRAINT_RE.findall(text)) / tok_n, 1.0)
        multistep = min(len(self.MULTISTEP_RE.findall(text)) / tok_n, 1.0)
        tool_hints = min(len(self.TOOL_RE.findall(text)) / tok_n, 1.0)
        question_count = min(text.count("?") / 5.0, 1.0)

        recent = recent_tokens if recent_tokens is not None else self._recent_tokens
        if not tokens:
            novelty = 0.0
        elif not recent:
            # why: empty recent at first lock caused novelty=1.0, inflating complexity and triggering deep reasoning mode unnecessarily
            novelty = 0.5
        else:
            novelty = len(set(tokens) - recent) / max(len(tokens), 1)

        signals = {
            "length_score": length_score,
            "code_density": code_density,
            "ambiguity": ambiguity,
            "constraints": constraints,
            "multistep": multistep,
            "tool_hints": tool_hints,
            "question_count": question_count,
            "novelty": novelty,
        }
        numer = sum(signals[name] * SIGNAL_WEIGHTS[name] for name in SIGNAL_WEIGHTS)
        return float(numer / WEIGHT_SUM)

    def update_recent(self, text: str) -> None:
        """Ingest tokens into the novelty set, capped at 2000."""
        if not text:
            return
        tokens = str(text).split()
        self._recent_tokens.update(tokens)
        overflow = len(self._recent_tokens) - 2000
        if overflow > 0:
            for tok in list(self._recent_tokens)[:overflow]:
                self._recent_tokens.discard(tok)


DEFAULT_SCORER = TaskComplexityScorer()


class ToolResultCompactor:
    """Head+tail MDL cut for oversized tool payloads. Stdlib only."""

    TRUNCATION_MARKERS = ["[truncated]", "...", "(continued)", "[omitted]"]

    def compact(self, content: str, max_chars: int = 4000) -> str:
        if len(content) <= max_chars:
            return content
        chunk = max_chars // 3
        head = content[:chunk]
        tail = content[-chunk:]
        omitted = len(content) - 2 * chunk
        return (
            head
            + chr(10)
            + "[...{} chars omitted by lambda-tuner MDL compactor...]".format(omitted)
            + chr(10)
            + tail
        )

    def should_compact(self, role: str, content: str) -> bool:
        return role == "tool" and len(content) > 4000


DEFAULT_COMPACTOR = ToolResultCompactor()
