#!/usr/bin/env python3
"""eval-compaction-data-bridge.py — wire compaction eval output into IT scripts.

Fixes:
  compaction-aep-typical-set.py n_pre=0 / n_post=0 (no pre/post files)
  compaction-chain-rule-mi.py h_x=0 / i_xy=0 (same)
  rd-compaction-advisor.py missing --current-tokens when called without CLI

Writes (under cache/):
  pre-compact-context.txt
  mid-compact-context.txt
  post-compact-context.txt
  current-token-count.json
  compaction-aep-typical-set.json   (via the AEP script)
  compaction-chain-rule-mi.json     (via the chain-rule script)

Also runs a planted-needle structural eval across policy arms when
--transcript and --questions are given (AUDIT-22: score needles before
declaring head_hit_rate broken). No LLM. Stdlib only.

Usage:
  python3 eval-compaction-data-bridge.py --self-test
  python3 eval-compaction-data-bridge.py --transcript T.json --questions Q.json --out DIR
  python3 eval-compaction-data-bridge.py --runner-out SCORECARD.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

NEEDLE_RE = re.compile(r"The deploy code for region (\d+) is (Z\d+)")

# Match evals/compaction/policies.py + ContextCompressor defaults (lean 1M window).
POLICIES = {
    "current": {"tail_token_budget": 25_000, "protect_first_n": 3, "protect_last_n": 20, "engine": "summary"},
    "tail25k": {"tail_token_budget": 25_000, "protect_first_n": 3, "protect_last_n": 20, "engine": "summary"},
    "tail10k": {"tail_token_budget": 10_000, "protect_first_n": 3, "protect_last_n": 20, "engine": "summary"},
    "codex_style": {"tail_token_budget": 2_000, "protect_first_n": 3, "protect_last_n": 3, "engine": "summary"},
    "lean": {"tail_token_budget": 25_000, "protect_first_n": 3, "protect_last_n": 20, "engine": "summary"},
    "jev": {"engine": "jev", "preserve_recent_messages": 6},
    "jev_tail40": {"engine": "jev", "preserve_recent_messages": 40},
}


def _hermes_home() -> Path:
    env = os.environ.get("HERMES_HOME", "").strip()
    p = Path(env) if env else Path.home() / ".hermes"
    if p.name != ".hermes" and p.parent.name == "profiles":
        return p.parent.parent
    return p


def _profile_root() -> Path:
    base = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
    profile = os.environ.get("HERMES_PROFILE", "")
    if profile and "profiles" not in str(base):
        return base / "profiles" / profile
    return base


def _cache_dir() -> Path:
    override = os.environ.get("UE_CACHE_DIR", "").strip()
    p = Path(override) if override else (_profile_root() / "cache")
    p.mkdir(parents=True, exist_ok=True)
    return p


def _scripts_dir() -> Path:
    return _hermes_home() / "hermes-scripts"


def estimate_tokens(msg: dict) -> int:
    total = len(msg.get("content") or "") if isinstance(msg.get("content"), str) else 0
    tc = msg.get("tool_calls")
    if tc:
        total += len(json.dumps(tc, default=str))
    return total // 4


def total_tokens(messages: list) -> int:
    return sum(estimate_tokens(m) for m in messages)


def serialize(messages: list) -> str:
    parts = []
    for m in messages:
        c = m.get("content")
        if isinstance(c, str) and c:
            parts.append(f"[{m.get('role')}] {c}")
    return "\n\n".join(parts)


def extract_needles(messages: list) -> list:
    out = []
    for i, m in enumerate(messages):
        c = m.get("content") or ""
        if not isinstance(c, str):
            continue
        for mm in NEEDLE_RE.finditer(c):
            out.append({
                "msg_index": i,
                "role": m.get("role"),
                "region": int(mm.group(1)),
                "code": mm.group(2),
            })
    return out


def protect_head_size(messages: list, protect_first_n: int) -> int:
    head = 1 if messages and messages[0].get("role") == "system" else 0
    return head + max(int(protect_first_n), 0)


def tail_cut(messages: list, head_end: int, token_budget: int, min_tail: int) -> int:
    """Walk backward accumulating tokens; never split the last row."""
    n = len(messages)
    if n <= head_end:
        return n
    budget = max(int(token_budget), 1)
    acc = 0
    cut = n
    floor = max(1, min(int(min_tail), n - head_end))
    for i in range(n - 1, head_end - 1, -1):
        acc += estimate_tokens(messages[i])
        if acc > budget and (n - i) >= floor:
            cut = i + 1
            break
        cut = i
    return max(cut, head_end)


def compress_summary(messages: list, spec: dict, oracle_summary: bool = False) -> list:
    head_end = protect_head_size(messages, spec.get("protect_first_n", 3))
    min_tail = max(3, min(spec.get("protect_last_n", 20), 8))
    cut = tail_cut(messages, head_end, spec.get("tail_token_budget", 25_000), min_tail)
    head = messages[:head_end]
    tail = messages[cut:]
    middle = messages[head_end:cut]
    if oracle_summary:
        needles = extract_needles(middle)
        body = "Oracle summary of compacted region. " + " ".join(
            f"The deploy code for region {n['region']} is {n['code']}." for n in needles
        )
        if not needles:
            body += "No planted deploy codes in middle."
    else:
        body = (
            "[compaction summary] Middle turns replaced. "
            "session_search can recover pre-compaction history. "
            "No planted facts copied (closed-book structural lower bound)."
        )
    summary_msg = {"role": "user", "content": body, "_compaction_summary": True}
    return head + [summary_msg] + tail


def compress_jev(messages: list, spec: dict) -> list:
    keep_recent = int(spec.get("preserve_recent_messages", 6))
    n = len(messages)
    tail_start = max(0, n - keep_recent)
    out = []
    for i, m in enumerate(messages):
        role = m.get("role")
        if role in ("system", "user", "assistant") or i >= tail_start:
            out.append(m)
        elif role == "tool":
            c = m.get("content") or ""
            truncated = (c[:80] + "…[jev-dropped]") if isinstance(c, str) and c else ""
            nm = dict(m)
            nm["content"] = truncated
            out.append(nm)
        else:
            out.append(m)
    return out


def apply_policy(name: str, messages: list, oracle_summary: bool = False) -> list:
    spec = POLICIES[name]
    if spec.get("engine") == "jev":
        return compress_jev(messages, spec)
    return compress_summary(messages, spec, oracle_summary=oracle_summary)


def classify_needles(needles: list, messages: list, spec: dict) -> dict:
    if spec.get("engine") == "jev":
        n = len(messages)
        keep_recent = int(spec.get("preserve_recent_messages", 6))
        tail_start = max(0, n - keep_recent)
        head_end = 0
        cut = tail_start
    else:
        head_end = protect_head_size(messages, spec.get("protect_first_n", 3))
        min_tail = max(3, min(spec.get("protect_last_n", 20), 8))
        cut = tail_cut(messages, head_end, spec.get("tail_token_budget", 25_000), min_tail)
    buckets = {
        "head": [],
        "middle": [],
        "tail": [],
        "head_end": head_end,
        "tail_start": cut,
    }
    for nd in needles:
        i = nd["msg_index"]
        if i < head_end:
            buckets["head"].append(nd)
        elif i >= cut:
            buckets["tail"].append(nd)
        else:
            buckets["middle"].append(nd)
    return buckets


def hit_rate(needles: list, text: str) -> float:
    if not needles:
        return None  # type: ignore[return-value]
    hits = sum(1 for n in needles if n["code"] in text)
    return hits / len(needles)


def score_arm(name: str, messages: list, needles: list, questions: list, oracle: bool = False) -> dict:
    spec = POLICIES[name]
    compressed = apply_policy(name, messages, oracle_summary=oracle)
    pre_text = serialize(messages)
    post_text = serialize(compressed)
    buckets = classify_needles(needles, messages, spec)
    before = total_tokens(messages)
    after = total_tokens(compressed)
    q_hits = 0
    q_n = 0
    for q in questions:
        needle = q.get("expected_answer_contains") or ""
        if not needle:
            continue
        q_n += 1
        if needle in post_text:
            q_hits += 1
    head_hr = hit_rate(buckets["head"], post_text)
    tail_hr = hit_rate(buckets["tail"], post_text)
    mid_hr = hit_rate(buckets["middle"], post_text)
    all_hr = hit_rate(needles, post_text) or 0.0
    return {
        "policy": name,
        "oracle_summary": oracle,
        "engine": spec.get("engine"),
        "before_tokens": before,
        "after_tokens": after,
        "after_msgs": len(compressed),
        "token_reduction": round(1.0 - (after / before), 6) if before else 0.0,
        "compression_ratio": round(after / before, 6) if before else 1.0,
        "head_end": buckets["head_end"],
        "tail_start": buckets["tail_start"],
        "n_needles": len(needles),
        "n_head_needles": len(buckets["head"]),
        "n_middle_needles": len(buckets["middle"]),
        "n_tail_needles": len(buckets["tail"]),
        "head_hit_rate": head_hr,
        "middle_hit_rate": mid_hr,
        "tail_hit_rate": tail_hr,
        "planted_needle_recall": round(all_hr, 6),
        "question_hit_rate": (q_hits / q_n) if q_n else None,
        "n_questions": q_n,
        "question_hits": q_hits,
        "distortion": round(1.0 - all_hr, 6),
        "head_codes": [n["code"] for n in buckets["head"]],
        "middle_codes": [n["code"] for n in buckets["middle"]],
        "tail_codes": [n["code"] for n in buckets["tail"]],
        "pre_chars": len(pre_text),
        "post_chars": len(post_text),
        "pre_text": pre_text,
        "post_text": post_text,
        "mid_text": serialize(messages[buckets["head_end"]:buckets["tail_start"]]),
    }


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def write_bridge_files(pre: str, mid: str, post: str, current_tokens: int) -> dict:
    cache = _cache_dir()
    atomic_write(cache / "pre-compact-context.txt", pre)
    atomic_write(cache / "mid-compact-context.txt", mid or pre[: max(1, (2 * len(pre)) // 3)])
    atomic_write(cache / "post-compact-context.txt", post)
    atomic_write(cache / "compacted-context.txt", post)
    tok = {
        "current_tokens": int(current_tokens),
        "tokens": int(current_tokens),
        "token_count": int(current_tokens),
        "source": "eval-compaction-data-bridge",
    }
    atomic_write(cache / "current-token-count.json", json.dumps(tok, indent=2) + "\n")
    return {"cache": str(cache), "current_tokens": current_tokens}


def run_it_scripts(pre_path: Path, post_path: Path) -> dict:
    scripts = _scripts_dir()
    env = os.environ.copy()
    env["UE_CACHE_DIR"] = str(_cache_dir())
    out = {}
    aep = scripts / "compaction-aep-typical-set.py"
    mi = scripts / "compaction-chain-rule-mi.py"
    if aep.exists():
        r = subprocess.run(
            [sys.executable, str(aep), "--pre", str(pre_path), "--post", str(post_path)],
            capture_output=True, text=True, timeout=30, env=env,
        )
        try:
            out["aep"] = json.loads(r.stdout or "{}")
        except json.JSONDecodeError:
            out["aep"] = {"raw": r.stdout, "stderr": r.stderr, "rc": r.returncode}
    else:
        out["aep"] = {"error": f"missing {aep}"}
    if mi.exists():
        r = subprocess.run(
            [sys.executable, str(mi)],
            capture_output=True, text=True, timeout=30, env=env,
        )
        try:
            out["chain_rule_mi"] = json.loads(r.stdout or "{}")
        except json.JSONDecodeError:
            out["chain_rule_mi"] = {"raw": r.stdout, "stderr": r.stderr, "rc": r.returncode}
    else:
        out["chain_rule_mi"] = {"error": f"missing {mi}"}
    return out


def load_messages(path: Path) -> list:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["messages"] if isinstance(data, dict) else data


def load_questions(path: Path) -> list:
    data = json.loads(path.read_text(encoding="utf-8"))
    out = []
    for q in data:
        if "expected_answer_contains" in q:
            out.append(q)
        elif "gold" in q:
            out.append({
                "question": q.get("q") or q.get("question"),
                "expected_answer_contains": q["gold"],
            })
        else:
            out.append(q)
    return out


def rd_table(arms: list) -> list:
    rows = []
    for a in arms:
        rows.append({
            "policy": a["policy"],
            "oracle_summary": a["oracle_summary"],
            "rate": a["compression_ratio"],
            "token_reduction": a["token_reduction"],
            "distortion": a["distortion"],
            "planted_needle_recall": a["planted_needle_recall"],
            "head_hit_rate": a["head_hit_rate"],
            "tail_hit_rate": a["tail_hit_rate"],
            "before_tokens": a["before_tokens"],
            "after_tokens": a["after_tokens"],
        })
    return rows


def strip_texts(arm: dict) -> dict:
    slim = dict(arm)
    slim.pop("pre_text", None)
    slim.pop("post_text", None)
    slim.pop("mid_text", None)
    return slim


def self_test() -> int:
    msgs = [
        {"role": "system", "content": "You are a test agent."},
        {"role": "user", "content": "remember the codes."},
        {"role": "assistant", "content": "The deploy code for region 0 is Z1111."},
        {"role": "tool", "content": "step output " * 50},
    ]
    for i in range(1, 12):
        msgs.append({"role": "assistant", "content": f"Working on step {i}." + (
            f" The deploy code for region {i} is Z{2000 + i}." if i % 5 == 0 else ""
        )})
        msgs.append({"role": "tool", "content": ("step output " * 80) + f"result-{i}"})
    msgs.append({"role": "assistant", "content": "The deploy code for region 99 is Z9999. done."})
    needles = extract_needles(msgs)
    assert any(n["code"] == "Z1111" for n in needles)
    arm = score_arm("codex_style", msgs, needles, [
        {"question": "region 0", "expected_answer_contains": "Z1111"},
    ], oracle=False)
    assert arm["before_tokens"] > arm["after_tokens"]
    assert arm["n_head_needles"] >= 1
    # Head needle must survive structural keep.
    assert arm["head_hit_rate"] == 1.0
    cache = write_bridge_files(arm["pre_text"], arm["mid_text"], arm["post_text"], arm["before_tokens"])
    p = Path(cache["cache"]) / "current-token-count.json"
    assert p.exists()
    data = json.loads(p.read_text())
    assert data["current_tokens"] == arm["before_tokens"]
    print("PASS eval-compaction-data-bridge self-test")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--transcript", default="")
    ap.add_argument("--questions", default="")
    ap.add_argument("--policies", default="current,tail25k,tail10k,codex_style,lean,jev,jev_tail40")
    ap.add_argument("--out", default="")
    ap.add_argument("--oracle-summary", action="store_true",
                    help="Also score an oracle-middle-in-summary arm per policy")
    args = ap.parse_args()
    if args.self_test:
        return self_test()

    if not args.transcript:
        print(json.dumps({"error": "pass --transcript or --self-test"}))
        return 2

    messages = load_messages(Path(args.transcript))
    questions = load_questions(Path(args.questions)) if args.questions else []
    needles = extract_needles(messages)
    names = [n.strip() for n in args.policies.split(",") if n.strip() in POLICIES]

    arms = []
    for name in names:
        arms.append(score_arm(name, messages, needles, questions, oracle=False))
        if args.oracle_summary and POLICIES[name].get("engine") != "jev":
            arms.append(score_arm(name, messages, needles, questions, oracle=True))

    # Bridge files from the 'current' closed-book arm (or first).
    primary = next((a for a in arms if a["policy"] == "current" and not a["oracle_summary"]), arms[0])
    written = write_bridge_files(
        primary["pre_text"], primary["mid_text"], primary["post_text"], primary["before_tokens"],
    )
    cache = _cache_dir()
    it = run_it_scripts(cache / "pre-compact-context.txt", cache / "post-compact-context.txt")

    slim_arms = [strip_texts(a) for a in arms]
    result = {
        "n_messages": len(messages),
        "n_needles": len(needles),
        "needles": needles,
        "n_questions": len(questions),
        "bridge": written,
        "it": it,
        "rd_curve": rd_table(slim_arms),
        "arms": slim_arms,
        "note": (
            "Structural closed-book lower bound: middle is replaced by a stub "
            "summary that does not copy planted facts (LLM summarizer not invoked). "
            "head_hit_rate of 0.0 on LLM exams is expected when questions are drawn "
            "only from summarized_region() and therefore never test head needles."
        ),
    }
    text = json.dumps(result, indent=2)
    print(text)
    if args.out:
        out = Path(args.out)
        if out.suffix.lower() == ".json":
            atomic_write(out, text + "\n")
        else:
            out.mkdir(parents=True, exist_ok=True)
            atomic_write(out / "planted-needle-scorecard.json", text + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
