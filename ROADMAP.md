# Roadmap

The living roadmap is tracked in **[Issue #2](https://github.com/DazzleLib/dazzle-linklib/issues/2)**.

`dazzle-linklib` is **L2** of the [DazzleLib stack](https://github.com/DazzleLib/.github/blob/main/docs/STACK-MAP.md):
the content-addressable link-record library.

| Phase | Theme | Status |
|---|---|---|
| Scaffold | Repo, MIT license, charter, day-one guards | done (0.1.0, unreleased) |
| P2 | Extract `DazzleLinkData` + JSON I/O from the dazzlelink tool; typed locator list + `content_id` + relations; injectable `resolve_target`; first PyPI ship | next |
| P2+ | Delete-and-delegate: filesystem mechanics -> `dazzle-filekit` (L1), UNC -> `unctools` (L0); thin the dazzlelink CLI to consume this lib | planned |
| Relinker | Generalize the locator/`content_id` model for the `rln.kr` hash-addressed resolver | aspirational |

See the architecture contract (STACK-MAP) for the frozen layer boundaries and
the L2 design decisions (D1 naming, D3 schema generalization, D6 graph split).
