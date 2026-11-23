#!/usr/bin/env python3
"""CONTINUITY signed context-token for delegate_task child construction.

HMAC-SHA256 over canonical JSON of all ContextToken fields except signature.
Crypto (ContextToken, _canonical_payload, sign, verify) copied from
/tmp/spikes/005-continuity-context-token/spike.py.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone


@dataclass
class ContextToken:
    origin_session_id: str
    granted_scope: list[str]
    tool_restrictions: list[str]
    expiry_turns: int
    issued_at: str
    signature: str = field(default="")


def _canonical_payload(obj: ContextToken | dict) -> bytes:
    data = asdict(obj) if isinstance(obj, ContextToken) else dict(obj)
    data.pop("signature", None)
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode(
        "utf-8"
    )


def sign(token: ContextToken, secret: bytes | str) -> str:
    """HMAC-SHA256 over JSON of all fields except signature. Mutates token.signature."""
    key = secret.encode("utf-8") if isinstance(secret, str) else secret
    digest = hmac.new(key, _canonical_payload(token), hashlib.sha256).hexdigest()
    token.signature = digest
    return digest


def verify(token_dict: dict, secret: bytes | str) -> bool:
    """Return True iff HMAC-SHA256 of unsigned fields matches token_dict['signature']."""
    if not isinstance(token_dict, dict):
        return False
    provided = token_dict.get("signature")
    if not provided or not isinstance(provided, str):
        return False
    key = secret.encode("utf-8") if isinstance(secret, str) else secret
    expected = hmac.new(key, _canonical_payload(token_dict), hashlib.sha256).hexdigest()
    try:
        return hmac.compare_digest(expected, provided)
    except (TypeError, ValueError):
        return False


def make_child_token(parent_session_id, scope, restrictions, expiry_turns, secret) -> ContextToken:
    token = ContextToken(
        origin_session_id=parent_session_id,
        granted_scope=list(scope),
        tool_restrictions=list(restrictions),
        expiry_turns=expiry_turns,
        issued_at=datetime.now(timezone.utc).isoformat(),
    )
    sign(token, secret)
    return token


def format_for_prompt(token: ContextToken) -> str:
    """Compact one-line string to embed in a child system prompt."""
    payload = json.dumps(asdict(token), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return f"CONTINUITY {payload}"
