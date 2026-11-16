#!/usr/bin/env python3
"""dolt-merge.py — PK three-way merge for JSON arrays (Dolt-inspired, no Dolt).

Merge algorithm (row PK, typically job_id / id):
  * PK only on one side and not in base: auto-include that row
  * In base, absent on one side, other side unchanged: delete
  * In base, absent on one side, other side modified: conflict (modify/delete)
  * Present in all three: field-by-field merge
      ours == theirs -> keep
      one side == base -> take the other
      both changed from base -> conflict
  * JSON/dict column values: recurse one level (merge sub-keys)

Conflicts are never silent last-write-wins. resolve_conflicts() applies
ours|theirs. CLI merge writes atomically (tmp + os.replace, sibling flock).

Usage:
  python3 dolt-merge.py merge --base BASE.json --ours OURS.json --theirs THEIRS.json --pk job_id --out MERGED.json
  python3 dolt-merge.py diff --old OLD.json --new NEW.json --pk job_id
  python3 dolt-merge.py --self-test
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import sys
import tempfile
import uuid
from pathlib import Path

_UNSET = object()


def _profile_root() -> Path:
    base = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
    profile = os.environ.get("HERMES_PROFILE", "")
    if profile and "profiles" not in str(base):
        return base / "profiles" / profile
    return base


def _json_copy(obj):
    return json.loads(json.dumps(obj, default=str))


def _as_mapping(val):
    if isinstance(val, dict):
        return val
    if isinstance(val, str):
        s = val.strip()
        if s.startswith("{") and s.endswith("}"):
            try:
                parsed = json.loads(s)
            except json.JSONDecodeError:
                return None
            if isinstance(parsed, dict):
                return parsed
    return None


def _conflict(pk_val, field, base_val, ours_val, theirs_val) -> dict:
    return {
        "pk_val": pk_val,
        "field": field,
        "base_val": base_val,
        "ours_val": ours_val,
        "theirs_val": theirs_val,
    }


def _index_rows(rows, pk: str) -> dict:
    out = {}
    if not rows:
        return out
    for row in rows:
        if not isinstance(row, dict):
            continue
        key = row.get(pk)
        if key is None:
            continue
        out[key] = row
    return out


def _pk_order(rows, pk: str) -> list:
    order = []
    seen = set()
    if not rows:
        return order
    for row in rows:
        if not isinstance(row, dict):
            continue
        key = row.get(pk)
        if key is None or key in seen:
            continue
        seen.add(key)
        order.append(key)
    return order


def _merge_dict_one_level(pk_val, field, base_d, ours_d, theirs_d, conflicts, orig_ours, orig_theirs, strategy):
    keys = set(base_d) | set(ours_d) | set(theirs_d)
    out = {}
    for k in keys:
        bv = base_d[k] if k in base_d else _UNSET
        ov = ours_d[k] if k in ours_d else _UNSET
        tv = theirs_d[k] if k in theirs_d else _UNSET
        nested = f"{field}.{k}"
        if ov is _UNSET and tv is _UNSET:
            continue
        if ov is _UNSET:
            if bv is _UNSET:
                out[k] = tv
                continue
            if tv == bv:
                continue
            chosen = tv if strategy == "theirs" else None
            conflicts.append(_conflict(pk_val, nested, None if bv is _UNSET else bv, None, tv))
            if strategy == "theirs":
                out[k] = chosen
            continue
        if tv is _UNSET:
            if bv is _UNSET:
                out[k] = ov
                continue
            if ov == bv:
                continue
            chosen = ov if strategy != "theirs" else None
            conflicts.append(_conflict(pk_val, nested, None if bv is _UNSET else bv, ov, None))
            if strategy != "theirs":
                out[k] = chosen
            continue
        if ov == tv:
            out[k] = ov
            continue
        if bv is not _UNSET and ov == bv:
            out[k] = tv
            continue
        if bv is not _UNSET and tv == bv:
            out[k] = ov
            continue
        conflicts.append(
            _conflict(pk_val, nested, None if bv is _UNSET else bv, ov, tv)
        )
        out[k] = tv if strategy == "theirs" else ov
    if isinstance(orig_ours, str) and isinstance(orig_theirs, str):
        return json.dumps(out)
    return out


def _merge_field(pk_val, field, base_val, ours_val, theirs_val, conflicts, strategy, depth=0):
    if ours_val == theirs_val:
        return ours_val
    if ours_val == base_val:
        return theirs_val
    if theirs_val == base_val:
        return ours_val
    if depth == 0:
        o_map = _as_mapping(ours_val)
        t_map = _as_mapping(theirs_val)
        if o_map is not None and t_map is not None:
            b_map = _as_mapping(base_val) or {}
            return _merge_dict_one_level(
                pk_val, field, b_map, o_map, t_map, conflicts, ours_val, theirs_val, strategy
            )
    conflicts.append(_conflict(pk_val, field, base_val, ours_val, theirs_val))
    return theirs_val if strategy == "theirs" else ours_val


def _merge_present_row(pk_val, pk, base_row, ours_row, theirs_row, conflicts, strategy) -> dict:
    keys = set()
    for row in (base_row, ours_row, theirs_row):
        if isinstance(row, dict):
            keys.update(row.keys())
    merged = {}
    for field in keys:
        if field == pk:
            merged[pk] = pk_val
            continue
        bv = base_row.get(field) if isinstance(base_row, dict) else None
        ov = ours_row.get(field) if isinstance(ours_row, dict) else None
        tv = theirs_row.get(field) if isinstance(theirs_row, dict) else None
        in_b = isinstance(base_row, dict) and field in base_row
        in_o = isinstance(ours_row, dict) and field in ours_row
        in_t = isinstance(theirs_row, dict) and field in theirs_row
        if in_o and not in_t:
            if in_b and ours_row.get(field) == base_row.get(field):
                continue
            if in_b:
                conflicts.append(_conflict(pk_val, field, bv, ov, None))
                if strategy != "theirs":
                    merged[field] = ov
                continue
            merged[field] = ov
            continue
        if in_t and not in_o:
            if in_b and theirs_row.get(field) == base_row.get(field):
                continue
            if in_b:
                conflicts.append(_conflict(pk_val, field, bv, None, tv))
                if strategy == "theirs":
                    merged[field] = tv
                continue
            merged[field] = tv
            continue
        if not in_o and not in_t:
            continue
        merged[field] = _merge_field(
            pk_val, field, bv if in_b else None, ov, tv, conflicts, strategy
        )
    if pk not in merged:
        merged[pk] = pk_val
    return merged


def merge_rows(base, ours, theirs, pk="job_id", strategy=None):
    """Three-way merge lists of dicts on `pk`.

    Returns (merged_list, conflicts_list). conflict shape:
      {pk_val, field, base_val, ours_val, theirs_val}
    """
    base = base or []
    ours = ours or []
    theirs = theirs or []
    if strategy is not None and strategy not in ("ours", "theirs"):
        raise ValueError("strategy must be 'ours', 'theirs', or None")
    b_idx = _index_rows(base, pk)
    o_idx = _index_rows(ours, pk)
    t_idx = _index_rows(theirs, pk)
    conflicts = []
    merged_idx = {}

    all_pks = []
    seen = set()
    for key in _pk_order(base, pk) + _pk_order(ours, pk) + _pk_order(theirs, pk):
        if key in seen:
            continue
        seen.add(key)
        all_pks.append(key)

    for key in all_pks:
        in_b = key in b_idx
        in_o = key in o_idx
        in_t = key in t_idx
        b_row = b_idx.get(key)
        o_row = o_idx.get(key)
        t_row = t_idx.get(key)

        if in_o and not in_t and not in_b:
            merged_idx[key] = _json_copy(o_row)
            continue
        if in_t and not in_o and not in_b:
            merged_idx[key] = _json_copy(t_row)
            continue
        if in_b and not in_o and not in_t:
            continue
        if in_o and in_t and not in_b:
            if o_row == t_row:
                merged_idx[key] = _json_copy(o_row)
            else:
                merged_idx[key] = _merge_present_row(
                    key, pk, {}, o_row, t_row, conflicts, strategy
                )
            continue
        if in_b and in_o and not in_t:
            if o_row == b_row:
                continue
            conflicts.append(_conflict(key, None, b_row, o_row, None))
            if strategy != "theirs":
                merged_idx[key] = _json_copy(o_row)
            continue
        if in_b and in_t and not in_o:
            if t_row == b_row:
                continue
            conflicts.append(_conflict(key, None, b_row, None, t_row))
            if strategy == "theirs":
                merged_idx[key] = _json_copy(t_row)
            continue
        merged_idx[key] = _merge_present_row(
            key, pk, b_row, o_row, t_row, conflicts, strategy
        )

    merged_list = [merged_idx[k] for k in all_pks if k in merged_idx]
    return merged_list, conflicts


def resolve_conflicts(conflicts, strategy="ours"):
    """Apply ours|theirs to a conflicts list. Returns resolved list with resolved_val."""
    if strategy not in ("ours", "theirs"):
        raise ValueError("strategy must be 'ours' or 'theirs'")
    key = "ours_val" if strategy == "ours" else "theirs_val"
    out = []
    for c in conflicts or []:
        rec = dict(c)
        rec["resolved_val"] = c.get(key)
        rec["strategy"] = strategy
        out.append(rec)
    return out


def diff_rows(old, new, pk="job_id") -> dict:
    old = old or []
    new = new or []
    o_idx = _index_rows(old, pk)
    n_idx = _index_rows(new, pk)
    added = []
    deleted = []
    modified = []
    for key in _pk_order(new, pk):
        if key not in o_idx:
            added.append(_json_copy(n_idx[key]))
        elif n_idx[key] != o_idx[key]:
            fields = {}
            o_row, n_row = o_idx[key], n_idx[key]
            keys = set(o_row) | set(n_row)
            for f in keys:
                ov = o_row.get(f, _UNSET)
                nv = n_row.get(f, _UNSET)
                if ov != nv:
                    fields[f] = [
                        None if ov is _UNSET else ov,
                        None if nv is _UNSET else nv,
                    ]
            modified.append({"pk_val": key, "fields": fields})
    for key in _pk_order(old, pk):
        if key not in n_idx:
            deleted.append(_json_copy(o_idx[key]))
    return {"added": added, "deleted": deleted, "modified": modified}


def _extract_rows(data):
    if isinstance(data, list):
        return data, "list", None, data
    if isinstance(data, dict):
        for key in ("jobs", "items", "rows", "data"):
            if isinstance(data.get(key), list):
                return data[key], "dict", key, data
        return [data], "single", None, data
    return [], "list", None, []


def _load_json(path: Path):
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        return []
    return json.loads(text)


def _rebuild(kind, wrapper, key, rows):
    if kind == "list":
        return rows
    if kind == "dict" and key is not None and isinstance(wrapper, dict):
        out = dict(wrapper)
        out[key] = rows
        return out
    if kind == "single":
        return rows[0] if rows else {}
    return rows


def _atomic_write_json(dest: Path, data) -> None:
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    lock_path = dest.with_suffix(".lock")
    tmp = dest.with_suffix(".tmp")
    payload = json.dumps(data, indent=2, default=str) + "\n"
    with open(lock_path, "w", encoding="utf-8") as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        tmp.write_text(payload, encoding="utf-8")
        os.replace(str(tmp), str(dest))


def cmd_merge(args) -> int:
    base_path = Path(args.base)
    ours_path = Path(args.ours)
    theirs_path = Path(args.theirs)
    for p in (base_path, ours_path, theirs_path):
        if not p.exists():
            print(f"ERROR: missing file: {p}", file=sys.stderr)
            return 2
    try:
        base_raw = _load_json(base_path)
        ours_raw = _load_json(ours_path)
        theirs_raw = _load_json(theirs_path)
    except json.JSONDecodeError as e:
        print(f"ERROR: malformed JSON: {e}", file=sys.stderr)
        return 2
    base_rows, _, _, _ = _extract_rows(base_raw)
    ours_rows, ours_kind, ours_key, ours_wrap = _extract_rows(ours_raw)
    theirs_rows, _, _, _ = _extract_rows(theirs_raw)
    merged, conflicts = merge_rows(
        base_rows, ours_rows, theirs_rows, pk=args.pk, strategy=args.strategy
    )
    out_obj = _rebuild(ours_kind, ours_wrap, ours_key, merged)
    _atomic_write_json(Path(args.out), out_obj)
    rec = {
        "merged_rows": len(merged),
        "conflicts": conflicts,
        "n_conflicts": len(conflicts),
        "out": str(args.out),
        "pk": args.pk,
        "strategy": args.strategy,
    }
    print(json.dumps(rec, indent=2, default=str))
    if conflicts and args.strategy is None:
        return 1
    return 0


def cmd_diff(args) -> int:
    old_path = Path(args.old)
    new_path = Path(args.new)
    for p in (old_path, new_path):
        if not p.exists():
            print(f"ERROR: missing file: {p}", file=sys.stderr)
            return 2
    try:
        old_raw = _load_json(old_path)
        new_raw = _load_json(new_path)
    except json.JSONDecodeError as e:
        print(f"ERROR: malformed JSON: {e}", file=sys.stderr)
        return 2
    old_rows, _, _, _ = _extract_rows(old_raw)
    new_rows, _, _, _ = _extract_rows(new_raw)
    rec = diff_rows(old_rows, new_rows, pk=args.pk)
    rec["pk"] = args.pk
    rec["n_added"] = len(rec["added"])
    rec["n_deleted"] = len(rec["deleted"])
    rec["n_modified"] = len(rec["modified"])
    print(json.dumps(rec, indent=2, default=str))
    return 0


def self_test() -> int:
    # Fast-forward: only theirs changed.
    base = [{"job_id": "a", "x": 1}, {"job_id": "b", "x": 2}]
    ours = [{"job_id": "a", "x": 1}, {"job_id": "b", "x": 2}]
    theirs = [{"job_id": "a", "x": 1}, {"job_id": "b", "x": 3}, {"job_id": "c", "x": 4}]
    merged, conflicts = merge_rows(base, ours, theirs)
    assert conflicts == []
    assert {r["job_id"]: r["x"] for r in merged} == {"a": 1, "b": 3, "c": 4}

    # Fast-forward the other way: only ours changed.
    merged, conflicts = merge_rows(base, theirs, ours)
    assert conflicts == []
    assert {r["job_id"]: r["x"] for r in merged} == {"a": 1, "b": 3, "c": 4}

    # Clean three-way: disjoint field edits.
    base = [{"job_id": "a", "x": 1, "y": 1}]
    ours = [{"job_id": "a", "x": 2, "y": 1}]
    theirs = [{"job_id": "a", "x": 1, "y": 3}]
    merged, conflicts = merge_rows(base, ours, theirs)
    assert conflicts == []
    assert merged == [{"job_id": "a", "x": 2, "y": 3}]

    # Scalar conflict.
    base = [{"job_id": "a", "x": 1}]
    ours = [{"job_id": "a", "x": 2}]
    theirs = [{"job_id": "a", "x": 3}]
    merged, conflicts = merge_rows(base, ours, theirs)
    assert len(conflicts) == 1
    assert conflicts[0]["field"] == "x"
    assert conflicts[0]["base_val"] == 1
    assert conflicts[0]["ours_val"] == 2
    assert conflicts[0]["theirs_val"] == 3
    assert merged[0]["x"] == 2  # unresolved keeps ours
    resolved = resolve_conflicts(conflicts, "ours")
    assert resolved[0]["resolved_val"] == 2
    resolved = resolve_conflicts(conflicts, "theirs")
    assert resolved[0]["resolved_val"] == 3
    merged_t, conflicts_t = merge_rows(base, ours, theirs, strategy="theirs")
    assert conflicts_t and merged_t[0]["x"] == 3

    # JSON/dict column merge (one level).
    base = [{"job_id": "a", "meta": {"p": 1, "q": 2}}]
    ours = [{"job_id": "a", "meta": {"p": 1, "q": 9}}]
    theirs = [{"job_id": "a", "meta": {"p": 7, "q": 2}}]
    merged, conflicts = merge_rows(base, ours, theirs)
    assert conflicts == []
    assert merged[0]["meta"] == {"p": 7, "q": 9}

    # JSON column conflict on a sub-key.
    ours = [{"job_id": "a", "meta": {"p": 3, "q": 2}}]
    theirs = [{"job_id": "a", "meta": {"p": 4, "q": 2}}]
    merged, conflicts = merge_rows(base, ours, theirs)
    assert any(c["field"] == "meta.p" for c in conflicts)

    # JSON string column merge.
    base = [{"job_id": "a", "meta": json.dumps({"p": 1, "q": 2})}]
    ours = [{"job_id": "a", "meta": json.dumps({"p": 1, "q": 9})}]
    theirs = [{"job_id": "a", "meta": json.dumps({"p": 7, "q": 2})}]
    merged, conflicts = merge_rows(base, ours, theirs)
    assert conflicts == []
    assert json.loads(merged[0]["meta"]) == {"p": 7, "q": 9}

    # Delete (in base, absent on one side, other unchanged).
    base = [{"job_id": "a", "x": 1}, {"job_id": "b", "x": 2}]
    ours = [{"job_id": "a", "x": 1}]
    theirs = [{"job_id": "a", "x": 1}, {"job_id": "b", "x": 2}]
    merged, conflicts = merge_rows(base, ours, theirs)
    assert conflicts == []
    assert [r["job_id"] for r in merged] == ["a"]

    # Modify/delete conflict.
    base = [{"job_id": "a", "x": 1}]
    ours = []
    theirs = [{"job_id": "a", "x": 2}]
    merged, conflicts = merge_rows(base, ours, theirs)
    assert len(conflicts) == 1
    assert conflicts[0]["pk_val"] == "a"
    assert conflicts[0]["field"] is None

    # Empty inputs.
    merged, conflicts = merge_rows([], [], [])
    assert merged == [] and conflicts == []
    merged, conflicts = merge_rows(None, None, None)
    assert merged == [] and conflicts == []

    # Add on both sides, same PK, different payload -> field conflicts.
    merged, conflicts = merge_rows(
        [],
        [{"job_id": "z", "x": 1}],
        [{"job_id": "z", "x": 2}],
    )
    assert any(c["field"] == "x" for c in conflicts)

    # diff
    d = diff_rows(
        [{"job_id": "a", "x": 1}, {"job_id": "b", "x": 2}],
        [{"job_id": "a", "x": 9}, {"job_id": "c", "x": 3}],
    )
    assert len(d["added"]) == 1 and d["added"][0]["job_id"] == "c"
    assert len(d["deleted"]) == 1 and d["deleted"][0]["job_id"] == "b"
    assert len(d["modified"]) == 1 and d["modified"][0]["pk_val"] == "a"

    # CLI round-trip on wrapped jobs.json shape.
    td = Path(tempfile.mkdtemp(prefix="dolt-merge-"))
    try:
        base_p = td / "base.json"
        ours_p = td / "ours.json"
        theirs_p = td / "theirs.json"
        out_p = td / "merged.json"
        base_p.write_text(json.dumps({"jobs": [{"id": "j1", "n": 1}], "updated_at": "t0"}))
        ours_p.write_text(json.dumps({"jobs": [{"id": "j1", "n": 2}], "updated_at": "t1"}))
        theirs_p.write_text(json.dumps({"jobs": [{"id": "j1", "n": 1}, {"id": "j2", "n": 3}], "updated_at": "t2"}))
        ns = {
            "base": str(base_p),
            "ours": str(ours_p),
            "theirs": str(theirs_p),
            "out": str(out_p),
            "pk": "id",
            "strategy": None,
        }
        rc = cmd_merge(argparse.Namespace(**ns))
        assert rc == 0
        got = json.loads(out_p.read_text())
        assert "jobs" in got
        ids = {j["id"]: j["n"] for j in got["jobs"]}
        assert ids == {"j1": 2, "j2": 3}
        old_p = td / "old.json"
        new_p = td / "new.json"
        old_p.write_text(json.dumps([{"job_id": "a", "x": 1}]))
        new_p.write_text(json.dumps([{"job_id": "a", "x": 1}, {"job_id": "b", "x": 2}]))
        rc = cmd_diff(argparse.Namespace(old=str(old_p), new=str(new_p), pk="job_id"))
        assert rc == 0
    finally:
        for p in td.glob("*"):
            try:
                p.unlink()
            except OSError:
                pass
        try:
            td.rmdir()
        except OSError:
            pass

    # uuid isolation: no production path writes
    _ = uuid.uuid4().hex
    print("PASS dolt-merge self-test")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--self-test", action="store_true")
    sub = ap.add_subparsers(dest="cmd")

    p_merge = sub.add_parser("merge", help="PK three-way merge")
    p_merge.add_argument("--base", required=True)
    p_merge.add_argument("--ours", required=True)
    p_merge.add_argument("--theirs", required=True)
    p_merge.add_argument("--pk", default="job_id")
    p_merge.add_argument("--out", required=True)
    p_merge.add_argument("--strategy", choices=("ours", "theirs"), default=None)

    p_diff = sub.add_parser("diff", help="PK diff of two JSON arrays")
    p_diff.add_argument("--old", required=True)
    p_diff.add_argument("--new", required=True)
    p_diff.add_argument("--pk", default="job_id")

    args = ap.parse_args()
    if args.self_test:
        return self_test()
    if args.cmd == "merge":
        return cmd_merge(args)
    if args.cmd == "diff":
        return cmd_diff(args)
    ap.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
