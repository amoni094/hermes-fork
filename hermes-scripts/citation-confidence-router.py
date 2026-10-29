#!/usr/bin/env python3
"""Route answers by citation confidence: cite if >0.7 else silent."""
import os
from pathlib import Path
_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base


import argparse
import json
import re
import sys
from datetime import datetime, timezone, UTC

OUT = _hermes_root / "cache" / "citation-routing.json"
CITE_RE = re.compile(r"(\[[0-9]+\]|https?://\S+|arxiv:\d{4}\.\d+|\([A-Za-z].*\d{4}\))", re.IGNORECASE)


def _atomic_write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2) + "\n")
    os.replace(str(tmp), str(path))


def route(claim: str, source: str = "", confidence: float | None = None) -> dict:
    has_cite = bool(CITE_RE.search(claim or "") or CITE_RE.search(source or "") or (source or "").strip())
    if confidence is None:
        conf = 0.85 if has_cite else 0.2
        src = source or ""
        looks_url = "http://" in src or "https://" in src or "[" in (claim or "")
        if has_cite and (not looks_url) and len((src or claim or "").split()) < 3:
            conf = 0.55
    else:
        conf = min(1.0, max(0.0, float(confidence)))
    decision = "cite_and_answer" if conf > 0.7 else "silent"
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "confidence": round(conf, 6),
        "has_source": has_cite,
        "decision": decision,
    }


def self_test() -> dict:
    a = route("The court held X [1].", source="https://example.com/case")
    b = route("I guess this is true.")
    assert a["decision"] == "cite_and_answer", a
    assert b["decision"] == "silent", b
    c = route("x", confidence=0.71)
    assert c["decision"] == "cite_and_answer"
    return {"self_test": "PASS", "cite": a, "silent": b}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--claim", default="")
    ap.add_argument("--source", default="")
    ap.add_argument("--confidence", type=float, default=None)
    args = ap.parse_args()
    if args.self_test:
        r = self_test()
        print(json.dumps(r, indent=2))
        sys.exit(0 if r.get("self_test") == "PASS" else 1)
    claim = args.claim
    if not claim and not sys.stdin.isatty():
        claim = sys.stdin.read()
    out = route(claim, args.source, args.confidence)
    try:
        _atomic_write_json(OUT, out)
    except Exception:
        pass
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
