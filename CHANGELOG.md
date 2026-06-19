# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to a PEP 440 versioning scheme (see `_version.py`).

Status: **scaffold (pre-alpha).** The public surface is locked from the first
release (`docs/api-stability.md`); changes land via the stack's shim policy
(temporary, noisy, tracked, terminal), never silently.

## [Unreleased]

### Added
- Project scaffold: MIT license, `dazzle_linklib` package, charter docstring,
  day-one guards (`docs/api-stability.md` + `tests/test_import_stability.py`).
- The L2 charter (README): content-addressable link record serving the
  dazzlelink CLI, preserve manifests, and Relinker; delegates filesystem
  mechanics to `dazzle-filekit` (L1) and UNC identity to `unctools` (L0).

### Notes
- The `DazzleLinkData` extraction + resolver (stack phase P2) is **not yet
  shipped** -- the package currently exposes only its version. Not released to
  PyPI until P2 adds real content (Roadmap, issue #2).

## [0.1.0] -- unreleased (scaffold)

Initial repository scaffold created from `git-repokit-template`.

[Unreleased]: https://github.com/DazzleLib/dazzle-linklib/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/DazzleLib/dazzle-linklib/releases/tag/v0.1.0
