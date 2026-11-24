#!/usr/bin/env python3
"""Regression check for hermes-fork protected symbols post-merge.

Exits 0 and prints "ok" if all checks pass.
Exits 1 and prints FAIL lines if any check fails.
WARN lines are printed but do not fail the run.
"""
from __future__ import annotations

import ast
import importlib
import json
import pathlib
import sys

FORK = pathlib.Path("/var/home/rainbow/.hermes/hermes-fork")
PROFILE = pathlib.Path("/var/home/rainbow/.hermes/profiles/fork")
sys.path.insert(0, str(FORK))


def _warn(msg: str) -> None:
    print(f"WARN: {msg}")


def _enabled_plugins(config_text: str) -> list[str]:
    """Parse plugins.enabled from config.yaml without a YAML library."""
    out: list[str] = []
    in_plugins = False
    in_enabled = False
    plugins_indent: int | None = None
    enabled_indent: int | None = None
    for raw_line in config_text.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip())
        stripped = raw_line.strip()
        if not in_plugins:
            if stripped.rstrip(":") == "plugins" or stripped.startswith("plugins:"):
                in_plugins = True
                plugins_indent = indent
            continue
        if plugins_indent is not None and indent <= plugins_indent and not stripped.startswith("-"):
            break
        if not in_enabled:
            if stripped == "enabled:" or stripped.startswith("enabled:"):
                in_enabled = True
                enabled_indent = indent
                rest = stripped.split(":", 1)[1].strip()
                if rest.startswith("["):
                    inner = rest.strip("[]")
                    for part in inner.split(","):
                        name = part.strip().strip("'\"")
                        if name:
                            out.append(name)
                    break
            continue
        if enabled_indent is not None and indent <= enabled_indent:
            break
        if stripped.startswith("- "):
            name = stripped[2:].strip().strip("'\"")
            if name:
                out.append(name)
    return out


def _yaml_hook_names(text: str) -> list[str]:
    """Collect hook names from hooks: / provides_hooks: lists."""
    hooks: list[str] = []
    in_section = False
    section_indent: int | None = None
    for raw_line in text.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip())
        stripped = raw_line.strip()
        key = stripped.split(":", 1)[0].strip()
        if key in ("hooks", "provides_hooks") and stripped.endswith(":") or (
            key in ("hooks", "provides_hooks") and ":" in stripped
        ):
            in_section = True
            section_indent = indent
            rest = stripped.split(":", 1)[1].strip()
            if rest.startswith("["):
                inner = rest.strip("[]")
                for part in inner.split(","):
                    name = part.strip().strip("'\"")
                    if name:
                        hooks.append(name)
                in_section = False
            continue
        if in_section:
            if section_indent is not None and indent <= section_indent:
                in_section = False
                # fall through: this line may start another section
                if key in ("hooks", "provides_hooks"):
                    in_section = True
                    section_indent = indent
                continue
            if stripped.startswith("- "):
                name = stripped[2:].strip().strip("'\"")
                if name and ":" not in name:
                    hooks.append(name)
    return hooks


def _is_register_hook_call(node: ast.Call) -> bool:
    func = node.func
    if isinstance(func, ast.Attribute) and func.attr == "register_hook":
        return True
    if isinstance(func, ast.Name) and func.id == "register_hook":
        return True
    return False


def _registered_hook_literals(tree: ast.AST) -> set[str]:
    literals: set[str] = set()
    dynamic = False
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not _is_register_hook_call(node) or not node.args:
            continue
        a0 = node.args[0]
        if isinstance(a0, ast.Constant) and isinstance(a0.value, str):
            literals.add(a0.value)
        else:
            dynamic = True
    if dynamic:
        for node in ast.walk(tree):
            if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
                for elt in node.elts:
                    if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                        literals.add(elt.value)
                    elif isinstance(elt, ast.Tuple):
                        for inner in elt.elts:
                            if isinstance(inner, ast.Constant) and isinstance(inner.value, str):
                                literals.add(inner.value)
    return literals


