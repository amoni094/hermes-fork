#!/usr/bin/env python3
"""Verify factual claims in output are attributed to sources (SEVA)."""
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

OUT = _hermes_root / "cache" / "fact-attribution.json"
CLAIM_RE = re.compile(r"(?:^|(?<=[.!?]\s))([A-Z][^.!?]{12,}[.!?])")
CITE_RE = re.compile(r"(\[[0-9]+\]|\([A-Za-z][A-Za-z0-9_-]*\s*,?\s*\d{4}\)|\barXiv:\d{4}\.\d+|https?://\S+)", re.IGNORECASE)


def _atomic_write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2) + "\n")
    os.replace(str(tmp), str(path))


def verify_attribution(text: str) -> dict:
    claims = [m.group(1).strip() for m in CLAIM_RE.finditer(text or "")]
    if not claims:
        sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text or "") if len(s.strip()) > 12]
        claims = sents
    attributed = []
    missing = []
    for c in claims:
        if CITE_RE.search(c):
            attributed.append(c)
        else:
            missing.append(c)
    n = len(claims)
    rate = (len(attributed) / float(n)) if n else 1.0
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "n_claims": n,
        "n_attributed": len(attributed),
        "attribution_rate": round(rate, 6),
        "missing": missing[:20],
        "ok": rate >= 0.7 or n == 0,
    }


def self_test() -> dict:
    t = "Water boils at 100 C [1]. Paris is the capital of France (Smith, 2020). Unsourced claim about widgets."
    r = verify_attribution(t)
    assert r["n_claims"] >= 2, r
    assert r["n_attributed"] >= 1, r
    empty = verify_attribution("")
    assert empty["n_claims"] == 0
    return {"self_test": "PASS", "sample": r}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--text", default="")
    args = ap.parse_args()
    if args.self_test:
        r = self_test()
        print(json.dumps(r, indent=2))
        sys.exit(0 if r.get("self_test") == "PASS" else 1)
    try:
        text = args.text
        if not text and not sys.stdin.isatty():
            text = sys.stdin.read()
        out = verify_attribution(text)
        try:
            _atomic_write_json(OUT, out)
        except Exception:
            pass
        print(json.dumps(out, indent=2))
    except Exception:
        pass


if __name__ == "__main__":
    main()
