"""Tests for the 0.3.0 portable path family: path_family / populate_locators,
kind-priority ordering, and the resolver walk (variants= / base_dir=).

Derived from the collabN-local falsification tests T1-T5 (see the Rnd4 final
assessment): AC-B population semantics, AC-C ordering, AC-D base_dir anchoring
+ machine-derived winners, AC-E no at-rest mirror.
"""

import os

from dazzle_linklib import (
    DazzleLinkData,
    default_path_variants,
    path_family,
    populate_locators,
    rebase,
    resolve_target,
)


def fake_variants(mapping):
    """Kinded variant source test double: {input_path: [(kind, value)]}."""

    def source(path):
        return mapping.get(path, [])

    return source


def _other_drive(path):
    """A drive letter different from path's (for cross-drive relpath)."""
    drive = os.path.splitdrive(os.path.abspath(str(path)))[0].upper()
    return "D:" if drive != "D:" else "E:"


# --- AC-C: kind-priority ordering (T1 inverted) -----------------------------

def test_get_locators_priority_order_regardless_of_insertion():
    r = DazzleLinkData()
    r.set_target_path(r"D:\abs\t.txt")
    # Deliberately adversarial insertion order (worst case for dict-order walks).
    r.data["link"]["target_representations"] = {
        "subst_path": r"C:\real\t.txt",
        "drive_path": r"Z:\t.txt",
        "unc_path": r"\\srv\share\t.txt",
        "original_path": r"D:\abs\t.txt",
        "relative_path": "sub/t.txt",
    }
    r.add_locator("url", "https://example.com/t")
    kinds = [l["kind"] for l in r.get_locators()]
    assert kinds == ["path", "relative", "unc", "drive", "subst", "url"]


def test_unknown_legacy_kinds_sort_after_family_alphabetically():
    r = DazzleLinkData()
    r.data["link"]["target_representations"] = {
        "zzz_path": "z", "aaa_path": "a", "unc_path": r"\\s\s\p",
    }
    kinds = [l["kind"] for l in r.get_locators()]
    assert kinds == ["unc", "aaa", "zzz"]


# --- path_family -------------------------------------------------------------

def test_path_family_original_always_and_relative_only_with_base_dir(tmp_path):
    target = tmp_path / "t.txt"
    fam_no_base = path_family(str(target), variants=fake_variants({}))
    assert fam_no_base == {"original_path": str(target)}  # link-side shape

    fam = path_family(str(target), base_dir=str(tmp_path), variants=fake_variants({}))
    assert fam["relative_path"] == "t.txt"


def test_path_family_maps_kinded_variants_to_legacy_keys(tmp_path):
    t = str(tmp_path / "t.txt")
    fam = path_family(
        t,
        variants=fake_variants({t: [("unc", r"\\srv\sh\t.txt"), ("subst", r"C:\real\t.txt")]}),
    )
    assert fam["unc_path"] == r"\\srv\sh\t.txt"
    assert fam["subst_path"] == r"C:\real\t.txt"


def test_path_family_cross_drive_omits_relative(tmp_path):
    t = str(tmp_path / "t.txt")
    fam = path_family(t, base_dir=_other_drive(t) + "\\elsewhere", variants=fake_variants({}))
    assert "relative_path" not in fam


def test_path_family_never_raises_on_bad_variant_source(tmp_path):
    def exploding(_path):
        raise RuntimeError("boom")

    fam = path_family(str(tmp_path / "t.txt"), variants=exploding)
    assert "original_path" in fam


# --- AC-B: populate_locators three-way refresh --------------------------------

def test_populate_writes_relative_and_variants(tmp_path):
    target = tmp_path / "asset.bin"
    target.write_text("x", encoding="utf-8")
    rec = DazzleLinkData()
    rec.set_target_path(str(target))

    reps = populate_locators(
        rec,
        record_dir=str(tmp_path),
        variants=fake_variants({str(target): [("unc", r"\\srv\sh\asset.bin")]}),
    )
    assert reps["relative_path"] == "asset.bin"
    assert reps["unc_path"] == r"\\srv\sh\asset.bin"
    assert reps["original_path"] == str(target)


def test_populate_overwrites_computed_but_preserves_uncomputed_variants(tmp_path):
    # Machine B computes no unc variant: the stored one (from machine A) SURVIVES.
    target = tmp_path / "asset.bin"
    rec = DazzleLinkData()
    rec.set_target_path(str(target))
    rec.data["link"]["target_representations"] = {
        "unc_path": r"\\machineA\share\asset.bin",  # someone else's portable fact
        "relative_path": "WRONG/stale.txt",
    }
    reps = populate_locators(rec, record_dir=str(tmp_path), variants=fake_variants({}))
    assert reps["unc_path"] == r"\\machineA\share\asset.bin"  # preserved
    assert reps["relative_path"] == "asset.bin"  # recomputed (overwrite)


def test_populate_cross_drive_REMOVES_stale_relative(tmp_path):
    # Provable absence: with a known record_dir on another drive, no valid
    # relative exists -- the stale one must be REMOVED (it would outrank
    # working unc/drive forms at resolve time).
    target = tmp_path / "asset.bin"
    rec = DazzleLinkData()
    rec.set_target_path(str(target))
    rec.data["link"]["target_representations"] = {"relative_path": "stale/rel.txt"}
    reps = populate_locators(
        rec, record_dir=_other_drive(target) + "\\records", variants=fake_variants({})
    )
    assert "relative_path" not in reps


