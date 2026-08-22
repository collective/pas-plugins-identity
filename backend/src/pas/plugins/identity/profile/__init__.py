"""The ``[profile]`` layer -- Profile content type and group support.

Optional: installed by ``pip install pas.plugins.identity[profile]``. This
layer may import :mod:`pas.plugins.identity.core`, through its public API and
its events only. Nothing in ``core`` may import from here, which is
what keeps the no-extras install working; the import-linter contract in
``pyproject.toml`` enforces it.
"""
