## Pitfall: critiquing a document that already has its own revision-history / changelog section

Some artifacts under review (design specs, governance frameworks) carry their own internal
record of prior adversarial passes — e.g. a "§N: what changed and why" or "traceability table"
section listing concerns raised in an earlier draft and how v-next resolved them. When this is
present, a fresh critique MUST explicitly scope itself to net-new findings only:

1. Read the existing changelog/traceability section in full before drafting a single finding.
2. Treat every concern already listed as resolved-and-cited there as OUT OF SCOPE for the new
   critique — do not re-raise it, even if your own research independently surfaces supporting
   citations for it. Re-litigating an already-fixed concern wastes the reviewer's and reader's
   time and makes the new critique look like it didn't read the document.
3. State the scope boundary explicitly in the critique's opening section ("this critique
   excludes concerns already resolved in §N; see net-new findings below") so a reader can verify
   you didn't just miss the existing table.
4. This is distinct from confirming a fix actually holds — if research surfaces evidence that a
   "resolved" item was resolved incorrectly or incompletely, that IS a legitimate new finding
   (flag it as "regression on previously-resolved concern," not as an original gap).

Skipping this step is the single most common way a critique of an iteratively-reviewed document
ends up hollow or redundant — the effort goes into re-deriving what the document's own authors
already fixed, instead of finding what's actually still missing.
