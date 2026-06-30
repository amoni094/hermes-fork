# Superpowers seed YAML contract note

Session-derived note for the class of Ouroboros plugins that prepare a downstream workflow handoff.

## Problem pattern

A plugin can successfully prepare artifacts and still recommend the wrong next command/artifact pair.

Observed class of mismatch:
- plugin prepared `handoff.md`, `provenance.json`, `evidence.json`, and a `seed.md`
- the recommended next step was a workflow run
- the workflow runner attempted to parse the seed as YAML
- the run failed before model/provider execution with a YAML parse error

## Durable fix pattern

For workflow-runner handoff artifacts:
- emit `seed.yaml`, not markdown prose `seed.md`
- generate a structured Seed document, not a human-readable heading/body note
- recommend the explicit command:
  - `ooo run workflow <seed.yaml>`

## Minimum seed checks

Before claiming the plugin handoff is correct:
1. open the generated seed artifact and confirm it is actual YAML
2. verify the seed contains contract fields expected by the installed Ouroboros version
3. run the workflow command once and confirm it gets past the seed-load phase
4. only after that investigate runtime/backend/provider failures

## Useful interpretation rule

If the failure happens at seed-load time, the problem is the artifact contract, not the provider backend.

## Dispatch/trust follow-up

After patching local plugin source, dispatched invocation may be refused because the installed plugin digest no longer matches the edited bytes.

Typical symptom:
- `plugin 'superpowers' bytes have changed since installation; refusing to invoke`

Treat this as a refresh requirement:
- reinstall the plugin from the edited local path
- re-grant the declared trust scopes
- then retest dispatched invocation
