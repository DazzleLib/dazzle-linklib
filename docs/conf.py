"""Sphinx configuration for the dazzle-linklib documentation.

The pages themselves are Markdown, read through MyST, so a single source
serves both GitHub (where most people meet this project) and the rendered
site. Nothing here requires the docs to be written twice. (The structure
mirrors dazzle-filekit's docs, the stack's reference implementation.)

Build locally:

    pip install -r docs/requirements.txt
    sphinx-build -b html docs docs/_build/html -W

`-W` turns warnings into errors, which is what the Read the Docs build does
too -- a broken cross-reference should fail the build rather than ship as a
dead link.
"""
from __future__ import annotations

import os
import sys
from datetime import date

# Import the package so the version below is the actual installed one rather
# than a copy that drifts.
sys.path.insert(0, os.path.abspath(".."))

# -- Project ---------------------------------------------------------------

project = "dazzle-linklib"
author = "Dustin Darcy"
copyright = f"{date.today().year}, {author}"

try:
    from dazzle_linklib import __version__ as release
except Exception:  # pragma: no cover - docs must build even if import fails
    release = "0.0.0"
version = ".".join(release.split(".")[:2])

# -- General ---------------------------------------------------------------

extensions = [
    # Markdown source, so docs/*.md render as-is
    "myst_parser",
    # API pages generated from the package's own docstrings
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",        # Google/NumPy-style docstring sections
    "sphinx.ext.viewcode",        # "[source]" links next to each symbol
    "sphinx.ext.intersphinx",     # link `pathlib.Path` etc. to the stdlib docs
    "sphinx.ext.autosectionlabel",
    # Presentation
    "sphinx_copybutton",          # copy button on every code block
    "sphinx_design",              # cards and grids on the landing page
    "sphinxcontrib.mermaid",      # diagrams as text, versioned with the docs
]

source_suffix = {".md": "markdown", ".rst": "restructuredtext"}
master_doc = "index"
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store", "README.md"]

# Section labels are prefixed with the document name so two pages may both
# have an "Overview" heading without colliding.
autosectionlabel_prefix_document = True
# Only label H1/H2. Deeper than that and the CHANGELOG's repeated
# '### Added' / '### Changed' headings collide with one another, which is
# correct Keep-a-Changelog structure, not a defect to work around.
autosectionlabel_maxdepth = 2

# -- MyST ------------------------------------------------------------------

myst_enable_extensions = [
    "colon_fence",      # ::: fences, needed by sphinx-design directives
    "deflist",          # definition lists
    "linkify",          # bare URLs become links
    "substitution",
    "tasklist",
    "attrs_inline",
]
myst_url_schemes = ("http", "https", "mailto")
myst_heading_anchors = 3
# Treat a plain ```mermaid fence as the mermaid directive. This is what
# lets one source serve both surfaces: GitHub renders ```mermaid natively,
# and it would show ```{mermaid} as a raw code block.
myst_fence_as_directive = ["mermaid"]

# -- autodoc ---------------------------------------------------------------

autodoc_default_options = {
    "members": True,
    "undoc-members": False,
}
autodoc_member_order = "bysource"

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}

# -- HTML ------------------------------------------------------------------

html_theme = "furo"
html_title = f"{project} {release.split('_')[0]}"
