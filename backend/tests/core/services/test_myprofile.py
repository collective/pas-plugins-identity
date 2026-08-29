"""``@my-profile`` -- the first-login routing question."""

from pas.plugins.identity.core.pas import PLUGIN_ID as CORE_PLUGIN_ID
from pas.plugins.identity.core.services.myprofile import MyProfileGet
from plone import api
from plone.app.testing import logout
from plone.app.testing import TEST_USER_ID
from zope.lifecycleevent import modified

import pytest


@pytest.fixture
def service(portal):
    """The service, constructed directly.

    :param portal: The Plone site.
    :returns: The service.
    """
    return MyProfileGet(portal, portal.REQUEST)


class TestAnonymous:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, service) -> None:
        self.portal = portal
        self.service = service

    def test_refused(self):
        """There is no "my" without a "me"."""
        logout()

        assert self.service.reply()["error"]["type"] == "Not authenticated"

    def test_status_is_401(self):
        """A JSON body, not a login form: the caller is a frontend."""
        logout()

        self.service.reply()

        assert self.portal.REQUEST.response.getStatus() == 401


class TestWithoutAProfile:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, service) -> None:
        self.portal = portal
        self.service = service

    def test_profile_is_null(self):
        """A user the layer has not minted one for yet."""
        assert self.service.reply()["profile"] is None

    def test_review_state_is_null(self):
        """Nothing to route on."""
        assert self.service.reply()["review_state"] is None

    def test_userid_is_still_reported(self):
        """The frontend should not need a second call to learn who it is."""
        assert self.service.reply()["userid"] == TEST_USER_ID


class TestWithAProfile:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, service, make_profile) -> None:
        self.portal = portal
        self.service = service
        self.make_profile = make_profile

    def test_url_is_reported(self):
        """Where Volto sends the user."""
        profile = self.make_profile(TEST_USER_ID)

        assert self.service.reply()["profile"] == profile.absolute_url()

    def test_incomplete_is_reported(self):
        """Which is what triggers the first-login prompt."""
        self.make_profile(TEST_USER_ID)

        assert self.service.reply()["review_state"] == "incomplete"

    def test_complete_is_reflected(self):
        """And what stops it appearing again."""
        profile = self.make_profile(TEST_USER_ID)
        api.content.transition(obj=profile, transition="complete")

        assert self.service.reply()["review_state"] == "complete"

    def test_somebody_elses_profile_is_not_reported(self):
        """ "My" means mine."""
        self.make_profile("someone-else")

        assert self.service.reply()["profile"] is None

    def test_id_is_the_service_url(self):
        """restapi convention."""
        self.make_profile(TEST_USER_ID)

        assert (
            self.service.reply()["@id"] == f"{self.portal.absolute_url()}/@my-profile"
        )


class TestTheProfilesOwnAddresses:
    """What the account page renders the verify buttons from.

    Deliberately separate from ``email_choices``: one is what the person has
    claimed, the other is what a provider offered and nobody has picked from.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, portal, service, make_profile) -> None:
        self.portal = portal
        self.service = service
        self.profile = make_profile(TEST_USER_ID, email="alice@example.com")

    def addresses(self) -> list:
        """Return the reported addresses.

        :returns: The ``emails`` entries.
        """
        return self.service.reply()["emails"]

    def test_the_profiles_addresses_are_reported(self):
        """In the person's own order, which is the order they mean."""
        self.profile.emails = ("alice@example.org", "alice@example.com")
        modified(self.profile)

        assert [entry["address"] for entry in self.addresses()] == [
            "alice@example.org",
            "alice@example.com",
        ]

    def test_an_unverified_address_says_so(self):
        """Adding an address does not prove it."""
        assert self.addresses()[0]["verified"] is False

    def test_a_verified_address_says_so(self):
        """A magic link is the only thing that changes this."""
        api.portal.get_tool("acl_users")[CORE_PLUGIN_ID].link(
            TEST_USER_ID, "email", "alice@example.com", {}
        )

        assert self.addresses()[0]["verified"] is True

    def test_the_preferred_one_is_marked(self):
        """So a page can show which address answers for this person without
        reimplementing the rule that picks it."""
        self.profile.emails = ("alice@example.org", "alice@example.com")
        modified(self.profile)
        api.portal.get_tool("acl_users")[CORE_PLUGIN_ID].link(
            TEST_USER_ID, "email", "alice@example.com", {}
        )

        preferred = [e["address"] for e in self.addresses() if e["preferred"]]

        assert preferred == ["alice@example.com"]

    def test_a_profile_with_none_reports_an_empty_list(self):
        """Never ``None``: the frontend iterates it."""
        self.profile.emails = ()
        modified(self.profile)

        assert self.addresses() == []


class TestNotInstalled:
    def test_answers_usably_without_the_layer(self, integration):
        """A frontend asking every site the same question deserves an answer.

        A 404 here would have to be special-cased by the caller, and "there
        are no profiles in this site" is a perfectly good answer.
        """
        site = integration["portal"]

        body = MyProfileGet(site, site.REQUEST).reply()

        assert body["profile"] is None
        assert body["review_state"] is None
