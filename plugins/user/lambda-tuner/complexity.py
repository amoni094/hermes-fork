"""Task complexity scorer — 9-signal inverse-entropy weighted mean in [0, 1]. Stdlib only."""
from __future__ import annotations

import re
import zlib
from typing import Optional


def description_compression_ratio(text: str) -> float:
    """MDL proxy: compressed_len / raw_len. High ratio = low compressibility = high complexity."""
    return len(zlib.compress(text.encode())) / max(len(text), 1)


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
# why: th-decomp2 — description complexity (MDL proxy via zlib) discriminates ambiguous from clear tasks
SIGNAL_WEIGHTS["description_complexity"] = 1.0
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
        """Inverse-entropy weighted mean of 9 sub-scores in [0, 1]. Empty text → 0.0."""
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
        # zlib headers can make ratio > 1 on short text; clamp so the mean stays in [0, 1]
        description_complexity = min(description_compression_ratio(text), 1.0)

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
            "description_complexity": description_complexity,
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


class TelegraphicCompressor:
    """Telegraphic pre-processing pass for tool_result payloads. Stdlib only.

    Strategy (in order, each pass lowers token count without losing meaning):
      1. Strip HTML tags and decode common HTML entities.
      2. Normalize excess whitespace (blank line runs → single blank, trailing spaces).
      3. Deduplicate adjacent repeated lines (verbatim and near-verbatim via prefix hash).
      4. Remove low-signal boilerplate lines (nav menus, cookie banners, "click here", …).
      5. Collapse long JSON/dict-like lines to structural skeleton (key names kept, values
         truncated) — preserves schema signal without raw data noise.
      6. If still over budget, apply head+tail window as last resort.

    Why this beats naive head+tail:
      - Keeps structural diversity across the entire payload (not just ends).
      - JSON/HTML tool results often have 40-60% low-signal whitespace/boilerplate.
      - No LLM call needed — runs in microseconds, stdlib only, fail-open.

    Target: reduce tool payloads to ≤ max_chars while retaining ≥ 85% of
    semantic signal for the LLM's use.  This is a heuristic — not a guarantee.
    """

    _HTML_TAG_RE = re.compile(r"<[^>]{0,200}>")
    _ENTITY_MAP = {
        "&amp;": "&", "&lt;": "<", "&gt;": ">", "&quot;": '"',
        "&apos;": "'", "&nbsp;": " ", "&#39;": "'", "&#x27;": "'",
    }
    _ENTITY_RE = re.compile(r"&(?:#\d{1,6}|#x[0-9a-fA-F]{1,6}|[a-zA-Z]{2,8});")

    # Boilerplate line patterns (case-insensitive, anchored at line start/end or full match).
    _BOILERPLATE_RE = re.compile(
        r"^\s*("
        r"skip\s+to\s+(main\s+)?content"
        r"|cookie\s+(policy|consent|notice|banner)"
        r"|accept\s+all\s+cookies"
        r"|privacy\s+policy"
        r"|terms\s+(of\s+)?(service|use)"
        r"|all\s+rights\s+reserved"
        r"|click\s+here\s+(to\s+)?"
        r"|subscribe\s+(to\s+)?(our\s+)?(newsletter|updates)"
        r"|follow\s+us\s+on"
        r"|share\s+(this\s+)?(article|page|post)"
        r"|advertisement"
        r"|table\s+of\s+contents"
        r"|\[image[^\]]{0,60}\]"
        r"|\[IMAGE[^\]]{0,60}\]"
        r")\s*$",
        re.IGNORECASE,
    )

    # JSON-like value patterns to truncate (keep the key, stub the value).
    _JSON_VALUE_RE = re.compile(
        r'("(?:[^"\\]|\\.){0,80}")(\s*:\s*)'  # key
        r'("(?:[^"\\]|\\.){80,}"'             # long string value
        r'|\[(?:[^\[\]]{200,})\]'             # long array
        r'|\{(?:[^{}]{200,})\})',              # long nested object
    )

    def _decode_entities(self, text: str) -> str:
        def _replace(m: re.Match) -> str:
            raw = m.group(0)
            return self._ENTITY_MAP.get(raw, raw) or raw
        return self._ENTITY_RE.sub(_replace, text)

    def _strip_html(self, text: str) -> str:
        text = self._HTML_TAG_RE.sub(" ", text)
        return self._decode_entities(text)

    def _normalize_whitespace(self, text: str) -> str:
        lines = text.splitlines()
        # Strip trailing whitespace per line.
        lines = [l.rstrip() for l in lines]
        # Collapse runs of blank lines to a single blank.
        out: list[str] = []
        prev_blank = False
        for line in lines:
            is_blank = not line.strip()
            if is_blank and prev_blank:
                continue
            out.append(line)
            prev_blank = is_blank
        return "\n".join(out)

    def _dedup_lines(self, text: str) -> str:
        """Remove adjacent identical lines and near-identical lines (same first 60 chars)."""
        lines = text.splitlines(keepends=True)
        out: list[str] = []
        prev_full = None
        prev_prefix = None
        for line in lines:
            stripped = line.rstrip()
            prefix = stripped[:60]
            if stripped == prev_full or (len(stripped) > 60 and prefix == prev_prefix):
                continue
            out.append(line)
            prev_full = stripped
            prev_prefix = prefix
        return "".join(out)

    def _remove_boilerplate(self, text: str) -> str:
        lines = text.splitlines(keepends=True)
        return "".join(l for l in lines if not self._BOILERPLATE_RE.match(l))

    def _skeleton_json_values(self, text: str) -> str:
        """Replace long JSON string/array/object values with a length stub."""
        def _stub(m: re.Match) -> str:
            key_part = m.group(1)
            sep_part = m.group(2)
            val = m.group(3)
            stub = '"[…{} chars]"'.format(len(val))
            return key_part + sep_part + stub
        return self._JSON_VALUE_RE.sub(_stub, text)

    def _head_tail(self, text: str, max_chars: int) -> str:
        chunk = max_chars // 3
        head = text[:chunk]
        tail = text[-chunk:]
        omitted = len(text) - 2 * chunk
        return (
            head + "\n[...{} chars omitted by lambda-tuner telegraphic compressor...]\n".format(omitted) + tail
        )

    def compress(self, content: str, max_chars: int = 4000) -> str:
        """Apply telegraphic passes in order; fall back to head+tail if still over budget."""
        text = content

        # Pass 1: strip HTML (web_extract output is often HTML-heavy)
        if "<" in text and ">" in text:
            candidate = self._strip_html(text)
            if len(candidate) < len(text):
                text = candidate

        # Pass 2: normalize whitespace
        text = self._normalize_whitespace(text)
        if len(text) <= max_chars:
            return text

        # Pass 3: remove boilerplate lines
        text = self._remove_boilerplate(text)
        if len(text) <= max_chars:
            return text

        # Pass 4: deduplicate adjacent repeated lines
        text = self._dedup_lines(text)
        if len(text) <= max_chars:
            return text

        # Pass 5: skeleton JSON values
        text = self._skeleton_json_values(text)
        if len(text) <= max_chars:
            return text

        # Pass 6: head+tail fallback
        return self._head_tail(text, max_chars)

    def should_compress(self, role: str, content: str, threshold: int = 2000) -> bool:
        """Fire on tool results over threshold chars (lower than old compactor's 4000 —
        telegraphic passes are cheap so we can apply earlier)."""
        return role == "tool" and len(content) > threshold


_DEFAULT_TELEGRAPHIC = TelegraphicCompressor()


class ToolResultCompactor:
    """Compatibility shim: delegates to TelegraphicCompressor, falls back to head+tail.

    External callers (plugins.py compact_tool_result, tests) use this class;
    keeping the API stable avoids touching call sites.
    """

    TRUNCATION_MARKERS = ["[truncated]", "...", "(continued)", "[omitted]"]

    def compact(self, content: str, max_chars: int = 4000) -> str:
        if len(content) <= max_chars:
            return content
        return _DEFAULT_TELEGRAPHIC.compress(content, max_chars)

    def should_compact(self, role: str, content: str) -> bool:
        # why: lower threshold (2000 vs 4000) — telegraphic passes are cheap stdlib ops,
        # applying earlier catches medium payloads that head+tail would miss entirely.
        return _DEFAULT_TELEGRAPHIC.should_compress(role, content, threshold=2000)


DEFAULT_COMPACTOR = ToolResultCompactor()
