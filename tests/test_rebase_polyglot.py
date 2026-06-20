"""rebase behavior on polyglot (embedded-script) and unparseable records.

Found during the v0.1.0 human-checklist run (Part D edge probe): ``rebase`` reads
records with ``json.load``, which can't parse the polyglot executable-script
format. The library deliberately does NOT rewrite polyglot records (it cannot
regenerate the script wrapper -- that is the dazzlelink CLI tool's job), so it
reports them in a dedicated ``skipped`` bucket with a clear reason rather than a
cryptic JSON error. Genuinely unparseable files still go to ``errors``.

``DazzleLinkData.from_file`` handles all three on-disk formats; ``rebase`` uses it
only to *classify* a non-JSON file (polyglot vs. garbage), never to rewrite it.
"""

import json

from dazzle_linklib import DazzleLinkData, rebase

_DATA_MARKER = "# DAZZLELINK_DATA_BEGIN"


def _write_polyglot(path, target_path, relative_path):
    """Write a polyglot (shebang + embedded JSON) dazzlelink record."""
    record_data = {
        "schema_version": 1,
        "link": {
            "original_path": target_path,
            "target_path": target_path,
            "type": "symlink",
            "target_representations": {
                "original_path": target_path,
                "relative_path": relative_path,
            },
        },
        "config": {"default_mode": "info"},
    }
    content = (
        "#!/usr/bin/env python3\n"
        "# Generated dazzlelink executable\n"
        f"# decoy: {_DATA_MARKER} in a comment\n"
        "import sys; sys.exit(0)\n"
        f"{_DATA_MARKER}\n"
        + json.dumps(record_data, indent=2)
        + "\n"
    )
    path.write_text(content, encoding="utf-8")
    return path


def test_from_file_reads_polyglot(tmp_path):
    """Baseline: DazzleLinkData.from_file handles the polyglot format correctly."""
    target = tmp_path / "target.txt"
    target.write_text("x", encoding="utf-8")
    dl = _write_polyglot(tmp_path / "poly.dazzlelink", str(target), "target.txt")
    r = DazzleLinkData.from_file(str(dl))
    assert r.get_original_path() == str(target)
    assert r.get_target_path() == str(target)


def test_rebase_skips_polyglot_without_rewriting(tmp_path):
    """A polyglot record is reported as skipped and left byte-for-byte intact."""
    target = tmp_path / "target.txt"
    target.write_text("x", encoding="utf-8")
    dl = _write_polyglot(tmp_path / "poly.dazzlelink", str(target), "STALE/path.txt")
    before = dl.read_bytes()

    result = rebase(str(tmp_path))

    assert len(result["skipped"]) == 1
    assert result["skipped"][0]["file"].endswith("poly.dazzlelink")
    assert "Executable" in result["skipped"][0]["reason"]
    assert result["changed"] == []
    assert result["errors"] == []
    # The script wrapper must NOT have been stripped to plain JSON.
    assert dl.read_bytes() == before
    assert _DATA_MARKER.encode() in dl.read_bytes()


def test_rebase_reports_garbage_as_error(tmp_path):
    """A truly unparseable file (not JSON, not polyglot) lands in errors."""
    bad = tmp_path / "bad.dazzlelink"
    bad.write_text("this is not json and has no marker", encoding="utf-8")

    result = rebase(str(tmp_path))

    assert len(result["errors"]) == 1
    assert result["errors"][0]["file"].endswith("bad.dazzlelink")
    assert result["skipped"] == []


def test_rebase_plain_json_still_works_alongside_polyglot(tmp_path):
    """Plain-JSON records rebase normally even when a polyglot sits beside them."""
    target = tmp_path / "real.txt"
    target.write_text("x", encoding="utf-8")

    plain = DazzleLinkData()
    plain.set_target_path(str(target))
    plain.data["link"]["target_representations"] = {
        "original_path": str(target),
        "relative_path": "STALE.txt",
    }
    plain.save_to_file(str(tmp_path / "plain.dazzlelink"))

    _write_polyglot(tmp_path / "poly.dazzlelink", str(target), "STALE.txt")

    result = rebase(str(tmp_path))

    assert len(result["changed"]) == 1  # the plain record got rebased
    assert result["changed"][0]["file"].endswith("plain.dazzlelink")
    assert len(result["skipped"]) == 1  # the polyglot got skipped
