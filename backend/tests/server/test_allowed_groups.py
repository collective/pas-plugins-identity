"""A client restricted to members of some groups.

The order of the checks is most of what is asserted. Somebody the client does
not admit is refused before the profile gate and before consent, so a
refusal leaves nothing behind: no consent on record, no ``ClientAuthorized``,
no code. And a refresh asks again, so leaving the group ends access once the
access token expires rather than when the refresh token does.
"""

from . import PROFILE_ID
from . import REDIRECT
from . import USERID
from pas.plugins.identity.core import audit
from pas.plugins.identity.server.browser import authorize
from pas.plugins.identity.server.browser.authorize import AuthorizeView
from pas.plugins.identity.server.browser.token import TokenView
from pas.plugins.identity.server.controlpanel.clients import ClientConfig
from pas.plugins.identity.server.controlpanel.clients import get_client
from pas.plugins.identity.server.controlpanel.clients import set_clients
from pas.plugins.identity.server.events import IClientAuthorized
from pas.plugins.identity.server.pas import PLUGIN_ID
from plone import api
from plone.app.testing import login
from plone.protect.authenticator import createToken
from urllib.parse import parse_qs
from urllib.parse import urlparse
from zope.component import adapter
from zope.component import getGlobalSiteManager

import json
import pytest


pytestmark = pytest.mark.portal(profiles=[PROFILE_ID])


#: The group the restricted client admits.
ALLOWED = "stats-readers"


@pytest.fixture
def groups(portal):
    """Create the allowed group, an unrelated one, and one nested in the first.

    :param portal: The Plone site.
    :returns: A helper adding a user to a group.
    """
    with api.env.adopt_roles(["Manager"]):
        api.group.create(groupname=ALLOWED)
        api.group.create(groupname="editors")
        api.group.create(groupname="stats-team")
        # A group as a member of a group: plone.api only adds users.
        api.portal.get_tool("portal_groups").addPrincipalToGroup("stats-team", ALLOWED)

    def join(userid: str, groupname: str) -> None:
        """Make a user a direct member of a group.

        :param userid: The user.
        :param groupname: The group.
        """
        with api.env.adopt_roles(["Manager"]):
            api.group.add_user(groupname=groupname, username=userid)

    return join


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


def call(portal, **params):
    """Drive the authorization endpoint for ``stats`` and return its Location.

    :param portal: The Plone site.
    :param params: Query parameters on top of a valid request.
    :returns: The Location header, or ``None`` when nothing redirected.
    """
    request = portal.REQUEST
    request.form.clear()
    request.form.update({
        "response_type": "code",
        "client_id": "stats",
        "redirect_uri": REDIRECT,
        "scope": "openid",
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


def refused(userid: str) -> list:
    """Return a user's ``client-refused`` audit entries.

    :param userid: The user.
    :returns: The entries, newest first.
    """
    return [e for e in audit.entries(userid) if e.event == audit.CLIENT_REFUSED]


class TestTheRegistration:
    """The model, with no request anywhere near it."""

    def test_empty_by_default(self):
        assert ClientConfig("app").allowed_groups == []

    def test_ids_are_stripped_and_deduplicated_in_order(self):
        client = ClientConfig("app", allowed_groups=[" b ", "a", "b", "", "  "])

        assert client.allowed_groups == ["b", "a"]

    def test_a_single_string_is_one_group(self):
        """Never a sequence of one-letter group ids."""
        assert ClientConfig("app", allowed_groups="editors").allowed_groups == [
            "editors"
        ]

    def test_assignment_normalises_too(self):
        """The PATCH endpoint assigns to the attribute directly."""
        client = ClientConfig("app")

        client.allowed_groups = ("a", "a")

        assert client.allowed_groups == ["a"]

    def test_it_round_trips(self):
        client = ClientConfig("app", allowed_groups=["a", "b"])

        again = ClientConfig.deserialize(client.serialize(include_hash=True))

        assert again.allowed_groups == ["a", "b"]

    def test_a_registration_stored_before_the_field_reads_as_empty(self):
        assert ClientConfig.deserialize({"client_id": "app"}).allowed_groups == []

    @pytest.mark.parametrize(
        "allowed,groups,expected",
        [
            ([], [], True),
            ([], ["anything"], True),
            (["a"], ["a"], True),
            (["a", "b"], ["x", "b"], True),
            (["a"], [], False),
            (["a"], ["b"], False),
        ],
    )
    def test_admits(self, allowed, groups, expected):
        assert ClientConfig("app", allowed_groups=allowed).admits(groups) is expected


class TestTheAuthorizationEndpoint:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, add_client, groups, fired, monkeypatch) -> None:
        self.portal = portal
        self.join = groups
        self.fired = fired
        # A user created the way a site creates one, so group membership goes
        # through this package's own group plugin. The stock test user lives
        # in source_users, which that plugin never reaches.
        with api.env.adopt_roles(["Manager"]):
            api.user.create(
                email="alice@example.org", username=USERID, password="irrelevant"
            )
        login(portal, USERID)
        # Their profile is incomplete, and the gate would pause every member
        # before a code. The one test about the gate turns it back on.
        monkeypatch.setattr(authorize, "incomplete_profile_url", lambda userid: "")
        self.userid = USERID
        self.consent = portal.acl_users[PLUGIN_ID].consent
        add_client(
            "stats",
            redirect_uris=[REDIRECT],
            grant_types=["authorization_code"],
            scope="openid",
            allowed_groups=[ALLOWED],
        )

    def test_a_member_gets_a_code(self):
        self.join(self.userid, ALLOWED)
        self.consent.record(self.userid, "stats", "openid")

        assert query(call(self.portal))["code"]

    def test_a_member_of_a_nested_group_gets_a_code(self):
        self.join(self.userid, "stats-team")
        self.consent.record(self.userid, "stats", "openid")

        assert query(call(self.portal))["code"]

    def test_a_member_is_still_asked_to_consent(self):
        """Being admitted is not agreeing: the consent screen still stands
        between a member and a code."""
        self.join(self.userid, ALLOWED)

        location = call(self.portal)

        assert location is None

    def test_a_non_member_is_refused(self):
        self.join(self.userid, "editors")
        self.consent.record(self.userid, "stats", "openid")

        answer = query(call(self.portal, state="xyzzy"))

        assert answer["error"] == "access_denied"
        assert answer["state"] == "xyzzy"
        assert "code" not in answer

    def test_prompt_none_is_refused_the_same_way(self):
        """Not ``consent_required`` or ``interaction_required``: asking would
        not change the answer."""
        answer = query(call(self.portal, prompt="none"))

        assert answer["error"] == "access_denied"

    def test_a_non_member_is_never_shown_the_consent_screen(self):
        location = call(self.portal)

        assert query(location)["error"] == "access_denied"

    def test_agreeing_on_the_consent_form_records_nothing(self):
        """The form posts back to this endpoint, and the check runs again on
        the way out, before the answer is recorded."""
        location = call(self.portal, consent="allow", _authenticator=createToken())

        assert query(location)["error"] == "access_denied"
        assert not self.consent.granted(self.userid, "stats", "openid")

    def test_no_client_authorized_is_fired(self):
        self.consent.record(self.userid, "stats", "openid")

        call(self.portal)

        assert self.fired == []

    def test_the_refusal_is_audited(self):
        call(self.portal)

        [entry] = refused(self.userid)
        assert entry.provider == "stats"
        assert entry.success is False
        assert entry.detail == {"client_id": "stats", "stage": "authorize"}

    def test_a_member_leaves_no_refusal(self):
        self.join(self.userid, ALLOWED)
        self.consent.record(self.userid, "stats", "openid")

        call(self.portal)

        assert refused(self.userid) == []

    def test_an_incomplete_profile_is_refused_not_paused(self, monkeypatch):
        """Nobody is asked to finish a profile for a client they may not use."""
        monkeypatch.setattr(
            authorize, "incomplete_profile_url", lambda userid: "http://nohost/p"
        )

        location = call(self.portal)

        assert location.startswith(REDIRECT)
        assert query(location)["error"] == "access_denied"

    def test_a_group_that_does_not_exist_admits_nobody(self):
        client = get_client("stats")
        client.allowed_groups = ["not-created-yet"]
        set_clients([client])
        self.join(self.userid, ALLOWED)

        assert query(call(self.portal))["error"] == "access_denied"


class TestAnUnrestrictedClient:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, add_client) -> None:
        self.portal = portal
        self.userid = api.user.get_current().getId()
        add_client(
            "stats",
            redirect_uris=[REDIRECT],
            grant_types=["authorization_code"],
            scope="openid",
        )
        portal.acl_users[PLUGIN_ID].consent.record(self.userid, "stats", "openid")

    def test_anybody_gets_a_code(self):
        assert query(call(self.portal))["code"]

    def test_nothing_is_audited_as_refused(self):
        call(self.portal)

        assert refused(self.userid) == []


