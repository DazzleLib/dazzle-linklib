"""The dazzle-linklib link record -- ``DazzleLinkData``.

Ported from the dazzlelink CLI tool's ``data.py`` (schema v1), generalized per
the L2 design (DWP decision D3) into a content-addressable link record:

* the v1 ``.dazzlelink`` JSON schema, verbatim (back-compat with every existing
  file -- new JSON, legacy flat, and the polyglot embedded-script format);
* a typed **locator list** (``get_locators``/``add_locator``) -- path-aliases
  today, network/decentralized locations (url/ipfs/torrent/...) for Relinker;
* an optional **content identity** (``content_id = {algorithm, digest}``);
* optional inter-record **relations** (``[{kind, target_content_id, attrs}]``)
  -- the graph node+edge model (D6); traversal is NOT owned here.

It satisfies :class:`dazzle_lib.Serializable` (``SCHEMA_VERSION`` + ``from_dict``)
and mixes in :class:`dazzle_lib.DazzleDataMixin` (``to_json``/``summary``/``__str__``).
Filesystem mechanics (timestamps, attributes, hashing, UNC) are NOT done here --
they delegate down to dazzle-filekit (L1) and unctools (L0).
"""

import datetime
import json

from dazzle_lib import DazzleDataMixin

from .exceptions import DazzleLinkError

# Maps the legacy ``target_representations`` dict keys to locator ``kind`` values
# so old path-alias records expose as typed locators losslessly.
_LEGACY_REP_KIND = {
    "original_path": "path",
    "relative_path": "relative",
    "unc_path": "unc",
    "drive_path": "drive",
}

_DATA_MARKER = "# DAZZLELINK_DATA_BEGIN"


