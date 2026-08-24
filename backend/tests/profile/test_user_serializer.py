"""``@users`` points at the Profile, once the layer put one there.

The core half of this is tested against a site where the extra was never
installed, which is where ``profile_url`` has to answer ``None`` rather than
break. This is the other half.
"""

from . import PROFILE_ID
from pas.plugins.identity.core.serializer import profile_url_of
from pas.plugins.identity.core.serializer import source_of
from plone import api
from plone.restapi.interfaces import ISerializeToJson
from zope.component import getMultiAdapter

import pytest


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

    def test_the_source_is_our_own_plugin(self):
        """A profile-backed userid is enumerated by the profile plugin, and
        PAS stamps that on the record -- the other two enumerators return
        nothing for it, so the answer is unambiguous rather than a race."""
        assert source_of("alice") == "identity_profile"
