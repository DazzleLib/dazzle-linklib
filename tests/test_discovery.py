"""Tests for record discovery + rebase (find_dazzlelinks / scan / rebase)."""

import json
import os

import pytest

from dazzle_linklib import DazzleLinkData, find_dazzlelinks, rebase, scan


def _write_record(path, target_path="", relative_path=None):
    rec = DazzleLinkData()
    if target_path:
        rec.set_target_path(target_path)
        rec.data["link"]["target_representations"]["original_path"] = target_path
    if relative_path is not None:
        rec.data["link"]["target_representations"]["relative_path"] = relative_path
    rec.save_to_file(str(path))
    return path


# --- find_dazzlelinks -----------------------------------------------------

def test_find_single_file(tmp_path):
    f = _write_record(tmp_path / "a.dazzlelink")
    found = find_dazzlelinks(str(f))
    assert [str(p) for p in found] == [str(f)]


def test_find_in_directory_non_recursive(tmp_path):
    _write_record(tmp_path / "a.dazzlelink")
    _write_record(tmp_path / "b.dazzlelink")
    (tmp_path / "note.txt").write_text("ignore me", encoding="utf-8")
    found = find_dazzlelinks(str(tmp_path))
    names = sorted(p.name for p in found)
    assert names == ["a.dazzlelink", "b.dazzlelink"]


def test_find_recursive(tmp_path):
    sub = tmp_path / "sub"
    sub.mkdir()
    _write_record(tmp_path / "top.dazzlelink")
    _write_record(sub / "deep.dazzlelink")
    flat = find_dazzlelinks(str(tmp_path), recursive=False)
    deep = find_dazzlelinks(str(tmp_path), recursive=True)
    assert {p.name for p in flat} == {"top.dazzlelink"}
    assert {p.name for p in deep} == {"top.dazzlelink", "deep.dazzlelink"}


def test_find_dedup_overlapping_patterns(tmp_path):
    f = _write_record(tmp_path / "a.dazzlelink")
    found = find_dazzlelinks([str(f), str(tmp_path)])
    assert len(found) == 1


def test_find_filename_pattern_filter(tmp_path):
    _write_record(tmp_path / "keep-me.dazzlelink")
    _write_record(tmp_path / "skip-me.dazzlelink")
    found = find_dazzlelinks(str(tmp_path), pattern="keep-*.dazzlelink")
    assert {p.name for p in found} == {"keep-me.dazzlelink"}


# --- scan -----------------------------------------------------------------

def test_scan_finds_records(tmp_path):
    sub = tmp_path / "sub"
    sub.mkdir()
    _write_record(tmp_path / "a.dazzlelink")
    _write_record(sub / "b.dazzlelink")
    found = scan(str(tmp_path), recursive=True)
    assert {p.name for p in found} == {"a.dazzlelink", "b.dazzlelink"}


def test_scan_rejects_non_directory(tmp_path):
    f = _write_record(tmp_path / "a.dazzlelink")
    with pytest.raises(NotADirectoryError):
        scan(str(f))


# --- rebase ---------------------------------------------------------------

def test_rebase_recomputes_relative_from_absolute(tmp_path):
    # A real target exists; the stored relative path is stale -> recompute it.
    target = tmp_path / "real_target.txt"
    target.write_text("hi", encoding="utf-8")
    dl = _write_record(
        tmp_path / "link.dazzlelink",
        target_path=str(target),
        relative_path="WRONG/stale.txt",
    )
    report = rebase(str(tmp_path))
    assert len(report["changed"]) == 1
    assert report["changed"][0]["action"] == "Recomputed relative from absolute"

    data = json.loads(dl.read_text(encoding="utf-8"))
    expected = os.path.relpath(str(target), os.path.dirname(os.path.abspath(str(dl))))
    assert data["link"]["target_representations"]["relative_path"] == expected


def test_rebase_in_sync_is_unchanged(tmp_path):
    target = tmp_path / "t.txt"
    target.write_text("hi", encoding="utf-8")
    dl_path = tmp_path / "link.dazzlelink"
    correct_rel = os.path.relpath(str(target), str(tmp_path))
    _write_record(dl_path, target_path=str(target), relative_path=correct_rel)
    report = rebase(str(tmp_path))
    assert len(report["unchanged"]) == 1
    assert not report["changed"]


def test_rebase_both_broken_is_error(tmp_path):
    _write_record(
        tmp_path / "broken.dazzlelink",
        target_path=str(tmp_path / "gone.txt"),
        relative_path="also/gone.txt",
    )
    report = rebase(str(tmp_path))
    assert len(report["errors"]) == 1
    assert "Both paths broken" in report["errors"][0]["error"]


def test_rebase_empty_directory(tmp_path):
    report = rebase(str(tmp_path))
    assert report == {"changed": [], "unchanged": [], "skipped": [], "errors": []}
