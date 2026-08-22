"""Sphinx configuration for pas.plugins.identity.

MyST rather than reStructuredText for the prose: the Plone documentation
ecosystem standardized on it, and every other file a contributor touches in
this repository is Markdown already.

The build is strict. ``-W`` in the Makefile turns warnings into errors, and
``nitpicky`` turns an unresolvable cross-reference into a warning, so a
renamed function that a page still links to fails CI rather than shipping a
dead link.
"""

project = "pas.plugins.identity"
author = "Érico Andrei"
copyright = "2026, Plone Foundation"  # noqa: A001 - Sphinx's own setting name

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
]

# No intersphinx. Nothing here uses a cross-project role, and under ``-W`` a
# failed inventory fetch turns a network blip into a red build -- which is a
# bad trade for resolving links this documentation does not make.

myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "fieldlist",
    "linkify",
    "substitution",
]

#: Heading levels that get an anchor, so pages can link into each other's
#: sections rather than only at their top.
myst_heading_anchors = 3

exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "furo"
html_static_path = ["_static"]
html_title = "pas.plugins.identity"

#: Names Sphinx cannot resolve and should not try to. Every entry is a type
#: from a package with no object inventory, not a typo we gave up on.
nitpick_ignore_regex = [
    ("py:class", r"Products\..*"),
    ("py:class", r"OFS\..*"),
    ("py:class", r"plone\..*"),
    ("py:class", r"zope\..*"),
    ("py:class", r"Any"),
]
