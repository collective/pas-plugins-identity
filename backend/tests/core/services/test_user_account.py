"""``GET @user-account/<userid>`` -- the administrator's view of one account.

Two questions the users control panel could not answer: which providers this
person has configured, and when they last got in. Both existed somewhere --
the identity store and the audit log -- and neither was reachable per user
without reading everything.
"""

from pas.plugins.identity.core import audit
from pas.plugins.identity.core.controlpanel import ProviderConfig
from pas.plugins.identity.core.controlpanel import set_providers
from pas.plugins.identity.core.pas import PLUGIN_ID as CORE_PLUGIN_ID
from pas.plugins.identity.core.services.useraccount import audit_entries
from pas.plugins.identity.core.services.useraccount.get import UserAccountGet
from plone import api
from plone.app.testing import login
from plone.app.testing import logout
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.app.testing import TEST_USER_NAME

import pytest


#: A provider to link identities against.
PROVIDER = {
    "id": "github",
    "driver": "github",
    "title": "GitHub",
    "enabled": True,
    "background_color": "#24292f",
    "config": {"client_id": "Iv1.abc", "client_secret": "gho_secret"},
}

SUBJECT = "12345"


class UserAccountCase:
    """Drives the service directly, as the other service tests do."""

    def account(self, *segments, **form) -> dict:
        """GET one user's account summary.

        :param segments: Path segments after the endpoint name.
        :param form: Query-string parameters.
        :returns: The service's reply.
        """
        self.request.form.update(form)
        service = UserAccountGet(self.portal, self.request)
        service.segments = list(segments)
        return service.reply()

    def status(self) -> int:
        """Return the status the last reply set.

        :returns: The HTTP status.
        """
        return self.request.response.getStatus()

    def plugin(self):
        """Return the core PAS plugin.

        :returns: The plugin.
        """
        return api.portal.get_tool("acl_users")[CORE_PLUGIN_ID]


class TestTheIdentities(UserAccountCase):
    @pytest.fixture(autouse=True)
    def _setup(self, portal, request_, make_profile) -> None:
        self.portal = portal
        self.request = request_
        setRoles(portal, TEST_USER_ID, ["Manager"])
        login(portal, TEST_USER_NAME)
        set_providers([ProviderConfig.deserialize(PROVIDER)])
        self.profile = make_profile(TEST_USER_ID, email="alice@example.com")
        self.plugin().link(TEST_USER_ID, "github", SUBJECT, {})

    def test_the_identity_is_reported(self):
        """The first of the two questions."""
        entry = self.account(TEST_USER_ID)["identities"][0]

        assert entry["provider"] == "github"
        assert entry["subject"] == SUBJECT

    def test_the_provider_is_named(self):
        """``@users`` already carries the id; an administrator reading a row
        wants the name."""
        assert self.account(TEST_USER_ID)["identities"][0]["title"] == "GitHub"

    def test_the_provider_style_comes_with_it(self):
        """So a panel can show the same button the person signs in with."""
        entry = self.account(TEST_USER_ID)["identities"][0]

        assert entry["background_color"] == "#24292f"

    def test_a_disabled_provider_is_flagged(self):
        """An identity against a provider somebody turned off looks like a
        broken login and reads like nothing."""
        set_providers([ProviderConfig.deserialize({**PROVIDER, "enabled": False})])

        entry = self.account(TEST_USER_ID)["identities"][0]

        assert entry["provider_configured"] is True
        assert entry["provider_enabled"] is False

    def test_a_deleted_provider_is_a_third_state(self):
        """Not configured at all, which is what a provider deleted out from
        under a stored identity looks like."""
        set_providers([])

        entry = self.account(TEST_USER_ID)["identities"][0]

        assert entry["provider_configured"] is False
        assert entry["title"] == "github"

    def test_a_user_with_none_reports_an_empty_list(self):
        """A password account is not an error."""
        with api.env.adopt_roles(["Manager"]):
            api.user.create(username="bob", email="bob@example.com")

        assert self.account("bob")["identities"] == []

    def test_the_profile_is_linked(self):
        """So the panel can send an administrator to the person's record."""
        assert self.account(TEST_USER_ID)["profile_url"].endswith(
            f"/identity-profiles/{TEST_USER_ID}"
        )


