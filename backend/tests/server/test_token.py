"""The token endpoint.

Every refusal answers the same way on purpose, so most of these tests assert
the error code rather than a message, and several exist only to prove that two
different mistakes are indistinguishable from outside.
"""

from . import PROFILE_ID
from pas.plugins.identity.server.browser.token import TokenView
from pas.plugins.identity.server.grants.codes import make_verifier
from pas.plugins.identity.server.pas import PLUGIN_ID
from pas.plugins.identity.server.grants.tokens import decode_access_token
from pas.plugins.identity.server.grants.tokens import ISSUER_RECORD
from plone import api
from urllib.parse import quote

import base64
import json
import pytest


pytestmark = pytest.mark.portal(profiles=[PROFILE_ID])

REDIRECT = "https://app.example.org/cb"
ISSUER = "https://id.example.org"


@pytest.fixture
def issuer(portal):
    """Configure the issuer, without which nothing can be signed."""
    api.portal.set_registry_record(ISSUER_RECORD, ISSUER)
    return ISSUER


@pytest.fixture
def confidential(portal, add_client):
    """A confidential client and its secret."""
    client, secret = add_client(
        "app",
        redirect_uris=[REDIRECT],
        grant_types=["authorization_code"],
        scope="read",
        public=False,
    )
    return client, secret


@pytest.fixture
def public(portal, add_client):
    """A public client, which must use PKCE."""
    client, _secret = add_client(
        "spa",
        redirect_uris=[REDIRECT],
        grant_types=["authorization_code"],
        public=True,
    )
    return client


@pytest.fixture
def codes(portal):
    """The authorization code store."""
    return api.portal.get_tool("acl_users")[PLUGIN_ID].codes


def post(portal, **params):
    """Drive the token view as a POST and return ``(status, body)``.

    :param portal: The Plone site.
    :param params: Form parameters.
    :returns: Status code and decoded JSON body.
    """
    auth = params.pop("_auth", None)
    request = portal.REQUEST
    request.form.clear()
    request.form.update(params)
    request.environ["REQUEST_METHOD"] = "POST"
    # ZPublisher moves the Authorization header onto ``_auth`` during request
    # construction, so a test that set the header would be setting something
    # the view never reads.
    request._auth = auth
    try:
        body = TokenView(portal, request)()
    finally:
        request._auth = None
    return request.response.getStatus(), json.loads(body)


def basic(client_id: str, secret: str) -> str:
    """Return an ``Authorization: Basic`` header value.

    :param client_id: The client id.
    :param secret: The client secret.
    :returns: The header value, credentials base64-encoded.
    """
    raw = f"{quote(client_id)}:{quote(secret)}".encode()
    return "Basic " + base64.b64encode(raw).decode()


class TestMethod:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, issuer, confidential) -> None:
        self.portal = portal

    def test_get_is_refused(self):
        """RFC 6749 §3.2: the token endpoint is POST."""
        request = self.portal.REQUEST
        request.form.clear()
        request.environ["REQUEST_METHOD"] = "GET"

        body = json.loads(TokenView(self.portal, request)())

        assert request.response.getStatus() == 405
        assert body["error"] == "invalid_request"


class TestClientAuthentication:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, issuer, confidential, codes) -> None:
        self.portal = portal
        self.client, self.secret = confidential
        self.codes = codes
        self.code = codes.issue("app", "alice", REDIRECT, scope="read")

    def test_the_right_secret_gets_a_token(self):
        status, body = post(
            self.portal,
            grant_type="authorization_code",
            code=self.code,
            redirect_uri=REDIRECT,
            client_id="app",
            client_secret=self.secret,
        )

        assert status == 200
        assert body["access_token"]

    def test_the_wrong_secret_is_refused(self):
        status, body = post(
            self.portal,
            grant_type="authorization_code",
            code=self.code,
            redirect_uri=REDIRECT,
            client_id="app",
            client_secret="wrong",
        )

        assert status == 401
        assert body["error"] == "invalid_client"

    def test_an_unknown_client_is_refused_the_same_way(self):
        """Indistinguishable from a wrong secret."""
        status, body = post(
            self.portal,
            grant_type="authorization_code",
            code=self.code,
            redirect_uri=REDIRECT,
            client_id="nobody",
            client_secret="whatever",
        )

        assert status == 401
        assert body["error"] == "invalid_client"

    def test_a_confidential_client_may_not_omit_its_secret(self):
        """Otherwise it would be let through the public-client path."""
        status, body = post(
            self.portal,
            grant_type="authorization_code",
            code=self.code,
            redirect_uri=REDIRECT,
            client_id="app",
        )

        assert status == 401
        assert body["error"] == "invalid_client"

    def test_a_failure_carries_the_www_authenticate_header(self):
        """RFC 6749 §5.2."""
        post(
            self.portal,
            grant_type="authorization_code",
            code=self.code,
            redirect_uri=REDIRECT,
            client_id="app",
            client_secret="wrong",
        )

        assert self.portal.REQUEST.response.getHeader("WWW-Authenticate")


