#!/usr/bin/env python3
"""Blackbox uncertainty estimation (lm-polygraph-style, API-only).

Stdlib only. Profile-aware. Never raises through shadow/cache paths (H-I7).
Hard core: every per-signal UE score and composite_ue are clipped to [0, 1].
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Iterable, Optional

_hermes_base = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_hermes_profile = os.environ.get("HERMES_PROFILE", "")
_hermes_root = (
    (_hermes_base / "profiles" / _hermes_profile)
    if _hermes_profile and "profiles" not in str(_hermes_base)
    else _hermes_base
)

LEV_CAP = 2000
TEXT_CAP = 50000
SAMPLE_CAP = 32
HIGH_UE_THRESHOLD = 0.5
LENGTH_PRIOR_N = 8.0
LENGTH_PRIOR_MEAN = 200.0
LENGTH_PRIOR_VAR = 100.0 ** 2  # weakly informative; empty text is anomalous

HEDGE_WORDS = (
    "might",
    "could",
    "possibly",
    "uncertain",
    "not sure",
    "may",
    "approximately",
    "likely",
    "probably",
    "unclear",
)

_HEDGE_RE = re.compile(
    r"\b(?:might|could|possibly|uncertain|may|approximately|likely|probably|unclear)\b"
    r"|not sure",
    re.IGNORECASE,
)
_SENT_SPLIT_RE = re.compile(r"[.!?\n]+")
_WORD_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)
_PCT_RE = re.compile(
    r"(?:i(?:['’]m| am)\s+)?(?P<p1>\d{1,3})\s*%\s*(?:confident|sure|certain)"
    r"|(?:confident|sure|certain)\s*(?:at|of|:)?\s*(?P<p2>\d{1,3})\s*%"
    r"|confidence\s*(?:is|[:=])\s*(?P<p3>\d{1,3})\s*%"
    r"|confidence\s*(?:is|[:=])\s*(?P<f>0?\.\d+|1(?:\.0+)?)",
    re.IGNORECASE,
)
_HIGH_CERT = (
    "highly certain",
    "i am certain",
    "i'm certain",
    "i’m certain",
    "no doubt",
    "highly confident",
    "i am sure",
    "i'm sure",
    "i’m sure",
    "definitely",
)
_LOW_CERT = (
    "i'm not sure",
    "i’m not sure",
    "i am not sure",
    "not sure",
    "uncertain",
    "i don't know",
    "i don’t know",
    "no idea",
    "hard to say",
    "unclear",
    "i'm unsure",
    "i’m unsure",
)


def _clip01(x: Any, default: float = 0.5) -> float:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(v):
        return default
    if v < 0.0:
        return 0.0
    if v > 1.0:
        return 1.0
    return v


def _cache_dir() -> Path:
    override = os.environ.get("UE_CACHE_DIR", "").strip()
    p = Path(override) if override else (_hermes_root / "cache")
    try:
        p.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return p


def _scores_path() -> Path:
    return _cache_dir() / "ue-blackbox-scores.jsonl"


def _length_stats_path() -> Path:
    return _cache_dir() / "ue-length-stats.json"


def _atomic_write_json(path: Path, obj: Any) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(str(tmp), str(path))
    except Exception:
        try:
            tmp = path.with_name(path.name + ".tmp")
            if tmp.exists():
                tmp.unlink()
        except Exception:
            pass


def _append_jsonl(path: Path, obj: Any) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(obj, ensure_ascii=False) + "\n"
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(line)
            fh.flush()
    except Exception:
        pass


def _read_json(path: Path, default: Any) -> Any:
    try:
        if not path.exists():
            return default
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        return data
    except Exception:
        return default


def _iter_jsonl(path: Path) -> Iterable[dict]:
    try:
        if not path.exists():
            return
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                s = line.strip()
                if not s or not s.startswith("{"):
                    continue
                try:
                    obj = json.loads(s)
                except Exception:
                    continue
                if isinstance(obj, dict):
                    yield obj
    except Exception:
        return


def _cap_text(s: Any) -> str:
    if s is None:
        return ""
    t = str(s)
    if len(t) > TEXT_CAP:
        return t[:TEXT_CAP]
    return t


def query_hash(query: str) -> str:
    return hashlib.sha256(_cap_text(query).encode("utf-8", errors="replace")).hexdigest()[:16]


def _levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    if abs(len(a) - len(b)) > max(len(a), len(b)):
        return max(len(a), len(b))
    # two-row DP
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i] + [0] * len(b)
        for j, cb in enumerate(b, 1):
            ins = cur[j - 1] + 1
            delete = prev[j] + 1
            sub = prev[j - 1] + (0 if ca == cb else 1)
            cur[j] = ins if ins < delete else delete
            if sub < cur[j]:
                cur[j] = sub
        prev = cur
    return prev[-1]


def pairwise_lexical_sim(samples: list[str]) -> Optional[float]:
    n = len(samples)
    if n < 2:
        return None
    acc = 0.0
    pairs = 0
    for i in range(n):
        si = samples[i][:LEV_CAP]
        for j in range(i + 1, n):
            sj = samples[j][:LEV_CAP]
            denom = max(len(si), len(sj), 1)
            sim = 1.0 - (_levenshtein(si, sj) / denom)
            if sim < 0.0:
                sim = 0.0
            acc += sim
            pairs += 1
    if pairs <= 0:
        return None
    return _clip01(acc / pairs, default=0.0)


def _trigrams(text: str) -> set:
    words = _WORD_RE.findall((text or "").lower())
    if len(words) >= 3:
        return {tuple(words[k : k + 3]) for k in range(len(words) - 2)}
    s = re.sub(r"\s+", " ", (text or "").lower()).strip()
    if len(s) >= 3:
        return {s[k : k + 3] for k in range(len(s) - 2)}
    if s:
        return {s}
    return set()


def jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    if union <= 0:
        return 0.0
    return inter / union


def semantic_cluster_count(samples: list[str], threshold: float = 0.5) -> Optional[int]:
    n = len(samples)
    if n < 1:
        return None
    grams = [_trigrams(s) for s in samples]
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x: int, y: int) -> None:
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[ry] = rx

    for i in range(n):
        for j in range(i + 1, n):
            if jaccard(grams[i], grams[j]) >= threshold:
                union(i, j)
    return len({find(i) for i in range(n)})


def verbalization_confidence(text: str) -> Optional[float]:
    """Parsed confidence in [0,1], or None when the text has no verbalized signal.

    Uninformative 0.5 must not enter the composite (would deflate/inflate UE).
    """
    t = (text or "").strip()
    if not t:
        return None
    m = _PCT_RE.search(t)
    if m:
        if m.group("f"):
            return _clip01(m.group("f"), default=0.5)
        raw = m.group("p1") or m.group("p2") or m.group("p3")
        if raw is not None:
            try:
                pct = float(raw)
            except ValueError:
                return None
            if pct > 100.0:
                pct = 100.0
            return _clip01(pct / 100.0, default=0.5)
    low = t.lower()
    for phrase in _LOW_CERT:
        if phrase in low:
            return 0.2
    for phrase in _HIGH_CERT:
        if phrase in low:
            return 0.9
    return None


def _load_length_stats() -> dict:
    st = _read_json(_length_stats_path(), default={})
    if not isinstance(st, dict):
        st = {}
    n = st.get("n", LENGTH_PRIOR_N)
    mean = st.get("mean", LENGTH_PRIOR_MEAN)
    m2 = st.get("m2", LENGTH_PRIOR_VAR * max(float(n) - 1.0, 1.0))
    try:
        n = float(n)
        mean = float(mean)
        m2 = float(m2)
    except (TypeError, ValueError):
        n, mean, m2 = LENGTH_PRIOR_N, LENGTH_PRIOR_MEAN, LENGTH_PRIOR_VAR * (LENGTH_PRIOR_N - 1.0)
    if n < 2 or not math.isfinite(n) or not math.isfinite(mean) or not math.isfinite(m2):
        n, mean, m2 = LENGTH_PRIOR_N, LENGTH_PRIOR_MEAN, LENGTH_PRIOR_VAR * (LENGTH_PRIOR_N - 1.0)
    return {"n": n, "mean": mean, "m2": m2}


def _update_length_stats(length: int) -> dict:
    st = _load_length_stats()
    n = st["n"] + 1.0
    delta = float(length) - st["mean"]
    mean = st["mean"] + delta / n
    m2 = st["m2"] + delta * (float(length) - mean)
    out = {"n": n, "mean": mean, "m2": m2}
    _atomic_write_json(_length_stats_path(), out)
    return out


def length_anomaly_score(text: str, update: bool = True) -> float:
    nchar = len(text or "")
    if nchar <= 0:
        if update:
            try:
                _update_length_stats(0)
            except Exception:
                pass
        return 1.0
    st = _load_length_stats()
    var = st["m2"] / max(st["n"] - 1.0, 1.0)
    std = math.sqrt(var) if var > 0.0 and math.isfinite(var) else 100.0
    if std < 1e-9:
        std = 100.0
    z = abs(float(nchar) - st["mean"]) / std
    # Dead-zone: |z|<=2 is not an anomaly (short "4" vs prior mean 200 is typical).
    if z <= 2.0:
        score = 0.0
    else:
        score = min(1.0, (z - 2.0) / 3.0)
    if update:
        try:
            _update_length_stats(nchar)
        except Exception:
            pass
    return _clip01(score, default=0.0)


def repetition_score(text: str) -> float:
    words = _WORD_RE.findall((text or "").lower())
    if len(words) < 6:
        return 0.0
    grams = [tuple(words[i : i + 3]) for i in range(len(words) - 2)]
    total = len(grams)
    if total <= 0:
        return 0.0
    uniq = len(set(grams))
    return _clip01((total - uniq) / total, default=0.0)


def hedge_phrase_score(text: str) -> float:
    t = (text or "").strip()
    if not t:
        return 1.0
    parts = [s.strip() for s in _SENT_SPLIT_RE.split(t) if s.strip()]
    if not parts:
        parts = [t]
    hits = 0
    for sent in parts:
        if _HEDGE_RE.search(sent):
            hits += 1
    return _clip01(hits / max(len(parts), 1), default=0.0)


def _load_consistency(query: str, override: Optional[float]) -> Optional[float]:
    if override is not None:
        return _clip01(override)
    qh = query_hash(query)
    candidates = [
        _cache_dir() / "consistency-scores.jsonl",
        _hermes_root / "cache" / "consistency-scores.jsonl",
        _cache_dir() / "condorcet-last.json",
    ]
    for path in candidates:
        try:
            if not path.exists():
                continue
            if path.suffix == ".json":
                obj = _read_json(path, default=None)
                if isinstance(obj, dict):
                    if obj.get("query_hash") in (None, qh, query):
                        for k in ("consistency", "consistency_score", "condorcet", "score"):
                            if k in obj:
                                return _clip01(obj[k])
                continue
            latest = None
            for row in _iter_jsonl(path):
                if row.get("query_hash") == qh or row.get("query") == query:
                    latest = row
            if isinstance(latest, dict):
                for k in ("consistency", "consistency_score", "condorcet", "score"):
                    if k in latest:
                        return _clip01(latest[k])
        except Exception:
            continue
    return None


def _parse_samples(raw: str, response: str) -> list[str]:
    if raw is None:
        raw = ""
    s = str(raw).strip()
    if not s:
        return []
    parts = [p.strip() for p in s.split("|")]
    out = [_cap_text(p) for p in parts if p.strip()]
    return out[:SAMPLE_CAP]


def compute_scores(
    query: str,
    response: str,
    samples_raw: str = "",
    logprob_confidence: Optional[float] = None,
    consistency_override: Optional[float] = None,
    update_length: bool = True,
) -> dict:
    query = _cap_text(query)
    response = _cap_text(response)
    samples = _parse_samples(samples_raw, response)
    empty = not response.strip() or not query.strip()

    lex = pairwise_lexical_sim(samples) if len(samples) >= 2 else None
    clusters = semantic_cluster_count(samples) if len(samples) >= 1 else None
    verb = verbalization_confidence(response)
    length_an = length_anomaly_score(response, update=update_length)
    rep = repetition_score(response)
    hedge = hedge_phrase_score(response)
    cons = _load_consistency(query, consistency_override)

    ue_parts: list[float] = []
    if lex is not None:
        ue_parts.append(_clip01(1.0 - lex, default=0.5))
    if clusters is not None and len(samples) >= 2:
        ue_parts.append(_clip01((clusters - 1) / max(len(samples) - 1, 1), default=0.5))
    if verb is not None:
        ue_parts.append(_clip01(1.0 - verb, default=0.5))
    ue_parts.append(_clip01(length_an, default=0.0))
    ue_parts.append(_clip01(rep, default=0.0))
    ue_parts.append(_clip01(hedge, default=0.0))
    if cons is not None:
        ue_parts.append(_clip01(1.0 - cons, default=0.5))

    if empty:
        composite = 1.0
    elif ue_parts:
        composite = _clip01(sum(ue_parts) / len(ue_parts), default=1.0)
    else:
        composite = 1.0  # fail-closed: no evidence

    # DPI belt: logprob confidence is an upper bound on claimed certainty.
    # If logprobs say the model is unsure, do not let blackbox composite look more sure.
    lp = None
    if logprob_confidence is not None:
        lp = _clip01(logprob_confidence)
        # implied UE from logprob
        lp_ue = _clip01(1.0 - lp, default=0.5)
        if composite < lp_ue:
            composite = lp_ue

    composite = _clip01(composite, default=1.0)
    high_ue = bool(composite > HIGH_UE_THRESHOLD)

    rec = {
        "ts": time.time(),
        "ts_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "query_hash": query_hash(query),
        "scores": {
            "lexical_sim": None if lex is None else round(_clip01(lex), 6),
            "cluster_count": clusters,
            "verbalization": None if verb is None else round(_clip01(verb), 6),
            "length_anomaly": round(_clip01(length_an), 6),
            "repetition": round(_clip01(rep), 6),
            "hedge_phrase": round(_clip01(hedge), 6),
            "consistency": None if cons is None else round(_clip01(cons), 6),
        },
        "composite_ue": round(composite, 6),
        "high_ue": high_ue,
        "n_samples": len(samples),
        "empty_input": empty,
        "logprob_confidence": None if lp is None else round(lp, 6),
        "dpi_applied": bool(lp is not None and empty is False),
    }
    return rec


def score_and_log(**kwargs: Any) -> dict:
    rec = compute_scores(**kwargs)
    _append_jsonl(_scores_path(), rec)
    return rec


def stats() -> dict:
    rows = list(_iter_jsonl(_scores_path()))
    n = len(rows)
    if n == 0:
        return {"n": 0, "mean_composite_ue": None, "high_ue_rate": None, "path": str(_scores_path())}
    comps = [_clip01(r.get("composite_ue"), default=None) for r in rows]
    comps = [c for c in comps if c is not None]
    # _clip01 never returns None; filter finite only
    comps = []
    for r in rows:
        try:
            v = float(r.get("composite_ue"))
        except (TypeError, ValueError):
            continue
        if math.isfinite(v):
            comps.append(_clip01(v, default=0.5))
    high = sum(1 for r in rows if r.get("high_ue") is True)
    mean = (sum(comps) / len(comps)) if comps else None
    return {
        "n": n,
        "mean_composite_ue": None if mean is None else round(mean, 6),
        "high_ue_rate": round(high / n, 6),
        "path": str(_scores_path()),
    }


def self_test() -> int:
    failures: list[str] = []

    def check(cond: bool, msg: str) -> None:
        if not cond:
            failures.append(msg)

    # Isolate cache so production jsonl is not required / polluted
    isolated = _hermes_root / "cache" / "scratch" / "ue-self-test-scorer"
    try:
        isolated.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    os.environ["UE_CACHE_DIR"] = str(isolated)
    for leftover in isolated.glob("*"):
        try:
            leftover.unlink()
        except Exception:
            pass

    # 1. empty inputs -> high UE, no raise
    r = compute_scores("", "", update_length=False)
    check(r["composite_ue"] == 1.0 and r["high_ue"] is True, "empty must be high_ue=1")
    check(0.0 <= r["composite_ue"] <= 1.0, "composite not in [0,1] empty")

    # 2. no cache files: scoring still works
    r2 = score_and_log(query="what is 2+2", response="4", update_length=True)
    check(0.0 <= r2["composite_ue"] <= 1.0, "composite not in [0,1] simple")
    check(_scores_path().exists(), "jsonl not created")

    # 3. hedge-heavy
    hedgy = "This might possibly be true. It could be uncertain. I'm not sure. It may, approximately, likely, probably be unclear."
    r3 = compute_scores("q", hedgy, update_length=False)
    check(r3["scores"]["hedge_phrase"] > 0.4, "hedge not detected: %s" % r3["scores"]["hedge_phrase"])

    # 4. verbalization numeric
    r4 = compute_scores("q", "I'm 80% confident this is right.", update_length=False)
    check(abs(r4["scores"]["verbalization"] - 0.8) < 1e-6, "verbalization 80%% failed: %s" % r4["scores"]["verbalization"])
    r4b = compute_scores("q", "The capital of France is Paris.", update_length=False)
    check(r4b["scores"]["verbalization"] is None, "uninformative verbalization must be null")

    # 5. identical samples -> high lexical sim, 1 cluster
    r5 = compute_scores(
        "q",
        "the cat sat on the mat",
        samples_raw="the cat sat on the mat|the cat sat on the mat|the cat sat on the mat",
        update_length=False,
    )
    check(r5["scores"]["lexical_sim"] is not None and r5["scores"]["lexical_sim"] > 0.99, "identical lex sim")
    check(r5["scores"]["cluster_count"] == 1, "identical cluster_count")

    # 6. diverse samples -> more clusters
    r6 = compute_scores(
        "q",
        "alpha",
        samples_raw="completely different zebra xylophone|the cat sat on the mat|quantum banana flux",
        update_length=False,
    )
    check(r6["scores"]["cluster_count"] is not None and r6["scores"]["cluster_count"] >= 2, "diverse clusters")

    # 7. DPI: logprob 0.2 must not yield implied confidence > 0.2
    r7 = compute_scores(
        "q",
        "I am highly certain this is correct.",
        logprob_confidence=0.2,
        update_length=False,
    )
    implied_conf = 1.0 - r7["composite_ue"]
    check(implied_conf <= 0.2 + 1e-9, "DPI violated: implied_conf=%s composite=%s" % (implied_conf, r7["composite_ue"]))

    # 8. logprob out of range clipped
    r8 = compute_scores("q", "ok", logprob_confidence=5.0, update_length=False)
    check(r8["logprob_confidence"] == 1.0, "logprob not clipped high")
    r8b = compute_scores("q", "ok", logprob_confidence=-2.0, update_length=False)
    check(r8b["logprob_confidence"] == 0.0, "logprob not clipped low")

    # 9. repetition
    r9 = compute_scores("q", "the cat sat the cat sat the cat sat the cat sat", update_length=False)
    check(r9["scores"]["repetition"] > 0.3, "repetition not detected")

    # 10. very long text does not raise
    long_s = ("word " * 20000) + "might"
    r10 = compute_scores("q" * 100, long_s, update_length=False)
    check(0.0 <= r10["composite_ue"] <= 1.0, "long text composite")

    # 11. malformed-like None strings
    r11 = compute_scores("None", "null", update_length=False)
    check(0.0 <= r11["composite_ue"] <= 1.0, "None-like")

    # 12. stats on jsonl
    st = stats()
    check(st["n"] >= 1, "stats n")

    # 13. consistency override in [0,1]
    r13 = compute_scores("q", "a stable answer", consistency_override=1.0, update_length=False)
    check(0.0 <= r13["composite_ue"] <= 1.0, "consistency composite")

    # 14. whitespace query treated empty
    r14 = compute_scores("   ", "hello world this is a response", update_length=False)
    check(r14["empty_input"] is True and r14["composite_ue"] == 1.0, "whitespace query not empty")

    if failures:
        print(json.dumps({"self_test": "FAIL", "failures": failures}))
        return 1
    print(json.dumps({"self_test": "PASS", "n_checks": 14}))
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    try:
        ap = argparse.ArgumentParser(description="Blackbox UE scorer (lm-polygraph-style)")
        ap.add_argument("--self-test", action="store_true")
        sub = ap.add_subparsers(dest="cmd")
        p_score = sub.add_parser("score", help="score a query/response")
        p_score.add_argument("--query", default="")
        p_score.add_argument("--response", default="")
        p_score.add_argument("--samples", default="")
        p_score.add_argument("--logprob-confidence", default=None)
        p_score.add_argument("--consistency", default=None)
        sub.add_parser("stats", help="aggregate jsonl stats")
        sub.add_parser("self-test", help="run self-test")
        args = ap.parse_args(argv)

        if args.self_test or args.cmd in ("self-test", "self_test"):
            return self_test()
        if args.cmd == "stats":
            print(json.dumps(stats(), ensure_ascii=False))
            return 0
        if args.cmd == "score" or args.cmd is None:
            lp = getattr(args, "logprob_confidence", None)
            cons = getattr(args, "consistency", None)
            lp_f: Optional[float] = None
            cons_f: Optional[float] = None
            if lp is not None and str(lp).strip() != "":
                try:
                    lp_f = float(lp)
                except (TypeError, ValueError):
                    lp_f = None
            if cons is not None and str(cons).strip() != "":
                try:
                    cons_f = float(cons)
                except (TypeError, ValueError):
                    cons_f = None
            rec = score_and_log(
                query=getattr(args, "query", ""),
                response=getattr(args, "response", ""),
                samples_raw=getattr(args, "samples", ""),
                logprob_confidence=lp_f,
                consistency_override=cons_f,
            )
            print(json.dumps(rec, ensure_ascii=False))
            return 0
        ap.print_help()
        return 1
    except Exception:
        try:
            print(json.dumps({"error": "unhandled", "composite_ue": 1.0, "high_ue": True, "scores": {}}))
        except Exception:
            pass
        return 1


if __name__ == "__main__":
    sys.exit(main())