def test_populate_without_record_dir_preserves_relative(tmp_path):
    # Couldn't compute (no anchor) -> preserve.
    rec = DazzleLinkData()
    rec.set_target_path(str(tmp_path / "t.txt"))
    rec.data["link"]["target_representations"] = {"relative_path": "keep/me.txt"}
    reps = populate_locators(rec, variants=fake_variants({}))
    assert reps["relative_path"] == "keep/me.txt"


def test_populate_idempotent_second_call_refreshes_no_dupes(tmp_path):
    target = tmp_path / "t.txt"
    rec = DazzleLinkData()
    rec.set_target_path(str(target))
    v = fake_variants({str(target): [("unc", r"\\s\sh\t.txt")]})
    populate_locators(rec, record_dir=str(tmp_path), variants=v)
    populate_locators(rec, record_dir=str(tmp_path), variants=v)
    reps = rec.get_target_representations()
    assert list(reps.keys()).count("unc_path") == 1
    kinds = [l["kind"] for l in rec.get_locators()]
    assert kinds.count("unc") == 1


def test_populate_no_target_is_noop():
    rec = DazzleLinkData()
    assert populate_locators(rec, record_dir=".") == {}


def test_populate_never_touches_unknown_keys_or_original(tmp_path):
    target = tmp_path / "t.txt"
    rec = DazzleLinkData()
    rec.set_target_path(str(target))
    rec.data["link"]["target_representations"] = {
        "original_path": "SOMEONE/ELSES/alias",
        "custom_path": "keep",
    }
    reps = populate_locators(rec, record_dir=str(tmp_path), variants=fake_variants({}))
    assert reps["original_path"] == "SOMEONE/ELSES/alias"
    assert reps["custom_path"] == "keep"


# --- AC-D: resolver walk (base_dir anchoring + variant expansion) -------------

def test_resolve_relative_from_any_cwd_with_base_dir(tmp_path, monkeypatch):
    # T2 fixed: base_dir anchors relative locators; CWD is irrelevant.
    recdir = tmp_path / "records"
    recdir.mkdir()
    real = recdir / "real.bin"
    real.write_text("x", encoding="utf-8")
    rec = DazzleLinkData()
    rec.data["link"]["target_representations"] = {"relative_path": "real.bin"}

    monkeypatch.chdir(tmp_path)  # a WRONG cwd on purpose
    assert resolve_target(rec) is None  # documented CWD-dependence without base_dir
    hit = resolve_target(rec, base_dir=str(recdir))
    assert hit is not None
    assert os.path.normcase(hit["value"]) == os.path.normcase(str(real))
    assert hit["kind"] == "relative"


def test_resolve_via_machine_derived_variant(tmp_path):
    # Stored form dead; the variants source derives a live candidate -> the
    # returned value is the DERIVED one, kind = the stored locator's kind.
    real = tmp_path / "live.bin"
    real.write_text("x", encoding="utf-8")
    dead = r"\\deadhost\share\live.bin"
    rec = DazzleLinkData()
    rec.set_target_path(dead)

    hit = resolve_target(rec, variants=fake_variants({dead: [("drive", str(real))]}))
    assert hit == {"kind": "path", "value": str(real)}


def test_resolve_no_variants_by_default_is_stored_walk_only(tmp_path):
    dead = r"\\deadhost\share\x.bin"
    rec = DazzleLinkData()
    rec.set_target_path(dead)
    # Without variants=, nothing derives the live path -> None (old behavior).
    assert resolve_target(rec) is None


def test_iter_candidates_dedups_across_locators_and_variants(tmp_path):
    from dazzle_linklib.resolver import _iter_candidates

    t = str(tmp_path / "t.txt")
    rec = DazzleLinkData()
    rec.set_target_path(t)
    rec.data["link"]["target_representations"] = {"original_path": t}
    # Variant derives the SAME value the next locator already holds.
    cands = [c for _, c in _iter_candidates(rec, variants=fake_variants({t: [("unc", t)]}))]
    assert len(cands) == len(set(os.path.normcase(c) for c in cands))


# --- AC-E: no at-rest mirror stays true through populate + rebase -------------

def test_populate_then_rebase_single_relative_locator(tmp_path):
    target = tmp_path / "asset.txt"
    target.write_text("x", encoding="utf-8")
    rec = DazzleLinkData()
    rec.set_target_path(str(target))
    populate_locators(rec, record_dir=str(tmp_path), variants=fake_variants({}))
    rec.save_to_file(str(tmp_path / "a.dazzlelink"))

    rebase(str(tmp_path))
    back = DazzleLinkData.from_file(str(tmp_path / "a.dazzlelink"))
    rels = [l for l in back.get_locators() if l["kind"] == "relative"]
    assert len(rels) == 1
    # Nothing was mirrored into link.locators at rest.
    assert back.to_dict()["link"].get("locators", []) == []


# --- default source sanity -----------------------------------------------------

def test_default_path_variants_is_kinded_and_never_raises(tmp_path):
    out = default_path_variants(str(tmp_path))
    assert isinstance(out, list)
    for kind, value in out:
        assert isinstance(kind, str) and isinstance(value, str)
    assert isinstance(default_path_variants(""), list)
