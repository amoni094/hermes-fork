# Large Corpus Synthesis Pattern
## Added: August 2026 (Vervaeke meaning crisis 50-episode synthesis)

Use when the task is: synthesize a large body of source material (50+ episodes, 30+
papers, a multi-volume series) where direct sequential fetching would overflow context.

---

## Pattern

### 1. Partition by semantic arc, not by count

Split the corpus into thematic clusters that have internal coherence:
- Historical/diagnostic arc
- Technical/theoretical arc
- Constructive/proposal arc
- Responses/critics arc

Arbitrary N-episode chunks force each subagent to contextualize across thematic
discontinuities. Arc partitions let each subagent build internal coherence naturally.

### 2. Dispatch 3 subagents in parallel (the confirmed limit for this environment)

Each subagent gets:
- Its URL/source list
- The exact output schema you need (don't let it invent structure)
- An explicit call-out for any section that requires special depth
  e.g. "Pay special attention to episodes 36-50 where the constructive proposal
  takes shape — extract SPECIFIC recommendations, not just descriptions."
- The expected output artifact (concatenated summaries, JSON, etc.)

### 3. CRITICAL: Read full output files before synthesizing

Subagent outputs are truncated in the parent context window — the inline delegation
result shows only head + tail. The middle is silently cut.

**Every time a subagent finishes:**
1. Look for the footer: `Full subagent output saved to: /path/file.txt`
2. Call `read_file(path=..., limit=2000)` on that path
3. For files >~44KB, use `offset` to page through the rest
4. Only synthesize after you have the full content of all three outputs

**Do not synthesize from the inline truncated result.** The middle sections — often
the most content-dense — are what get cut. For a 50-episode synthesis the middle
section is typically the theoretical core or the constructive proposal, i.e. exactly
what matters most.

### 4. Run adversarial pass on the synthesis, not the subagent outputs

The adversarial pass should target the final synthesis, not individual subagent summaries.
Load `references/philosophy-intellectual-history-adversarial-synthesis.md` from the
`adversarial-review` skill for philosophy/intellectual-history work.

For philosophy syntheses, the five key attack vectors are:
1. Genealogy-as-causation conflation
2. Romanticization of premodern life
3. Source-authority laundering
4. Coherence-vs-correspondence conflation
5. Institutional feasibility gap

### 5. Integrate external critique as a second-phase delegation

If the user then asks for external academic criticism integrated into the synthesis,
dispatch a second parallel batch targeting:
- Cognitive science critiques (is the theory testable?)
- Philosophical critiques (analytic pushback)
- Historical/genealogical critiques (is the narrative too selective?)
- Religious/theological critiques (what do tradition-insiders say?)
- Sociological/political critiques (is this a material problem, not cognitive?)
- Internal consistency critiques (does the framework contradict itself?)

Run a second adversarial pass after integration — the integration itself introduces
new failure modes (new text contradicting old, count drift, new HIGH findings not
reflected in totals).

---

## Worked example: Vervaeke AMTMC (Aug 2026)

- 50 episodes split into 3 arcs: eps 1-10 / eps 11-25 / eps 26-50
- 3 parallel subagents, each given the 4-part schema + arc-specific instructions
- Eps 26-50 subagent explicitly told: "extract SPECIFIC recommendations for the
  constructive proposal" — this produced a usable table; the generic instruction
  would have produced only descriptions
- All three outputs read via read_file before synthesis — the middle sections
  (cog-sci arc eps 27-35, and wisdom arc eps 40-45) would have been cut
- Adversarial pass ran three attacks: RR circularity, institutional infeasibility,
  genealogy selectivity — all partially confirmed, none collapsed the synthesis
- Second batch of 2 subagents dispatched for external criticism research, then
  integrated into updated synthesis
