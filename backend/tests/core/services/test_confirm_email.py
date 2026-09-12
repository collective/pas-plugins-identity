"""``POST @confirm-email`` -- the answer to the question ``@my-profile`` asks."""

from .. import body
from pas.plugins.identity.core.confirmation import ask_if_needed
from pas.plugins.identity.core.confirmation import CONFIRM_RECORD
from pas.plugins.identity.core.confirmation import confirmation_pending
from pas.plugins.identity.core.services.myprofile.confirm import ConfirmEmailPost
from pas.plugins.identity.core.store import EMAIL_PROVIDER
from plone import api
from plone.app.testing import logout
from plone.app.testing import TEST_USER_ID

import pytest


FIRST = "alice@example.com"
SECOND = "alice@example.org"


class ServiceCase:
    """The test user's Profile, holding two verified addresses and asked."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, plugin, make_profile) -> None:
        self.portal = portal
        self.request = portal.REQUEST
        api.portal.set_registry_record(CONFIRM_RECORD, True)
        self.profile = make_profile(TEST_USER_ID, fullname="Alice Liddell")
        for address in (FIRST, SECOND):
            plugin.store.add(EMAIL_PROVIDER, address, TEST_USER_ID, {})
        self.profile.emails = (FIRST, SECOND)
        assert ask_if_needed(self.profile) is True

    def reply(self, data: dict) -> dict:
        """Call the service with a JSON body.

        :param data: The body.
        :returns: The service's reply.
        """
        body(self.request, data)
        return ConfirmEmailPost(self.portal, self.request).reply()

    def status(self) -> int:
        """Return the response status.

        :returns: The status code.
        """
        return self.request.response.getStatus()


class TestTheAnswer(ServiceCase):
    def test_the_address_moves_to_the_front(self):
        self.reply({"email": SECOND})

        assert self.profile.emails == (SECOND, FIRST)

    def test_the_profile_is_released(self):
        self.reply({"email": SECOND})

        assert confirmation_pending(self.profile) is False

    def test_the_body_is_my_profile_as_it_is_now(self):
        """So the frontend routes on the answer without a second call."""
        data = self.reply({"email": SECOND})

        assert data["confirm_email"] is False
        assert data["review_state"] == "complete"
        assert data["emails"][0]["address"] == SECOND

    def test_the_status_is_200(self):
        self.reply({"email": SECOND})

        assert self.status() == 200

    def test_the_owner_needs_no_permission_to_write(self):
        """The write ends in a modification event, and a Member may not be
        allowed the save autoversioning answers it with."""
        with api.env.adopt_roles(["Member"]):
            self.reply({"email": SECOND})

        assert confirmation_pending(self.profile) is False


class TestRefusals(ServiceCase):
    def test_anonymous_is_refused(self):
        logout()

        assert self.reply({"email": SECOND})["error"]["type"] == "Not authenticated"
        assert self.status() == 401

    def test_a_user_without_a_profile_is_refused(self):
        api.content.delete(obj=self.profile)

        assert self.reply({"email": SECOND})["error"]["type"] == "No profile"
        assert self.status() == 404

    @pytest.mark.parametrize("data", [{}, {"email": ""}, {"email": ["x@y.z"]}])
    def test_an_address_is_required(self, data: dict):
        assert self.reply(data)["error"]["type"] == "Missing parameters"
        assert self.status() == 400

    def test_a_profile_nobody_asked_is_a_conflict(self):
        """The endpoint answers a question; reordering addresses is a PATCH."""
        self.reply({"email": SECOND})

        assert self.reply({"email": FIRST})["error"]["type"] == "Nothing to confirm"
        assert self.status() == 409
        assert self.profile.emails == (SECOND, FIRST)

    def test_an_address_that_is_not_verified_is_refused(self):
        data = self.reply({"email": "alice@example.net"})

        assert data["error"]["type"] == "Not a verified address"
        assert self.status() == 400
        assert confirmation_pending(self.profile) is True
