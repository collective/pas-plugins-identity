"""A provider's avatar, on a site whose users are Profiles.

The layer decided that a user's picture lives on their Profile, and only the
*upload* path honoured it: an avatar synced at login went to
``portal_memberdata``, so the Profile content object showed an empty picture
field on a site that was displaying a picture. These are the tests for the
other writer, and for the precedence between the two -- a picture somebody
chose beats one a provider supplied, whichever wrote last.
"""

from . import PROFILE_ID
from pas.plugins.identity.core import portraits
from pas.plugins.identity.core.serializer import portrait_of
from pas.plugins.identity.profile.subscribers import remembered_picture_url
from plone import api
from plone.namedfile.file import NamedBlobImage

import pytest


pytestmark = pytest.mark.portal(profiles=[PROFILE_ID])

#: The smallest valid PNG, so a test never carries a binary fixture file.
PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00"
    b"\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\n"
    b"IDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00"
    b"\x00IEND\xaeB`\x82"
)

#: A different one, so "it was replaced" is distinguishable from "it stayed".
OTHER_PNG = PNG.replace(b"IDATx\x9cc\x00\x01", b"IDATx\x9cc\x00\x02")


def member_portrait(userid: str):
    """Return the stored member portrait, or ``None`` for the default.

    :param userid: The user to look at.
    :returns: The image, or ``None``.
    """
    from Products.PlonePAS.tools.membership import default_portrait

    portrait = api.portal.get_tool("portal_membership").getPersonalPortrait(userid)
    if portrait is None or portrait.getId() == default_portrait.split("/")[-1]:
        return None
    return portrait


class TestAUserWithAProfile:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, make_profile) -> None:
        self.portal = portal
        self.profile = make_profile("alice", email="alice@example.com")
        api.portal.set_registry_record(portraits.ENABLED_RECORD, True)

    def store(self, data: bytes = PNG, url: str = "https://cdn/a.png") -> None:
        """Store an avatar the way a login does.

        :param data: The image bytes.
        :param url: The claim they came from.
        """
        portraits.store("alice", data, url)

    def test_the_picture_lands_on_the_profile(self):
        """The bug: it went to memberdata, and the Profile -- which the
        reader consults first -- kept showing an empty field."""
        self.store()

        assert self.profile.picture is not None
        assert self.profile.picture.data == PNG

    def test_it_does_not_also_write_the_member(self):
        """One store per user. Two pictures are two things to disagree."""
        self.store()

        assert member_portrait("alice") is None

    def test_the_reader_answers_with_it(self):
        """Storing it where nothing reads it is the failure being fixed, so
        the test goes all the way to the read path."""
        self.store()

        assert portrait_of("alice") == (
            f"{self.profile.absolute_url()}/@@images/picture"
        )

    def test_the_media_type_is_read_from_the_bytes(self):
        """A blob served back as ``application/octet-stream`` is a download
        rather than a picture."""
        self.store()

        assert self.profile.picture.contentType == "image/png"

    def test_the_provider_may_replace_its_own_picture(self):
        """Changing your avatar at the provider should change it here."""
        self.store()

        self.store(OTHER_PNG, "https://cdn/b.png")

        assert self.profile.picture.data == OTHER_PNG

    def test_it_never_replaces_a_picture_the_user_chose(self):
        """The precedence this layer has always claimed, now enforced
        against the writer that could break it."""
        self.profile.picture = NamedBlobImage(
            data=PNG, contentType="image/png", filename="mine.png"
        )

        self.store(OTHER_PNG)

        assert self.profile.picture.data == PNG

    def test_a_refused_picture_still_becomes_the_member_portrait(self):
        """Refusing is not an error: the avatar is kept where it went before
        this layer existed, as the fallback nobody sees."""
        self.profile.picture = NamedBlobImage(
            data=PNG, contentType="image/png", filename="mine.png"
        )

        self.store(OTHER_PNG)

        assert member_portrait("alice") is not None

    def test_uploading_your_own_ends_the_providers_claim(self):
        """A picture the provider put there, then replaced by the user. The
        provider must not take it back at the next login."""
        from pas.plugins.identity.profile.services.users import ProfileUsersPatch

        self.store()
        assert remembered_picture_url(self.profile)

        service = ProfileUsersPatch(self.portal, self.portal.REQUEST)
        service.set_member_portrait(
            api.user.get(userid="alice"),
            {"data": OTHER_PNG, "content-type": "image/png", "filename": "me.png"},
        )

        assert remembered_picture_url(self.profile) == ""
        self.store(PNG, "https://cdn/c.png")
        assert self.profile.picture.data == OTHER_PNG

    def test_clearing_it_lets_a_provider_fill_it_again(self):
        """Removing your picture is not a refusal of every future one."""
        from pas.plugins.identity.profile.services.users import ProfileUsersPatch

        service = ProfileUsersPatch(self.portal, self.portal.REQUEST)
        service.set_member_portrait(
            api.user.get(userid="alice"),
            {"data": PNG, "content-type": "image/png", "filename": "me.png"},
        )
        service.set_member_portrait(api.user.get(userid="alice"), None)

        self.store(OTHER_PNG)

        assert self.profile.picture.data == OTHER_PNG


class TestAUserWithoutAProfile:
    """The site's own ``admin``, or an account from before the layer."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal
        self.userid = api.user.get_current().getId()
        api.portal.set_registry_record(portraits.ENABLED_RECORD, True)

    def test_the_member_portrait_still_answers(self):
        """There is no Profile to be authoritative, and nothing here should
        invent one."""
        portraits.store(self.userid, PNG, "https://cdn/a.png")

        assert member_portrait(self.userid) is not None
        assert portrait_of(self.userid) is None
