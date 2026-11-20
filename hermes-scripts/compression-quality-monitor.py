#!/usr/bin/env python3
"""Compression quality monitor (single-user context loss).

Parses agent.log for compression telemetry, rearm, and ineffective-compaction
warnings. Flags stale rd-compaction-advisory.json when it disagrees with live
prompt tokens. Writes cache/compression-quality.json (+ optional alarm).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone, UTC
from pathlib import Path

TS_RE = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})")
WINDOW_S = 24 * 3600
STALE_ADVISORY_RATIO = 8.0
STALE_ADVISORY_ABS = 400_000
THRESHOLD_DEFAULT = 120_000


def _hermes_home() -> Path:
    env = os.environ.get("HERMES_HOME", "").strip()
    path = Path(env).expanduser().resolve() if env else (Path.home() / ".hermes")
    if path.name == ".hermes":
        return path
    if path.parent.name == "profiles":
        return path.parent.parent
    return path


def _profile_name() -> str:
    return os.environ.get("HERMES_PROFILE") or "fork"


def _hermes_root() -> Path:
    home = _hermes_home()
    env = os.environ.get("HERMES_HOME", "").strip()
    if env:
        p = Path(env).expanduser().resolve()
        if p.parent.name == "profiles":
            return p
    cand = home / "profiles" / _profile_name()
    return cand if cand.is_dir() else home


def _atomic_write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    data = json.dumps(payload, indent=2, default=str) + "\n"
    fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
    try:
        os.write(fd, data.encode())
        os.fsync(fd)
    finally:
        os.close(fd)
    os.replace(tmp, path)


def _now() -> datetime:
    return datetime.now(UTC)


def _parse_log_ts(line: str) -> float | None:
    m = TS_RE.match(line)
    if not m:
        return None
    try:
        dt = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")
        return dt.replace(tzinfo=datetime.now().astimezone().tzinfo).timestamp()
    except ValueError:
        return None


def _log_paths(home: Path, root: Path) -> list[Path]:
    out: list[Path] = []
    seen: set[Path] = set()
    for d in (home / "logs", root / "logs"):
        if not d.is_dir():
            continue
        for name in ("agent.log", "agent.log.1", "agent.log.2"):
            p = d / name
            if p.is_file():
                rp = p.resolve()
                if rp not in seen:
                    seen.add(rp)
                    out.append(p)
    return out


def parse_telemetry_json(line: str) -> dict | None:
    marker = "context compression attempt telemetry:"
    idx = line.find(marker)
    if idx < 0:
        return None
    raw = line[idx + len(marker) :].strip()
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(obj, dict):
        return None
    return obj


def scan_logs(paths: list[Path], cutoff: float) -> dict:
    n_telem = 0
    n_rearm = 0
    n_ineffective = 0
    n_abort = 0
    last_prompt = None
    last_threshold = None
    last_outcome = None
    abort_reasons: dict[str, int] = {}
    outcomes: dict[str, int] = {}
    for path in paths:
        try:
            fh = path.open(errors="replace")
        except OSError:
            continue
        with fh:
            for line in fh:
                ts = _parse_log_ts(line)
                if ts is not None and ts < cutoff:
                    continue
                if "Compression budget rearmed after provider-confirmed recovery" in line:
                    n_rearm += 1
                    m = re.search(r"prompt=(\d+)\s*<\s*threshold=(\d+)", line)
                    if m:
                        last_prompt = int(m.group(1))
                        last_threshold = int(m.group(2))
                if "Compaction did not clear the threshold" in line:
                    n_ineffective += 1
                    m = re.search(r":\s*(\d+)\s+real tokens still >=\s*(\d+)", line)
                    if m:
                        last_prompt = int(m.group(1))
                        last_threshold = int(m.group(2))
                telem = parse_telemetry_json(line)
                if telem is None:
                    continue
                n_telem += 1
                outcome = str(
                    telem.get("commit_status")
                    or telem.get("outcome")
                    or telem.get("status")
                    or "unknown"
                )
                outcomes[outcome] = outcomes.get(outcome, 0) + 1
                last_outcome = outcome
                if outcome in {"aborted", "abort", "skipped"}:
                    n_abort += 1
                    reason = str(
                        telem.get("failure_class")
                        or telem.get("abort_reason")
                        or telem.get("reason")
                        or "unspecified"
                    )
                    abort_reasons[reason] = abort_reasons.get(reason, 0) + 1
                pt = (
                    telem.get("tokens_after")
                    or telem.get("prompt_tokens")
                    or telem.get("last_prompt_tokens")
                    or telem.get("current_estimated_tokens")
                )
                th = telem.get("effective_threshold") or telem.get("threshold") or telem.get(
                    "compression_threshold"
                )
                if isinstance(pt, (int, float)):
                    last_prompt = int(pt)
                if isinstance(th, (int, float)):
                    last_threshold = int(th)
                reclaimed = telem.get("tokens_reclaimed")
                if isinstance(reclaimed, (int, float)):
                    outcomes["_reclaimed_sum"] = outcomes.get("_reclaimed_sum", 0) + int(reclaimed)
                omitted = telem.get("summary_input_omitted_chars")
                if isinstance(omitted, (int, float)) and omitted > 0:
                    outcomes["_summary_omitted_chars"] = outcomes.get("_summary_omitted_chars", 0) + int(
                        omitted
                    )
    return {
        "n_telemetry": n_telem,
        "n_rearm": n_rearm,
        "n_ineffective": n_ineffective,
        "n_abort": n_abort,
        "last_prompt_tokens": last_prompt,
        "last_threshold": last_threshold,
        "last_outcome": last_outcome,
        "abort_reasons": abort_reasons,
        "outcomes": outcomes,
    }


def load_advisory(root: Path) -> dict | None:
    p = root / "cache" / "rd-compaction-advisory.json"
    if not p.is_file():
        return None
    try:
        obj = json.loads(p.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    return obj if isinstance(obj, dict) else None


def latest_token_usage_prompt(home: Path, root: Path) -> int | None:
    last = None
    for d in (home / "logs", root / "logs"):
        p = d / "token-usage.jsonl"
        if not p.is_file():
            continue
        try:
            with p.open() as fh:
                fh.seek(0, os.SEEK_END)
                size = fh.tell()
                fh.seek(max(0, size - 65536))
                chunk = fh.read()
        except OSError:
            continue
        for line in chunk.splitlines()[::-1]:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("scope") == "ue_blackbox":
                continue
            pt = rec.get("prompt_tokens")
            if isinstance(pt, (int, float)):
                last = int(pt)
                break
    return last


def build_report(scan: dict, advisory: dict | None, live_prompt: int | None) -> dict:
    alarms: list[dict] = []
    last_prompt = scan.get("last_prompt_tokens")
    live = live_prompt if live_prompt is not None else last_prompt
    adv_tokens = None
    if advisory:
        adv_tokens = advisory.get("current_tokens")
        if not isinstance(adv_tokens, (int, float)):
            adv_tokens = None
        else:
            adv_tokens = int(adv_tokens)
    if (
        adv_tokens is not None
        and live is not None
        and live > 0
        and adv_tokens > STALE_ADVISORY_ABS
        and adv_tokens > live * STALE_ADVISORY_RATIO
    ):
        alarms.append(
            {
                "severity": "HIGH",
                "why": "rd-compaction-advisory current_tokens is stale vs live prompt",
                "advisory_tokens": adv_tokens,
                "live_prompt_tokens": live,
                "ratio": round(adv_tokens / live, 2),
            }
        )
    if scan.get("n_ineffective", 0) >= 3:
        alarms.append(
            {
                "severity": "MEDIUM",
                "why": "compaction failed to clear threshold multiple times",
                "n_ineffective": scan["n_ineffective"],
            }
        )
    n_telem = scan.get("n_telemetry") or 0
    n_abort = scan.get("n_abort") or 0
    if n_telem >= 8 and n_abort / n_telem > 0.5:
        alarms.append(
            {
                "severity": "MEDIUM",
                "why": "more than half of compression attempts aborted",
                "n_abort": n_abort,
                "n_telemetry": n_telem,
            }
        )
    status = "ok"
    if any(a["severity"] == "HIGH" for a in alarms):
        status = "alarm"
    elif alarms:
        status = "warn"
    return {
        "ts": _now().isoformat(),
        "window_s": WINDOW_S,
        "status": status,
        "scan": scan,
        "live_prompt_tokens": live,
        "advisory_tokens": adv_tokens,
        "threshold_default": THRESHOLD_DEFAULT,
        "alarms": alarms,
        "theory": "ContextCompressor rearm/ineffective + Rate-Distortion advisory freshness",
    }


def _self_test() -> int:
    home = _hermes_home()
    os.environ["HERMES_HOME"] = str(home / "profiles" / "fork")
    assert _hermes_home() == home
    os.environ["HERMES_HOME"] = str(home)
    line = 'x context compression attempt telemetry: {"outcome": "aborted", "abort_reason": "below_min", "prompt_tokens": 80000, "threshold": 120000}'
    obj = parse_telemetry_json(line)
    assert obj and obj["outcome"] == "aborted"
    assert parse_telemetry_json("nope") is None
    report = build_report(
        {
            "n_telemetry": 10,
            "n_rearm": 1,
            "n_ineffective": 4,
            "n_abort": 6,
            "last_prompt_tokens": 70000,
            "last_threshold": 120000,
            "abort_reasons": {"below_min": 6},
            "outcomes": {"aborted": 6, "ok": 4},
        },
        {"current_tokens": 5080871},
        70000,
    )
    assert report["status"] == "alarm"
    assert any("stale" in a["why"] for a in report["alarms"])
    print(json.dumps({"status": "ok", "self_test": True}))
    return 0


def _run() -> int:
    home = _hermes_home()
    root = _hermes_root()
    cutoff = time.time() - WINDOW_S
    scan = scan_logs(_log_paths(home, root), cutoff)
    advisory = load_advisory(root)
    live = latest_token_usage_prompt(home, root)
    report = build_report(scan, advisory, live)
    out = root / "cache" / "compression-quality.json"
    _atomic_write(out, report)
    alarm_path = root / "cache" / "compression-quality-alarm.json"
    if report["status"] in {"warn", "alarm"} and report["alarms"]:
        sev = "HIGH" if report["status"] == "alarm" else "MEDIUM"
        _atomic_write(
            alarm_path,
            {
                "ts": report["ts"],
                "name": "compression-quality-monitor",
                "severity": sev,
                "status": report["status"],
                "summary": f"compression {report['status']}: {len(report['alarms'])} issue(s)",
                "alarms": report["alarms"],
            },
        )
    elif alarm_path.exists():
        try:
            alarm_path.unlink()
        except OSError:
            pass
    print(json.dumps({"status": report["status"], "out": str(out), "n_telemetry": scan["n_telemetry"]}))
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-test", action="store_true")
    p.add_argument("--run", action="store_true")
    args = p.parse_args(argv)
    if args.self_test:
        return _self_test()
    # Scheduler does not pass job.args; cron argv is empty → default --run.
    try:
        return _run()
    except Exception as exc:
        print(f"fail-open: {exc}", file=sys.stderr)
        return 0


if __name__ == "__main__":
    sys.exit(main())
