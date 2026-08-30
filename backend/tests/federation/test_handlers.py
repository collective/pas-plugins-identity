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

from ..conftest import DEMO_PROFILES
from . import SERVER_PROFILE_ID
from identitydemo import settings
from identitydemo.setuphandlers import DemoRefused
from identitydemo.setuphandlers import guard
from identitydemo.setuphandlers.idp import install_idp
from identitydemo.setuphandlers.rp import install_rp
from pas.plugins.identity.core.catalog import PROFILE_PORTAL_TYPE
from pas.plugins.identity.core.container import TYPE_RECORD as CONTAINER_TYPE_RECORD
from pas.plugins.identity.core.controlpanel import CALLBACK_URL_RECORD
from pas.plugins.identity.core.controlpanel import get_provider
from pas.plugins.identity.core.interfaces import ICredentialStorage
from pas.plugins.identity.core.subscribers import get_profile
from pas.plugins.identity.server.controlpanel.clients import get_client
from pas.plugins.identity.server.controlpanel.clients import get_clients
from pas.plugins.identity.server.grants.tokens import ISSUER_RECORD
from plone import api
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID

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
    def _setup(self, portal, monkeypatch, demo_registry):
        monkeypatch.setenv(settings.OPT_IN_ENV, "1")
        self.portal = portal
        self.setup_tool = portal.portal_setup
        # The handler runs after the profile's registry XML, which is where
        # the demo client and every server setting now live.
        demo_registry("idp")

    def test_creates_the_demo_user(self):
        """Through ``api.user.create``, the seat every user goes through.

        They were a ``principals.json`` payload, and the principals importer
        creates users the way Plone always has -- which on the provider meant
        a ``source_users`` row in the site whose point is that a user is a
        content object.
        """
        install_idp(self.setup_tool)

        user = api.user.get(userid=settings.DEMO_USER_ID)

        assert user is not None
        assert user.getProperty("email") == settings.DEMO_USER_EMAIL
        assert user.getProperty("fullname") == settings.DEMO_USER_FULLNAME

    def test_the_demo_user_can_sign_in(self):
        """The password is what the documentation tells a reader to type, so
        it has to be stored as a password rather than as a property."""
        install_idp(self.setup_tool)

        assert self.portal.acl_users.authenticate(
            settings.DEMO_USER_ID, settings.DEMO_USER_PASSWORD, self.portal.REQUEST
        )

    def test_needs_no_opt_in(self):
        """The guard protects the relying party profile, which registers a
        published client secret. A demo user whose password is in the same
        public repository is not protected by refusing to create them."""
        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.delenv(settings.OPT_IN_ENV, raising=False)
        try:
            install_idp(self.setup_tool)
        finally:
            monkeypatch.undo()

        assert api.user.get(userid=settings.DEMO_USER_ID) is not None

    def test_the_issuer_is_written_from_the_environment(self):
        """It is not in the registry XML, and must not be: the two demo
        stacks disagree on it and the issuer is compared as a string."""
        install_idp(self.setup_tool)

        assert api.portal.get_registry_record(ISSUER_RECORD) == settings.IDP_PUBLIC_URL

    def test_the_client_redirect_uri_is_written_from_the_environment(self):
        """The XML states one, but it is the manual stack's. The hermetic
        stack reaches the relying party on another port and another path, and
        the redirect URI is compared byte for byte at the token endpoint."""
        install_idp(self.setup_tool)

        client = get_client(settings.DEMO_CLIENT_ID)

        assert client.redirect_uris == [settings.DEMO_REDIRECT_URI]

    def test_is_idempotent(self):
        """Re-applying the profile against a warm volume must not mint a
        second client or raise on the user that already exists."""
        install_idp(self.setup_tool)
        install_idp(self.setup_tool)

        assert len(get_clients()) == 1
        assert api.user.get(userid=settings.DEMO_USER_ID) is not None


