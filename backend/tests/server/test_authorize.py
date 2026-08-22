"""The authorization endpoint.

The split that matters is where an error goes. A request that has not
established a trustworthy redirect URI is refused *here*; everything else is
reported to the client at its registered URI. Getting that backwards is an
open redirect, so it is asserted in both directions.
"""

from . import PROFILE_ID
from pas.plugins.identity.server.browser.authorize import AuthorizeView
from pas.plugins.identity.server.codes import make_verifier
from pas.plugins.identity.server.pas import PLUGIN_ID
from plone import api
from plone.app.testing import logout
from urllib.parse import parse_qs
from urllib.parse import urlparse

import pytest


pytestmark = pytest.mark.portal(profiles=[PROFILE_ID])

REDIRECT = "https://app.example.org/cb"


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


@pytest.fixture
def public_client(portal, add_client):
    """Register a public client, for which PKCE is mandatory."""
    client, _secret = add_client(
        "spa",
        redirect_uris=[REDIRECT],
        grant_types=["authorization_code"],
        public=True,
    )
    return client


@pytest.fixture
def consented(portal):
    """Return a helper pre-recording the current user's consent.

    The tests that use it are about issuing a code, and the consent screen
    would otherwise stand between every one of them and the thing they
    assert. Consent itself is tested in ``test_consent.py``.

    :param portal: The Plone site.
    :returns: Callable taking a client id and scope.
    """

    def record(client_id: str, scope: str = "") -> None:
        """Record consent for the current user.

        :param client_id: The client agreed to.
        :param scope: The scopes agreed to.
        """
        plugin = portal.acl_users[PLUGIN_ID]
        plugin.consent.record(api.user.get_current().getId(), client_id, scope)

    return record


def call(portal, **params):
    """Drive the view and return ``(status, location, body)``.

    :param portal: The Plone site.
    :param params: Query parameters for the authorization request.
    :returns: Status, Location header, and body.
    """
    request = portal.REQUEST
    request.form.clear()
    request.form.update(params)
    body = AuthorizeView(portal, request)()
    return (
        request.response.getStatus(),
        request.response.getHeader("Location"),
        body,
    )


def query(location: str) -> dict:
    """Return the query parameters of a redirect target.

    :param location: The Location header.
    :returns: Flattened query parameters.
    """
    return {k: v[0] for k, v in parse_qs(urlparse(location).query).items()}


class TestRefusedWithoutRedirecting:
    """Failures that must never be sent to the redirect URI."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, client) -> None:
        self.portal = portal

    def test_an_unknown_client_is_refused_in_place(self):
        status, location, _body = call(
            self.portal,
            response_type="code",
            client_id="nobody",
            redirect_uri=REDIRECT,
        )

        assert status == 400
        assert location is None

    def test_an_unregistered_redirect_uri_is_refused_in_place(self):
        """The whole point: this is the open-redirect boundary."""
        status, location, _body = call(
            self.portal,
            response_type="code",
            client_id="app",
            redirect_uri="https://evil.example.org/cb",
        )

        assert status == 400
        assert location is None

    def test_a_near_miss_redirect_uri_is_still_refused(self):
        """Exact matching, asserted through the endpoint and not only at the
        registry."""
        status, location, _body = call(
            self.portal,
            response_type="code",
            client_id="app",
            redirect_uri=f"{REDIRECT}/",
        )

        assert status == 400
        assert location is None

    def test_a_disabled_client_is_refused(self):
        from pas.plugins.identity.server.clients import get_clients
        from pas.plugins.identity.server.clients import set_clients

        clients = get_clients()
        clients[0].enabled = False
        set_clients(clients)

        status, _location, _body = call(
            self.portal,
            response_type="code",
            client_id="app",
            redirect_uri=REDIRECT,
        )

        assert status == 400

    def test_the_error_page_escapes_what_the_caller_sent(self):
        """The client id lands in HTML and is attacker-controlled precisely
        when this page renders."""
        _status, _location, body = call(
            self.portal,
            response_type="code",
            client_id="<script>alert(1)</script>",
            redirect_uri=REDIRECT,
        )

        assert "<script>" not in body
        assert "&lt;script&gt;" in body


class TestReportedToTheClient:
    """Failures that belong at the redirect URI."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, client) -> None:
        self.portal = portal

    def test_an_unsupported_response_type_redirects_an_error(self):
        _status, location, _body = call(
            self.portal,
            response_type="token",
            client_id="app",
            redirect_uri=REDIRECT,
        )

        assert location.startswith(REDIRECT)
        assert query(location)["error"] == "unsupported_response_type"

    def test_an_unregistered_scope_is_refused(self):
        _status, location, _body = call(
            self.portal,
            response_type="code",
            client_id="app",
            redirect_uri=REDIRECT,
            scope="read admin",
        )

        assert query(location)["error"] == "invalid_scope"

    def test_a_grant_the_client_may_not_use_is_refused(self):
        from pas.plugins.identity.server.clients import get_clients
        from pas.plugins.identity.server.clients import set_clients

        clients = get_clients()
        clients[0].grant_types = ["client_credentials"]
        set_clients(clients)

        _status, location, _body = call(
            self.portal,
            response_type="code",
            client_id="app",
            redirect_uri=REDIRECT,
        )

        assert query(location)["error"] == "unauthorized_client"

    def test_state_comes_back_on_an_error(self):
        """It is the client's CSRF token; it has to survive the failure path
        as well as the success one."""
        _status, location, _body = call(
            self.portal,
            response_type="token",
            client_id="app",
            redirect_uri=REDIRECT,
            state="xyzzy",
        )

        assert query(location)["state"] == "xyzzy"

    def test_an_anonymous_end_user_is_reported_as_login_required(self):
        logout()

        _status, location, _body = call(
            self.portal,
            response_type="code",
            client_id="app",
            redirect_uri=REDIRECT,
        )

        assert query(location)["error"] == "login_required"