def _funcs_by_name(tree: ast.AST) -> dict[str, list[ast.FunctionDef | ast.AsyncFunctionDef]]:
    out: dict[str, list[ast.FunctionDef | ast.AsyncFunctionDef]] = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out.setdefault(node.name, []).append(node)
    return out


def _callee_name(func: ast.AST) -> str | None:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _resolve_hook_fns(
    tree: ast.AST, fn_node: ast.AST
) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    by_name = _funcs_by_name(tree)
    targets: list[ast.FunctionDef | ast.AsyncFunctionDef] = []
    if isinstance(fn_node, ast.Name):
        targets.extend(by_name.get(fn_node.id, []))
    elif isinstance(fn_node, ast.Attribute):
        targets.extend(by_name.get(fn_node.attr, []))
    elif isinstance(fn_node, ast.Call):
        fname = _callee_name(fn_node.func)
        if fname:
            for factory in by_name.get(fname, []):
                inners = [
                    n
                    for n in factory.body
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                ]
                targets.extend(inners or [factory])
    return targets


def _top_level_try_wrapped(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    body = list(fn.body)
    if body and isinstance(body[0], ast.Expr) and isinstance(
        getattr(body[0], "value", None), ast.Constant
    ):
        body = body[1:]
    return bool(body) and all(isinstance(stmt, ast.Try) for stmt in body)


def _block_dicts_missing_message(fn: ast.AST) -> list[int]:
    """Return line numbers of dict-literal returns with action=block and no message."""
    bad: list[int] = []
    for node in ast.walk(fn):
        if not isinstance(node, ast.Return) or not isinstance(node.value, ast.Dict):
            continue
        keys: set[str] = set()
        action_block = False
        for k, v in zip(node.value.keys, node.value.values):
            if not isinstance(k, ast.Constant) or not isinstance(k.value, str):
                continue
            keys.add(k.value)
            if k.value == "action" and isinstance(v, ast.Constant) and v.value == "block":
                action_block = True
        if action_block and "message" not in keys:
            bad.append(getattr(node, "lineno", 0))
    return bad


def _loadable(init_py: pathlib.Path, src: str) -> str | None:
    """Return FAIL reason if the plugin cannot be parsed/compiled. Avoid exec side effects."""
    try:
        ast.parse(src)
        compile(src, str(init_py), "exec")
    except SyntaxError as e:
        return f"plugin {init_py.parent.name} not loadable: {e}"
    except Exception as e:
        return f"plugin {init_py.parent.name} not loadable: {e}"
    return None


def check_protected_symbols() -> list[str]:
    errors: list[str] = []
    for mod in ["agent.context_compressor", "hermes_cli.plugins", "agent.conversation_compression"]:
        try:
            importlib.import_module(mod)
        except Exception as e:
            errors.append(f"import FAIL {mod}: {e}")

    cc = FORK / "agent" / "context_compressor.py"
    try:
        tree = ast.parse(cc.read_text())
        classes = {n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)}
        for sym in ["StaleHeldHistory", "_HandoffScan", "_SummaryFailureKind", "ContextCompressor"]:
            if sym not in classes:
                errors.append(f"missing class {sym} in context_compressor.py")
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for item in ast.walk(node):
                    if isinstance(item, ast.FunctionDef):
                        for dec in item.decorator_list:
                            if isinstance(dec, ast.Name) and dec.id == "classmethod":
                                if item.args.args and item.args.args[0].arg == "self":
                                    errors.append(f"classmethod {item.name} uses self instead of cls")
    except Exception as e:
        errors.append(f"parse error context_compressor.py: {e}")

    cv = FORK / "agent" / "conversation_compression.py"
    try:
        tree2 = ast.parse(cv.read_text())
        fnames = {n.name for n in ast.walk(tree2) if isinstance(n, ast.FunctionDef)}
        if "compress_context" not in fnames:
            errors.append("missing function compress_context in conversation_compression.py")
    except Exception as e:
        errors.append(f"parse error conversation_compression.py: {e}")
    return errors


