# Python Package Isolation Patterns with uv

Session: veto 0.15.2 installation on Python 3.14

## Problem
When using uv on Fedora Atomic / systems with immutable `/usr`, `pip install --user` is blocked (`uv pip install --user` returns error about virtualenvs being required). This prevents system-level package installs, which is by design (isolation safety). But it means any package with compiled C extensions (rpds-py, Pydantic-core, etc.) requires a venv.

## Solution: uv venv Isolation

Create a dedicated venv for the package and its version:

```bash
# Create isolated venv with specific Python version
uv venv ~/.venvs/<package>-py<version> --python python3.<version>

# Activate and install
source ~/.venvs/<package>-py314/bin/activate
uv pip install <package>
```

**Example (veto on Python 3.14):**
```bash
uv venv ~/.venvs/veto-py314 --python python3.14
source ~/.venvs/veto-py314/bin/activate
uv pip install veto
```

### Key Points

1. **Version Naming:** Use `<name>-py<major><minor>` in the venv directory (e.g., `veto-py314` for Python 3.14). This prevents collision when the same tool needs different Python versions.

2. **Venv Already Exists:** If you're re-running venv setup, use `--clear` to force recreation:
   ```bash
   uv venv ~/.venvs/veto-py314 --python python3.14 --clear
   ```

3. **Multiple Python Versions:** The system may have both `python3` (default) and `python3.14`. Specify the exact version:
   ```bash
   # Fails if 3.14 wheels exist but 3.13 is default — uv resolves to 3.13
   uv venv ~/.venvs/veto-py314 --python python3  # Don't do this

   # Correct — pin the binary explicitly
   uv venv ~/.venvs/veto-py314 --python python3.14
   ```

4. **Transitive Dependencies with C Extensions:** rpds-py (used by Pydantic), cryptography, and others have manylinux wheels for Python 3.14+. If a wheel is missing, the error message will be clear — but it's usually a venv isolation issue first, missing wheel second.

## Tool-Specific Config: veto Local-Only Mode

veto can run in **cloud-validation mode** (requires network + `VETO_API_KEY`) or **local-only mode** (rules files in local dir, no external calls).

### Local-Only Setup (Recommended for Hermes)

```python
from veto import Veto, VetoOptions

veto = await Veto.init(VetoOptions(
    mode='strict',
    validation_mode='local'
))
```

This:
- Does not require `VETO_API_KEY`
- Does not make network calls to `api.runveto.com`
- Uses local rules from `./veto/rules/` (if present)

### Initialize Local Rules

```bash
# Generate local rules structure
npx --package veto-cli@latest veto init

# Or pass rules via Python:
rules_dir = pathlib.Path(__file__).parent / 'veto' / 'rules'
veto = await Veto.init(VetoOptions(
    mode='strict',
    validation_mode='local',
    rules_dir=str(rules_dir)
))
```

### Cloud Mode (Not Recommended for Agent Sessions)

If you do need cloud validation:
```python
veto = await Veto.init(VetoOptions(
    mode='strict',
    validation_mode='cloud',
    api_key=os.environ['VETO_API_KEY']
))
```

**Pitfall:** Cloud mode will fail if the host cannot reach `api.runveto.com` or if that domain's SSL certificate is invalid (e.g., hostname mismatch on local/private networks). Local-only is safer for automation.

## Git Performance: Avoiding Full-Tree Scans

When using `git add` from a nested Hermes directory (e.g., `~/.hermes/skills`), git can scan the entire home directory if the repo root is `/home/user` rather than `~/.hermes`.

**Symptom:** `git add .` times out or takes >30s even on fast systems.

**Fix:**

1. **Know your repo root:**
   ```bash
   cd ~/.hermes/skills && git rev-parse --show-toplevel
   # Outputs: /home/user (not ~/.hermes — the problem)
   ```

2. **Use explicit paths instead of `.`:**
   ```bash
   # Instead of:
   git add .

   # Use:
   git add skills/  # or specific files
   ```

3. **Or: use a narrower add wrapper:**
   ```bash
   # Only add files from current subtree
   git add --pathspec-from-file <(git diff --name-only HEAD -- .)
   ```

4. **For Hermes skills specifically:** Use a dedicated git repo under `~/.hermes/skills-repo/` or commit via a wrapper script that explicitly lists `skills/` to avoid scanning siblings.

## Verification Checklist

After setting up a venv:

```bash
source ~/.venvs/<package>-py<version>/bin/activate
python3 --version  # Confirm Python version
python3 -c "import <package>; print('OK')"  # Confirm import works
```

For veto specifically:

```bash
source ~/.venvs/veto-py314/bin/activate
python3 -c "
import asyncio
from veto import Veto, VetoOptions

async def test():
    veto = await Veto.init(VetoOptions(mode='strict', validation_mode='local'))
    decision = await veto.guard('bash', {'command': 'echo test'})
    print('veto guard returned:', decision.decision)

asyncio.run(test())
"
```

Expected output: `veto guard returned: allow` (or `deny` for risky commands, depending on local rules).
