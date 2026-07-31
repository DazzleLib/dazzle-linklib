"""Tests for the locality axis + selection (0.4.0, issue dazzlelink#25).

Covers the Amendment-2 design: the LOCALITY Continuum contract, kind->rung
mapping, reach aliases, rank-distance preference ordering (AC-13), reach
filtering, SchemeAwareReachability (AC-6), and preference-beats-presence at the
resolver level (AC-10).
"""

import os

import pytest

from dazzle_linklib import (
    LOCALITY_CONTINUUM,
    LOCALITY_SPACE,
    REACH_ALIASES,
    DazzleLinkData,
    DazzleLinkError,
    SchemeAwareReachability,
    filter_by_reach,
    locator_rung,
    order_by_preference,
    reach_of,
    resolve_rung,
    resolve_target,
)


def _loc(kind, value):
    return {"kind": kind, "value": value}


# --- ladder contract ---------------------------------------------------------

def test_ladder_contract():
    assert LOCALITY_CONTINUUM.neutral() == "machine"
    assert LOCALITY_CONTINUUM.subtype == "full"
    assert LOCALITY_CONTINUUM.rank("file") > 0 > LOCALITY_CONTINUUM.rank("internet")
    # warm = more present = local possession
    assert LOCALITY_CONTINUUM.is_warmer("file", "internet")
    assert set(REACH_ALIASES) == {"local", "local-network", "remote"}
    # the space hook-up exists and carries the axis
    assert LOCALITY_SPACE.axis("locality") is LOCALITY_CONTINUUM


def test_kind_rung_map():
    assert locator_rung("path") == "file"
    assert locator_rung("relative") == "file"
    assert locator_rung("subst") == "file"      # expanded real local path
    assert locator_rung("drive") == "unc"       # a mapped letter IS the share
    assert locator_rung("unc") == "unc"
    assert locator_rung("url") == "internet"
    assert locator_rung("ipfs") == "internet"
    assert locator_rung("no-such-kind") is None  # never guessed


def test_reach_of_regions():
    assert reach_of("file") == "local"
    assert reach_of("machine") == "boundary"
    assert reach_of("unc") == "local-network"
    assert reach_of("ftp") == "local-network"
    assert reach_of("internet") == "remote"


def test_resolve_rung_accepts_rungs_and_aliases():
    assert resolve_rung("internet") == "internet"
    assert resolve_rung("remote") == "internet"
    assert resolve_rung("local") == "file"
    assert resolve_rung("local-network") == "unc"
    with pytest.raises(DazzleLinkError) as ei:
        resolve_rung("nearby")
    # error names the valid vocabulary
    assert "internet" in str(ei.value) and "remote" in str(ei.value)


# --- preference ordering (AC-13) ----------------------------------------------

def test_order_by_preference_rank_distance():
    locs = [_loc("path", "a"), _loc("unc", "b"), _loc("url", "c")]
    # prefer internet: url (d=0) -> unc (d=3) -> path/file (d=7)
    kinds = [l["kind"] for l in order_by_preference(locs, "internet")]
    assert kinds == ["url", "unc", "path"]
    # prefer ssh (-2): unc (d=1) -> url (d=2) -> path (d=5)
    kinds = [l["kind"] for l in order_by_preference(locs, "ssh")]
    assert kinds == ["unc", "url", "path"]
    # reach alias works the same as its representative rung
    assert ([l["kind"] for l in order_by_preference(locs, "remote")]
            == [l["kind"] for l in order_by_preference(locs, "internet")])


def test_order_by_preference_stable_and_unknown_last():
    locs = [_loc("path", "a"), _loc("relative", "b"),
            _loc("mystery", "m"), _loc("url", "c")]
    ordered = order_by_preference(locs, "file")
    # path and relative share the file rung: original order kept (stable)
    assert [l["kind"] for l in ordered][:2] == ["path", "relative"]
    # unknown kind sorts last, after even the farthest known rung
    assert ordered[-1]["kind"] == "mystery"


# --- reach filtering -----------------------------------------------------------

