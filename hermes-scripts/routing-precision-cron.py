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

"""Weekly precision regression audit for the model-tier classifier."""

import importlib.util
import json
import sys
from datetime import UTC, datetime


CANONICAL_AUDIT = [
    ("is it worth testing against a more comprehensive/harder test suite?", "reason", 0, None),
    ("shouldnt orchestrator be smarter than worker?", "reason", 0, None),
    ("why not sonnet 4.6 or opus 4.8 or 5+", "reason", 0, None),
    ("whats a tier above deepseek flash for orchestrator? shouldnt it be flexible depending on task anyway?", "reason", 0, None),
    ("wire into live hermes routing then do a recursive adversarial pass and wiring audit. In parallel, is it worth considering", "elite", 0, None),
    ("consider o3, gpt 5.5 and 5.6 vs sonnet 5 too", "reason", 1, "reason"),
    ("yes but what about higher tier claude models too?", "reason", 1, "reason"),
    ("are there any grounds to use higher tier models?", "reason", 1, "reason"),
    ("are there any other models that are available from the api keys you have that you havent tested?", "fast", 0, None),
    ("yes. should you also test out each model you use via evals etc to refine when to use them?", "reason", 1, "reason"),
    ("build both the orchestrator layer and the 5 model routing layer", "reason", 0, None),
    ("yes, but is it also worth having sonnet or another smart llm in the background of tasks as orchestrator?", "reason", 1, "reason"),
    ("can you also consider which tasks are suited to deepseek, and other grok/gpt/claude models?", "reason", 1, "reason"),
    ("is it a good idea to lower the llm model to something more basic for shorter tasks and keep better models for longer tasks", "reason", 0, None),
    ("so for more advanced models like sonnet 4.6 none of this makes a difference?", "reason", 1, "reason"),
    ("Compute the sum of the squares of the first 4000 integers using a SINGLE inline python3 -c one-liner", "math", 0, None),
    ("in parallel, recursively survey the knowledge corpus (math/cs/cog sci, books, hermes research and anything else) for imp", "reason", 0, None),
    ("fix all gaps and then do a recursive adversarial pass and wiring audit", "elite", 0, None),
    ("howre we tracking on those and how are we mitigating bad merges or prompt changes?", "reason", 1, "reason"),
    ("whatre the key eval metrics for AI harnesses like hermes-fork", "reason", 0, None),
    ("the desktp backup should backup everything in hermes - memory, scripts, skills, runtime, config and anything else", "reason", 0, None),
    ("do a recursive adversarial pass and wiring audit then commit/push and merge to git backup to the desktop pc too", "elite", 0, None),
    ("fix the acp retreive tool error", "fast", 0, None),
    ("did all cron jobs run overnight", "fast", 0, None),
    ("fix all crons with sandbox errors", "fast", 0, None),
    ("rerun all but no more than 3 at a time", "fast", 1, "fast"),
    ("did you miss any crons when i rebooted before", "fast", 0, None),
    ("update the hermes-fork readme on git", "fast", 0, None),
    ("can you stagger the crons that run at midnight? they seem to use a lot of cpu/ram", "reason", 0, None),
    ("governance hardblock was deliberately switched off wasnt it", "reason", 0, None),
    ("fix all whichever way is best", "fast", 1, "fast"),
    ("is memory working as it should be?", "reason", 0, None),
    ("are there any other similarly dormant parts of hermes-fork?", "reason", 1, "reason"),
    ("are all scripts and crons relevant to compaction wired as they should be?", "reason", 1, "reason"),
    ("using your knowledge base including but not limited to the math/cs/cog sci corpus and books and the hermes research corp", "reason", 0, None),
    ("is the compaction working fully now?", "reason", 1, "reason"),
    ("reconcile all the 4 files and also do a recursive adversarial pass and wiring audit", "elite", 0, None),
    ("all merged and synced with local?", "fast", 1, "fast"),
    ("wire relay_compaction and activate the HHR branch", "reason", 0, None),
    ("fix the hindsight gate issue", "reason", 0, None),
    ("is hermes-forks compression system better than hermes-main?", "reason", 0, None),
    ("is it synced with local?", "fast", 1, "fast"),
    ("did you do a recursive adversarial pass", "fast", 1, "elite"),
    ("there are 3-4 trees in the yard theyre not tall (no more than 2m)", "reason", 1, "reason"),
    ("what about a renovation upfront of the kitchen/bathroom and a fresh paint job then an extension", "reason", 1, "reason"),
    ("id want to renovate/build over time", "reason", 2, "reason"),
    ("bible street not court", "fast", 1, "reason"),
    ("what about 124 bible court eltham?", "reason", 1, "reason"),
    ("its a big plot of land though cant I extend over time?", "reason", 2, "reason"),
    ("what about 3 grey st eltham", "reason", 1, "reason"),
    ("hmm but theres no public transport there", "reason", 2, "reason"),
    ("I always thought frankston north was a nicer and more prestigious area", "reason", 0, None),
    ("when you say frankston, do you mean frankston north around kananook station", "reason", 1, "reason"),
    ("Is Eltham worth buying into now or should I wait till next year", "reason", 0, None),
    ("based on the likely election result can you recut your suburb recommendations?", "reason", 1, "reason"),
    ("its subject to a cultural sensitivity overlay does that change the equation?", "reason", 1, "reason"),
    ("can I independently check the permits?", "reason", 1, "reason"),
    ("is it worth buying into now though or should I wait?", "reason", 1, "reason"),
    ("recall the research you did on house buying / suburb selection recently", "reason", 0, None),
    ("whats the best rear sway bar to get for this", "reason", 0, None),
]


