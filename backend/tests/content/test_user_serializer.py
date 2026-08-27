"""``@users`` points at the Profile, once the layer put one there.

The core half of this is tested against a site where the extra was never
installed, which is where ``profile_url`` has to answer ``None`` rather than
break. This is the other half.
"""

from . import PROFILE_ID
from pas.plugins.identity.core.serializer import portrait_of
from pas.plugins.identity.core.serializer import profile_url_of
from pas.plugins.identity.core.serializer import source_of
from plone import api
from plone.namedfile.file import NamedBlobImage
from plone.restapi.interfaces import ISerializeToJson
from zope.component import getMultiAdapter

import pytest


#: The smallest valid PNG, so a test never carries a binary fixture file.
PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00"
    b"\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\n"
    b"IDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00"
    b"\x00IEND\xaeB`\x82"
)


pytestmark = pytest.mark.portal(profiles=[PROFILE_ID])


class TestProfileUrl:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, make_profile) -> None:
        self.portal = portal
        self.request = portal.REQUEST
        self.profile = make_profile("alice", email="alice@example.com")

    def serialize(self, userid: str):
        """Return the JSON ``@users`` would answer with.

        :param userid: The user to serialize.
        :returns: The payload.
        """
        member = api.user.get(userid=userid)
        return getMultiAdapter((member, self.request), ISerializeToJson)()

    def test_points_at_the_profile(self):
        """Which is the whole reason the field exists: a client showing a
        user should be able to link to their Profile without knowing where
        this site decided to keep them."""
        assert profile_url_of("alice") == self.profile.absolute_url()

    def test_the_payload_carries_it(self):
        """Through the serializer, not only the helper."""
        assert self.serialize("alice")["profile_url"] == self.profile.absolute_url()

    def test_a_user_without_a_profile_has_none(self):
        """The layer being installed does not mean every user has one: a
        Profile is minted at first login, so an account that has never
        logged in through a provider has no Profile yet."""
        assert profile_url_of("nobody-at-all") is None

    def test_a_profile_without_a_picture_falls_back(self):
        """No picture chosen, so whatever the member portrait holds stands --
        which is where a provider-synced avatar lands."""
        assert portrait_of("alice") is None

    def test_the_profile_picture_wins(self):
        """A picture somebody uploaded beats one a provider supplied."""
        self.profile.image = NamedBlobImage(
            data=PNG, filename="face.png", contentType="image/png"
        )

        assert portrait_of("alice") == (f"{self.profile.absolute_url()}/@@images/image")

    def test_the_payload_carries_the_profile_picture(self):
        """Through the serializer, which is what the avatar reads."""
        self.profile.image = NamedBlobImage(
            data=PNG, filename="face.png", contentType="image/png"
        )

        assert self.serialize("alice")["portrait"].endswith("/@@images/image")

    def test_a_user_with_no_profile_has_no_picture(self):
        """The layer being installed does not give everybody a Profile."""
        assert portrait_of("nobody-at-all") is None

    def test_the_source_is_our_own_plugin(self):
        """A profile-backed userid is enumerated by the profile plugin, and
        PAS stamps that on the record -- the other two enumerators return
        nothing for it, so the answer is unambiguous rather than a race."""
        assert source_of("alice") == "identity_profile"
