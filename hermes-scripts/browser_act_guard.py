#!/usr/bin/env python3
"""Browser-act helpers borrowed from browser-use patterns (no nested Agent).

Pure, local, deterministic utilities for interactive browser runs:

- page fingerprint (url + element count + content hash)
- normalized action hashes (stable across cosmetic arg churn)
- soft loop detection with escalating nudges (not hard kills)
- ActionResult-style memory split (content-once vs long-term)
- multi-act early-stop decision when the page fingerprint changes

Usage (CLI):
  python3 browser_act_guard.py fingerprint --url URL --count N [--text-file F | --text T]
  python3 browser_act_guard.py action-hash --json '{"type":"click","index":3}'
  python3 browser_act_guard.py observe --state-file PATH --action-json J --fingerprint FP
  python3 browser_act_guard.py split --content-file F [--long-term L] [--error E]
  python3 browser_act_guard.py multi-act-stop --prev-fp A --curr-fp B --index I [--max N]
  python3 browser_act_guard.py filter-snapshot --text-file F [--max-lines N]

Designed for skill-driven use from Hermes browser sessions. Does not launch
browsers or depend on browser-use / Playwright SDKs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

DEFAULT_MAX_ACTIONS = 5
DEFAULT_SOFT_THRESHOLD = 2
DEFAULT_MEDIUM_THRESHOLD = 3
DEFAULT_HARD_THRESHOLD = 5
DEFAULT_STAGNANT_PAGES = 3
CONTENT_HASH_CHARS = 16
ACTION_TEXT_HASH_CHARS = 12
MAX_LONG_TERM_CHARS = 400
MAX_ERROR_CHARS = 600


# ── fingerprint / action hash ─────────────────────────────────────────────────


def _sha(text: str, n: int = CONTENT_HASH_CHARS) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:n]


def normalize_url(url: str) -> str:
    """Strip fragment; keep query (often meaningful for SPA state)."""
    u = (url or "").strip()
    if not u:
        return ""
    # drop fragment only
    if "#" in u:
        u = u.split("#", 1)[0]
    return u.rstrip("/")


def page_fingerprint(
    url: str,
    element_count: int,
    text: str = "",
    *,
    content_hash: Optional[str] = None,
) -> str:
    """Stable page fingerprint: url|count|content_hash.

    content_hash may be precomputed; otherwise derived from text.
    Empty text with no content_hash yields hash of empty string (still stable).
    """
    try:
        count = int(element_count)
    except (TypeError, ValueError):
        count = 0
    if count < 0:
        count = 0
    ch = (content_hash or "").strip() or _sha(text or "")
    return f"{normalize_url(url)}|{count}|{ch}"


def _token_sort(s: str) -> str:
    toks = re.findall(r"[a-z0-9]+", (s or "").lower())
    return " ".join(sorted(toks))


def normalize_action(action: Dict[str, Any]) -> str:
    """Normalize an action dict to a comparable hash key.

    Supported shapes (tolerant):
      {"type":"click","index":3} / {"action":"click","element":3} / {"type":"click","ref":"@e3"}
      {"type":"type"|"fill","index"|ref, "text":"..."}
      {"type":"navigate"|"open", "url":"..."}
      {"type":"search"|"find", "query"|"text":"..."}  # token-sorted
      {"type":"scroll", "direction":"down", "amount":3}
      {"type":"press"|"key", "key"|"keys":"Enter"}
    Unknown fields are ignored; unknown types fall back to sorted JSON.
    """
    if not isinstance(action, dict):
        return f"invalid|{_sha(str(action))}"

    raw_type = (
        action.get("type")
        or action.get("action")
        or action.get("name")
        or "unknown"
    )
    t = str(raw_type).strip().lower().replace("-", "_")

    def _index() -> str:
        for k in ("index", "element", "ref", "selector", "sel"):
            if k in action and action[k] is not None and str(action[k]).strip() != "":
                v = str(action[k]).strip()
                # normalize @e3 / e3 / 3
                m = re.search(r"(\d+)$", v)
                if m and k in ("index", "element", "ref"):
                    return m.group(1)
                return v
        return ""

    def _text_key(keys: Sequence[str] = ("text", "value", "query", "q")) -> str:
        for k in keys:
            if k in action and action[k] is not None:
                return _sha(str(action[k]), ACTION_TEXT_HASH_CHARS)
        return ""

    if t in ("click", "dblclick", "double_click", "right_click", "hover", "focus", "check", "uncheck"):
        return f"{t}|idx={_index()}"
    if t in ("type", "fill", "select", "upload"):
        return f"{t}|idx={_index()}|txt={_text_key()}"
    if t in ("navigate", "open", "goto"):
        url = action.get("url") or action.get("href") or ""
        return f"navigate|url={normalize_url(str(url))}"
    if t in ("search", "find", "search_page"):
        q = action.get("query") or action.get("text") or action.get("value") or ""
        return f"search|q={_token_sort(str(q))}"
    if t == "scroll":
        direction = str(action.get("direction") or action.get("dir") or "down").lower()
        amount = action.get("amount", action.get("px", ""))
        return f"scroll|dir={direction}|amt={amount}|idx={_index()}"
    if t in ("press", "key", "keyboard"):
        key = action.get("key") or action.get("keys") or action.get("text") or ""
        return f"key|{str(key).lower()}"
    if t in ("wait", "sleep"):
        return f"wait|{action.get('ms', action.get('seconds', action.get('time', '')))}"
    if t == "done":
        return "done"
    # fallback: stable dump of scalar fields only
    scalars = {
        k: action[k]
        for k in sorted(action.keys())
        if isinstance(action[k], (str, int, float, bool)) or action[k] is None
    }
    return f"{t}|{_sha(json.dumps(scalars, sort_keys=True, default=str))}"


def action_hash(action: Dict[str, Any]) -> str:
    return _sha(normalize_action(action), 16)


# ── loop guard ────────────────────────────────────────────────────────────────


@dataclass
class LoopState:
    """Persistent soft-loop detector state (JSON-serializable)."""

    recent_pairs: List[str] = field(default_factory=list)  # "ahash@fp"
    recent_fps: List[str] = field(default_factory=list)
    same_action_streak: int = 0
    stagnant_page_streak: int = 0
    last_action_hash: str = ""
    last_fingerprint: str = ""
    nudge_level: str = "none"  # none|soft|medium|hard
    last_nudge: str = ""
    total_observations: int = 0
    # caps
    max_recent: int = 20

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "LoopState":
        if not data:
            return cls()
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        kwargs = {k: v for k, v in data.items() if k in known}
        return cls(**kwargs)


@dataclass
class LoopObservation:
    action_hash: str
    fingerprint: str
    same_action_streak: int
    stagnant_page_streak: int
    nudge_level: str
    nudge: str
    should_break: bool
    suggestion: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def observe_loop(
    state: LoopState,
    action: Dict[str, Any],
    fingerprint: str,
    *,
    soft: int = DEFAULT_SOFT_THRESHOLD,
    medium: int = DEFAULT_MEDIUM_THRESHOLD,
    hard: int = DEFAULT_HARD_THRESHOLD,
    stagnant_pages: int = DEFAULT_STAGNANT_PAGES,
) -> Tuple[LoopState, LoopObservation]:
    """Record one (action, page) observation and return escalating nudge if thrashing.

    Soft loop detection (browser-use style): does NOT hard-kill the agent.
    Escalates steer → constrain → stop suggestions for the skill layer.
    """
    if action.get("_prehashed") and action.get("hash"):
        ah = str(action["hash"])
    else:
        ah = action_hash(action)

    fp = (fingerprint or "").strip()
    state.total_observations += 1

    if ah and ah == state.last_action_hash:
        state.same_action_streak += 1
    else:
        state.same_action_streak = 1
    state.last_action_hash = ah

    if fp and fp == state.last_fingerprint:
        state.stagnant_page_streak += 1
    else:
        state.stagnant_page_streak = 1 if fp else 0
    state.last_fingerprint = fp

    pair = f"{ah}@{fp}"
    state.recent_pairs.append(pair)
    state.recent_fps.append(fp)
    if len(state.recent_pairs) > state.max_recent:
        state.recent_pairs = state.recent_pairs[-state.max_recent :]
    if len(state.recent_fps) > state.max_recent:
        state.recent_fps = state.recent_fps[-state.max_recent :]

    # identical action@page repeats
    pair_repeats = state.recent_pairs.count(pair)

    level = "none"
    nudge = ""
    should_break = False
    suggestion = ""

    thrash = max(state.same_action_streak, pair_repeats)
    page_stuck = state.stagnant_page_streak >= stagnant_pages and thrash >= soft

    if thrash >= hard:
        level = "hard"
        should_break = True
        nudge = (
            f"HARD loop: action hash {ah[:8]}… repeated {thrash}x "
            f"(page_streak={state.stagnant_page_streak})."
        )
        suggestion = (
            "Stop this approach. Switch tool ladder: web_extract/firecrawl → "
            "blocked-page-recovery → browser_exec script → different selector strategy. "
            "Do not re-click the same control."
        )
    elif thrash >= medium or page_stuck:
        level = "medium"
        nudge = (
            f"MEDIUM loop: same action {thrash}x "
            f"(page_streak={state.stagnant_page_streak})."
        )
        suggestion = (
            "Constrain: re-snapshot, try a different ref/selector, or batch remaining "
            "fills via browser_exec. Prefer search_page/find before another blind click."
        )
    elif thrash >= soft:
        level = "soft"
        nudge = f"SOFT loop: same action repeated {thrash}x."
        suggestion = (
            "Steer: verify the control actually changed state (snapshot/is checked). "
            "If form-filling, batch remaining fields in one multi-act step."
        )

    state.nudge_level = level
    state.last_nudge = nudge

    obs = LoopObservation(
        action_hash=ah,
        fingerprint=fp,
        same_action_streak=state.same_action_streak,
        stagnant_page_streak=state.stagnant_page_streak,
        nudge_level=level,
        nudge=nudge,
        should_break=should_break,
        suggestion=suggestion,
    )
    return state, obs


# ── ActionResult memory split ─────────────────────────────────────────────────


@dataclass
class ActionResultSplit:
    """Split bulky extract content from durable long-term memory."""

    extracted_content: str = ""
    include_content_only_once: bool = True
    long_term_memory: str = ""
    error: str = ""
    content_chars: int = 0
    long_term_chars: int = 0

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d

    def agent_view(self, *, seen_content: bool = False) -> Dict[str, Any]:
        """What to inject into the next agent turn.

        If include_content_only_once and content was already shown, omit extracted_content.
        Always keep long_term_memory + error.
        """
        out: Dict[str, Any] = {}
        if self.error:
            out["error"] = self.error[:MAX_ERROR_CHARS]
        if self.long_term_memory:
            out["long_term_memory"] = self.long_term_memory[:MAX_LONG_TERM_CHARS]
        show_content = self.extracted_content and not (
            self.include_content_only_once and seen_content
        )
        if show_content:
            out["extracted_content"] = self.extracted_content
            out["include_content_only_once"] = self.include_content_only_once
        return out


def split_action_result(
    content: str = "",
    *,
    long_term: str = "",
    error: str = "",
    include_once: bool = True,
    auto_long_term: bool = True,
) -> ActionResultSplit:
    """Build an ActionResult-style split.

    If long_term is empty and auto_long_term, derive a short durable line from content
    (first non-empty line, truncated) — never a full paste.
    """
    content = content or ""
    error = (error or "")[:MAX_ERROR_CHARS]
    lt = (long_term or "").strip()
    if not lt and auto_long_term and content.strip() and not error:
        for line in content.splitlines():
            s = line.strip()
            if s:
                lt = s[:MAX_LONG_TERM_CHARS]
                break
    elif lt:
        lt = lt[:MAX_LONG_TERM_CHARS]
    return ActionResultSplit(
        extracted_content=content,
        include_content_only_once=bool(include_once),
        long_term_memory=lt,
        error=error,
        content_chars=len(content),
        long_term_chars=len(lt),
    )


# ── multi-act early stop ──────────────────────────────────────────────────────


def multi_act_should_stop(
    prev_fingerprint: str,
    curr_fingerprint: str,
    action_index: int,
    *,
    max_actions: int = DEFAULT_MAX_ACTIONS,
    force_stop: bool = False,
) -> Dict[str, Any]:
    """Decide whether to stop a multi-act batch early.

    Stop when:
    - force_stop
    - page fingerprint changed after an action (navigation/DOM change)
    - action_index+1 would exceed max_actions (0-based index of action just done)
    """
    try:
        idx = int(action_index)
    except (TypeError, ValueError):
        idx = 0
    if idx < 0:
        idx = 0
    try:
        cap = int(max_actions)
    except (TypeError, ValueError):
        cap = DEFAULT_MAX_ACTIONS
    if cap < 1:
        cap = 1

    prev = (prev_fingerprint or "").strip()
    curr = (curr_fingerprint or "").strip()
    # Both sides must be non-empty; empty fp never counts as a page change.
    page_changed = bool(prev and curr and prev != curr)
    at_cap = (idx + 1) >= cap
    stop = bool(force_stop or page_changed or at_cap)
    reason = (
        "force"
        if force_stop
        else "page_changed"
        if page_changed
        else "max_actions"
        if at_cap
        else "continue"
    )
    return {
        "stop": stop,
        "reason": reason,
        "page_changed": page_changed,
        "actions_done": idx + 1,
        "max_actions": cap,
        "prev_fingerprint": prev,
        "curr_fingerprint": curr,
    }


# ── snapshot noise filter (lightweight; not full paint-order) ─────────────────


_NOISE_LINE_RE = re.compile(
    r"(cookie|consent|newsletter|subscribe|sign.?up.?for|accept all|reject all|"
    r"privacy policy|terms of (use|service)|enable (javascript|cookies)|"
    r"loading\.\.\.|advertisement|\bad\b|tracker)",
    re.I,
)


def filter_snapshot_lines(
    text: str,
    *,
    max_lines: Optional[int] = None,
    drop_noise: bool = True,
) -> Dict[str, Any]:
    """Drop common chrome/noise lines from an AX/snapshot dump.

    This is NOT a paint-order occlusion filter — only cheap text heuristics.
    Returns kept text + stats so callers can see what was removed.
    """
    lines = (text or "").splitlines()
    kept: List[str] = []
    dropped = 0
    for line in lines:
        if drop_noise and _NOISE_LINE_RE.search(line) and len(line.strip()) < 120:
            # keep if it looks like a real control with a ref id
            if not re.search(r"@e\d+|\[\d+\]|ref=", line):
                dropped += 1
                continue
        kept.append(line)
    if max_lines is not None and max_lines > 0 and len(kept) > max_lines:
        omitted = len(kept) - max_lines
        kept = kept[:max_lines]
        kept.append(f"[... {omitted} more lines omitted by filter-snapshot]")
        dropped += omitted
    out = "\n".join(kept)
    return {
        "text": out,
        "kept_lines": len(kept),
        "dropped_lines": dropped,
        "original_lines": len(lines),
        "original_chars": len(text or ""),
        "kept_chars": len(out),
    }


# ── state IO ──────────────────────────────────────────────────────────────────


def load_state(path: Path) -> LoopState:
    if not path.exists():
        return LoopState()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return LoopState()
    if not isinstance(data, dict):
        return LoopState()
    return LoopState.from_dict(data)


def save_state(path: Path, state: LoopState) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(state.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


# ── CLI ───────────────────────────────────────────────────────────────────────


def _read_text_arg(args: argparse.Namespace) -> str:
    if getattr(args, "text_file", None):
        return Path(args.text_file).read_text(encoding="utf-8", errors="replace")
    return getattr(args, "text", None) or ""


def _print(obj: Any) -> None:
    print(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False))


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    fp = sub.add_parser("fingerprint", help="Compute page fingerprint")
    fp.add_argument("--url", required=True)
    fp.add_argument("--count", type=int, required=True)
    fp.add_argument("--text", default="")
    fp.add_argument("--text-file")
    fp.add_argument("--content-hash", default="")

    ah = sub.add_parser("action-hash", help="Normalize + hash an action JSON object")
    ah.add_argument("--json", required=True, dest="action_json")

    obs = sub.add_parser("observe", help="Record action+fingerprint into loop state")
    obs.add_argument("--state-file", required=True)
    obs.add_argument("--action-json", required=True)
    obs.add_argument("--fingerprint", required=True)
    obs.add_argument("--soft", type=int, default=DEFAULT_SOFT_THRESHOLD)
    obs.add_argument("--medium", type=int, default=DEFAULT_MEDIUM_THRESHOLD)
    obs.add_argument("--hard", type=int, default=DEFAULT_HARD_THRESHOLD)
    obs.add_argument("--stagnant-pages", type=int, default=DEFAULT_STAGNANT_PAGES)

    sp = sub.add_parser("split", help="ActionResult memory split")
    sp.add_argument("--content", default="")
    sp.add_argument("--content-file")
    sp.add_argument("--long-term", default="")
    sp.add_argument("--error", default="")
    sp.add_argument("--include-once", action="store_true", default=True)
    sp.add_argument("--no-include-once", action="store_false", dest="include_once")
    sp.add_argument("--seen-content", action="store_true", default=False)
    sp.add_argument("--no-auto-long-term", action="store_true", default=False)

    ma = sub.add_parser("multi-act-stop", help="Early-stop decision for multi-act batch")
    ma.add_argument("--prev-fp", required=True)
    ma.add_argument("--curr-fp", required=True)
    ma.add_argument("--index", type=int, required=True, help="0-based index of action just executed")
    ma.add_argument("--max", type=int, default=DEFAULT_MAX_ACTIONS, dest="max_actions")
    ma.add_argument("--force-stop", action="store_true")

    fl = sub.add_parser("filter-snapshot", help="Drop common chrome/noise lines from snapshot text")
    fl.add_argument("--text", default="")
    fl.add_argument("--text-file")
    fl.add_argument("--max-lines", type=int, default=None)
    fl.add_argument("--keep-noise", action="store_true", default=False)

    args = p.parse_args(list(argv) if argv is not None else None)

    if args.cmd == "fingerprint":
        text = _read_text_arg(args)
        ch = args.content_hash or None
        fprint = page_fingerprint(args.url, args.count, text, content_hash=ch)
        _print(
            {
                "fingerprint": fprint,
                "url": normalize_url(args.url),
                "element_count": max(0, int(args.count)),
                "content_hash": ch or _sha(text),
            }
        )
        return 0

    if args.cmd == "action-hash":
        try:
            action = json.loads(args.action_json)
        except json.JSONDecodeError as e:
            _print({"error": f"invalid json: {e}"})
            return 2
        if not isinstance(action, dict):
            _print({"error": "action json must be an object"})
            return 2
        norm = normalize_action(action)
        _print({"normalized": norm, "hash": _sha(norm, 16)})
        return 0

    if args.cmd == "observe":
        try:
            action = json.loads(args.action_json)
        except json.JSONDecodeError as e:
            _print({"error": f"invalid json: {e}"})
            return 2
        if not isinstance(action, dict):
            _print({"error": "action json must be an object"})
            return 2
        path = Path(args.state_file)
        state = load_state(path)
        state, observation = observe_loop(
            state,
            action,
            args.fingerprint,
            soft=args.soft,
            medium=args.medium,
            hard=args.hard,
            stagnant_pages=args.stagnant_pages,
        )
        save_state(path, state)
        _print({"observation": observation.to_dict(), "state": state.to_dict()})
        return 0

    if args.cmd == "split":
        content = args.content
        if args.content_file:
            content = Path(args.content_file).read_text(encoding="utf-8", errors="replace")
        result = split_action_result(
            content,
            long_term=args.long_term,
            error=args.error,
            include_once=args.include_once,
            auto_long_term=not args.no_auto_long_term,
        )
        _print(
            {
                "split": result.to_dict(),
                "agent_view": result.agent_view(seen_content=args.seen_content),
            }
        )
        return 0

    if args.cmd == "multi-act-stop":
        _print(
            multi_act_should_stop(
                args.prev_fp,
                args.curr_fp,
                args.index,
                max_actions=args.max_actions,
                force_stop=args.force_stop,
            )
        )
        return 0

    if args.cmd == "filter-snapshot":
        text = _read_text_arg(args)
        _print(
            filter_snapshot_lines(
                text,
                max_lines=args.max_lines,
                drop_noise=not args.keep_noise,
            )
        )
        return 0

    p.error(f"unknown command {args.cmd}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
