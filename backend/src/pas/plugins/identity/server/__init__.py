"""The ``[server]`` layer (Gates S1--S3) -- Plone as an OAuth 2.1 / OIDC provider.

Optional: installed by ``pip install pas.plugins.identity[server]``. This
layer may import :mod:`pas.plugins.identity.core`, through its public API and
its events only. Nothing in ``core`` may import from here, and neither may
:mod:`pas.plugins.identity.profile` (§4.2); the import-linter contract in
``pyproject.toml`` enforces both.
"""
