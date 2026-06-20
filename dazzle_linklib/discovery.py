"""Discovery and path-rebasing over ``.dazzlelink`` record files.

This is the L2 record-oriented surface:

* :func:`find_dazzlelinks` -- locate ``.dazzlelink`` files by path/glob/pattern;
* :func:`scan` -- find every ``.dazzlelink`` record under a directory tree;
* :func:`rebase` -- synchronize a record's stored absolute and relative target
  paths (the record-file rebase, distinct from rewriting live OS symlinks).

Boundary note: discovering and rewriting *live OS symlinks* (``os.readlink`` /
``os.symlink`` / ``os.path.islink`` traversal) is filesystem mechanics owned by
``dazzle-filekit`` (L1) and stays in the dazzlelink CLI tool -- this library
operates on the record FILES, not on the symlinks they describe. The
``os.path.relpath`` call in :func:`rebase` is slated to delegate to filekit's
``compute_relative_path`` (STACK-MAP V12-tail) once that home is in the env.
"""

import fnmatch
import glob
import json
import logging
import os
from pathlib import Path

from .exceptions import DazzleLinkError
from .record import DazzleLinkData

logger = logging.getLogger(__name__)

DEFAULT_EXT = ".dazzlelink"


def find_dazzlelinks(path_patterns, recursive=False, pattern=None, dazzlelink_ext=DEFAULT_EXT):
    """Find ``.dazzlelink`` files by path, directory, or glob pattern.

    Args:
        path_patterns: A path/glob string or a list of them. Each may be a
            direct file, a directory, or a wildcard pattern.
        recursive: Recurse into subdirectories when a pattern names a directory.
        pattern: Filename glob to filter matches (default ``*<ext>``).
        dazzlelink_ext: The record extension to match (default ``.dazzlelink``).

    Returns:
        list[pathlib.Path]: Matching record paths, de-duplicated, order-stable.
    """
    if isinstance(path_patterns, str):
        path_patterns = [path_patterns]
    if pattern is None:
        pattern = f"*{dazzlelink_ext}"

    found = []
    for path_pattern in path_patterns:
        # Expand any glob in the input; fall back to the literal path.
        expanded_paths = glob.glob(path_pattern, recursive=False) or [path_pattern]

        for path in expanded_paths:
            path_obj = Path(path)

            if path_obj.is_file():
                if path_obj.suffix == dazzlelink_ext and (
                    pattern == f"*{dazzlelink_ext}" or fnmatch.fnmatch(path_obj.name, pattern)
                ):
                    found.append(path_obj)

            elif path_obj.is_dir():
                if recursive:
                    for root, _, files in os.walk(path_obj):
                        root_path = Path(root)
                        for file in files:
                            if file.endswith(dazzlelink_ext) and fnmatch.fnmatch(file, pattern):
                                found.append(root_path / file)
                else:
                    for file in path_obj.glob(pattern):
                        if file.is_file() and file.suffix == dazzlelink_ext:
                            found.append(file)

            elif "*" in str(path_obj) or "?" in str(path_obj):
                # A wildcard pattern glob() didn't expand; try the parent dir.
                try:
                    parent = path_obj.parent
                    if parent.exists():
                        for file in parent.glob(path_obj.name):
                            if (
                                file.is_file()
                                and file.suffix == dazzlelink_ext
                                and fnmatch.fnmatch(file.name, pattern)
                            ):
                                found.append(file)
                except OSError as e:
                    logger.debug("Error while processing pattern %s: %s", path_obj, e)

    # De-duplicate, preserving first-seen order.
    seen = set()
    unique = []
    for link in found:
        key = str(link)
        if key not in seen:
            seen.add(key)
            unique.append(link)
    return unique


def scan(directory, recursive=True, dazzlelink_ext=DEFAULT_EXT):
    """Find every ``.dazzlelink`` record under ``directory``.

    A thin record-oriented wrapper over :func:`find_dazzlelinks` (this is the
    L2 sense of "scan": discover RECORDS, not live OS symlinks).

    Args:
        directory: Directory to scan.
        recursive: Recurse into subdirectories (default True).
        dazzlelink_ext: The record extension to match.

    Returns:
        list[pathlib.Path]: Record paths found under ``directory``.

    Raises:
        NotADirectoryError: if ``directory`` is not a directory.
    """
    directory = Path(directory)
    if not directory.is_dir():
        raise NotADirectoryError(f"{directory} is not a directory")
    return find_dazzlelinks([str(directory)], recursive=recursive, dazzlelink_ext=dazzlelink_ext)