class TestGrantType:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, issuer, confidential) -> None:
        self.portal = portal
        self.client, self.secret = confidential

    def test_an_unsupported_grant_type_is_refused(self):
        status, body = post(
            self.portal,
            grant_type="password",
            client_id="app",
            client_secret=self.secret,
        )

        assert status == 400
        assert body["error"] == "unsupported_grant_type"

    def test_a_missing_grant_type_is_refused(self):
        status, body = post(self.portal, client_id="app", client_secret=self.secret)

        assert status == 400
        assert body["error"] == "unsupported_grant_type"


class TestExchange:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, issuer, confidential, codes) -> None:
        self.portal = portal
        self.client, self.secret = confidential
        self.codes = codes
        self.code = codes.issue("app", "alice", REDIRECT, scope="read")

    def _exchange(self, **overrides):
        params = {
            "grant_type": "authorization_code",
            "code": self.code,
            "redirect_uri": REDIRECT,
            "client_id": "app",
            "client_secret": self.secret,
        }
        params.update(overrides)
        return post(self.portal, **params)

    def test_the_response_is_rfc6749_shaped(self):
        _status, body = self._exchange()

        assert body["token_type"] == "Bearer"
        assert body["expires_in"] == 900
        assert body["scope"] == "read"

    def test_the_token_verifies_and_names_the_user(self):
        _status, body = self._exchange()

        claims = decode_access_token(body["access_token"], audience="app")

        assert claims["sub"] == "alice"
        assert claims["scope"] == "read"

    def test_the_code_is_spent(self):
        self._exchange()

        status, body = self._exchange()

        assert status == 400
        assert body["error"] == "invalid_grant"

    def test_a_wrong_redirect_uri_is_refused(self):
        status, body = self._exchange(redirect_uri="https://app.example.org/other")

        assert status == 400
        assert body["error"] == "invalid_grant"

    def test_an_unknown_code_is_refused_the_same_way(self):
        status, body = self._exchange(code="never-issued")

        assert status == 400
        assert body["error"] == "invalid_grant"

    def test_a_code_issued_to_another_client_is_refused(self):
        """Even with this client's own valid credentials."""
        other = self.codes.issue("other-app", "alice", REDIRECT)

        status, body = self._exchange(code=other)

        assert status == 400
        assert body["error"] == "invalid_grant"

    def test_the_response_is_not_cacheable(self):
        """RFC 6749 §5.1: a cached token response is a leaked token."""
        self._exchange()
        response = self.portal.REQUEST.response

        assert response.getHeader("Cache-Control") == "no-store"
        assert response.getHeader("Pragma") == "no-cache"

    def test_a_server_with_no_issuer_reports_a_request_error(self):
        """A misconfiguration the operator has to see, distinct from a
        refusal the client caused."""
        api.portal.set_registry_record(ISSUER_RECORD, "")

        status, body = self._exchange()

        assert status == 400
        assert body["error"] == "invalid_request"


class TestPublicClientExchange:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, issuer, public, codes) -> None:
        self.portal = portal
        self.codes = codes
        self.verifier, self.challenge = make_verifier()
        self.code = codes.issue("spa", "alice", REDIRECT, challenge=self.challenge)

    def _exchange(self, **overrides):
        params = {
            "grant_type": "authorization_code",
            "code": self.code,
            "redirect_uri": REDIRECT,
            "client_id": "spa",
            "code_verifier": self.verifier,
        }
        params.update(overrides)
        return post(self.portal, **params)

    def test_the_right_verifier_gets_a_token(self):
        status, body = self._exchange()

        assert status == 200
        assert decode_access_token(body["access_token"], audience="spa")

    def test_the_wrong_verifier_is_refused(self):
        other, _challenge = make_verifier()

        status, body = self._exchange(code_verifier=other)

        assert status == 400
        assert body["error"] == "invalid_grant"

    def test_a_missing_verifier_is_refused(self):
        """The attack PKCE exists to stop: an intercepted code, redeemed by
        somebody who never had the verifier."""
        status, body = self._exchange(code_verifier="")

        assert status == 400
        assert body["error"] == "invalid_grant"

    def test_the_code_is_spent_even_when_the_verifier_was_wrong(self):
        """Otherwise one intercepted code buys unlimited guesses."""
        other, _challenge = make_verifier()
        self._exchange(code_verifier=other)

        status, body = self._exchange()

        assert status == 400
        assert body["error"] == "invalid_grant"