class TestIssuing:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, client, consented) -> None:
        self.portal = portal
        consented("app", "read write")

    def test_a_code_comes_back(self):
        _status, location, _body = call(
            self.portal,
            response_type="code",
            client_id="app",
            redirect_uri=REDIRECT,
        )

        assert query(location)["code"]

    def test_the_redirect_is_a_302(self):
        status, _location, _body = call(
            self.portal,
            response_type="code",
            client_id="app",
            redirect_uri=REDIRECT,
        )

        assert status == 302

    def test_it_redirects_to_the_registered_uri(self):
        _status, location, _body = call(
            self.portal,
            response_type="code",
            client_id="app",
            redirect_uri=REDIRECT,
        )

        assert location.startswith(f"{REDIRECT}?")

    def test_state_is_echoed_verbatim(self):
        _status, location, _body = call(
            self.portal,
            response_type="code",
            client_id="app",
            redirect_uri=REDIRECT,
            state="opaque value",
        )

        assert query(location)["state"] == "opaque value"

    def test_no_state_means_no_state_parameter(self):
        """Inventing one would break a client that checks for its absence."""
        _status, location, _body = call(
            self.portal,
            response_type="code",
            client_id="app",
            redirect_uri=REDIRECT,
        )

        assert "state" not in query(location)

    def test_the_code_records_the_authenticated_user(self):
        _status, location, _body = call(
            self.portal,
            response_type="code",
            client_id="app",
            redirect_uri=REDIRECT,
            scope="read",
        )

        codes = api.portal.get_tool("acl_users")[PLUGIN_ID].codes
        grant = codes.redeem(query(location)["code"], "app", REDIRECT)

        assert grant.subject == api.user.get_current().getId()
        assert grant.scope == "read"


class TestPKCERequired:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, public_client, consented) -> None:
        self.portal = portal
        consented("spa")

    def test_a_public_client_without_pkce_is_refused(self):
        """S8."""
        _status, location, _body = call(
            self.portal,
            response_type="code",
            client_id="spa",
            redirect_uri=REDIRECT,
        )

        assert query(location)["error"] == "invalid_request"

    def test_a_public_client_with_pkce_gets_a_code(self):
        _verifier, challenge = make_verifier()

        _status, location, _body = call(
            self.portal,
            response_type="code",
            client_id="spa",
            redirect_uri=REDIRECT,
            code_challenge=challenge,
            code_challenge_method="S256",
        )

        assert query(location)["code"]

    def test_plain_is_refused(self):
        _verifier, challenge = make_verifier()

        _status, location, _body = call(
            self.portal,
            response_type="code",
            client_id="spa",
            redirect_uri=REDIRECT,
            code_challenge=challenge,
            code_challenge_method="plain",
        )

        assert query(location)["error"] == "invalid_request"
