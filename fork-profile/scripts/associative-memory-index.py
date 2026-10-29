#!/usr/bin/env python3
"""SAM-style associative memory index (Raaijmakers & Shiffrin 1981).

Builds a TF-IDF bigram index over lifecycle.db fact_text fields plus skill
descriptions. Retrieval score = tfidf_dot(query, doc) * strength(block_id).

Stdlib only. Atomic JSON via tmp + os.replace. WAL + timeout on sqlite.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import math
import os
import re
import sqlite3
import sys
import tempfile
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

_hermes_base = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_hermes_profile = os.environ.get("HERMES_PROFILE", "")
_hermes_root = (
    (_hermes_base / "profiles" / _hermes_profile)
    if _hermes_profile and "profiles" not in str(_hermes_base)
    else _hermes_base
)

_canonical_lifecycle = Path.home() / ".hermes" / "memory-facts" / "lifecycle.db"
LIFECYCLE_DB = (
    _canonical_lifecycle
    if _canonical_lifecycle.exists()
    else (_hermes_base / "memory-facts" / "lifecycle.db")
)
INDEX_PATH = _hermes_root / "memory-facts" / "assoc-index.json"
SKILLS_DIR = _hermes_root / "skills"
TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall((text or "").lower())


def bigrams(text: str) -> list[str]:
    toks = _tokenize(text)
    if len(toks) < 2:
        return list(toks)
    return [toks[i] + " " + toks[i + 1] for i in range(len(toks) - 1)]


def _connect(db_path: Path):
    if not db_path.exists():
        return None
    conn = sqlite3.connect(str(db_path), timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _table_columns(conn, table: str) -> list[str]:
    try:
        return [r[1] for r in conn.execute("PRAGMA table_info(" + table + ")")]
    except Exception:
        return []


def _id_column(cols: list[str]):
    for name in ("block_id", "memory_id"):
        if name in cols:
            return name
    return None


def _load_facts(db_path: Path) -> list[tuple[str, str]]:
    """Return (block_id, text) pairs. Empty if DB empty or no fact_text column."""
    conn = _connect(db_path)
    if conn is None:
        print("WARNING: lifecycle.db missing; skipping fact text index", file=sys.stderr)
        return []
    try:
        cols = _table_columns(conn, "fact_lifecycle")
        if not cols:
            print("WARNING: fact_lifecycle missing; skipping fact text index", file=sys.stderr)
            return []
        if "fact_text" not in cols:
            print(
                "WARNING: fact_lifecycle has no fact_text column; indexing skills only",
                file=sys.stderr,
            )
            return []
        id_col = _id_column(cols)
        if id_col is None:
            sql = "SELECT rowid, fact_text FROM fact_lifecycle"
        else:
            sql = "SELECT " + id_col + ", fact_text FROM fact_lifecycle"
        rows = conn.execute(sql).fetchall()
        out: list[tuple[str, str]] = []
        for bid, text in rows:
            text = (text or "").strip()
            if not text:
                continue
            out.append((str(bid), text))
        if not out:
            print("WARNING: lifecycle.db fact_lifecycle is empty", file=sys.stderr)
        return out
    except Exception as exc:
        print("WARNING: fact indexing failed: " + str(exc), file=sys.stderr)
        return []
    finally:
        conn.close()


def _parse_skill_description(path: Path) -> str:
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    desc = ""
    if raw.startswith("---"):
        parts = raw.split("---", 2)
        if len(parts) >= 3:
            for line in parts[1].splitlines():
                stripped = line.strip()
                if stripped.lower().startswith("description:"):
                    desc = stripped.split(":", 1)[1].strip().strip('"').strip("'")
                    break
    return (path.parent.name + " " + desc).strip()


def _load_skills(skills_dir: Path) -> list[tuple[str, str]]:
    if not skills_dir.is_dir():
        return []
    out: list[tuple[str, str]] = []
    for md in skills_dir.rglob("SKILL.md"):
        text = _parse_skill_description(md)
        if not text:
            continue
        out.append(("skill:" + md.parent.name, text))
    return out


def _tfidf_index(docs: list[tuple[str, str]]) -> dict:
    """Build {bigram: {block_id: tfidf_weight}}."""
    tf: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    df: dict[str, int] = defaultdict(int)
    for bid, text in docs:
        grams = bigrams(text)
        if not grams:
            continue
        local: dict[str, float] = defaultdict(float)
        for gram in grams:
            local[gram] += 1.0
        n = float(len(grams))
        for gram, count in local.items():
            tf[gram][bid] = count / n
        for gram in local:
            df[gram] += 1
    n_docs = max(len(docs), 1)
    index: dict[str, dict[str, float]] = {}
    for gram, posts in tf.items():
        idf = math.log((n_docs + 1.0) / (df[gram] + 1.0)) + 1.0
        index[gram] = {bid: round(weight * idf, 8) for bid, weight in posts.items()}
    return index


def _atomic_write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(".lock")
    with open(lock_path, "w") as lock_f:
        fcntl.flock(lock_f, fcntl.LOCK_EX)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(obj, indent=2), encoding="utf-8")
        os.replace(str(tmp), str(path))


class AssociativeMemoryIndex:
    """TF-IDF bigram index with SAM strength weighting."""

    def __init__(self, db_path=None, index_path=None, skills_dir=None):
        self.db_path = Path(db_path) if db_path else LIFECYCLE_DB
        self.index_path = Path(index_path) if index_path else INDEX_PATH
        self.skills_dir = Path(skills_dir) if skills_dir else SKILLS_DIR
        self.index: dict = {}
        self._load()

    def _load(self) -> None:
        if not self.index_path.exists():
            self.index = {}
            return
        try:
            obj = json.loads(self.index_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            self.index = {}
            return
        if isinstance(obj, dict) and isinstance(obj.get("index"), dict):
            self.index = obj["index"]
        elif isinstance(obj, dict):
            self.index = obj
        else:
            self.index = {}

    def rebuild(self) -> dict:
        facts = _load_facts(self.db_path)
        skills = _load_skills(self.skills_dir)
        docs = facts + skills
        self.index = _tfidf_index(docs)
        payload = {
            "built_at": datetime.now(timezone.utc).isoformat(),
            "n_docs": len(docs),
            "n_facts": len(facts),
            "n_skills": len(skills),
            "n_bigrams": len(self.index),
            "index": self.index,
        }
        _atomic_write(self.index_path, payload)
        return {
            "n_docs": len(docs),
            "n_facts": len(facts),
            "n_skills": len(skills),
            "n_bigrams": len(self.index),
        }

    def strength_weight(self, block_id: str) -> float:
        conn = _connect(self.db_path)
        if conn is None:
            return 1.0
        try:
            cols = _table_columns(conn, "fact_lifecycle")
            if "strength" not in cols:
                return 1.0
            id_col = _id_column(cols)
            if id_col is None:
                return 1.0
            row = conn.execute(
                "SELECT strength FROM fact_lifecycle WHERE " + id_col + " = ? LIMIT 1",
                (block_id,),
            ).fetchone()
            if not row or row[0] is None:
                return 1.0
            try:
                strength = float(row[0])
            except (TypeError, ValueError):
                return 1.0
            if not math.isfinite(strength) or strength <= 0.0:
                return 1.0
            return strength
        except Exception:
            return 1.0
        finally:
            conn.close()

    def retrieve(self, query: str, top_k: int = 10) -> list[tuple[str, float]]:
        if not query or not self.index:
            return []
        qgrams = bigrams(query)
        if not qgrams:
            return []
        qtf: dict[str, float] = defaultdict(float)
        for gram in qgrams:
            qtf[gram] += 1.0
        scores: dict[str, float] = defaultdict(float)
        for gram, q_weight in qtf.items():
            posts = self.index.get(gram) or {}
            for bid, weight in posts.items():
                scores[bid] += q_weight * float(weight)
        ranked = [
            (bid, tfidf_score * self.strength_weight(bid))
            for bid, tfidf_score in scores.items()
        ]
        ranked.sort(key=lambda item: item[1], reverse=True)
        return ranked[: max(0, int(top_k))]


def retrieve(query: str, top_k: int = 10) -> list[tuple[str, float]]:
    return AssociativeMemoryIndex().retrieve(query, top_k=top_k)


def strength_weight(block_id: str) -> float:
    return AssociativeMemoryIndex().strength_weight(block_id)


def rebuild() -> dict:
    return AssociativeMemoryIndex().rebuild()


def _self_test() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="ami-"))
    idx_path = tmp / ("assoc_" + uuid.uuid4().hex + ".json")
    ami = AssociativeMemoryIndex(
        db_path=tmp / "missing.db",
        index_path=idx_path,
        skills_dir=tmp / "skills",
    )
    docs = [
        ("b1", "unique zebra astronomy catalog of southern sky objects"),
        ("b2", "ordinary grocery list milk eggs bread"),
        ("b3", "unrelated kubernetes pod restart backoff"),
    ]
    ami.index = _tfidf_index(docs)
    _atomic_write(idx_path, {"index": ami.index})
    hits = ami.retrieve("unique zebra astronomy catalog", top_k=3)
    assert hits, "expected retrieval hits"
    assert hits[0][0] == "b1", hits
    assert ami.retrieve("", top_k=10) == []
    assert ami.strength_weight("b1") == 1.0
    assert _load_facts(tmp / "missing.db") == []
    print(json.dumps({"ok": True, "top": hits[0][0], "score": hits[0][1]}))
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="SAM associative memory index")
    parser.add_argument("--rebuild", action="store_true")
    parser.add_argument("--query", default=None)
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        return _self_test()
    ami = AssociativeMemoryIndex()
    if args.rebuild:
        stats = ami.rebuild()
        print(json.dumps({"rebuild": True, **stats}))
        if args.query is None:
            return 0
    if args.query is not None:
        hits = ami.retrieve(args.query, top_k=args.top_k)
        print(json.dumps([{"block_id": bid, "score": score} for bid, score in hits], indent=2))
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
