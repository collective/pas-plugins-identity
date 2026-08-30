"""Uninstalling leaves no registration behind and no account data missing.

Two things have to be true at once, and they pull in opposite directions: the
registrations must all go, and the user data must all stay. An uninstall that
also deleted everybody's Profile would pass a naive "no orphans" check and be
a disaster in a real site.
"""

from pas.plugins.identity import PACKAGE_NAME
from pas.plugins.identity.core.catalog import CATALOG_ID
from pas.plugins.identity.core.catalog import GROUP_PORTAL_TYPE
from pas.plugins.identity.core.catalog import PROFILE_PORTAL_TYPE
from pas.plugins.identity.core.controlpanel.controlpanel import CONFIGLET_ID
from pas.plugins.identity.core.pas import PLUGIN_ID
from pas.plugins.identity.core.pas.profile import PLUGIN_ID as PROFILE_PLUGIN_ID
from plone import api

import pytest


@pytest.fixture
def profile_with_data(portal, container):
    """A Profile that must survive the uninstall.

    :param portal: The Plone site.
    :param container: The Profile container, created first.
    :returns: Physical path of the Profile.
    """
    with api.env.adopt_roles(["Manager"]):
        profile = api.content.create(
            container=container,
            type=PROFILE_PORTAL_TYPE,
            id="alice",
            userid="alice",
            login="alice@example.com",
            fullname="Alice Liddell",
        )
    return "/".join(profile.getPhysicalPath())


@pytest.fixture(autouse=True)
def uninstalled(portal, profile_with_data, installer):
    """Uninstall the add-on, with a Profile already in the site.

    :param portal: The Plone site.
    :param profile_with_data: Path of a Profile created beforehand.
    :param installer: plone.app.testing's installer.
    :returns: That path.
    """
    installer.uninstall_product(PACKAGE_NAME)
    return profile_with_data


class TestSetupUninstall:
    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal

    def test_addon_uninstalled(self, installer):
        """Test if pas.plugins.identity is uninstalled."""
        assert installer.is_product_installed(PACKAGE_NAME) is False

    def test_browserlayer_not_registered(self, browser_layers):
        """Nothing bound to the layer answers any more."""
        from pas.plugins.identity.interfaces import IBrowserLayer

        assert IBrowserLayer not in browser_layers

    def test_controlpanel_removed(self):
        """A configlet left behind links to a panel the site no longer has."""
        tool = api.portal.get_tool("portal_controlpanel")

        assert CONFIGLET_ID not in [action.id for action in tool.listActions()]

    def test_the_versioning_modifier_is_removed(self):
        """It guards this package's credential annotation and nothing else, so
        a site without this package has no use for it -- and a persistent
        object whose class left with the package is a broken one."""
        from pas.plugins.identity.core.versioning import MODIFIER_ID

        tool = api.portal.get_tool("portal_modifier")

        assert MODIFIER_ID not in tool.objectIds()

    def test_registry_records_removed(self):
        """No orphan settings behind an add-on nobody can configure."""
        assert (
            api.portal.get_registry_record(
                "pas.plugins.identity.providers", default=None
            )
            is None
        )

    def test_profile_records_removed(self):
        """Including the ones that say where principals are filed."""
        registry = api.portal.get_tool("portal_registry")

        assert [
            name
            for name in registry.records
            if name.startswith("pas.plugins.identity.profile_")
        ] == []


class TestRegistrationsRemoved:
    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal

    def test_catalog_removed(self):
        """The derived index goes; reinstalling rebuilds it."""
        assert CATALOG_ID not in self.portal.objectIds()

    @pytest.mark.parametrize("portal_type", [PROFILE_PORTAL_TYPE, GROUP_PORTAL_TYPE])
    def test_type_removed(self, portal_type: str):
        """Both FTIs are unregistered, not just the one anybody remembers."""
        types = api.portal.get_tool("portal_types")

        assert portal_type not in types.objectIds()

    @pytest.mark.parametrize(
        "workflow", ["user_profile_workflow", "user_group_workflow"]
    )
    def test_workflow_removed(self, workflow: str):
        """And both workflow definitions."""
        workflows = api.portal.get_tool("portal_workflow")

        assert workflow not in workflows.objectIds()

    @pytest.mark.parametrize("plugin_id", [PLUGIN_ID, PROFILE_PLUGIN_ID])
    def test_pas_plugin_removed(self, plugin_id: str):
        """No orphan plugins."""
        acl_users = api.portal.get_tool("acl_users")

        assert plugin_id not in acl_users.objectIds()

    @pytest.mark.parametrize("plugin_id", [PLUGIN_ID, PROFILE_PLUGIN_ID])
    def test_pas_plugin_deactivated_everywhere(self, plugin_id: str):
        """A plugin id left in an interface list breaks the next PAS lookup."""
        plugins = api.portal.get_tool("acl_users").plugins

        for info in plugins.listPluginTypeInfo():
            assert plugin_id not in plugins.listPluginIds(info["interface"])

    def test_properties_fall_back_to_the_seeded_sheet(self):
        """The site still works, on the stock plugins alone."""
        acl_users = api.portal.get_tool("acl_users")
        acl_users.source_users.addUser("bob", "bob", "placeholder-password")
        api.user.get(userid="bob").setMemberProperties({"fullname": "Bob"})

        assert api.user.get(userid="bob").getProperty("fullname") == "Bob"


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
