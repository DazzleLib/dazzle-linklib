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
import re
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

# A value whose FORM is scheme-addressed (url/ipfs/magnet/... -- anything a
# shell-open handler dispatches on). Two-plus chars before :// so a Windows
# drive letter ("C:\x") can never match; UNC forms ("\\srv\share") have no
# scheme and fall through to the filesystem check.
_SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.\-]*://")


class SchemeAwareReachability:
    """Reachability for records that mix path and scheme-addressed locators.

    Scheme-form values (``https://...``, ``ipfs://...``) are **assumed
    reachable** -- no network I/O, offline-correct, and exactly the "natural
    last resort" posture: whether the scheme actually opens is the OS
    handler's business at open time. Everything else is judged by filesystem
    existence. Openability is form-determined here; a locator's *kind* remains
    population-side provenance (the kind/form doctrine, S8) -- this checker
    never sees kinds.

    Compose verification on top per the decorator pattern in docs/api.md
    (exists AND digest matches) when a record carries a ``content_id``.
    """

    def is_reachable(self, value: str) -> bool:
        try:
            if not value:
                return False
            if _SCHEME_RE.match(str(value)):
                return True
            return os.path.exists(value)
        except (OSError, ValueError, TypeError):
            return False


def default_reachability() -> ReachabilityResolver:
    """The module-default reachability checker (filesystem existence)."""
    return _DEFAULT_REACHABILITY


def _select_locators(record, *, prefer=None, only=None, kinds=None):
    """The selector stage: filter/order a record's locators (locality axis).

    Applied kinds-filter -> reach-filter -> preference-ordering; each step is a
    no-op when its argument is None, so defaults preserve the plain
    get_locators() order exactly.
    """
    locators = record.get_locators()
    if kinds is not None:
        wanted = set(kinds)
        locators = [loc for loc in locators if loc.get("kind") in wanted]
    if only is not None:
        from .locality import filter_by_reach

        locators = filter_by_reach(locators, only)
    if prefer is not None:
        from .locality import order_by_preference

        locators = order_by_preference(locators, prefer)
    return locators


def _iter_candidates(record, *, variants=None, base_dir=None,
                     prefer=None, only=None, kinds=None):
    """Yield ``(locator, candidate)`` pairs in resolution order.

    The single source of truth for WHAT a resolution tries and in WHAT order --
    :func:`resolve_target` takes the first reachable hit, and a caller wanting
    diagnostics ("which forms were tried?") or all-live-candidates semantics
    (Relinker) walks this generator itself.

    Per locator (in :meth:`~dazzle_linklib.DazzleLinkData.get_locators` priority
    order): the locator's own value first -- ``relative`` values anchored at
    ``base_dir`` when given (without ``base_dir`` a relative candidate is
    yielded as-is and is CWD-dependent; pass the record file's directory) --
    then each derivation from the kinded ``variants`` source. Candidates are
    deduplicated case-insensitively across the whole walk.

    Selection (the locality axis, see :mod:`dazzle_linklib.locality`):
    ``kinds`` filters to exact locator kinds; ``only`` filters to a locality
    rung or reach alias; ``prefer`` reorders by rank-distance from a rung or
    reach alias (preference, not filter -- everything else remains fallback).

    Args:
        record: anything exposing ``get_locators() -> [{'kind', 'value'}]``.
        variants: kinded variant source ``path -> [(kind, value)]`` applied to
            each anchored candidate (live re-resolution on THIS machine's
            mappings). ``None`` -> no expansion (the stored-locator walk only).
        base_dir: anchor directory for ``relative`` locators.
        prefer: locality rung or reach alias to order candidates toward.
        only: locality rung or reach alias to restrict candidates to.
        kinds: iterable of locator kinds to restrict candidates to.
    """
    seen = set()

    def _fresh(value):
        key = os.path.normcase(str(value))
        if key in seen:
            return False
        seen.add(key)
        return True

    for locator in _select_locators(record, prefer=prefer, only=only, kinds=kinds):
        value = locator.get("value")
        if not value:
            continue
        if locator.get("kind") == "relative" and base_dir is not None:
            candidate = os.path.normpath(os.path.join(str(base_dir), value))
        else:
            candidate = value
        if _fresh(candidate):
            yield locator, candidate
        if variants is not None:
            try:
                derived = list(variants(str(candidate)))
            except Exception:
                derived = []
            for _kind, derived_value in derived:
                if derived_value and _fresh(derived_value):
                    yield locator, str(derived_value)


def resolve_target(record, *, reachability=None, variants=None, base_dir=None,
                   prefer=None, only=None, kinds=None):
    """Return the first reachable locator for ``record``, or ``None``.

    Walks the record's locators in priority order (see
    :meth:`~dazzle_linklib.DazzleLinkData.get_locators`), anchoring ``relative``
    locators at ``base_dir`` and -- when a ``variants`` source is given --
    re-deriving each candidate's alternative names on the EXECUTING machine's
    current mappings (live re-resolution: a dead drive letter stored on machine
    A can still resolve via the UNC form machine B maps today).

    Args:
        record: A :class:`~dazzle_linklib.DazzleLinkData` (anything exposing
            ``get_locators() -> [{'kind', 'value'}]``).
        reachability: A :class:`ReachabilityResolver` to judge each candidate.
            Defaults to filesystem existence. Injected, never mutating I/O.
            Identity verification composes here: wrap the checker so
            ``is_reachable = exists AND digest matches`` and a failing
            candidate simply lets the walk continue (see docs/api.md).
        variants: kinded variant source ``path -> [(kind, value)]`` for live
            re-resolution; ``None`` (default) walks stored locators only.
            Pass :func:`~dazzle_linklib.default_path_variants` for the
            unctools-backed default.
        base_dir: directory the record file lives in; anchors ``relative``
            locators. Without it, relative candidates are CWD-dependent.
        prefer: locality rung or reach alias (see
            :mod:`dazzle_linklib.locality`) -- reorders candidates by
            rank-distance toward it. A PREFERENCE: everything else remains
            as fallback.
        only: locality rung or reach alias -- restricts candidates to that
            rung/reach (a filter; no matches -> ``None``).
        kinds: iterable of locator kinds to restrict candidates to.

    Returns:
        dict | None: ``{'kind', 'value'}`` for the first reachable candidate --
        ``value`` may be a machine-derived variant of the stored locator, not
        the stored string itself -- or ``None`` if nothing is reachable.
    """
    checker = reachability if reachability is not None else default_reachability()
    for locator, candidate in _iter_candidates(
        record, variants=variants, base_dir=base_dir,
        prefer=prefer, only=only, kinds=kinds,
    ):
        if checker.is_reachable(candidate):
            return {"kind": locator.get("kind"), "value": candidate}
    return None


__all__ = [
    "ReachabilityResolver",
    "FilesystemReachability",
    "SchemeAwareReachability",
    "default_reachability",
    "resolve_target",
]
