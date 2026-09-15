#!/usr/bin/env python3
"""
validate-skill-ssl.py — Validate SSL frontmatter in a Hermes SKILL.md file.

Usage:
    python validate-skill-ssl.py path/to/SKILL.md

Exit codes:
    0 — all checks PASS
    1 — one or more checks FAIL
    2 — usage error

Based on the SSL (Scheduling-Structural-Logical) schema defined in
~/.hermes/skills/SKILL_TEMPLATE.md (arXiv:2604.24026).
"""

import sys
import re

# ── Try to import yaml; fall back to a minimal parser if unavailable ──────────
HAS_YAML = False
try:
    import yaml as _yaml_module
    HAS_YAML = True
except ImportError:
    _yaml_module = None  # type: ignore[assignment]

VALID_RISK_LEVELS = {"low", "medium", "high"}

# ── Result collector ─────────────────────────────────────────────────────────

results: list[tuple[str, str, str]] = []   # (status, field, reason)
has_fail = False


def record(status: str, field: str, reason: str) -> None:
    global has_fail
    results.append((status, field, reason))
    if status == "FAIL":
        has_fail = True


def print_results() -> None:
    width_status = 4
    width_field  = max((len(f) for _, f, _ in results), default=10)
    print()
    print(f"{'STATUS':<{width_status+2}}  {'FIELD':<{width_field+2}}  REASON")
    print("-" * 72)
    for status, field, reason in results:
        marker = "✔" if status == "PASS" else ("⚠" if status == "WARN" else "✘")
        print(f"{marker} {status:<{width_status}}  {field:<{width_field+2}}  {reason}")
    print()
    failing = [f for s, f, _ in results if s == "FAIL"]
    warning = [f for s, f, _ in results if s == "WARN"]
    if has_fail:
        print(f"RESULT: FAIL  ({len(failing)} failure(s): {', '.join(failing)})")
    elif warning:
        print(f"RESULT: WARN  ({len(warning)} warning(s): {', '.join(warning)})")
    else:
        print("RESULT: PASS  — all checks passed")
    print()


# ── Thompson helpers (additive; lint-time only) ───────────────────────────────

_DOLLAR_VAR_RE = re.compile(r"\$([A-Za-z_][A-Za-z0-9_]*)")
_IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_LAW_STOPWORDS = {
    "a", "an", "the", "and", "or", "not", "no", "if", "then", "iff", "equals",
    "eq", "implies", "forall", "exists", "true", "false", "must", "may", "only",
    "all", "any", "in", "of", "to", "for", "with", "without", "is", "are", "be",
    "does", "do", "must", "shall", "should", "can", "cannot", "via", "from",
    "into", "on", "at", "by", "as", "vs", "than", "that", "this", "those",
    "these", "it", "its", "we", "our", "law", "invariant", "preserves",
    "preserve", "never", "always", "under", "over", "when", "where",
}

VALID_WITNESS = {"opaque", "transparent"}
VALID_FORALL_TYPECLASS_KEYS = ("type_class", "type-class", "typeclass", "type_class_ref")


def _dollar_vars(*texts: object) -> set[str]:
    found: set[str] = set()
    for t in texts:
        if t is None:
            continue
        if isinstance(t, (list, tuple)):
            for item in t:
                found |= _dollar_vars(item)
        elif isinstance(t, dict):
            for v in t.values():
                found |= _dollar_vars(v)
        else:
            found.update(_DOLLAR_VAR_RE.findall(str(t)))
    return found


def _arg_names(args: object) -> set[str] | None:
    """Declared ssl_scheduling.args names, or None if args is undeclared."""
    if args is None:
        return None
    names: set[str] = set()
    if isinstance(args, dict):
        names = {str(k) for k in args.keys()}
    elif isinstance(args, list):
        for item in args:
            if isinstance(item, str) and item.strip():
                names.add(item.strip())
            elif isinstance(item, dict):
                n = item.get("name") or item.get("key") or item.get("arg")
                if n is not None and str(n).strip():
                    names.add(str(n).strip())
    else:
        names = {str(args)}
    return names


def _names_from_entries(entries: object) -> set[str]:
    names: set[str] = set()
    if not isinstance(entries, list):
        return names
    for item in entries:
        if isinstance(item, str) and item.strip():
            names.add(item.strip())
        elif isinstance(item, dict):
            n = item.get("name")
            if isinstance(n, str) and n.strip():
                names.add(n.strip())
    return names


