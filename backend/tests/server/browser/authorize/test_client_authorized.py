"""The event fired when a user authorizes a client.

What an integration needs from it is that it fires for exactly the
authorizations that happened: once per issued code, whichever path led there,
and never for a request that stopped short of one. Both halves are asserted,
because a fire moved one step earlier in the view would still pass every test
of the first half.
"""

from ... import PROFILE_ID
from ... import REDIRECT
from ... import SERVICE_USER
from AccessControl import Unauthorized
from pas.plugins.identity import api as identity_api
from pas.plugins.identity.core import audit
from pas.plugins.identity.server.browser import authorize
from pas.plugins.identity.server.browser.authorize import AuthorizeView
from pas.plugins.identity.server.browser.token import TokenView
from pas.plugins.identity.server.events import ClientAuthorized
from pas.plugins.identity.server.events import IClientAuthorized
from pas.plugins.identity.server.pas import PLUGIN_ID
from plone import api
from plone.app.testing import logout
from plone.protect.authenticator import createToken
from urllib.parse import parse_qs
from urllib.parse import urlparse
from zope.component import adapter
from zope.component import getGlobalSiteManager

import pytest


pytestmark = pytest.mark.portal(profiles=[PROFILE_ID])


@pytest.fixture
def fired():
    """Record every :class:`IClientAuthorized` fired during a test.

    :returns: The list the recorder appends to.
    """
    events = []

    @adapter(IClientAuthorized)
    def recorder(event):
        events.append(event)

    gsm = getGlobalSiteManager()
    gsm.registerHandler(recorder)
    yield events
    gsm.unregisterHandler(recorder)


@pytest.fixture
def client(portal, add_client):
    """Register a confidential client that may use the code grant."""
    client, _secret = add_client(
        "app",
        redirect_uris=[REDIRECT],
        grant_types=["authorization_code"],
        scope="read write",
        public=False,
    )
    return client


def call(portal, **params):
    """Drive the authorization endpoint and return the Location header.

    :param portal: The Plone site.
    :param params: Query parameters, on top of a valid request for ``app``.
    :returns: The Location header, or ``None`` when nothing redirected.
    """
    request = portal.REQUEST
    request.form.clear()
    request.form.update({
        "response_type": "code",
        "client_id": "app",
        "redirect_uri": REDIRECT,
        "scope": "read",
        **params,
    })
    AuthorizeView(portal, request)()
    return request.response.getHeader("Location")


def query(location: str) -> dict:
    """Return the query parameters of a redirect target.

    :param location: The Location header.
    :returns: Flattened query parameters.
    """
    return {k: v[0] for k, v in parse_qs(urlparse(location).query).items()}


class TestItFires:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, client, fired) -> None:
        self.portal = portal
        self.fired = fired
        self.userid = api.user.get_current().getId()
        self.consent = portal.acl_users[PLUGIN_ID].consent

    def test_once_for_an_issued_code(self):
        self.consent.record(self.userid, "app", "read")

        location = call(self.portal)

        assert query(location)["code"]
        assert len(self.fired) == 1

    def test_it_carries_the_user_the_client_and_the_scope(self):
        self.consent.record(self.userid, "app", "read write")

        call(self.portal, scope="read write")

        event = self.fired[0]
        assert event.userid == self.userid
        assert event.client_id == "app"
        assert event.scope == "read write"

    def test_for_a_silent_sign_in(self):
        """``prompt=none`` with consent on record is the sign-in an
        integration is most likely to miss: nobody saw a screen."""
        self.consent.record(self.userid, "app", "read")

        location = call(self.portal, prompt="none")

        assert query(location)["code"]
        assert len(self.fired) == 1

    def test_when_consent_is_given_now(self):
        call(self.portal, consent="allow", _authenticator=createToken())

        assert len(self.fired) == 1

    def test_on_every_sign_in_not_only_the_first(self):
        """Which is why the docstring tells subscribers to write only on a
        change."""
        self.consent.record(self.userid, "app", "read")

        call(self.portal)
        call(self.portal)

        assert len(self.fired) == 2

    def test_it_is_an_identity_event(self):
        """A subscriber to every identity event hears this one too."""
        self.consent.record(self.userid, "app", "read")

        call(self.portal)

        assert identity_api.IIdentityEvent.providedBy(self.fired[0])


