#!/usr/bin/env python3
"""Data collection hook: probe whether real embedding vectors exist.

Checks:
  (1) graphiti.db entities table with non-null embedding column
  (2) lifecycle.db any table with an embedding column
  (3) .npy / .faiss files under ~/.hermes (skips venv/site-packages noise)

Logs result to cache/ann-embeddings-probe.json.
Recommendation: USE_REAL if total > 100, SYNTHETIC_OK if total == 0, PARTIAL otherwise.
Synthetic/in-memory fallback throughout. Stdlib only.
"""

from __future__ import annotations

import argparse
import ast as _ast
import json
import os
import sqlite3
import struct
from datetime import datetime, timezone, UTC
from pathlib import Path
from typing import Any

HERMES_HOME = Path(__file__).resolve().parents[3]
_env_home = os.environ.get("HERMES_HOME", "").strip()
if _env_home:
    _eh = Path(_env_home)
    _hh = str(_eh)
    if "profiles" in _hh and (_hh.endswith("fork") or _hh.endswith("fork/")):
        HERMES_HOME = _eh.parent.parent
    else:
        HERMES_HOME = _eh
PROFILE_ROOT = HERMES_HOME / "profiles" / "fork"
DB_PATH = PROFILE_ROOT / "cache" / "lifecycle.db"
REPORT_PATH = PROFILE_ROOT / "cache" / "ann-embeddings-probe.json"

_SKIP_DIRS = {
    "venv",
    ".venv",
    "site-packages",
    "dist-packages",
    "node_modules",
    "__pycache__",
    ".git",
    "uv",
    "archive-v0",
    "integrations.disabled",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
}

_SAFE_IDENT = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_")


def _atomic_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    os.replace(tmp, path)


def _ident_ok(name: str) -> bool:
    return bool(name) and all(c in _SAFE_IDENT for c in name)


def _open_ro(path: Path) -> sqlite3.Connection | None:
    try:
        if not path.exists():
            return None
        return sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    except Exception:
        return None


def _count_embedding_col(con: sqlite3.Connection) -> tuple[bool, int]:
    """Return (has_embedding_col, non_null_count) across all tables."""
    total = 0
    has = False
    try:
        tables = con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    except Exception:
        return False, 0
    for (name,) in tables:
        if not _ident_ok(name):
            continue
        try:
            cols = con.execute(f'PRAGMA table_info("{name}")').fetchall()
        except Exception:
            continue
        emb_cols = [c[1] for c in cols if str(c[1]).lower() == "embedding"]
        if not emb_cols:
            continue
        has = True
        col = emb_cols[0]
        if not _ident_ok(col):
            continue
        try:
            n = con.execute(
                f'SELECT COUNT(*) FROM "{name}" WHERE "{col}" IS NOT NULL'
            ).fetchone()[0]
            total += int(n or 0)
        except Exception:
            continue
    return has, total