def _tools_used(structural: dict | None) -> list:
    if not isinstance(structural, dict):
        return []
    tools = structural.get("tools_used")
    return tools if isinstance(tools, list) else []


def _has_checker_or_typeclass(obj: dict) -> bool:
    checker = obj.get("checker")
    if checker not in (None, "", [], {}):
        return True
    for k in VALID_FORALL_TYPECLASS_KEYS:
        if obj.get(k) not in (None, "", [], {}):
            return True
    return False


def _validate_forall_block(field: str, forall: object) -> None:
    """THOMPSON-8 / THOMPSON-2: forall block without a checker is advisory only.
    NOTE: Without a real type checker binary, FAIL is too strong — emit WARN instead.
    A forall without checker is undecidable in general but we cannot verify that here."""
    if forall is None:
        return
    if isinstance(forall, str):
        # Bare string is treated as a type-class reference.
        if not forall.strip():
            record("WARN", field, "forall without checker or type-class reference (cannot enforce)")
        else:
            record("PASS", field, "forall names a type-class reference")
        return
    if isinstance(forall, list):
        if not forall:
            record("WARN", field, "empty forall list; no checker (advisory only)")
            return
        for i, item in enumerate(forall):
            _validate_forall_block(f"{field}[{i}]", item)
        return
    if not isinstance(forall, dict):
        record("WARN", field, "forall block has unexpected type; expected dict, list, or string")
        return
    if not _has_checker_or_typeclass(forall):
        nested = forall.get("forall")
        if nested is not None:
            _validate_forall_block(field, nested)
            return
        record("WARN", field, "forall without checker or type-class reference (advisory only)")
    else:
        record("PASS", field, "forall has checker or type-class reference")


# ── YAML / frontmatter extraction ─────────────────────────────────────────────

def extract_frontmatter(path: str) -> tuple[str | None, str | None]:
    """Return (raw_yaml_string, error_message). raw_yaml_string is None on error."""
    try:
        with open(path, encoding="utf-8") as fh:
            content = fh.read()
    except OSError as exc:
        return None, f"Cannot read file: {exc}"

    if not content.startswith("---"):
        return None, "File does not start with '---' — not a valid SKILL.md"

    # Find the closing ---
    match = re.search(r"\n---\n", content[3:])
    if not match:
        return None, "No closing '---' found — frontmatter is not terminated"

    raw_yaml = content[3 : match.start() + 3]   # slice between the two ---
    return raw_yaml, None


def parse_yaml(raw: str) -> tuple[dict | None, str | None]:
    if HAS_YAML and _yaml_module is not None:
        try:
            data = _yaml_module.safe_load(raw)
            if not isinstance(data, dict):
                return None, "Frontmatter parsed but is not a YAML mapping"
            return data, None
        except _yaml_module.YAMLError as exc:
            return None, f"YAML parse error: {exc}"
    else:
        # Minimal fallback: detect ssl_ top-level keys by line scan
        # Good enough for presence checks but won't give nested access.
        data: dict = {}
        current_top: str | None = None
        for line in raw.splitlines():
            m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):", line)
            if m:
                current_top = m.group(1)
                data[current_top] = {}   # placeholder; nesting not parsed
        return data, "yaml module unavailable — deep validation skipped (install PyYAML)"


# ── SSL validators ────────────────────────────────────────────────────────────

