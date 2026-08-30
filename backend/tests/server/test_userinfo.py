"""The ``id_token`` and the userinfo endpoint.

The two ways a relying party learns who signed in, and they are not
interchangeable. The ``id_token`` is a *statement*, signed for the relying
party to read itself; the access token is a *credential*, which the relying
party brings back here. Mixing them up is how an access token ends up being
treated as proof of identity by something that never verified it.

The nonce tests are the ones that matter for federation: this package's own
client requires ``nonce`` as an essential claim with an exact value, so an
authorization server that drops it produces logins that fail with no useful
message.
"""

from . import PROFILE_ID
from pas.plugins.identity.server.browser.userinfo import UserInfoView
from pas.plugins.identity.server.grants.tokens import ISSUER_RECORD
from pas.plugins.identity.server.grants.tokens import mint_access_token
from pas.plugins.identity.server.grants.tokens import mint_id_token
from pas.plugins.identity.server.grants.tokens import token_response
from pas.plugins.identity.server.pas import PLUGIN_ID
from plone import api

import json
import pytest


pytestmark = pytest.mark.portal(profiles=[PROFILE_ID])

ISSUER = "https://id.example.org"
USERID = "alice"


@pytest.fixture
def issuer(portal):
    """Configure the issuer."""
    api.portal.set_registry_record(ISSUER_RECORD, ISSUER)
    return ISSUER


@pytest.fixture
def user(portal):
    """A user with claimable properties."""
    with api.env.adopt_roles(["Manager"]):
        return api.user.create(
            email="alice@example.org",
            username=USERID,
            password="irrelevant-to-tokens",
            properties={"fullname": "Alice Liddell"},
        )


@pytest.fixture
def client(portal, issuer, user, add_client):
    """An enabled client tokens can be addressed to."""
    client, _secret = add_client("app", scope="openid profile email", public=False)
    return client


def decode_id_token(token: str) -> dict:
    """Decode an ``id_token`` the way a relying party would.

    Through authlib against the published JWKS, not by splitting the string:
    a test that reads the payload without checking the signature would pass
    for a token no client would accept.

    :param token: The encoded token.
    :returns: The validated claims.
    """
    from authlib.jose import JsonWebToken
    from pas.plugins.identity.server.utils.keys import ALGORITHM
    from pas.plugins.identity.server.utils.keys import key_set

    claims = JsonWebToken([ALGORITHM]).decode(token, key=key_set())
    claims.validate()
    return dict(claims)


def get(portal, header: str | None):
    """Drive the userinfo view and return ``(status, body)``.

    :param portal: The Plone site.
    :param header: The Authorization header, or ``None`` for no header.
    :returns: Status code and decoded JSON body.
    """
    request = portal.REQUEST
    request._auth = header
    body = UserInfoView(portal, request)()
    return request.response.getStatus(), json.loads(body)


class TestTheIdToken:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, client) -> None:
        self.portal = portal

    def test_it_verifies_against_the_published_keys(self):
        """The whole contract: a relying party fetches the JWKS and validates
        with it, having been handed nothing else."""
        claims = decode_id_token(mint_id_token("app", USERID))

        assert claims["sub"] == USERID

    def test_the_audience_is_the_client(self):
        assert decode_id_token(mint_id_token("app", USERID))["aud"] == "app"

    def test_the_issuer_is_the_configured_one(self):
        assert decode_id_token(mint_id_token("app", USERID))["iss"] == ISSUER

    def test_the_nonce_is_echoed_verbatim(self):
        """This package's own client requires it as an essential claim with
        an exact value. Dropping it produces a login that fails with nothing
        useful to say."""
        claims = decode_id_token(mint_id_token("app", USERID, nonce="xyzzy"))

        assert claims["nonce"] == "xyzzy"

    def test_no_nonce_claim_when_none_was_sent(self):
        """Absent rather than empty: a client checking for its own nonce
        should not find a blank one that never matches."""
        assert "nonce" not in decode_id_token(mint_id_token("app", USERID))

    def test_it_carries_the_scoped_claims(self):
        """So a relying party learns who signed in without a second round
        trip, while userinfo stays there for the ones that prefer to ask."""
        claims = decode_id_token(mint_id_token("app", USERID, "openid profile"))

        assert claims["name"] == "Alice Liddell"

    def test_it_releases_nothing_the_scope_did_not(self):
        claims = decode_id_token(mint_id_token("app", USERID, "openid"))

        assert "name" not in claims
        assert "email" not in claims