class TestTheLastLogin(UserAccountCase):
    @pytest.fixture(autouse=True)
    def _setup(self, portal, request_, make_profile) -> None:
        self.portal = portal
        self.request = request_
        setRoles(portal, TEST_USER_ID, ["Manager"])
        login(portal, TEST_USER_NAME)
        make_profile(TEST_USER_ID, email="alice@example.com")

    def record(self, event: str, success: bool = True) -> None:
        """Write one audit entry for the test user.

        :param event: The event name.
        :param success: Whether it succeeded.
        """
        audit.record(TEST_USER_ID, event, "github", success)

    def test_nothing_recorded_is_null(self):
        """Not the same as "never logged in": the log is bounded, and a
        dormant account has had its entries purged."""
        assert self.account(TEST_USER_ID)["last_authenticated"] is None

    def test_a_successful_login_is_reported(self):
        """The second of the two questions, and nothing in Plone records
        it."""
        self.record(audit.AUTHENTICATED)

        assert self.account(TEST_USER_ID)["last_authenticated"] is not None

    def test_a_failure_does_not_count(self):
        """ "Last authenticated" is about getting in."""
        self.record(audit.AUTHENTICATED, success=False)

        assert self.account(TEST_USER_ID)["last_authenticated"] is None

    def test_another_event_does_not_count(self):
        """Linking an identity is not signing in."""
        self.record(audit.IDENTITY_LINKED)

        assert self.account(TEST_USER_ID)["last_authenticated"] is None

    def test_the_most_recent_one_wins(self):
        """Entries come back newest first, so the first match is the
        answer."""
        self.record(audit.AUTHENTICATED)
        self.record(audit.AUTHENTICATED)

        reported = self.account(TEST_USER_ID)["last_authenticated"]
        newest = max(
            entry.timestamp
            for entry in audit_entries(TEST_USER_ID)
            if entry.event == audit.AUTHENTICATED
        )

        assert reported == newest.isoformat()

    def test_recent_events_come_with_it(self):
        """So the panel can show *how* they got in, not only when."""
        self.record(audit.AUTHENTICATED)

        body = self.account(TEST_USER_ID)

        assert body["events_total"] == 1
        assert body["events"][0]["event"] == audit.AUTHENTICATED

    def test_the_event_list_is_capped(self):
        """The log is bounded per user; this bounds the response."""
        for _ in range(12):
            self.record(audit.AUTHENTICATED)

        body = self.account(TEST_USER_ID, events=5)

        assert body["events_total"] == 12
        assert len(body["events"]) == 5

    def test_a_nonsense_limit_falls_back(self):
        """A query string is whatever somebody typed."""
        self.record(audit.AUTHENTICATED)

        assert len(self.account(TEST_USER_ID, events="lots")["events"]) == 1


class TestTheAddresses(UserAccountCase):
    @pytest.fixture(autouse=True)
    def _setup(self, portal, request_, make_profile) -> None:
        self.portal = portal
        self.request = request_
        setRoles(portal, TEST_USER_ID, ["Manager"])
        login(portal, TEST_USER_NAME)
        self.profile = make_profile(TEST_USER_ID, email="alice@example.com")

    def test_the_addresses_are_reported(self):
        """Which addresses an account can be matched on is part of the same
        question as which providers it uses."""
        assert [e["address"] for e in self.account(TEST_USER_ID)["emails"]] == [
            "alice@example.com"
        ]

    def test_verification_is_reported(self):
        """A verified address is what auto-linking attaches a new provider
        account to, so an administrator needs to see which are proved."""
        self.plugin().link(TEST_USER_ID, "email", "alice@example.com", {})

        assert self.account(TEST_USER_ID)["emails"][0]["verified"] is True

    def test_a_user_without_a_profile_reports_none(self):
        """An account that predates this add-on. Created straight in
        ``source_users``, because ``api.user.create`` mints a Profile on a
        site that keeps users as content -- which is every site with this
        add-on installed."""
        self.portal.acl_users.source_users.addUser("bob", "bob", "placeholder-password")

        assert self.account("bob")["emails"] == []


class TestAccess(UserAccountCase):
    @pytest.fixture(autouse=True)
    def _setup(self, portal, request_, make_profile) -> None:
        self.portal = portal
        self.request = request_
        setRoles(portal, TEST_USER_ID, ["Manager"])
        login(portal, TEST_USER_NAME)
        make_profile(TEST_USER_ID, email="alice@example.com")
        with api.env.adopt_roles(["Manager"]):
            api.user.create(
                username="bob", email="bob@example.com", password="bob-secret-1"
            )

    def test_anonymous_is_refused(self):
        """This is an account's authentication history."""
        logout()

        self.account(TEST_USER_ID)

        assert self.status() == 401

    def test_a_manager_may_read_anybody(self):
        """The whole point: it is a users control panel action."""
        self.account("bob")

        assert self.status() == 200

    def test_an_ordinary_user_may_not_read_somebody_else(self):
        """Somebody else's providers and login times are not theirs."""
        setRoles(self.portal, TEST_USER_ID, ["Member"])

        self.account("bob")

        assert self.status() == 403

    def test_an_ordinary_user_may_read_their_own(self):
        """The same facts are already theirs through @identities and
        @audit-log; refusing here would only mean the frontend needing two
        code paths to draw one panel."""
        setRoles(self.portal, TEST_USER_ID, ["Member"])

        self.account(TEST_USER_ID)

        assert self.status() == 200

    def test_the_url_is_traversed_rather_than_supplied(self):
        """The service is published, so the userid arrives as a segment."""
        service = UserAccountGet(self.portal, self.request)
        service.publishTraverse(self.request, "alice")

        assert service.segments == ["alice"]

    def test_an_unknown_user_is_a_404(self):
        self.account("nobody")

        assert self.status() == 404

    def test_a_missing_userid_is_a_400(self):
        """The endpoint is about one account."""
        self.account()

        assert self.status() == 400
