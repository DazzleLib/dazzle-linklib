# dazzle-linklib

[![PyPI](https://img.shields.io/pypi/v/dazzle-linklib?color=green)](https://pypi.org/project/dazzle-linklib/)
[![Release Date](https://img.shields.io/github/release-date/DazzleLib/dazzle-linklib?color=green)](https://github.com/DazzleLib/dazzle-linklib/releases)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS%20%7C%20BSD-lightgrey.svg)](docs/platform-support.md)

**Content-addressable link-record library** -- the **L2** serialization layer of
the [DazzleLib stack](https://github.com/DazzleLib/.github/blob/main/docs/STACK-MAP.md).

A link record maps an **identity** to a **typed list of locators** plus
metadata, and knows how to serialize, find, and resolve itself. One model
serves three consumers:

- the **dazzlelink** filesystem CLI (the `.dazzlelink` file format),
- **preserve**'s content-hash manifest (L3), and
- **Relinker** -- a hash-addressed, decentralized anti-link-rot resolver
  (`rln.kr/{hash}` -> a multi-protocol location set).

## What this owns (and what it doesn't)

`dazzle-linklib` owns the link **record**: its schema, JSON I/O, the locator
list, `content_id`, relation edges, and the injectable target resolver. It
**delegates** the rest down the stack:

| Concern | Layer |
|---|---|
| Link record, locators, `content_id`, relations, resolve | **dazzle-linklib (L2, this lib)** |
| File/link mechanics (create/detect/read, copy, hash, metadata) | `dazzle-filekit` (L1) |
| UNC <-> drive identity, path origin classification | `unctools` (L0) |
| Shared Protocols / TypedDicts / exception root | `dazzle-lib` (B) |
| Graph **traversal** (walking the records' relation edges) | `dazzletreelib` (perpendicular) |

"Records that point at each other" live here; "walking and interpreting those
pointers" do not. (See the L2 design rationale, decision D6.)

## Status

**Pre-alpha (0.2.0) -- first functional release.** The link-record core (stack
phase P2) is extracted from the `dazzlelink` tool: the record model
(`DazzleLinkData`), record discovery/rebase (`find_dazzlelinks`/`scan`/`rebase`),
and the injectable target resolver (`resolve_target`). It is verified
wire-compatible with the published `dazzlelink` 0.8.0 tool in both directions.
The down-stack delegation of filesystem mechanics to `dazzle-filekit` (L1) and
`unctools` (L0) follows -- see the
[Roadmap](https://github.com/DazzleLib/dazzle-linklib/issues/2).

## Usage

```python
from dazzle_linklib import DazzleLinkData, find_dazzlelinks, resolve_target

# Read a .dazzlelink record (nested JSON, legacy flat, or embedded-script form).
record = DazzleLinkData.from_file("photo.png.dazzlelink")
print(record.get_target_path())

# Author a record with typed locators + a content identity (Relinker-ready).
record = DazzleLinkData()
record.set_target_path(r"D:\archive\photo.png")
record.add_locator("ipfs", "QmHash...")
record.set_content_id("sha256", "deadbeef...")
record.save_to_file("photo.png.dazzlelink")

# Discover records under a tree and resolve one to its first live locator.
for path in find_dazzlelinks("backup/", recursive=True):
    located = resolve_target(DazzleLinkData.from_file(str(path)))
    print(path, "->", located)
```

## Installation

```bash
pip install dazzle-linklib
```

### From source

```bash
git clone https://github.com/DazzleLib/dazzle-linklib.git
cd dazzle-linklib
pip install -e ".[dev]"
```

## Development

```bash
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -e ".[dev]"

# Run tests
python -m pytest tests/ -v

# Install git hooks
bash scripts/install-hooks.sh
```

## License

MIT. See [LICENSE](LICENSE) for details.
