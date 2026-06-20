"""Target resolution -- pick a record's best live locator.

The resolver is **injectable** (the L1/L0 resolver-edge pattern): this library
owns the candidate-walk *strategy* (which locators to try, in what order), while
*judging* whether any single locator is reachable is delegated to a pluggable
:class:`ReachabilityResolver`. The filesystem default judges by existence; the
Relinker injects a network/protocol checker (http/ipfs/torrent/...) without this
library importing anything network-aware.

``ReachabilityResolver`` is a structural, ``runtime_checkable`` Protocol with a
single ``is_reachable(value) -> bool`` method, so a test can inject a fake with
no base class and no stack import.
"""

import logging
import os
from typing import Protocol, runtime_checkable

logger = logging.getLogger(__name__)


@runtime_checkable
class ReachabilityResolver(Protocol):
    """Judges whether a single locator value is currently reachable."""

    def is_reachable(self, value: str) -> bool:  # pragma: no cover - protocol
        ...


class FilesystemReachability:
    """Default checker: a locator is reachable iff it exists on the filesystem.

    URLs and content-address locators (``https://``, ``ipfs://``, ...) are not
    filesystem paths, so ``os.path.exists`` naturally reports them unreachable --
    resolving those is the injected (e.g. Relinker) checker's job.
    """

    def is_reachable(self, value: str) -> bool:
        try:
            return bool(value) and os.path.exists(value)
        except (OSError, ValueError):
            return False


_DEFAULT_REACHABILITY = FilesystemReachability()


def default_reachability() -> ReachabilityResolver:
    """The module-default reachability checker (filesystem existence)."""
    return _DEFAULT_REACHABILITY


def resolve_target(record, *, reachability=None):
    """Return the first reachable locator for ``record``, or ``None``.

    The candidate order is the record's own locator order
    (:meth:`DazzleLinkData.get_locators` -- path aliases first, original ahead of
    derived, then explicit locators), so the most authoritative locator wins.

    Args:
        record: A :class:`~dazzle_linklib.DazzleLinkData` (anything exposing
            ``get_locators() -> [{'kind', 'value'}]``).
        reachability: A :class:`ReachabilityResolver` to judge each candidate.
            Defaults to filesystem existence. Injected, never mutating I/O.

    Returns:
        dict | None: the first ``{'kind', 'value'}`` locator judged reachable,
        or ``None`` if none are.
    """
    checker = reachability if reachability is not None else default_reachability()
    for locator in record.get_locators():
        value = locator.get("value")
        if value and checker.is_reachable(value):
            return locator
    return None


__all__ = [
    "ReachabilityResolver",
    "FilesystemReachability",
    "default_reachability",
    "resolve_target",
]