class TestTheRefreshGrant:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, issuer, add_client, groups) -> None:
        self.portal = portal
        self.join = groups
        with api.env.adopt_roles(["Manager"]):
            api.user.create(
                email="alice@example.org", username=USERID, password="irrelevant"
            )
        _client, self.secret = add_client(
            "stats",
            redirect_uris=[REDIRECT],
            grant_types=["authorization_code", "refresh_token"],
            scope="openid",
            public=False,
            allowed_groups=[ALLOWED],
        )
        self.store = portal.acl_users[PLUGIN_ID].refresh

    def exchange(self, token: str) -> tuple[int, dict]:
        """Present a refresh token for ``stats`` at the token endpoint.

        :param token: The refresh token.
        :returns: Status and decoded body.
        """
        request = self.portal.REQUEST
        request.form.clear()
        request.form.update({
            "grant_type": "refresh_token",
            "refresh_token": token,
            "client_id": "stats",
            "client_secret": self.secret,
        })
        request.environ["REQUEST_METHOD"] = "POST"
        body = TokenView(self.portal, request)()
        return request.response.getStatus(), json.loads(body)

    def test_a_member_is_refreshed(self):
        self.join(USERID, ALLOWED)

        status, body = self.exchange(self.store.issue("stats", USERID, "openid"))

        assert status == 200
        assert body["refresh_token"]

    def test_somebody_who_left_the_group_is_refused(self):
        """Issued while they were a member; refused at the next rotation."""
        token = self.store.issue("stats", USERID, "openid")

        status, body = self.exchange(token)

        assert status == 400
        assert body["error"] == "invalid_grant"
        assert "refresh_token" not in body

    def test_their_tokens_for_the_client_are_revoked(self):
        """Including the replacement the rotation minted, which nobody saw,
        and any other token of theirs for this client."""
        other = self.store.issue("stats", USERID, "openid")

        self.exchange(self.store.issue("stats", USERID, "openid"))

        assert self.store.count() == 0
        status, _body = self.exchange(other)
        assert status == 400

    def test_the_refusal_is_audited(self):
        self.exchange(self.store.issue("stats", USERID, "openid"))

        [entry] = refused(USERID)
        assert entry.detail == {"client_id": "stats", "stage": "refresh"}
