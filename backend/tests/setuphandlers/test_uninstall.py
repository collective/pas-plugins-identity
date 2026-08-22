from pas.plugins.identity import PACKAGE_NAME
from pas.plugins.identity.core.controlpanel.controlpanel import CONFIGLET_ID
from plone import api

import pytest


class TestSetupUninstall:
    @pytest.fixture(autouse=True)
    def uninstalled(self, installer):
        installer.uninstall_product(PACKAGE_NAME)

    def test_addon_uninstalled(self, installer):
        """Test if pas.plugins.identity is uninstalled."""
        assert installer.is_product_installed(PACKAGE_NAME) is False

    def test_browserlayer_not_registered(self, browser_layers):
        """Test that IBrowserLayer is not registered."""
        from pas.plugins.identity.interfaces import IBrowserLayer

        assert IBrowserLayer not in browser_layers

    def test_controlpanel_removed(self, portal):
        """A configlet left behind links to a panel the site no longer has."""
        tool = api.portal.get_tool("portal_controlpanel")

        assert CONFIGLET_ID not in [action.id for action in tool.listActions()]

    def test_registry_records_removed(self, portal):
        """No orphan settings behind an add-on nobody can configure."""
        assert (
            api.portal.get_registry_record(
                "pas.plugins.identity.providers", default=None
            )
            is None
        )
