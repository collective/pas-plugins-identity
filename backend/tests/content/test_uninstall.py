"""Uninstalling the ``[content]`` layer.

Two things have to be true at once, and they pull in opposite directions: the
registrations must all go, and the user data must all stay. An uninstall that
also deleted everybody's Profile would pass a naive "no orphans" check and be
a disaster in a real site.
"""

from . import PROFILE_ID
from pas.plugins.identity import PACKAGE_NAME
from pas.plugins.identity.content.catalog import CATALOG_ID
from pas.plugins.identity.content.catalog import PROFILE_PORTAL_TYPE
from pas.plugins.identity.content.interfaces import IIdentityContentLayer
from pas.plugins.identity.content.pas import PLUGIN_ID as PROFILE_PLUGIN_ID
from plone import api

import pytest


pytestmark = pytest.mark.portal(profiles=[PROFILE_ID])


@pytest.fixture
def profile_with_data(portal):
    """A Profile that must survive the uninstall.

    :param portal: The Plone site.
    :returns: Physical path of the Profile.
    """
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
    setup.runAllImportStepsFromProfile(f"profile-{PACKAGE_NAME}.content:uninstall")
    return profile_with_data


class TestRegistrationsRemoved:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, uninstalled) -> None:
        self.portal = portal
        self.uninstalled = uninstalled

    def test_catalog_removed(self):
        """The derived index goes; reinstalling rebuilds it."""
        assert CATALOG_ID not in self.portal.objectIds()

    def test_type_removed(self):
        """The FTI is unregistered."""
        types = api.portal.get_tool("portal_types")
        assert PROFILE_PORTAL_TYPE not in types.objectIds()

    def test_workflow_removed(self):
        """The workflow definition is unregistered."""
        workflows = api.portal.get_tool("portal_workflow")
        assert "identity_profile_workflow" not in workflows.objectIds()

    def test_group_type_removed(self):
        """Both content types go, not just the one anybody remembers."""
        types = api.portal.get_tool("portal_types")
        assert "UserGroup" not in types.objectIds()

    def test_group_workflow_removed(self):
        """And both workflows."""
        workflows = api.portal.get_tool("portal_workflow")
        assert "identity_group_workflow" not in workflows.objectIds()

    def test_pas_plugin_removed(self):
        """No orphan plugins."""
        acl_users = api.portal.get_tool("acl_users")

        assert PROFILE_PLUGIN_ID not in acl_users.objectIds()

    def test_pas_plugin_deactivated_everywhere(self):
        """A plugin id left in an interface list breaks the next PAS lookup."""
        plugins = api.portal.get_tool("acl_users").plugins

        for info in plugins.listPluginTypeInfo():
            assert PROFILE_PLUGIN_ID not in plugins.listPluginIds(info["interface"])

    def test_properties_fall_back_to_the_seeded_sheet(self):
        """The site still works, on whatever core left behind."""
        acl_users = api.portal.get_tool("acl_users")
        acl_users.source_users.addUser("bob", "bob", "placeholder-password")
        api.user.get(userid="bob").setMemberProperties({"fullname": "Bob"})

        assert api.user.get(userid="bob").getProperty("fullname") == "Bob"

    def test_browserlayer_removed(self, browser_layers):
        """Nothing bound to the layer answers any more."""
        assert IIdentityContentLayer not in browser_layers

    def test_registry_records_removed(self):
        """No orphan registry keys."""
        registry = api.portal.get_tool("portal_registry")
        assert [
            name
            for name in registry.records
            if name.startswith("pas.plugins.identity.profile_")
        ] == []


class TestContentKept:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, uninstalled) -> None:
        self.portal = portal
        self.uninstalled = uninstalled

    def test_profile_survives(self):
        """Uninstalling an add-on is not an instruction to delete accounts."""
        assert self.portal.unrestrictedTraverse(self.uninstalled, None) is not None

    def test_field_values_survive(self):
        """The data is intact, not just the object."""
        profile = self.portal.unrestrictedTraverse(self.uninstalled)
        assert profile.fullname == "Alice Liddell"

    def test_container_survives(self):
        """So does the folder holding them."""
        assert "identity-profiles" in self.portal.objectIds()
