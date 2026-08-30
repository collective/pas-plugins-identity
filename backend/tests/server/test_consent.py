"""The consent screen and the store behind it.

The screen is the only part of this package a person actually looks at, and
the thing it is guarding against is not a protocol error: it is somebody's
account being handed to an application they never agreed to. So the tests
that matter most here are the ones about when the prompt appears -- and about
the request that arrives claiming they already answered.
"""

from . import PROFILE_ID
from . import REDIRECT
from bs4 import BeautifulSoup
from pas.plugins.identity.server.browser.authorize import AuthorizeView
from pas.plugins.identity.server.consent import ConsentStore
from pas.plugins.identity.server.pas import PLUGIN_ID
from plone.protect.authenticator import createToken
from urllib.parse import parse_qs
from urllib.parse import urlparse
from zExceptions import Forbidden

import pytest


pytestmark = pytest.mark.portal(profiles=[PROFILE_ID])


@pytest.fixture
def client(portal, add_client):
    """A confidential client with two scopes to ask for."""
    client, _secret = add_client(
        "app",
        title="Example App",
        redirect_uris=[REDIRECT],
        grant_types=["authorization_code"],
        scope="read write",
        public=False,
    )
    return client


@pytest.fixture
def store(portal):
    """The consent store."""
    return portal.acl_users[PLUGIN_ID].consent


