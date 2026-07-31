# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to a PEP 440 versioning scheme (see `_version.py`).

Status: **pre-alpha.** The public surface is locked from the first functional
release (`docs/api-stability.md`); changes land via the stack's shim policy
(temporary, noisy, tracked, terminal), never silently.

## [Unreleased]

## [0.4.0] -- 2026-07-30

**The locality-selection release** (dazzlelink#25 train): a record's locators
now sit on a real locality axis, and resolution takes a rung on it -- CHOICE
(preference), not just fallback.

### Added
- `locality` module: `LOCALITY_CONTINUUM` -- the locality ladder as a
  `dazzle_lib.Continuum` (warm/+ = local possession: memory/file/link/
  removable; the rank-0 seat is the machine boundary; cold/- = unc/ssh/ftp/
  internet; `subtype="full"`). `LOCALITY_SPACE` (single-axis
  `ContinuumSpace.compose`) is the hook future fidelity axes intersect
  (the Relinker degrees-of-removal model). Helpers: `locator_rung` (kind ->
  rung; kind stays mechanism-of-derivation, rung is WHERE the value lives --
  a `drive` letter shares the `unc` rung; unknown kinds have no rung, never
  guessed), `reach_of`, `resolve_rung` (rung or reach alias `local` /
  `local-network` / `remote`), `order_by_preference` (stable rank-distance
  sort), `filter_by_reach`.
- `resolve_target(..., prefer=, only=, kinds=)` -- selection on the walk:
  `kinds` filters exact kinds, `only` filters to a rung/reach, `prefer`
  REORDERS by rank-distance from a rung/reach (everything else remains
  fallback). Defaults preserve 0.3.0 behavior exactly. `_iter_candidates`
  carries the same parameters (diagnostics see what resolution sees).
- `SchemeAwareReachability` -- reachability for records mixing path and
  scheme-addressed locators: scheme-form values (`https://...`, `ipfs://...`)
  are assumed reachable (no network I/O, offline-correct -- whether a scheme
  opens is the OS handler's business at open time); everything else is judged
  by filesystem existence. Openability is form-determined; a locator's kind
  remains population-side provenance.

### Changed
- `dazzle-lib` floor raised to `>=0.8.2` (`Continuum(subtype=)` /
  `ContinuumSpace.compose`) -- this library is the stack's first Continuum
  consumer outside dazzlecmd/loglib.

## [0.3.0] -- 2026-07-30

**The portable-paths release** (dazzlelink#13/#24 train). Records now carry --
and can re-derive -- the path forms that survive machine changes: relative
(synced trees), UNC/drive (network bases), and subst expansions.

### Added
- `populate_locators(record, *, record_dir=None, variants=None)` -- the
  create-side portability operation: computes and stores the target's path
  family (`relative_path` anchored at the record's directory + `unc_path` /
  `drive_path` / `subst_path` from the kinded variant source) in
  `target_representations`. Three-way refresh: computed values overwrite;
  provable absence removes (relative only -- cross-drive with a known anchor);
  couldn't-compute preserves (a missing mapping HERE never invalidates a
  variant stored by the creating machine). Never raises.
- `path_family(path, *, base_dir=None, variants=None)` -- one path's
  representation family as a legacy-keyed dict; `base_dir=None` omits the
  relative key (the historical link-side shape). The building block the
  dazzlelink tool uses for both target and link representations.
- `default_path_variants` -- the kinded variant source (unctools
  `path_variants`): `[(kind, value)]` where kind is the mechanism-of-derivation
  (unc/drive/subst), not the form of the value. Injectable everywhere it is
  consumed.
- `resolve_target(..., variants=None, base_dir=None)` -- **live re-resolution**
  and correct relative anchoring: `base_dir` anchors `relative` locators at the
  record file's directory (previously CWD-accidental); a `variants` source
  re-derives each candidate against the EXECUTING machine's current mappings,
  so a dead stored form resolves via the form this machine maps today. The
  walk is a generator (`resolver._iter_candidates`) -- the diagnostic source
  for "what was tried" and the future all-live-candidates surface. The winner's
  `value` may be machine-derived. Default (`variants=None`) keeps the stored-
  locator-only walk.
- `export_link(populate=..., variants=...)` -- opt-in population at export
  (default False: population enumerates drive mappings; bulk exporters opt in
  deliberately).
- api.md documents the identity-verification pattern (a `ReachabilityResolver`
  decorator: exists AND digest matches -- the walk continues past a failed
  candidate naturally).

### Changed
- `get_locators()` now orders the path family by the documented
  resolution-priority heuristic `path -> relative -> unc -> drive -> subst ->
  other legacy aliases -> explicit locators` (previously dict insertion order,
  which put `relative` last). Inner-family order was never a documented
  contract; the new order matches the dazzlelink tool's shipped fallback
  behavior (absolute -> relative -> representations). `subst_path` joins the
  legacy kind mapping.
- New hard dependency `unctools>=0.3.0` (the kinded `path_variants` + one-shot
  subst enumeration) -- the L0 delegation this library's pyproject anticipated.

## [0.2.2] -- 2026-06-20

### Fixed
- Require `dazzle-filekit>=0.3.1`. filekit 0.3.0 corrupted a symlink **target's**
  timestamps when `apply_record_metadata` / `recreate_link` applied a record's
  timestamps to a link (`os.utime` and the default Win32 handle follow the
  reparse point to the target). The fix lives in filekit 0.3.1 (link-targeting
  `SetFileTime` / `os.utime(follow_symlinks=False)`); the dependency floor is
  raised so the operations get correct behavior.

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

[Unreleased]: https://github.com/DazzleLib/dazzle-linklib/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/DazzleLib/dazzle-linklib/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/DazzleLib/dazzle-linklib/compare/v0.2.2...v0.3.0
[0.2.2]: https://github.com/DazzleLib/dazzle-linklib/compare/v0.2.1...v0.2.2
[0.2.1]: https://github.com/DazzleLib/dazzle-linklib/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/DazzleLib/dazzle-linklib/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/DazzleLib/dazzle-linklib/releases/tag/v0.1.0