class TestGrantRegistration:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, issuer, add_client, codes) -> None:
        self.portal = portal
        _client, self.secret = add_client(
            "svc",
            redirect_uris=[REDIRECT],
            grant_types=["client_credentials"],
            public=False,
        )
        self.code = codes.issue("svc", "alice", REDIRECT)

    def test_a_client_not_registered_for_the_code_grant_is_refused(self):
        """It authenticated perfectly well; it is simply not allowed to be
        here. Refused as invalid_grant, like every other code failure, so the
        registration is not probeable."""
        status, body = post(
            self.portal,
            grant_type="authorization_code",
            code=self.code,
            redirect_uri=REDIRECT,
            client_id="svc",
            client_secret=self.secret,
        )

        assert status == 400
        assert body["error"] == "invalid_grant"


class TestBasicClientAuthentication:
    """RFC 6749 §2.3.1 requires the token endpoint to accept HTTP Basic and
    makes the form optional. This server took only the form until the
    federation stack stood two of these sites up and the relying party -- authlib, whose
    default is client_secret_basic -- was refused with invalid_client by its
    own authorization server."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, issuer, add_client, codes) -> None:
        self.portal = portal
        _client, self.secret = add_client(
            "basic-client",
            redirect_uris=[REDIRECT],
            grant_types=["authorization_code"],
            public=False,
        )
        self.code = codes.issue("basic-client", "alice", REDIRECT)

    def _exchange(self, **kwargs):
        return post(
            self.portal,
            grant_type="authorization_code",
            code=self.code,
            redirect_uri=REDIRECT,
            **kwargs,
        )

    def test_a_basic_header_authenticates_the_client(self):
        status, body = self._exchange(_auth=basic("basic-client", self.secret))

        assert status == 200
        assert "access_token" in body

    def test_a_wrong_secret_in_the_header_is_refused(self):
        status, _body = self._exchange(_auth=basic("basic-client", "wrong"))

        assert status == 401

    def test_credentials_are_url_decoded(self):
        """§2.3.1 says both halves are form-urlencoded before the base64.
        Nothing this server mints needs it, so this is for a client
        registered elsewhere."""
        raw = b"basic-client:" + self.secret.encode()
        header = "Basic " + base64.b64encode(raw).decode()

        status, _body = self._exchange(_auth=header)

        assert status == 200

    def test_a_malformed_header_is_refused_rather_than_ignored(self):
        """Falling through to the form here would authenticate a request
        whose header could not be read."""
        status, _body = self._exchange(
            _auth="Basic not-base64!!", client_id="basic-client"
        )

        assert status == 401

    def test_a_header_without_a_colon_is_refused(self):
        header = "Basic " + base64.b64encode(b"no-colon-here").decode()

        status, _body = self._exchange(_auth=header)

        assert status == 401

    def test_sending_a_secret_both_ways_is_refused(self):
        """RFC 6749 §2.3 forbids using more than one method at once."""
        status, _body = self._exchange(
            _auth=basic("basic-client", self.secret),
            client_id="basic-client",
            client_secret=self.secret,
        )

        assert status == 401

    def test_a_client_id_that_disagrees_with_the_header_is_refused(self):
        """One client id asserted twice with two different answers. Picking a
        winner is how a confused-deputy bug starts."""
        status, _body = self._exchange(
            _auth=basic("basic-client", self.secret), client_id="someone-else"
        )

        assert status == 401

    def test_a_matching_client_id_in_the_form_is_allowed(self):
        """Sending the id both ways is not sending the *secret* both ways,
        and plenty of clients do it."""
        status, _body = self._exchange(
            _auth=basic("basic-client", self.secret), client_id="basic-client"
        )

        assert status == 200
