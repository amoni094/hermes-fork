#!/usr/bin/python3
"""
monitor-suite-runner.py

Runs all Hermes monitoring scripts and prints a consolidated summary.
Designed for cron execution (no_agent=true).
BH-FDR (Benjamini-Hochberg) post-filter at q=0.10 annotates alarms with
bh_fdr_reject; never mutates existing status fields.
"""
import os
import re as _re
import subprocess
import sys
import json
from pathlib import Path
from datetime import datetime, timezone, UTC

_hermes_base = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_hermes_profile = os.environ.get("HERMES_PROFILE", "")
_hermes_root = (
    (_hermes_base / "profiles" / _hermes_profile)
    if _hermes_profile and "profiles" not in str(_hermes_base)
    else _hermes_base
)
_BASE_SCRIPTS = Path.home() / ".hermes" / "scripts"
SCRIPTS = _hermes_root / "scripts"
CACHE = _hermes_root / "cache" / "monitors"
BH_Q = 0.10

monitors = [
    "session-stability-monitor.py",
    "frequency-stability-monitor.py",
    "duality-gap-monitor.py",
    "uncertainty-calibration-monitor.py",
    "cascade-error-budget-allocator.py",
    "absorption-capacity-regime-monitor.py",
    "hierarchy-coherence-monitor.py",
    "redundancy-stability-monitor.py",
    "information-refinement-utility-monitor.py",
    "adaptive-context-mesh.py",
    "belief-consistency-validator.py",
    "tool-effect-validator.py",
    "safety-metric-evaluator.py",
    "constraint-validator-with-rollback.py",
    "experience-verifier.py",
    "spec-semantic-graph-builder.py",
    "plan-enforcement-gate.py",
    "containment-monitor.py",
    "parametric-retrieval-validator.py",
    "recursive-exploration-manager.py",
    "skill-graph-reachability-verifier.py",
    "constraint-alignment-validator.py",
    "federated-consensus-monitor.py",
    "cot-injection-detector.py",
    "information-bottleneck-monitor.py",
    "boundary-information-monitor.py",
    "kl-curvature-memory-monitor.py",
    "radius-hierarchy-monitor.py",
    "mask-coupling-monitor.py",
    "adaptive-leakage-accumulator.py",
    "hierarchy-radius-monitor.py",
    "spatial-mixing-error-budget.py",
    "magnitude-mirage-calibrator.py",
    "online-allocation-regret-monitor.py",
    "adversarial-robustness-tester.py",
    "quantization-behavior-monitor.py",
    "quickest-change-detector.py",
    "simulator-fisher-estimator.py",
    "horizon-constraint-validator.py",
    "state-concentration-monitor.py",
    "divergence-curvature-monitor.py",
    "bound-hierarchy-monitor.py",
    "prediction-tradeoff-monitor.py",
    "proportionality-monitor.py",
    "performative-stability-monitor.py",
    "context-budget-potential-monitor.py",
    "adaptive-key-leakage-monitor.py",
    "action-divergence-monitor.py",
    "signal-separation-monitor.py",
    "participation-surplus-monitor.py",
    "adversarial-allocation-auditor.py",
    "iterative-critique-convergence-monitor.py",
    "retrieval-saturation-monitor.py",
    "consensus-convergence-monitor.py",
    "entropy-fidelity-stability-monitor.py",
    "relaxation-gap-monitor.py",
    "sybil-risk-monitor.py",
    "regime-transition-monitor.py",
    "quantization-state-divergence-monitor.py",
    "belief-probe-evaluator.py",
]


def _pvalue(status: str) -> float:
    if status == "ALARM":
        return 0.01
    if status in ("ERROR", "TIMEOUT") or str(status).startswith("ERROR"):
        return 0.05
    return 1.0


def bh_fdr_filter(results: list, q: float = BH_Q) -> list:
    """Benjamini-Hochberg FDR. Adds bh_fdr_reject; never mutates status."""
    m = len(results)
    if m == 0:
        return results
    ranked = sorted(enumerate(results), key=lambda iv: _pvalue(iv[1].get("status", "")))
    largest_k = 0
    for rank, (_i, rec) in enumerate(ranked, 1):
        if _pvalue(rec.get("status", "")) <= (rank * q / m):
            largest_k = rank
    reject_idx = {ranked[k][0] for k in range(largest_k)}
    for i, rec in enumerate(results):
        rec["bh_fdr_reject"] = i in reject_idx
    return results


def _resolve(name: str) -> Path | None:
    for d in (SCRIPTS, _BASE_SCRIPTS, Path.home() / ".hermes" / "hermes-scripts"):
        p = d / name
        if p.is_file():
            return p
    return None


