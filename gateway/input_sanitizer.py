"""input_sanitizer.py — neutralise prompt-injection markers in inbound platform text.

Injects nothing into model context; only strips/escapes sequences that could cause
the model to treat user content as a turn boundary or a trusted slash command.
"""
from __future__ import annotations
import re

# Anthropic turn delimiters: \n\nHuman: and \n\nAssistant: anywhere in the text.
# These are the actual injection vectors — no line-anchor needed, the double-newline
# prefix is part of the match so we replace the whole sequence.
_ANTHROPIC_HUMAN = re.compile(r'\n\nHuman\s*:', re.IGNORECASE)
_ANTHROPIC_ASSISTANT = re.compile(r'\n\nAssistant\s*:', re.IGNORECASE)
# Hermes slash commands at the START of a line (multiline ^ is correct here).
_SLASH_CMD = re.compile(r'(?m)^[ \t]*/(approve|deny|yolo|stop|new|restart|reset)\b', re.IGNORECASE)


def sanitize_inbound_text(text: str) -> str:
    """Strip prompt-injection markers from a platform inbound message body."""
    if not text:
        return text
    text = _ANTHROPIC_HUMAN.sub('\u200b\u200b[Human]:', text)
    text = _ANTHROPIC_ASSISTANT.sub('\u200b\u200b[Assistant]:', text)
    text = _SLASH_CMD.sub(lambda m: '\u200b' + m.group(0).lstrip(), text)
    return text
