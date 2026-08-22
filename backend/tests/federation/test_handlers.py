"""What the demo profiles' post handlers do to a site.

These run in process, on the ordinary integration site, and call the handlers
directly. They deliberately do *not* apply ``identitydemo:idp`` or
``identitydemo:rp`` through GenericSetup: registering a second
``PloneSandboxLayer`` to get the demo's ZCML loaded would leave two layers
sharing one site for the whole session, and the failure that causes surfaces
in an unrelated suite.

The profile wiring — metadata dependencies, the ZCML, the post-handler
binding — is therefore not covered here. It is exercised by bringing the
compose stack in ``docker-compose.yml`` up, which is currently a manual step:
the automated end-to-end flow test is blocked on the token-endpoint
authentication mismatch that bringing it up for the first time uncovered.
"""

from . import SERVER_PROFILE_ID
from identitydemo import settings
from identitydemo.setuphandlers import DemoRefused
from identitydemo.setuphandlers import guard
from identitydemo.setuphandlers import install_idp
from identitydemo.setuphandlers import install_rp
from pas.plugins.identity.core.controlpanel import get_provider
from pas.plugins.identity.server.clients import get_client
from pas.plugins.identity.server.clients import get_clients
from pas.plugins.identity.server.clients import verify_secret
from pathlib import Path
from plone import api
from xml.etree import ElementTree

import identitydemo
import pytest


class TestGuard:
    def test_refuses_without_the_opt_in(self, monkeypatch):
        """The only thing standing between a curious click in
        ``portal_setup`` and a site holding a published client secret."""
        monkeypatch.delenv(settings.OPT_IN_ENV, raising=False)

        with pytest.raises(DemoRefused):
            guard()

    def test_refuses_when_the_opt_in_is_empty(self, monkeypatch):
        """``IDENTITY_DEMO=`` is how a compose file switches the demo off
        without deleting the line, so an empty value must not count."""
        monkeypatch.setenv(settings.OPT_IN_ENV, "")

        with pytest.raises(DemoRefused):
            guard()

    def test_says_why_it_stopped(self, monkeypatch):
        """A profile that appears to install and silently does nothing is
        worse to debug than one that refuses out loud."""
        monkeypatch.delenv(settings.OPT_IN_ENV, raising=False)

        with pytest.raises(DemoRefused, match=settings.OPT_IN_ENV):
            guard()


@pytest.mark.portal(profiles=[SERVER_PROFILE_ID])
class TestInstallIdP:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, monkeypatch):
        monkeypatch.setenv(settings.OPT_IN_ENV, "1")
        self.portal = portal
        self.setup_tool = portal.portal_setup

    def test_refuses_without_the_opt_in(self, monkeypatch):
        """The guard is on the handler, not only on a caller of it."""
        monkeypatch.delenv(settings.OPT_IN_ENV, raising=False)

        with pytest.raises(DemoRefused):
            install_idp(self.setup_tool)

        assert get_client(settings.DEMO_CLIENT_ID) is None

    def test_registers_the_demo_client(self):
        install_idp(self.setup_tool)

        client = get_client(settings.DEMO_CLIENT_ID)

        assert client is not None
        assert client.title == settings.DEMO_CLIENT_TITLE

    def test_the_registered_secret_is_the_documented_one(self):
        """The whole reason the handler builds a ``ClientConfig`` by hand
        instead of calling ``add_client``: the relying party is installed in
        another container and can only be handed a literal."""
        install_idp(self.setup_tool)

        client = get_client(settings.DEMO_CLIENT_ID)

        assert verify_secret(settings.DEMO_CLIENT_SECRET, client.secret_hash)

    def test_the_secret_is_not_stored_in_the_clear(self):
        """Stated because the secret being a known literal makes it easy to
        stop caring how it is stored."""
        install_idp(self.setup_tool)

        client = get_client(settings.DEMO_CLIENT_ID)

        assert settings.DEMO_CLIENT_SECRET not in client.secret_hash

    def test_the_redirect_uri_points_at_the_relying_party(self):
        install_idp(self.setup_tool)

        client = get_client(settings.DEMO_CLIENT_ID)

        assert client.redirect_uris == [settings.DEMO_REDIRECT_URI]

    def test_creates_the_demo_user(self):
        install_idp(self.setup_tool)

        user = api.user.get(userid=settings.DEMO_USER_ID)

        assert user is not None
        assert user.getProperty("email") == settings.DEMO_USER_EMAIL

    def test_is_idempotent(self):
        """Re-applying the profile against a warm volume must not mint a
        second client or raise on the user that already exists."""
        install_idp(self.setup_tool)
        install_idp(self.setup_tool)

        assert len(get_clients()) == 1
        assert api.user.get(userid=settings.DEMO_USER_ID) is not None


