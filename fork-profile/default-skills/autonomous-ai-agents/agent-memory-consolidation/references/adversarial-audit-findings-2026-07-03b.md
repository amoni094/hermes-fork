# Adversarial Memory Audit — Session Log 2026-07-03 (Passes 3–9)

Continuation of the same day's recursive audit. Passes 3–9 ran on refreshed surfaces
each time. Net reduction across the session: ~9280 → 7809 bytes total (-16%).
MEMORY.md alone: 1,818 → 1,435 bytes. CTX-now: ~1,050 → 473 bytes.

## Pass 3 Findings

| ID | Sev | Surface | Issue | Fix |
|---|---|---|---|---|
| STRUCT-A | HIGH | CTX-systems | LLM routing block still present as a section (pointer was added but section header remained) | Removed section entirely; pointer-in-Memory Stack is enough |
| DUP-A | HIGH | CTX-now | Graphiti temperature open loop listed as open item | Removed; maintenance note (permanent gap, not completable) |
| STALE-A | MEDIUM | CTX-projects | Graphiti MCP Integration still in Active despite being completed infra | Moved to Completed |
| STRUCT-B | MEDIUM | CTX-now | last-reviewed stale (2026-07-02) | Updated to 2026-07-03 on all CTX files |
| DUP-B | LOW | MEMORY.md | Ollama wording "embeddings only" vs CTX-systems "not in routing chain" | Clarified MEMORY.md to match; acceptable two-level pattern |

## Pass 4 Findings (13 findings, larger refactor pass)

| ID | Sev | Surface | Issue | Fix |
|---|---|---|---|---|
| DUP-A | HIGH | MEMORY.md | Graphiti MCP detail (service name, URL) in MEMORY.md stub and CTX-systems Memory Stack | Removed from MEMORY.md stub; CTX-systems authoritative |
| DUP-B | HIGH | MEMORY.md | Graphiti temperature=None patch note crept back into MEMORY.md via prior fix | Removed; Maintenance Notes in CTX-systems only |
| MISS-A | HIGH | MEMORY.md | Cron line still named 3 jobs (repeated after Pass 3) | Compressed to pointer |
| STRUCT-A | MEDIUM | CTX-now | Current Phase still decaying into session log | Reframed as stable state snapshot (second application of same fix) |
| STRUCT-B | MEDIUM | CTX-now | Reasoning convention still in Current Focus despite Move in Pass 2 | Confirmed removed; moved to CTX-systems |
| DUP-C | MEDIUM | CTX-now | Self-referential "CTX files due for review" in Open Loops | Removed |
| DUP-D | MEDIUM | CTX-now | Recent Decisions still had decisions >7 days old | Cleared |
| STRUCT-C | MEDIUM | CTX-systems | Active MCP Servers section duplicating Memory Stack | Merged; section removed |
| STALE-A | MEDIUM | CTX-projects | Fable-5 and Ouroboros still in Active | Moved to Completed |
| STRUCT-D | LOW | CTX-systems | Ollama overlap | Acceptable — no change |
| STALE-B | LOW | CTX-projects | 30-day archive policy missing from Completed | Added |
| STRUCT-E | LOW | MEMORY.md | Agent design principle in prompt-resident memory | Removed |
| STRUCT-F | LOW | MEMORY.md | Guardian API key config in always-injected memory | Moved to CTX-systems Local Services |

Note: MEMORY.md Pass 4 patches triggered `? on memory` (tool returned ambiguous result) twice.
Verified actual result by `cat`-ing the file directly. Always verify memory writes with
`cat ~/.hermes/memories/MEMORY.md` not read_file (dedup suppression) after batch operations.

## Pass 5 Findings

| ID | Sev | Surface | Issue | Fix |
|---|---|---|---|---|
| INAC-A | MEDIUM | MEMORY.md | Cron line still listed 3 explicit job names despite prior compression | Re-compressed to pointer only |
| STRUCT-B | MEDIUM | CTX-projects | Siegward entry in Active section labelled "inactive" — contradiction | Left in Active pending user confirmation (Siegward) |
| STRUCT-A | LOW | CTX-now | "Add ## Open Loops" meta-instruction embedded as bullet under Current State | Moved to Staleness Signal section |
| DUP-A | LOW | CTX-systems | FalkorDB container detail in Memory Stack AND Maintenance Notes | Removed from Memory Stack; Maintenance Notes authoritative |
| VERIFY-A | LOW | CTX-systems | Graphiti search example uses `group_ids` — parameter name unverified | Added "verify param name on first use" note inline |

