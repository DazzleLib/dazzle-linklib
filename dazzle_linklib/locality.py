"""The LOCALITY axis -- where a copy lives, as a real dazzle-lib Continuum.

The Relinker continuum vision (see the 2026-07-30 vision note): every locator
sits somewhere on a signed axis running from "in hand" to "out on the net",
with the **machine boundary as the rank-0 invariant seat**. Selection is then a
rung on the axis, not a bespoke string enum -- ``--prefer internet`` orders
candidates by rank-distance from that rung, and future fidelity axes intersect
this one through :data:`LOCALITY_SPACE` (the ContinuumSpace hook-up).

House conventions (per the dazzlecmd survey): module-level frozen constants,
warm = more present (a copy in hand is maximally present, so the LOCAL reach is
the warm/positive side), ``invariant=`` names the conserved quantity at 0, and
the vocabulary is rung / axis / reach (never "band"/"tier"). ``local`` /
``local-network`` / ``remote`` are **reach aliases** -- documented shorthands
for regions of the ladder -- not rungs.

Kind -> rung mapping note (mechanism vs place): a locator's *kind* records how
its value was derived (D3/S8); its *rung* records where that value LIVES. A
``drive`` locator (a mapped letter) shares the ``unc`` rung -- it is the same
share by another name. A ``subst`` locator's value is an expanded local path ->
``file`` rung. Unknown kinds have no rung: they are excluded by reach filters
and ordered last, never guessed.
"""

from dazzle_lib import Continuum, ContinuumSpace

from .exceptions import DazzleLinkError

#: The locality ladder. Warm (+) = local possession; cold (-) = remote; the
#: rank-0 seat is the machine boundary itself. ``memory`` and ``removable``
#: are reserved rungs -- no locator kind maps to them yet, but the ladder
#: declares the full shape so later kinds slot in without renumbering.
LOCALITY_CONTINUUM = Continuum(
    name="locality",
    ranks={
        "memory": 4,      # actively loaded (reserved)
        "file": 3,        # a plain file on a local disk
        "link": 2,        # a link on disk pointing at a file (reserved)
        "removable": 1,   # a removable volume (reserved)
        "machine": 0,     # the boundary seat
        "unc": -1,        # a share on the local network (incl. mapped letters)
        "ssh": -2,        # a host reachable by ssh (reserved)
        "ftp": -3,        # an ftp endpoint (reserved)
        "internet": -4,   # the open internet (urls, content-addressed nets)
    },
    invariant="the machine boundary -- where local possession ends",
    subtype="full",
)

#: Single-axis PRODUCT composition today; Relinker's fidelity axes (the
#: degrees-of-removal ContinuumSpace) intersect here later without rework.
LOCALITY_SPACE = ContinuumSpace.compose(
    "locality-space",
    {"locality": LOCALITY_CONTINUUM},
    meaning="how close to in-hand a locator's copy lives",
)

# Locator kind -> rung name. Kind is mechanism-of-derivation; rung is place.
_KIND_RUNG = {
    "path": "file",
    "relative": "file",
    "subst": "file",     # value is the expanded real local path
    "drive": "unc",      # a mapped letter IS the share by another name
    "unc": "unc",
    "ssh": "ssh",
    "sftp": "ssh",
    "ftp": "ftp",
    "url": "internet",
    "http": "internet",
    "https": "internet",
    "ipfs": "internet",
    "torrent": "internet",
    "magnet": "internet",
    "arweave": "internet",
}

#: Reach aliases: shorthand names for regions of the ladder, mapped to a
#: representative rung for preference ordering. NOT rungs themselves.
REACH_ALIASES = {
    "local": "file",
    "local-network": "unc",
    "remote": "internet",
}


def locator_rung(kind):
    """The locality rung for a locator kind, or ``None`` for unknown kinds."""
    return _KIND_RUNG.get(kind)


def reach_of(rung):
    """The reach a rung belongs to: local / boundary / local-network / remote."""
    rank = LOCALITY_CONTINUUM.rank(rung)
    if rank > 0:
        return "local"
    if rank == 0:
        return "boundary"
    if rank >= -3:
        return "local-network"
    return "remote"


def resolve_rung(name):
    """Resolve a rung name OR reach alias to a rung on the axis.

    Raises:
        DazzleLinkError: naming the valid rungs and aliases, if unknown.
    """
    if name in LOCALITY_CONTINUUM.levels():
        return name
    if name in REACH_ALIASES:
        return REACH_ALIASES[name]
    raise DazzleLinkError(
        f"unknown locality rung or reach {name!r} -- rungs: "
        f"{', '.join(LOCALITY_CONTINUUM.levels())}; reaches: "
        f"{', '.join(REACH_ALIASES)}"
    )


def _rank_or_none(kind):
    rung = locator_rung(kind)
    return None if rung is None else LOCALITY_CONTINUUM.rank(rung)


def order_by_preference(locators, prefer):
    """Stable-sort locators by rank-distance from the preferred rung/reach.

    ``--prefer internet`` walks url -> ftp -> ssh -> unc -> local forms;
    ``--prefer file`` derives the default local-first order formally. Locators
    whose kind has no rung sort last (distance unknown, never guessed);
    original relative order is preserved within equal distances (stable sort).
    """
    target_rank = LOCALITY_CONTINUUM.rank(resolve_rung(prefer))
    far = max(abs(r) for r in LOCALITY_CONTINUUM.ranks.values()) * 2 + 1

    def distance(locator):
        rank = _rank_or_none(locator.get("kind"))
        return far if rank is None else abs(rank - target_rank)

    return sorted(locators, key=distance)


def filter_by_reach(locators, only):
    """Locators whose rung falls in the given reach (or exact rung).

    A reach alias selects its whole region; a rung name selects exactly that
    rung. Unknown-kind locators never match (no rung, no guess).
    """
    rung = resolve_rung(only)
    if only in REACH_ALIASES:
        wanted_reach = only

        def match(kind):
            r = locator_rung(kind)
            return r is not None and reach_of(r) == wanted_reach
    else:
        def match(kind):
            return locator_rung(kind) == rung

    return [loc for loc in locators if match(loc.get("kind"))]


__all__ = [
    "LOCALITY_CONTINUUM",
    "LOCALITY_SPACE",
    "REACH_ALIASES",
    "locator_rung",
    "reach_of",
    "resolve_rung",
    "order_by_preference",
    "filter_by_reach",
]
