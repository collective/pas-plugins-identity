"""``@oauth-grants`` -- what a person has authorized, and undoing it.

The mirror image of ``@identities``, and the tests that matter most are the
ones about withdrawal actually reaching something. A screen that says
"revoked" while the application keeps working for another fortnight is worse
than no screen: it tells somebody a false thing about their own account.
"""

from . import PROFILE_ID
from datetime import datetime
from datetime import timedelta
from datetime import UTC
from pas.plugins.identity.server.consent import ConsentRecord
from pas.plugins.identity.server.consent import ConsentStore
from pas.plugins.identity.server.pas import PLUGIN_ID
from pas.plugins.identity.server.services.grants.delete import GrantsDelete
from pas.plugins.identity.server.services.grants.get import GrantsGet
from plone import api
from plone.app.testing import logout

import pytest


pytestmark = pytest.mark.portal(profiles=[PROFILE_ID])

REDIRECT = "https://app.example.org/cb"


@pytest.fixture
def plugin(portal):
    """The server PAS plugin, holding both stores."""
    return portal.acl_users[PLUGIN_ID]


@pytest.fixture
def userid() -> str:
    """The authenticated user's id."""
    return api.user.get_current().getId()


@pytest.fixture
def clients(portal, add_client):
    """Two registered clients to have agreements with."""
    for client_id, title in (("app", "Example App"), ("kiosk", "Lobby kiosk")):
        add_client(
            client_id,
            title=title,
            redirect_uris=[REDIRECT],
            grant_types=["authorization_code", "refresh_token"],
            scope="openid profile email",
            public=False,
        )


def listing(portal):
    """Drive ``GET @oauth-grants``.

    :param portal: The Plone site.
    :returns: The reply body.
    """
    portal.REQUEST.form.clear()
    return GrantsGet(portal, portal.REQUEST).reply()


def withdraw(portal, *segments):
    """Drive ``DELETE @oauth-grants/<client_id>``.

    :param portal: The Plone site.
    :param segments: Path segments after the endpoint.
    :returns: The reply body.
    """
    portal.REQUEST.form.clear()
    service = GrantsDelete(portal, portal.REQUEST)
    service.segments = list(segments)
    return service.reply()


class TestTheStore:
    """Plain unit tests, with no request anywhere near them."""

    @pytest.fixture(autouse=True)
    def _setup(self) -> None:
        self.store = ConsentStore()

    def test_a_new_user_has_authorized_nothing(self):
        assert self.store.for_user("alice") == []

    def test_it_lists_what_they_agreed_to(self):
        self.store.record("alice", "app", "openid profile")

        (client_id, record) = self.store.for_user("alice")[0]

        assert client_id == "app"
        assert record.scopes == frozenset({"openid", "profile"})

    def test_it_lists_nobody_elses(self):
        """The whole store is walked, so this is the check that the walk
        filters rather than merely iterates."""
        self.store.record("bob", "app", "openid")

        assert self.store.for_user("alice") == []

    def test_the_newest_agreement_comes_first(self):
        """Which is the order the screen wants: what did I authorize most
        recently, and did I mean to."""
        old = ConsentRecord({"openid"}, datetime.now(UTC) - timedelta(days=30))
        self.store._grants[("alice", "old-app")] = old
        self.store.record("alice", "new-app", "openid")

        assert [c for c, _ in self.store.for_user("alice")] == [
            "new-app",
            "old-app",
        ]

    def test_two_granted_in_the_same_moment_still_have_an_order(self):
        """Which the demo stack manages routinely, and an unstable listing
        reorders itself under the reader between refreshes."""
        stamp = datetime.now(UTC)
        self.store._grants[("alice", "b-app")] = ConsentRecord({"openid"}, stamp)
        self.store._grants[("alice", "a-app")] = ConsentRecord({"openid"}, stamp)

        assert [c for c, _ in self.store.for_user("alice")] == ["a-app", "b-app"]

    def test_forgetting_removes_the_agreement(self):
        self.store.record("alice", "app", "openid")

        assert self.store.forget("alice", "app") is True
        assert self.store.granted("alice", "app", "openid") is False

    def test_forgetting_what_is_not_there_is_not_an_error(self):
        """What a second withdrawal of the same grant looks like. A caller
        that treats it as a failure turns a double-click into one."""
        assert self.store.forget("alice", "app") is False

    def test_forgetting_leaves_the_other_agreements_alone(self):
        self.store.record("alice", "app", "openid")
        self.store.record("alice", "kiosk", "openid")

        self.store.forget("alice", "app")

        assert [c for c, _ in self.store.for_user("alice")] == ["kiosk"]

    def test_forgetting_does_not_block_the_client(self):
        """The user said "not any more", not "never again". Blocking is the
        operator's action on the registry, not this one."""
        self.store.record("alice", "app", "openid")
        self.store.forget("alice", "app")

        self.store.record("alice", "app", "openid")

        assert self.store.granted("alice", "app", "openid") is True