def test_filter_by_reach_alias_selects_region():
    locs = [_loc("path", "a"), _loc("unc", "b"), _loc("ftp", "f"), _loc("url", "c")]
    kinds = [l["kind"] for l in filter_by_reach(locs, "local-network")]
    assert kinds == ["unc", "ftp"]


def test_filter_by_reach_rung_is_exact():
    locs = [_loc("unc", "b"), _loc("ftp", "f")]
    assert [l["kind"] for l in filter_by_reach(locs, "unc")] == ["unc"]


def test_filter_by_reach_unknown_kind_never_matches():
    locs = [_loc("mystery", "m")]
    assert filter_by_reach(locs, "remote") == []


# --- SchemeAwareReachability (AC-6) ---------------------------------------------

def test_scheme_aware_matrix(tmp_path):
    checker = SchemeAwareReachability()
    real = tmp_path / "x.txt"
    real.write_text("x", encoding="utf-8")
    assert checker.is_reachable("https://example.org/a b.pdf") is True  # spaced URL
    assert checker.is_reachable("ipfs://QmHash") is True
    assert checker.is_reachable(str(real)) is True
    assert checker.is_reachable(str(tmp_path / "missing")) is False
    assert checker.is_reachable(r"\\srv\share\x") is False   # UNC: exists-semantics
    assert checker.is_reachable(r"C:\nonexistent\p") is False  # drive letter != scheme
    assert checker.is_reachable("") is False
    assert checker.is_reachable(None) is False  # never raises


# --- resolver integration --------------------------------------------------------

def _two_target_record(tmp_path):
    local = tmp_path / "doc.pdf"
    local.write_text("pdf", encoding="utf-8")
    rec = DazzleLinkData()
    rec.set_target_path(str(local))
    rec.add_locator("url", "https://example.org/doc.pdf")
    return rec, local


def test_default_order_local_wins(tmp_path):
    rec, local = _two_target_record(tmp_path)
    hit = resolve_target(rec, reachability=SchemeAwareReachability())
    assert hit["value"] == str(local)


def test_prefer_remote_beats_local_presence(tmp_path):
    # AC-10: the local file EXISTS and the URL still wins under preference.
    rec, _local = _two_target_record(tmp_path)
    for spelling in ("remote", "internet"):
        hit = resolve_target(
            rec, reachability=SchemeAwareReachability(), prefer=spelling
        )
        assert hit == {"kind": "url", "value": "https://example.org/doc.pdf"}


def test_url_only_record_resolves(tmp_path):
    rec = DazzleLinkData()
    rec.add_locator("url", "https://example.org/only.pdf")
    hit = resolve_target(rec, reachability=SchemeAwareReachability())
    assert hit["kind"] == "url"


def test_only_filter_and_no_match_is_none(tmp_path):
    rec, local = _two_target_record(tmp_path)
    hit = resolve_target(rec, reachability=SchemeAwareReachability(), only="remote")
    assert hit["kind"] == "url"
    assert resolve_target(
        rec, reachability=SchemeAwareReachability(), only="local-network"
    ) is None


def test_kinds_filter(tmp_path):
    rec, local = _two_target_record(tmp_path)
    hit = resolve_target(
        rec, reachability=SchemeAwareReachability(), kinds=["url"]
    )
    assert hit["kind"] == "url"


def test_fallback_survives_preference(tmp_path):
    # Preference is not a filter: with the URL kind filtered OUT and remote
    # preferred, the local file still resolves (everything stays fallback).
    rec, local = _two_target_record(tmp_path)
    hit = resolve_target(
        rec, reachability=SchemeAwareReachability(),
        prefer="remote", kinds=["path", "relative", "unc", "drive", "subst"],
    )
    assert hit["value"] == str(local)


def test_defaults_unchanged_without_selectors(tmp_path):
    # 0.3.0 behavior byte-identical when no selector args are passed: the
    # default checker still reports urls unreachable.
    rec, local = _two_target_record(tmp_path)
    hit = resolve_target(rec)
    assert hit["value"] == str(local)
    os.unlink(str(local))
    assert resolve_target(rec) is None
