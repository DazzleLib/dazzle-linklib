# API Stability

`dazzle-linklib` is **L2** of the DazzleLib stack: the dazzlelink CLI, preserve
(L3), and Relinker all build on its link-record model, so its public surface is
**locked from the first release**. The canary test
`tests/test_import_stability.py` enumerates the locked symbols and fails if any
disappears or moves.

## Policy

1. **Locked symbols never vanish silently.** Removing or renaming one follows
   the stack's shim policy (STACK-MAP Rule 6): a temporary NOISY shim
   (`DeprecationWarning` naming the new home and removal version), registered
   in the stack's alias register, removed on schedule.
2. **Record schema only gains keys.** The `.dazzlelink` JSON format and the
   typed locator list evolve by addition; removing or re-typing an existing
   field is a breaking change requiring a `SCHEMA_VERSION` bump + a CHANGELOG
   migration note + coordination with every consumer below.
3. **Additions follow the rule of two**: a symbol is promoted to the locked
   surface once a second consumer depends on it.
4. **Boundary discipline**: this library does not reimplement filesystem
   mechanics (L1 `dazzle-filekit`), UNC identity (L0 `unctools`), or graph
   traversal (`dazzletreelib`). A change that pulls one of those concerns into
   L2 is an architecture change, not a code review comment (STACK-MAP D6).

## Locked surface (0.1.0 scaffold)

| Module | Symbols |
|---|---|
| `dazzle_linklib` (re-exports) | `__version__`, `__app_name__`, `PIP_VERSION` |

The record model (`DazzleLinkData`, JSON I/O, locator list, `content_id`,
relations, `resolve_target`) is **not yet part of the locked surface** -- it
lands in stack phase **P2** and joins this table at its first release. Until
then the package intentionally exposes only its version.

## Planned surface (P2)

| Symbol | Role |
|---|---|
| `DazzleLinkData` | the link record (schema v1 + typed locator list + `content_id` + relations) |
| `export_link` / `import_link` | JSON serialize / deserialize |
| `find_dazzlelinks` / `scan` / `rebase` | discovery + path rebasing over records |
| `resolve_target` (injectable) | identity -> best live locator |

## Upstream dependency (dazzle-lib)

This library consumes from the bedrock `dazzle-lib` (B): `Serializable`,
`LinkTargetDict`, `LinkError`, `DazzleDataMixin`. Those are locked by
`dazzle-lib`'s own api-stability contract; a change there is coordinated via
its consumer table.

## Known consumers

| Consumer | Symbols | Since |
|---|---|---|
| dazzlelink CLI tool (DazzleTools) | record model + export/import/scan/rebase | stack phase P2 |
| dazzle-preservelib (planned / L3) | record model via the `[dazzlelink]` extra | stack phase P3 |
| Relinker (planned) | locator list + `content_id` model | aspirational |

Update this table whenever a consumer adopts a symbol -- it is the blast-radius
map for any proposed change.
