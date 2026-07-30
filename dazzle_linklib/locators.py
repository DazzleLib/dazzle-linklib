"""Locator population -- give a record its portable path family at create time.

The portability layer's create side: compute a target's alternative names --
relative (from the record's own directory), UNC, mapped-drive, and subst
expansions -- and store them in the record so any machine can re-resolve later.
This lives in L2 so EVERY consumer (the dazzlelink CLI, preserve, Relinker)
inherits portability by calling one operation, instead of each re-gluing it.

The variant source is **kinded**: a callable ``path -> [(kind, value)]`` where
``kind`` is the *mechanism-of-derivation* (``unc`` / ``drive`` / ``subst``),
because provenance is unrecoverable from the string form -- a subst expansion's
value is a plain local path. The default source is unctools'
:func:`~unctools.path_variants` (L0 owns enumeration + provenance; this module
owns only the kind -> legacy-key schema mapping). Inject a fake for tests, or a
richer source for Relinker.

At-rest encoding (see the L2 design DWP + api-stability policy 2): the path
family is stored in the legacy ``target_representations`` dict
(``original_path`` / ``relative_path`` / ``unc_path`` / ``drive_path`` /
``subst_path``); ``link.locators`` at rest is reserved for non-path kinds
(url/ipfs/...). ``get_locators()`` types the legacy keys losslessly at read
time, so there is deliberately NO at-rest mirror (one ``rebase`` would desync
it).
"""

import logging
import os

logger = logging.getLogger(__name__)

# Legacy-dict keys this module owns and may rewrite. original_path and any
# unknown keys are never touched.
_OWNED_VARIANT_KEYS = ("unc_path", "drive_path", "subst_path")
_OWNED_KEYS = ("relative_path",) + _OWNED_VARIANT_KEYS


def default_path_variants(path):
    """The default kinded variant source: unctools' ``path_variants``.

    Returns ``[(kind, value)]`` derivations (input excluded); ``[]`` on
    non-Windows or when unctools cannot enumerate. Never raises.
    """
    try:
        from unctools import path_variants
    except ImportError:  # pragma: no cover - unctools is a hard dep
        logger.debug("unctools unavailable; no path variants")
        return []
    try:
        return list(path_variants(path))
    except Exception as e:
        logger.debug("path_variants failed for %s: %s", path, e)
        return []


def path_family(path, *, base_dir=None, variants=None):
    """Compute a path's at-rest representation family as a legacy-keyed dict.

    Args:
        path: the path to describe.
        base_dir: directory to compute ``relative_path`` from (the record
            file's directory). ``None`` -> no relative key (the historical
            shape of a link's own ``path_representations``).
        variants: kinded variant source ``path -> [(kind, value)]``; ``None``
            uses :func:`default_path_variants`. Each ``(kind, value)`` maps to
            the ``f"{kind}_path"`` key (unknown kinds map generically, so a
            richer source degrades additively).

    Returns:
        dict: always contains ``original_path``; other keys only when derived.
        Never raises -- each derivation is best-effort.
    """
    family = {"original_path": str(path)}

    source = variants if variants is not None else default_path_variants
    try:
        for kind, value in source(str(path)):
            if kind and value:
                family[f"{kind}_path"] = str(value)
    except Exception as e:
        logger.debug("variant source failed for %s: %s", path, e)

    if base_dir is not None:
        try:
            family["relative_path"] = os.path.relpath(str(path), str(base_dir))
        except ValueError:
            # Cross-drive on Windows: provably no valid relative form exists.
            logger.debug("no relative form for %s from %s (cross-drive)", path, base_dir)

    return family


def populate_locators(record, *, record_dir=None, variants=None):
    """Populate a record's portable path family (the create-side operation).

    Computes the target's representation family via :func:`path_family` and
    folds it into ``target_representations`` under a three-way refresh rule:

    * **computed a value** -> overwrite the owned key;
    * **provable absence** -> remove the stale key. This applies ONLY to
      ``relative_path`` (derived purely from target + ``record_dir``: a
      cross-drive ``ValueError`` with a known ``record_dir`` proves no valid
      relative exists -- and a stale relative would outrank working forms at
      resolve time). Variant keys (unc/drive/subst) are machine-local
      derivations: a missing mapping HERE does not invalidate a value stored
      by the creating machine, so they are never removed, only overwritten;
    * **couldn't compute** (no ``record_dir``; enumeration unavailable) ->
      preserve whatever is stored.

    ``original_path`` is seeded only if absent (the record's stored
    ``target_path`` is authoritative; an existing ``original_path`` alias is
    someone else's data). Unknown keys are never touched. Never raises.

    Args:
        record: a :class:`~dazzle_linklib.DazzleLinkData`.
        record_dir: the directory the ``.dazzlelink`` file lives in (anchors
            ``relative_path``). ``None`` -> relative is left as-is.
        variants: kinded variant source; ``None`` -> unctools default.

    Returns:
        dict: the updated ``target_representations`` (live reference).
    """
    target = record.get_target_path()
    link_section = record.to_dict().setdefault("link", {})
    reps = link_section.setdefault("target_representations", {})
    if not target:
        return reps

    computed = path_family(target, base_dir=record_dir, variants=variants)

    reps.setdefault("original_path", computed["original_path"])

    for key in _OWNED_VARIANT_KEYS:
        if key in computed:
            reps[key] = computed[key]
        # absent -> preserve: machine-local absence proves nothing

    if record_dir is not None:
        if "relative_path" in computed:
            reps["relative_path"] = computed["relative_path"]
        else:
            # Provable absence (cross-drive): a stale relative is a hazard.
            reps.pop("relative_path", None)

    return reps


__all__ = ["path_family", "populate_locators", "default_path_variants"]
