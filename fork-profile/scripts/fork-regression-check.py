#!/usr/bin/env python3
"""Regression check for hermes-fork protected symbols post-merge.

Exits 0 and prints "ok" if all checks pass.
Exits 1 and prints FAIL lines if any check fails.
"""
import ast
import importlib
import pathlib
import sys

FORK = pathlib.Path("/var/home/rainbow/.hermes/hermes-fork")
sys.path.insert(0, str(FORK))

errors = []

# Import smoke
for mod in ["agent.context_compressor", "hermes_cli.plugins", "agent.conversation_compression"]:
    try:
        importlib.import_module(mod)
    except Exception as e:
        errors.append(f"import FAIL {mod}: {e}")

# Protected classes in context_compressor
cc = FORK / "agent" / "context_compressor.py"
try:
    tree = ast.parse(cc.read_text())
    classes = {n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)}
    for sym in ["StaleHeldHistory", "_HandoffScan", "_SummaryFailureKind", "ContextCompressor"]:
        if sym not in classes:
            errors.append(f"missing class {sym} in context_compressor.py")
    # classmethod self-bug scan
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

# Protected function in conversation_compression
cv = FORK / "agent" / "conversation_compression.py"
try:
    tree2 = ast.parse(cv.read_text())
    fnames = {n.name for n in ast.walk(tree2) if isinstance(n, ast.FunctionDef)}
    if "compress_context" not in fnames:
        errors.append("missing function compress_context in conversation_compression.py")
except Exception as e:
    errors.append(f"parse error conversation_compression.py: {e}")

if errors:
    for e in errors:
        print(f"FAIL: {e}")
    sys.exit(1)
else:
    print("ok")
