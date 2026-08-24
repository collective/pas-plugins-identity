"""What ``@users`` says about a user once this package is installed.

The interesting field is ``source``. It is not derived here: PAS aggregates
its enumeration plugins and stamps ``pluginid`` on the record it returns, so
this reads the answer PAS already resolved to rather than re-running the
resolution and hoping to agree with it.
"""

from .services import USERINFO
from pas.plugins.identity.core.pas import PLUGIN_ID
from pas.plugins.identity.core.serializer import identities_of
from pas.plugins.identity.core.serializer import profile_url_of
from pas.plugins.identity.core.serializer import source_of
from plone import api
from plone.restapi.interfaces import ISerializeToJson
from zope.component import getMultiAdapter

import pytest


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
    def _setup(self, portal, request_, member) -> None:
        self.portal = portal
        self.request = request_
        self.member = member

    def test_none_without_the_profile_layer(self):
        """The layer is optional, so the field answers rather than breaking.

        This test runs on a site where the extra was never installed, which
        is the case a serializer that assumed it would fail on.
        """
        assert profile_url_of(self.member) is None
        assert self.serialize(self.member)["profile_url"] is None
