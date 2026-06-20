"""Exceptions for dazzle-linklib, rooted in the dazzle-lib stack hierarchy.

``DazzleLinkError`` subclasses :class:`dazzle_lib.LinkError` (itself a
:class:`dazzle_lib.DazzleError`) so any consumer can catch the whole stack's
errors via ``DazzleError``. ``DazzleLinkException`` is kept as a back-compat
alias -- the dazzlelink CLI tool and preservelib import that name.
"""

from dazzle_lib import LinkError


class DazzleLinkError(LinkError):
    """Raised for .dazzlelink record problems: parse, serialize, resolve."""


# Back-compat alias (dazzlelink tool + preservelib import DazzleLinkException).
DazzleLinkException = DazzleLinkError

__all__ = ["DazzleLinkError", "DazzleLinkException"]
