"""Record-centric operations -- create / recreate / export / import a link.

These are the **complete** L2 operations: a consumer (the dazzlelink CLI,
preserve, Relinker) calls one of these instead of gluing a record together with
filesystem mechanics itself. The record-policy (which path to link, which
timestamps a strategy implies) lives here; the OS mechanics (symlink creation,
metadata/timestamp writes -- including the Windows reparse-point ctypes) are
delegated to **dazzle-filekit** (L1). The record's timestamp blocks already
match filekit's ``metadata["timestamps"]`` shape, so the adapter is thin.
"""

import os

import dazzle_filekit as fk

from .exceptions import DazzleLinkError
from .record import DazzleLinkData

# Timestamp strategies for recreate_link, mirroring the dazzlelink CLI:
#   current      -- leave the recreated link at its creation time (no-op)
#   symlink      -- restore the original link's recorded timestamps
#   target       -- restore the target's timestamps (live target if requested,
#                   else the recorded target timestamps)
#   preserve-all -- alias of target (kept for CLI parity)
_STRATEGIES = ("current", "symlink", "target", "preserve-all", "preserve")


def export_link(record, file_path, make_executable=False):
    """Write ``record`` to ``file_path`` as a ``.dazzlelink`` file.

    A module-level convenience over :meth:`DazzleLinkData.save_to_file` (for
    consumers -- e.g. preserve -- that prefer functions over methods).

    Returns:
        bool: True on success.
    """
    return record.save_to_file(file_path, make_executable=make_executable)


def import_link(file_path):
    """Load a ``.dazzlelink`` file into a :class:`DazzleLinkData`.

    A module-level convenience over :meth:`DazzleLinkData.from_file`.
    """
    return DazzleLinkData.from_file(file_path)


def create_link(record, link_path=None, *, force=True):
    """Create the OS symlink ``record`` describes, via filekit.

    Args:
        record: a :class:`DazzleLinkData` whose ``target_path`` is the symlink
            target.
        link_path: where to create the link; defaults to the record's
            ``original_path``.
        force: overwrite an existing file/link at ``link_path`` (default True).

    Returns:
        str: the created link path.

    Raises:
        DazzleLinkError: if the record lacks a target/link path, or the
            underlying symlink creation fails.
    """
    target = record.get_target_path()
    if not target:
        raise DazzleLinkError("record has no target_path to link to")
    if link_path is None:
        link_path = record.get_original_path()
    if not link_path:
        raise DazzleLinkError("no link_path given and record has no original_path")

    parent = os.path.dirname(os.path.abspath(str(link_path)))
    if parent:
        os.makedirs(parent, exist_ok=True)

    is_dir = record.get_target_type() == "directory"
    try:
        ok = fk.create_symlink(target, link_path, force=force, target_is_directory=is_dir)
    except OSError as e:
        raise DazzleLinkError(f"failed to create symlink {link_path} -> {target}: {e}")
    if not ok:
        raise DazzleLinkError(f"failed to create symlink {link_path} -> {target}")
    return str(link_path)


def _timestamps_for_strategy(record, strategy, use_live_target):
    """Resolve which ``{created, modified, accessed}`` a strategy implies, or None.

    This is the record-policy half of the operation -- it never writes anything.
    """
    if strategy == "current":
        return None
    if strategy == "symlink":
        ts = record.get_link_timestamps()
    elif strategy in ("target", "preserve-all", "preserve"):
        ts = None
        if use_live_target:
            live = record.get_target_path()
            if live and os.path.exists(live):
                ts = fk.collect_file_metadata(live).get("timestamps")
        if not ts or ts.get("modified") is None:
            ts = record.get_target_timestamps()
    else:
        raise DazzleLinkError(
            f"unknown timestamp strategy {strategy!r} (expected one of {_STRATEGIES})"
        )
    if not ts or ts.get("modified") is None:
        return None
    # filekit needs a complete timestamps dict with real epoch numbers: it
    # requires all three keys present and cannot interpret a None (a partial or
    # None-bearing dict aborts the whole metadata apply -- timestamps AND
    # attributes). Backfill any missing/None created/accessed with modified.
    modified = ts.get("modified")
    created = ts.get("created")
    accessed = ts.get("accessed")
    return {
        "created": created if created is not None else modified,
        "modified": modified,
        "accessed": accessed if accessed is not None else modified,
    }