def _self_test() -> int:
    test = [{"script": f"s{i}", "status": "ALARM" if i < 3 else "OK"} for i in range(10)]
    snapshot = [dict(x) for x in test]
    out = bh_fdr_filter(test, q=0.10)
    assert all(x.get("status") == snapshot[i]["status"] for i, x in enumerate(out)), "status mutated"
    assert sum(1 for x in out if x.get("bh_fdr_reject")) == 3, "expected 3 BH rejects"
    assert all(x.get("status") == "ALARM" for x in out if x.get("bh_fdr_reject"))
    empty = bh_fdr_filter([], q=0.10)
    assert empty == []
    none = bh_fdr_filter([{"script": "s0", "status": "OK"} for _ in range(10)], q=0.10)
    assert sum(1 for x in none if x.get("bh_fdr_reject")) == 0
    assert all(x.get("status") == "OK" for x in none)
    print("BH self-test: PASS")
    return 0


def run_suite() -> int:
    now = datetime.now(UTC).isoformat()
    results = []
    for m in monitors:
        path = _resolve(m)
        if path is None:
            results.append({"script": m, "status": "MISSING"})
            continue
        try:
            r = subprocess.run(
                [sys.executable, str(path)],
                capture_output=True, text=True, timeout=30, check=False,
            )
            out = r.stdout.strip()
            err = r.stderr.strip()
            combined = out + "\n" + err if err else out
            alarm_line = any(
                _re.match(r"ALARM:\s+YES\b", line.strip(), _re.IGNORECASE) or
                line.strip().lower().startswith("alarm: yes") or
                "FRAGMENTED:        YES" in line or
                "SATURATED" in line
                for line in combined.splitlines()
            )
            no_alarm_line = any(
                _re.match(r"ALARM:\s+NO\b", line.strip(), _re.IGNORECASE) or
                line.strip().lower().startswith("alarm: no") or
                "insufficient data" in line
                for line in combined.splitlines()
            )
            alarm = alarm_line and not no_alarm_line
            status = "ALARM" if alarm else ("ERROR" if r.returncode != 0 else "OK")
            entry = {"script": m, "status": status, "output": combined[-400:]}
            if err and not alarm:
                entry["stderr"] = err[-200:]
            results.append(entry)
        except subprocess.TimeoutExpired:
            results.append({"script": m, "status": "TIMEOUT"})
        except Exception as e:
            results.append({"script": m, "status": f"ERROR: {e}"})

    bh_fdr_filter(results, q=BH_Q)
    alarms = [r for r in results if r["status"] == "ALARM"]
    errors = [r for r in results if r["status"] not in ("OK", "ALARM", "MISSING")]
    missing = [r for r in results if r["status"] == "MISSING"]
    ran = [r for r in results if r["status"] not in ("MISSING",)]
    bh_confirmed = [r for r in alarms if r.get("bh_fdr_reject")]
    bh_suppressed = [r for r in alarms if not r.get("bh_fdr_reject")]

    print(f"=== Hermes Monitor Suite — {now[:10]} ===")
    print(f"Ran: {len(ran)}  Missing: {len(missing)}  Alarms: {len(alarms)}  Errors: {len(errors)}")
    print(f"BH-FDR(q={BH_Q:.2f}): {len(bh_confirmed)} confirmed, {len(bh_suppressed)} suppressed")
    if bh_suppressed:
        for r in bh_suppressed:
            print(f"  suppressed: {r.get('script')}")
    print()
    for r in results:
        flag = " R" if r.get("bh_fdr_reject") else "  "
        print(f"  [{r['status']:<7}]{flag} {r['script']}")
    if alarms:
        print("\n--- ALARM DETAILS ---")
        for r in alarms:
            print(f"\n{r['script']}:")
            print(r.get("output", "")[:400])

    out_file = CACHE / "monitor-suite-latest.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    _out_tmp = out_file.with_suffix(".json.tmp")
    _out_tmp.write_text(json.dumps({"ts": now, "results": results, "bh_q": BH_Q}, indent=2))
    os.replace(str(_out_tmp), str(out_file))
    print(f"\nSummary: {out_file}")

    try:
        _alarm_summary = _hermes_root / "cache" / "alarm-summary.json"
        if _alarm_summary.exists():
            _asdata = json.loads(_alarm_summary.read_text())
            _count = _asdata.get("count", 0)
            if _count > 0:
                _alarms_list = _asdata.get("active_alarms", [])
                _high = sum(1 for a in _alarms_list if a.get("severity") == "HIGH")
                _med = sum(1 for a in _alarms_list if a.get("severity") == "MEDIUM")
                print(f"[monitor-suite] ALARMS: {_count} active (HIGH: {_high} MEDIUM: {_med})")
    except Exception:
        pass
    return 0


def main() -> None:
    if "--self-test" in sys.argv:
        try:
            sys.exit(_self_test())
        except Exception as exc:
            print(f"BH self-test: FAIL {exc}")
            sys.exit(1)
    try:
        sys.exit(run_suite())
    except Exception as e:
        print(json.dumps({"error": str(e), "ts": datetime.now(UTC).isoformat()}))
        sys.exit(1)


if __name__ == "__main__":
    main()
