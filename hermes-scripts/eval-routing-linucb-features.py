#!/usr/bin/env python3
"""eval-routing-linucb-features.py — 8-d contextual LinUCB on qrels.jsonl.

Features per (query, skill) pair:
  0 query_len            character length of query
  1 max_token_overlap    |Q ∩ skill.tokens| / max(|Q|, 1)
  2 skill_name_match     1 if skill-name tokens subset of query else Jaccard
  3 description_len      character length of skill description
  4 bm25_score           BM25 cosine of query vs skill
  5 hour_of_day          synthetic in [0,1] from qid hash (no clock in qrels)
  6 session_depth_proxy  synthetic in [0,1] from qid ordinal
  7 query_word_count     whitespace word count

Disjoint-arm LinUCB (shared theta, ridge): A <- A + x x^T, b <- b + r x.
95% CI: theta_i ± 1.96 * sigma * sqrt((A^{-1})_{ii}), sigma from residuals.

Source: Li et al. LinUCB; Lattimore & Szepesvari Ch 19.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import os
import re
import sys
import tempfile
import time
from collections import defaultdict
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base

EPS = 1e-15
D = 8
RIDGE = 1.0
ALPHA = 0.5
BM25_K1 = 1.5
BM25_B = 0.75
FEATURE_NAMES = [
    "query_len",
    "max_token_overlap",
    "skill_name_match",
    "description_len",
    "bm25_score",
    "hour_of_day",
    "session_depth_proxy",
    "query_word_count",
]
STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "be", "use", "when",
    "that", "this", "it", "as", "if", "how", "what", "which", "do", "does",
    "can", "will", "not", "all", "any", "has", "have", "been", "using",
}


def _cache_dir() -> Path:
    override = os.environ.get('HERMES_CACHE_DIR', '').strip()
    p = Path(override) if override else (_hermes_root / 'cache')
    try:
        p.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return p


def _atomic_write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(obj, indent=2) + '\n')
    os.replace(str(tmp), str(path))


def _load_json(path: Path, default):
    try:
        return json.loads(path.read_text())
    except (OSError, FileNotFoundError, json.JSONDecodeError):
        return default


def tokenize(text: str) -> list:
    tokens = re.findall(r"[a-z][a-z0-9]*", (text or "").lower())
    return [t for t in tokens if t not in STOPWORDS and len(t) > 2]


def build_bm25(skills: list):
    n = len(skills)
    df = defaultdict(int)
    dls = []
    for s in skills:
        toks = s.get("tokens") or tokenize(" ".join([s.get("name") or "", s.get("description") or ""]))
        s["_toks"] = [t.lower() for t in toks]
        dls.append(len(s["_toks"]))
        for t in set(s["_toks"]):
            df[t] += 1
    avgdl = (sum(dls) / n) if n else 1.0
    idf = {t: max(math.log((n - c + 0.5) / (c + 0.5) + 1), 0.0) for t, c in df.items()}
    for s, dl in zip(skills, dls):
        tf_raw = defaultdict(float)
        for t in s["_toks"]:
            tf_raw[t] += 1
        vec = {}
        for t, freq in tf_raw.items():
            tf_bm25 = (freq * (BM25_K1 + 1)) / (freq + BM25_K1 * (1 - BM25_B + BM25_B * dl / max(avgdl, EPS)))
            vec[t] = tf_bm25 * idf.get(t, 0.0)
        nrm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        s["_vec"] = {t: v / nrm for t, v in vec.items()}
    return skills, idf


def query_vec(tokens, idf):
    q_tf = defaultdict(float)
    for t in tokens:
        q_tf[t] += 1
    raw = {}
    for t, freq in q_tf.items():
        tf_bm25 = (freq * (BM25_K1 + 1)) / (freq + BM25_K1)
        raw[t] = tf_bm25 * idf.get(t, 0.0)
    nrm = math.sqrt(sum(v * v for v in raw.values())) or 1.0
    return {t: v / nrm for t, v in raw.items()}


def cosine(a, b):
    return sum(a[t] * b[t] for t in set(a) & set(b))


def mat_eye(d, ridge=RIDGE):
    return [[ridge if i == j else 0.0 for j in range(d)] for i in range(d)]


def mat_vec(A, x):
    return [sum(A[i][j] * x[j] for j in range(len(x))) for i in range(len(A))]


def vec_dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def invert(A):
    """Gauss-Jordan inverse; A is dxd. Raises on singular."""
    n = len(A)
    m = [A[i][:] + [1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
    for i in range(n):
        piv = i
        best = abs(m[i][i])
        for r in range(i + 1, n):
            if abs(m[r][i]) > best:
                best = abs(m[r][i])
                piv = r
        if best < EPS:
            raise ValueError("singular")
        if piv != i:
            m[i], m[piv] = m[piv], m[i]
        div = m[i][i]
        for c in range(2 * n):
            m[i][c] /= div
        for r in range(n):
            if r == i:
                continue
            f = m[r][i]
            for c in range(2 * n):
                m[r][c] -= f * m[i][c]
    return [row[n:] for row in m]


def sherman_morrison(Ainv, x):
    Ax = mat_vec(Ainv, x)
    den = 1.0 + vec_dot(x, Ax)
    if abs(den) < EPS:
        return Ainv
    d = len(x)
    out = [row[:] for row in Ainv]
    for i in range(d):
        for j in range(d):
            out[i][j] -= Ax[i] * Ax[j] / den
    return out


def _hour_proxy(qid: str) -> float:
    h = hashlib.sha256(("hour:" + qid).encode()).digest()
    return (h[0] % 24) / 23.0 if 23 else 0.0


def _depth_proxy(qid: str, ordinal: int, n_q: int) -> float:
    return (ordinal / max(n_q - 1, 1)) if n_q else 0.0


def extract_features(query, skill, bm25, qid, ordinal, n_q):
    qtoks = tokenize(query)
    stoks = set(skill.get("_toks") or tokenize(" ".join([skill.get("name") or "", skill.get("description") or ""])))
    qset = set(qtoks)
    overlap = (len(qset & stoks) / max(len(qset), 1)) if qset else 0.0
    name_toks = set(tokenize((skill.get("name") or "").replace("-", " ")))
    if name_toks and name_toks <= qset:
        name_match = 1.0
    elif name_toks or qset:
        name_match = len(name_toks & qset) / max(len(name_toks | qset), 1)
    else:
        name_match = 0.0
    desc = skill.get("description") or ""
    x = [
        float(len(query)) / 200.0,           # scale chars
        float(overlap),
        float(name_match),
        float(len(desc)) / 200.0,
        float(bm25),
        float(_hour_proxy(qid)),
        float(_depth_proxy(qid, ordinal, n_q)),
        float(len(query.split())) / 20.0,
    ]
    return x


def load_qrels(path: Path) -> list:
    rows = []
    if not path.exists():
        return rows
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict):
            continue
        rows.append(obj)
    return rows


def run_linucb(qrels, skills, idf):
    by_name = {s.get("name"): s for s in skills}
    # group by qid
    groups = defaultdict(list)
    for row in qrels:
        qid = str(row.get("qid") or row.get("query") or "")
        groups[qid].append(row)
    qids = list(groups)
    A = mat_eye(D)
    Ainv = invert(A)
    b = [0.0] * D
    xs, rs = [], []
    n_updates = 0
    for qi, qid in enumerate(qids):
        for row in groups[qid]:
            skill_name = row.get("skill") or row.get("skill_name") or ""
            skill = by_name.get(skill_name)
            if not skill:
                continue
            query = row.get("query") or ""
            qv = query_vec(tokenize(query), idf)
            bm25 = cosine(qv, skill.get("_vec") or {})
            x = extract_features(query, skill, bm25, qid, qi, len(qids))
            try:
                rel = float(row.get("relevance", row.get("rel", 0)))
            except (TypeError, ValueError):
                rel = 0.0
            r = 1.0 if rel >= 1.0 else 0.0
            Ainv = sherman_morrison(Ainv, x)
            for i in range(D):
                b[i] += r * x[i]
            xs.append(x)
            rs.append(r)
            n_updates += 1
    theta = mat_vec(Ainv, b)
    # residual sigma
    sse = 0.0
    for x, r in zip(xs, rs):
        pred = vec_dot(theta, x)
        sse += (r - pred) ** 2
    dof = max(len(xs) - D, 1)
    sigma = math.sqrt(sse / dof) if xs else 1.0
    ci = []
    for i in range(D):
        se = sigma * math.sqrt(max(Ainv[i][i], 0.0))
        ci.append({
            "feature": FEATURE_NAMES[i],
            "theta": round(theta[i], 6),
            "se": round(se, 6),
            "ci95_lo": round(theta[i] - 1.96 * se, 6),
            "ci95_hi": round(theta[i] + 1.96 * se, 6),
        })
    return {
        "d": D,
        "n_updates": n_updates,
        "n_queries": len(qids),
        "theta": [round(v, 6) for v in theta],
        "feature_names": FEATURE_NAMES,
        "sigma": round(sigma, 6),
        "ci95": ci,
        "ridge": RIDGE,
        "alpha_ucb": ALPHA,
    }


def run(cache=None):
    cache = cache or _cache_dir()
    idx = _load_json(cache / "skill-router-index.json", {})
    skills = idx.get("skills") if isinstance(idx, dict) else []
    skills = [s for s in skills if isinstance(s, dict) and s.get("name")] if isinstance(skills, list) else []
    skills, idf = build_bm25(skills)
    qrels_path = cache / "qrels.jsonl"
    qrels = load_qrels(qrels_path)
    result = {
        "ts": time.time(),
        "n_skills": len(skills),
        "n_qrels": len(qrels),
        "qrels_path": str(qrels_path),
    }
    if not skills or not qrels:
        result["error"] = "missing_skills_or_qrels"
        result["theta"] = [0.0] * D
        result["ci95"] = []
        return result
    lin = run_linucb(qrels, skills, idf)
    result.update(lin)
    out = cache / "scratch" / "eval-routing-linucb-features.json"
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        _atomic_write_json(out, result)
        result["wrote"] = str(out)
    except Exception:
        pass
    return result


def self_test():
    failures = []
    try:
        skills = [
            {"name": "bandit-skill", "description": "contextual linear bandit regret bound", "tokens": ["contextual", "linear", "bandit", "regret", "bound"]},
            {"name": "pasta-skill", "description": "cooking pasta recipe boiling water", "tokens": ["cooking", "pasta", "recipe", "boiling", "water"]},
        ]
        skills, idf = build_bm25(skills)
        qrels = [
            {"qid": "q1", "query": "linear bandit regret", "skill": "bandit-skill", "relevance": 1},
            {"qid": "q1", "query": "linear bandit regret", "skill": "pasta-skill", "relevance": 0},
            {"qid": "q2", "query": "cook pasta recipe", "skill": "pasta-skill", "relevance": 1},
            {"qid": "q2", "query": "cook pasta recipe", "skill": "bandit-skill", "relevance": 0},
        ]
        lin = run_linucb(qrels, skills, idf)
        assert lin["d"] == 8
        assert lin["n_updates"] == 4
        assert len(lin["theta"]) == 8
        assert len(lin["ci95"]) == 8
        # bm25_score feature should be positively associated with reward
        bm25_i = FEATURE_NAMES.index("bm25_score")
        assert lin["theta"][bm25_i] > 0.0, lin["theta"]
        x = extract_features("linear bandit regret", skills[0], 0.9, "q1", 0, 2)
        assert len(x) == 8
        assert all(math.isfinite(v) for v in x)
    except Exception as e:
        failures.append(f"linucb: {e}")
    try:
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d / "skill-router-index.json").write_text(json.dumps({
                "skills": [
                    {"name": "s1", "description": "foo bar", "tokens": ["foo", "bar"]},
                    {"name": "s2", "description": "baz qux", "tokens": ["baz", "qux"]},
                ]
            }))
            (d / "qrels.jsonl").write_text(
                json.dumps({"qid": "q1", "query": "foo bar", "skill": "s1", "relevance": 1}) + "\n"
                + json.dumps({"qid": "q1", "query": "foo bar", "skill": "s2", "relevance": 0}) + "\n"
            )
            r = run(cache=d)
            assert r.get("n_updates", 0) >= 1
            assert (d / "scratch" / "eval-routing-linucb-features.json").exists()
            # empty qrels
            (d / "qrels.jsonl").write_text("")
            r2 = run(cache=d)
            assert r2.get("error") == "missing_skills_or_qrels"
            # malformed line skipped
            (d / "qrels.jsonl").write_text("not json\n" + json.dumps({"qid": "q", "query": "foo", "skill": "s1", "relevance": 1}) + "\n")
            r3 = run(cache=d)
            assert r3.get("n_qrels") == 1
    except Exception as e:
        failures.append(f"io: {e}")
    return {"self_test": "PASS" if not failures else "FAIL", "n_failures": len(failures), "failures": failures}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        r = self_test()
        print(json.dumps(r, indent=2))
        sys.exit(0 if r["self_test"] == "PASS" else 1)
    try:
        print(json.dumps(run(), indent=2))
    except Exception:
        print(json.dumps({"error": "shadow_path_failed"}))
        sys.exit(0)


if __name__ == "__main__":
    main()