class TestTheListing:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, clients, plugin, userid) -> None:
        self.portal = portal
        self.plugin = plugin
        self.userid = userid
        self.plugin.consent.record(userid, "app", "openid profile")

    def test_it_lists_what_this_user_authorized(self):
        body = listing(self.portal)

        assert [item["client_id"] for item in body["items"]] == ["app"]

    def test_it_names_the_application_the_way_the_person_saw_it(self):
        """A client id is what the operator typed; the title is what the
        consent screen said."""
        assert listing(self.portal)["items"][0]["title"] == "Example App"

    def test_it_says_when_they_agreed(self):
        assert listing(self.portal)["items"][0]["granted_at"]

    def test_it_says_what_each_scope_releases(self):
        """ "profile" tells the person nothing. The claims are what they
        actually agreed to hand over."""
        scopes = listing(self.portal)["items"][0]["scopes"]

        profile = next(s for s in scopes if s["id"] == "profile")
        assert "preferred_username" in profile["claims"]

    def test_it_lists_nothing_for_a_user_who_authorized_nothing(self):
        """An empty list, not an error: "nothing" is an answer somebody
        opened this page to get."""
        self.plugin.consent.forget(self.userid, "app")

        assert listing(self.portal)["items"] == []

    def test_an_unregistered_client_is_still_listed(self):
        """The operator removed it; the agreement did not go with it. Hiding
        it would leave a record the user cannot see or withdraw."""
        self.plugin.consent.record(self.userid, "ghost", "openid")

        item = next(
            i for i in listing(self.portal)["items"] if i["client_id"] == "ghost"
        )
        assert item["registered"] is False
        assert item["title"] == "ghost"

    def test_it_says_how_long_access_can_outlive_a_withdrawal(self):
        """An access token is self-encoded with no denylist, so nothing can
        reach one already minted. The screen has to be able to say so."""
        assert listing(self.portal)["access_token_ttl"] == 900

    def test_an_anonymous_caller_is_refused(self):
        logout()

        assert listing(self.portal)["error"]["type"] == "Not authenticated"


class TestWithdrawing:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, clients, plugin, userid) -> None:
        self.portal = portal
        self.plugin = plugin
        self.userid = userid
        self.plugin.consent.record(userid, "app", "openid profile")

    def issue_refresh(self, client_id: str, subject: str | None = None) -> str:
        """Issue a refresh token, as the code grant would.

        :param client_id: The client it is for.
        :param subject: The userid it acts for; the caller by default.
        :returns: The token.
        """
        return self.plugin.refresh.issue(
            client_id=client_id,
            subject=subject or self.userid,
            scope="openid profile",
        )

    def test_the_agreement_is_gone(self):
        withdraw(self.portal, "app")

        assert self.plugin.consent.granted(self.userid, "app", "openid") is False

    def test_the_client_is_asked_again_next_time(self):
        """Which is what withdrawing means: not blocked, asked."""
        withdraw(self.portal, "app")

        assert self.plugin.consent.for_user(self.userid) == []

    def test_it_revokes_what_the_agreement_already_granted(self):
        """The half that makes the other half true. Forgetting the record
        only decides the next authorization; this ends the current one."""
        self.issue_refresh("app")

        body = withdraw(self.portal, "app")

        assert body["refresh_tokens_revoked"] == 1
        assert self.plugin.refresh.count() == 0

    def test_it_revokes_every_session_with_that_client(self):
        """One person can have several: a phone and a laptop are two."""
        self.issue_refresh("app")
        self.issue_refresh("app")

        assert withdraw(self.portal, "app")["refresh_tokens_revoked"] == 2

    def test_it_leaves_the_other_applications_alone(self):
        """The user said no to this one. Ending their sessions everywhere
        would be answering a question they did not ask."""
        self.plugin.consent.record(self.userid, "kiosk", "openid")
        self.issue_refresh("app")
        self.issue_refresh("kiosk")

        withdraw(self.portal, "app")

        # The kiosk's, and only the kiosk's.
        assert self.plugin.refresh.count() == 1
        assert self.plugin.consent.granted(self.userid, "kiosk", "openid") is True

    def test_it_leaves_other_people_alone(self):
        """Same client, different person. Withdrawing is about one account."""
        self.issue_refresh("app", subject="somebody-else")

        body = withdraw(self.portal, "app")

        assert body["refresh_tokens_revoked"] == 0
        assert self.plugin.refresh.count() == 1

    def test_it_says_what_it_could_not_reach(self):
        """Access tokens are self-encoded with no denylist. The window is
        reported so a screen can say it rather than imply a cutoff."""
        assert withdraw(self.portal, "app")["access_token_ttl"] == 900

    def test_withdrawing_twice_is_reported_rather_than_pretended(self):
        """Saying "revoked" for something that was not there tells somebody
        a false thing about their own account."""
        withdraw(self.portal, "app")

        assert withdraw(self.portal, "app")["error"]["type"] == "Not authorized"

    def test_withdrawing_what_was_never_agreed_to_is_refused(self):
        assert withdraw(self.portal, "kiosk")["error"]["type"] == "Not authorized"

    def test_an_unregistered_client_can_still_be_withdrawn(self):
        """The record outlives the registration, so the withdrawal has to
        reach it."""
        self.plugin.consent.record(self.userid, "ghost", "openid")

        assert withdraw(self.portal, "ghost")["client_id"] == "ghost"

    def test_it_needs_a_client_to_withdraw(self):
        assert withdraw(self.portal)["error"]["type"] == "Bad request"

    def test_an_anonymous_caller_is_refused(self):
        logout()

        assert withdraw(self.portal, "app")["error"]["type"] == "Not authenticated"
