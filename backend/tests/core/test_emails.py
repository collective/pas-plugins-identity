"""A Profile carries a list of addresses, and ``email`` is derived from it.

The rule under test: ``email`` is the first *verified* address, or the first
address at all. Verified means this site holds an ``email`` identity for it --
what a magic link creates -- and nothing else. A provider asserting
``email_verified`` has never counted anywhere in this package and does not
start counting here.
"""

from pas.plugins.identity.core.emails import clean
from pas.plugins.identity.core.emails import normalize
from pas.plugins.identity.core.pas import PLUGIN_ID as CORE_PLUGIN_ID
from pas.plugins.identity.core.subscribers import get_profile
from plone import api
from plone.app.testing import TEST_USER_ID
from zope.lifecycleevent import modified

import pytest


ADDRESS = "alice@example.com"
OTHER = "alice@example.org"


class TestNormalizing:
    """Applied on the way in, so what is indexed and what is compared are
    the same strings."""

    def test_case_and_space_are_folded(self):
        """A mailbox is not two mailboxes because somebody shift-locked."""
        assert normalize("  Alice@Example.COM ") == "alice@example.com"

    def test_duplicates_collapse(self):
        """Two spellings of one address are one entry."""
        assert clean(["A@x.com", "a@X.com"]) == ("a@x.com",)

    def test_order_is_preserved(self):
        """It is the person's order, and it decides which address wins."""
        assert clean([OTHER, ADDRESS]) == (OTHER, ADDRESS)

    def test_empties_are_dropped(self):
        """A blank row in a form is not an address."""
        assert clean(["", "  ", ADDRESS]) == (ADDRESS,)

    def test_nothing_is_an_empty_tuple(self):
        """Never ``None``: every reader iterates it."""
        assert clean(None) == ()


class ProfileCase:
    """A profile whose addresses and verification can be moved around."""

    def verify(self, address: str, userid: str | None = None) -> None:
        """Record that this site proved an address for a user.

        Through the identity store rather than a flag, because that is what a
        magic link actually writes and what everything else reads.

        :param address: The address to prove.
        :param userid: The owner, defaulting to this test's user.
        """
        store = api.portal.get_tool("acl_users")[CORE_PLUGIN_ID].store
        store.add("email", address, userid or TEST_USER_ID, {})
        modified(self.profile)


class TestOutsideASite:
    """A Profile can be read where there is no portal at all.

    An object being constructed by an import, or a test touching the class
    directly. Nothing is verified in that world, and nothing may raise.
    """

    def test_nothing_is_verified_without_a_portal(self, monkeypatch):
        from pas.plugins.identity.core import emails

        def no_portal(_name):
            raise api.exc.CannotGetPortalError("no site")

        monkeypatch.setattr(emails.api.portal, "get_tool", no_portal)

        assert emails.verified_addresses("alice", (ADDRESS,)) == ()

    def test_the_first_address_still_answers(self, monkeypatch):
        from pas.plugins.identity.core import emails

        def no_portal(_name):
            raise api.exc.CannotGetPortalError("no site")

        monkeypatch.setattr(emails.api.portal, "get_tool", no_portal)

        assert emails.preferred_address("alice", (ADDRESS,)) == ADDRESS


class TestTheDerivedAddress(ProfileCase):
    @pytest.fixture(autouse=True)
    def _setup(self, portal, make_profile) -> None:
        self.portal = portal
        self.profile = make_profile(TEST_USER_ID, email=ADDRESS)

    def test_one_address_is_the_address(self):
        """The common case, and the one every existing test relies on."""
        assert self.profile.email == ADDRESS

    def test_the_first_wins_when_none_is_verified(self):
        """The order is the person's, so the first is their preference."""
        self.profile.emails = (OTHER, ADDRESS)

        assert self.profile.email == OTHER

    def test_a_verified_address_outranks_the_order(self):
        """ "Your preferred address, unless you have proved a better one"."""
        self.profile.emails = (OTHER, ADDRESS)
        self.verify(ADDRESS)

        assert self.profile.email == ADDRESS

    def test_the_first_verified_wins_among_several(self):
        """Order still decides once proof is out of the way."""
        self.profile.emails = (OTHER, ADDRESS)
        self.verify(OTHER)
        self.verify(ADDRESS)

        assert self.profile.email == OTHER

    def test_no_addresses_is_an_empty_string(self):
        """Never ``None``: it is read as a member property and rendered."""
        self.profile.emails = ()

        assert self.profile.email == ""

    def test_somebody_elses_proof_does_not_count(self):
        """The store is keyed on the address, so a check that only asked
        whether the address was verified would hand one person's proof to
        anybody who typed their address."""
        with api.env.adopt_roles(["Manager"]):
            api.user.create(username="mallory", email="mallory@example.com")
        self.profile.emails = (OTHER, ADDRESS)
        self.verify(ADDRESS, userid="mallory")

        assert self.profile.email == OTHER
        assert self.profile.verified_emails == ()


