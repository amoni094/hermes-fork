#!/usr/bin/env python3
"""Named-variable path-taint propagation over Hermes delegation logs.

Builds a causal DAG by propagating file paths, URLs, IDs, and quoted
identifiers from tool outputs into later tool inputs. Compares edge
count against a 10-gram substring baseline (spike 008b).

Usage:
  python3 appa-path-taint.py --session-log PATH
  python3 appa-path-taint.py --sessions-dir DIR
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict, deque
from pathlib import Path
from typing import Any

MIN_TOKEN_LEN = 6
NGRAM_N = 10
RESULTS_PATH = Path("/tmp/appa-path-taint-results.json")

RE_ABS_PATH = re.compile(r"/[a-zA-Z0-9_./~-]{4,}")
RE_HOME_PATH = re.compile(r"~[/a-zA-Z0-9_.-]+")
RE_URL = re.compile(r'https?://[^\s"\'<>]{8,}')
RE_ARXIV = re.compile(r"\b\d{4}\.\d{4,5}\b")
RE_QUOTED_ID = re.compile(r"""["']([a-zA-Z0-9_-]{8,})["']""")

# Quoted identifiers that are structural JSON/log noise, not data taint tokens.
# Without this blocklist, keys like tool_name, completed, skill_view produce
# false taint edges everywhere they appear in serialised log output.
_QUOTED_ID_BLOCKLIST = frozenset({
    "tool_name", "tool_call", "tool_result", "completed", "assistant",
    "skill_view", "read_file", "write_file", "search_files", "execute_code",
    "web_search", "web_extract", "terminal", "tool_use", "function",
    "arguments", "parameters", "task_index", "task_id", "session_id",
    "run_date", "sweep_date", "generated_at", "optimizations",
})

RE_TOOL_CALL_TAG = re.compile(r"\[TOOL_CALL\]\s*(\S+)")
RE_TOOL_RESULT_TAG = re.compile(r"\[TOOL_RESULT\]")

RE_LIVE = re.compile(
    r"^(?:\d{2}:\d{2}:\d{2}\s+)?(tool|result)\s+\|\s+(.*)$"
)
RE_LIVE_CALL = re.compile(r"^->\s*([A-Za-z0-9_.-]+)(?:\((.*)\))?\s*$")


class ToolCall:
    __slots__ = ("name", "index", "inp", "out")

    def __init__(self, name: str, index: int, inp: str = "", out: str = "") -> None:
        self.name = name or "unknown"
        self.index = index
        self.inp = inp
        self.out = out


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False, default=str)
    except TypeError:
        return str(value)


def extract_taint_tokens(text: str) -> set[str]:
    if not text:
        return set()
    tokens: set[str] = set()
    for rx in (RE_ABS_PATH, RE_HOME_PATH, RE_URL, RE_ARXIV):
        tokens.update(rx.findall(text))
    tokens.update(t for t in RE_QUOTED_ID.findall(text) if t not in _QUOTED_ID_BLOCKLIST)
    tokens = {t for t in tokens if len(t) >= MIN_TOKEN_LEN}
    # Drop prefix-only tokens: keep only maximal tokens (not strict prefixes of another
    # token in the same set). Without this, '/var/home' creates spurious edges to every
    # call that uses '/var/home/rainbow/...' — a common-ancestor false positive that
    # inflates edge counts and contaminates reduction metrics.
    maximal: set[str] = set()
    sorted_toks = sorted(tokens, key=len, reverse=True)
    for t in sorted_toks:
        if not any(longer.startswith(t) and longer != t for longer in maximal):
            maximal.add(t)
    return maximal


def ngrams(text: str, n: int = NGRAM_N) -> set[str]:
    if not text or len(text) < n:
        return set()
    return {text[i : i + n] for i in range(len(text) - n + 1)}


def _json_tool_calls(obj: dict[str, Any]) -> list[tuple[str, str]]:
    """Return (name, input_text) pairs from a JSON log object."""
    found: list[tuple[str, str]] = []
    tcalls = obj.get("tool_calls")
    if isinstance(tcalls, list):
        for tc in tcalls:
            if not isinstance(tc, dict):
                continue
            fn_obj = tc.get("function")
            fn: dict[str, Any] = fn_obj if isinstance(fn_obj, dict) else tc
            name = fn.get("name") or fn.get("tool_name") or tc.get("name") or ""
            args = fn.get("arguments", fn.get("input", fn.get("parameters", "")))
            if name:
                found.append((str(name), _stringify(args)))
    name = obj.get("tool_name") or obj.get("name") or obj.get("tool")
    role = str(obj.get("role") or obj.get("type") or "").lower()
    if name and role not in {"tool", "tool_result", "result"}:
        inp = obj.get("arguments", obj.get("input", obj.get("parameters", obj.get("content", ""))))
        found.append((str(name), _stringify(inp)))
    return found


