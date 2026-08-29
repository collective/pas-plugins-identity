"""``enabled`` and ``show_in_login`` are two questions, and the style fields.

The distinction under test: *availability* is whether a provider works at
all, and *visibility* is whether the login screen advertises it. Before they
were split, taking a provider off the login page also took it away from every
account already signed in through it.
"""

from . import GITHUB_PROVIDER
from pas.plugins.identity.core.controlpanel import enabled_providers
from pas.plugins.identity.core.controlpanel import get_provider
from pas.plugins.identity.core.controlpanel import get_provider_record
from pas.plugins.identity.core.controlpanel import InvalidColor
from pas.plugins.identity.core.controlpanel import login_providers
from pas.plugins.identity.core.controlpanel import normalize_color
from pas.plugins.identity.core.controlpanel import ProviderConfig
from pas.plugins.identity.core.controlpanel import set_providers
from pas.plugins.identity.core.utils.svg import InvalidSVG

import pytest


#: An enabled provider the operator has taken off the login screen.
HIDDEN_PROVIDER = {
    "id": "staff",
    "driver": "oidc-generic",
    "title": "Staff directory",
    "enabled": True,
    "show_in_login": False,
    "config": {"issuer": "https://staff.example", "client_id": "plone"},
}

#: A disabled provider, which is offered nowhere whatever else it says.
DISABLED_BUT_SHOWN = {
    "id": "retired",
    "driver": "oidc-generic",
    "title": "Retired",
    "enabled": False,
    "show_in_login": True,
    "config": {"issuer": "https://retired.example"},
}

#: A minimal but real SVG.
ICON = '<svg xmlns="http://www.w3.org/2000/svg"><path d="M0 0"/></svg>'


class TestVisibility:
    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal
        set_providers([
            ProviderConfig.deserialize(GITHUB_PROVIDER),
            ProviderConfig.deserialize(HIDDEN_PROVIDER),
            ProviderConfig.deserialize(DISABLED_BUT_SHOWN),
        ])

    def test_a_hidden_provider_is_still_available(self):
        """That is the whole reason the two settings are two settings."""
        assert [p.provider_id for p in enabled_providers()] == ["github", "staff"]

    def test_a_hidden_provider_is_not_offered_at_login(self):
        """The login screen draws no button for it."""
        assert [p.provider_id for p in login_providers()] == ["github"]

    def test_a_disabled_provider_is_offered_nowhere(self):
        """``show_in_login`` is only meaningful while the provider works."""
        assert "retired" not in [p.provider_id for p in enabled_providers()]
        assert "retired" not in [p.provider_id for p in login_providers()]

    def test_the_setting_round_trips_as_its_own_record(self):
        """A record, so a GenericSetup export carries it."""
        assert get_provider_record("staff", "show_in_login") is False
        assert get_provider_record("github", "show_in_login") is True

    def test_an_older_provider_is_shown(self):
        """Absent means shown. Every provider stored before this setting
        existed was on the login page, and reading the key back as False
        would take a site's login buttons away on upgrade."""
        provider = ProviderConfig.deserialize({
            "id": "old",
            "driver": "github",
            "enabled": True,
        })

        assert provider.show_in_login is True


class TestStyle:
    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal

    def test_the_style_round_trips(self):
        """Icon and colours are stored per provider."""
        set_providers([
            ProviderConfig.deserialize({
                **GITHUB_PROVIDER,
                "icon": ICON,
                "background_color": "#24292F",
                "foreground_color": "#FFF",
            })
        ])

        provider = get_provider("github")

        assert "<path" in provider.icon
        # Lowercased on the way in, so two spellings of one colour are one
        # value in the registry and in every export of it.
        assert provider.background_color == "#24292f"
        assert provider.foreground_color == "#fff"

    def test_a_colour_without_its_hash_is_accepted(self):
        """Operators type it both ways; only one of them is stored."""
        assert normalize_color("24292f") == "#24292f"

    def test_an_empty_colour_is_not_an_error(self):
        """Clearing a colour is an ordinary edit, and means 'use the
        frontend's own styling'."""
        assert normalize_color("") == ""

    def test_a_colour_that_is_not_hex_is_refused(self):
        """Anything looser would carry a CSS expression into the style
        attribute the frontend builds from this."""
        with pytest.raises(InvalidColor):
            normalize_color("red; background: url(//evil.example)")

    def test_the_icon_is_sanitized_on_the_way_in(self):
        """On assignment rather than on render: sanitizing on the way out
        would leave the dangerous version in the registry and in every
        export of it."""
        provider = ProviderConfig(
            provider_id="github",
            driver_id="github",
            icon=(
                '<svg xmlns="http://www.w3.org/2000/svg">'
                "<script>alert(1)</script>"
                "</svg>"
            ),
        )

        assert "script" not in provider.icon

    def test_an_icon_that_is_not_an_svg_is_refused(self):
        """Refused rather than silently emptied, so an operator finds out."""
        with pytest.raises(InvalidSVG):
            ProviderConfig(provider_id="x", driver_id="github", icon="<html/>")

    def test_style_carries_only_presentation(self):
        """It is served on a public login page, so it is a fixed three keys
        rather than a filtered view of the whole record."""
        provider = ProviderConfig.deserialize({
            **GITHUB_PROVIDER,
            "icon": ICON,
            "background_color": "#24292f",
        })

        assert set(provider.style()) == {
            "icon",
            "background_color",
            "foreground_color",
        }
