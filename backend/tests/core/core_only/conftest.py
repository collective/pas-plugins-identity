"""Fixtures for a site with the ``core`` profile and nothing else."""

from . import CORE_PROFILE
from pas.plugins.identity import PACKAGE_NAME
from pas.plugins.identity.core.pas import PLUGIN_ID
from plone import api

import pytest


@pytest.fixture(autouse=True)
def core_only(portal, installer):
    """Leave the test site with the ``core`` profile and nothing else.

    The add-on is taken out of the test site and ``core`` alone is applied,
    inside the test's transaction, the way
    :mod:`tests.core.test_uninstalled_site` builds its site.

    :param portal: The Plone site.
    :param installer: plone.app.testing's installer.
    :returns: The Plone site.
    """
    installer.uninstall_product(PACKAGE_NAME)
    setup = api.portal.get_tool("portal_setup")
    setup.runAllImportStepsFromProfile(f"profile-{CORE_PROFILE}")
    return portal


@pytest.fixture
def identity_plugin(core_only):
    """Return the identity plugin ``core`` installed.

    :param core_only: The core-only site.
    :returns: The plugin.
    """
    return api.portal.get_tool("acl_users")[PLUGIN_ID]