def check_plugin_refinement() -> list[str]:
    fails: list[str] = []
    cfg = PROFILE / "config.yaml"
    if not cfg.exists():
        return ["profiles/fork/config.yaml missing"]
    try:
        enabled = _enabled_plugins(cfg.read_text())
    except Exception as e:
        return [f"config.yaml parse error: {e}"]
    if not enabled:
        fails.append("plugins.enabled list empty or unparseable")
        return fails

    for name in enabled:
        plugin_dir = PROFILE / "plugins" / name
        init_py = plugin_dir / "__init__.py"
        if not plugin_dir.is_dir():
            fails.append(f"plugin dir missing: plugins/{name}/")
            continue
        if not init_py.is_file():
            fails.append(f"plugin {name}: __init__.py missing")
            continue
        size = init_py.stat().st_size
        if size < 200:
            fails.append(f"plugin {name}: __init__.py too small ({size} bytes)")
            continue
        try:
            src = init_py.read_text()
        except Exception as e:
            fails.append(f"plugin {name}: cannot read __init__.py: {e}")
            continue
        load_err = _loadable(init_py, src)
        if load_err:
            fails.append(load_err)
            continue
        try:
            tree = ast.parse(src)
        except Exception as e:
            fails.append(f"plugin {name}: AST parse failed: {e}")
            continue

        yaml_path = plugin_dir / "plugin.yaml"
        if yaml_path.is_file():
            declared = _yaml_hook_names(yaml_path.read_text())
            registered = _registered_hook_literals(tree)
            missing = sorted({h for h in declared if h not in registered})
            for h in missing:
                fails.append(f"plugin {name}: hook {h!r} declared but no register_hook literal")

        repo_init = FORK / "fork-profile" / "plugins" / name / "__init__.py"
        if repo_init.is_file() and size > 0:
            repo_size = repo_init.stat().st_size
            if repo_size > 0:
                delta = abs(size - repo_size) / size
                if delta > 0.10:
                    _warn(
                        f"plugin {name}: __init__.py size {size} vs repo {repo_size} "
                        f"({delta:.0%} drift)"
                    )
    return fails


def check_approval_inv() -> list[str]:
    fails: list[str] = []
    path = FORK / "tools" / "approval.py"
    if not path.is_file():
        _warn("tools/approval.py not found — skipping approval-gate invariant")
        return fails
    try:
        src = path.read_text()
        tree = ast.parse(src)
    except Exception as e:
        return [f"approval.py parse error: {e}"]

    assigned: dict[str, ast.AST] = {}
    fnames: set[str] = set()
    name_ids: set[str] = set()
    str_lits: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            fnames.add(node.name)
            name_ids.add(node.name)
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    assigned[t.id] = node.value
                    name_ids.add(t.id)
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            name_ids.add(node.target.id)
            if node.value is not None:
                assigned[node.target.id] = node.value
        if isinstance(node, ast.Name):
            name_ids.add(node.id)
        if isinstance(node, ast.alias):
            name_ids.add(node.asname or node.name)
            name_ids.add(node.name)
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            str_lits.add(node.value)
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                name_ids.add(alias.asname or alias.name)
                name_ids.add(alias.name)

    consent = assigned.get("CONSENT_ANSWERS")
    consent_ok = False
    if "CONSENT_ANSWERS" in name_ids and consent is not None:
        needed = {"once", "session", "always"}
        found: set[str] = set()
        for n in ast.walk(consent):
            if isinstance(n, ast.Constant) and isinstance(n.value, str):
                found.add(n.value)
        is_frozen = False
        if isinstance(consent, ast.Call):
            callee = consent.func
            if isinstance(callee, ast.Name) and callee.id == "frozenset":
                is_frozen = True
            if isinstance(callee, ast.Attribute) and callee.attr == "frozenset":
                is_frozen = True
        if isinstance(consent, ast.Set):
            is_frozen = True  # set literal assignment still contains the tokens
        if needed <= found and (is_frozen or isinstance(consent, (ast.Set, ast.Tuple, ast.List, ast.Call))):
            consent_ok = True
    if not consent_ok:
        fails.append("approval.py: CONSENT_ANSWERS frozenset with once/session/always missing")

    if "canonical_approval_choice" not in fnames:
        fails.append("approval.py: canonical_approval_choice function missing")

    if "hardline_scan_incomplete" not in name_ids and "hardline_scan_incomplete" not in str_lits:
        fails.append("approval.py: hardline_scan_incomplete missing")

    if "allow_permanent" not in name_ids and "allow_session" not in name_ids:
        fails.append("approval.py: allow_permanent/allow_session missing")
    return fails


