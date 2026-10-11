#!/usr/bin/env python3
"""skill-beta-seed.py — seed Beta priors from BM25 self-rank reciprocal rank.

For each skill, query = name + description. Rank all skills by BM25 cosine.
If the skill sits at 1-indexed rank r, set alpha = 1 + 1/r, beta = 1
(Jeffreys-free uniform prior plus a single fractional pseudo-success).

Does not overwrite skills that already have observations (alpha+beta > 2)
unless --force. Writes cache/skill-beta-state-seeded.json always; --apply
merges into cache/skill-beta-state.json.

Source: Lattimore KL-UCB needs a non-vacuous Beta prior; Manning BM25 ranking.
"""
from __future__ import annotations
import argparse
import json
import math
import os
import re
import sys
import tempfile
import time
from collections import defaultdict
from pathlib import Path

import os
from pathlib import Path
_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base

EPS = 1e-15
BM25_K1 = 1.5
BM25_B = 0.75
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


def build_bm25(skills: list) -> tuple:
    n = len(skills)
    df = defaultdict(int)
    doc_lengths = []
    for s in skills:
        toks = s.get("tokens") or []
        doc_lengths.append(len(toks))
        for t in set(toks):
            df[t] += 1
    avgdl = (sum(doc_lengths) / n) if n else 1.0
    idf = {t: max(math.log((n - cnt + 0.5) / (cnt + 0.5) + 1), 0.0) for t, cnt in df.items()}
    vecs = []
    for s, dl in zip(skills, doc_lengths):
        tf_raw = defaultdict(float)
        for t in (s.get("tokens") or []):
            tf_raw[t] += 1
        vec = {}
        for t, freq in tf_raw.items():
            tf_bm25 = (freq * (BM25_K1 + 1)) / (freq + BM25_K1 * (1 - BM25_B + BM25_B * dl / max(avgdl, EPS)))
            vec[t] = tf_bm25 * idf.get(t, 0.0)
        nrm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        vecs.append({t: v / nrm for t, v in vec.items()})
    return vecs, idf


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
    shared = set(a) & set(b)
    return sum(a[t] * b[t] for t in shared)


def self_ranks(skills, vecs, idf):
    ranks = {}
    for i, s in enumerate(skills):
        name = s.get("name") or ""
        qtoks = tokenize(" ".join([name, s.get("description") or ""])) or list(s.get("tokens") or [])
        qv = query_vec(qtoks, idf)
        scored = [(cosine(qv, vecs[j]), skills[j].get("name") or "") for j in range(len(skills))]
        scored.sort(key=lambda x: (-x[0], x[1]))
        r = len(skills)
        for k, (_sc, nm) in enumerate(scored, 1):
            if nm == name:
                r = k
                break
        ranks[name] = r
    return ranks


def seed_state(skills, existing=None, force=False):
    existing = existing if isinstance(existing, dict) else {}
    if not skills:
        return {"skills": {}, "n_skills": 0, "ts": time.time(), "method": "bm25_reciprocal_rank"}
    vecs, idf = build_bm25(skills)
    ranks = self_ranks(skills, vecs, idf)
    out = {}
    for s in skills:
        name = s.get("name") or ""
        if not name:
            continue
        prev = existing.get(name) if isinstance(existing.get(name), dict) else {}
        try:
            pa = float(prev.get("alpha", 1.0))
            pb = float(prev.get("beta", 1.0))
        except (TypeError, ValueError):
            pa, pb = 1.0, 1.0
        observed = (pa + pb) > 2.0 + 1e-9
        r = max(int(ranks.get(name, len(skills))), 1)
        alpha = 1.0 + 1.0 / r
        beta = 1.0
        if observed and not force:
            out[name] = {
                "alpha": pa,
                "beta": pb,
                "seeded": False,
                "self_rank": r,
                "source": "observed",
            }
        else:
            out[name] = {
                "alpha": alpha,
                "beta": beta,
                "seeded": True,
                "self_rank": r,
                "source": "bm25_reciprocal_rank",
            }
    # keep observed skills that are not in the BM25 index
    for nm, prev in existing.items():
        if nm in out or not isinstance(prev, dict):
            continue
        try:
            pa = float(prev.get("alpha", 1.0))
            pb = float(prev.get("beta", 1.0))
        except (TypeError, ValueError):
            continue
        if (pa + pb) > 2.0 + 1e-9:
            out[nm] = {
                "alpha": pa,
                "beta": pb,
                "seeded": False,
                "self_rank": None,
                "source": "observed_unindexed",
            }
    return {
        "ts": time.time(),
        "method": "bm25_reciprocal_rank",
        "formula": "alpha=1+1/r, beta=1; r=BM25 self-rank of name+description",
        "n_skills": len(out),
        "n_seeded": sum(1 for v in out.values() if v.get("seeded")),
        "n_preserved": sum(1 for v in out.values() if not v.get("seeded")),
        "skills": out,
    }


