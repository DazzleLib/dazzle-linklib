"""Tests for the locality axis + selection (0.4.0 #25; monopole reshape 0.5.0).

Covers the #25 DWP Amendment 4 design: the monopole ladder (local at the
rank-0 rest seat, single reach extending outward -- AC-16), the
producer-grounded kind->rung map (ssh/sftp/ftp deliberately rung-less --
AC-19), the selector spelling chain rung -> reach alias -> scheme alias ->
registry-free kind fallthrough (AC-17/18), rank-distance preference ordering
(AC-13), SchemeAwareReachability (AC-6), and preference-beats-presence at the
resolver level (AC-10).
"""

import os

import pytest

from dazzle_linklib import (
    LOCALITY_CONTINUUM,
    LOCALITY_SPACE,
    REACH_ALIASES,
    SCHEME_ALIASES,
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


# --- ladder contract (AC-16) --------------------------------------------------

def test_ladder_contract():
    # The rest seat IS the default: rank 0 = local possession (monopole).
    assert LOCALITY_CONTINUUM.neutral() == "local"
    assert LOCALITY_CONTINUUM.subtype == "monopole"
    assert LOCALITY_CONTINUUM.warm_pole() == "local"
    # warm = more possessed (house presence convention, oracle-verified).
    assert LOCALITY_CONTINUUM.is_warmer("local", "internet")
    assert LOCALITY_CONTINUUM.rank("local") == 0
    assert LOCALITY_CONTINUUM.rank("intranet") == -1
    assert LOCALITY_CONTINUUM.rank("internet") == -2
    assert set(REACH_ALIASES) == {"local-network", "remote"}
    assert set(SCHEME_ALIASES) == {"http", "https", "url"}
    # the space hook-up exists and carries the axis
    assert LOCALITY_SPACE.axis("locality") is LOCALITY_CONTINUUM


def test_kind_rung_map_is_producer_grounded():
    assert locator_rung("path") == "local"
    assert locator_rung("relative") == "local"
    assert locator_rung("subst") == "local"       # expanded real local path
    assert locator_rung("drive") == "intranet"    # a mapped letter IS the share
    assert locator_rung("unc") == "intranet"
    assert locator_rung("url") == "internet"
    assert locator_rung("ipfs") == "internet"
    # AC-19: recognized kinds with NO producer vouching for locality get no
    # rung -- same treatment as unknown kinds, never guessed.
    assert locator_rung("ssh") is None
    assert locator_rung("sftp") is None
    assert locator_rung("ftp") is None
    assert locator_rung("no-such-kind") is None


def test_reach_of_regions():
    assert reach_of("local") == "local"
    assert reach_of("intranet") == "local-network"
    assert reach_of("internet") == "remote"


# --- the spelling chain (AC-17) -------------------------------------------------

def test_resolve_rung_spelling_chain():
    # rung names
    assert resolve_rung("local") == "local"
    assert resolve_rung("intranet") == "intranet"
    assert resolve_rung("internet") == "internet"
    # reach aliases
    assert resolve_rung("remote") == "internet"
    assert resolve_rung("local-network") == "intranet"
    # scheme aliases (AC-17): tier semantics for the common web spellings
    assert resolve_rung("http") == "internet"
    assert resolve_rung("https") == "internet"
    assert resolve_rung("url") == "internet"
    # anything else is NOT a rung spelling -- the selection functions treat it
    # as a kind (fallthrough); resolve_rung itself still refuses, naming the
    # rung/alias vocabulary.
    with pytest.raises(DazzleLinkError) as ei:
        resolve_rung("gopher")
    msg = str(ei.value)
    assert "intranet" in msg and "remote" in msg and "https" in msg


# --- preference ordering (AC-13 + AC-18) -----------------------------------------

def test_order_by_preference_rank_distance():
    locs = [_loc("path", "a"), _loc("unc", "b"), _loc("url", "c")]
    # prefer internet: url (d=0) -> unc (d=1) -> path (d=2)
    kinds = [l["kind"] for l in order_by_preference(locs, "internet")]
    assert kinds == ["url", "unc", "path"]
    # prefer local derives the default order formally
    kinds = [l["kind"] for l in order_by_preference(locs, "local")]
    assert kinds == ["path", "unc", "url"]
    # reach + scheme aliases behave as their rung
    for spelling in ("remote", "http", "url"):
        assert ([l["kind"] for l in order_by_preference(locs, spelling)]
                == [l["kind"] for l in order_by_preference(locs, "internet")])


def test_order_by_preference_stable_and_rungless_last():
    locs = [_loc("path", "a"), _loc("relative", "b"),
            _loc("ssh", "s"), _loc("url", "c")]
    ordered = order_by_preference(locs, "local")
    # path and relative share the local rung: original order kept (stable)
    assert [l["kind"] for l in ordered][:2] == ["path", "relative"]
    # rung-less kind (ssh, AC-19) sorts last under a rung preference
    assert ordered[-1]["kind"] == "ssh"


def test_kind_fallthrough_preference_is_registry_free():
    # AC-18: any non-rung spelling is a kind preference -- including kinds no
    # registry knows (gopher) and rung-less recognized kinds (ftp).
    locs = [_loc("path", "a"), _loc("ftp", "f"), _loc("gopher", "g")]
    assert [l["kind"] for l in order_by_preference(locs, "ftp")][0] == "ftp"
    assert [l["kind"] for l in order_by_preference(locs, "gopher")][0] == "gopher"
    # preference is not a filter: everything else remains, in original order
    assert [l["kind"] for l in order_by_preference(locs, "gopher")][1:] == ["path", "ftp"]


# --- reach / kind filtering (AC-18, AC-19) ----------------------------------------

def test_filter_by_reach_rung_and_aliases():
    locs = [_loc("path", "a"), _loc("unc", "b"), _loc("drive", "d"), _loc("url", "c")]
    assert [l["kind"] for l in filter_by_reach(locs, "local-network")] == ["unc", "drive"]
    assert [l["kind"] for l in filter_by_reach(locs, "intranet")] == ["unc", "drive"]
    assert [l["kind"] for l in filter_by_reach(locs, "remote")] == ["url"]
    assert [l["kind"] for l in filter_by_reach(locs, "http")] == ["url"]  # scheme alias
    assert [l["kind"] for l in filter_by_reach(locs, "local")] == ["path"]


def test_filter_kind_fallthrough():
    locs = [_loc("unc", "b"), _loc("ftp", "f"), _loc("gopher", "g")]
    # AC-18: --only <kind> filters to exactly that kind, registry-free.
    assert [l["kind"] for l in filter_by_reach(locs, "ftp")] == ["ftp"]
    assert [l["kind"] for l in filter_by_reach(locs, "gopher")] == ["gopher"]
    # a spelling matching nothing yields [] -- the record is the validator.
    assert filter_by_reach(locs, "archie") == []


def test_rungless_kinds_never_match_rung_spellings():
    # AC-19: ssh/ftp are excluded by every reach filter (no rung, no guess)...
    locs = [_loc("ssh", "s"), _loc("ftp", "f")]
    for spelling in ("local", "local-network", "remote"):
        assert filter_by_reach(locs, spelling) == []
    # ...but stay selectable by name.
    assert [l["kind"] for l in filter_by_reach(locs, "ssh")] == ["ssh"]


# --- SchemeAwareReachability (AC-6) ---------------------------------------------

def test_scheme_aware_matrix(tmp_path):
    checker = SchemeAwareReachability()
    real = tmp_path / "x.txt"
    real.write_text("x", encoding="utf-8")
    assert checker.is_reachable("https://example.org/a b.pdf") is True  # spaced URL
    assert checker.is_reachable("ipfs://QmHash") is True
    assert checker.is_reachable("gopher://old.net/doc") is True  # any scheme
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
    # AC-10: the local file EXISTS and the URL still wins under preference --
    # via the reach alias, the rung, and the scheme aliases (AC-17).
    rec, _local = _two_target_record(tmp_path)
    for spelling in ("remote", "internet", "http", "url"):
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


def test_only_kind_fallthrough_resolves(tmp_path):
    # AC-18 at the resolver: --only <kind spelling> walks only that kind.
    rec, local = _two_target_record(tmp_path)
    hit = resolve_target(
        rec, reachability=SchemeAwareReachability(), only="url"
    )
    # NOTE: "url" is a scheme ALIAS (tier), which here selects the same single
    # locator; a pure fallthrough kind needs a non-alias spelling:
    rec.add_locator("gopher", "gopher://old.net/doc.pdf")
    hit = resolve_target(
        rec, reachability=SchemeAwareReachability(), only="gopher"
    )
    assert hit == {"kind": "gopher", "value": "gopher://old.net/doc.pdf"}


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
