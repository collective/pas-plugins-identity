"""An authorization paused to complete a profile, then resumed.

The scenario a live demo produced on 2026-08-27 and no test covered. A person
signs in at the provider, the relying party redirects them here to authorize,
and their profile is not complete enough to say anything about them. They fill
it in, the authorization resumes, and the relying party exchanges its code --
four seconds after the profile was saved, in the run that was reported -- and
creates an account with neither an email address nor a name.

The suspicion was that the server had captured claims when the code was
issued, so anything the person typed afterwards arrived too late. It has not:
:func:`~pas.plugins.identity.server.grants.tokens.mint_id_token` calls
``claims_for`` at token issue, and an authorization code carries a subject and
a scope rather than a snapshot of a user. These tests hold that where it can
be seen from outside -- a claim that changed between the two halves of one
authorization is released as it stands at the exchange.

Written from the relying party's side deliberately: what matters is not that
``claims_for`` reads live properties, which its own tests already say, but
that nothing between the authorize request and the token response freezes
them.
"""

from . import PROFILE_ID
from . import REDIRECT
from pas.plugins.identity.server.browser.token import TokenView
from pas.plugins.identity.server.pas import PLUGIN_ID
from plone import api

import json
import pytest


pytestmark = pytest.mark.portal(profiles=[PROFILE_ID])

USERID = "dana"
#: What the account carries before anybody fills the form in.
PLACEHOLDER = "placeholder@example.org"
SCOPE = "openid email profile"


@pytest.fixture
def incomplete(portal):
    """A user whose profile says nothing about them yet.

    No address and no name -- the state the person is in when the gate sends
    them to the edit form, and the state the reported account was created in.

    ``fullname`` is empty and the address is a placeholder rather than
    nothing, because neither can be arranged otherwise: ``api.user.create``
    refuses to make a user without an address, and ``setMemberProperties``
    silently drops a write that would blank one -- verified here, not
    assumed. An externally authenticated user never goes through either and
    really can start out with no address at all; what these tests need is
    only that both claims *change* while the authorization is paused.

    :param portal: The Plone site.
    :returns: The new member.
    """
    with api.env.adopt_roles(["Manager"]):
        return api.user.create(
            email=PLACEHOLDER,
            username=USERID,
            password="irrelevant-to-claims",
        )


@pytest.fixture
def client(portal, issuer, incomplete, add_client):
    """A confidential client that may run the code grant.

    :param portal: The Plone site.
    :param issuer: Ensures the issuer is configured first.
    :param incomplete: Ensures the user exists first.
    :param add_client: The client factory.
    :returns: ``(client, secret)``.
    """
    return add_client(
        "app",
        redirect_uris=[REDIRECT],
        grant_types=["authorization_code"],
        scope=SCOPE,
        public=False,
    )


def decode_id_token(token: str) -> dict:
    """Decode an ``id_token`` the way a relying party would.

    Through authlib against the published JWKS rather than by splitting the
    string: a test that read the payload without checking the signature would
    pass for a token no client would accept.

    :param token: The encoded token.
    :returns: The validated claims.
    """
    from authlib.jose import JsonWebToken
    from pas.plugins.identity.server.utils.keys import ALGORITHM
    from pas.plugins.identity.server.utils.keys import key_set

    claims = JsonWebToken([ALGORITHM]).decode(token, key=key_set())
    claims.validate()
    return dict(claims)


class TestClaimsAfterAPausedAuthorization:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, client) -> None:
        self.portal = portal
        self.client, self.secret = client
        self.codes = portal.acl_users[PLUGIN_ID].codes

    def authorize(self) -> str:
        """Issue a code, as the authorize endpoint does.

        This is the pause: the code exists, the browser has been handed back
        to the relying party, and nothing has been said about the user yet.

        :returns: The authorization code.
        """
        return self.codes.issue("app", USERID, REDIRECT, scope=SCOPE)

    def complete_the_profile(self) -> None:
        """Fill in what the site requires, as the edit form would."""
        with api.env.adopt_roles(["Manager"]):
            api.user.get(userid=USERID).setMemberProperties({
                "email": "dana@example.org",
                "fullname": "Dana Scully",
            })

    def exchange(self, code: str):
        """Redeem a code at the token endpoint.

        :param code: The authorization code.
        :returns: Status code and decoded JSON body.
        """
        request = self.portal.REQUEST
        request.form.clear()
        request.form.update({
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT,
            "client_id": "app",
            "client_secret": self.secret,
        })
        request.environ["REQUEST_METHOD"] = "POST"
        body = TokenView(self.portal, request)()
        return request.response.getStatus(), json.loads(body)

    def test_the_completed_claims_are_the_ones_released(self):
        """The reported bug, asserted from the relying party's side: the
        person filled the form in while the authorization was paused, so the
        account the relying party creates has their address and their name."""
        code = self.authorize()
        self.complete_the_profile()

        status, body = self.exchange(code)

        assert status == 200
        claims = decode_id_token(body["id_token"])
        assert claims["email"] == "dana@example.org"
        assert claims["name"] == "Dana Scully"

    def test_an_authorization_issued_before_the_edit_is_still_valid(self):
        """Completing a profile must not invalidate an authorization already
        in flight -- that would turn the gate into a way to lose the code the
        person was sent here to get."""
        code = self.authorize()
        self.complete_the_profile()

        status, _body = self.exchange(code)

        assert status == 200

    def test_the_uncompleted_profile_is_what_an_early_exchange_gets(self):
        """The other half of the same fact, and what makes the test above
        mean anything: redeemed before the form is filled in, the same code
        carries the account as it stands. ``name`` is absent rather than
        empty, because ``claims_for`` omits an empty value -- so a relying
        party can tell "not said" from "said to be blank"."""
        status, body = self.exchange(self.authorize())

        assert status == 200
        claims = decode_id_token(body["id_token"])
        assert claims["email"] == PLACEHOLDER
        assert "name" not in claims

    def test_a_second_authorization_sees_the_same_completed_claims(self):
        """The demo's second sign-in was what filled the account in, which is
        what made the first look like a one-off. Both now say the same."""
        self.complete_the_profile()

        _status, body = self.exchange(self.authorize())

        claims = decode_id_token(body["id_token"])
        assert claims["email"] == "dana@example.org"
        assert claims["name"] == "Dana Scully"
