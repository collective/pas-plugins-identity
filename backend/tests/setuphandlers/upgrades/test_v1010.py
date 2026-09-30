"""Version 1010: listing every user asks the profile plugin too (#131).

The class answers ``IUserIntrospection`` from the deploy on. A site installed
earlier has to be told to ask it, and that activation is what this step adds.
"""

from pas.plugins.identity.core.pas.profile import PLUGIN_ID
from plone import api
from Products.PlonePAS.interfaces.plugins import IUserIntrospection
from Products.PluggableAuthService.interfaces.plugins import IPropertiesPlugin

import pytest


class TestTheProfilePluginIsActivated:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, upgrade_from) -> None:
        self.plugins = api.portal.get_tool("acl_users").plugins
        self.upgrade_from = upgrade_from
        # Deactivated first, so this tests the upgrade rather than the install.
        self.plugins.deactivatePlugin(IUserIntrospection, PLUGIN_ID)
        assert PLUGIN_ID not in self.plugins.listPluginIds(IUserIntrospection)

    def test_it_is_activated(self):
        self.upgrade_from("1009")

        assert PLUGIN_ID in self.plugins.listPluginIds(IUserIntrospection)

    def test_properties_order_is_left_alone(self):
        """Only the one interface: a site that moved the plugin down
        ``IPropertiesPlugin`` keeps that order."""
        self.plugins.movePluginsDown(IPropertiesPlugin, [PLUGIN_ID])
        before = self.plugins.listPluginIds(IPropertiesPlugin)

        self.upgrade_from("1009")

        assert self.plugins.listPluginIds(IPropertiesPlugin) == before

    def test_running_it_twice_is_harmless(self):
        self.upgrade_from("1009")
        self.upgrade_from("1009")

        assert (
            list(self.plugins.listPluginIds(IUserIntrospection)).count(PLUGIN_ID) == 1
        )
