"""The client-credentials grant.

The opposite discipline to the authorization code grant, which is why these
live in their own module. There every refusal is the same sentence, because
the caller may be guessing. Here the caller has already proved it holds the
client secret before any of these checks run, so naming the failure tells it
nothing it could not have found out anyway -- and every one of these failures
is a registration mistake somebody has to be able to read.
"""

from . import PROFILE_ID
from . import SERVICE_USER
from pas.plugins.identity.server.browser.token import TokenView
from pas.plugins.identity.server.controlpanel.clients import get_clients
from pas.plugins.identity.server.controlpanel.clients import set_clients
from pas.plugins.identity.server.grants.tokens import decode_access_token
from plone import api

import json
import pytest


pytestmark = pytest.mark.portal(profiles=[PROFILE_ID])


def post(portal, **params):
    """Drive the token view as a POST and return ``(status, body)``.

    :param portal: The Plone site.
    :param params: Form parameters.
    :returns: Status code and decoded JSON body.
    """
    request = portal.REQUEST
    request.form.clear()
    request.form.update(params)
    request.environ["REQUEST_METHOD"] = "POST"
    body = TokenView(portal, request)()
    return request.response.getStatus(), json.loads(body)


@pytest.fixture
def service_user(portal):
    """A real Plone user for the client to act as.

    Elevated, unlike everything else in this package's server tests: creating
    a user is the one thing here that needs a role, and the ``portal`` marker
    applies profiles without granting one.
    """
    with api.env.adopt_roles(["Manager"]):
        return api.user.create(
            email="svc@example.org",
            username=SERVICE_USER,
            password="not-used-by-this-grant",
        )


@pytest.fixture
def service_client(portal, issuer, service_user, add_client):
    """A confidential client registered for the grant, with a service user."""
    client, secret = add_client(
        "indexer",
        grant_types=["client_credentials"],
        scope="read write",
        public=False,
        service_user=SERVICE_USER,
    )
    return client, secret


class TestTheGrant:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, service_client) -> None:
        self.portal = portal
        self.client, self.secret = service_client

    def test_it_issues_a_token(self):
        status, body = post(
            self.portal,
            grant_type="client_credentials",
            client_id="indexer",
            client_secret=self.secret,
        )

        assert status == 200
        assert body["token_type"] == "Bearer"

    def test_the_subject_is_the_service_user(self):
        """The whole point of nominating one: a token whose `sub` named the
        client would authenticate a principal no roles plugin has heard of."""
        _status, body = post(
            self.portal,
            grant_type="client_credentials",
            client_id="indexer",
            client_secret=self.secret,
        )

        assert decode_access_token(body["access_token"])["sub"] == SERVICE_USER

    def test_the_audience_is_still_the_client(self):
        """The subject moved to the service user; the audience did not. A
        token minted for one client must not be replayable at a resource
        server that trusts another."""
        _status, body = post(
            self.portal,
            grant_type="client_credentials",
            client_id="indexer",
            client_secret=self.secret,
        )

        assert decode_access_token(body["access_token"])["aud"] == "indexer"

    def test_omitting_the_scope_grants_the_registered_one(self):
        """There is no user to narrow it, so the registration is the whole
        of the client's authority and asking for nothing means asking for
        that."""
        _status, body = post(
            self.portal,
            grant_type="client_credentials",
            client_id="indexer",
            client_secret=self.secret,
        )

        assert body["scope"] == "read write"

    def test_a_narrower_scope_is_honoured(self):
        _status, body = post(
            self.portal,
            grant_type="client_credentials",
            client_id="indexer",
            client_secret=self.secret,
            scope="read",
        )

        assert body["scope"] == "read"

    def test_a_scope_it_does_not_have_is_refused(self):
        status, body = post(
            self.portal,
            grant_type="client_credentials",
            client_id="indexer",
            client_secret=self.secret,
            scope="read delete",
        )

        assert status == 400
        assert body["error"] == "invalid_scope"
        assert "delete" in body["error_description"]

    def test_no_code_is_written(self):
        """This grant has no code to burn, and the write frequency it avoids
        is the reason C7 says tokens are self-encoded."""
        codes = self.portal.acl_users["identity_server"].codes

        post(
            self.portal,
            grant_type="client_credentials",
            client_id="indexer",
            client_secret=self.secret,
        )

        assert codes.count() == 0


class TestClientAuthentication:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, service_client, add_client) -> None:
        self.portal = portal
        self.client, self.secret = service_client
        self.add_client = add_client

    def test_a_public_client_cannot_use_this_grant(self):
        """RFC 6749 §4.4 requires client authentication outright. The code
        grant lets a public client through on its id alone because PKCE does
        the proving; there is no second factor here at all."""
        self.add_client("spa", grant_types=["client_credentials"], public=True)

        status, body = post(
            self.portal,
            grant_type="client_credentials",
            client_id="spa",
        )

        assert status == 401
        assert body["error"] == "invalid_client"

    def test_the_wrong_secret_is_refused(self):
        status, body = post(
            self.portal,
            grant_type="client_credentials",
            client_id="indexer",
            client_secret="wrong",
        )

        assert status == 401
        assert body["error"] == "invalid_client"

    def test_a_disabled_client_is_refused(self):
        clients = get_clients()
        for client in clients:
            client.enabled = False
        set_clients(clients)

        status, body = post(
            self.portal,
            grant_type="client_credentials",
            client_id="indexer",
            client_secret=self.secret,
        )

        assert status == 401
        assert body["error"] == "invalid_client"


class TestRegistrationMistakes:
    """Everything an operator can get wrong, said plainly."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, issuer, service_user, add_client) -> None:
        self.portal = portal
        self.add_client = add_client

    def test_a_client_not_registered_for_the_grant(self):
        _client, secret = self.add_client(
            "web",
            grant_types=["authorization_code"],
            service_user=SERVICE_USER,
        )

        status, body = post(
            self.portal,
            grant_type="client_credentials",
            client_id="web",
            client_secret=secret,
        )

        assert status == 400
        assert body["error"] == "unauthorized_client"

    def test_a_client_with_no_service_user(self):
        _client, secret = self.add_client(
            "orphan",
            grant_types=["client_credentials"],
        )

        status, body = post(
            self.portal,
            grant_type="client_credentials",
            client_id="orphan",
            client_secret=secret,
        )

        assert status == 400
        assert body["error"] == "invalid_client"
        assert "service user" in body["error_description"]

    def test_a_service_user_that_does_not_exist(self):
        """Registered against a userid nobody ever created, or one deleted
        since. Either way the token would act as nobody."""
        _client, secret = self.add_client(
            "ghost",
            grant_types=["client_credentials"],
            service_user="never-created",
        )

        status, body = post(
            self.portal,
            grant_type="client_credentials",
            client_id="ghost",
            client_secret=secret,
        )

        assert status == 400
        assert body["error"] == "invalid_client"
        assert "never-created" in body["error_description"]


class TestTheGrantList:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, service_client) -> None:
        self.portal = portal

    def test_an_unsupported_grant_names_the_supported_ones(self):
        """Both of them, so a client integrator can see what changed when a
        grant is added rather than reading the source."""
        status, body = post(self.portal, grant_type="password", client_id="indexer")

        assert status == 400
        assert body["error"] == "unsupported_grant_type"
        assert "authorization_code" in body["error_description"]
        assert "client_credentials" in body["error_description"]
