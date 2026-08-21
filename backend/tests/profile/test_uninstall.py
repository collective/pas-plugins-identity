"""Uninstalling the ``[profile]`` layer (I8).

Two things have to be true at once, and they pull in opposite directions: the
registrations must all go, and the user data must all stay. An uninstall that
also deleted everybody's Profile would pass a naive "no orphans" check and be
a disaster in a real site.
"""

from pas.plugins.identity import PACKAGE_NAME
from pas.plugins.identity.profile.catalog import CATALOG_ID
from pas.plugins.identity.profile.catalog import PROFILE_PORTAL_TYPE
from pas.plugins.identity.profile.interfaces import IIdentityProfileLayer
from plone import api

import pytest


@pytest.fixture
def profile_with_data(portal):
    """A Profile that must survive the uninstall.

    :param portal: The Plone site.
    :returns: Physical path of the Profile.
    """
    with api.env.adopt_roles(["Manager"]):
        profile = api.content.create(
            container=portal["identity-profiles"],
            type=PROFILE_PORTAL_TYPE,
            id="alice",
            userid="alice",
            login="alice@example.com",
            fullname="Alice Liddell",
        )
    return "/".join(profile.getPhysicalPath())


@pytest.fixture
def uninstalled(portal, profile_with_data):
    """Apply the uninstall profile.

    :param portal: The Plone site.
    :param profile_with_data: Path of a Profile created beforehand.
    :returns: That path.
    """
    setup = api.portal.get_tool("portal_setup")
    setup.runAllImportStepsFromProfile(f"profile-{PACKAGE_NAME}:uninstall-profile")
    return profile_with_data


class TestRegistrationsRemoved:
    def test_catalog_removed(self, portal, uninstalled):
        """The derived index goes; reinstalling rebuilds it."""
        assert CATALOG_ID not in portal.objectIds()

    def test_type_removed(self, portal, uninstalled):
        """The FTI is unregistered."""
        types = api.portal.get_tool("portal_types")
        assert PROFILE_PORTAL_TYPE not in types.objectIds()

    def test_workflow_removed(self, portal, uninstalled):
        """The workflow definition is unregistered."""
        workflows = api.portal.get_tool("portal_workflow")
        assert "identity_profile_workflow" not in workflows.objectIds()

    def test_browserlayer_removed(self, portal, uninstalled, browser_layers):
        """Nothing bound to the layer answers any more."""
        assert IIdentityProfileLayer not in browser_layers

    def test_registry_records_removed(self, portal, uninstalled):
        """No orphan registry keys (I8)."""
        registry = api.portal.get_tool("portal_registry")
        assert [
            name
            for name in registry.records
            if name.startswith("pas.plugins.identity.profile_")
        ] == []


class TestContentKept:
    def test_profile_survives(self, portal, uninstalled):
        """Uninstalling an add-on is not an instruction to delete accounts."""
        assert portal.unrestrictedTraverse(uninstalled, None) is not None

    def test_field_values_survive(self, portal, uninstalled):
        """The data is intact, not just the object."""
        profile = portal.unrestrictedTraverse(uninstalled)
        assert profile.fullname == "Alice Liddell"

    def test_container_survives(self, portal, uninstalled):
        """So does the folder holding them."""
        assert "identity-profiles" in portal.objectIds()
