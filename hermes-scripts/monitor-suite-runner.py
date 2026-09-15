#!/usr/bin/python3
"""
monitor-suite-runner.py

Runs all Hermes monitoring scripts and prints a consolidated summary.
Designed for cron execution (no_agent=true).
"""
import subprocess, sys, json
from pathlib import Path
from datetime import datetime, timezone

SCRIPTS = Path.home() / ".hermes/scripts"
CACHE   = Path.home() / ".hermes/cache/monitors"

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
    "retrieval-saturation-monitor.py",
    "consensus-convergence-monitor.py",
    "entropy-fidelity-stability-monitor.py",
    "relaxation-gap-monitor.py",
    "sybil-risk-monitor.py",
    "regime-transition-monitor.py",
    "quantization-state-divergence-monitor.py",
    "belief-probe-evaluator.py",
    # Analysis/utility (run-on-demand, not daily monitors)
]

now = datetime.now(timezone.utc).isoformat()
results = []
for m in monitors:
    path = SCRIPTS / m
    if not path.exists():
        results.append({"script": m, "status": "MISSING"})
        continue
    try:
        r = subprocess.run(
            [sys.executable, str(path)],
            capture_output=True, text=True, timeout=30
        )
        out = r.stdout.strip()
        # Detect alarms via exit code (scripts exit 1 on alarm) or explicit ALARM line
        import re as _re
        alarm_line = any(
            _re.match(r"ALARM:\s+YES\b", line.strip(), _re.IGNORECASE) or
            line.strip().lower().startswith("alarm: yes") or
            "FRAGMENTED:        YES" in line or
            "SATURATED" in line
            for line in out.splitlines()
        )
        no_alarm_line = any(
            _re.match(r"ALARM:\s+NO\b", line.strip(), _re.IGNORECASE) or
            line.strip().lower().startswith("alarm: no") or
            "insufficient data" in line
            for line in out.splitlines()
        )
        # Alarm iff: explicit alarm keyword found AND no "no/insufficient" override
        alarm = alarm_line and not no_alarm_line
        status = "ALARM" if alarm else ("ERROR" if r.returncode != 0 else "OK")
        results.append({"script": m, "status": status, "output": out[-300:]})
    except subprocess.TimeoutExpired:
        results.append({"script": m, "status": "TIMEOUT"})
    except Exception as e:
        results.append({"script": m, "status": f"ERROR: {e}"})

# Print summary
alarms = [r for r in results if r["status"] == "ALARM"]
errors = [r for r in results if r["status"] not in ("OK", "ALARM", "MISSING")]

print(f"=== Hermes Monitor Suite — {now[:10]} ===")
print(f"Ran: {len(results)}  Alarms: {len(alarms)}  Errors: {len(errors)}")
print()
for r in results:
    print(f"  [{r['status']:<7}] {r['script']}")
if alarms:
    print("\n--- ALARM DETAILS ---")
    for r in alarms:
        print(f"\n{r['script']}:")
        print(r.get("output","")[:400])

# Write summary JSON
out_file = CACHE / "monitor-suite-latest.json"
out_file.parent.mkdir(parents=True, exist_ok=True)
out_file.write_text(json.dumps({"ts": now, "results": results}, indent=2))
print(f"\nSummary: {out_file}")
