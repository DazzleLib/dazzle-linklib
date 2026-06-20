"""Tests for the ``DazzleLinkData`` record model (stack phase P2).

Covers the design DWP acceptance checks for the record port:
  AC-1  every existing .dazzlelink form round-trips (v1 JSON, legacy flat,
        polyglot embedded-script, BOM-prefixed);
  AC-2  typed url/ipfs locators + content_id round-trip without breaking
        path-only records;
  bedrock conformance: DazzleLinkData satisfies dazzle_lib.Serializable and is a
        DazzleDataMixin; DazzleLinkError is rooted under the stack hierarchy.
"""

import json

import pytest

import dazzle_lib
from dazzle_linklib import DazzleLinkData, DazzleLinkError, DazzleLinkException


# --- bedrock conformance --------------------------------------------------

def test_satisfies_serializable_protocol():
    rec = DazzleLinkData()
    assert isinstance(rec, dazzle_lib.Serializable)
    assert DazzleLinkData.SCHEMA_VERSION == 1


def test_is_dazzle_data_mixin():
    rec = DazzleLinkData()
    assert isinstance(rec, dazzle_lib.DazzleDataMixin)
    # to_json comes from the mixin and must emit parseable JSON.
    parsed = json.loads(rec.to_json())
    assert parsed["schema_version"] == 1


def test_exception_rooted_in_stack():
    assert issubclass(DazzleLinkError, dazzle_lib.LinkError)
    assert issubclass(DazzleLinkError, dazzle_lib.DazzleError)


def test_exception_backcompat_alias():
    assert DazzleLinkException is DazzleLinkError


# --- to_dict / from_dict round-trip ---------------------------------------

def test_to_dict_from_dict_round_trip():
    rec = DazzleLinkData()
    rec.set_original_path(r"C:\code\dazzlelink\README.md")
    rec.set_target_path(r"D:\target\README.md")
    rec.set_default_mode("open")
    rec.set_platform("windows")

    clone = DazzleLinkData.from_dict(json.loads(json.dumps(rec.to_dict())))
    assert clone.get_original_path() == r"C:\code\dazzlelink\README.md"
    assert clone.get_target_path() == r"D:\target\README.md"
    assert clone.get_default_mode() == "open"
    assert clone.get_platform() == "windows"


def test_fresh_record_has_v1_schema():
    rec = DazzleLinkData()
    d = rec.to_dict()
    assert d["schema_version"] == 1
    for section in ("link", "target", "security", "config", "dazzlelink_metadata"):
        assert section in d


def test_update_metadata_appends_history():
    rec = DazzleLinkData()
    before = len(rec.get_update_history())
    rec.update_metadata("rebased")
    assert rec.get_update_history()[-1] == "rebased"
    assert len(rec.get_update_history()) == before + 1


# --- AC-1: on-disk form round-trips ---------------------------------------

def test_plain_v1_json_round_trip(tmp_path):
    rec = DazzleLinkData()
    rec.set_original_path("orig/path")
    rec.set_target_path("target/path")
    p = tmp_path / "a.dazzlelink"
    assert rec.save_to_file(str(p)) is True

    loaded = DazzleLinkData.from_file(str(p))
    assert loaded.get_original_path() == "orig/path"
    assert loaded.get_target_path() == "target/path"


def test_legacy_flat_format_read(tmp_path):
    # Legacy flat records stored target_path at the top level.
    p = tmp_path / "flat.dazzlelink"
    p.write_text(json.dumps({"target_path": r"D:\old\target.txt"}), encoding="utf-8")
    rec = DazzleLinkData.from_file(str(p))
    assert rec.get_target_path() == r"D:\old\target.txt"


def test_embedded_script_exact_line_marker(tmp_path):
    # The polyglot executable form puts JSON after a standalone
    # '# DAZZLELINK_DATA_BEGIN' line. The marker literal also appears earlier in
    # the generated script's own source -- a substring search (the source bug)
    # would grab the decoy; we must match the EXACT line.
    script = (
        "#!/usr/bin/env python\n"
        "# decoy mentioning the # DAZZLELINK_DATA_BEGIN marker in a comment\n"
        "print('open target')\n"
        "# DAZZLELINK_DATA_BEGIN\n"
        + json.dumps({"link": {"original_path": "embedded/path"}})
        + "\n"
    )
    p = tmp_path / "exe.dazzlelink"
    p.write_text(script, encoding="utf-8")
    rec = DazzleLinkData.from_file(str(p))
    assert rec.get_original_path() == "embedded/path"