class DazzleLinkData(DazzleDataMixin):
    """Abstract data type for a dazzlelink record (schema v1 + L2 extensions)."""

    SCHEMA_VERSION = 1

    def __init__(self, data=None):
        """Wrap existing ``data`` or build a fresh v1 record structure."""
        if data is None:
            now = datetime.datetime.now()
            self.data = {
                "schema_version": 1,
                "created_by": "DazzleLink v1",
                "creation_timestamp": now.timestamp(),
                "creation_date": now.isoformat(),
                "dazzlelink_metadata": {
                    "last_updated_timestamp": now.timestamp(),
                    "last_updated_date": now.isoformat(),
                    "update_history": ["initial_creation"],
                },
                "link": {
                    "original_path": "",
                    "path_representations": {},
                    "target_path": "",
                    "target_representations": {},
                    "type": "unknown",
                    "relative_path": False,
                    "timestamps": {
                        "created": None, "modified": None, "accessed": None,
                        "created_iso": None, "modified_iso": None, "accessed_iso": None,
                    },
                    "attributes": {"hidden": False, "system": False, "readonly": False},
                },
                "target": {
                    "exists": False, "type": "unknown", "size": None,
                    "checksum": None, "extension": None,
                    "timestamps": {
                        "created": None, "modified": None, "accessed": None,
                        "created_iso": None, "modified_iso": None, "accessed_iso": None,
                    },
                },
                "security": {"permissions": None, "owner": None, "group": None},
                "config": {"default_mode": "info", "platform": "unknown"},
            }
        else:
            self.data = data

    # -- Schema information -------------------------------------------------
    def get_schema_version(self):
        """Schema version of the record."""
        return self.data.get("schema_version", 1)

    def get_creator(self):
        """Creator string."""
        return self.data.get("created_by", "Unknown")

    # -- Creation timestamps -----------------------------------------------
    def get_creation_timestamp(self):
        return self.data.get("creation_timestamp")

    def get_creation_date(self):
        return self.data.get("creation_date")

    # -- Dazzlelink metadata -----------------------------------------------
    def get_last_updated_timestamp(self):
        meta = self.data.get("dazzlelink_metadata", {})
        return meta.get("last_updated_timestamp", self.get_creation_timestamp())

    def get_last_updated_date(self):
        meta = self.data.get("dazzlelink_metadata", {})
        return meta.get("last_updated_date", self.get_creation_date())

    def get_update_history(self):
        meta = self.data.get("dazzlelink_metadata", {})
        return meta.get("update_history", ["initial_creation"])

    def update_metadata(self, reason="manual_update"):
        """Record an update (timestamp + append to update_history)."""
        now = datetime.datetime.now()
        meta = self.data.setdefault("dazzlelink_metadata", {})
        meta["last_updated_timestamp"] = now.timestamp()
        meta["last_updated_date"] = now.isoformat()
        meta.setdefault("update_history", ["initial_creation"]).append(reason)

    # -- Link information --------------------------------------------------
    def get_link_type(self):
        return self.data.get("link", {}).get("type", "unknown")

    def get_original_path(self):
        return self.data.get("link", {}).get("original_path", "")

    def set_original_path(self, path):
        self.data.setdefault("link", {})["original_path"] = str(path)

    def get_target_path(self):
        # Legacy flat format stored target_path at the top level.
        if "target_path" in self.data:
            return self.data["target_path"]
        return self.data.get("link", {}).get("target_path", "")

    def set_target_path(self, path):
        self.data.setdefault("link", {})["target_path"] = str(path)

    def get_path_representations(self):
        link = self.data.get("link", {})
        return link.get("path_representations", {"original_path": self.get_original_path()})

    def get_target_representations(self):
        link = self.data.get("link", {})
        return link.get("target_representations", {"original_path": self.get_target_path()})

    # -- L2: typed locators (D3) -------------------------------------------
    def get_locators(self):
        """All target locators as a typed ``[{kind, value}]`` list.

        Merges the legacy ``target_representations`` path-alias dict (mapped to
        kinds path/relative/unc/drive/...) with any explicit ``link.locators``
        entries (url/ipfs/torrent/...). Order: legacy aliases first, then
        explicit locators; duplicates (same kind+value) are collapsed.
        """
        seen = set()
        locators = []
        # The canonical stored target_path is always the first candidate, so a
        # record with only target_path set (target_representations empty -- the
        # common shape) still yields a locator and resolves.
        target_path = self.get_target_path()
        if target_path:
            pair = ("path", target_path)
            seen.add(pair)
            locators.append({"kind": "path", "value": target_path})
        for key, value in self.get_target_representations().items():
            if not value:
                continue
            kind = _LEGACY_REP_KIND.get(key, key[:-5] if key.endswith("_path") else key)
            pair = (kind, value)
            if pair not in seen:
                seen.add(pair)
                locators.append({"kind": kind, "value": value})
        for loc in self.data.get("link", {}).get("locators", []):
            pair = (loc.get("kind"), loc.get("value"))
            if pair not in seen:
                seen.add(pair)
                locators.append({"kind": loc.get("kind"), "value": loc.get("value")})
        return locators

    def add_locator(self, kind, value):
        """Add a typed locator (e.g. ``add_locator('ipfs', 'Qm...')``)."""
        self.data.setdefault("link", {}).setdefault("locators", []).append(
            {"kind": kind, "value": value}
        )

    # -- L2: content identity (D3) -----------------------------------------
    def get_content_id(self):
        """The content identity ``{algorithm, digest}`` or ``None`` if unset."""
        return self.data.get("content_id")

    def set_content_id(self, algorithm, digest):
        """Set the content identity (e.g. ``set_content_id('sha512', '...')``)."""
        self.data["content_id"] = {"algorithm": algorithm, "digest": digest}

    # -- L2: relations / graph edges (D6) ----------------------------------
    def get_relations(self):
        """Inter-record edges as ``[{kind, target_content_id, attrs}]``."""
        return self.data.get("relations", [])

    def add_relation(self, kind, target_content_id, attrs=None):
        """Add an edge to another record by its ``content_id`` digest."""
        self.data.setdefault("relations", []).append(
            {"kind": kind, "target_content_id": target_content_id, "attrs": attrs or {}}
        )

    # -- Link timestamps ---------------------------------------------------
    def get_link_timestamps(self):
        return self.data.get("link", {}).get("timestamps", {
            "created": None, "modified": None, "accessed": None,
            "created_iso": None, "modified_iso": None, "accessed_iso": None,
        })

    def set_link_timestamps(self, created=None, modified=None, accessed=None):
        ts = self.data.setdefault("link", {}).setdefault("timestamps", {})
        self._apply_timestamps(ts, created, modified, accessed)

    # -- Target information ------------------------------------------------
    def get_target_exists(self):
        return self.data.get("target", {}).get("exists", False)

    def get_target_type(self):
        return self.data.get("target", {}).get("type", "unknown")

    def get_target_size(self):
        return self.data.get("target", {}).get("size")

    def get_target_timestamps(self):
        target = self.data.get("target", {})
        if "timestamps" in target:
            return target["timestamps"]
        return {
            "created": None, "modified": None, "accessed": None,
            "created_iso": None, "modified_iso": None, "accessed_iso": None,
        }

    def set_target_timestamps(self, created=None, modified=None, accessed=None):
        ts = self.data.setdefault("target", {}).setdefault("timestamps", {})
        self._apply_timestamps(ts, created, modified, accessed)

    @staticmethod
    def _apply_timestamps(ts, created, modified, accessed):
        for key, value in (("created", created), ("modified", modified), ("accessed", accessed)):
            if value is not None:
                ts[key] = value
                ts[f"{key}_iso"] = (
                    datetime.datetime.fromtimestamp(value).isoformat() if value else None
                )

    # -- Configuration -----------------------------------------------------
    def get_default_mode(self):
        return self.data.get("config", {}).get("default_mode", "info")

    def set_default_mode(self, mode):
        self.data.setdefault("config", {})["default_mode"] = mode

    def get_platform(self):
        return self.data.get("config", {}).get("platform", "unknown")

    def set_platform(self, platform):
        self.data.setdefault("config", {})["platform"] = platform

    # -- Serializable ------------------------------------------------------
    def to_dict(self):
        """The record as a JSON-safe dict (satisfies Serializable / the mixin)."""
        return self.data

    @classmethod
    def from_dict(cls, data):
        """Construct a record from a dict produced by :meth:`to_dict`."""
        return cls(data)

    # -- File I/O ----------------------------------------------------------
    @classmethod
    def from_file(cls, file_path):
        """Load a record from a ``.dazzlelink`` file.

        Handles all three on-disk forms: plain v1 JSON, the legacy flat JSON,
        and the polyglot executable-script format (JSON after a standalone
        ``# DAZZLELINK_DATA_BEGIN`` line). BOM-tolerant (utf-8-sig).

        Raises:
            DazzleLinkError: if the file cannot be parsed as any known form.
        """
        try:
            with open(file_path, "r", encoding="utf-8-sig") as f:
                content = f.read()
        except OSError as e:
            raise DazzleLinkError(f"Error reading dazzlelink file {file_path}: {e}")

        try:
            return cls(json.loads(content))
        except json.JSONDecodeError:
            pass

        # Executable (script-embedded) form: find the marker as an EXACT line --
        # the literal also appears in the generated script's own source, so a
        # substring search would grab the wrong (earlier) occurrence.
        json_text = None
        lines = content.splitlines(keepends=True)
        for i, line in enumerate(lines):
            if line.strip() == _DATA_MARKER:
                json_text = "".join(lines[i + 1:])
                break
        if json_text is not None:
            try:
                return cls(json.loads(json_text))
            except json.JSONDecodeError:
                raise DazzleLinkError(f"Cannot parse embedded JSON in {file_path}")
        raise DazzleLinkError(f"Invalid dazzlelink file: {file_path}")

    def save_to_file(self, file_path, make_executable=False):
        """Write the record as JSON.

        ``make_executable`` is accepted for back-compat but is a no-op here:
        polyglot executable-script generation is the dazzlelink CLI tool's
        concern (it stays in the tool, not this library).

        Returns:
            bool: True on success, False on write error.
        """
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
            return True
        except OSError as e:
            print(f"Error saving dazzlelink file {file_path}: {e}")
            return False


__all__ = ["DazzleLinkData"]
