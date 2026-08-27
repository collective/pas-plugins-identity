"""``@my-profile`` -- the first-login routing question."""

from .. import PROFILE_ID
from pas.plugins.identity.content.services.myprofile import MyProfileGet
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