def _is_tool_event_json(obj: dict[str, Any]) -> bool:
    """True only for JSON lines that look like Hermes/OpenAI tool log events."""
    if obj.get("tool_calls") or obj.get("tool_name") or obj.get("tool_result") is not None:
        return True
    role = str(obj.get("role") or "").lower()
    if role in {"tool", "tool_result", "assistant", "function"}:
        return True
    typ = str(obj.get("type") or "").lower()
    return typ in {"tool_call", "tool_result", "function_call", "tool"}


def _json_is_result(obj: dict[str, Any]) -> bool:
    role = str(obj.get("role") or obj.get("type") or "").lower()
    if role in {"tool", "tool_result", "result"}:
        return True
    if obj.get("tool_result") is not None or obj.get("output") is not None:
        if not obj.get("tool_calls"):
            return True
    return False


def _json_result_text(obj: dict[str, Any]) -> str:
    for key in ("content", "output", "result", "tool_result", "text"):
        if key in obj and obj[key] is not None:
            return _stringify(obj[key])
    return _stringify(obj)


def parse_log_text(text: str, start_index: int = 0) -> list[ToolCall]:
    """Parse one log blob. JSON-per-line first, then bracket tags, then live transcript."""
    calls: list[ToolCall] = []
    idx = start_index
    pending: deque[ToolCall] = deque()
    tag_current: ToolCall | None = None
    tag_in_result = False
    tag_input_parts: list[str] = []
    tag_output_parts: list[str] = []
    used_json = False
    used_tags = False

    def flush_tag() -> None:
        nonlocal tag_current, tag_in_result, tag_input_parts, tag_output_parts, idx
        if tag_current is None:
            return
        tag_current.inp = "\n".join(tag_input_parts)
        tag_current.out = "\n".join(tag_output_parts)
        tag_current.index = idx
        calls.append(tag_current)
        idx += 1
        tag_current = None
        tag_in_result = False
        tag_input_parts = []
        tag_output_parts = []

    def open_call(name: str, inp: str = "") -> ToolCall:
        nonlocal idx
        tc = ToolCall(name, idx, inp=inp)
        pending.append(tc)
        calls.append(tc)
        idx += 1
        return tc

    def attach_result(out: str, hint_name: str = "") -> None:
        tc: ToolCall | None = None
        if hint_name:
            for i, cand in enumerate(pending):
                if cand.name == hint_name:
                    tc = pending[i]
                    del pending[i]
                    break
        if tc is None and pending:
            tc = pending.popleft()
        if tc is None:
            if calls:
                calls[-1].out = (calls[-1].out + "\n" + out).strip() if calls[-1].out else out
            return
        tc.out = (tc.out + "\n" + out).strip() if tc.out else out

    for raw in text.splitlines():
        line = raw.rstrip("\n")
        stripped = line.strip()
        if not stripped:
            continue

        m_call = RE_TOOL_CALL_TAG.search(line)
        if m_call:
            used_tags = True
            flush_tag()
            rest = line[m_call.end() :].strip()
            tag_current = ToolCall(m_call.group(1), -1)
            tag_in_result = False
            tag_input_parts = [rest] if rest else []
            tag_output_parts = []
            continue
        if RE_TOOL_RESULT_TAG.search(line):
            used_tags = True
            if tag_current is None:
                tag_current = ToolCall("unknown", -1)
            tag_in_result = True
            after = RE_TOOL_RESULT_TAG.split(line, maxsplit=1)[-1].strip()
            if after:
                tag_output_parts.append(after)
            continue
        if tag_current is not None:
            if tag_in_result:
                tag_output_parts.append(line)
            else:
                tag_input_parts.append(line)
            continue

        obj = None
        if stripped.startswith("{") and stripped.endswith("}"):
            try:
                loaded = json.loads(stripped)
            except json.JSONDecodeError:
                loaded = None
            if isinstance(loaded, dict) and _is_tool_event_json(loaded):
                obj = loaded

        if obj is not None:
            used_json = True
            if _json_is_result(obj) and not obj.get("tool_calls"):
                attach_result(_json_result_text(obj), str(obj.get("tool_name") or obj.get("name") or ""))
                continue
            pairs = _json_tool_calls(obj)
            if pairs:
                for name, inp in pairs:
                    open_call(name, inp)
                if _json_is_result(obj):
                    attach_result(_json_result_text(obj))
                continue
            if _json_is_result(obj):
                attach_result(_json_result_text(obj))
            continue

        if used_json or used_tags:
            continue

        m_live = RE_LIVE.match(line)
        if not m_live:
            continue
        kind, payload = m_live.group(1), m_live.group(2).strip()
        if kind == "tool":
            m_name = RE_LIVE_CALL.match(payload)
            if m_name:
                name = m_name.group(1)
                args = m_name.group(2) or ""
            else:
                name = payload.lstrip("-> ").split("(", 1)[0].strip() or "unknown"
                args = payload
            open_call(name, args)
        elif kind == "result":
            hint = payload.split()[0] if payload else ""
            attach_result(payload, hint)

    flush_tag()
    return calls