def call(portal, **params):
    """Drive the view and return ``(status, location, body)``.

    :param portal: The Plone site.
    :param params: Request parameters.
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


class TestTheStore:
    """Plain unit tests, with no request anywhere near them."""

    @pytest.fixture(autouse=True)
    def _setup(self) -> None:
        self.store = ConsentStore()

    def test_nothing_is_granted_to_begin_with(self):
        assert self.store.granted("alice", "app") is False

    def test_a_recorded_agreement_is_granted(self):
        self.store.record("alice", "app", "read")

        assert self.store.granted("alice", "app", "read") is True

    def test_it_covers_a_narrower_request(self):
        """Agreeing to more than is asked for is still agreement."""
        self.store.record("alice", "app", "read write")

        assert self.store.granted("alice", "app", "read") is True

    def test_it_does_not_cover_a_wider_one(self):
        """The client came back for more, so the user is asked again."""
        self.store.record("alice", "app", "read")

        assert self.store.granted("alice", "app", "read write") is False

    def test_recording_replaces_rather_than_merges(self):
        """The user was shown a list and agreed to that list. Adding to a set
        they were never shown in full is how a consent screen ends up
        recording more than anybody said yes to."""
        self.store.record("alice", "app", "read write")

        self.store.record("alice", "app", "read")

        assert self.store.granted("alice", "app", "write") is False

    def test_an_empty_scope_still_needs_a_record(self):
        """A client asking for no scope is not asking for nothing: it wants a
        token that speaks for this user. Being asked once is the point."""
        assert self.store.granted("alice", "app", "") is False

        self.store.record("alice", "app", "")

        assert self.store.granted("alice", "app", "") is True

    @pytest.mark.parametrize(
        "userid,client_id",
        [("bob", "app"), ("alice", "other")],
        ids=["between-users", "between-clients"],
    )
    def test_agreements_do_not_leak(self, userid: str, client_id: str):
        """An agreement names both a person and an application, and changing
        either one is a different agreement."""
        self.store.record("alice", "app", "read")

        assert self.store.granted(userid, client_id, "read") is False


class TestThePrompt:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, client, store, userid) -> None:
        self.portal = portal
        self.store = store
        self.userid = userid

    def test_a_first_request_renders_the_form(self):
        status, location, body = call(
            self.portal,
            response_type="code",
            client_id="app",
            redirect_uri=REDIRECT,
            scope="read",
        )

        assert status == 200
        assert location is None
        assert "<form" in body

    def test_nothing_is_issued_while_the_user_is_being_asked(self):
        """The most important assertion in this module. A consent screen that
        has already issued the code is decoration."""
        codes = self.portal.acl_users[PLUGIN_ID].codes

        call(
            self.portal,
            response_type="code",
            client_id="app",
            redirect_uri=REDIRECT,
            scope="read",
        )

        assert codes.count() == 0

    def test_the_form_names_the_client_and_the_user(self):
        _status, _location, body = call(
            self.portal,
            response_type="code",
            client_id="app",
            redirect_uri=REDIRECT,
        )

        assert "Example App" in body

    def test_the_form_lists_the_requested_scopes(self):
        _status, _location, body = call(
            self.portal,
            response_type="code",
            client_id="app",
            redirect_uri=REDIRECT,
            scope="read write",
        )

        listed = [
            item.text.strip()
            for item in BeautifulSoup(body, "html.parser").find_all("li")
        ]

        assert listed == ["read", "write"]

    def test_the_form_carries_the_request_back(self):
        """Including the state and the PKCE challenge. Losing either between
        the question and the answer breaks the flow in a way that looks like
        a client bug."""
        _status, _location, body = call(
            self.portal,
            response_type="code",
            client_id="app",
            redirect_uri=REDIRECT,
            state="xyzzy",
            code_challenge="abc",
            code_challenge_method="S256",
        )

        assert 'value="xyzzy"' in body
        assert 'value="abc"' in body

    def test_an_agreed_request_is_not_asked_again(self):
        self.store.record(self.userid, "app", "read")

        status, location, _body = call(
            self.portal,
            response_type="code",
            client_id="app",
            redirect_uri=REDIRECT,
            scope="read",
        )

        assert status == 302
        assert query(location)["code"]

    def test_a_wider_request_is_asked_again(self):
        self.store.record(self.userid, "app", "read")

        status, _location, body = call(
            self.portal,
            response_type="code",
            client_id="app",
            redirect_uri=REDIRECT,
            scope="read write",
        )

        assert status == 200
        assert "<form" in body

    def test_the_prompt_comes_after_validation(self):
        """A user must never be shown a form asking them to approve a request
        that was going to be refused anyway."""
        status, location, _body = call(
            self.portal,
            response_type="code",
            client_id="app",
            redirect_uri=REDIRECT,
            scope="read admin",
        )

        assert status == 302
        assert query(location)["error"] == "invalid_scope"


class TestTheAnswer:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, client, store, userid) -> None:
        self.portal = portal
        self.store = store
        self.userid = userid

    def answer(self, consent: str, token: str | None = None, **extra):
        """Post the consent form back.

        :param consent: The button pressed.
        :param token: The CSRF token; a valid one by default.
        :param extra: Extra request parameters.
        :returns: Status, Location and body.
        """
        return call(
            self.portal,
            response_type="code",
            client_id="app",
            redirect_uri=REDIRECT,
            scope="read",
            consent=consent,
            _authenticator=createToken() if token is None else token,
            **extra,
        )

    def test_allowing_issues_a_code(self):
        status, location, _body = self.answer("allow")

        assert status == 302
        assert query(location)["code"]

    def test_allowing_records_the_agreement(self):
        self.answer("allow")

        assert self.store.granted(self.userid, "app", "read") is True

    def test_denying_reports_access_denied_to_the_client(self):
        _status, location, _body = self.answer("deny")

        assert location.startswith(REDIRECT)
        assert query(location)["error"] == "access_denied"

    def test_denying_records_nothing(self):
        self.answer("deny")

        assert self.store.granted(self.userid, "app", "read") is False

    def test_denying_echoes_the_state(self):
        """The client's CSRF token has to survive a refusal as surely as a
        success."""
        _status, location, _body = self.answer("deny", state="xyzzy")

        assert query(location)["state"] == "xyzzy"

    def test_anything_that_is_not_allow_is_a_refusal(self):
        """Consent is the thing that must be explicit, so it is the only
        value spelled out. A future template growing a third button must not
        accidentally grant."""
        _status, location, _body = self.answer("maybe-later")

        assert query(location)["error"] == "access_denied"

    def test_a_forged_consent_is_forbidden(self):
        """Not a denial: a consent POST without a valid token is an attempt
        to authorize an application in somebody else's name, and it should
        look like the attack it is rather than like the user clicking no."""
        with pytest.raises(Forbidden):
            self.answer("allow", token="not-a-token")

    def test_a_forged_consent_records_nothing(self):
        with pytest.raises(Forbidden):
            self.answer("allow", token="not-a-token")

        assert self.store.granted(self.userid, "app", "read") is False

    def test_the_answer_is_revalidated(self):
        """The second request re-runs every check the first one did, so a
        client disabled while the user was reading the form is refused on the
        way out."""
        from pas.plugins.identity.server.controlpanel.clients import get_clients
        from pas.plugins.identity.server.controlpanel.clients import set_clients

        clients = get_clients()
        clients[0].enabled = False
        set_clients(clients)

        status, location, _body = self.answer("allow")

        assert status == 400
        assert location is None
