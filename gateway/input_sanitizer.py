"""input_sanitizer.py — neutralise prompt-injection markers in inbound platform text.

Injects nothing into model context; only strips/escapes sequences that could cause
the model to treat user content as a turn boundary or a trusted slash command.

Coverage:
  - Anthropic: \\n\\nHuman: / \\n\\nAssistant: (double AND single newline variants)
  - ChatML/OpenAI: <|im_start|> / <|im_end|>
  - XML system-prompt injection: </system> / <system> etc.
  - OpenAI JSON role markers embedded in text
  - Hermes slash commands at line start
"""
from __future__ import annotations
import re

# Anthropic-style turn delimiters (double-newline prefix).
_ANTHROPIC_HUMAN = re.compile(r'\n\n(Human\s*:)', re.IGNORECASE)
_ANTHROPIC_ASSISTANT = re.compile(r'\n\n(Assistant\s*:)', re.IGNORECASE)

# Single-newline variants (weaker, but still injection vectors).
_ANTHROPIC_HUMAN_SN = re.compile(r'\n(Human\s*:)', re.IGNORECASE)
_ANTHROPIC_ASSISTANT_SN = re.compile(r'\n(Assistant\s*:)', re.IGNORECASE)

# ChatML / OpenAI tiktoken markers.
_CHATML_START = re.compile(r'<\|im_start\|>', re.IGNORECASE)
_CHATML_END = re.compile(r'<\|im_end\|>', re.IGNORECASE)

# XML-style system prompt injection.
_XML_SYSTEM = re.compile(r'<(/?)system\b', re.IGNORECASE)
_XML_PROMPT = re.compile(r'<(/?)prompt\b', re.IGNORECASE)
_XML_INSTRUCTION = re.compile(r'<(/?)instruction\b', re.IGNORECASE)

# OpenAI JSON role injection: {"role": "system"} embedded in message body.
_JSON_ROLE = re.compile(r'\{[^}]{0,60}"role"\s*:\s*"(system|user|assistant)"', re.IGNORECASE)

# Hermes slash commands at the start of a line.
_SLASH_CMD = re.compile(r'(?m)^[ \t]*/(approve|deny|yolo|stop|new|restart|reset)\b', re.IGNORECASE)

# Replacement marker — unambiguously inert, visible in logs, not ZWS-stripped.
_MARKER = "[⚠STRIPPED:{label}]"


def sanitize_inbound_text(text: str) -> str:
    """Neutralise prompt-injection markers in a platform inbound message body.

    Preserves all meaningful content; only replaces recognised injection sequences
    with visible inert markers. Safe to call on every inbound message.
    """
    if not text:
        return text
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
    text = _SLASH_CMD.sub(lambda m: _MARKER.format(label=f"/{m.group(1)}"), text)
    return text