@pytest.mark.portal(profiles=[SERVER_PROFILE_ID])
class TestTheDemoUserIsContent:
    """What the provider profile is *for*: a user who is a content object.

    The demo user used to be imported as principals, which put them in
    ``source_users`` -- in the one site whose whole point is that a site does
    not need that store. This asserts the end state the profile aims at, on
    the layers the profile depends on.

    The password behavior is enabled here by hand, because the demo's own
    ``types/UserProfile.xml`` cannot be applied to this site -- see the
    ``demo_registry`` fixture for why the same compromise is made for the
    registry. :meth:`test_the_demo_profile_enables_the_behavior` is what keeps
    the hand-written half honest.
    """

    BEHAVIOR = "pas.plugins.identity.password"

    @pytest.fixture(autouse=True)
    def _setup(self, portal, monkeypatch, demo_registry):
        monkeypatch.setenv(settings.OPT_IN_ENV, "1")
        self.portal = portal
        self.setup_tool = portal.portal_setup
        setRoles(portal, TEST_USER_ID, ["Manager"])
        demo_registry("idp")
        # The demo keeps its Profiles in a Document, which is a container
        # only because the demo runs plone.volto. This site does not, so the
        # container type is the one detail of that registry this test has to
        # disagree with -- what is under test is where the *user* lands.
        api.portal.set_registry_record(CONTAINER_TYPE_RECORD, "Folder")
        fti = portal.portal_types[PROFILE_PORTAL_TYPE]
        fti.behaviors = (*fti.behaviors, self.BEHAVIOR)
        install_idp(self.setup_tool)

    def test_the_demo_user_has_a_profile(self):
        assert get_profile(settings.DEMO_USER_ID) is not None

    def test_the_demo_user_is_not_in_source_users(self):
        """The row that turned up in the ZMI beside every demo user.

        ``getUserIds`` rather than ``getUserById``: that manager answers for
        a principal it does not hold, so it cannot show an absence.
        """
        assert (
            settings.DEMO_USER_ID not in self.portal.acl_users.source_users.getUserIds()
        )

    def test_the_password_is_on_the_profile(self):
        profile = get_profile(settings.DEMO_USER_ID)

        assert ICredentialStorage(profile).check_password(settings.DEMO_USER_PASSWORD)

    def test_they_can_still_sign_in(self):
        """All of the above is only worth having if the credential still
        works from the login form."""
        assert self.portal.acl_users.authenticate(
            settings.DEMO_USER_ID, settings.DEMO_USER_PASSWORD, self.portal.REQUEST
        )

    def test_the_demo_profile_enables_the_behavior(self):
        """The half this test site cannot apply. Without it the demo would
        keep its passwords in ``source_users`` and nothing here would say
        so."""
        xml = (DEMO_PROFILES / "idp/types/UserProfile.xml").read_text()

        assert self.BEHAVIOR in xml


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
        """With the peer driver, not the generic one.

        A Plone site federating against another Plone site is what
        ``plone-identity`` exists for, so the demo has to be the thing it
        claims to demonstrate. The driver subclasses the generic OIDC one and
        takes no special path through the flow; what it carries is the
        configuration a peer can be known in advance to want.
        """
        install_rp(self.setup_tool)

        provider = get_provider(settings.DEMO_PROVIDER_ID)

        assert provider is not None
        assert provider.driver_id == "plone-identity"

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


class TestSettingsReachTheSite:
    """The issuer and the callback URL used to be stated twice -- once in
    ``identitydemo.settings`` for the Python handlers, once in profile XML for
    GenericSetup -- with nothing making them agree. They are now written by
    the handlers from the one value, because the URLs come from the
    environment and XML cannot read one. These assert they arrive."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, monkeypatch):
        monkeypatch.setenv(settings.OPT_IN_ENV, "1")
        self.portal = portal
        self.setup_tool = portal.portal_setup

    def test_the_callback_url_is_configured_from_the_settings(self):
        """The relying party's ``callback_url``, the redirect URI registered
        with the provider and this constant are compared byte for byte at the
        token endpoint. One value, written twice into two sites."""
        install_rp(self.setup_tool)

        assert (
            api.portal.get_registry_record(CALLBACK_URL_RECORD)
            == settings.DEMO_REDIRECT_URI
        )


class TestDeploymentURLs:
    """Two demo deployments, one package. The hermetic stack publishes ports
    and serves Plone at ``/Plone``; the manual stack puts Traefik in front and
    serves each site at the root of its own host."""

    def test_a_trailing_slash_is_stripped(self):
        """An issuer is compared as a string and never parsed, so a trailing
        slash from a copy-pasted environment variable is a login that fails
        with nothing useful to say."""
        assert settings._url("UNSET_IN_TESTS", "http://example.org/site/") == (
            "http://example.org/site"
        )

    def test_the_environment_wins_over_the_default(self, monkeypatch):
        monkeypatch.setenv("DEMO_PROBE_URL", "http://id.localhost")

        assert settings._url("DEMO_PROBE_URL", "http://unused") == (
            "http://id.localhost"
        )

    def test_an_empty_variable_falls_back_to_the_default(self, monkeypatch):
        """Compose writes an empty value for a variable it has no setting
        for, and an empty issuer is a site that serves 503 for reasons nobody
        would guess from the compose file."""
        monkeypatch.setenv("DEMO_PROBE_URL", "")

        assert settings._url("DEMO_PROBE_URL", "http://fallback") == ("http://fallback")
