# Plugin Patch: Embedding Keys Stripped from hermes.env (2026-08-11)

## Problem

Hindsight daemon startup was intermittent. Every new Hermes session triggered an
unnecessary daemon restart, and on some restarts the daemon started without embedding
credentials, silently falling back to local/384d embeddings.

## Root cause (two-part)

### Part A — `_build_embedded_profile_env()` doesn't forward EMBEDDINGS keys

`~/.hermes/hermes-agent/plugins/memory/hindsight/__init__.py`
`_build_embedded_profile_env(config)` built `hermes.env` from a hardcoded set of
LLM/log/idle_timeout keys. It never iterated config.json for keys with the
`HINDSIGHT_API_EMBEDDINGS_` prefix, even though those keys were present in config.json.

Result: every call to `_materialize_embedded_profile_env()` overwrote `hermes.env`
with only 4-5 keys, stripping the 4 EMBEDDINGS keys that had been written manually.

### Part B — `config_changed` loop triggered on every session start

`_start_daemon()` (around line 1672) compared the saved `hermes.env` against the
freshly built env:

```python
expected_env = _build_embedded_profile_env(self._config)  # 4-5 keys
saved = _load_simple_env(profile_env)                      # 9 keys (had EMBEDDINGS)
config_changed = saved != expected_env                     # always True
```

Because the saved file had 9 keys but the built env had only 4-5, `config_changed`
was True on every session start. This caused:
1. `_materialize_embedded_profile_env()` to overwrite hermes.env with the stripped 4-5 key version
2. A daemon stop + restart with the now-stripped env
3. Daemon starts without EMBEDDINGS keys → falls back to local/384d embeddings

## Diagnosis path taken

1. `cat ~/.hindsight/profiles/hermes-default.log` → showed `ValueError: LLM API key is required`
   for the `hermes-default` profile (secondary issue, separate from main bug)
2. `cat ~/.hindsight/profiles/hermes.env` → showed only 4 keys, EMBEDDINGS missing
3. Read `_build_embedded_profile_env()` in the plugin → confirmed no EMBEDDINGS forwarding
4. Read `_start_daemon()` → found `config_changed` comparison logic
5. Simulated via venv python → confirmed `config_changed` would be True every session

## Fix applied

Added to `_build_embedded_profile_env()` after the `idle_timeout` block, before `return env_values`:

```python
# Forward HINDSIGHT_API_EMBEDDINGS_* keys from config.json into the
# daemon's env file.  Without this the daemon restarts without embedding
# credentials, silently falling back to LLM-only recall and causing
# intermittent "config changed → restart" loops on every session because
# the saved .env always differs from the freshly built one.
for key, value in config.items():
    if key.startswith("HINDSIGHT_API_EMBEDDINGS_") and value:
        env_values[key] = str(value)
```

Then immediately regenerated `hermes.env` by calling `_materialize_embedded_profile_env(config)`
via the venv python — no daemon restart needed (daemon was already running with the correct
keys from the manually-maintained hermes.env).

## Verification

```
Built env keys: 9, saved keys: 9, config_changed: False
```

78 memory-related tests passed. Daemon healthy at :9177.

## After hermes update

The patch is in a tracked file that updates replace. Always verify post-update:
```bash
grep -n "HINDSIGHT_API_EMBEDDINGS_" ~/.hermes/hermes-agent/plugins/memory/hindsight/__init__.py
# If empty → patch was dropped → re-apply or stash pop
git -C ~/.hermes/hermes-agent stash list   # find pre-update-<ts>
git -C ~/.hermes/hermes-agent stash pop stash@{N}
```

## Secondary issue: hermes-default.lock and hermes-default profile

The `bank_id_template: "hermes-{profile}"` with `agent_identity="default"` resolves
the bank to `hermes-default`. But `_embedded_profile_name()` reads only `config.get("profile", "hermes")`
— a static field — so the daemon always runs under profile `hermes`, not `hermes-default`.

The `hermes-default.lock` file exists because the daemon_embed_manager created it when
attempting to start a `hermes-default` daemon (which failed with "LLM API key required"
because no `hermes-default.env` exists). This is a benign artifact — the daemon correctly
runs under the `hermes` profile and serves the `hermes-default` bank over the same port.
The lock file is a zero-byte stale artifact; can be removed safely.
