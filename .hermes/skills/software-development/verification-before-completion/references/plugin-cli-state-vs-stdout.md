# Plugin CLI verification: persisted state beats stdout

Use this when verifying plugin/extension installation or configuration in Hermes-like CLIs.

Key rule:
- Do not treat printed JSON or a success-looking table as sufficient proof if the command exits non-zero.
- For plugin workflows, verify the persisted state separately.

Recommended verification order:
1. Run the install/trust/config command.
2. Check the command exit code.
3. Read back the native installed-state view (`plugin inspect`, `plugin list`, or equivalent).
4. Read back the lockfile/config file that records the install subject/version/path when available.
5. Only then claim the plugin is installed/configured.

Practical pattern captured from session:
- Prefer the CLI's non-interactive primitive install verb for reproducible local plugin installs.
- After install, explicitly re-read trust state and granted scopes.
- If a plugin command prints valid output but exits non-zero afterward, report the command as failed even if the output looked plausible; rely on `inspect`/lockfile readback for the narrower claim that installation/trust succeeded.

What to say:
- "Installed and trusted, verified by plugin inspect + lockfile readback, but invocation still exits non-zero, so the runtime command path is not yet verified."

What not to say:
- "Works" based only on stdout from a failed command.
