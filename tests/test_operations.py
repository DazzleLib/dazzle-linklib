"""Tests for the record-centric operations (export/import/create/recreate).

The create/recreate tests need real symlink creation, which on Windows requires
Developer Mode or elevation. They skip cleanly where symlinks aren't permitted,
so CI without that privilege stays green while still exercising the OS mechanic
where it is available.
"""

import os

import pytest

from dazzle_linklib import (
    DazzleLinkData,
    create_link,
    export_link,
    import_link,
    recreate_link,
)


def _symlinks_available(tmp_path):
    target = tmp_path / "_probe_target"
    target.write_text("x", encoding="utf-8")
    link = tmp_path / "_probe_link"
    try:
        os.symlink(target, link)
    except (OSError, NotImplementedError):
        return False
    return os.path.islink(link)


@pytest.fixture
def needs_symlinks(tmp_path):
    if not _symlinks_available(tmp_path):
        pytest.skip("symlink creation not permitted on this platform/account")


# --- export_link / import_link (no symlinks; always run) ------------------

def test_export_import_round_trip(tmp_path):
    rec = DazzleLinkData()
    rec.set_original_path("orig")
    rec.set_target_path("target")
    p = tmp_path / "a.dazzlelink"

    assert export_link(rec, str(p)) is True
    loaded = import_link(str(p))
    assert isinstance(loaded, DazzleLinkData)
    assert loaded.get_original_path() == "orig"
    assert loaded.get_target_path() == "target"


# --- create_link ----------------------------------------------------------

def test_create_link_makes_symlink(tmp_path, needs_symlinks):
    target = tmp_path / "real.txt"
    target.write_text("hi", encoding="utf-8")
    link = tmp_path / "link.txt"

    rec = DazzleLinkData()
    rec.set_target_path(str(target))

    created = create_link(rec, str(link))
    assert os.path.islink(created)
    assert os.path.realpath(created) == os.path.realpath(str(target))


def test_create_link_defaults_to_original_path(tmp_path, needs_symlinks):
    target = tmp_path / "real.txt"
    target.write_text("hi", encoding="utf-8")
    link = tmp_path / "from_original.txt"

    rec = DazzleLinkData()
    rec.set_target_path(str(target))
    rec.set_original_path(str(link))

    created = create_link(rec)  # no link_path -> original_path
    assert os.path.realpath(created) == os.path.realpath(str(link))
    assert os.path.islink(link)


def test_create_link_without_target_raises(tmp_path):
    from dazzle_linklib import DazzleLinkError

    rec = DazzleLinkData()  # no target_path
    rec.set_original_path(str(tmp_path / "l"))
    with pytest.raises(DazzleLinkError):
        create_link(rec)


# --- recreate_link (the keystone workflow) --------------------------------

def test_recreate_link_from_record_file(tmp_path, needs_symlinks):
    # Author a record pointing at a real target, save it, delete the link,
    # then recreate the link from the .dazzlelink alone (the anti-link-rot path).
    target = tmp_path / "asset.bin"
    target.write_text("payload", encoding="utf-8")
    link = tmp_path / "asset.lnk"

    rec = DazzleLinkData()
    rec.set_target_path(str(target))
    rec.set_original_path(str(link))
    dl = tmp_path / "asset.dazzlelink"
    rec.save_to_file(str(dl))

    recreated = recreate_link(str(dl))
    assert os.path.islink(recreated)
    assert os.path.realpath(recreated) == os.path.realpath(str(target))


def test_recreate_link_target_location_override(tmp_path, needs_symlinks):
    target = tmp_path / "asset.bin"
    target.write_text("payload", encoding="utf-8")
    link = tmp_path / "orig" / "asset.lnk"
    (tmp_path / "orig").mkdir()

    rec = DazzleLinkData()
    rec.set_target_path(str(target))
    rec.set_original_path(str(link))
    dl = tmp_path / "asset.dazzlelink"
    rec.save_to_file(str(dl))

    dest = tmp_path / "elsewhere"
    dest.mkdir()
    recreated = recreate_link(str(dl), target_location=str(dest))
    # Recreated under dest, keeping the original filename.
    assert os.path.dirname(recreated) == str(dest)
    assert os.path.basename(recreated) == "asset.lnk"
    assert os.path.islink(recreated)


def test_recreate_link_restores_windows_attributes(tmp_path, needs_symlinks):
    import sys

    if sys.platform != "win32":
        pytest.skip("file attributes are a Windows concern")
    import ctypes

    target = tmp_path / "asset.bin"
    target.write_text("payload", encoding="utf-8")
    link = tmp_path / "asset.lnk"

    rec = DazzleLinkData()
    rec.set_target_path(str(target))
    rec.set_original_path(str(link))
    rec.data["link"]["attributes"] = {"hidden": True, "system": False, "readonly": True}
    dl = tmp_path / "asset.dazzlelink"
    rec.save_to_file(str(dl))

    recreated = recreate_link(str(dl))
    attrs = ctypes.windll.kernel32.GetFileAttributesW(recreated)
    assert attrs & 0x2  # FILE_ATTRIBUTE_HIDDEN
    assert attrs & 0x1  # FILE_ATTRIBUTE_READONLY
    # The target itself must be untouched.
    tgt_attrs = ctypes.windll.kernel32.GetFileAttributesW(str(target))
    assert not (tgt_attrs & 0x2)
    assert target.read_text(encoding="utf-8") == "payload"


def test_recreate_link_unknown_strategy_raises(tmp_path, needs_symlinks):
    from dazzle_linklib import DazzleLinkError

    target = tmp_path / "asset.bin"
    target.write_text("payload", encoding="utf-8")
    rec = DazzleLinkData()
    rec.set_target_path(str(target))
    rec.set_original_path(str(tmp_path / "asset.lnk"))
    dl = tmp_path / "asset.dazzlelink"
    rec.save_to_file(str(dl))

    with pytest.raises(DazzleLinkError):
        recreate_link(str(dl), timestamp_strategy="bogus")