class TestInstallRP:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, monkeypatch):
        monkeypatch.setenv(settings.OPT_IN_ENV, "1")
        self.portal = portal
        self.setup_tool = portal.portal_setup

    def test_refuses_without_the_opt_in(self, monkeypatch):
        monkeypatch.delenv(settings.OPT_IN_ENV, raising=False)

        with pytest.raises(DemoRefused):
            install_rp(self.setup_tool)

        assert get_provider(settings.DEMO_PROVIDER_ID) is None

    def test_registers_the_provider(self):
        install_rp(self.setup_tool)

        provider = get_provider(settings.DEMO_PROVIDER_ID)

        assert provider is not None
        assert provider.driver_id == "oidc-generic"

    def test_the_issuer_is_the_public_url(self):
        """Not the compose service name. Discovery publishes one issuer and
        the browser is redirected to it, so a server-to-server convenience
        name here would break the half of the flow that runs in the user
        agent."""
        install_rp(self.setup_tool)

        provider = get_provider(settings.DEMO_PROVIDER_ID)

        assert provider.config["issuer"] == settings.IDP_PUBLIC_URL

    def test_carries_the_credentials_the_provider_registered(self):
        """The two halves of the demo agree by both reading ``settings``.
        This is the assertion that fails if one of them is edited alone."""
        install_rp(self.setup_tool)

        provider = get_provider(settings.DEMO_PROVIDER_ID)

        assert provider.config["client_id"] == settings.DEMO_CLIENT_ID
        assert provider.config["client_secret"] == settings.DEMO_CLIENT_SECRET

    def test_is_idempotent(self):
        install_rp(self.setup_tool)
        install_rp(self.setup_tool)

        assert get_provider(settings.DEMO_PROVIDER_ID) is not None


class TestSettingsMatchTheProfileXML:
    """The issuer and the container type are stated twice: once in
    ``identitydemo.settings``, which the Python handlers read, and once in the
    ``idp`` profile's registry XML, which GenericSetup reads. Nothing makes
    them agree, so these assert it. A drift here is a demo that comes up,
    serves discovery, and fails the flow with a mismatched ``iss``."""

    @staticmethod
    def _registry_value(profile: str, filename: str, key: str) -> str:
        path = (
            Path(identitydemo.__file__).parent
            / "profiles"
            / profile
            / "registry"
            / filename
        )
        # S314: the file being parsed is this package's own profile XML,
        # two directories away, and is in the same commit as this test.
        tree = ElementTree.parse(path)  # noqa: S314
        for value in tree.getroot().iter("value"):
            if value.get("key") == key:
                return (value.text or "").strip()
        raise AssertionError(f"{key} is not set in {filename}")

    def test_the_issuer_matches(self):
        issuer = self._registry_value(
            "idp",
            "pas.plugins.identity.server.interfaces.IServerSettings.xml",
            "server_issuer",
        )

        assert issuer == settings.IDP_PUBLIC_URL

    def test_the_callback_url_matches(self):
        """The relying party's ``callback_url``, the redirect URI registered
        with the identity provider and this constant are compared byte for
        byte at the token endpoint. Two of the three are set from Python and
        the third from XML."""
        callback = self._registry_value(
            "rp",
            "pas.plugins.identity.core.controlpanel.interfaces.IIdentitySettings.xml",
            "callback_url",
        )

        assert callback == settings.DEMO_REDIRECT_URI

    def test_a_missing_key_is_an_error_rather_than_a_pass(self):
        """The helper above returns the value it finds. Were a lookup for an
        absent key to return the empty string, a drift test would compare it
        to a constant, fail, and be "fixed" by someone reading the comparison
        rather than the lookup. It raises instead."""
        with pytest.raises(AssertionError, match="server_issuer_typo"):
            self._registry_value(
                "idp",
                "pas.plugins.identity.server.interfaces.IServerSettings.xml",
                "server_issuer_typo",
            )