def validate_ssl_scheduling(block: dict | None) -> None:
    prefix = "ssl_scheduling"
    if block is None:
        record("WARN", prefix, "Block absent — SSL scheduling metadata missing")
        return
    if not isinstance(block, dict):
        record("FAIL", prefix, "Must be a YAML mapping")
        return

    # triggers
    triggers = block.get("triggers")
    if triggers is None:
        record("WARN", f"{prefix}.triggers", "Missing — no scheduling triggers defined")
    elif not isinstance(triggers, list):
        record("FAIL", f"{prefix}.triggers", f"Must be a list, got {type(triggers).__name__}")
    elif len(triggers) == 0:
        record("WARN", f"{prefix}.triggers", "Empty list — add at least one trigger")
    else:
        non_str = [t for t in triggers if not isinstance(t, str)]
        if non_str:
            record("FAIL", f"{prefix}.triggers", f"All items must be strings; bad: {non_str[:2]}")
        else:
            record("PASS", f"{prefix}.triggers", f"{len(triggers)} trigger(s) defined")

    # preconditions (THOMPSON-8: string prose or executable {name, check, equals})
    arg_names = _arg_names(block.get("args"))
    preconditions = block.get("preconditions")
    if preconditions is None:
        record("WARN", f"{prefix}.preconditions", "Missing — preconditions not declared")
    elif not isinstance(preconditions, list):
        record("FAIL", f"{prefix}.preconditions", f"Must be a list, got {type(preconditions).__name__}")
    else:
        record("PASS", f"{prefix}.preconditions", f"{len(preconditions)} precondition(s) declared")
        for i, pre in enumerate(preconditions):
            field = f"{prefix}.preconditions[{i}]"
            if isinstance(pre, str):
                record("WARN", field, "prose precondition; not executable")
                continue
            if not isinstance(pre, dict):
                record("FAIL", field, f"Must be a string or mapping, got {type(pre).__name__}")
                continue
            if "forall" in pre:
                _validate_forall_block(field, pre)
            check = pre.get("check")
            if check is None and "forall" in pre:
                continue
            if not isinstance(check, list):
                record("WARN", field, "Executable precondition has check: but it is not a list (advisory only)")
                continue
            equals = pre.get("equals")
            if equals is not None and not isinstance(equals, bool):
                record("WARN", field, "equals should be true or false (advisory only)")
                continue
            unbound = set()
            for argv_item in check:
                for var in _dollar_vars(argv_item):
                    if arg_names is None or var not in arg_names:
                        unbound.add(var)
            if unbound:
                record(
                    "WARN", field,
                    f"$var substitution may be unbound in check argv: {sorted(unbound)} "
                    "(check ssl_scheduling.args — advisory only; not run at lint time)",
                )
            else:
                pname = pre.get("name") or f"precondition[{i}]"
                record("PASS", field, f"executable precondition '{pname}' (not run at lint time)")

    # estimated_steps
    estimated_steps = block.get("estimated_steps")
    if estimated_steps is None:
        record("WARN", f"{prefix}.estimated_steps", "Missing — step count not declared")
    elif not isinstance(estimated_steps, int) or isinstance(estimated_steps, bool):
        record("FAIL", f"{prefix}.estimated_steps", f"Must be an integer, got {type(estimated_steps).__name__}")
    elif estimated_steps < 1:
        record("FAIL", f"{prefix}.estimated_steps", f"Must be ≥ 1, got {estimated_steps}")
    else:
        record("PASS", f"{prefix}.estimated_steps", f"{estimated_steps} step(s) estimated")

    # THOMPSON-2/8: forall at scheduling level (checker or type-class required)
    if "forall" in block:
        _validate_forall_block(f"{prefix}.forall", block.get("forall"))

    # THOMPSON-1: optional output_family under ssl_scheduling
    output_family = block.get("output_family")
    args_nonempty = bool(arg_names)
    if output_family is None:
        if args_nonempty:
            record("WARN", f"{prefix}.output_family", "no output_family; output type independent of args")
        return
    if not isinstance(output_family, list):
        record("FAIL", f"{prefix}.output_family", f"Must be a list, got {type(output_family).__name__}")
        return
    family_ok = True
    for i, clause in enumerate(output_family):
        field = f"{prefix}.output_family[{i}]"
        if not isinstance(clause, dict):
            record("FAIL", field, f"Must be a mapping {{when, produces}}, got {type(clause).__name__}")
            family_ok = False
            continue
        when = clause.get("when")
        produces = clause.get("produces")
        if not isinstance(when, dict):
            record("FAIL", field, "when must be a mapping of arg: value")
            family_ok = False
            when = {}
        if not isinstance(produces, dict):
            record("FAIL", field, "produces must be a mapping {kind, from}")
            family_ok = False
            produces = {}
        when_keys = {str(k) for k in when.keys()}
        if when_keys:
            if arg_names is None:
                record("WARN", field, "no args declared for when binding")
            else:
                unknown = sorted(k for k in when_keys if k not in arg_names)
                if unknown:
                    record("FAIL", field, f"when keys not in ssl_scheduling.args: {unknown}")
                    family_ok = False
        from_expr = produces.get("from")
        unbound_from = [v for v in _dollar_vars(from_expr) if v not in when_keys]
        if unbound_from:
            record("FAIL", field, f"$var in produces.from not in when keys: {unbound_from}")
            family_ok = False
        if "kind" not in produces:
            record("FAIL", field, "produces.kind is required")
            family_ok = False
    if family_ok:
        record("PASS", f"{prefix}.output_family", f"{len(output_family)} output family clause(s)")


