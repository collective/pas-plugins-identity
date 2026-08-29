"""The ``[server]`` layer -- Plone as an OAuth 2.1 / OIDC provider.

Optional, and the only optional thing left: installed by ``pip install
pas.plugins.identity[server]``, because ``cryptography`` is compiled and a
site that is not an authorization server has no reason to carry it.

This layer may import :mod:`pas.plugins.identity.core`, through its public API
and its events only. Nothing in ``core`` may import from here; the
import-linter contract in ``pyproject.toml`` enforces it.
"""
