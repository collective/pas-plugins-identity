"""What ``@users`` says about a user once this package is installed.

The interesting field is ``source``. It is not derived here: PAS aggregates
its enumeration plugins and stamps ``pluginid`` on the record it returns, so
this reads the answer PAS already resolved to rather than re-running the
resolution and hoping to agree with it.
"""

from ..services import USERINFO
from pas.plugins.identity.core.pas import PLUGIN_ID
from pas.plugins.identity.core.serializers.user import identities_of
from pas.plugins.identity.core.serializers.user import portrait_of
from pas.plugins.identity.core.serializers.user import profile_url_of
from pas.plugins.identity.core.serializers.user import source_of
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


class SerializerCase:
    """Serializes a member the way ``@users`` does."""

    def serialize(self, userid: str):
        """Return the JSON ``@users`` would answer with.

        :param userid: The user to serialize.
        :returns: The payload.
        """
        member = api.user.get(userid=userid)
        return getMultiAdapter((member, self.request), ISerializeToJson)()

    def plugin(self):
        """Return the identity plugin.

        :returns: The plugin installed in this site.
        """
        return api.portal.get_tool("acl_users")[PLUGIN_ID]


class TestSource(SerializerCase):
    @pytest.fixture(autouse=True)
    def _setup(self, portal, request_, member) -> None:
        self.portal = portal
        self.request = request_
        self.member = member

    def test_names_the_plugin_the_userid_came_from(self):
        """A password user belongs to Plone's own user source."""
        assert self.serialize(self.member)["source"] == "source_users"

    def test_the_source_is_what_pas_itself_resolved_to(self):
        """Read rather than derived: the helper and the payload agree
        because both come from the same aggregated record."""
        assert self.serialize(self.member)["source"] == source_of(self.member)

    def test_an_unknown_userid_has_no_source(self):
        """No plugin claims it, so there is nothing to name -- and saying so
        is better than guessing at the first plugin in the list."""
        assert source_of("nobody-at-all") is None

    def test_a_longer_userid_is_not_matched(self):
        """``searchUsers`` is a substring search by default.

        Without ``exact_match`` this is the bug: asking about ``alice``
        answers about ``alice2`` as readily, and the source reported is
        whichever record happened to come back first.
        """
        assert source_of(self.member[:-1]) is None


class TestIdentities(SerializerCase):
    @pytest.fixture(autouse=True)
    def _setup(self, portal, request_, member, configured) -> None:
        self.portal = portal
        self.request = request_
        self.member = member

    def test_empty_for_a_password_user(self):
        """Nothing linked is an empty list, not a missing key: a client
        rendering "no identities" should not have to tell the two apart."""
        assert self.serialize(self.member)["identities"] == []

    def test_lists_what_is_linked(self):
        """The provider and subject, which is what identifies the link."""
        self.plugin().link(self.member, "dex", USERINFO["sub"], {})

        identities = self.serialize(self.member)["identities"]

        assert len(identities) == 1
        assert identities[0]["provider"] == "dex"
        assert identities[0]["subject"] == USERINFO["sub"]

    def test_carries_when_it_was_linked(self):
        """An administrator looking at an account wants to know since when."""
        self.plugin().link(self.member, "dex", USERINFO["sub"], {})

        assert self.serialize(self.member)["identities"][0]["created"]

    def test_never_linked_reads_as_null_rather_than_missing(self):
        """``last_login`` is None until the identity is actually used."""
        self.plugin().link(self.member, "dex", USERINFO["sub"], {})

        assert self.serialize(self.member)["identities"][0]["last_login"] is None

    def test_no_secret_leaves(self):
        """Claims are stored against an identity and are not part of this."""
        self.plugin().link(self.member, "dex", USERINFO["sub"], {"email": "x@y.z"})

        assert set(self.serialize(self.member)["identities"][0]) == {
            "provider",
            "subject",
            "created",
            "last_login",
        }

    def test_identities_of_agrees_with_the_payload(self):
        """One implementation, two callers."""
        self.plugin().link(self.member, "dex", USERINFO["sub"], {})

        assert self.serialize(self.member)["identities"] == identities_of(self.member)


class TestProfileUrl(SerializerCase):
    @pytest.fixture(autouse=True)
    def _setup(self, portal, request_, make_profile) -> None:
        self.portal = portal
        self.request = request_
        self.profile = make_profile("alice", email="alice@example.com")

    def test_points_at_the_profile(self):
        """Which is the whole reason the field exists: a client showing a
        user should be able to link to their Profile without knowing where
        this site decided to keep them."""
        assert profile_url_of("alice") == self.profile.absolute_url()

    def test_the_payload_carries_it(self):
        """Through the serializer, not only the helper."""
        assert self.serialize("alice")["profile_url"] == self.profile.absolute_url()

    def test_a_user_without_a_profile_has_none(self):
        """Not every userid has one: a Profile is minted when somebody is
        added or first signs in, and a userid nothing ever created has
        none."""
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
        """A userid nothing created has nothing to hold a picture."""
        assert portrait_of("nobody-at-all") is None

    def test_the_source_is_our_own_plugin(self):
        """A profile-backed userid is enumerated by the profile plugin, and
        PAS stamps that on the record -- the other two enumerators return
        nothing for it, so the answer is unambiguous rather than a race."""
        assert source_of("alice") == "identity_profile"
