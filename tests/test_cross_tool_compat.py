"""Cross-tool design-validation: the dazzlelink CLI tool <-> dazzle-linklib.

The user's acceptance test for the L2 extraction: *"make sure the library can be
directly imported into dazzlelink as a standalone tool. That's how we'll know if
we are designing the library properly."* This proves the ported record is
**wire-compatible** with the real shipped tool by round-tripping actual
``.dazzlelink`` files in both directions:

  * a file written by the **tool's** ``DazzleLinkData`` reads correctly with the
    **library's** ``DazzleLinkData`` (the library can consume the tool's output);
  * a file written by the **library** reads correctly with the **tool** (the
    tool can consume the library's output -- forward path to thinning the CLI).

It is skipped when the ``dazzlelink`` tool is not installed (e.g. the library's
own CI), so the library never gains a hard dependency on its consumer (AC-4).
"""

import pytest

# Skip the whole module if the consumer tool isn't installed alongside us.
dazzlelink_data = pytest.importorskip("dazzlelink.data")

from dazzle_linklib import DazzleLinkData as LibRecord

ToolRecord = dazzlelink_data.DazzleLinkData


def test_library_imports_standalone():
    """The blunt check: the library imports on its own, no tool required."""
    import importlib

    lib = importlib.import_module("dazzle_linklib")
    assert hasattr(lib, "DazzleLinkData")


def test_tool_file_reads_in_library(tmp_path):
    rec = ToolRecord()
    rec.set_original_path(r"C:\src\file.txt")
    rec.set_target_path(r"D:\dst\file.txt")
    rec.set_default_mode("open")
    rec.set_platform("windows")
    rec.set_link_timestamps(modified=1_700_000_000)

    p = tmp_path / "from_tool.dazzlelink"
    rec.save_to_file(str(p))

    loaded = LibRecord.from_file(str(p))
    assert loaded.get_original_path() == r"C:\src\file.txt"
    assert loaded.get_target_path() == r"D:\dst\file.txt"
    assert loaded.get_default_mode() == "open"
    assert loaded.get_platform() == "windows"
    assert loaded.get_link_timestamps()["modified"] == 1_700_000_000


def test_library_file_reads_in_tool(tmp_path):
    rec = LibRecord()
    rec.set_original_path("orig/path")
    rec.set_target_path("target/path")
    rec.set_default_mode("info")
    rec.set_platform("linux")

    p = tmp_path / "from_lib.dazzlelink"
    rec.save_to_file(str(p))

    loaded = ToolRecord.from_file(str(p))
    assert loaded.get_original_path() == "orig/path"
    assert loaded.get_target_path() == "target/path"
    assert loaded.get_default_mode() == "info"
    assert loaded.get_platform() == "linux"


def test_schema_shapes_match(tmp_path):
    """The two records produce the same top-level schema shape for a v1 record."""
    tool_keys = set(ToolRecord().to_dict().keys())
    lib_keys = set(LibRecord().to_dict().keys())
    # The library is a superset: it may add optional L2 keys later, but every
    # key the tool emits must be present (no field dropped in the port).
    assert tool_keys <= lib_keys, f"library dropped tool keys: {tool_keys - lib_keys}"


def test_l2_extensions_survive_tool_round_trip(tmp_path):
    """D3 additions (locators/content_id) ride along through the tool unharmed.

    The tool doesn't understand these keys, but a generic JSON round-trip must
    not strip them -- so a library->tool->library trip preserves them.
    """
    rec = LibRecord()
    rec.set_original_path("p")
    rec.add_locator("ipfs", "QmHash")
    rec.set_content_id("sha256", "deadbeef")

    p = tmp_path / "ext.dazzlelink"
    rec.save_to_file(str(p))

    # Tool reads + rewrites (round-trips the raw dict it doesn't interpret).
    tool_rec = ToolRecord.from_file(str(p))
    p2 = tmp_path / "ext2.dazzlelink"
    tool_rec.save_to_file(str(p2))

    back = LibRecord.from_file(str(p2))
    assert back.get_content_id() == {"algorithm": "sha256", "digest": "deadbeef"}
    kinds = {(l["kind"], l["value"]) for l in back.get_locators()}
    assert ("ipfs", "QmHash") in kinds
