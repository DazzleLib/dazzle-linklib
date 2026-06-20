# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to a PEP 440 versioning scheme (see `_version.py`).

Status: **pre-alpha.** The public surface is locked from the first functional
release (`docs/api-stability.md`); changes land via the stack's shim policy
(temporary, noisy, tracked, terminal), never silently.

## [Unreleased]

## [0.2.1] -- 2026-06-20

### Added
- `apply_record_metadata(record, link_path, *, timestamp_strategy, use_live_target)`
  -- apply a record's timestamp strategy + file attributes to an existing link.
  The metadata half of `recreate_link`, exposed for consumers that create a link
  themselves and compute their own link paths (e.g. a batch importer).

### Fixed
- The timestamp adapter handed filekit partial / None-bearing timestamp dicts
  for records with only `modified` set (created/accessed None), which made
  filekit abort the whole metadata apply -- dropping both timestamps and file
  attributes. The adapter now backfills missing created/accessed with `modified`
  so filekit always receives a complete dict. Affected `recreate_link` too.

## [0.2.0] -- 2026-06-19

**First functional release.** Extracts the link-record core (stack phase P2)
from the dazzlelink CLI tool: the record model, record discovery/rebase, and the
injectable target resolver. Verified wire-compatible with the published
`dazzlelink` 0.8.0 tool in both directions.

### Added
- `DazzleLinkData` -- the `.dazzlelink` record (schema v1, verbatim) with the L2
  generalizations layered on additively: a typed locator list
  (`get_locators`/`add_locator`), an optional `content_id`, and inter-record
  `relations`. Path-only records gain no new keys. Reads all three on-disk forms
  (nested JSON, legacy flat, polyglot embedded-script) with BOM tolerance.
- `find_dazzlelinks` / `scan` / `rebase` -- discovery and stored-path rebasing
  over record **files** (not live OS symlinks, which stay in the CLI tool).
- `resolve_target` + `ReachabilityResolver` (a structural, `runtime_checkable`
  Protocol) + `default_reachability` -- the injectable resolver: the library
  owns the candidate walk, the checker judges reachability (filesystem default;
  Relinker injects a network checker).
- `export_link` / `import_link` / `create_link` / `recreate_link` -- the
  record-centric operations. They own the record-policy (where to link, which
  timestamps a strategy implies) and delegate the OS mechanics (symlink
  creation, timestamp/metadata writes) to `dazzle-filekit`, so a consumer
  recreates a link from a record in one call instead of gluing record + filekit
  together itself.
- `DazzleLinkError` (rooted under `dazzle_lib.LinkError`) and the
  `DazzleLinkException` back-compat alias.
- Test suite: 66 tests (record, discovery, resolver, operations, cross-tool
  compat, the no-upstream-import and locked-surface canaries) + a public human
  test checklist.

### Changed
- The public surface (`docs/api-stability.md` + the import-stability canary) now
  locks the record/discovery/resolver/operations symbols. Runtime dependencies:
  `dazzle-lib>=0.1.0` (bedrock contracts) and `dazzle-filekit>=0.3.0` (the OS
  mechanics the operations delegate to); `unctools` joins when its delegation
  code lands.

### Notes
- `rebase` skips polyglot (executable-script) records rather than rewriting them
  -- the library cannot regenerate the script wrapper (that is the dazzlelink CLI
  tool's concern), so it reports them in a `skipped` bucket and leaves them
  intact instead of stripping the wrapper to plain JSON.

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

[Unreleased]: https://github.com/DazzleLib/dazzle-linklib/compare/v0.2.1...HEAD
[0.2.1]: https://github.com/DazzleLib/dazzle-linklib/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/DazzleLib/dazzle-linklib/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/DazzleLib/dazzle-linklib/releases/tag/v0.1.0
