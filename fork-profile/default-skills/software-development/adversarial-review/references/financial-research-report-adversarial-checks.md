# Financial Research Report — Adversarial Check Patterns
# Distilled from Aug 2026 multilingual trading strategy report review session

## Attack categories specific to multi-section financial research reports

### 1. Body vs Table Sharpe inconsistency (HIGH)
When a report has both prose sections and a summary comparison table, the same
strategy's Sharpe can differ between the two because the table was written at a
different time from the body, or rounding was applied inconsistently.

Detection pattern:
  - For every strategy in the comparison table, grep the body for all Sharpe mentions
  - Check body narrative Sharpe range matches table cell exactly (including [UV] flags)
  - Common drift: body says "0.91-1.21" but summary section (Part 5) says "0.91-1.12"

Concrete case (Aug 2026): Japan BB/RSI body correctly reported 0.91 (basic) up to 1.21
(quality-enhanced). Part 5 convergence summary cited 0.91-1.12, truncating the highest
figure. Fix: always copy the body range verbatim into any summary that references it.

### 2. Leveraged vs Unleveraged Sharpe conflation (HIGH)
Academic papers on trend-following and multi-asset strategies often report Sharpe ratios
under vol-targeting with leverage (e.g. 10% annualised vol target). These numbers
(e.g. 1.28 for Moskowitz et al. 2012) are NOT the implementable Sharpe for an individual
investor who cannot apply leverage.

Detection pattern:
  - Any time a Sharpe > 0.8 appears for a futures strategy, check the paper methodology
  - Look for: "vol target", "vol-scaled", "10% annual volatility", "leverage ratio"
  - If the strategy used vol targeting, the QuantConnect/paperswithbacktest unleveraged
    backtest is a better individual-investor reference (often 0.4-0.6 lower than paper figure)
  - The paperswithbacktest/awesome-systematic-trading repo is a useful cross-reference:
    it shows QuantConnect unleveraged Sharpe alongside the original paper Sharpe

Concrete case (Aug 2026): Moskowitz et al. (2012) report Sharpe ~1.28 (vol-targeted).
Unleveraged QuantConnect backtest in awesome-systematic-trading shows ~0.58. The report's
"clearly dominates" conclusion was overstated when using the institutional figure. Fix:
always show BOTH figures and state which is which; calibrate "vs Slava" comparisons
against the unleveraged figure, not the institutional one.

### 3. Citations in body missing from reference list (MEDIUM)
For any research report with inline prose citations + a separate reference list,
run a systematic sweep:

Detection pattern (executable):
  import re
  body = report_text[:reference_list_start_index]
  # Extract all author-year citations: "(AuthorName YYYY)" or "AuthorName et al. (YYYY)"
  cited = re.findall(r'(\w[\w\-]+(?:\s+et\s+al\.)?)[\s,\(]+((?:19|20)\d{2})', body)
  # Extract all reference list entries
  listed = re.findall(r'\[[\w\d]+\]\s+(\w[\w\-]+)', reference_section)
  # Compare; flag any cited_author not in listed_author set

Common missing-reference classes found in practice:
  - Methodological tools cited in passing (e.g. "Barroso & Santa-Clara 2015 practical rule")
  - Counter-evidence cited to contextualize findings (Sullivan et al. 1999 data-snooping)
  - Background knowledge cited by secondary source (Asness 2011 Japan momentum)
  - Data-source papers for comparison table entries (QuantConnect backtest sources)
  - Accruals attenuation papers (Green, Hand & Soliman 2011 for Sloan 1996 decay section)
  - Liquidity-adjusted PEAD papers (Chordia et al 2009 for drift calibration)

### 4. Broken/truncated URLs (MEDIUM)
URLs collected during web sweeps are often truncated by anti-bot redirects or copy errors.

Detection: regex for [...]  or ...  inside URL strings
  Pattern: `r'https?://[^\s]+\.\.\.[^\s]*'` or `r'semanticscholar\.org/paper/\.\.\.'`

Fix: replace with "[URL NOT CAPTURED at time of sweep]" — never leave a partial URL
that looks like it might work but doesn't.

### 5. CGT rate vs effective rate framing (MEDIUM)
In Australian tax context, "23.5% CGT rate" is incorrect — there is no 23.5% rate.
Correct framing: "effective rate of ~23.5% (47% marginal × 50% CGT discount for
assets held >12 months)."

Similarly: never say "47% CGT rate" — the rate is 47% marginal income tax applied
to the net capital gain (which may be discounted first).

### 6. Reference numbering drift after removals/additions (MEDIUM)
When dangling references are removed and new references are added, in-body citations
that use "[NN]" style numbering will point to wrong entries unless all references
are renumbered and every body citation updated simultaneously.

Detection:
  - After any reference list edit, grep body for "[NN]" style citations
  - Verify each "[NN]" maps to the correct entry in the current list
  - Special attention to "see ref NN" style mentions — these are easy to miss
    since they don't appear next to the author name they reference

