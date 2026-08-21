from pas.plugins.identity import PACKAGE_NAME
from pas.plugins.identity.setuphandlers import HiddenProfiles


class TestHiddenProfiles:
    """The add-ons control panel should offer one thing: the add-on."""

    def test_uninstall_profiles_hidden(self):
        """Uninstall profiles are reached through the add-on, not listed."""
        hidden = HiddenProfiles().getNonInstallableProfiles()

        assert f"{PACKAGE_NAME}:uninstall" in hidden
        assert f"{PACKAGE_NAME}:uninstall-profile" in hidden
        assert f"{PACKAGE_NAME}:uninstall-server" in hidden

    def test_default_profile_stays_installable(self):
        """Hiding must not hide the profile people actually install."""
        assert f"{PACKAGE_NAME}:default" not in (
            HiddenProfiles().getNonInstallableProfiles()
        )

    def test_upgrades_package_hidden(self):
        """The upgrades package is machinery, not a product."""
        assert HiddenProfiles().getNonInstallableProducts() == [
            f"{PACKAGE_NAME}.upgrades"
        ]


class TestSetupInstall:
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
