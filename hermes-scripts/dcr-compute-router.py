#!/usr/bin/env python3
"""Route queries between divergent and convergent reasoning (DCR)."""
import os
from pathlib import Path
_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base


import argparse
import json
import sys
from datetime import datetime, timezone, UTC

OUT = _hermes_root / "cache" / "dcr-routing.json"
KEYS = ("compare", "analyze", "explain")


def _atomic_write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2) + "\n")
    os.replace(str(tmp), str(path))


def complexity(query: str) -> dict:
    words = (query or "").split()
    wc = len(words)
    ql = (query or "").lower()
    hits = [k for k in KEYS if k in ql]
    score = wc + 8 * len(hits)
    mode = "divergent" if score >= 24 or len(hits) >= 2 else "convergent"
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "query_word_count": wc,
        "keywords": hits,
        "complexity": score,
        "mode": mode,
    }


def self_test() -> dict:
    d = complexity("Please compare and analyze and explain the differences between A and B in detail with examples")
    c = complexity("ok")
    assert d["mode"] == "divergent", d
    assert c["mode"] == "convergent", c
    return {"self_test": "PASS", "divergent": d, "convergent": c}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--query", default="")
    ap.add_argument("--text", default="")
    args = ap.parse_args()
    if args.self_test:
        r = self_test()
        print(json.dumps(r, indent=2))
        sys.exit(0 if r.get("self_test") == "PASS" else 1)
    q = args.query or args.text
    if not q and not sys.stdin.isatty():
        q = sys.stdin.read()
    out = complexity(q)
    try:
        _atomic_write_json(OUT, out)
    except Exception:
        pass
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
