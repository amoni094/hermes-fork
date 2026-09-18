## Metric-Identity Verification (the dominant failure mode)

The most common citation error is NOT a wrong arXiv ID — it is a correct ID with the wrong quantity extracted:
- **Prevalence vs precision**: "61.2% of skills have defects" vs "SkillSpec achieves 61.2% precision"
- **Eval type vs production**: "64.4% cost reduction" vs "Type II vs Type III estimated inference cost"
- **Post-trained vs scaffold-only**: "72.6% SWE-bench" vs "requires two RL post-trained agents"
- **Rank correlation vs gain**: "rho=0.9747" ≠ a percentage improvement

**Required check for every numeric claim in a research integration:**
1. Find the exact table/figure in the abstract or paper where the number appears
2. Quote the metric NAME from the paper (e.g. "Strict Success Rate", "F1 precision", "Spearman rho")
3. State the experimental conditions (e.g. "post-trained Qwen-2.5-72B only", "held-out eval set", "Type II vs Type III")
4. Only then embed in the skill or config doc

This check catches errors that arXiv ID + title verification cannot catch.



Add these checks when adversarially reviewing any work that integrates research papers into
skills, config, or scripts (e.g. post-sweep implementation passes).

## Citation accuracy
- Fetch arXiv abstract directly (web_extract https://arxiv.org/abs/<ID>)
  Verify: title matches, key finding matches the claimed result, and numeric figures match
  (e.g. "64.4% cheaper loops" vs "24.69% SSR with rho=0.9747")
- Do NOT trust self-reported findings that paraphrase arXiv without checking the source

## Config wiring
- For every new YAML key proposed, search the Hermes source or dispatcher for that key
  (`search_files(pattern='key_name', path='~/.hermes/hermes-agent/', target='content')`)
- If not found in source: label the config as aspirational documentation, not active feature
- Never assume a config key does something just because Hermes is config-driven

## Script existence
- For every script path referenced in a skill, verify:
  1. File exists: `ls -la <path>`
  2. Non-zero bytes: size > 0
  3. Parses as valid Python: `python3 -c "import ast; ast.parse(open('<path>').read())"`
  4. If skill docs say 'run X', X must pass all three checks
- 0-byte scripts (root-owned dir write failure pattern) silently exit 0 -- this is CRITICAL

## Side-effect safety
- Any smoke_test, auto-run, or install-time execution of a script must be sandboxed
- Scripts with network calls, file writes, git commits, or email sends MUST NOT run
  automatically unless behind tool-sandbox.sh or equivalent
- Verify `block_on_fail: false` does not silently enable side-effect execution

## Aspirational vs active
- Label clearly: "cron pattern (aspirational -- no cron configured)"
- Label clearly: "future upgrade path -- not yet implemented"
- Do NOT let aspirational patterns appear as active operational procedures
- Check that any 'cron' claim has an entry in `cronjob_manage action=list`

## The governance decay self-test
- After any skill update pass, verify the updated skills themselves don't have
  the Governance Decay problem: constraints added in this session to skill prose
  will be forgotten at next compaction if they aren't in a pinned location
- Skills survive compaction (they're files); MEMORY.md constraints survive only if
  the compressor respects protect_last_n or the fact is in the system prompt

## Inference-Time Constraint + Proxy Implementation Review

When reviewing any implementation derived from a cognitive-science, information-theory,
or ML paper that is being applied to an agent runtime (e.g. Hermes compressor patches,
memory policy changes, scoring function tweaks), run these additional attack vectors:

### A. Inference-time feasibility gate
Check: does the paper's algorithm require logits, gradients, attention weights, KV cache
access, or a training loop? If yes, the full algorithm CANNOT be implemented at inference
time. Any claim to "implement ECS" or "implement IB" without these is false.
Required labeling: "proxy inspired by" or "heuristic informed by" — never "implements".
Flag any skill or comment that drops the proxy qualifier.

### B. Proxy overclaim scan
For each paper cited as justification for an agent behavior change:
1. State what the paper's actual algorithm requires (the full method)
2. State what the proxy actually computes (the Hermes approximation)
3. Confirm the proxy is labeled as a proxy in the implementation comment AND in any
   skill that documents it. A proxy without a label is an overclaim.
Example of correct labeling (context_compressor.py):
  "ACON-informed" not "ACON implemented"; "VISTA-inspired" not "VISTA".

### C. Over-eviction risk check
New preamble rules, demotion criteria, or KEEP/DROP instructions interact additively with
existing rules. Before shipping any new eviction criterion, check:
- Does the new rule overlap with an existing rule and create a double-eviction trigger?
  (E.g. "omit confirmations" + existing NOISE tag for confirmations = same class triggered twice)
- Could the new rule's wording catch turns that are nominally in the DROP category but
  contain verbatim identifiers (file paths, commit SHAs, error codes) that should survive?
  Rule: a DROP instruction must never override a VERBATIM PRESERVATION RULE.
- Is there a plausible false positive where a turn looks like a "confirmation" or
  "repeated search" but actually carries the only copy of a critical artifact?
Mitigation: add a VERBATIM OVERRIDE clause to any new eviction rule. Pattern:
  "Omit turns that merely confirmed X — EXCEPT when the confirmation message also
  contains a file path, URL, session ID, or exact error message that has not yet
  been echoed elsewhere in the summary."

### D. Internal consistency check
Before merging a new rule into the summarizer preamble or a compaction skill:
1. List all existing rules in the same preamble/skill that affect the same category
   (KEEP, DROP, VERBATIM, causal direction)
2. Apply the new rule and the existing rules to the same hypothetical turn. Do they
   produce the same verdict? If they produce different verdicts, one rule dominates or
   they conflict — the conflict must be resolved by explicit priority ordering.
3. Check that VERBATIM PRESERVATION RULES always win against DROP rules. State this
   priority explicitly in the preamble if not already present.

### E. Source paper verification (signal-noise domain)
For papers in the context compression / agent memory domain, the following common
misattributions have been observed:
- Citing ECS (arXiv:2601.11585) as justification for a keyword-similarity rule: ECS is
  explicitly about distribution shift, not keyword overlap — the opposite.
- Citing SelfCompact (arXiv:2606.23525) for a token-threshold trigger: SelfCompact is
  about task-phase awareness (sub-task resolved vs mid-derivation), not absolute token count.
- Citing STALE (arXiv:2605.06527) for TTL-based expiry: STALE is about semantic staleness
  (world changed, fact still within TTL), not TTL expiry which Hindsight already handles.
- Citing TEPA (arXiv:2608.07429) for any automated revocation: TEPA requires a full
  enumerate-all + conflict-detection loop, not a manual guideline.
Verification: fetch the abstract and confirm the paper's mechanism matches the claimed use.
