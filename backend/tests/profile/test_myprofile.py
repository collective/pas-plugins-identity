"""``@my-profile`` -- the first-login routing question (Gate 6c)."""

from pas.plugins.identity.profile.catalog import PROFILE_PORTAL_TYPE
from pas.plugins.identity.profile.services.myprofile import MyProfileGet
from plone import api
from plone.app.testing import logout
from plone.app.testing import TEST_USER_ID

import pytest


@pytest.fixture
def service(portal):
    """The service, constructed directly.

    :param portal: The Plone site.
    :returns: The service.
    """
    return MyProfileGet(portal, portal.REQUEST)


@pytest.fixture
def make_profile(portal):
    """Return a factory for a Profile belonging to a userid.

    :param portal: The Plone site.
    :returns: Callable taking a userid.
    """

    def factory(userid: str) -> object:
        with api.env.adopt_roles(["Manager"]):
            return api.content.create(
                container=portal["identity-profiles"],
                type=PROFILE_PORTAL_TYPE,
                id=userid,
                userid=userid,
                login=f"{userid}@example.com",
            )

    return factory


class TestAnonymous:
    def test_refused(self, portal, service):
        """There is no "my" without a "me"."""
        logout()

        assert service.reply()["error"]["type"] == "Not authenticated"

    def test_status_is_401(self, portal, service):
        """A JSON body, not a login form: the caller is a frontend."""
        logout()

        service.reply()

        assert portal.REQUEST.response.getStatus() == 401


class TestWithoutAProfile:
    def test_profile_is_null(self, service):
        """A user the layer has not minted one for yet."""
        assert service.reply()["profile"] is None

    def test_review_state_is_null(self, service):
        """Nothing to route on."""
        assert service.reply()["review_state"] is None

    def test_userid_is_still_reported(self, service):
        """The frontend should not need a second call to learn who it is."""
        assert service.reply()["userid"] == TEST_USER_ID


class TestWithAProfile:
    def test_url_is_reported(self, service, make_profile):
        """Where Volto sends the user."""
        profile = make_profile(TEST_USER_ID)

        assert service.reply()["profile"] == profile.absolute_url()

    def test_incomplete_is_reported(self, service, make_profile):
        """Which is what triggers the first-login prompt."""
        make_profile(TEST_USER_ID)

        assert service.reply()["review_state"] == "incomplete"

    def test_complete_is_reflected(self, service, make_profile):
        """And what stops it appearing again."""
        profile = make_profile(TEST_USER_ID)
        with api.env.adopt_roles(["Manager"]):
            api.content.transition(obj=profile, transition="complete")

        assert service.reply()["review_state"] == "complete"

    def test_somebody_elses_profile_is_not_reported(self, service, make_profile):
        """ "My" means mine."""
        make_profile("someone-else")

        assert service.reply()["profile"] is None

    def test_id_is_the_service_url(self, service, portal, make_profile):
        """restapi convention."""
        make_profile(TEST_USER_ID)

        assert service.reply()["@id"] == f"{portal.absolute_url()}/@my-profile"


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
