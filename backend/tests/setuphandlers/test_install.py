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
            f"{PACKAGE_NAME}.content:uninstall",
            f"{PACKAGE_NAME}.server:uninstall",
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


class TestTheLayersAreTheirOwnProducts:
    """Each optional layer installs as its own entry in the add-ons panel.

    That follows from where its ``registerProfile`` lives: GenericSetup builds
    the profile id from the package the directive is in, so the layers are
    ``pas.plugins.identity.content`` and ``pas.plugins.identity.server``
    rather than extra profiles of the distribution.

    The installer resolves a product's version through
    ``importlib.metadata.distribution``, and neither of these package names is
    a distribution. That answers empty rather than raising -- but "rather than
    raising" is the whole reason this class exists, because it is the one way
    this arrangement could break the control panel for the whole site.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, portal, installer) -> None:
        self.portal = portal
        self.installer = installer

    @pytest.mark.parametrize(
        "product",
        [
            f"{PACKAGE_NAME}.content",
            f"{PACKAGE_NAME}.server",
        ],
    )
    def test_the_layer_is_installable(self, product: str):
        """The panel offers it, which means it found a default profile."""
        assert self.installer.is_product_installable(product) is True

    @pytest.mark.parametrize(
        "product",
        [
            f"{PACKAGE_NAME}.content",
            f"{PACKAGE_NAME}.server",
        ],
    )
    def test_the_install_profile_resolves(self, product: str):
        """``default`` is the name the panel's install button applies."""
        profile = self.installer.get_install_profile(product)
        assert profile is not None
        assert profile["id"] == f"{product}:default"

    @pytest.mark.parametrize(
        "product",
        [
            f"{PACKAGE_NAME}.content",
            f"{PACKAGE_NAME}.server",
        ],
    )
    def test_the_uninstall_profile_resolves(self, product: str):
        """Hidden from the list, still reachable through the add-on."""
        profile = self.installer.get_uninstall_profile(product)
        assert profile is not None
        assert profile["id"] == f"{product}:uninstall"

    @pytest.mark.parametrize(
        "product",
        [
            f"{PACKAGE_NAME}.content",
            f"{PACKAGE_NAME}.server",
        ],
    )
    def test_asking_for_a_version_does_not_raise(self, product: str):
        """A package that is not a distribution has no version to report.

        The panel renders the empty string; what it must not do is propagate
        ``PackageNotFoundError`` out of a listing that also has to render
        every other add-on on the site.
        """
        assert self.installer.get_product_version(product) == ""


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
