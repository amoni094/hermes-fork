# Claude routing matrix for Hermes delegation

Aspirational Claude-only pattern (not this instance):

- Orchestrator: Opus-class
- Workers: Sonnet-class
- Tiny extractors: Haiku-class

**Live map (2026-08-25):** load `claude-routing-hierarchy`. Do not treat the
commands below as something to re-apply.

- Parent: `grok-4.5` / xai (`model.default`)
- Leaves: `mistral-small-latest` / mistral (`delegation.model`)
- Intensive: new session `grok-4.6`
- Long context: new session `claude-opus-4-8`
- Adversarial: dedicated session `gpt-5.6-sol` / `custom:openai`

`delegate_task` has no per-call model. Empty `delegation.model` would inherit the
parent; this instance **sets** it, so children do not inherit Grok.

Dated snapshot this file used to claim (`model.default` and `delegation.model`
both `claude-sonnet-4-6`) is obsolete. If you need Claude workers, start a
Claude-pinned session or a temporary `delegation.model` override and restore
to `mistral-small-latest` immediately after spawn.