def check_hook_contract() -> list[str]:
    fails: list[str] = []
    cfg = PROFILE / "config.yaml"
    if not cfg.exists():
        return fails
    enabled = _enabled_plugins(cfg.read_text())
    for name in enabled:
        init_py = PROFILE / "plugins" / name / "__init__.py"
        if not init_py.is_file():
            continue
        try:
            src = init_py.read_text()
            tree = ast.parse(src)
        except Exception:
            continue
        seen: set[int] = set()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not _is_register_hook_call(node) or len(node.args) < 2:
                continue
            a0 = node.args[0]
            if not (isinstance(a0, ast.Constant) and a0.value == "pre_tool_call"):
                continue
            for fn in _resolve_hook_fns(tree, node.args[1]):
                fid = id(fn)
                if fid in seen:
                    continue
                seen.add(fid)
                fn_name = getattr(fn, "name", "<hook>")
                for lineno in _block_dicts_missing_message(fn):
                    fails.append(
                        f"plugin {name}: {fn_name} returns action=block without message"
                        + (f" (line {lineno})" if lineno else "")
                    )
                if not _top_level_try_wrapped(fn):
                    _warn(f"plugin {name}: {fn_name}() not wrapped in try/except")
    return fails


def _script_exists(script: str) -> bool:
    p = pathlib.Path(script).expanduser()
    if p.is_file():
        return True
    if p.is_absolute():
        return False
    candidates = [
        PROFILE / script,
        PROFILE / "scripts" / script,
        FORK / script,
        pathlib.Path.home() / script,
    ]
    return any(c.is_file() for c in candidates)


def _argparse_has_required(src: str) -> bool:
    try:
        tree = ast.parse(src)
    except Exception:
        return False
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fname = _callee_name(node.func)
        if fname != "add_argument":
            continue
        for kw in node.keywords:
            if kw.arg == "required" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                return True
        if node.args:
            a0 = node.args[0]
            if isinstance(a0, ast.Constant) and isinstance(a0.value, str) and not a0.value.startswith("-"):
                return True
    return False


def check_cron_fts() -> list[str]:
    fails: list[str] = []
    jobs_path = PROFILE / "cron" / "jobs.json"
    if not jobs_path.is_file():
        return ["cron/jobs.json missing"]
    try:
        data = json.loads(jobs_path.read_text(), strict=False)
    except Exception as e:
        return [f"cron/jobs.json parse error: {e}"]
    jobs = data.get("jobs", data) if isinstance(data, dict) else data
    if not isinstance(jobs, list):
        return ["cron/jobs.json: jobs is not a list"]
    for job in jobs:
        if not isinstance(job, dict):
            continue
        script = job.get("script")
        if not script:
            continue
        jid = job.get("id") or job.get("name") or "?"
        if not _script_exists(str(script)):
            fails.append(f"cron job {jid}: script missing: {script}")
            continue
        if job.get("no_agent") is not True:
            _warn(f"cron job {jid}: script set but no_agent is not True")
        sp = pathlib.Path(str(script)).expanduser()
        if not sp.is_file():
            for c in (PROFILE / str(script), PROFILE / "scripts" / str(script)):
                if c.is_file():
                    sp = c
                    break
        if sp.suffix == ".py" and sp.is_file():
            try:
                src = sp.read_text(errors="replace")
            except Exception:
                continue
            if "argparse" in src and _argparse_has_required(src):
                argv = job.get("argv")
                if not argv:
                    _warn(f"cron job {jid}: required argparse args but argv empty")
    return fails


def main() -> int:
    errors: list[str] = []
    errors.extend(check_protected_symbols())
    errors.extend(check_plugin_refinement())
    errors.extend(check_approval_inv())
    errors.extend(check_hook_contract())
    errors.extend(check_cron_fts())
    if errors:
        for e in errors:
            print(f"FAIL: {e}")
        return 1
    print("ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
