"""``PATCH @users/<id>`` -- where a portrait upload actually lands.

The read side already preferred the Profile's picture. Until this override
the write side did not: an upload went to ``portal_memberdata``, and the
reader kept answering with the Profile's empty field. The bug looked like an
upload that succeeded and changed nothing, which is why the tests here assert
on *both* stores rather than only on the one that was written.
"""

from .. import PROFILE_ID
from base64 import b64encode
from pas.plugins.identity.content.services.users import ProfileUsersPatch
from pas.plugins.identity.core.serializer import portrait_of
from plone import api

import pytest


#: The smallest valid PNG, so a test never carries a binary fixture file.
PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00"
    b"\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\n"
    b"IDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00"
    b"\x00IEND\xaeB`\x82"
)

pytestmark = pytest.mark.portal(profiles=[PROFILE_ID])


def upload(data: bytes = PNG) -> dict:
    """Build the portrait mapping Volto sends.

    :param data: The image bytes.
    :returns: The mapping, base64-encoded as the API expects.
    """
    return {
        "data": b64encode(data).decode("ascii"),
        "encoding": "base64",
        "content-type": "image/png",
        "filename": "me.png",
    }


def stored_on_the_member(userid: str):
    """Return the member portrait, or ``None`` when it is the default.

    :param userid: The user to look at.
    :returns: The stored image, or ``None``.
    """
    from Products.PlonePAS.tools.membership import default_portrait

    portal = api.portal.get()
    portrait = api.portal.get_tool("portal_membership").getPersonalPortrait(userid)
    if portrait is None or portrait.getId() == default_portrait.split("/")[-1]:
        return None
    return portrait if portrait.aq_parent != portal else None


class TestAUserWithAProfile:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, make_profile) -> None:
        self.portal = portal
        self.profile = make_profile("alice", email="alice@example.com")
        self.service = ProfileUsersPatch(portal, portal.REQUEST)
        self.user = api.user.get(userid="alice")

    def test_the_picture_lands_on_the_profile(self):
        """The whole bug: it used to land in memberdata, which the reader
        consults second."""
        self.service.set_member_portrait(self.user, upload())

        assert self.profile.image is not None
        assert self.profile.image.data == PNG

    def test_the_content_type_survives(self):
        """A blob served back as ``application/octet-stream`` is a download
        rather than a picture."""
        self.service.set_member_portrait(self.user, upload())

        assert self.profile.image.contentType == "image/png"

    def test_the_reader_now_answers_with_it(self):
        """Storing it where nothing reads it is the failure this fixes, so
        the test goes all the way to the read path."""
        self.service.set_member_portrait(self.user, upload())

        assert portrait_of("alice") == (f"{self.profile.absolute_url()}/@@images/image")

    def test_it_does_not_also_write_the_member(self):
        """One store per user. Writing both would leave two pictures to
        disagree, and the fallback would quietly stop being a fallback."""
        self.service.set_member_portrait(self.user, upload())

        assert stored_on_the_member("alice") is None

    def test_removing_it_clears_the_profile(self):
        """And leaves the user with no picture at all rather than with the
        one they replaced."""
        self.service.set_member_portrait(self.user, upload())

        self.service.set_member_portrait(self.user, None)

        assert self.profile.image is None
        assert portrait_of("alice") is None

    def test_removing_a_picture_that_is_not_there_is_not_an_error(self):
        """A preferences form that submits an empty portrait field."""
        self.service.set_member_portrait(self.user, None)

        assert self.profile.image is None


class TestAUserWithoutAProfile:
    """The site's own ``admin``, or an account from before this layer."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal
        self.service = ProfileUsersPatch(portal, portal.REQUEST)
        self.user = api.user.get(userid=api.user.get_current().getId())

    def test_the_member_portrait_still_works(self):
        """Stock behaviour, because there is no Profile to be authoritative
        and nothing here should invent one."""
        self.service.set_member_portrait(self.user, upload())

        assert stored_on_the_member(self.user.getId()) is not None
