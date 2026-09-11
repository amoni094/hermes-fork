"""Task complexity scorer — 8-signal mean in [0, 1]. Stdlib only."""
from __future__ import annotations

import re
from typing import Optional


class TaskComplexityScorer:
    AMBIGUITY_RE = re.compile(r"(maybe|could|unclear|possibly|not sure|might)", re.IGNORECASE)
    CONSTRAINT_RE = re.compile(r"(must|never|always|only|required|forbidden)", re.IGNORECASE)
    MULTISTEP_RE = re.compile(r"(then|after that|next|finally|step [0-9]|first.*then)", re.IGNORECASE)
    TOOL_RE = re.compile(r"(terminal|file|search|deploy|build|install|run|execute)", re.IGNORECASE)
    _CODE_CHARS_RE = re.compile(r"[`{}[\]();=<>#\\]")

    def __init__(self) -> None:
        self._recent_tokens: set[str] = set()

    def score(self, text: str, recent_tokens: Optional[set] = None) -> float:
        """Mean of 8 sub-scores in [0, 1]. Empty text → 0.0."""
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
        else:
            novelty = sum(1 for tok in tokens if tok not in recent) / len(tokens)

        scores = (
            length_score,
            code_density,
            ambiguity,
            constraints,
            multistep,
            tool_hints,
            question_count,
            novelty,
        )
        return float(sum(scores) / len(scores))

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