def _now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_classifier():
    path = _hermes_base / "hermes-scripts" / "model-tier-classifier.py"
    spec = importlib.util.spec_from_file_location("model_tier_classifier_audit", path)
    if spec is None or spec.loader is None:
        raise FileNotFoundError(str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_metrics_db():
    path = _hermes_base / "hermes-scripts" / "routing-metrics-db.py"
    spec = importlib.util.spec_from_file_location("routing_metrics_db", path)
    if spec is None or spec.loader is None:
        raise FileNotFoundError(str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_audit(examples, classify_fn) -> dict:
    labels = []
    preds = []
    for query, label, turn_index, prior_tier in examples:
        payload = {"query": query, "turn_index": int(turn_index or 0), "prior_tier": prior_tier}
        try:
            out = classify_fn(payload)
        except Exception:
            out = {}
        pred = str((out or {}).get("tier") or "")
        labels.append(str(label))
        preds.append(pred)

    n = len(labels) or 1
    correct = sum(1 for a, b in zip(labels, preds) if a == b)
    accuracy = correct / n
    tiers = sorted(set(labels) | set(preds) | {"fast", "math", "longctx", "tooluse", "reason", "elite"})
    per_tier = {}
    for t in tiers:
        tp = sum(1 for a, b in zip(labels, preds) if a == t and b == t)
        fp = sum(1 for a, b in zip(labels, preds) if a != t and b == t)
        fn = sum(1 for a, b in zip(labels, preds) if a == t and b != t)
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec = tp / (tp + fn) if (tp + fn) else 0.0
        per_tier[t] = {
            "precision": prec,
            "recall": rec,
            "support": sum(1 for a in labels if a == t),
            "predicted": sum(1 for b in preds if b == t),
            "tp": tp,
            "fp": fp,
            "fn": fn,
        }
    return {
        "n": len(labels),
        "correct": correct,
        "accuracy": accuracy,
        "per_tier": per_tier,
        "labels": labels,
        "preds": preds,
    }


def extra_jsonl_examples() -> list[tuple]:
    path = _hermes_root / "routing-labelled-examples.jsonl"
    out = []
    if not path.is_file():
        return out
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return out
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        q = str(rec.get("query") or "")
        lab = str(rec.get("label") or "")
        if not q or not lab:
            continue
        ti = rec.get("turn_index") or 0
        try:
            ti = int(ti)
        except (TypeError, ValueError):
            ti = 0
        pt = rec.get("prior_tier")
        out.append((q, lab, ti, pt))
    return out


def main() -> int:
    ts = _now_iso()
    clf = load_classifier()
    result = run_audit(CANONICAL_AUDIT, clf.classify)
    pt = result["per_tier"]
    acc = float(result["accuracy"])
    fast_rec = float(pt.get("fast", {}).get("recall") or 0.0)
    reason_rec = float(pt.get("reason", {}).get("recall") or 0.0)
    elite_prec = float(pt.get("elite", {}).get("precision") or 0.0)

    alerts = []
    if acc < 0.85:
        alerts.append("ALERT: precision below threshold")
        print("ALERT: precision below threshold")
    if fast_rec < 0.40:
        alerts.append("ALERT: fast recall degraded (many fast queries going to reason)")
        print("ALERT: fast recall degraded (many fast queries going to reason)")
    if elite_prec < 0.80:
        alerts.append("ALERT: elite precision degraded")
        print("ALERT: elite precision degraded")

    # Hamming drift vs last week's predictions (Cover/stability). Alarm if >10% changed.
    curr_preds = {}
    for (q, _lab, *_rest), pred in zip(CANONICAL_AUDIT, result.get("preds") or []):
        curr_preds[q] = pred
    pred_path = _hermes_root / "cache" / "routing-precision-preds.json"
    try:
        pred_path.parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    prev_preds = {}
    try:
        raw_prev = json.loads(pred_path.read_text(encoding="utf-8"))
        if isinstance(raw_prev, dict):
            prev_preds = {str(k): str(v) for k, v in raw_prev.items()}
    except (OSError, FileNotFoundError, json.JSONDecodeError, TypeError):
        prev_preds = {}
    hamming = {"n_shared": 0, "n_changed": 0, "frac": 0.0, "alarm": False, "changed": []}
    try:
        sig_path = _hermes_base / "hermes-scripts" / "routing-tier-signals.py"
        spec = importlib.util.spec_from_file_location("routing_tier_signals", sig_path)
        if spec is not None and spec.loader is not None:
            smod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(smod)
            hamming = smod.hamming_drift(prev_preds, curr_preds)
    except Exception:
        keys = sorted(set(prev_preds) & set(curr_preds))
        if keys:
            changed = [k for k in keys if prev_preds[k] != curr_preds[k]]
            frac = len(changed) / len(keys)
            hamming = {
                "n_shared": len(keys),
                "n_changed": len(changed),
                "frac": frac,
                "alarm": frac > 0.10,
                "changed": changed[:20],
            }
    if hamming.get("alarm"):
        msg = (
            f"ALERT: classifier Hamming drift "
            f"{float(hamming.get('frac') or 0)*100:.1f}% of queries changed tier"
        )
        alerts.append(msg)
        print(msg)

    payload = {
        "ts": ts,
        "n": result["n"],
        "correct": result["correct"],
        "accuracy": acc,
        "fast_recall": fast_rec,
        "reason_recall": reason_rec,
        "elite_precision": elite_prec,
        "per_tier": {k: {kk: vv for kk, vv in v.items() if kk not in ("tp", "fp", "fn")} for k, v in pt.items()},
        "alerts": alerts,
        "hamming": {k: v for k, v in hamming.items() if k != "changed"},
    }
    try:
        mdb = load_metrics_db()
        mdb.write_metric("precision_audit", payload, source="cron")
        mdb.write_metric("hamming_drift", hamming, source="cron")
    except Exception as exc:
        print("WARN: routing_metrics write failed:", type(exc).__name__, file=sys.stderr)
    try:
        tmp = pred_path.with_suffix(pred_path.suffix + ".tmp")
        tmp.write_text(json.dumps(curr_preds, indent=2) + "\n", encoding="utf-8")
        os.replace(str(tmp), str(pred_path))
    except Exception as exc:
        print("WARN: pred snapshot write failed:", type(exc).__name__, file=sys.stderr)

    print(
        f"PRECISION_AUDIT ts={ts} accuracy={acc*100:.1f}% "
        f"fast_rec={fast_rec*100:.1f}% reason_rec={reason_rec*100:.1f}% "
        f"elite_prec={elite_prec*100:.1f}%"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