class TestItDoesNotFire:
    """Every way the flow stops before a code exists."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, client, fired) -> None:
        self.portal = portal
        self.fired = fired
        self.userid = api.user.get_current().getId()

    def test_while_consent_is_pending(self):
        call(self.portal)

        assert self.fired == []

    def test_when_consent_is_refused(self):
        location = call(self.portal, consent="deny", _authenticator=createToken())

        assert query(location)["error"] == "access_denied"
        assert self.fired == []

    def test_when_the_user_must_sign_in(self):
        logout()

        with pytest.raises(Unauthorized):
            call(self.portal)

        assert self.fired == []

    def test_when_prompt_none_finds_no_session(self):
        logout()

        location = call(self.portal, prompt="none")

        assert query(location)["error"] == "login_required"
        assert self.fired == []

    def test_while_the_profile_is_incomplete(self, monkeypatch):
        """The gate's own tests decide *when* a profile is incomplete; this
        one only holds that a paused request announces nothing."""
        monkeypatch.setattr(
            authorize, "incomplete_profile_url", lambda userid: "http://nohost/p"
        )
        self.portal.acl_users[PLUGIN_ID].consent.record(self.userid, "app", "read")

        location = call(self.portal)

        assert authorize.RESUME_PARAM in query(location)
        assert self.fired == []

    def test_for_a_refused_request(self):
        location = call(self.portal, scope="admin")

        assert query(location)["error"] == "invalid_scope"
        assert self.fired == []


class TestTheAuditLog:
    """Recorded through the subscriber the ``[server]`` ZCML registers.

    Read back from the log rather than asserted on the subscriber, because a
    subscriber nothing registers passes every test that calls it directly.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, portal, client) -> None:
        self.portal = portal
        self.userid = api.user.get_current().getId()
        self.consent = portal.acl_users[PLUGIN_ID].consent

    def recorded(self) -> list:
        """Return this user's ``client-authorized`` entries.

        :returns: The entries, newest first.
        """
        return [
            entry
            for entry in audit.entries(self.userid)
            if entry.event == audit.CLIENT_AUTHORIZED
        ]

    def test_an_issued_code_is_recorded(self):
        self.consent.record(self.userid, "app", "read write")

        call(self.portal, scope="read write")

        [entry] = self.recorded()
        assert entry.success is True
        assert entry.provider == "app"
        assert entry.detail["client_id"] == "app"
        assert entry.detail["scope"] == "read write"

    def test_the_code_is_not_recorded(self):
        """The audit log never holds a credential, and a code is one until it
        is redeemed."""
        self.consent.record(self.userid, "app", "read")

        location = call(self.portal)

        code = query(location)["code"]
        [entry] = self.recorded()
        assert code not in repr(entry.serialize())

    def test_a_request_that_stops_short_records_nothing(self):
        call(self.portal)

        assert self.recorded() == []


class TestClientCredentials:
    """A service acting as itself authorizes nothing on anybody's behalf."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, issuer, add_client, fired) -> None:
        self.portal = portal
        self.fired = fired
        with api.env.adopt_roles(["Manager"]):
            api.user.create(
                email="svc@example.org",
                username=SERVICE_USER,
                password="not-used-by-this-grant",
            )
        _client, self.secret = add_client(
            "indexer",
            grant_types=["client_credentials"],
            scope="read",
            public=False,
            service_user=SERVICE_USER,
        )

    def test_it_does_not_fire(self):
        request = self.portal.REQUEST
        request.form.clear()
        request.form.update({
            "grant_type": "client_credentials",
            "client_id": "indexer",
            "client_secret": self.secret,
        })
        request.environ["REQUEST_METHOD"] = "POST"
        TokenView(self.portal, request)()

        assert request.response.getStatus() == 200
        assert self.fired == []


class TestTheFacade:
    def test_the_event_is_the_one_fired(self):
        """A subscriber registered through the façade must see the event the
        view actually fires."""
        assert identity_api.IClientAuthorized is IClientAuthorized
        assert identity_api.ClientAuthorized is ClientAuthorized