def validate_ssl_structural(block: dict | None) -> None:
    prefix = "ssl_structural"
    if block is None:
        record("WARN", prefix, "Block absent — SSL structural metadata missing")
        return
    if not isinstance(block, dict):
        record("FAIL", prefix, "Must be a YAML mapping")
        return

    # tools_used
    tools_used = block.get("tools_used")
    if tools_used is None:
        record("WARN", f"{prefix}.tools_used", "Missing — tool list not declared")
    elif not isinstance(tools_used, list):
        record("FAIL", f"{prefix}.tools_used", f"Must be a list, got {type(tools_used).__name__}")
    elif len(tools_used) == 0:
        record("WARN", f"{prefix}.tools_used", "Empty list — declare at least one tool")
    else:
        non_str = [t for t in tools_used if not isinstance(t, str)]
        if non_str:
            record("FAIL", f"{prefix}.tools_used", f"All items must be strings; bad: {non_str[:2]}")
        else:
            record("PASS", f"{prefix}.tools_used", f"{len(tools_used)} tool(s) listed: {tools_used}")

    # subtasks
    subtasks = block.get("subtasks")
    if subtasks is None:
        record("WARN", f"{prefix}.subtasks", "Missing — subtask phases not declared")
    elif not isinstance(subtasks, list):
        record("FAIL", f"{prefix}.subtasks", f"Must be a list, got {type(subtasks).__name__}")
    else:
        record("PASS", f"{prefix}.subtasks", f"{len(subtasks)} subtask(s) defined")


def validate_ssl_logical(block: dict | None, structural: dict | None = None) -> None:
    prefix = "ssl_logical"
    if block is None:
        record("WARN", prefix, "Block absent — SSL logical metadata missing")
        return
    if not isinstance(block, dict):
        record("FAIL", prefix, "Must be a YAML mapping")
        return

    # side_effects
    side_effects = block.get("side_effects")
    if side_effects is None:
        record("WARN", f"{prefix}.side_effects", "Missing — side effects not declared")
    elif not isinstance(side_effects, list):
        record("FAIL", f"{prefix}.side_effects", f"Must be a list, got {type(side_effects).__name__}")
    else:
        record("PASS", f"{prefix}.side_effects", f"{len(side_effects)} side effect(s) declared")

    # resources
    resources = block.get("resources")
    if resources is None:
        record("WARN", f"{prefix}.resources", "Missing — resource list not declared")
    elif not isinstance(resources, list):
        record("FAIL", f"{prefix}.resources", f"Must be a list, got {type(resources).__name__}")
    else:
        record("PASS", f"{prefix}.resources", f"{len(resources)} resource(s) listed")

    # risk_level
    risk_level = block.get("risk_level")
    if risk_level is None:
        record("FAIL", f"{prefix}.risk_level", "Missing — risk_level is required when ssl_logical is present")
    elif not isinstance(risk_level, str):
        record("FAIL", f"{prefix}.risk_level", f"Must be a string, got {type(risk_level).__name__}")
    elif risk_level not in VALID_RISK_LEVELS:
        record("FAIL", f"{prefix}.risk_level",
               f"'{risk_level}' is not a valid level; must be one of {sorted(VALID_RISK_LEVELS)}")
    else:
        record("PASS", f"{prefix}.risk_level", f"'{risk_level}' is a valid risk level")

    # THOMPSON-6: optional ssl_logical.invariants as co-located laws
    tools_used = _tools_used(structural)
    tools_used_names = {t for t in tools_used if isinstance(t, str)}
    invariants = block.get("invariants")
    if invariants is None or (isinstance(invariants, list) and len(invariants) == 0):
        if tools_used_names:
            record("WARN", f"{prefix}.invariants", "signature without laws")
        return
    if not isinstance(invariants, list):
        record("FAIL", f"{prefix}.invariants", f"Must be a list, got {type(invariants).__name__}")
        return

    allowed_names = set()
    ops_union_ok = True
    for inv in invariants:
        if isinstance(inv, dict) and isinstance(inv.get("ops"), list):
            allowed_names.update(str(o) for o in inv["ops"])
    allowed_names |= _names_from_entries(block.get("resources"))
    allowed_names |= _names_from_entries(block.get("side_effects"))

    inv_ok = True
    for i, inv in enumerate(invariants):
        field = f"{prefix}.invariants[{i}]"
        if not isinstance(inv, dict):
            record("FAIL", field, f"Must be a mapping {{name, ops, law}}, got {type(inv).__name__}")
            inv_ok = False
            continue
        name = inv.get("name")
        ops = inv.get("ops")
        law = inv.get("law")
        if not isinstance(name, str) or not name.strip():
            record("FAIL", field, "name must be a non-empty string")
            inv_ok = False
        if not isinstance(ops, list):
            record("FAIL", field, "ops must be a list of tool names")
            inv_ok = False
            ops = []
        else:
            bad_ops = [o for o in ops if not isinstance(o, str) or o not in tools_used_names]
            if bad_ops:
                record("FAIL", field, f"ops not in ssl_structural.tools_used: {bad_ops}")
                inv_ok = False
                ops_union_ok = False
        if not isinstance(law, str) or not law.strip():
            record("FAIL", field, "law must be a non-empty string")
            inv_ok = False
            law = ""
        mentioned: set[str] = set(_dollar_vars(law))
        for ident in _IDENT_RE.findall(law):
            low = ident.lower()
            if low in _LAW_STOPWORDS:
                continue
            if ident in tools_used_names or "_" in ident or ident in allowed_names:
                mentioned.add(ident)
        unknown = sorted(n for n in mentioned if n not in allowed_names)
        if unknown:
            record(
                "FAIL", field,
                f"names in law not in ops ∪ resources ∪ side_effects: {unknown}",
            )
            inv_ok = False
        witness = inv.get("witness")
        if witness is not None:
            if witness not in VALID_WITNESS:
                record("FAIL", field, "witness must be 'opaque' or 'transparent'")
                inv_ok = False
            elif witness == "transparent" and risk_level == "high":
                record("WARN", field, "high-risk skill exports implementation details")
    if inv_ok and ops_union_ok:
        record("PASS", f"{prefix}.invariants", f"{len(invariants)} invariant law(s)")


