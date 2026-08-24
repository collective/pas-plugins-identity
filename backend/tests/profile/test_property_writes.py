"""Writing a user property lands on the Profile.

The failure this covers was silent in the worst way. ``MemberData``'s
``setMemberProperties`` walks the ordered property sheets and, for each key,
stops at the first sheet that *has* it -- writing through that sheet if it is
mutable and, if it is not, breaking out of the loop having written nowhere.
No exception, no log line, a successful return.

This layer's plugin is deliberately at the top of the ``IPropertiesPlugin``
order, because a Profile has to win a *read* against ``mutable_properties``.
Its sheet used to be immutable, which meant it also won every *write* and
threw it away: the user's own preferences form, the ``@users`` control panel
and the login path all reported success and changed nothing.
"""

from . import PROFILE_ID
from pas.plugins.identity.core.interfaces import IOwnsUserProperties
from pas.plugins.identity.profile.catalog import PROFILE_PORTAL_TYPE
from pas.plugins.identity.profile.catalog import query_catalog
from pas.plugins.identity.profile.pas import PLUGIN_ID
from plone import api
from Products.PlonePAS.interfaces.propertysheets import IMutablePropertySheet

import pytest


pytestmark = pytest.mark.portal(profiles=[PROFILE_ID])


@pytest.fixture
def alice(portal, acl_users):
    """Return alice's Profile, with a PAS user behind it.

    :param portal: The Plone site.
    :param acl_users: The site's PAS instance.
    :returns: The Profile.
    """
    acl_users.source_users.addUser("alice", "alice", "placeholder-password")
    return api.content.create(
        container=portal["identity-profiles"],
        type=PROFILE_PORTAL_TYPE,
        id="alice",
        userid="alice",
        login="alice@example.com",
        fullname="Alice Example",
    )


class TestTheSheetIsWritable:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, alice) -> None:
        self.portal = portal
        self.profile = alice
        self.member = api.user.get(userid="alice")
        self.plugin = portal.acl_users[PLUGIN_ID]

    def test_the_sheet_declares_itself_mutable(self):
        """Which is the single bit ``setMemberProperties`` branches on."""
        sheet = self.plugin.getPropertiesForUser(self.member.getUser())

        assert IMutablePropertySheet.providedBy(sheet)

    def test_a_write_reaches_the_profile(self):
        self.member.setMemberProperties({"location": "Berlin"})

        assert self.profile.location == "Berlin"

    def test_a_write_is_readable_again(self):
        """Reads come from the catalog, so a write nobody reindexed is a
        write nobody can see -- including the form that just made it."""
        self.member.setMemberProperties({"description": "Writes Python."})

        assert api.user.get(userid="alice").getProperty("description") == (
            "Writes Python."
        )

    def test_a_write_reaches_the_catalog(self):
        self.member.setMemberProperties({"fullname": "Alice Liddell"})

        brain = query_catalog().unrestrictedSearchResults(userid="alice")[0]

        assert brain.fullname == "Alice Liddell"

    def test_several_properties_at_once(self):
        self.member.setMemberProperties({
            "fullname": "Alice Liddell",
            "email": "alice@example.org",
            "home_page": "https://alice.example.org",
        })

        assert self.profile.fullname == "Alice Liddell"
        assert self.profile.email == "alice@example.org"
        assert self.profile.home_page == "https://alice.example.org"

    def test_a_user_without_a_profile_is_not_ours_to_serve(self):
        """The sheet is absent rather than empty, so ``setMemberProperties``
        falls through to whatever plugin does store that user."""
        self.portal.acl_users.source_users.addUser("bob", "bob", "placeholder")
        bob = api.user.get(userid="bob")

        assert self.plugin.getPropertiesForUser(bob.getUser()) is None


class TestCoreStandsAside:
    """Both this plugin and core's would otherwise apply the same property
    map to the same fields, and only this one remembers which of them a human
    has since edited."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, alice) -> None:
        self.portal = portal
        self.profile = alice

    def test_the_plugin_claims_ownership(self):
        assert IOwnsUserProperties.providedBy(self.portal.acl_users[PLUGIN_ID])

    def test_core_sees_the_claim(self):
        from pas.plugins.identity.core.pas import PLUGIN_ID as CORE_PLUGIN_ID

        core = self.portal.acl_users[CORE_PLUGIN_ID]

        assert core._properties_owned_elsewhere("alice")

    def test_core_keeps_a_user_it_alone_serves(self):
        """A site can run this layer and still have users it does not give a
        Profile to, and those are core's to write."""
        from pas.plugins.identity.core.pas import PLUGIN_ID as CORE_PLUGIN_ID

        self.portal.acl_users.source_users.addUser("bob", "bob", "placeholder")
        core = self.portal.acl_users[CORE_PLUGIN_ID]

        assert not core._properties_owned_elsewhere("bob")
