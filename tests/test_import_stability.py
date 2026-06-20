"""Import-stability canary (see docs/api-stability.md).

Every symbol listed here is part of the locked public API. If this test
fails, a consumer somewhere breaks: do NOT silently fix the test -- follow
the api-stability.md process (deprecate with a noisy shim, register it,
slate removal).

The record model lands incrementally through P2: ``DazzleLinkData`` and the
exception types are present now; the discovery/resolver surface
(export/import/scan/rebase, ``resolve_target``) joins as it ships.
"""

import importlib

LOCKED_SURFACE = {
    "dazzle_linklib": [
        "__version__",
        "__app_name__",
        "PIP_VERSION",
        # Record model (P2) -- the link record + its stack-rooted exceptions.
        "DazzleLinkData",
        "DazzleLinkError",
        "DazzleLinkException",
        # Discovery + rebase over record files (P2).
        "find_dazzlelinks",
        "scan",
        "rebase",
        # Injectable target resolver (P2).
        "resolve_target",
        "ReachabilityResolver",
        "default_reachability",
    ],
}


def test_locked_surface_importable():
    missing = []
    for module_name, symbols in LOCKED_SURFACE.items():
        module = importlib.import_module(module_name)
        for symbol in symbols:
            if not hasattr(module, symbol):
                missing.append(f"{module_name}.{symbol}")
    assert not missing, (
        f"Locked API symbols missing: {missing} -- see docs/api-stability.md "
        f"before changing the public surface."
    )


def test_package_is_importable():
    """The package imports cleanly with no side effects at import time."""
    mod = importlib.import_module("dazzle_linklib")
    assert isinstance(mod.__version__, str)
    assert mod.__app_name__ == "dazzle-linklib"
