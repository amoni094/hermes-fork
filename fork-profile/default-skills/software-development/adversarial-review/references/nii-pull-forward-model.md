# NII Pull-Forward Model: Formula Basis vs Table Basis

## The Failure Mode

Financial model documents for revenue-acceleration benefits (especially mortgage/lending AI)
frequently show a scenario table whose numbers don't match what the stated formula produces.
The table is internally consistent; the formula is written correctly; neither flags itself.
The mismatch is a hidden multiplier — typically an average loan life assumption that converts
annual origination volume into an outstanding book figure.

## Concrete Case (Aug 2026 — AU Bank Trust Deed AI)

### What the document said

Formula:
  Annual Revenue Acceleration =
    Annual New Loan Volume × Deed Review Proportion × Days Saved × Daily NIM Rate
  Daily NIM Rate = 1.75% / 365 = 0.004795% per day

Scenario table (central, mid-tier bank):
  AUD 3B deed-affected volume × 2 days × daily NIM → AUD 2.88M/year

### What the formula actually produces

  3,000,000,000 × 0.0175 / 365 × 2 = AUD 287,671/year  (~AUD 288K)

The table shows 10× the formula's output.

### The hidden multiplier

The table was computed on the *outstanding book*, not the annual origination cohort:

  Outstanding book = Annual New Originations × Average Loan Life
  = AUD 20B/yr × 15% deed rate × 10yr average life = AUD 30B

  AUD 30B × 0.0175 / 365 × 2 = AUD 2.877M  ✓ matches table

The 10-year average loan life assumption was never stated anywhere in the document.

### Why it's a valid model (once made explicit)

The economic logic IS correct: when you settle deed-affected loans N days earlier,
those loans remain on book for years. Each year you earn N extra days of NIM on the
entire *outstanding* stock of loans that settled early under the program — not just
the current year's new cohort. The annual steady-state benefit is:

  Annual orig × deed% × loan_life × (NIM/365) × days_saved

where loan_life and annual orig cancel conceptually (you're computing the outstanding
book), giving you the formula above applied to the outstanding book.

### The fix pattern

1. Rewrite the formula to state the outstanding-book basis explicitly:
   ```
   Deed-Affected Outstanding Book =
     Annual New Loan Volume × Deed Review Proportion × Average Loan Life (years)
   Annual Revenue Acceleration = Outstanding Book × Days Saved × Daily NIM Rate
   ```

2. Add an [ASSUMPTION] block for the loan-life value with:
   - The central estimate used (10yr)
   - The evidence base (RBA mortgage retention data, typical ranges 4-7yr refinancers,
     longer for loyal owner-occupiers)
   - The scaling rule: "A 5-year assumption halves the figures."

3. In any per-loan narrative section, use the outstanding book count, not just the
   annual cohort: "45,000 loans on book (4,500/yr × 10yr life) × 2 days × AUD 28.77 =
   approximately AUD 2.6M" — consistent with the dollar-based calculation.

## Python Verification Snippet

Use this in execute_code to check any financial scenario table:

```python
def verify_nii_table(scenarios, nim_bps=175, deed_pct=0.15, loan_life_yrs=10):
    """
    scenarios: list of (name, annual_orig_aud, days_saved, reported_aud)
    Returns list of (name, computed, reported, match, pct_diff)
    """
    nim = nim_bps / 10000  # convert bps to decimal
    daily_nim = nim / 365
    results = []
    for name, annual_orig, days, reported in scenarios:
        outstanding = annual_orig * deed_pct * loan_life_yrs
        computed = outstanding * daily_nim * days
        match = abs(computed - reported) / reported < 0.02  # 2% tolerance
        pct_diff = (computed - reported) / reported * 100
        results.append((name, computed, reported, match, pct_diff))
    return results

# Example: AU bank trust deed AI (Aug 2026)
scenarios = [
    ("Conservative mid", 20e9, 1, 1.44e6),
    ("Central mid",      20e9, 2, 2.88e6),
    ("Upper mid",        20e9, 4, 5.75e6),
    ("Central large",    50e9, 2, 7.19e6),
]
for name, computed, reported, match, pct in verify_nii_table(scenarios):
    status = "OK" if match else "MISMATCH"
    print(f"{status} {name}: computed={computed/1e6:.3f}M reported={reported/1e6:.3f}M diff={pct:.1f}%")
```

Expected output (all OK when loan_life_yrs=10):
```
OK Conservative mid: computed=1.438M reported=1.440M diff=-0.1%
OK Central mid:      computed=2.877M reported=2.880M diff=-0.1%
OK Upper mid:        computed=5.753M reported=5.750M diff=0.1%
OK Central large:    computed=7.192M reported=7.190M diff=0.0%
```

If any row shows MISMATCH, find the implied loan_life:
```python
def implied_loan_life(annual_orig, deed_pct, days, reported, nim_bps=175):
    nim = nim_bps / 10000
    daily_nim = nim / 365
    # reported = annual_orig * deed_pct * loan_life * daily_nim * days
    return reported / (annual_orig * deed_pct * daily_nim * days)

# All four rows above return 10.0 years when reported = table values
```

## Detection Checklist for Financial Model Reviews

1. For every scenario table row, compute the central case from the formula's stated inputs.
2. If computed ≠ table by more than 5%, find the multiplier:
   - Check for loan_life, cohort_years, portfolio_turnover, or similar terms in surrounding text.
   - Compute implied multiplier = table_value / formula_value — is it a round number (5, 10)?
3. If multiplier found: flag as missing [ASSUMPTION], not an error.
4. If no multiplier found and values are off by 10×: likely a units error (% applied as decimal).
5. Always cross-check per-loan narrative sections against the formula table:
   - "N apps × days × per-loan-day" should approximate the table entry for the same scenario.
   - If narrative uses annual cohort count but table uses outstanding book, the narrative
     will be ~10× low — flag the inconsistency and add the loan-life scaling note.