def test_bom_prefixed_file(tmp_path):
    p = tmp_path / "bom.dazzlelink"
    payload = json.dumps({"link": {"original_path": "bom/path"}}).encode("utf-8")
    p.write_bytes(b"\xef\xbb\xbf" + payload)
    rec = DazzleLinkData.from_file(str(p))
    assert rec.get_original_path() == "bom/path"


def test_invalid_file_raises(tmp_path):
    p = tmp_path / "bad.dazzlelink"
    p.write_text("not json and has no marker", encoding="utf-8")
    with pytest.raises(DazzleLinkError):
        DazzleLinkData.from_file(str(p))


def test_missing_file_raises(tmp_path):
    with pytest.raises(DazzleLinkError):
        DazzleLinkData.from_file(str(tmp_path / "does-not-exist.dazzlelink"))


# --- AC-2: typed locators + content_id + relations ------------------------

def test_explicit_locators_round_trip():
    rec = DazzleLinkData()
    rec.add_locator("url", "https://example.com/x")
    rec.add_locator("ipfs", "QmHash")
    clone = DazzleLinkData.from_dict(json.loads(json.dumps(rec.to_dict())))
    kinds = {(l["kind"], l["value"]) for l in clone.get_locators()}
    assert ("url", "https://example.com/x") in kinds
    assert ("ipfs", "QmHash") in kinds


def test_legacy_target_representations_surface_as_locators():
    rec = DazzleLinkData()
    rec.data["link"]["target_representations"] = {
        "original_path": "/abs/p",
        "relative_path": "../p",
        "unc_path": r"\\srv\share\p",
        "drive_path": r"Z:\p",
    }
    kinds = {(l["kind"], l["value"]) for l in rec.get_locators()}
    assert ("path", "/abs/p") in kinds
    assert ("relative", "../p") in kinds
    assert ("unc", r"\\srv\share\p") in kinds
    assert ("drive", r"Z:\p") in kinds


def test_locators_dedup_legacy_and_explicit():
    rec = DazzleLinkData()
    rec.data["link"]["target_representations"] = {"original_path": "/abs/p"}
    # Same (kind, value) added explicitly must not duplicate.
    rec.add_locator("path", "/abs/p")
    locs = [l for l in rec.get_locators() if l == {"kind": "path", "value": "/abs/p"}]
    assert len(locs) == 1


def test_content_id_round_trip():
    rec = DazzleLinkData()
    rec.set_content_id("sha256", "deadbeef")
    clone = DazzleLinkData.from_dict(json.loads(json.dumps(rec.to_dict())))
    assert clone.get_content_id() == {"algorithm": "sha256", "digest": "deadbeef"}


def test_relations_round_trip():
    rec = DazzleLinkData()
    rec.add_relation("derived_from", "cafef00d", {"note": "test"})
    clone = DazzleLinkData.from_dict(json.loads(json.dumps(rec.to_dict())))
    rels = clone.get_relations()
    assert len(rels) == 1
    assert rels[0]["kind"] == "derived_from"
    assert rels[0]["target_content_id"] == "cafef00d"
    assert rels[0]["attrs"] == {"note": "test"}


def test_path_only_record_gains_no_l2_keys():
    # A plain path record must not sprout content_id/relations it never set --
    # additive generalization must stay invisible to legacy consumers.
    rec = DazzleLinkData()
    rec.set_original_path("p")
    d = rec.to_dict()
    assert "content_id" not in d
    assert "relations" not in d
    assert rec.get_content_id() is None
    assert rec.get_relations() == []


def test_link_and_target_timestamps_apply_iso():
    rec = DazzleLinkData()
    rec.set_link_timestamps(modified=1_700_000_000)
    rec.set_target_timestamps(created=1_700_000_001)
    assert rec.get_link_timestamps()["modified"] == 1_700_000_000
    assert rec.get_link_timestamps()["modified_iso"] is not None
    assert rec.get_target_timestamps()["created"] == 1_700_000_001
    assert rec.get_target_timestamps()["created_iso"] is not None