def load_calls(session_log: Path | None, sessions_dir: Path | None) -> list[ToolCall]:
    paths: list[Path] = []
    if session_log is not None:
        paths.append(session_log)
    else:
        assert sessions_dir is not None
        if sessions_dir.is_dir():
            paths = sorted(p for p in sessions_dir.rglob("*.log") if p.is_file())
        elif sessions_dir.is_file():
            paths = [sessions_dir]
    calls: list[ToolCall] = []
    for path in paths:
        try:
            # Stream line-by-line to avoid loading 50-100MB logs into memory at once.
            lines_buf: list[str] = []
            with path.open(encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    lines_buf.append(line)
                    # Flush in chunks to keep memory bounded (~4MB per chunk).
                    if len(lines_buf) >= 40_000:
                        parsed = parse_log_text("".join(lines_buf), start_index=len(calls))
                        calls.extend(parsed)
                        lines_buf = []
            if lines_buf:
                parsed = parse_log_text("".join(lines_buf), start_index=len(calls))
                calls.extend(parsed)
        except OSError as exc:
            print(f"warn: cannot read {path}: {exc}", file=sys.stderr)
            continue
    return calls


def build_taint_dag(
    calls: list[ToolCall],
) -> tuple[list[tuple[str, int]], list[dict[str, Any]], dict[str, int]]:
    nodes = [(c.name, c.index) for c in calls]
    token_sets = [extract_taint_tokens(c.out) for c in calls]
    edges: list[dict[str, Any]] = []
    seen: set[tuple[int, int, str]] = set()
    token_edge_counts: dict[str, int] = Counter()

    n = len(calls)
    # Index tokens -> producing call indices for faster dst scans.
    producers: dict[str, list[int]] = defaultdict(list)
    for i, toks in enumerate(token_sets):
        for tok in toks:
            producers[tok].append(i)

    for dst_i, dst in enumerate(calls):
        if not dst.inp:
            continue
        inp = dst.inp
        matched: set[str] = set()
        for tok, srcs in producers.items():
            if tok in matched:
                continue
            if tok not in inp:
                continue
            matched.add(tok)
            for src_i in srcs:
                if src_i >= dst_i:
                    continue
                key = (src_i, dst_i, tok)
                if key in seen:
                    continue
                seen.add(key)
                src = calls[src_i]
                edges.append(
                    {
                        "src": [src.name, src.index],
                        "dst": [dst.name, dst.index],
                        "token": tok,
                    }
                )
                token_edge_counts[tok] += 1
    return nodes, edges, token_edge_counts


def baseline_edge_count(calls: list[ToolCall]) -> int:
    """Unique (src, dst) pairs that share at least one 10-gram (spike 008b)."""
    out_grams = [ngrams(c.out) for c in calls]
    in_grams = [ngrams(c.inp) for c in calls]
    count = 0
    n = len(calls)
    nonempty_src = [(i, g) for i, g in enumerate(out_grams) if g]
    for dst_i in range(n):
        dg = in_grams[dst_i]
        if not dg:
            continue
        for src_i, sg in nonempty_src:
            if src_i >= dst_i:
                break
            if sg & dg:
                count += 1
    return count


def dag_stats(
    nodes: list[tuple[str, int]], edges: list[dict[str, Any]]
) -> tuple[int, list[str]]:
    """Return (max_depth, root_labels). Root depth is 0; depth is longest edge path."""
    node_ids = [(n[0], n[1]) for n in nodes]
    preds: dict[tuple[str, int], set[tuple[str, int]]] = {nid: set() for nid in node_ids}
    succs: dict[tuple[str, int], set[tuple[str, int]]] = {nid: set() for nid in node_ids}
    for e in edges:
        src = (e["src"][0], e["src"][1])
        dst = (e["dst"][0], e["dst"][1])
        if src not in preds:
            preds[src] = set()
            succs[src] = set()
        if dst not in preds:
            preds[dst] = set()
            succs[dst] = set()
        preds[dst].add(src)
        succs[src].add(dst)

    roots = [nid for nid in node_ids if not preds.get(nid)]
    depth: dict[tuple[str, int], int] = {}

    def longest(nid: tuple[str, int], stack: set[tuple[str, int]]) -> int:
        if nid in depth:
            return depth[nid]
        if nid in stack:
            return 0
        stack.add(nid)
        best = 0
        for p in preds.get(nid, ()):
            best = max(best, 1 + longest(p, stack))
        stack.remove(nid)
        depth[nid] = best
        return best

    max_depth = 0
    for nid in node_ids:
        max_depth = max(max_depth, longest(nid, set()))

    root_labels = [f"{name}#{idx}" for name, idx in roots]
    return max_depth, root_labels


def print_summary(
    nodes: list[tuple[str, int]],
    edges: list[dict[str, Any]],
    token_counts: dict[str, int],
    baseline: int,
    max_depth: int,
    roots: list[str],
) -> None:
    n_nodes = len(nodes)
    n_edges = len(edges)
    print(
        f"Nodes: {n_nodes} | Edges: {n_edges} | Max depth: {max_depth} | Root nodes: {roots}"
    )
    print("Top 10 propagated tokens:")
    top = sorted(token_counts.items(), key=lambda kv: (-kv[1], kv[0]))[:10]
    if not top:
        print("  (none)")
    else:
        for i, (tok, cnt) in enumerate(top, 1):
            print(f"  {i}. {tok} ({cnt} edges)")
    print(f"10-gram baseline edge count: {baseline}")
    print(f"Named-taint edge count: {n_edges}")
    if baseline > 0:
        reduction = 100.0 * (1.0 - (n_edges / baseline))
        print(f"Reduction: {reduction:.1f}% fewer edges")
    else:
        print("Reduction: n/a (baseline has 0 edges)")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Named-variable path-taint DAG over Hermes logs")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--session-log", type=Path, help="single log file")
    g.add_argument("--sessions-dir", type=Path, help="directory of .log files")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    session_log = args.session_log
    sessions_dir = args.sessions_dir
    if session_log is not None and not session_log.exists():
        print(f"warn: log not found: {session_log}", file=sys.stderr)
        _write_empty_results()
        return 0
    if sessions_dir is not None and not sessions_dir.exists():
        print(f"warn: directory not found: {sessions_dir}", file=sys.stderr)
        _write_empty_results()
        return 0

    calls = load_calls(session_log, sessions_dir)
    if not calls:
        print("warn: no tool calls parsed from log(s)", file=sys.stderr)
        _write_empty_results()
        return 0

    nodes, edges, token_counts = build_taint_dag(calls)
    baseline = baseline_edge_count(calls)
    max_depth, roots = dag_stats(nodes, edges)
    print_summary(nodes, edges, token_counts, baseline, max_depth, roots)

    payload = {
        "nodes": [[name, idx] for name, idx in nodes],
        "edges": edges,
        "stats": {
            "n_nodes": len(nodes),
            "n_edges": len(edges),
            "baseline_edges": baseline,
        },
    }
    try:
        _tmp_results_path = RESULTS_PATH.with_suffix('.tmp')
        _tmp_results_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        _tmp_results_path.replace(RESULTS_PATH)
    except OSError as exc:
        print(f"warn: could not write {RESULTS_PATH}: {exc}", file=sys.stderr)
    return 0


def _write_empty_results() -> None:
    payload = {
        "nodes": [],
        "edges": [],
        "stats": {"n_nodes": 0, "n_edges": 0, "baseline_edges": 0},
    }
    try:
        _tmp_results_path = RESULTS_PATH.with_suffix('.tmp')
        _tmp_results_path.write_text(json.dumps(payload), encoding="utf-8")
        _tmp_results_path.replace(RESULTS_PATH)
    except OSError:
        pass
    print("Nodes: 0 | Edges: 0 | Max depth: 0 | Root nodes: []")
    print("Top 10 propagated tokens:")
    print("  (none)")
    print("10-gram baseline edge count: 0")
    print("Named-taint edge count: 0")
    print("Reduction: n/a (baseline has 0 edges)")


if __name__ == "__main__":
    sys.exit(main())
