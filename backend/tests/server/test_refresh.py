"""Refresh tokens and their rotation.

Rotation on its own buys very little: an attacker holding a stolen copy just
uses it first, and the legitimate client is the one whose token stops working.
What makes it worth doing is reuse detection, so the tests that matter here
are the replay ones -- a spent token turning up again means two parties hold
it, exactly one is entitled to it, there is no way to tell which, and so
neither keeps access.
"""

from . import PROFILE_ID
from datetime import datetime
from datetime import timedelta
from datetime import UTC
from pas.plugins.identity.server.browser.token import TokenView
from pas.plugins.identity.server.pas import PLUGIN_ID
from pas.plugins.identity.server.refresh import RefreshError
from pas.plugins.identity.server.refresh import RefreshTokenStore
from pas.plugins.identity.server.tokens import decode_access_token
from pas.plugins.identity.server.tokens import ISSUER_RECORD
from plone import api

import json
import pytest


pytestmark = pytest.mark.portal(profiles=[PROFILE_ID])

ISSUER = "https://id.example.org"
REDIRECT = "https://app.example.org/cb"
USERID = "alice"


@pytest.fixture
def issuer(portal):
    """Configure the issuer."""
    api.portal.set_registry_record(ISSUER_RECORD, ISSUER)
    return ISSUER


@pytest.fixture
def user(portal):
    """A user for tokens to act for."""
    with api.env.adopt_roles(["Manager"]):
        return api.user.create(
            email="alice@example.org",
            username=USERID,
            password="irrelevant-to-tokens",
        )


@pytest.fixture
def refreshable(portal, issuer, user, add_client):
    """A client registered for the code grant *and* refresh."""
    client, secret = add_client(
        "app",
        redirect_uris=[REDIRECT],
        grant_types=["authorization_code", "refresh_token"],
        scope="openid profile email",
        public=False,
    )
    return client, secret


@pytest.fixture
def store(portal):
    """The refresh-token store on the plugin."""
    return portal.acl_users[PLUGIN_ID].refresh


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


class TestTheStore:
    """Plain unit tests, with no request anywhere near them."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.store = RefreshTokenStore()

    def test_rotation_returns_a_different_token(self):
        token = self.store.issue("app", USERID, "openid")

        replacement, _grant = self.store.rotate(token, "app")

        assert replacement != token

    def test_rotation_carries_the_grant_forward(self):
        token = self.store.issue("app", USERID, "openid profile")

        _replacement, grant = self.store.rotate(token, "app")

        assert grant.subject == USERID
        assert grant.scope == "openid profile"

    def test_the_previous_token_stops_working(self):
        """The plan's check, and the minimum rotation has to deliver."""
        token = self.store.issue("app", USERID)
        self.store.rotate(token, "app")

        with pytest.raises(RefreshError):
            self.store.rotate(token, "app")

    def test_the_replacement_keeps_the_family(self):
        """Rotation is a chain, not a series of unrelated tokens: revocation
        has to be able to reach every descendant of one authorization."""
        token = self.store.issue("app", USERID)

        replacement, grant = self.store.rotate(token, "app")

        assert self.store._tokens[replacement].family == grant.family

    def test_replaying_a_spent_token_kills_the_family(self):
        """The whole point. Two parties hold this token and exactly one is
        entitled to it; since there is no way to tell which, neither keeps
        access and both go back to the authorization endpoint."""
        first = self.store.issue("app", USERID)
        live, _grant = self.store.rotate(first, "app")

        with pytest.raises(RefreshError):
            self.store.rotate(first, "app")

        assert self.store.count() == 0
        with pytest.raises(RefreshError):
            self.store.rotate(live, "app")

    def test_a_replay_does_not_touch_another_family(self):
        """One compromised chain must not log out every other client."""
        other = self.store.issue("other-app", "bob")
        first = self.store.issue("app", USERID)
        self.store.rotate(first, "app")

        with pytest.raises(RefreshError):
            self.store.rotate(first, "app")

        assert self.store.rotate(other, "other-app")

    def test_serialize_does_not_include_the_token(self):
        """This object is what the token maps *to*, and the mapping key is
        the secret."""
        token = self.store.issue("app", USERID, "openid")

        rendered = self.store._tokens[token].serialize()

        assert token not in str(rendered)
        assert rendered["subject"] == USERID
        assert rendered["scope"] == "openid"

    def test_an_unknown_token_is_refused(self):
        with pytest.raises(RefreshError):
            self.store.rotate("never-issued", "app")

    def test_another_clients_token_is_refused(self):
        """A refresh token is a bearer credential, so without this a client
        that obtained somebody else's could refresh it into one of its own."""
        token = self.store.issue("app", USERID)

        with pytest.raises(RefreshError):
            self.store.rotate(token, "other-app")

    def test_a_wrong_client_does_not_spend_the_token(self):
        """The legitimate client must still be able to use it."""
        token = self.store.issue("app", USERID)
        with pytest.raises(RefreshError):
            self.store.rotate(token, "other-app")

        assert self.store.rotate(token, "app")

    def test_an_expired_token_is_refused(self):
        token = self.store.issue("app", USERID)
        self.store._tokens[token].expires_at = datetime.now(UTC) - timedelta(seconds=1)

        with pytest.raises(RefreshError):
            self.store.rotate(token, "app")

    def test_an_expired_token_is_still_spent(self):
        """Burned before the expiry check, exactly as an authorization code
        is: a presented token is gone whether or not the presentation was
        any good."""
        token = self.store.issue("app", USERID)
        self.store._tokens[token].expires_at = datetime.now(UTC) - timedelta(seconds=1)
        with pytest.raises(RefreshError):
            self.store.rotate(token, "app")

        assert token not in self.store._tokens

    def test_expired_tokens_are_swept(self):
        """The store cannot grow forever in a site where most integrations
        are set up once and abandoned."""
        token = self.store.issue("app", USERID)
        self.store._tokens[token].expires_at = datetime.now(UTC) - timedelta(seconds=1)

        self.store.issue("app", "bob")

        assert self.store.count() == 1

    def test_spent_records_are_swept_too(self):
        """Kept only as long as the token could have been redeemable. Past
        that a replay is refused by expiry anyway."""
        token = self.store.issue("app", USERID)
        self.store.rotate(token, "app")
        self.store._spent[token] = (
            self.store._spent[token][0],
            datetime.now(UTC) - timedelta(seconds=1),
        )

        self.store.issue("app", "bob")

        assert token not in self.store._spent


