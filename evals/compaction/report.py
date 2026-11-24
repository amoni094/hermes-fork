"""Render a compaction-eval scorecard as a terminal table + markdown.

Usage: python evals/compaction/report.py <results_dir>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def _fmt_cost(v) -> str:
    if v is None:
        return "-"
    try:
        return f"{float(v):.6f}"
    except (TypeError, ValueError):
        return "-"


def _print_table(headers, rows) -> str:
    widths = [max(len(headers[i]), *(len(r[i]) for r in rows)) if rows else len(headers[i])
              for i in range(len(headers))]
    line = "  ".join(h.ljust(widths[i]) for i, h in enumerate(headers))
    print(line)
    print("-" * len(line))
    for r in rows:
        print("  ".join(str(r[i]).ljust(widths[i]) for i in range(len(headers))))
    md = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    for r in rows:
        md.append("| " + " | ".join(r) + " |")
    return "\n".join(md)


def main():
    out_dir = Path(sys.argv[1])
    card = json.loads((out_dir / "scorecard.json").read_text(encoding="utf-8"))
    card.sort(key=lambda s: -(s.get("recall_pct") or 0))

    rows = []
    for s in card:
        before = s.get("before_tokens", 0)
        after = s.get("after_tokens", 0)
        kept = f"{100 * after / before:.1f}%" if before and after else "?"
        recall = s.get("recall_pct")
        recall_s = f"{recall}%" if recall is not None else "-"
        cost = s.get("total_cost_usd", s.get("cost_usd"))
        cpt = s.get("cost_per_task_usd")
        rows.append((
            s["policy"], recall_s, f"{before:,}", f"{after:,}" if after else "-",
            kept,
            str(s.get("compress_seconds", "-")),
            _fmt_cost(cost),
            _fmt_cost(cpt),
        ))

    headers = ("policy", "recall", "tokens before", "tokens after", "kept", "sec",
               "cost_usd", "cost_per_task_usd")
    md_parts = [_print_table(headers, rows)]

    stratum_rows = []
    for s in card:
        by_ws = s.get("by_where_stratum") or {}
        if not by_ws:
            continue
        for stratum, stats in by_ws.items():
            if isinstance(stats, dict):
                rp = stats.get("recall_pct")
                n = stats.get("n", 0)
            else:
                rp, n = stats, "?"
            rp_s = f"{rp}%" if rp is not None else "-"
            stratum_rows.append((s["policy"], str(stratum), rp_s, str(n)))
    if stratum_rows:
        print()
        print("by_where_stratum")
        sh = ("policy", "stratum", "recall", "n")
        md_parts.append("")
        md_parts.append("### by_where_stratum")
        md_parts.append(_print_table(sh, stratum_rows))

    (out_dir / "scorecard.md").write_text("\n".join(md_parts) + "\n", encoding="utf-8")
    print(f"\nmarkdown -> {out_dir}/scorecard.md")


if __name__ == "__main__":
    main()
