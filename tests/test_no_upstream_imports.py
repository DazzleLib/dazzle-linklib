"""AC-4 canary: dazzle-linklib (L2) must never import UP the stack.

Dependencies point DOWN only (STACK-MAP R2). L2 may consume the bedrock
``dazzle_lib`` (B) and -- as delegation code lands -- ``dazzle_filekit`` (L1)
and ``unctools`` (L0). It must import NOTHING from its consumers: the
``dazzlelink`` CLI tool or ``preservelib`` (L3). A violation here means a
circular dependency that would make the library un-shippable on its own.
"""

import ast
import pathlib

PACKAGE_ROOT = pathlib.Path(__file__).resolve().parent.parent / "dazzle_linklib"

# Top-level module names that would represent an upward (consumer) import.
FORBIDDEN_ROOTS = {"dazzlelink", "preservelib", "preserve"}


def _iter_imported_roots(py_file):
    tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name.split(".")[0]
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:  # ignore relative intra-package imports
                yield node.module.split(".")[0]


def test_no_imports_from_consumers():
    offenders = []
    for py_file in PACKAGE_ROOT.rglob("*.py"):
        for root in _iter_imported_roots(py_file):
            if root in FORBIDDEN_ROOTS:
                offenders.append(f"{py_file.name} imports '{root}'")
    assert not offenders, (
        "dazzle-linklib (L2) must not import its consumers (deps point down "
        f"only, STACK-MAP R2): {offenders}"
    )
