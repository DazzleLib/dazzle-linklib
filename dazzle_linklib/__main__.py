"""Allow running as: python -m dazzle_linklib

dazzle-linklib is a LIBRARY, not a CLI -- the `dazzlelink` command lives in the
DazzleTools/dazzlelink tool (STACK-MAP D1). Running the module just reports the
installed version.
"""
from . import __app_name__, __version__


def main() -> None:
    print(f"{__app_name__} {__version__}")
    print("Library only -- the dazzlelink CLI lives in DazzleTools/dazzlelink.")


if __name__ == "__main__":
    main()
