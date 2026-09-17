# Dispatcher and collision pitfalls

Condensed notes from a local Ouroboros plugin debugging session.

## 1) Command collision avoidance
A plugin exposing bare subcommands like `inspect`, `catalog`, and `convert` is more fragile than one using plugin-qualified names. In a local fork of `hermes-skill-assimilator`, the safe rename set was:

- `inspect` -> `hermes-inspect`
- `catalog` -> `hermes-catalog`
- `convert` -> `hermes-convert`

When applying this class of fix, patch all three surfaces together:
1. `ouroboros.plugin.json`
2. Python argparse / CLI parser
3. README examples

## 2) Caller workspace vs installed plugin tree
For plugins that emit `.omx/...` artifacts, `Path.cwd()` is not a safe assumption under dispatcher invocation. A direct module run may honor the shell's working directory, while the dispatcher can launch from plugin home.

Safer default:

```python
if value:
    return Path(value)
base = Path(os.environ.get("PWD") or Path.cwd())
return base / ".omx" / "superpowers"
```

Reason: this keeps run artifacts in the caller workspace and avoids mutating `~/.ouroboros/plugins/<plugin>/`, which can otherwise accumulate transient state and create confusing trust/digest behavior.

## 3) Important diagnostic split
A nonzero `ooo <plugin> ...` exit code does not automatically mean the plugin logic failed.

In the reproduced case:
- direct `python3 -m superpowers_ouroboros brainstorming ...` succeeded
- valid JSON was printed
- expected `.omx/superpowers/runs/...` artifacts were created
- dispatched `ooo superpowers ...` still exited with code 1 and surfaced a traceback ending in `plugin_dispatch.py`

Interpretation rule:
- If direct module execution succeeds and artifacts verify on disk, classify the remaining issue as dispatcher/core behavior until disproven.

## 4) Minimum verification set for future sessions
- run one direct module invocation
- run the equivalent `ooo` invocation
- record both exit codes
- inspect stdout/stderr separately
- list artifact files on disk
- check whether installed plugin home gained a new `.omx` directory
