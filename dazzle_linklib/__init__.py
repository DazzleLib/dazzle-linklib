"""dazzle-linklib -- the DazzleLib stack's L2 link-record library.

A **content-addressable link record**: one model that maps an identity to a
typed list of locators plus metadata, and knows how to serialize, find, and
resolve itself. It is the portable-DATA layer beneath three consumers:

* the **dazzlelink** filesystem CLI (the `.dazzlelink` file format),
* **preserve**'s content-hash manifest (L3), and
* **Relinker** -- a hash-addressed, decentralized anti-link-rot resolver
  (``rln.kr/{hash}`` -> a multi-protocol location set).

The boundary (STACK-MAP, layers B/L0/L1/L2/L3): this library owns the link
RECORD -- its schema, JSON I/O, locator list, ``content_id``, and relation
edges -- and the injectable target resolver. It does NOT own filesystem
mechanics (those delegate down to ``dazzle-filekit`` L1), UNC/drive identity
(``unctools`` L0), or graph TRAVERSAL (``dazzletreelib`` is the perpendicular
traversal tier). "Records that point at each other" live here; "walking and
interpreting those pointers" do not (see the L2 design DWP, decision D6).

Status: **P2 build in progress (0.1.x, pre-alpha).** The record model
(``DazzleLinkData``), its exceptions, the record discovery/rebase surface
(``find_dazzlelinks``/``scan``/``rebase``), and the injectable target resolver
(``resolve_target``) are extracted from the dazzlelink tool. Tracked on the
roadmap (issue #2).

License: MIT (whole stack; STACK-MAP D11). Architecture contract:
https://github.com/DazzleLib/.github/blob/main/docs/STACK-MAP.md
"""

from ._version import PIP_VERSION, __app_name__, __version__
from .discovery import find_dazzlelinks, rebase, scan
from .exceptions import DazzleLinkError, DazzleLinkException
from .record import DazzleLinkData
from .resolver import ReachabilityResolver, default_reachability, resolve_target

__all__ = [
    "__version__",
    "__app_name__",
    "PIP_VERSION",
    "DazzleLinkData",
    "DazzleLinkError",
    "DazzleLinkException",
    "find_dazzlelinks",
    "scan",
    "rebase",
    "resolve_target",
    "ReachabilityResolver",
    "default_reachability",
]
