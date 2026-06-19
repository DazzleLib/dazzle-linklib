# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to a PEP 440 versioning scheme (see `_version.py`).

Status: **scaffold (pre-alpha).** The public surface is locked from the first
release (`docs/api-stability.md`); changes land via the stack's shim policy
(temporary, noisy, tracked, terminal), never silently.

## [Unreleased]

## [0.1.0] -- 2026-06-19

**Name-reservation placeholder.** Published to PyPI to claim the
`dazzle-linklib` name; exposes only its version -- no functional content yet.

### Added
- Project scaffold: MIT license, `dazzle_linklib` package, charter docstring,
  day-one guards (`docs/api-stability.md` + `tests/test_import_stability.py`).
- README badges (PyPI, release date, Python, license, platform).
- The L2 charter (README): content-addressable link record serving the
  dazzlelink CLI, preserve manifests, and Relinker; delegates filesystem
  mechanics to `dazzle-filekit` (L1) and UNC identity to `unctools` (L0).

### CI
- `release.yml` keys off the GitHub Release published event (not tag push) so
  publishing fires once, after the notes exist.

### Notes
- The `DazzleLinkData` extraction + resolver (stack phase P2) is **not yet
  shipped** -- it lands in a later release (Roadmap, issue #2).

[Unreleased]: https://github.com/DazzleLib/dazzle-linklib/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/DazzleLib/dazzle-linklib/releases/tag/v0.1.0