def _metadata_for_recreation(record, strategy, use_live_target):
    """Build the filekit metadata dict to apply to a recreated link.

    Combines the timestamp strategy (record-policy) with the record's stored file
    attributes (hidden/system/readonly). Returns an empty dict if there is
    nothing to apply. filekit's ``apply_file_metadata`` writes both, and it acts
    on the link itself -- it does not follow through to the target.
    """
    metadata = {}
    timestamps = _timestamps_for_strategy(record, strategy, use_live_target)
    if timestamps is not None:
        metadata["timestamps"] = timestamps
    attrs = record.to_dict().get("link", {}).get("attributes") or {}
    if any(attrs.get(k) for k in ("hidden", "system", "readonly")):
        metadata["windows"] = {
            "is_hidden": bool(attrs.get("hidden", False)),
            "is_system": bool(attrs.get("system", False)),
            "is_readonly": bool(attrs.get("readonly", False)),
        }
    return metadata


def apply_record_metadata(record, link_path, *, timestamp_strategy="current", use_live_target=False):
    """Apply a record's timestamp strategy + file attributes to an existing link.

    The metadata half of :func:`recreate_link`, exposed for consumers that
    already hold a record and a link they created themselves (e.g. a batch
    importer that computes its own link paths). Writes the timestamps the
    strategy implies and the recorded Windows attributes (hidden/system/
    readonly) onto ``link_path`` via filekit -- it acts on the link, not the
    target. A no-op (returns False) when the strategy/record imply nothing.

    Args:
        record: a :class:`DazzleLinkData`.
        link_path: an existing link to apply metadata to.
        timestamp_strategy: ``current`` / ``symlink`` / ``target`` /
            ``preserve-all`` (see module docstring).
        use_live_target: for the ``target`` strategy, prefer the live target's
            timestamps if it exists.

    Returns:
        bool: True if metadata was applied, False if there was nothing to do.
    """
    metadata = _metadata_for_recreation(record, timestamp_strategy, use_live_target)
    if not metadata:
        return False
    fk.apply_file_metadata(link_path, metadata)
    return True


def recreate_link(
    dazzlelink_path,
    *,
    target_location=None,
    timestamp_strategy="current",
    use_live_target=False,
    update_record=False,
    force=True,
):
    """Recreate the symlink a ``.dazzlelink`` record describes.

    The keystone anti-link-rot operation: load the record, create the symlink,
    and apply the chosen timestamp strategy -- all in one call, so a consumer
    never stitches record + resolve + filekit together itself.

    Args:
        dazzlelink_path: the ``.dazzlelink`` file to recreate from.
        target_location: if given, create the link in this directory under the
            record's original filename; otherwise at the record's original path.
        timestamp_strategy: one of ``current`` / ``symlink`` / ``target`` /
            ``preserve-all`` (see module docstring).
        use_live_target: for the ``target`` strategy, read timestamps from the
            live target file if it exists, else fall back to the recorded ones.
        update_record: stamp + re-save the record's metadata after recreation.
        force: overwrite an existing file/link at the destination.

    Returns:
        str: the recreated link path.

    Raises:
        DazzleLinkError: on parse failure or if the link cannot be created.
    """
    record = DazzleLinkData.from_file(dazzlelink_path)

    if target_location:
        original_name = os.path.basename(record.get_original_path())
        link_path = os.path.join(target_location, original_name)
    else:
        link_path = record.get_original_path()

    create_link(record, link_path, force=force)

    apply_record_metadata(
        record,
        link_path,
        timestamp_strategy=timestamp_strategy,
        use_live_target=use_live_target,
    )

    if update_record:
        record.update_metadata(reason="symlink_recreation")
        # When recreating against a live target, fold the target's current
        # timestamps back into the record so the saved .dazzlelink reflects what
        # was actually linked.
        if use_live_target and timestamp_strategy in ("target", "preserve-all", "preserve"):
            target = record.get_target_path()
            if target and os.path.exists(target):
                live = fk.collect_file_metadata(target).get("timestamps") or {}
                record.set_target_timestamps(
                    created=live.get("created"),
                    modified=live.get("modified"),
                    accessed=live.get("accessed"),
                )
        record.save_to_file(dazzlelink_path)

    return str(link_path)


__all__ = [
    "export_link",
    "import_link",
    "create_link",
    "recreate_link",
    "apply_record_metadata",
]
