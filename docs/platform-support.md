# Platform Support

`dazzle-linklib` is a pure-Python library. The link **record** (schema, JSON
I/O, locators, `content_id`, relations) is platform-independent. Any
platform-specific behavior (junction vs symlink semantics, UNC paths) is
delegated down the stack to `dazzle-filekit` (L1) and `unctools` (L0), which
carry their own platform matrices.

| Platform | Status |
|----------|--------|
| Windows 10/11 | Expected to work (primary development target) |
| Linux | Expected to work |
| macOS | Expected to work |

Python: **3.9+**.

Status is "expected to work" until the P2 extraction lands and the test suite
exercises real records on each platform. This table will be updated to "Tested"
per platform as CI and human checklists confirm it.
