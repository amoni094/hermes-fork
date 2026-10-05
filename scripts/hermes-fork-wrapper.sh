#!/usr/bin/env bash
# hermes-fork wrapper — install to ~/.local/bin/hermes-fork
#
# CRITICAL: must point at .hermes/bin/hermes (the store Python launcher),
# NOT at venv/bin/hermes (in-tree venv, may be an older Python version).
#
# If ~/.local/bin/hermes-fork points at venv/bin/hermes and the PM has
# migrated to a newer Python, activate_dependencies() will swap in compiled
# extensions built for the newer Python into the older interpreter. Compiled
# extensions (pydantic_core, jiter, etc.) will fail with:
#   No module named 'pydantic_core._pydantic_core'
# Hermes surfaces this as the misleading "anthropic package is required" error.
#
# To install: cp scripts/hermes-fork-wrapper.sh ~/.local/bin/hermes-fork && chmod +x ~/.local/bin/hermes-fork
# To verify:  head -1 ~/.hermes/hermes-fork/.hermes/bin/hermes  # should be store Python shebang
#             hermes-fork -z 'say ok'
HERMES_FORK_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CANONICAL_LAUNCHER="${HERMES_FORK_ROOT}/.hermes/bin/hermes"

# Safety check: warn if canonical launcher is missing (fall through to allow diagnosis)
if [[ ! -x "$CANONICAL_LAUNCHER" ]]; then
    echo "hermes-fork: WARNING: canonical launcher not found at $CANONICAL_LAUNCHER" >&2
    echo "hermes-fork: Run 'hermes pm sync' to rebuild, or check the install." >&2
    exit 1
fi

exec "$CANONICAL_LAUNCHER" --profile fork "$@"
