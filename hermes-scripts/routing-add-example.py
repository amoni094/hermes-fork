#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path


def _hermes_home() -> Path:
    env = os.environ.get("HERMES_HOME", "").strip()
    p = Path(env) if env else Path.home() / ".hermes"
    if p.name != ".hermes" and p.parent.name == "profiles":
        return p.parent.parent
    cur = p
    for _ in range(4):
        if (cur / "hermes-scripts").is_dir():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    return p


_hermes_base = _hermes_home()
_hermes_profile = os.environ.get("HERMES_PROFILE", "")
_hermes_root = (
    (_hermes_base / "profiles" / _hermes_profile)
    if _hermes_profile and "profiles" not in str(_hermes_base)
    else _hermes_base
)

"""Append a labelled routing example and re-run the precision audit."""

import importlib.util
import json
import sys
from datetime import UTC, datetime


VALID = frozenset({"fast", "math", "longctx", "tooluse", "reason", "elite"})


def _now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise FileNotFoundError(str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def usage() -> None:
    print(
        'Usage: python3 routing-add-example.py "<query>" <tier> [turn_index] [prior_tier]',
        file=sys.stderr,
    )


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) < 2:
        usage()
        return 2
    query = args[0]
    tier = str(args[1]).strip().lower()
    if tier == "slow":
        tier = "reason"
    if tier not in VALID:
        print("ERROR: tier must be one of", ", ".join(sorted(VALID)), file=sys.stderr)
        return 2
    turn_index = 0
    if len(args) >= 3 and args[2] not in ("", "None", "none"):
        try:
            turn_index = int(args[2])
        except ValueError:
            print("ERROR: turn_index must be int", file=sys.stderr)
            return 2
    prior_tier = None
    if len(args) >= 4 and args[3] not in ("", "None", "none"):
        prior_tier = str(args[3]).strip().lower()
        if prior_tier == "slow":
            prior_tier = "reason"

    rec = {
        "query": query,
        "label": tier,
        "turn_index": turn_index,
        "prior_tier": prior_tier,
        "added_ts": _now_iso(),
    }
    path = _hermes_root / "routing-labelled-examples.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"APPENDED {path}")

    prec = _load("routing_precision_cron", _hermes_base / "hermes-scripts" / "routing-precision-cron.py")
    clf = prec.load_classifier()
    examples = list(prec.CANONICAL_AUDIT) + prec.extra_jsonl_examples()
    result = prec.run_audit(examples, clf.classify)
    acc = float(result["accuracy"])
    print(
        f"AUDIT n={result['n']} accuracy={acc*100:.1f}% "
        f"correct={result['correct']}/{result['n']}"
    )
    mismatches = [
        (q, lab, pred)
        for (q, lab, *_rest), pred in zip(examples, result["preds"])
        if lab != pred
    ]
    if mismatches:
        print(f"MISCLASSIFIED {len(mismatches)}")
        for q, lab, pred in mismatches[:12]:
            print(f"  gold={lab} pred={pred} q={q[:80]!r}")

    prev_acc = None
    try:
        mdb = prec.load_metrics_db()
        prev = mdb.read_latest("precision_audit", 1)
        if prev:
            prev_acc = float((prev[0].get("value") or {}).get("accuracy") or 0)
    except Exception:
        prev_acc = None
    if prev_acc is not None and (prev_acc - acc) > 0.02:
        print(
            f"REGRESSION WARNING accuracy dropped {(prev_acc - acc)*100:.1f}pp "
            f"(prev={prev_acc*100:.1f}% now={acc*100:.1f}%)"
        )
    try:
        mdb = prec.load_metrics_db()
        mdb.write_metric(
            "precision_audit",
            {
                "ts": _now_iso(),
                "n": result["n"],
                "correct": result["correct"],
                "accuracy": acc,
                "source_script": "routing-add-example",
                "canonical_n": len(prec.CANONICAL_AUDIT),
                "jsonl_n": result["n"] - len(prec.CANONICAL_AUDIT),
            },
            source="manual",
        )
    except Exception as exc:
        print("WARN: routing_metrics write failed:", type(exc).__name__, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
