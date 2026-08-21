"""Fixtures for the migration tests (Gate 7)."""

import pytest


@pytest.fixture
def portal(integration):
    """The site, with this package installed.

    :param integration: The integration layer.
    :returns: The Plone site.
    """
    return integration["portal"]
