#!/usr/bin/env python3
"""
contract-dfa-checker.py — ContrAgent DFA online/offline checker.

Based on: ContrAgent (arXiv:2609.18128) — symbolic temporal supervision via LTLf contracts.
Replaces stochastic LLM judges with deterministic DFA-based verdicts.

Usage:
  python3 contract-dfa-checker.py --trace session.jsonl        # offline trace check
  python3 contract-dfa-checker.py --tool TOOL_NAME [--cmd CMD] # online pre-flight check
  python3 contract-dfa-checker.py --list                       # list loaded contracts
"""
import argparse, json, os, pathlib, sys

HERMES_HOME = pathlib.Path(os.environ.get("HERMES_HOME", str(pathlib.Path.home() / ".hermes")))
CONTRACTS_PATH = HERMES_HOME / "config" / "contracts.json"


def load_contracts() -> list:
    if not CONTRACTS_PATH.exists():
        return []
    try:
        data = json.loads(CONTRACTS_PATH.read_text())
        return data.get("contracts", [])
    except Exception as e:
        print(f"[contract-dfa] load error: {e}", file=sys.stderr)
        return []


def classify_tool(tool_name: str, cmd: str, contract: dict) -> str:
    """Classify a tool call into a DFA symbol for this contract."""
    symbols = contract.get("tool_symbols", {})
    for sym, tools in symbols.items():
        for t in tools:
            if t in tool_name or (cmd and t in cmd):
                return sym
    return "safe_tool"


def run_dfa(dfa: dict, tool_sequence: list) -> tuple:
    """Run DFA on tool symbols. Returns (final_state, accepted)."""
    state = dfa["initial"]
    for sym in tool_sequence:
        trans = dfa["transitions"].get(state, {})
        if sym in trans:
            state = trans[sym]
        elif "other" in trans:
            state = trans["other"]
        if state in dfa.get("reject", []):
            return state, False
    return state, state in dfa.get("accept", [state])


def check_trace(trace_path: pathlib.Path) -> dict:
    """Check a session JSONL trace against all contracts."""
    contracts = load_contracts()
    if not contracts:
        return {"verdict": "skip", "reason": "no contracts loaded"}

    try:
        lines = trace_path.read_text(errors="replace").splitlines()
    except OSError as e:
        return {"verdict": "error", "reason": str(e)}

    tool_events = []
    for line in lines:
        try:
            row = json.loads(line)
        except Exception:
            continue
        if row.get("role") in ("tool", "tool_call") or row.get("type") == "tool_use":
            tool_name = row.get("name", row.get("tool_name", ""))
            content = str(row.get("input", row.get("content", "")))
            if tool_name:
                tool_events.append({"tool": tool_name, "content": content})

    results = []
    for contract in contracts:
        symbols = [classify_tool(e["tool"], e["content"], contract) for e in tool_events]
        final_state, accepted = run_dfa(contract["dfa"], symbols)
        results.append({
            "contract_id": contract["id"],
            "name": contract["name"],
            "accepted": accepted,
            "final_state": final_state,
        })

    violations = [r for r in results if not r["accepted"]]
    return {
        "verdict": "pass" if not violations else "fail",
        "contracts_checked": len(results),
        "violations": violations,
    }


def check_tool_online(tool_name: str, cmd: str = "") -> dict:
    """Online pre-flight: check if executing tool_name/cmd would violate any contract."""
    contracts = load_contracts()
    blocks = []
    for contract in contracts:
        sym = classify_tool(tool_name, cmd, contract)
        for state_name, transitions in contract["dfa"]["transitions"].items():
            next_state = transitions.get(sym, state_name)
            if next_state in contract["dfa"].get("reject", []):
                blocks.append({
                    "contract_id": contract["id"],
                    "name": contract["name"],
                    "symbol": sym,
                    "blocked_from_state": state_name,
                })
    return {
        "tool": tool_name,
        "blocked": len(blocks) > 0,
        "blocks": blocks,
    }


def cmd_list() -> None:
    contracts = load_contracts()
    if not contracts:
        print("No contracts loaded.")
        return
    for c in contracts:
        print(f"  [{c['id']}] {c['name']}: {c.get('description', '')[:80]}")


def main() -> None:
    parser = argparse.ArgumentParser(description="ContrAgent DFA contract checker")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--trace", metavar="JSONL", help="Check session JSONL trace offline")
    group.add_argument("--tool", metavar="TOOL", help="Online pre-flight check for a tool call")
    group.add_argument("--list", action="store_true", help="List loaded contracts")
    parser.add_argument("--cmd", default="", help="Command string for --tool check")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    if args.list:
        cmd_list()
    elif args.trace:
        result = check_trace(pathlib.Path(args.trace))
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            v = result.get("verdict", "?")
            print(f"Verdict: {v} ({result.get('contracts_checked', 0)} contracts checked)")
            for viol in result.get("violations", []):
                print(f"  VIOLATION [{viol['contract_id']}] {viol['name']}: "
                      f"final_state={viol['final_state']}")
        sys.exit(0 if result.get("verdict") == "pass" else 1)
    elif args.tool:
        result = check_tool_online(args.tool, args.cmd)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            if result["blocked"]:
                print(f"BLOCKED: {args.tool}")
                for b in result["blocks"]:
                    print(f"  [{b['contract_id']}] {b['name']}: "
                          f"{b['symbol']} from {b['blocked_from_state']}")
            else:
                print(f"ALLOW: {args.tool}")
        sys.exit(1 if result["blocked"] else 0)


if __name__ == "__main__":
    main()