def _index_skills(cache: Path) -> list:
    idx = _load_json(cache / "skill-router-index.json", {})
    skills = idx.get("skills") if isinstance(idx, dict) else []
    return [s for s in skills if isinstance(s, dict) and s.get("name")] if isinstance(skills, list) else []


def _flat_beta(bundle: dict) -> dict:
    """Flatten to the on-disk skill-beta-state.json shape {name: {alpha, beta}}."""
    skills = bundle.get("skills") if isinstance(bundle, dict) else {}
    flat = {}
    for nm, e in (skills or {}).items():
        if not isinstance(e, dict):
            continue
        try:
            flat[nm] = {"alpha": float(e.get("alpha", 1.0)), "beta": float(e.get("beta", 1.0))}
        except (TypeError, ValueError):
            flat[nm] = {"alpha": 1.0, "beta": 1.0}
    return flat


def run(cache=None, apply=False, force=False):
    cache = cache or _cache_dir()
    skills = _index_skills(cache)
    existing = _load_json(cache / "skill-beta-state.json", {})
    if not isinstance(existing, dict):
        existing = {}
    # tolerate wrapped shape
    if "skills" in existing and isinstance(existing.get("skills"), dict) and "alpha" not in str(list(existing.keys())[:3]):
        existing = existing["skills"]
    bundle = seed_state(skills, existing=existing, force=force)
    seeded_path = cache / "skill-beta-state-seeded.json"
    try:
        _atomic_write_json(seeded_path, bundle)
    except Exception:
        pass
    if apply:
        try:
            _atomic_write_json(cache / "skill-beta-state.json", _flat_beta(bundle))
        except Exception:
            pass
    bundle["wrote"] = str(seeded_path)
    bundle["applied"] = bool(apply)
    return bundle


def self_test():
    failures = []
    try:
        skills = [
            {"name": "alpha-skill", "description": "unique zebra routing tokens xyzzy", "tokens": ["unique", "zebra", "routing", "tokens", "xyzzy"]},
            {"name": "beta-skill", "description": "common overlap words routing", "tokens": ["common", "overlap", "words", "routing"]},
            {"name": "gamma-skill", "description": "unrelated cooking pasta recipe", "tokens": ["unrelated", "cooking", "pasta", "recipe"]},
        ]
        bundle = seed_state(skills, existing={}, force=True)
        st = bundle["skills"]
        assert len(st) == 3, len(st)
        for nm, e in st.items():
            r = e["self_rank"]
            assert abs(e["alpha"] - (1.0 + 1.0 / r)) < 1e-12
            assert abs(e["beta"] - 1.0) < 1e-12
            assert 1 <= r <= 3
        # alpha-skill should self-rank near 1
        assert st["alpha-skill"]["self_rank"] == 1, st["alpha-skill"]
        # preserve observed
        existing = {"alpha-skill": {"alpha": 4.0, "beta": 2.0}}
        b2 = seed_state(skills, existing=existing, force=False)
        assert abs(b2["skills"]["alpha-skill"]["alpha"] - 4.0) < 1e-12
        assert b2["skills"]["alpha-skill"]["seeded"] is False
        b3 = seed_state(skills, existing=existing, force=True)
        assert b3["skills"]["alpha-skill"]["seeded"] is True
    except Exception as e:
        failures.append(f"seed: {e}")
    try:
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d / "skill-router-index.json").write_text(json.dumps({
                "skills": [
                    {"name": "s1", "description": "foo bar baz", "tokens": ["foo", "bar", "baz"]},
                    {"name": "s2", "description": "qux quux", "tokens": ["qux", "quux"]},
                ]
            }))
            r = run(cache=d, apply=True, force=True)
            assert (d / "skill-beta-state-seeded.json").exists()
            assert (d / "skill-beta-state.json").exists()
            flat = json.loads((d / "skill-beta-state.json").read_text())
            assert "s1" in flat and "alpha" in flat["s1"]
            # malformed json fallback
            (d / "skill-beta-state.json").write_text("{not json")
            r2 = run(cache=d, apply=False, force=False)
            assert r2["n_skills"] == 2
            # empty index
            (d / "skill-router-index.json").write_text("{}")
            r3 = run(cache=d)
            assert r3["n_skills"] == 0
            # empty string query tokens still ok
            assert seed_state([{"name": "x", "description": "", "tokens": []}])["n_skills"] == 1
    except Exception as e:
        failures.append(f"io: {e}")
    return {"self_test": "PASS" if not failures else "FAIL", "n_failures": len(failures), "failures": failures}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--apply", action="store_true", help="merge into skill-beta-state.json")
    ap.add_argument("--force", action="store_true", help="overwrite observed betas")
    args = ap.parse_args()
    if args.self_test:
        r = self_test()
        print(json.dumps(r, indent=2))
        sys.exit(0 if r["self_test"] == "PASS" else 1)
    try:
        print(json.dumps(run(apply=args.apply, force=args.force), indent=2))
    except Exception:
        print(json.dumps({"error": "shadow_path_failed"}))
        sys.exit(0)


if __name__ == "__main__":
    main()
