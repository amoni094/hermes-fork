#!/usr/bin/env python3
"""Score whether a reasoning trace helps human evaluation of LLM outputs."""
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

OUT = _hermes_root / "cache" / "reasoning-trace-eval-log.json"

STEP_RE = re.compile(
    r"(?:^|\n)\s*(?:step\s*\d+[:.)]\s*|[-*]\s+|\d+[.)]\s+)(.+)",
    re.IGNORECASE,
)


def _atomic_write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2) + "\n")
    os.replace(str(tmp), str(path))


def extract_steps(text: str) -> list:
    t = text or ""
    chunks = re.split(r"(?i)step\s*\d+[:.)]\s*", t)
    found = [c.strip().rstrip(".") for c in chunks if c.strip()]
    if t.lower().lstrip().startswith("step") and found:
        return found
    if len(found) >= 3:
        return found
    found2 = [m.group(1).strip() for m in STEP_RE.finditer(t) if m.group(1).strip()]
    if found2:
        return found2
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", t) if s.strip()]
    return sents[:12]


def _tokens(s: str) -> set:
    return set(re.findall(r"[a-z0-9]+", (s or "").lower()))


def coherence(steps: list) -> float:
    if len(steps) < 2:
        return 1.0 if steps else 0.0
    sims = []
    for a, b in zip(steps, steps[1:]):
        ta, tb = _tokens(a), _tokens(b)
        if not ta and not tb:
            sims.append(1.0)
            continue
        sims.append(len(ta & tb) / float(len(ta | tb) or 1))
    return sum(sims) / float(len(sims))


def relevance(steps: list, query: str) -> float:
    q = _tokens(query)
    if not steps:
        return 0.0
    if not q:
        return 1.0
    hits = [len(q & _tokens(s)) / float(len(q) or 1) for s in steps]
    return sum(hits) / float(len(hits))


def evaluate(text: str, query: str = "") -> dict:
    steps = extract_steps(text)
    coh = coherence(steps)
    rel = relevance(steps, query)
    helpful = 0.5 * coh + 0.5 * rel
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "n_steps": len(steps),
        "coherence": round(coh, 6),
        "relevance": round(rel, 6),
        "helpful_score": round(helpful, 6),
        "helps_human_eval": helpful >= 0.35,
        "steps": steps[:20],
    }


def self_test() -> dict:
    text = "Step 1: Parse the query. Step 2: Retrieve evidence. Step 3: Answer the query using evidence."
    r = evaluate(text, query="query evidence answer")
    assert r["n_steps"] >= 3, r
    assert r["coherence"] >= 0.0
    empty = evaluate("")
    assert empty["n_steps"] == 0
    return {"self_test": "PASS", "sample": r}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--text", default="")
    ap.add_argument("--query", default="")
    args = ap.parse_args()
    if args.self_test:
        r = self_test()
        print(json.dumps(r, indent=2))
        sys.exit(0 if r.get("self_test") == "PASS" else 1)
    text = args.text
    if not text and not sys.stdin.isatty():
        text = sys.stdin.read()
    out = evaluate(text, args.query)
    try:
        _atomic_write_json(OUT, out)
    except Exception:
        pass
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
