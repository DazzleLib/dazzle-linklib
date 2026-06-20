"""One-off smoke test for the ported DazzleLinkData record model (P2, Task #1).

Verifies, before wiring the broader surface and the pytest suite:
  (a) `import dazzle_linklib` exposes DazzleLinkData / DazzleLinkError / alias;
  (b) a fresh record round-trips through to_dict/from_dict;
  (c) save_to_file/from_file round-trips (plain v1 JSON);
  (d) the polyglot embedded-script form parses via the exact-line marker;
  (e) the D3 additions (add_locator/set_content_id/add_relation) round-trip and
      legacy target_representations surface as typed locators;
  (f) DazzleLinkData satisfies dazzle_lib.Serializable / is a DazzleDataMixin;
  (g) DazzleLinkError is rooted under the dazzle_lib stack hierarchy.

Run: python tests/one-offs/smoke_record.py
"""

import json
import tempfile
from pathlib import Path

import dazzle_linklib
from dazzle_linklib import DazzleLinkData, DazzleLinkError, DazzleLinkException
import dazzle_lib

_failures = []


def check(label, cond):
    status = "PASS" if cond else "FAIL"
    print(f"[{status}] {label}")
    if not cond:
        _failures.append(label)


# (a) public surface
check("import exposes DazzleLinkData", hasattr(dazzle_linklib, "DazzleLinkData"))
check("DazzleLinkException is DazzleLinkError alias", DazzleLinkException is DazzleLinkError)

# (b) fresh record round-trips through to_dict/from_dict
rec = DazzleLinkData()
rec.set_original_path(r"C:\code\dazzlelink\README.md")
rec.set_target_path(r"C:\code\dazzlelink\README.md")
rec.set_default_mode("open")
rec.set_platform("windows")
d = rec.to_dict()
rec2 = DazzleLinkData.from_dict(json.loads(json.dumps(d)))
check("from_dict preserves original_path", rec2.get_original_path() == r"C:\code\dazzlelink\README.md")
check("from_dict preserves default_mode", rec2.get_default_mode() == "open")
check("SCHEMA_VERSION == 1", DazzleLinkData.SCHEMA_VERSION == 1)

# (c) save_to_file / from_file round-trip (plain v1 JSON)
with tempfile.TemporaryDirectory() as td:
    p = Path(td) / "a.dazzlelink"
    ok = rec.save_to_file(str(p))
    check("save_to_file returns True", ok is True)
    loaded = DazzleLinkData.from_file(str(p))
    check("from_file round-trips original_path", loaded.get_original_path() == rec.get_original_path())

    # legacy flat format: target_path at top level
    flat = Path(td) / "flat.dazzlelink"
    flat.write_text(json.dumps({"target_path": r"D:\old\target.txt"}), encoding="utf-8")
    flat_rec = DazzleLinkData.from_file(str(flat))
    check("legacy flat target_path read", flat_rec.get_target_path() == r"D:\old\target.txt")

    # (d) polyglot embedded-script form: JSON after an EXACT '# DAZZLELINK_DATA_BEGIN' line.
    # The marker literal deliberately appears earlier in a comment to catch the
    # substring-vs-exact-line bug from the source data.py.
    script = (
        "#!/usr/bin/env python\n"
        "# This script writes the line: # DAZZLELINK_DATA_BEGIN (decoy in source)\n"
        "print('open target')\n"
        "# DAZZLELINK_DATA_BEGIN\n"
        + json.dumps({"link": {"original_path": "embedded/path"}})
        + "\n"
    )
    sp = Path(td) / "exe.dazzlelink"
    sp.write_text(script, encoding="utf-8")
    emb = DazzleLinkData.from_file(str(sp))
    check("embedded-script exact-line marker parse", emb.get_original_path() == "embedded/path")

    # BOM tolerance (utf-8-sig)
    bom = Path(td) / "bom.dazzlelink"
    bom.write_bytes(b"\xef\xbb\xbf" + json.dumps({"link": {"original_path": "bom/path"}}).encode("utf-8"))
    bom_rec = DazzleLinkData.from_file(str(bom))
    check("BOM-prefixed file parses", bom_rec.get_original_path() == "bom/path")

    # invalid file raises DazzleLinkError
    bad = Path(td) / "bad.dazzlelink"
    bad.write_text("not json and no marker", encoding="utf-8")
    try:
        DazzleLinkData.from_file(str(bad))
        check("invalid file raises DazzleLinkError", False)
    except DazzleLinkError:
        check("invalid file raises DazzleLinkError", True)

# (e) D3 additions round-trip
rec3 = DazzleLinkData()
rec3.add_locator("url", "https://example.com/x")
rec3.add_locator("ipfs", "QmHash")
rec3.set_content_id("sha256", "deadbeef")
rec3.add_relation("derived_from", "cafef00d", {"note": "test"})
# legacy target_representations should surface as typed locators too
rec3.data["link"]["target_representations"] = {"original_path": "/abs/p", "unc_path": r"\\srv\share\p"}
round = DazzleLinkData.from_dict(json.loads(json.dumps(rec3.to_dict())))
locs = round.get_locators()
kinds = {(l["kind"], l["value"]) for l in locs}
check("explicit url locator round-trips", ("url", "https://example.com/x") in kinds)
check("explicit ipfs locator round-trips", ("ipfs", "QmHash") in kinds)
check("legacy original_path -> 'path' locator", ("path", "/abs/p") in kinds)
check("legacy unc_path -> 'unc' locator", ("unc", r"\\srv\share\p") in kinds)
check("content_id round-trips", round.get_content_id() == {"algorithm": "sha256", "digest": "deadbeef"})
rels = round.get_relations()
check("relation round-trips", rels and rels[0]["kind"] == "derived_from" and rels[0]["target_content_id"] == "cafef00d")

# path-only record must NOT gain content_id/relations/locators keys it never set
plain = DazzleLinkData()
check("path-only record has no content_id key", "content_id" not in plain.to_dict())
check("path-only record has no relations key", "relations" not in plain.to_dict())

# (f) Serializable / mixin conformance
check("isinstance Serializable", isinstance(rec, dazzle_lib.Serializable))
check("isinstance DazzleDataMixin", isinstance(rec, dazzle_lib.DazzleDataMixin))
check("to_json works (from mixin)", isinstance(rec.to_json(), str) and json.loads(rec.to_json()))

# (g) exception hierarchy rooted in the stack
check("DazzleLinkError subclasses dazzle_lib.LinkError", issubclass(DazzleLinkError, dazzle_lib.LinkError))
check("DazzleLinkError subclasses dazzle_lib.DazzleError", issubclass(DazzleLinkError, dazzle_lib.DazzleError))

print()
if _failures:
    print(f"{len(_failures)} FAILURE(S): {_failures}")
    raise SystemExit(1)
print("ALL SMOKE CHECKS PASSED")
