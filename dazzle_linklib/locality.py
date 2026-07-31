"""The LOCALITY axis -- where a copy lives, as a real dazzle-lib Continuum.

The Relinker continuum vision (the 2026-07-30 vision note + the #25 DWP
Amendment 4): every locator sits on a monopole ladder running outward from
possession. The rank-0 seat is the REST STATE -- the copy in hand, the default
the tool assumes when no selector is given -- and each step outward is one
degree of locational removal (removal distance = ``abs(rank)``, the
MATERIALIZATION "degrees of indirection" pattern). The machine boundary is not
a seat: it is the ``local -> intranet`` EDGE, the capability cliff where direct
file APIs stop being available (each step outward keeps a shrinking subset of
capabilities; capability-loss channel sets are ledgered, declared when a
capability-gated consumer exists).

House conventions (dazzle-lib docs/the-ladder.md; the 2026-07-05 bedrock DWP):
warm = more of the quality expressed -- possession is the quality here, so the
warm pole is ``local`` at 0 and the single reach extends negatively, exactly
like every shipped monopole (visibility, activation, materialization,
upstream). ``invariant=`` names the conserved quantity at 0. Vocabulary is
rung / axis / reach (never "band"/"tier").

Kind vs rung (mechanism vs place -- D3/S8, sharpened in DWP A4.7): a locator's
*kind* records how its value was derived; kind and locality are ORTHOGONAL
axes (ssh/http/anything can be loopback, LAN, or internet -- a protocol does
not determine a place). The kind -> rung map below is therefore a
producer-grounded heuristic, trustworthy exactly where a producer vouches for
the value's locality: unc/drive values come from real machine mappings
(intranet), the path family from a local filesystem walk (local), and url from
``--also-url`` meaning "the web copy" (internet). Kinds no producer vouches
for -- ssh, sftp, ftp -- have NO rung: excluded by reach filters, ordered
last, never guessed. They remain selectable by NAME via the kind fallthrough
(below). Reserved former seats (memory/link/removable warm-side; ssh/ftp
cold-side) are ledgered in the #25 DWP with reopen triggers; rungs are
insertable later without breaking anything (locality is derived, never stored
in records) -- only the rank-0 seat is immovable (house doctrine).

Selector spelling chain (DWP A4.2/A4.6, registry-free by design): a
``prefer``/``only`` spelling resolves as (1) a rung name, (2) a reach alias
(``remote``, ``local-network``), (3) a scheme alias (``http``/``https``/
``url`` -> internet), and otherwise (4) falls through to KIND selection --
any protocol spelling at all (ftp, ssh, gopher, archie, a user-invented one)
selects locators of that kind verbatim. The RECORD is the validator: a
spelling matching nothing surfaces as a no-match error naming what the record
has, not as a vocabulary error.
"""

from dazzle_lib import Continuum, ContinuumSpace

from .exceptions import DazzleLinkError

#: The locality ladder: a monopole -- possession at the rank-0 rest seat, the
#: single reach extending outward/negative. Removal distance = ``abs(rank)``.
LOCALITY_CONTINUUM = Continuum(
    name="locality",
    ranks={
        "local": 0,       # the rest state / DEFAULT: the copy is in hand
        "intranet": -1,   # the network neighborhood (shares, mapped letters)
        "internet": -2,   # beyond it (the open net, content-addressed nets)
    },
    invariant="possession -- the copy in hand",
    subtype="monopole",
)

#: Single-axis PRODUCT composition today; Relinker's fidelity axes (the
#: degrees-of-removal ContinuumSpace) and the ledgered PROTOCOL/kind axis
#: (DWP A4.7: BOUNDARY x PROTOCOL) intersect here later without rework.
LOCALITY_SPACE = ContinuumSpace.compose(
    "locality-space",
    {"locality": LOCALITY_CONTINUUM},
    meaning="how close to in-hand a locator's copy lives",
)

# Locator kind -> rung name: producer-grounded heuristic (see module
# docstring). ssh/sftp/ftp are deliberately ABSENT -- recognized kinds with no
# rung (no producer vouches for their locality); select them by name instead.
_KIND_RUNG = {
    "path": "local",
    "relative": "local",
    "subst": "local",       # value is the expanded real local path
    "drive": "intranet",    # a mapped letter IS the share by another name
    "unc": "intranet",
    "url": "internet",
    "http": "internet",
    "https": "internet",
    "ipfs": "internet",
    "torrent": "internet",
    "magnet": "internet",
    "arweave": "internet",
}

