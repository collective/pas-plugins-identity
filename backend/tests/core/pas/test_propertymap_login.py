"""The provider's property map, applied through a real login."""

from . import CLAIMS
from . import DEX_IDENTITY
from pas.plugins.identity.core.controlpanel import ProviderConfig
from pas.plugins.identity.core.controlpanel import set_providers
from pas.plugins.identity.core.pas import EXTRACTOR
from plone import api

import pytest


PROVIDER, SUBJECT = DEX_IDENTITY

#: Claims carrying values Plone does not normalize, so the map is the only
#: way they can reach a user property.
RICH_CLAIMS = {
    **CLAIMS,
    "raw": {
        "login": "ericof",
        "profile": "https://example.org/~ericof",
        "address": {"formatted": "São Paulo"},
    },
}


def configure(propertymap: dict[str, str]) -> None:
    """Store the Dex provider with a property map.

    :param propertymap: Claim path to user field.
    """
    set_providers([
        ProviderConfig(
            provider_id=PROVIDER,
            driver_id="oidc-generic",
            title="Dex",
            propertymap=propertymap,
        )
    ])


class TestPropertyMapOnLogin:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, plugin) -> None:
        self.portal = portal
        self.plugin = plugin

    def authenticate(self, claims=RICH_CLAIMS) -> str:
        """Run a login and return the userid it resolved to.

        :param claims: Claims to authenticate with.
        :returns: The Plone userid.
        """
        userid, _ = self.plugin.authenticateCredentials({
            "extractor": EXTRACTOR,
            "provider": PROVIDER,
            "subject": SUBJECT,
            "claims": claims,
        })
        return userid

    def test_mapped_claim_reaches_the_user(self):
        """The whole point: a claim Plone does not know lands on a field."""
        configure({"profile": "home_page"})

        member = api.user.get(userid=self.authenticate())

        assert member.getProperty("home_page") == "https://example.org/~ericof"

    def test_dotted_path_reaches_the_user(self):
        configure({"address.formatted": "location"})

        member = api.user.get(userid=self.authenticate())

        assert member.getProperty("location") == "São Paulo"

    def test_no_map_writes_nothing_extra(self):
        """A provider without a map behaves exactly as before."""
        configure({})

        member = api.user.get(userid=self.authenticate())

        assert not member.getProperty("home_page")

    def test_applied_on_a_later_login_not_only_at_creation(self):
        """The user already exists; the map must still run."""
        configure({})
        userid = self.authenticate()
        assert not api.user.get(userid=userid).getProperty("home_page")

        configure({"profile": "home_page"})
        assert self.authenticate() == userid

        member = api.user.get(userid=userid)
        assert member.getProperty("home_page") == "https://example.org/~ericof"

    def test_local_edit_survives_the_next_login(self):
        """An edit made in Plone is not undone by the provider."""
        configure({"profile": "home_page"})
        userid = self.authenticate()

        api.user.get(userid=userid).setMemberProperties({
            "home_page": "https://erico.example/"
        })
        self.authenticate()

        member = api.user.get(userid=userid)
        assert member.getProperty("home_page") == "https://erico.example/"

    def test_missing_claim_does_not_blank_the_property(self):
        """A provider that stops sending a claim must not erase the value."""
        configure({"profile": "home_page"})
        userid = self.authenticate()
        assert api.user.get(userid=userid).getProperty("home_page")

        self.authenticate(claims={**CLAIMS, "raw": {}})

        member = api.user.get(userid=userid)
        assert member.getProperty("home_page") == "https://example.org/~ericof"

    def test_unconfigured_provider_is_survivable(self):
        """Authenticating against a provider with no record must not raise."""
        set_providers([])

        assert self.authenticate() is not None
