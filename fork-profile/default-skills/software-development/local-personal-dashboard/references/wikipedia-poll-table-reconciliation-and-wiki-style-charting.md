# Wikipedia poll-table reconciliation and wiki-style charting

Use this when a polling dashboard is sourced from the Wikipedia federal-election polling table and the displayed numbers or chart do not match the visible source.

Key lessons from this session
- The table can mix:
  - a single aggregate Coalition cell with `colspan=3`
  - separate LIB / LNP / NAT cells
  - a follow-on 2PP row for some pollsters
- Naive full expansion of every `colspan` can misalign meanings across primary and 2PP lanes.
- Safer pattern:
  1. read the first five metadata cells (`date`, `pollster`, `client`, `mode`, `sample`)
  2. treat the remaining cells as logical slots, not just expanded columns
  3. fill the eight primary slots first
  4. if the Coalition position arrives as one `colspan=3` cell, treat that value as the Coalition aggregate
  5. only sum LIB/LNP/NAT when they are truly separate cells
  6. send any remaining cell-span overflow into the trailing 2PP slots
- Always compare at least a few generated rows against the literal visible source rows before trusting the artifact.

Concrete row semantics observed
- Roy Morgan rows looked like:
  - `27 | 15 | — | 2.5 | 13.5 | 31.5 | 10.5`
  - meaning: ALP 27, LIB 15, LNP n/a, NAT 2.5, Greens 13.5, One Nation 31.5, IND/OTH 10.5 combined
  - Coalition primary should therefore be 17.5, not 31.5
- DemosAU / Resolve / Newspoll rows used an aggregate Coalition cell:
  - `18%` or `20%` with `colspan=3`
  - this should map directly to Coalition primary, not be redistributed later
- Some pollsters used a second row for 2PP. The parser must not assume the first row contains every 2PP value.

Chart-shape lesson
- After the numbers reconcile, make the chart more like the wiki source by preferring:
  - line-only rendering or at least very quiet markers
  - a wide inner plot area
  - light y-axis labels
  - less dashboard chrome
- Styling must follow data correctness, not hide parser mistakes.
