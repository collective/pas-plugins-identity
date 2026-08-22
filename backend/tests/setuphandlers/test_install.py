from pas.plugins.identity import PACKAGE_NAME
from plone import api

import pytest


@pytest.fixture(scope="class")
def portal(portal_class):
    """Return the portal."""
    yield portal_class


class TestHiddenProfiles:
    """The add-ons control panel should offer one thing: the add-on."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal
        self.non_installable = api.addon._get_non_installable_addons()

    @pytest.mark.parametrize(
        "profile",
        [
            f"{PACKAGE_NAME}:uninstall",
            f"{PACKAGE_NAME}:uninstall-profile",
            f"{PACKAGE_NAME}:uninstall-server",
        ],
    )
    def test_uninstall_profiles_hidden(self, profile: str):
        """Uninstall profiles are reached through the add-on, not listed."""
        assert profile in self.non_installable.profiles

    @pytest.mark.parametrize(
        "profile",
        [
            f"{PACKAGE_NAME}:default",
        ],
    )
    def test_default_profile_stays_installable(self, profile: str):
        """Hiding must not hide the profile people actually install."""
        assert profile not in self.non_installable.profiles

    @pytest.mark.parametrize(
        "package",
        [
            f"{PACKAGE_NAME}.upgrades",
        ],
    )
    def test_upgrades_package_hidden(self, package: str):
        """The upgrades package is machinery, not a product."""
        assert package in self.non_installable.products


class TestSetupInstall:
    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal

    def test_addon_installed(self, installer):
        """Test if pas.plugins.identity is installed."""
        assert installer.is_product_installed(PACKAGE_NAME) is True

    def test_browserlayer(self, browser_layers):
        """Test that IBrowserLayer is registered."""
        from pas.plugins.identity.interfaces import IBrowserLayer

        assert IBrowserLayer in browser_layers

    def test_latest_version(self, profile_last_version):
        """Test latest version of default profile."""
        assert profile_last_version(f"{PACKAGE_NAME}:default") == "1000"