def rebase(directory, recursive=True, only_broken=False, dazzlelink_ext=DEFAULT_EXT):
    """Synchronize stored absolute and relative target paths in record files.

    For each record found:

    * absolute valid, relative stale  -> recompute relative from absolute;
    * absolute broken, relative valid -> recompute absolute from relative;
    * both valid and in sync          -> unchanged;
    * both broken                     -> reported as an error.

    This rebases the *record's stored paths* -- it does NOT touch live OS
    symlinks (that is the CLI tool's ``rebase_links``, filekit's domain).

    Args:
        directory: Directory to scan for records.
        recursive: Recurse into subdirectories (default True).
        only_broken: Accepted for parity with the CLI; this already only
            rewrites records whose stored paths are out of sync.
        dazzlelink_ext: The record extension to match.

    Polyglot (executable-script) records are **skipped**, not rewritten: the
    library cannot regenerate the script wrapper (that is the dazzlelink CLI
    tool's concern -- ``save_to_file`` here writes plain JSON), so rewriting one
    would silently strip its executable form. They are reported in ``skipped``
    with a clear reason rather than failing with a JSON parse error.

    Returns:
        dict: ``{'changed': [...], 'unchanged': [...], 'skipped': [...],
        'errors': [...]}``.
    """
    result = {"changed": [], "unchanged": [], "skipped": [], "errors": []}

    records = find_dazzlelinks([str(directory)], recursive=recursive, dazzlelink_ext=dazzlelink_ext)
    if not records:
        logger.info("No %s files found in %s", dazzlelink_ext, directory)
        return result

    logger.info("Rebasing %d record file(s)...", len(records))

    for dl_path in records:
        dl_path = str(dl_path)
        try:
            try:
                with open(dl_path, "r", encoding="utf-8-sig") as f:
                    data = json.load(f)
            except ValueError:
                # Not plain JSON. If it parses as a record at all, it's the
                # polyglot executable-script form -- skip it (rewriting would
                # strip the script wrapper, which the library cannot rebuild).
                # If it doesn't parse either, it's a genuine error.
                try:
                    DazzleLinkData.from_file(dl_path)
                except DazzleLinkError as e:
                    result["errors"].append({"file": dl_path, "error": str(e)})
                    continue
                result["skipped"].append(
                    {
                        "file": dl_path,
                        "reason": (
                            "Executable/embedded .dazzlelink not rebased by the "
                            "library; regenerate it via the dazzlelink tool."
                        ),
                    }
                )
                continue

            link_section = data.get("link", {})
            target_path = link_section.get("target_path", "")
            target_reps = link_section.get("target_representations", {})
            relative_path = target_reps.get("relative_path", "")

            dl_dir = os.path.dirname(os.path.abspath(dl_path))

            abs_valid = os.path.exists(target_path) if target_path else False
            rel_resolved = (
                os.path.normpath(os.path.join(dl_dir, relative_path)) if relative_path else ""
            )
            rel_valid = os.path.exists(rel_resolved) if rel_resolved else False

            if abs_valid:
                # Absolute is the source of truth; keep relative in sync.
                # NOTE (V12-tail): os.path.relpath -> filekit.compute_relative_path at delegation.
                expected_relative = os.path.relpath(target_path, dl_dir)
                if relative_path == expected_relative:
                    result["unchanged"].append(
                        {"file": dl_path, "reason": "Both paths valid and in sync"}
                    )
                    continue
                target_reps["relative_path"] = expected_relative
                data.setdefault("link", {})["target_representations"] = target_reps
                with open(dl_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, default=str)
                result["changed"].append(
                    {
                        "file": dl_path,
                        "action": "Recomputed relative from absolute",
                        "old_relative": relative_path,
                        "new_relative": expected_relative,
                    }
                )

            elif rel_valid:
                # Absolute broken but relative resolves -> recompute absolute.
                new_absolute = os.path.abspath(rel_resolved)
                data.setdefault("link", {})["target_path"] = new_absolute
                target_reps["original_path"] = new_absolute
                data["link"]["target_representations"] = target_reps
                with open(dl_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, default=str)
                result["changed"].append(
                    {
                        "file": dl_path,
                        "action": "Recomputed absolute from relative",
                        "old_absolute": target_path,
                        "new_absolute": new_absolute,
                    }
                )

            else:
                result["errors"].append(
                    {
                        "file": dl_path,
                        "error": (
                            f"Both paths broken. Absolute: {target_path}, "
                            f"Relative: {relative_path}"
                        ),
                    }
                )

        except (OSError, ValueError) as e:
            result["errors"].append({"file": dl_path, "error": str(e)})

    return result


__all__ = ["find_dazzlelinks", "scan", "rebase"]
