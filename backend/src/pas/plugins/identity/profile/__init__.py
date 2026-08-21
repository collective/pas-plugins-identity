"""The ``[profile]`` layer (Gate 6) -- Profile content type and group support.

Optional: installed by ``pip install pas.plugins.identity[profile]``. This
layer may import :mod:`pas.plugins.identity.core`, through its public API and
its events only. Nothing in ``core`` may import from here (§4.2), which is
what keeps the no-extras install working (I5); the import-linter contract in
``pyproject.toml`` enforces it.
"""