def _probe_graphiti() -> tuple[bool, int]:
    candidates = [
        HERMES_HOME / "graphiti.db",
        PROFILE_ROOT / "cache" / "graphiti.db",
        HERMES_HOME / "cache" / "graphiti.db",
        PROFILE_ROOT / "graphiti.db",
    ]
    for path in candidates:
        con = _open_ro(path)
        if con is None:
            continue
        try:
            tables = {
                r[0]
                for r in con.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            if "entities" not in tables:
                # still count any embedding col
                has, n = _count_embedding_col(con)
                if has:
                    return True, n
                continue
            cols = con.execute('PRAGMA table_info("entities")').fetchall()
            emb = [c[1] for c in cols if str(c[1]).lower() == "embedding"]
            if not emb:
                continue
            col = emb[0]
            if not _ident_ok(col):
                continue
            n = con.execute(
                f'SELECT COUNT(*) FROM "entities" WHERE "{col}" IS NOT NULL'
            ).fetchone()[0]
            return True, int(n or 0)
        except Exception:
            continue
        finally:
            try:
                con.close()
            except Exception:
                pass
    return False, 0


def _probe_lifecycle() -> tuple[bool, int]:
    con = _open_ro(DB_PATH)
    if con is None:
        return False, 0
    try:
        return _count_embedding_col(con)
    except Exception:
        return False, 0
    finally:
        try:
            con.close()
        except Exception:
            pass


def _npy_row_count(path: Path) -> int:
    try:
        with path.open("rb") as f:
            magic = f.read(6)
            if magic != b"\x93NUMPY":
                return 0
            ver = f.read(2)
            if not ver:
                return 0
            if ver[0] == 1:
                hlen = struct.unpack("<H", f.read(2))[0]
            else:
                hlen = struct.unpack("<I", f.read(4))[0]
            header = f.read(hlen).decode("latin1")
            meta = _ast.literal_eval(header.strip())
            shape = meta.get("shape") or ()
            if not shape:
                return 0
            return int(shape[0])
    except Exception:
        return 0


def _walk_npy_faiss(root: Path, limit: int = 200) -> list[str]:
    found: list[str] = []
    if not root.exists():
        return found
    try:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
            parts = set(Path(dirpath).parts)
            if parts & _SKIP_DIRS:
                dirnames[:] = []
                continue
            if "site-packages" in parts:
                dirnames[:] = []
                continue
            for fn in filenames:
                if fn.endswith(".npy") or fn.endswith(".faiss"):
                    found.append(str(Path(dirpath) / fn))
                    if len(found) >= limit:
                        return found
    except Exception:
        pass
    return found


def _recommend(total: int) -> str:
    if total > 100:
        return "USE_REAL"
    if total == 0:
        return "SYNTHETIC_OK"
    return "PARTIAL"


def run_probe(dry_run: bool = False) -> dict[str, Any]:
    g_has, g_n = _probe_graphiti()
    l_has, l_n = _probe_lifecycle()
    files = _walk_npy_faiss(HERMES_HOME)
    file_n = 0
    for fp in files:
        p = Path(fp)
        if p.suffix == ".npy":
            file_n += _npy_row_count(p)
        else:
            # faiss index present but unreadable without faiss: count as 1 vector marker
            file_n += 1
    total = int(g_n) + int(l_n) + int(file_n)
    result: dict[str, Any] = {
        "ts": datetime.now(UTC).isoformat(),
        "graphiti_has_embeddings": bool(g_has and g_n > 0),
        "lifecycle_has_embeddings": bool(l_has and l_n > 0),
        "npy_faiss_found": files,
        "total_embedding_count": total,
        "recommendation": _recommend(total),
        "graphiti_count": g_n,
        "lifecycle_count": l_n,
        "file_vector_count": file_n,
    }
    if not dry_run:
        try:
            _atomic_json(REPORT_PATH, result)
            result["report_path"] = str(REPORT_PATH)
        except Exception:
            result["report_path"] = None
    return result


def layer1_demo() -> None:
    result = run_probe(dry_run=True)  # do not clobber production report
    assert result["recommendation"] in ("USE_REAL", "SYNTHETIC_OK", "PARTIAL"), result
    assert "ts" in result
    assert isinstance(result["graphiti_has_embeddings"], bool)
    assert isinstance(result["lifecycle_has_embeddings"], bool)
    assert isinstance(result["npy_faiss_found"], list)
    assert isinstance(result["total_embedding_count"], int)
    assert result["total_embedding_count"] >= 0
    print(
        f"[layer1] PASS ann-embeddings-probe rec={result['recommendation']} "
        f"total={result['total_embedding_count']} npy_faiss={len(result['npy_faiss_found'])}"
    )


def main() -> None:
    pa = argparse.ArgumentParser(description="ANN embeddings probe")
    pa.add_argument("--layer1", action="store_true")
    pa.add_argument("--self-test", action="store_true")
    args = pa.parse_args()
    if args.layer1 or args.self_test:
        layer1_demo()
        return
    result = run_probe()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
