# Hermes Venv Dependency Drift — Daemon Startup Failure

## Pattern

A daemon (e.g. hindsight) fails at startup with an import error for a package
that IS installed in the venv. The surface error names a package (e.g.
`sentence-transformers is required for LocalSTEmbeddings`) but the real failure
is a transitive dependency version conflict introduced when a major library
tightened its version requirements in a newer release.

## Reproduction (July 2026 — hindsight daemon)

```
ImportError: sentence-transformers is required for LocalSTEmbeddings.
Install it with: pip install sentence-transformers
```

Importing sentence-transformers in the venv produced:
```
ImportError: huggingface-hub>=1.5.0,<2.0 is required for a normal functioning
of this module, but found huggingface-hub==1.2.3.
```

Root cause: `transformers` 5.10.2 tightened its huggingface-hub requirement.
The venv was last updated when the constraint was looser; huggingface-hub was
pinned at 1.2.3 and violated the new constraint at runtime.

## Repair Sequence

1. Identify the daemon's exact venv:
   `/var/home/rainbow/.hermes/hermes-agent/venv/`

2. Reproduce the import failure directly in that venv:
   ```
   /var/home/rainbow/.hermes/hermes-agent/venv/bin/python \
     -c "import sentence_transformers; print(sentence_transformers.__version__)"
   ```
   Read the FULL traceback — it names the conflicting package and version constraint.

3. Check the installed version of the conflicting transitive dep:
   ```
   /var/home/rainbow/.hermes/hermes-agent/venv/bin/pip show huggingface-hub transformers
   ```

4. Upgrade the conflicting dep to satisfy the constraint:
   ```
   /var/home/rainbow/.hermes/hermes-agent/venv/bin/pip install "huggingface-hub>=1.5.0"
   ```
   (Resolved to 1.24.0.)

5. Retest the import:
   ```
   /var/home/rainbow/.hermes/hermes-agent/venv/bin/python \
     -c "import sentence_transformers; print('OK', sentence_transformers.__version__)"
   ```

6. Verify daemon health (hindsight on port 9177):
   ```
   curl http://localhost:9177/health
   # Expected: {"status":"healthy","database":"connected"}
   ```

## Diagnostic Triage Path

1. Check daemon log first: `~/.hindsight/profiles/hermes.log`
   (or `~/.hermes/logs/hindsight-embed.log`)
2. If surface error says "install X", DON'T install blindly — test the import in the venv first.
3. Import traceback usually names the real culprit within 3–5 lines.
4. `pip show <conflicting-pkg>` confirms the version mismatch.
5. Fix in the daemon's venv, not the system/user Python.

## Common Trigger

Major libraries (transformers, sentence-transformers, torch, accelerate) ship
new releases that tighten transitive constraints. A venv frozen months earlier
can silently violate those constraints until the library is actually imported
at runtime — often only when a daemon starts.

## Notes

- `hermes doctor` reports "hindsight provider active" even when the daemon is
  crashing — it checks plugin install state, not live daemon health.
- The hindsight daemon is at:
  `/var/home/rainbow/.hermes/hermes-agent/venv/lib/python3.11/site-packages/hindsight_api/`
- The daemon executable: `hindsight-api` in the hermes venv bin.
