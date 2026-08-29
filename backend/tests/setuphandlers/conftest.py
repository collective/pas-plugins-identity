"""Fixtures for the install and uninstall suites.

Deliberately thin. What every other suite gets from ``tests/core/conftest.py``
-- a manager role and a Profile container waiting for it -- is exactly what
these tests are about, so they start from a site that has only been installed
and make what they need, by name.
"""

from pas.plugins.identity.core.catalog import CATALOG_ID
from pas.plugins.identity.core.container import get_container
from plone import api

import pytest


@pytest.fixture
def catalog(portal):
    """The Profile catalog.

    :param portal: The Plone site.
    :returns: The catalog tool.
    """
    return api.portal.get_tool(CATALOG_ID)


@pytest.fixture
def container(portal):
    """Create the Profile container, as a first login would.

    :param portal: The Plone site.
    :returns: The container.
    """
    with api.env.adopt_roles(["Manager"]):
        return get_container(create=True)
