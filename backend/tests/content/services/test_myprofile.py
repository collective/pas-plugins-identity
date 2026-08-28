"""``@my-profile`` -- the first-login routing question."""

from .. import PROFILE_ID
from pas.plugins.identity.content.services.myprofile import MyProfileGet
from pas.plugins.identity.core.pas import PLUGIN_ID as CORE_PLUGIN_ID
from plone import api
from plone.app.testing import logout
from plone.app.testing import TEST_USER_ID

import pytest


pytestmark = pytest.mark.portal(profiles=[PROFILE_ID])


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


class TestTheAddressesOnOffer:
    """What the form asks with, when nobody has picked an address yet.

    A provider offering several addresses -- GitHub returns every one on the
    account -- has not said which the person is here as, and picking for them
    decides which existing account a verified-email link would attach to. So
    the driver carries the list, the profile is minted without an address and
    is therefore `incomplete`, and this is how the form the gate holds the
    user on learns what to offer.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, portal, service, make_profile) -> None:
        self.portal = portal
        self.service = service
        self.profile = make_profile(TEST_USER_ID)
        self.store = portal.acl_users[CORE_PLUGIN_ID].store

    def link(self, provider: str, subject: str, choices) -> None:
        """Record an identity offering these addresses.

        :param provider: Provider id.
        :param subject: Provider-side subject.
        :param choices: What its driver carried forward.
        """
        self.store.add(provider, subject, TEST_USER_ID, {"email_choices": choices})

    def test_none_when_nothing_offers_any(self):
        """Every provider that sends one address, and every user who has
        already answered, looks like this."""
        assert self.service.reply()["email_choices"] == []

    def test_the_offered_addresses_are_reported(self):
        self.link(
            "github",
            "1",
            (
                {"address": "me@example.com", "verified": True, "primary": True},
                {"address": "old@example.com", "verified": False, "primary": False},
            ),
        )

        addresses = [c["address"] for c in self.service.reply()["email_choices"]]

        assert addresses == ["me@example.com", "old@example.com"]

    def test_each_says_where_it_came_from(self):
        """So the form can tell the user why it is asking."""
        self.link("github", "1", ({"address": "me@example.com", "verified": True},))

        assert self.service.reply()["email_choices"][0]["provider"] == "github"

    def test_the_providers_verification_claim_is_carried(self):
        """Carried to be shown, never to be acted on: only an address this
        site confirmed with a magic link counts as verified here."""
        self.link("github", "1", ({"address": "me@example.com", "verified": True},))

        assert self.service.reply()["email_choices"][0]["verified"] is True

    def test_two_providers_are_gathered_into_one_question(self):
        """The form asks once, however many providers offered something."""
        self.link("github", "1", ({"address": "me@example.com", "verified": True},))
        self.link("gitlab", "2", ({"address": "work@example.com", "verified": True},))

        addresses = {c["address"] for c in self.service.reply()["email_choices"]}

        assert addresses == {"me@example.com", "work@example.com"}

    def test_the_same_address_from_two_providers_is_one_answer(self):
        """Not something to make the user resolve."""
        self.link("github", "1", ({"address": "me@example.com", "verified": True},))
        self.link("gitlab", "2", ({"address": "me@example.com", "verified": True},))

        assert len(self.service.reply()["email_choices"]) == 1

    def test_an_identity_that_carried_nothing_is_not_an_error(self):
        """Every provider but GitHub, and GitHub before this existed."""
        self.store.add("dex", "3", TEST_USER_ID, {"email": "someone@example.com"})

        assert self.service.reply()["email_choices"] == []