class TestTheGrant:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, refreshable, store) -> None:
        self.portal = portal
        self.client, self.secret = refreshable
        self.store = store

    def refresh_token(self, scope: str = "openid profile") -> str:
        """Issue a refresh token directly, skipping the code flow.

        :param scope: The scopes it carries.
        :returns: The token.
        """
        return self.store.issue("app", USERID, scope)

    def exchange(self, token: str, **extra):
        """Present a refresh token at the token endpoint.

        :param token: The refresh token.
        :param extra: Extra form parameters.
        :returns: Status and body.
        """
        return post(
            self.portal,
            grant_type="refresh_token",
            refresh_token=token,
            client_id="app",
            client_secret=self.secret,
            **extra,
        )

    def test_it_returns_a_new_access_token(self):
        status, body = self.exchange(self.refresh_token())

        assert status == 200
        assert decode_access_token(body["access_token"])["sub"] == USERID

    def test_it_returns_a_new_refresh_token(self):
        token = self.refresh_token()

        _status, body = self.exchange(token)

        assert body["refresh_token"] != token

    def test_the_old_one_is_refused_afterwards(self):
        token = self.refresh_token()
        self.exchange(token)

        status, body = self.exchange(token)

        assert status == 400
        assert body["error"] == "invalid_grant"

    def test_an_openid_scope_still_gets_an_id_token(self):
        _status, body = self.exchange(self.refresh_token("openid"))

        assert "id_token" in body

    def test_the_scope_can_be_narrowed(self):
        _status, body = self.exchange(
            self.refresh_token("openid profile"), scope="openid"
        )

        assert body["scope"] == "openid"

    def test_the_scope_cannot_be_widened(self):
        """Silently granting more than the user agreed to at the
        authorization endpoint would make consent a one-time formality."""
        status, body = self.exchange(self.refresh_token("openid"), scope="openid email")

        assert status == 400
        assert body["error"] == "invalid_scope"

    def test_a_client_not_registered_for_it_is_refused(self, add_client):
        _other, secret = add_client(
            "web", grant_types=["authorization_code"], public=False
        )

        status, body = post(
            self.portal,
            grant_type="refresh_token",
            refresh_token=self.refresh_token(),
            client_id="web",
            client_secret=secret,
        )

        assert status == 400
        assert body["error"] == "unauthorized_client"

    def test_a_garbage_token_is_refused_like_any_other(self):
        status, body = self.exchange("never-issued")

        assert status == 400
        assert body["error"] == "invalid_grant"


class TestIssuance:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, refreshable, store) -> None:
        self.portal = portal
        self.client, self.secret = refreshable
        self.store = store
        self.codes = portal.acl_users[PLUGIN_ID].codes

    def redeem_a_code(self, client_id: str = "app", secret: str | None = None):
        """Run the code grant and return the response body.

        :param client_id: The client redeeming.
        :param secret: Its secret; the fixture's by default.
        :returns: Status and body.
        """
        code = self.codes.issue(client_id, USERID, REDIRECT, scope="openid")
        return post(
            self.portal,
            grant_type="authorization_code",
            code=code,
            redirect_uri=REDIRECT,
            client_id=client_id,
            client_secret=self.secret if secret is None else secret,
        )

    def test_the_code_grant_issues_one(self):
        _status, body = self.redeem_a_code()

        assert body["refresh_token"]

    def test_a_client_without_the_grant_gets_none(self, add_client):
        """Gated on the registration rather than a scope, so whether a client
        may keep working without its user present is an operator's decision
        rather than something the client grants itself by asking."""
        _other, secret = add_client(
            "web",
            redirect_uris=[REDIRECT],
            grant_types=["authorization_code"],
            scope="openid",
            public=False,
        )

        _status, body = self.redeem_a_code("web", secret)

        assert "refresh_token" not in body

    def test_client_credentials_never_gets_one(self, add_client):
        """RFC 6749 §4.4.3 says so, and the reasoning is plain: the client
        can mint another token whenever it likes with its own secret, so a
        refresh token would be a second credential with nothing to add."""
        _svc, secret = add_client(
            "svc",
            grant_types=["client_credentials", "refresh_token"],
            scope="openid",
            public=False,
            service_user=USERID,
        )

        _status, body = post(
            self.portal,
            grant_type="client_credentials",
            client_id="svc",
            client_secret=secret,
        )

        assert "refresh_token" not in body