Concrete case (Aug 2026): Asness (2011) was added as [37] but body cited
"[see ref 36]" (Ceta Research). Required separate patch pass.

### 7. Inverted Sharpe direction / anomaly count (HIGH) [Pass 2, Aug 2026]
When a subagent reports a comparative claim like "Model A explains 20/35 anomalies
vs 28/35 for Model B — A is markedly superior", verify the direction: if A < B, the
claim is inverted. This occurs when the subagent conflates counts from different papers,
test sets, or significance thresholds.

Detection:
  - Any claim "X explains N/M anomalies vs Y explains P/M, X is superior": verify N > P.
  - Similarly: "Sharpe of 0.3 for X clearly beats Y's Sharpe of 0.8" is inverted.

Fix: remove the specific comparative count if unverifiable from the abstract; retain
the directional claim with a verification note.

Concrete case (Aug 2026 Pass 2): q-factor section stated "q-model explains 20/35
anomalies vs 28/35 for FF3 — markedly superior". Since 20 < 28, this contradicts
the superiority claim. The count was removed; directional finding retained.

### 8. Model-version attribution: "X absorbs Y" claims (HIGH) [Pass 2, Aug 2026]
Claims that model X "absorbs" or "subsumes" factor Y are version-specific. A common
subagent error: attributing a result from a 2021 extended model to the 2015 original.

Detection:
  - "absorbs momentum", "subsumes value", "explains away anomaly" — check which
    year/version of the model is cited. Look for the exact paper year in the body.
  - Hou-Xue-Zhang family specifically:
    q4 (2015 RFS 28(3):650-705) does NOT absorb UMD momentum.
    q5 (2021 RFS 34(3):1260-1300, adds expected-growth factor) makes stronger claims.
    Citing 2015 for momentum absorption = wrong paper.

Fix: remove the absorption claim for the older paper, or add the newer paper citation.

### 9. Layered strategy vs individual factor decay — unreconciled numbers (MEDIUM) [Pass 2]
When a report has a layered-strategy net estimate (e.g. "5-8% pa net from accruals +
PEAD + analyst revision") AND a factor-decay finding (e.g. "momentum premium ~2% pa
today"), the reader perceives contradiction unless explicitly reconciled.

Detection: search for a factor-decay percentage and a layered-strategy percentage
within the same report; verify there is a reconciliation note near one of them.

Fix template — add near the decay finding:
  "NOTE: This [N]% pa refers to standalone [factor name] only. The [X-Y]% net estimate
   in [section] is the LAYERED strategy ([component A] + [component B] + ...), which
   are additive with separate decay profiles. Not contradictory — different layers."

Concrete case (Aug 2026 Pass 2): Lee (2025) showed momentum ~2% pa; Part 8 showed
layered PEAD+accruals+analyst revision at ~5-8% pa net. Added reconciliation note.

### 10. Combined reference entries (MEDIUM) [Pass 2, Aug 2026]
Two unrelated papers should never appear in a single reference entry
(e.g. "[38] Paper A (2012) / Paper B (2014)"). This occurs when a subagent conflates
two sources or couldn't resolve which was cited.

Detection: grep reference list for " / " within a single [NN] entry.
Fix: determine which paper is actually cited in the body (search body for the Sharpe value
or claim attributed to that reference number), then split into two entries. Update
body citations that used the old number.

### 11. Miscategorised paper type in a cluster table (MEDIUM) [Pass 2, Aug 2026]
When research is organized by cluster (ML/alt-data, factor, PEAD, etc.), a paper that
belongs to a different cluster can end up in the wrong section's table.

Detection: for each comparison table row, ask "is this paper's primary contribution
about [cluster topic]?" A factor-crowding paper in an ML cluster causes the reader to
infer ML is decaying, when actually the underlying mechanical factor is decaying.

Fix: add footnote asterisk [*] with a clarifying note, or move the paper to the
correct section.

## Standard check sequence for financial research reports

Run this sequence mechanically before declaring an adversarial pass complete:

1. Body vs table Sharpe: for each strategy row, grep body for Sharpe value and verify table cell
2. Leveraged Sharpe: for any futures strategy with Sharpe > 0.8, confirm vol-targeting disclosed
3. Citations sweep: for each cited author-year in body, confirm entry in reference list
4. Reference sweep: for each [NN] entry in reference list, confirm it is cited in body
5. URL check: grep for "..." inside any URL string
6. CGT framing: grep for "% CGT rate" — should only appear as "effective rate of X%"
7. Reference numbering: for any "see ref NN" citation, verify NN maps to the correct entry
8. Count drift: verify any count claims in summary sections match enumeration in body
9. Inverted comparison: for "A explains N/M vs B explains P/M — A is superior", verify N > P
10. Model vintage: for "absorbs momentum" claims, verify the cited paper year supports the claim
11. Layered vs standalone reconciliation: if factor-decay % and layered-strategy % coexist,
    verify there is an explicit reconciliation note
12. Combined reference entries: grep for " / " within reference entries; split if found
13. Cluster miscategorisation: for each comparison table row, verify paper type matches cluster label
