# Adversarial Pass — 2026-09-02 Findings

Independent grok-4.6 subagent pass on three artifacts:
`hindsight-api.service`, `hindsight-watchdog.py`, `hindsight-stack-operations/SKILL.md`.

## Real bugs found (that the self-review missed)

### BUG 1 (HIGH): `StartLimitIntervalSec` in `[Service]` section — silently ignored

**Root cause**: `StartLimitIntervalSec` is a `[Unit]` directive. Placing it in `[Service]`
causes systemd to silently drop it with a warning:
```
hindsight-api.service: Unknown key name 'StartLimitIntervalSec' in section 'Service'
```
The burst-limit never fires. Service can restart infinitely with no rate cap.

**Fix**: Move `StartLimitBurst=` and `StartLimitIntervalSec=` to the `[Unit]` section.

**Detection**: `systemd-analyze verify ~/.config/systemd/user/hindsight-api.service`
shows the warning. Always run this after editing a unit file.

**Verified**: After fix, `systemctl --user show hindsight-api.service --property=StartLimitBurst`
returns `StartLimitBurst=5` (non-zero = active).

---

### BUG 2 (MEDIUM): `CrossEncoder()` re-verifies with HuggingFace CDN even from cache

**Root cause**: `sentence_transformers.CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')`
makes a network HEAD request to HuggingFace to check for model updates, even when the
model is fully cached locally in `~/.cache/huggingface/`. On a slow or stalled CDN
connection this can hang for minutes.

**Fix**: Set `HF_HUB_OFFLINE=1` in the environment before loading:
```python
import os
os.environ["HF_HUB_OFFLINE"] = "1"
from sentence_transformers import CrossEncoder
model = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
```
Or in the systemd unit's `[Service]` section:
```ini
Environment=HF_HUB_OFFLINE=1
```
**Caution**: Only safe once the model has been downloaded at least once. On a fresh
install with no cache, `HF_HUB_OFFLINE=1` causes `EnvironmentError: Offline mode is
enabled, cannot make API call to check for model updates.`

**Mitigation**: Guard with a cache-presence check before setting offline mode:
```python
import os
from pathlib import Path
HF_CACHE = Path.home() / ".cache/huggingface/hub"
MODEL_ID = "cross-encoder--ms-marco-MiniLM-L-6-v2"
if any(HF_CACHE.glob(f"models--{MODEL_ID}/snapshots/*")):
    os.environ["HF_HUB_OFFLINE"] = "1"
```

---

### False negatives in self-authored verification tests

The initial self-review passed 32/32 checks but missed both bugs above.
**Lesson**: Positive tests written by the same agent that made the changes
cannot be trusted as adversarial coverage. For any system-critical artifact:

1. Self-review catches the obvious.
2. Independent subagent (grok-4.6, no prior context) catches what self-review misses.
3. `systemd-analyze verify <unit>` is a required post-edit step — never skip it.

---

## Session state at close
- Service unit fixed: `StartLimitBurst`/`StartLimitIntervalSec` moved to `[Unit]`
- `HF_HUB_OFFLINE=1` approach documented; not yet applied to unit (deferred — requires
  cache-presence guard to be safe on fresh installs; hindsight-api startup does its own
  model loading, not the ExecStartPre)
- Watchdog script clean: dead function removed, TOCTOU race fixed, PID=0 guard added,
  tail-read replaces full-file-read, log rotation at 500KB
- Skill Cause 3 section corrected: no longer claims system python3 has sentence_transformers
