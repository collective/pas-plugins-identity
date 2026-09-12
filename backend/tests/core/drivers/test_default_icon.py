"""A default login-button icon per driver, and a provider's own upload over it.

The default is resolved when a provider is drawn and never stored, so the
tests below ask three places: the driver, the provider's ``style()`` -- which
both ``@login-providers`` and ``@identities`` render through -- and what the
provider would write back.
"""

from importlib.resources import files
from pas.plugins.identity.core.controlpanel import ProviderConfig
from pas.plugins.identity.core.drivers import all_drivers
from pas.plugins.identity.core.drivers.oidc import GenericOIDCDriver
from pas.plugins.identity.core.services.login import render_provider
from pas.plugins.identity.core.utils.svg import sanitize

import pytest


#: An icon a provider could have uploaded.
ICON = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16">'
    '<path d="M8 1l7 13H1z"/></svg>'
)

#: Every driver this package ships, each with an icon file named after it.
SHIPPED = ["github", "google", "oidc-generic", "plone-identity", "email"]


def shipped_source(driver_id: str) -> str:
    """Return the icon file a shipped driver names, as it is on disk.

    :param driver_id: The driver.
    :returns: The unsanitized SVG source.
    """
    icons = files("pas.plugins.identity.core.drivers").joinpath("icons")
    return icons.joinpath(f"{driver_id}.svg").read_text(encoding="utf-8")


class TestEveryDriverHasOne:
    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.drivers = all_drivers()

    @pytest.mark.parametrize("driver_id", SHIPPED)
    def test_it_is_the_shipped_file_sanitized(self, driver_id: str):
        """Through ``core/utils/svg.py`` like an upload, although it ships with
        the package: an icon is inlined into the login page, and where it came
        from does not change what inlining it does."""
        assert self.drivers[driver_id].default_icon == sanitize(
            shipped_source(driver_id)
        )

    def test_no_registered_driver_is_left_without_one(self):
        """A driver added later without an icon fails here rather than drawing
        a bare label nobody notices."""
        assert all(driver.default_icon for driver in self.drivers.values())

    def test_the_inkscape_metadata_is_not_served(self):
        """The OpenID mark is an Inkscape file. What reaches a login page is
        its two paths."""
        icon = self.drivers["oidc-generic"].default_icon

        assert "sodipodi" not in icon
        assert "metadata" not in icon


class TestADriverWithoutAUsableIcon:
    def test_no_resource_is_no_icon(self):
        class Plain(GenericOIDCDriver):
            icon_resource = ""

        assert Plain().default_icon == ""

    @pytest.mark.parametrize(
        "resource",
        [
            pytest.param(
                "pas.plugins.identity.core.drivers:icons/no-such.svg",
                id="missing-file",
            ),
            pytest.param("no.such.package:icon.svg", id="missing-package"),
            pytest.param(
                "pas.plugins.identity.core.drivers:__init__.py", id="not-an-svg"
            ),
        ],
    )
    def test_a_broken_resource_is_no_icon_and_a_warning(self, resource: str, caplog):
        """A third-party driver shipping a broken icon must not take the login
        page down with it."""

        class Broken(GenericOIDCDriver):
            icon_resource = resource

        assert Broken().default_icon == ""
        assert resource in caplog.text


class TestTheProvidersOwnIconWins:
    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.default = all_drivers()["github"].default_icon

    def provider(self, **overrides) -> ProviderConfig:
        """Return a GitHub provider.

        :param overrides: Constructor arguments to change.
        :returns: The provider.
        """
        return ProviderConfig(**{
            "provider_id": "github",
            "driver_id": "github",
            **overrides,
        })

    def test_no_upload_draws_the_drivers_icon(self):
        assert self.provider().style()["icon"] == self.default

    def test_an_upload_is_drawn_instead(self):
        style = self.provider(icon=ICON).style()

        assert style["icon"] == sanitize(ICON)
        assert style["icon"] != self.default

    def test_the_default_is_never_stored(self):
        """Resolved on the way out, so the record, the control panel form and
        every export carry only what somebody uploaded."""
        provider = self.provider()
        provider.style()

        assert provider.icon == ""
        assert provider.serialize()["icon"] == ""

    def test_a_provider_whose_driver_is_gone_has_no_icon(self):
        provider = self.provider(provider_id="gone", driver_id="no-such-driver")

        assert provider.style()["icon"] == ""

    def test_the_login_listing_draws_it(self):
        """The wiring, not only the method: ``@login-providers`` renders each
        button through ``render_provider``."""
        entry = render_provider("http://nohost/plone/@login-providers", self.provider())

        assert entry["icon"] == self.default
