# Rendering Floor and Completion Contracts

> Offloaded from SKILL.md body (size > 600 lines). Load on demand via skill_view. Paper metrics and dated incident notes are not timeless — re-verify before citing as current.

## Rendering Floor: Surface-Agnostic Output Contract (Compound Engineering, 2026)

When a skill produces findings (review results, audit reports, research outputs), define
a **rendering floor** — a single surface-agnostic contract for how findings are presented
across every output mode, so that improving one surface cannot silently leave others behind.

### What the rendering floor specifies

1. **Decision-first field order** — the finding's verdict/action appears first, not last
2. **No opaque tokens in the decision block** — the decision must be human-readable without
   referencing an external lookup table
3. **Consistent severity vocabulary** — exactly HIGH / MEDIUM / LOW, declared once at the top,
   no compound labels (no MED-HIGH, LOW-MED, etc.)
4. **Every surface maps its own layout onto the floor** — interactive walkthrough, batch report,
   unattended pipeline envelope, and one-line preview are all different presentations of the
   same floor contract

### Per-surface adaptations (example)

| Surface | Layout | Fields shown |
|---------|--------|--------------|
| Interactive | Numbered list, each finding shown separately | All fields |
| Batch report | Table with verdict, severity, file:line, title | Summary fields |
| Pipeline envelope | JSON array `{id, severity, verdict, autofix_class}` | Machine-readable only |
| One-line preview | `[SEVERITY] title (file:line)` | Minimal |

**Cross-check:** when modifying how findings appear on ONE surface, verify all other
surfaces still conform to the rendering floor before shipping.

## Mandatory Completion Contracts (Compound Engineering, 2026)

Skills that include a handoff step are NOT complete until:
1. The handoff menu/options have been presented to the user, AND
2. The user's selected action has been executed (not just acknowledged)

Presenting the menu and stopping = incomplete. This applies to any skill that ends with
a "what next?" branch (review → commit? → open PR? → file issue?).

### Encoding a completion contract in a skill

Add an explicit completion contract section to skills that have post-task handoffs:

```
## Completion contract

This skill is complete ONLY when:
1. The [output artifact] has been written/produced
2. The post-completion menu has been presented (options: A, B, C)
3. The user's chosen option has been executed (not just presented)

Pipeline exception: when invoked with mode:pipeline or mode:return-to-caller,
skip steps 2-3 and return the structured envelope directly.
```

### Why this matters

Without an explicit completion contract, an agent can declare "done" after writing a
plan but before helping the user act on it. The contract closes the loop: the artifact
+ the action are both required. Pipeline callers get an exception so they don't block
waiting for user interaction that will never come.