class TestWritingTheDerivedField(ProfileCase):
    """A great deal of code writes ``email``; none of it may be made to fail."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, make_profile) -> None:
        self.portal = portal
        self.profile = make_profile(TEST_USER_ID, email=ADDRESS)

    def test_creating_with_an_address_seeds_the_list(self):
        """Which is how every existing caller keeps working."""
        assert self.profile.emails == (ADDRESS,)

    def test_a_write_moves_the_address_to_the_front(self):
        """The thing being written is *the* address, so it becomes the one
        that answers."""
        self.profile.email = OTHER

        assert self.profile.emails == (OTHER, ADDRESS)
        assert self.profile.email == OTHER

    def test_a_write_never_duplicates(self):
        """Writing what is already there is a no-op, not a second entry."""
        self.profile.email = ADDRESS

        assert self.profile.emails == (ADDRESS,)

    def test_an_empty_write_is_ignored(self):
        """A provider that stopped sending an address has not said the person
        no longer has one, and an empty list is an incomplete profile."""
        self.profile.email = ""

        assert self.profile.emails == (ADDRESS,)

    def test_a_write_is_normalized(self):
        """So the entry matches what the identity store holds."""
        self.profile.email = "  Alice@Example.ORG "

        assert self.profile.emails[0] == OTHER


class TestTheCatalog(ProfileCase):
    """Everything that matters reads these from metadata, not the object."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, make_profile, catalog) -> None:
        self.portal = portal
        self.catalog = catalog
        self.profile = make_profile(TEST_USER_ID, email=ADDRESS)

    def brain(self):
        """Return this profile's brain.

        :returns: The brain.
        """
        return self.catalog.unrestrictedSearchResults(userid=TEST_USER_ID)[0]

    def test_every_address_is_indexed(self):
        """Not only the one ``email`` resolves to: the question asked of the
        index is "whose profile carries this address"."""
        self.profile.emails = (OTHER, ADDRESS)
        modified(self.profile)

        found = self.catalog.unrestrictedSearchResults(emails=ADDRESS)

        assert [b.userid for b in found] == [TEST_USER_ID]

    def test_the_derived_address_is_metadata(self):
        """The property sheet and enumeration are served from brains alone."""
        assert self.brain().email == ADDRESS

    def test_verifying_reindexes_the_profile(self):
        """The one that would otherwise go stale. Confirming a magic link
        writes to the identity store and never touches the Profile, so the
        derived value would be right on the object and wrong everywhere it is
        read."""
        self.profile.emails = (OTHER, ADDRESS)
        modified(self.profile)
        assert self.brain().email == OTHER

        plugin = api.portal.get_tool("acl_users")[CORE_PLUGIN_ID]
        plugin.link(TEST_USER_ID, "email", ADDRESS, {})

        assert self.brain().email == ADDRESS
        assert list(self.brain().verified_emails) == [ADDRESS]

    def test_unlinking_reindexes_it_too(self):
        """The other direction: proof can be taken away."""
        self.profile.emails = (OTHER, ADDRESS)
        modified(self.profile)
        plugin = api.portal.get_tool("acl_users")[CORE_PLUGIN_ID]
        plugin.link(TEST_USER_ID, "email", ADDRESS, {})

        plugin.unlink(TEST_USER_ID, "email", ADDRESS)

        assert self.brain().email == OTHER


class TestThroughTheMemberProperty(ProfileCase):
    """``email`` is still an ordinary Plone member property."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, make_profile) -> None:
        self.portal = portal
        self.profile = make_profile(TEST_USER_ID, email=ADDRESS)

    def test_plone_reads_the_derived_value(self):
        """Every template, every claim and the property map all go through
        this, and none of them has heard of the list."""
        assert api.user.get(userid=TEST_USER_ID).getProperty("email") == ADDRESS

    def test_a_verified_address_changes_what_plone_reads(self):
        """The whole point of deriving it."""
        self.profile.emails = (OTHER, ADDRESS)
        modified(self.profile)
        api.portal.get_tool("acl_users")[CORE_PLUGIN_ID].link(
            TEST_USER_ID, "email", ADDRESS, {}
        )

        assert api.user.get(userid=TEST_USER_ID).getProperty("email") == ADDRESS


class TestGetProfileStillWorks:
    """A guard on the accessor everything else in this module goes through."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, make_profile) -> None:
        self.portal = portal
        make_profile(TEST_USER_ID, email=ADDRESS)

    def test_it_finds_the_profile(self):
        assert get_profile(TEST_USER_ID) is not None
