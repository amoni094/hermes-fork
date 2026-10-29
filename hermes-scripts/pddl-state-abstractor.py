#!/usr/bin/env python3
"""Abstract a task description into PDDL-like typed objects, predicates, transitions."""
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

OUT = _hermes_root / "cache" / "pddl-state.json"
STOP = set("the a an of to for and or in on with from by is are be this that".split())


def _atomic_write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2) + "\n")
    os.replace(str(tmp), str(path))


def tokens(text: str) -> list:
    return [t for t in re.findall(r"[A-Za-z][A-Za-z0-9_-]*", text or "") if t.lower() not in STOP]


def abstract_state(task: str) -> dict:
    toks = tokens(task)
    nouns = [t.lower() for t in toks]
    objects = []
    seen = set()
    for n in nouns:
        if n not in seen:
            seen.add(n)
            objects.append({"name": n, "type": "object"})
    predicates = []
    tl = (task or "").lower()
    if "file" in tl or "write" in tl:
        predicates.append("at(?file, ?path)")
    if "install" in tl or "setup" in tl:
        predicates.append("installed(?pkg)")
    if "test" in tl:
        predicates.append("tested(?target)")
    if not predicates:
        predicates.append("pending(?task)")
    transitions = [
        {"from": "init", "action": "start", "to": "working", "pre": predicates[:1], "add": ["in-progress(?task)"]},
        {"from": "working", "action": "finish", "to": "done", "pre": ["in-progress(?task)"], "add": ["complete(?task)"]},
    ]
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "task": task,
        "objects": objects[:32],
        "predicates": predicates,
        "transitions": transitions,
        "init": ["pending(task)"],
        "goal": ["complete(task)"],
    }


def self_test() -> dict:
    r = abstract_state("Write a file and run tests for the installer")
    assert r["objects"], r
    assert r["predicates"], r
    assert r["transitions"], r
    empty = abstract_state("")
    assert empty["goal"]
    return {"self_test": "PASS", "sample": r}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--task", default="")
    ap.add_argument("--text", default="")
    args = ap.parse_args()
    if args.self_test:
        r = self_test()
        print(json.dumps(r, indent=2))
        sys.exit(0 if r.get("self_test") == "PASS" else 1)
    task = args.task or args.text
    if not task and not sys.stdin.isatty():
        task = sys.stdin.read()
    out = abstract_state(task)
    try:
        _atomic_write_json(OUT, out)
    except Exception:
        pass
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
