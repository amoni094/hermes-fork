#!/usr/bin/python3
"""
legendre-state-compactor.py

Compresses long episodic session traces into k+1 Legendre polynomial
coefficients, enabling lossless (up to k) reconstruction and compact
representation for memory/context handoffs.

Math basis (functional_analysis / approximation_theory): any square-integrable
function on [-1,1] can be approximated arbitrarily well by a Legendre series.
For a session trace T = [t_0, t_1, ..., t_n] (tool-call sequence encoded as
numeric vector), the Legendre expansion f(x) = Σ_k c_k P_k(x) yields a
k+1-dimensional coefficient vector that captures k-th order structure.

For Hermes:
  - Session trace = sequence of tool-call type integers (vocabulary-encoded)
  - Compress: fit k+1 Legendre coefficients to the trace via least-squares
  - Reconstruct: evaluate Legendre series at n points to recover trace
  - Residual ||T - T_hat|| measures information loss
  - Use case: compact session summary for cron continuity / warm-start packets

This gives a principled alternative to truncation: instead of dropping the
tail of a long session, compress the entire trace into k+1 scalars that
preserve low-frequency structure (recurring tool patterns, phase transitions).
"""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from numpy.polynomial.legendre import legfit, legval

HOME      = Path.home()
SESSIONS  = HOME / ".hermes/sessions"
CACHE_DIR = HOME / ".hermes/cache/monitors"
OUT_FILE  = CACHE_DIR / "legendre-compaction.json"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _extract_tools(text: str) -> list[str]:
    tools: list[str] = []
    for line in text.split("\n"):
        try:
            obj = json.loads(line)
            if obj.get("role") == "assistant":
                for tc in obj.get("tool_calls", []):
                    if isinstance(tc, dict):
                        name = tc.get("function", {}).get("name", "")
                        if name:
                            tools.append(name)
        except Exception:
            pass
    return tools


def _encode_tools(tools: list[str]) -> tuple[np.ndarray, dict[str, int]]:
    """Encode tool names as integers, return array and vocabulary."""
    vocab: dict[str, int] = {}
    for t in tools:
        if t not in vocab:
            vocab[t] = len(vocab)
    encoded = np.array([vocab[t] for t in tools], dtype=float)
    return encoded, vocab


def _compress(trace: np.ndarray, k: int) -> tuple[np.ndarray, float]:
    """
    Fit k+1 Legendre coefficients to trace.
    Returns (coefficients, reconstruction_error).
    """
    n = len(trace)
    # Map indices to [-1, 1]
    x = np.linspace(-1, 1, n)
    # Fit Legendre polynomial of degree k
    coeffs = legfit(x, trace, k)
    # Reconstruct
    reconstructed = legval(x, coeffs)
    error = float(np.sqrt(np.mean((trace - reconstructed) ** 2)))
    return coeffs, error


def analyse_session(path: Path, k: int = 8) -> dict | None:
    try:
        text = path.read_text()
    except Exception:
        return None
    tools = _extract_tools(text)
    if len(tools) < k + 2:
        return None

    trace, vocab = _encode_tools(tools)
    coeffs, error = _compress(trace, k)

    # Compression ratio: k+1 floats vs n integers
    original_size  = len(tools)
    compressed_size = k + 1
    ratio = compressed_size / original_size

    return {
        "session":         path.stem[:20],
        "n_tools":         len(tools),
        "k_order":         k,
        "coefficients":    [round(float(c), 6) for c in coeffs],
        "recon_error":     round(error, 4),
        "compression_ratio": round(ratio, 4),
        "vocab_size":      len(vocab),
        "vocab":           {v: i for i, v in enumerate(vocab)},
    }


def run(dry_run: bool = False, k: int = 8, show_all: bool = False) -> None:
    now = datetime.now(timezone.utc).isoformat()
    session_files = sorted(SESSIONS.glob("*.jsonl"))

    results: list[dict] = []
    for sf in session_files:
        r = analyse_session(sf, k=k)
        if r:
            results.append(r)

    print(f"\n=== Legendre State Compactor — {now[:10]} ===")
    print(f"Sessions compressed: {len(results)}  (k={k} order)")

    if results:
        mean_ratio = sum(r["compression_ratio"] for r in results) / len(results)
        mean_error = sum(r["recon_error"] for r in results) / len(results)
        print(f"Mean compression ratio: {mean_ratio:.4f}  ({100*(1-mean_ratio):.1f}% size reduction)")
        print(f"Mean reconstruction error (RMSE): {mean_error:.4f}")

        top = sorted(results, key=lambda r: -r["n_tools"])
        for r in (top if show_all else top[:5]):
            print(f"\n  {r['session']}  n={r['n_tools']} tools  "
                  f"→ {r['k_order']+1} coeffs  "
                  f"ratio={r['compression_ratio']:.3f}  err={r['recon_error']:.4f}")
            print(f"  vocab ({r['vocab_size']}): {list(r['vocab'].keys())[:5]}")
            print(f"  c[0:3]: {r['coefficients'][:3]}")
    else:
        print("No sessions long enough to compress (need ≥ k+2 tool calls).")

    if not dry_run and results:
        OUT_FILE.write_text(json.dumps({
            "ts": now, "k": k,
            "sessions": len(results),
            "mean_ratio": round(sum(r["compression_ratio"] for r in results) / len(results), 4),
            "detail": results,
        }, indent=2))
        print(f"\nWritten: {OUT_FILE}")
    elif dry_run:
        print("(dry-run)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Legendre episodic state compactor")
    parser.add_argument("--k",       type=int, default=8, help="Legendre polynomial order (default 8)")
    parser.add_argument("--all",     action="store_true", help="Show all sessions")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run(dry_run=args.dry_run, k=args.k, show_all=args.all)


if __name__ == "__main__":
    main()
