"""input_sanitizer.py — neutralise prompt-injection markers in inbound platform text.

Injects nothing into model context; only strips/escapes sequences that could cause
the model to treat user content as a turn boundary or a trusted slash command.

Coverage:
  - Unicode invisible/formatting chars (ZWSP, NBSP, SHY etc.) stripped first (P4-M2)
  - Anthropic: \\n\\nHuman: / \\n\\nAssistant: (double AND single newline variants)
  - Anthropic: Human:/Assistant: at start-of-string / start-of-line (P4-L1)
  - ChatML/OpenAI: <|im_start|> / <|im_end|>
  - XML system-prompt injection: </system> / <system> etc.
  - OpenAI JSON role markers embedded in text
  - Hermes slash commands at line start (Unicode whitespace aware — P4-M1)
"""
from __future__ import annotations
import re

# P4-M2 fix: strip zero-width / soft-hyphen / BOM / invisible formatting chars before
# any delimiter regex runs — prevents "Human\u200b:" bypass.
_INVISIBLE_UNICODE = re.compile(
    r'[\u00ad\u200b\u200c\u200d\u200e\u200f\u2060\u2061\u2062\u2063\u2064\ufeff]'
)

# Anthropic-style turn delimiters (double-newline prefix).
_ANTHROPIC_HUMAN = re.compile(r'\n\n(Human\s*:)', re.IGNORECASE)
_ANTHROPIC_ASSISTANT = re.compile(r'\n\n(Assistant\s*:)', re.IGNORECASE)

# Single-newline variants (weaker, but still injection vectors).
_ANTHROPIC_HUMAN_SN = re.compile(r'\n(Human\s*:)', re.IGNORECASE)
_ANTHROPIC_ASSISTANT_SN = re.compile(r'\n(Assistant\s*:)', re.IGNORECASE)

# P4-L1 fix: start-of-string / start-of-line Human:/Assistant: (no newline prefix).
_ANTHROPIC_HUMAN_BOL = re.compile(r'(?m)^(Human\s*:)', re.IGNORECASE)
_ANTHROPIC_ASSISTANT_BOL = re.compile(r'(?m)^(Assistant\s*:)', re.IGNORECASE)

# ChatML / OpenAI tiktoken markers.
_CHATML_START = re.compile(r'<\|im_start\|>', re.IGNORECASE)
_CHATML_END = re.compile(r'<\|im_end\|>', re.IGNORECASE)

# XML-style system prompt injection.
_XML_SYSTEM = re.compile(r'<(/?)system\b', re.IGNORECASE)
_XML_PROMPT = re.compile(r'<(/?)prompt\b', re.IGNORECASE)
_XML_INSTRUCTION = re.compile(r'<(/?)instruction\b', re.IGNORECASE)

# OpenAI JSON role injection: {"role": "system"} embedded in message body.
# P3-M1 fix: removed {}-boundary — matches "role":"system/user/assistant" anywhere.
_JSON_ROLE = re.compile(r'"role"\s*:\s*"(system|user|assistant)"', re.IGNORECASE)

# Hermes slash commands at the start of a line — catch-all pattern since the command
# registry is plugin-extensible (any /word could be a real command). Restrict to
# word-char-only names to avoid false positives on URL paths (/usr/bin etc.).
# P4-M1 fix: use \s* (Unicode whitespace) instead of [ \t]* to catch NBSP/ZWSP prefix.
_SLASH_CMD = re.compile(r'(?m)^\s*(/[a-zA-Z][a-zA-Z0-9_]{0,31})\b', re.IGNORECASE)

# Replacement marker — unambiguously inert, visible in logs, not ZWS-stripped.
_MARKER = "[⚠STRIPPED:{label}]"


def sanitize_inbound_text(text: str) -> str:
    """Neutralise prompt-injection markers in a platform inbound message body.

    Preserves all meaningful content; only replaces recognised injection sequences
    with visible inert markers. Safe to call on every inbound message.
    """
    if not text:
        return text
    # P4-M2: strip invisible Unicode formatting chars before delimiter regexes.
    text = _INVISIBLE_UNICODE.sub('', text)
    # P4-L1: start-of-string / start-of-line (applied before newline-prefix variants).
    text = _ANTHROPIC_HUMAN_BOL.sub(_MARKER.format(label="Human:"), text)
    text = _ANTHROPIC_ASSISTANT_BOL.sub(_MARKER.format(label="Assistant:"), text)
    # Anthropic double-newline variants (replace the role token, keep surrounding newlines).
    text = _ANTHROPIC_HUMAN.sub(r'\n\n' + _MARKER.format(label="Human:"), text)
    text = _ANTHROPIC_ASSISTANT.sub(r'\n\n' + _MARKER.format(label="Assistant:"), text)
    # Single-newline variants.
    text = _ANTHROPIC_HUMAN_SN.sub(r'\n' + _MARKER.format(label="Human:"), text)
    text = _ANTHROPIC_ASSISTANT_SN.sub(r'\n' + _MARKER.format(label="Assistant:"), text)
    # ChatML.
    text = _CHATML_START.sub(_MARKER.format(label="im_start"), text)
    text = _CHATML_END.sub(_MARKER.format(label="im_end"), text)
    # XML role tags.
    text = _XML_SYSTEM.sub(_MARKER.format(label="system-tag"), text)
    text = _XML_PROMPT.sub(_MARKER.format(label="prompt-tag"), text)
    text = _XML_INSTRUCTION.sub(_MARKER.format(label="instruction-tag"), text)
    # JSON role injection (replace whole match).
    text = _JSON_ROLE.sub(_MARKER.format(label="json-role"), text)
    # Hermes slash commands.
    text = _SLASH_CMD.sub(lambda m: _MARKER.format(label=m.group(1)), text)
    return text