## Pass 6 Findings

| ID | Sev | Surface | Issue | Fix |
|---|---|---|---|---|
| STRUCT-B | MEDIUM | CTX-projects | Siegward still in Active / Recent section despite "inactive" status | Moved to On Hold / Completed |
| DUP-A | LOW | CTX-systems | "backed by FalkorDB" in both Memory Stack and Maintenance Notes | Removed from Memory Stack |
| STRUCT-A | LOW | CTX-now | Open Loops / Recent Decisions meta-instruction misplaced | Moved to Staleness Signal |
| VERIFY-A | LOW | CTX-systems | Graphiti group_ids param (repeat) | Added inline verify note |
| Bonus LOW | CTX-systems | "Canonical durable memory" line in Hermes Agent section redundant with MEMORY.md header | Removed line |
| Bonus LOW | CTX-systems | "No sudo; system layer is immutable" less actionable than toolbox/flatpak | Replaced with "use toolbox/flatpak for host tools" |
| Bonus LOW | CTX-systems | LLM Routing section header still present despite content removed | Removed section entirely |

## Pass 7 Findings

| ID | Sev | Surface | Issue | Fix |
|---|---|---|---|---|
| STALE-A | HIGH | CTX-projects | Siegward inactive since 2026-05-25 = 39 days, exceeds 30-day retention policy | Removed from CTX-projects; vault note [[Siegward Daily Memory Dashboard]] is the archive |
| CLARITY-A | LOW | MEMORY.md | "reasoning=hermes-reasoning" reads as config key not group name | Changed to "reasoning group: hermes-reasoning" with semicolon |
| VERIFY-A | LOW | CTX-systems | group_ids param (third occurrence) | Noted |

## Pass 8 Findings

| ID | Sev | Surface | Issue | Fix |
|---|---|---|---|---|
| STRUCT-B | (resolved) | CTX-projects | Siegward in Completed but still present at 39 days | Removed entirely; vault-archived |
| CLARITY-A | LOW | MEMORY.md | Graphiti clarity fix | Applied |
| VERIFY-A | LOW | CTX-systems | Graphiti search param | Updated example to list syntax + inline verify note |

## Pass 9 — Clean pass

0 HIGH, 0 MEDIUM, 0 LOW. Audit complete.

---

## New Heuristics Validated This Session (Passes 3–9)

### 1. Retention policy expiry is a HIGH finding, not a LOW
When a Completed entry is past its stated retention period (e.g. 30 days), it becomes a
HIGH finding even though individual project entries read as LOW. The reason: the policy
was explicitly added by the audit; if the agent lets the first entry immediately violate it,
the policy is worthless.

### 2. Repeated fixes signal structural resistance — patch the template
DUP-A (MEMORY.md Graphiti stub) and STRUCT-A (CTX-now Current Phase log) were
re-found in Pass 4 despite being fixed in Pass 2. This means the fix didn't hold across
the context boundary. The right response: add the anti-pattern explicitly to the SKILL.md
finding table (as was done) AND ensure the fix description includes the exact text to write,
not just the principle. Vague fix descriptions produce vague patches that drift back.

### 3. `cat` beats read_file for memory verification
After any `memory(operations=[...])` call that returns `? on memory` or is otherwise
ambiguous, verify with `cat ~/.hermes/memories/MEMORY.md` via terminal, not read_file.
read_file has dedup suppression that returns "unchanged since last read" and withholds
content when nothing changed since the last call.

### 4. Empty section shells are worse than no section
After gutting a section of its content (e.g. Recent Decisions: "Nothing to record"),
an empty section with a placeholder is structurally noisier than no section. Prefer
removing the section header entirely and adding a one-line instruction in Staleness Signal:
"Add ## Open Loops / ## Recent Decisions only when content exists." This was validated
in Passes 5–6 and is now in the skill finding table.

### 5. Inactive project in Active section = MEDIUM (not LOW)
An entry marked "inactive" but sitting in "Active / Recent" is a structural contradiction
that will mislead any agent reading the section as its current workload. Categorize as
MEDIUM immediately; do not wait for the user to confirm inactivity. If inactive for >30 days,
immediately apply the retention policy (HIGH).

### 6. CTX-systems redundancy: `group_ids` vs `group_id`
Graphiti MCP tool actual parameter name was unverified. When writing search examples for
any MCP tool in CTX-systems, add "verify param name on first use" inline rather than
asserting the parameter name as fact. This prevents outdated docs from causing silent
wrong-group queries.