class TestTheTokenResponse:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, client) -> None:
        self.portal = portal

    def test_an_openid_scope_gets_an_id_token(self):
        body = token_response("app", USERID, "openid profile")

        assert decode_id_token(body["id_token"])["sub"] == USERID

    def test_without_openid_there_is_no_id_token(self):
        """A client that did not ask to be told who the user is does not get
        told. An access token is not an identity assertion."""
        assert "id_token" not in token_response("app", USERID, "profile")

    def test_the_nonce_reaches_the_id_token(self):
        body = token_response("app", USERID, "openid", nonce="xyzzy")

        assert decode_id_token(body["id_token"])["nonce"] == "xyzzy"


class TestUserInfo:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, client) -> None:
        self.portal = portal

    def token(self, scope: str = "openid profile email") -> str:
        """Return an access token for Alice.

        :param scope: Granted scopes.
        :returns: The encoded token.
        """
        return mint_access_token("app", USERID, scope)[0]

    def test_it_answers_the_scoped_claims(self):
        status, body = get(self.portal, f"Bearer {self.token()}")

        assert status == 200
        assert body["sub"] == USERID
        assert body["name"] == "Alice Liddell"
        assert body["email"] == "alice@example.org"

    def test_the_scope_comes_from_the_token(self):
        """Not from the request. A caller cannot widen what it was granted by
        asking for more at this endpoint."""
        _status, body = get(self.portal, f"Bearer {self.token('openid')}")

        assert body == {"sub": USERID}

    def test_no_token_is_refused_with_the_right_header(self):
        """RFC 6750. A relying party's back-channel GET cannot read an HTML
        login page, which is what a protected Plone view would now answer."""
        status, body = get(self.portal, None)

        assert status == 401
        assert body["error"] == "invalid_request"
        assert self.portal.REQUEST.response.getHeader("WWW-Authenticate").startswith(
            "Bearer"
        )

    def test_a_garbage_token_is_refused(self):
        status, body = get(self.portal, "Bearer not-a-jwt")

        assert status == 401
        assert body["error"] == "invalid_token"

    def test_an_expired_token_is_refused(self):
        expired = mint_access_token("app", USERID, "openid", ttl=-1)[0]

        status, _body = get(self.portal, f"Bearer {expired}")

        assert status == 401

    def test_a_token_for_a_removed_client_is_refused(self):
        """With no denylist (D3), unregistering a client is the only
        revocation this server has -- and it has to reach here too, or
        userinfo becomes the one endpoint a withdrawn client keeps using."""
        from pas.plugins.identity.server.controlpanel.clients import remove_client

        token = self.token()
        remove_client("app")

        status, _body = get(self.portal, f"Bearer {token}")

        assert status == 401

    def test_basic_auth_is_not_a_bearer_token(self):
        status, body = get(self.portal, "Basic YWxpY2U6c2VjcmV0")

        assert status == 401
        assert body["error"] == "invalid_request"

    def test_the_answer_is_never_cached(self):
        """It is about one person and one token; a shared cache holding it
        would hand one relying party another's user."""
        get(self.portal, f"Bearer {self.token()}")

        assert self.portal.REQUEST.response.getHeader("Cache-Control") == "no-store"

    def test_the_scheme_is_case_insensitive(self):
        status, _body = get(self.portal, f"bearer {self.token()}")

        assert status == 200


class TestCodesCarryTheNonce:
    """The nonce arrives at ``/authorize`` and is needed at ``/token``."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, client) -> None:
        self.portal = portal
        self.codes = portal.acl_users[PLUGIN_ID].codes

    def test_it_survives_the_round_trip(self):
        code = self.codes.issue(
            "app", USERID, "https://app.example.org/cb", nonce="xyzzy"
        )

        grant = self.codes.redeem(code, "app", "https://app.example.org/cb")

        assert grant.nonce == "xyzzy"

    def test_it_defaults_to_empty(self):
        code = self.codes.issue("app", USERID, "https://app.example.org/cb")

        assert self.codes.redeem(code, "app", "https://app.example.org/cb").nonce == ""