#: Reach aliases: natural-speech shorthands for rungs. NOT rungs themselves.
#: (``local`` needs no alias -- it IS the rung.)
REACH_ALIASES = {
    "local-network": "intranet",
    "remote": "internet",
}

#: Scheme aliases (DWP A4.6, user-decided): the most common protocol
#: spellings resolve to the internet rung with TIER semantics -- "the web
#: copy". Distinct from kind fallthrough, which is mechanism-exact.
SCHEME_ALIASES = {
    "http": "internet",
    "https": "internet",
    "url": "internet",
}


def locator_rung(kind):
    """The locality rung for a locator kind, or ``None`` when no producer
    vouches for the kind's locality (ssh/sftp/ftp, unknown kinds)."""
    return _KIND_RUNG.get(kind)


def reach_of(rung):
    """The reach a rung belongs to: local / local-network / remote."""
    rank = LOCALITY_CONTINUUM.rank(rung)
    if rank == 0:
        return "local"
    if rank == -1:
        return "local-network"
    return "remote"


def resolve_rung(name):
    """Resolve a rung name, reach alias, or scheme alias to a rung.

    This resolves RUNG spellings only -- the kind fallthrough (any other
    protocol spelling selects by kind) lives in :func:`order_by_preference` /
    :func:`filter_by_reach`, which try this first and fall through on the
    error.

    Raises:
        DazzleLinkError: naming the rung/alias vocabulary, if unknown here.
    """
    if name in LOCALITY_CONTINUUM.levels():
        return name
    if name in REACH_ALIASES:
        return REACH_ALIASES[name]
    if name in SCHEME_ALIASES:
        return SCHEME_ALIASES[name]
    raise DazzleLinkError(
        f"{name!r} is not a locality rung ({', '.join(LOCALITY_CONTINUUM.levels())}), "
        f"reach alias ({', '.join(REACH_ALIASES)}), or scheme alias "
        f"({', '.join(SCHEME_ALIASES)})"
    )


def _rank_or_none(kind):
    rung = locator_rung(kind)
    return None if rung is None else LOCALITY_CONTINUUM.rank(rung)


def order_by_preference(locators, prefer):
    """Stable-sort locators by the preference spelling.

    Rung/reach/scheme spellings sort by rank-distance from the resolved rung
    (``prefer='remote'`` walks internet -> intranet -> local forms;
    ``prefer='local'`` derives the default order formally). Any OTHER spelling
    is a KIND preference: locators of exactly that kind first, everything else
    after in original order (registry-free -- gopher, archie, s3, anything).
    Preference never filters; rung-less locators sort last under rung
    preference (distance unknown, never guessed).
    """
    try:
        target_rank = LOCALITY_CONTINUUM.rank(resolve_rung(prefer))
    except DazzleLinkError:
        return sorted(locators, key=lambda loc: 0 if loc.get("kind") == prefer else 1)
    far = max(abs(r) for r in LOCALITY_CONTINUUM.ranks.values()) * 2 + 1

    def distance(locator):
        rank = _rank_or_none(locator.get("kind"))
        return far if rank is None else abs(rank - target_rank)

    return sorted(locators, key=distance)


def filter_by_reach(locators, only):
    """Locators matching the selection spelling.

    Rung/reach/scheme spellings select the resolved rung's locators; any
    OTHER spelling selects locators of exactly that kind (registry-free).
    Rung-less locators (ssh/sftp/ftp, unknown kinds) never match a rung
    spelling -- select them by kind name.
    """
    try:
        rung = resolve_rung(only)
    except DazzleLinkError:
        return [loc for loc in locators if loc.get("kind") == only]
    return [loc for loc in locators if locator_rung(loc.get("kind")) == rung]


__all__ = [
    "LOCALITY_CONTINUUM",
    "LOCALITY_SPACE",
    "REACH_ALIASES",
    "SCHEME_ALIASES",
    "locator_rung",
    "reach_of",
    "resolve_rung",
    "order_by_preference",
    "filter_by_reach",
]