# ── Required frontmatter fields ───────────────────────────────────────────────

def validate_required_fields(fm: dict) -> None:
    for field in ("name", "description"):
        if field not in fm:
            record("FAIL", field, f"Required frontmatter field '{field}' is missing")
        else:
            value = fm[field]
            if not isinstance(value, str) or not value.strip():
                record("FAIL", field, f"'{field}' must be a non-empty string")
            else:
                record("PASS", field, f"Present ({len(value)} chars)")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} path/to/SKILL.md", file=sys.stderr)
        sys.exit(2)

    path = sys.argv[1]
    print(f"\nValidating SSL frontmatter: {path}")

    # 1. Extract frontmatter
    raw_yaml, err = extract_frontmatter(path)
    if err or raw_yaml is None:
        record("FAIL", "frontmatter", err or "Could not extract frontmatter")
        print_results()
        sys.exit(1)

    # 2. Parse YAML
    fm, warn = parse_yaml(raw_yaml)
    if fm is None:
        record("FAIL", "yaml-parse", warn or "YAML parse failed")
        print_results()
        sys.exit(1)
    if warn:
        record("WARN", "yaml-module", warn)

    # 3. Required base fields
    validate_required_fields(fm)

    # 4. Check SSL presence at all
    ssl_keys = [k for k in fm if k.startswith("ssl_")]
    if not ssl_keys:
        record("WARN", "ssl_*", "No ssl_ blocks found — this skill has no SSL metadata")
        print_results()
        sys.exit(0)   # WARN but not FAIL for absence of SSL (it's optional)

    record("PASS", "ssl_presence", f"SSL blocks found: {ssl_keys}")

    # 5. Validate each block
    scheduling = fm.get("ssl_scheduling")
    structural = fm.get("ssl_structural")
    logical = fm.get("ssl_logical")
    validate_ssl_scheduling(scheduling)
    validate_ssl_structural(structural)
    validate_ssl_logical(logical, structural=structural if isinstance(structural, dict) else None)

    # 6. Print summary and exit
    print_results()
    sys.exit(1 if has_fail else 0)


if __name__ == "__main__":
    main()
