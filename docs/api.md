# API Reference

The public API of `dazzle-linklib` (L2 of the [DazzleLib stack](https://github.com/DazzleLib/.github/blob/main/docs/STACK-MAP.md)). This is the usage reference; the stability *policy* (what is locked, how it deprecates, how the schema may evolve) lives in [api-stability.md](api-stability.md).

Everything documented here is importable from the top-level package:

```python
from dazzle_linklib import (
    DazzleLinkData,
    find_dazzlelinks, scan, rebase,
    export_link, import_link, create_link, recreate_link,
    resolve_target, ReachabilityResolver, default_reachability,
    DazzleLinkError, DazzleLinkException,
)
```

Package metadata is also exposed: `__version__` (full build string), `__app_name__` (`"dazzle-linklib"`), and `PIP_VERSION` (the PEP 440 release version).

---

## `DazzleLinkData`

The `.dazzlelink` link record: schema v1 plus the L2 generalizations (a typed locator list, an optional `content_id`, and inter-record relations). It satisfies `dazzle_lib.Serializable` and mixes in `dazzle_lib.DazzleDataMixin`, so it carries `to_json()` / `summary()` / `__str__()` for free.

`class DazzleLinkData(data: dict | None = None)`

Construct an empty v1 record (`data=None`) or wrap an existing record dict (the in-memory representation returned by `to_dict()`). The class attribute `SCHEMA_VERSION` is `1`.

### Construction and serialization

| Method | Returns | Notes |
|---|---|---|
| `DazzleLinkData()` | `DazzleLinkData` | a fresh v1 record |
| `DazzleLinkData.from_dict(data)` | `DazzleLinkData` | wrap a dict produced by `to_dict()` (classmethod) |
| `DazzleLinkData.from_file(path)` | `DazzleLinkData` | load from disk; reads all three on-disk forms, BOM-tolerant (classmethod) |
| `to_dict()` | `dict` | the JSON-safe record dict (the live backing store) |
| `to_json()` | `str` | `to_dict()` rendered as JSON (from the mixin) |
| `summary()` | `str` | one-line summary for logs (from the mixin) |
| `save_to_file(path, make_executable=False)` | `bool` | write as JSON; `True` on success. `make_executable` is accepted but a **no-op** — polyglot executable-script generation stays in the dazzlelink CLI tool |

`from_file` accepts: nested v1 JSON, the legacy flat format (`target_path` at the top level), and the polyglot executable-script format (JSON after a standalone `# DAZZLELINK_DATA_BEGIN` line, matched as an exact line). It raises `DazzleLinkError` if the file cannot be parsed as any known form, or on a read error.

### Path accessors

| Method | Returns / effect |
|---|---|
| `get_original_path()` / `set_original_path(path)` | the link's own path |
| `get_target_path()` / `set_target_path(path)` | the path the link points at (reads the legacy top-level `target_path` if present) |
| `get_link_type()` | `"symlink"` / `"junction"` / `"unknown"` / ... |
| `get_path_representations()` | the link's path-alias dict |
| `get_target_representations()` | the target's path-alias dict (the legacy locator store) |

### Typed locators (L2)

The locator list generalizes the legacy `target_representations` path-alias dict into a typed `[{"kind", "value"}]` list — path aliases today (`path`/`relative`/`unc`/`drive`), network and content-address locators tomorrow (`url`/`ipfs`/`torrent`/...).

| Method | Returns / effect |
|---|---|
| `get_locators()` | `list[{"kind", "value"}]` — the stored `target_path` first (always seeded), then legacy `target_representations` aliases mapped to kinds, then explicit `add_locator` entries; duplicates collapsed |
| `add_locator(kind, value)` | append a typed locator, e.g. `add_locator("ipfs", "Qm...")` |

### Content identity and relations (L2)

| Method | Returns / effect |
|---|---|
| `get_content_id()` | `{"algorithm", "digest"}` or `None` |
| `set_content_id(algorithm, digest)` | e.g. `set_content_id("sha256", "deadbeef...")` |
| `get_relations()` | `list[{"kind", "target_content_id", "attrs"}]` |
| `add_relation(kind, target_content_id, attrs=None)` | add an edge to another record by its `content_id` digest |

These are **additive**: a record that never sets them carries no `content_id` / `relations` keys, so path-only records are byte-identical to v1.

### Timestamps, target details, config, metadata

| Method | Returns / effect |
|---|---|
| `get_link_timestamps()` / `set_link_timestamps(created=None, modified=None, accessed=None)` | the link's `{created, modified, accessed}` (epoch) + `*_iso` mirrors |
| `get_target_timestamps()` / `set_target_timestamps(...)` | same for the target |
| `get_target_exists()` / `get_target_type()` / `get_target_size()` | target details |
| `get_default_mode()` / `set_default_mode(mode)` | per-file execute mode (`"info"`, `"open"`, ...) |
| `get_platform()` / `set_platform(platform)` | the recording platform |
| `get_schema_version()` / `get_creator()` | record provenance |
| `get_creation_timestamp()` / `get_creation_date()` | creation provenance |
| `get_last_updated_timestamp()` / `get_last_updated_date()` / `get_update_history()` | update provenance |
| `update_metadata(reason="manual_update")` | stamp an update + append `reason` to the history |

### Example

```python
from dazzle_linklib import DazzleLinkData

# Author a record with a typed locator and a content identity.
rec = DazzleLinkData()
rec.set_original_path(r"C:\links\photo.png.dazzlelink")
rec.set_target_path(r"D:\archive\photo.png")
rec.add_locator("ipfs", "QmHash...")
rec.set_content_id("sha256", "deadbeef...")
rec.save_to_file("photo.png.dazzlelink")

# Read it back (any on-disk form) and inspect.
again = DazzleLinkData.from_file("photo.png.dazzlelink")
assert again.get_target_path() == r"D:\archive\photo.png"
assert again.get_content_id() == {"algorithm": "sha256", "digest": "deadbeef..."}
```

---

## Discovery and rebase

These operate on record **files**. Discovering and rewriting live OS symlinks is filesystem mechanics owned by `dazzle-filekit` (L1) and the dazzlelink CLI tool, not by this library.

### `find_dazzlelinks(path_patterns, recursive=False, pattern=None, dazzlelink_ext=".dazzlelink")`

Find `.dazzlelink` files by path, directory, or glob. `path_patterns` is a single string or a list of them; each may be a direct file, a directory, or a wildcard pattern. `pattern` filters filenames (default `*<ext>`). Returns a de-duplicated, order-stable `list[pathlib.Path]`.

### `scan(directory, recursive=True, dazzlelink_ext=".dazzlelink")`

Find every `.dazzlelink` record under `directory` (the record-oriented sense of "scan"). A thin wrapper over `find_dazzlelinks`. Returns `list[pathlib.Path]`. Raises `NotADirectoryError` if `directory` is not a directory.

### `rebase(directory, recursive=True, only_broken=False, dazzlelink_ext=".dazzlelink")`

Synchronize each record's stored absolute and relative target paths:

- absolute valid, relative stale → recompute the relative path;
- absolute broken, relative valid → recompute the absolute path;
- both valid and in sync → unchanged;
- both broken → reported as an error.

Returns a report dict with four buckets:

```python
{"changed": [...], "unchanged": [...], "skipped": [...], "errors": [...]}
```

Polyglot (executable-script) records go to `skipped`, **not** rewritten: the library cannot regenerate the script wrapper (that is the CLI tool's job), so it reports them with a reason and leaves the file byte-for-byte intact rather than stripping the wrapper to plain JSON. Genuinely unparseable files go to `errors`.

```python
from dazzle_linklib import rebase

report = rebase("backup/", recursive=True)
print(len(report["changed"]), "rebased,", len(report["skipped"]), "skipped")
```

---

## Target resolution

### `resolve_target(record, *, reachability=None)`

Return the first reachable locator for `record`, or `None`. The candidate order is the record's own locator order (`get_locators()` — the stored `target_path` first, then aliases, then explicit locators), so the most authoritative locator wins.

`record` is a `DazzleLinkData` (or anything exposing `get_locators() -> [{"kind", "value"}]`). `reachability` is a `ReachabilityResolver` that judges each candidate; it defaults to filesystem existence. Returns the chosen `{"kind", "value"}` dict, or `None` if none are reachable.

The library owns the candidate-walk *strategy*; the injected checker only judges a single locator. The checker is consulted in order and `resolve_target` stops at the first reachable one — it never mutates I/O.

### `ReachabilityResolver`

A structural, `runtime_checkable` `Protocol` with one method:

```python
def is_reachable(self, value: str) -> bool: ...
```

Any object with that method satisfies it — no base class, no import from this library. This is the injection seam: a test passes a fake; Relinker passes a network/protocol checker (http/ipfs/torrent/...).

### `default_reachability()`

Return the module-default checker (`FilesystemReachability`), which reports a locator reachable iff its value exists on the filesystem. URLs and content-address locators are not filesystem paths, so the default reports them unreachable — judging those is the injected checker's job.

```python
from dazzle_linklib import DazzleLinkData, resolve_target

class NetReachability:
    def is_reachable(self, value):
        return value.startswith(("http://", "https://", "ipfs://"))

rec = DazzleLinkData.from_file("photo.png.dazzlelink")
located = resolve_target(rec, reachability=NetReachability())   # injected
fs_located = resolve_target(rec)                                # filesystem default
```

---

## Operations

The record-centric operations. Each is **complete**: it owns the record-policy
and delegates OS mechanics (symlink creation, timestamp/metadata writes) to
`dazzle-filekit` internally, so a consumer calls one function instead of stitching
a record together with the filesystem itself.

### `export_link(record, file_path, make_executable=False)`

Write `record` to `file_path` as a `.dazzlelink` file. A module-level convenience over `DazzleLinkData.save_to_file`. Returns `True` on success.

### `import_link(file_path)`

Load a `.dazzlelink` file into a `DazzleLinkData`. A module-level convenience over `DazzleLinkData.from_file`.

### `create_link(record, link_path=None, *, force=True)`

Create the OS symlink `record` describes (target = `record.get_target_path()`), via `filekit.create_symlink`. `link_path` defaults to the record's `original_path`; `force` overwrites an existing file/link. Creates parent directories as needed. Returns the created link path. Raises `DazzleLinkError` if the record lacks a target/link path or the symlink creation fails.

### `recreate_link(dazzlelink_path, *, target_location=None, timestamp_strategy="current", use_live_target=False, update_record=False, force=True)`

The keystone anti-link-rot operation: load the record, create the symlink, and apply the chosen timestamp strategy — in one call.

- `target_location` — if given, create the link in this directory under the record's original filename; otherwise at the record's `original_path`.
- `timestamp_strategy` — one of `current` (leave at creation time), `symlink` (restore the recorded link timestamps), `target` (restore the target's timestamps), or `preserve-all` (alias of `target`).
- `use_live_target` — for the `target` strategy, read timestamps from the live target file if it exists, else fall back to the recorded ones.
- `update_record` — stamp and re-save the record's metadata after recreation.

Returns the recreated link path. Raises `DazzleLinkError` on parse failure, an unknown strategy, or if the link cannot be created.

```python
from dazzle_linklib import DazzleLinkData, recreate_link

# Author + save a record, then recreate the link from the .dazzlelink alone.
rec = DazzleLinkData()
rec.set_target_path(r"D:\archive\photo.png")
rec.set_original_path(r"C:\links\photo.png")
rec.save_to_file("photo.dazzlelink")

link = recreate_link("photo.dazzlelink", timestamp_strategy="target", use_live_target=True)
```

The timestamp **strategy** (which timestamps to apply) is record-policy and lives here; the actual write onto the symlink (including the Windows reparse-point handling) is `dazzle-filekit`'s.

## Exceptions

### `DazzleLinkError`

Raised for `.dazzlelink` record problems: parse, serialize, resolve. It subclasses `dazzle_lib.LinkError` (itself a `dazzle_lib.DazzleError`), so a consumer can catch the whole stack's errors via `DazzleError`:

```python
from dazzle_lib import DazzleError
from dazzle_linklib import DazzleLinkData

try:
    DazzleLinkData.from_file("maybe-corrupt.dazzlelink")
except DazzleError as e:
    ...  # caught, whichever stack layer raised it
```

### `DazzleLinkException`

A back-compat alias for `DazzleLinkError` (the dazzlelink CLI tool and preserve import this name).

---

## The `.dazzlelink` record schema (v1)

`to_dict()` returns this shape. The L2 additions (`link.locators`, top-level `content_id`, top-level `relations`) appear only when set, so a path-only record is exactly a v1 record.

```jsonc
{
  "schema_version": 1,
  "created_by": "DazzleLink v1",
  "creation_timestamp": 0.0,
  "creation_date": "ISO-8601",
  "dazzlelink_metadata": {
    "last_updated_timestamp": 0.0,
    "last_updated_date": "ISO-8601",
    "update_history": ["initial_creation"]
  },
  "link": {
    "original_path": "",
    "path_representations": {},
    "target_path": "",
    "target_representations": {},      // legacy path-alias store
    "type": "unknown",
    "relative_path": false,
    "timestamps": { "created": null, "modified": null, "accessed": null,
                    "created_iso": null, "modified_iso": null, "accessed_iso": null },
    "attributes": { "hidden": false, "system": false, "readonly": false },
    "locators": [ { "kind": "ipfs", "value": "Qm..." } ]   // L2, additive
  },
  "target": {
    "exists": false, "type": "unknown", "size": null,
    "checksum": null, "extension": null,
    "timestamps": { "created": null, "modified": null, "accessed": null,
                    "created_iso": null, "modified_iso": null, "accessed_iso": null }
  },
  "security": { "permissions": null, "owner": null, "group": null },
  "config": { "default_mode": "info", "platform": "unknown" },

  "content_id": { "algorithm": "sha256", "digest": "..." },                  // L2, additive
  "relations": [ { "kind": "derived_from", "target_content_id": "...", "attrs": {} } ]  // L2, additive
}
```

Schema evolution is **additive only** — removing or re-typing a field is a breaking change requiring a `SCHEMA_VERSION` bump (see [api-stability.md](api-stability.md), policy 2).

---

## See also

- [api-stability.md](api-stability.md) — the stability policy, locked-surface canary, and consumer table.
- [STACK-MAP.md](https://github.com/DazzleLib/.github/blob/main/docs/STACK-MAP.md) — the full stack architecture contract.
- The bedrock contracts this library consumes (`Serializable`, `DazzleDataMixin`, `LinkError`, `LinkTargetDict`) are documented in [dazzle-lib](https://github.com/DazzleLib/dazzle-lib).
