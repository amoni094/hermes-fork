#!/usr/bin/env python3
"""Thin wrapper: l1-tracegrant lives in ~/.hermes/scripts/ (shared).

Exposes tracegrant_check and tracegrant_log_grant for import by other scripts.
When imported as a module (run_name != '__main__'), the __main__ block is NOT
executed so argparse does not fire at import time.

When executed directly (e.g. by a cron job as a CLI), delegates to the shared
script's main() via importlib so the CLI still works.
"""
import importlib.util
import pathlib
import sys

TARGET = pathlib.Path('/var/home/rainbow/.hermes/scripts/l1-tracegrant.py')

# Load the shared module WITHOUT triggering its __main__ block.
_spec = importlib.util.spec_from_file_location("_l1_tracegrant_shared", TARGET)
assert _spec is not None, f"Cannot find spec for {TARGET}"
_mod = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_mod)  # type: ignore[union-attr]

# Re-export the public API so importers can do:
#   from l1_tracegrant import tracegrant_check, tracegrant_log_grant
tracegrant_check = _mod.tracegrant_check
tracegrant_log_grant = _mod.tracegrant_log_grant
tracegrant_audit = _mod.tracegrant_audit
tracegrant_verify = _mod.tracegrant_verify
tracegrant_revoke = _mod.tracegrant_revoke

if __name__ == "__main__":
    # CLI delegation: run the shared script's main() with the current sys.argv.
    sys.argv[0] = str(TARGET)
    sys.exit(_mod.main())
