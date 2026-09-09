"""What the catalog declares, and what actually answers for it.

Issue #39 asked for an explicit indexer per index and per metadata column, each
one asserted. Ten of the fourteen would have returned the attribute the
``IIndexableObject`` wrapper already finds, which restates the attribute name
in a second place rather than checking anything -- and a pass-through indexer
that has itself gone stale is exactly as silent as no indexer at all.

The risk the issue describes is real and is what this module tests instead: a
behavior moves a field, nothing raises, and the index quietly holds nothing.
``core.doctor`` cannot see that one, because it reads the object through the
same attribute the catalog does and finds both sides equally empty. So here a
Profile and a Group are filled in completely and every declared index and
column is required to have landed a value.

The second class is the other half, and it is about which catalog answers.
A Profile is ordinary content, so it is catalogued in ``portal_catalog`` too,
and the two catalogs share five index names. An indexer of ours registered
without naming :class:`IIdentityProfileCatalog` answers for *both* -- that was
the bug fixed in #38, and the test below is what stops the next one arriving
unnoticed.
"""

from pas.plugins.identity.core.catalog import GROUP_METADATA
from pas.plugins.identity.core.catalog import GROUP_PORTAL_TYPE
from pas.plugins.identity.core.catalog import PROFILE_METADATA
from pas.plugins.identity.core.catalog import PROFILE_PORTAL_TYPE
from pas.plugins.identity.core.indexers import site_searchable_text_index
from pas.plugins.identity.core.interfaces import IIdentityProfileCatalog
from pas.plugins.identity.core.pas import PLUGIN_ID
from plone import api
from plone.indexer.interfaces import IIndexer
from Products.ZCatalog.interfaces import IZCatalog
from zope.component import getGlobalSiteManager

import pytest


#: Everything this package's own registrations are compared against. An
#: indexer bound to this is asked only where enumeration reads.
OUR_CATALOG = IIdentityProfileCatalog


def index_data(catalog, portal_type: str) -> dict:
    """Return the indexed values for the one object of a type.

    :param catalog: The catalog to ask.
    :param portal_type: The type whose single object to read.
    :returns: Mapping of index name to what it holds. An index with nothing
        for this object answers with the empty string.
    """
    brain = catalog.unrestrictedSearchResults(portal_type=portal_type)[0]
    return catalog.getIndexDataForRID(brain.getRID())


def our_indexers() -> list:
    """Return every ``IIndexer`` registration made by this package.

    Read from the global site manager rather than from the ZCML, so that the
    answer is what is actually installed. ``@indexer`` replaces the decorated
    function with a factory, so the module-level name is the factory and the
    function it wraps is what says whose registration this is.

    :returns: The adapter registrations.
    """
    return [
        registration
        for registration in getGlobalSiteManager().registeredAdapters()
        if registration.provided is IIndexer
        and getattr(
            getattr(registration.factory, "callable", None), "__module__", ""
        ).startswith("pas.plugins.identity")
    ]


class TestEveryDeclaredIndexAndColumnIsAnswered:
    """Nothing the catalog declares is quietly empty.

    One Profile and one Group, both filled in as completely as the schema
    allows, because the two share a catalog and neither alone covers it: a
    Profile has no ``group_id`` and a Group has no ``login``.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, portal, catalog, make_profile, make_group) -> None:
        self.catalog = catalog
        self.group = make_group("wonderland", description="Down the rabbit hole")
        self.profile = make_profile(
            "alice",
            fullname="Alice Liddell",
            email="alice@example.com",
            emails=["alice@example.com"],
            home_page="https://example.com/alice",
            description="Fond of white rabbits",
            location="Oxford",
            group_ids=["wonderland"],
        )
        # ``verified_emails`` is derived from the identity store rather than
        # written on the Profile, so proving the address is the only way to
        # give that column a value to be checked.
        api.portal.get_tool("acl_users")[PLUGIN_ID].link(
            "alice", "email", "alice@example.com", {}
        )

    def test_every_index_holds_something(self):
        """The declaration this test exists for. An index nothing fills is an
        index every query silently misses, and adding one to the XML is the
        easy half of adding one."""
        profile = index_data(self.catalog, PROFILE_PORTAL_TYPE)
        group = index_data(self.catalog, GROUP_PORTAL_TYPE)

        empty = [
            name
            for name in self.catalog.indexes()
            if not profile.get(name) and not group.get(name)
        ]

        assert empty == []

    def test_every_profile_column_has_a_value(self):
        """A column is what the PAS property sheet and enumeration are served
        from, so an empty one is a user attribute that has stopped existing
        as far as Plone is concerned."""
        brain = self.catalog.unrestrictedSearchResults(portal_type=PROFILE_PORTAL_TYPE)[
            0
        ]

        assert [
            name for name in PROFILE_METADATA if not getattr(brain, name, None)
        ] == []

    def test_every_group_column_has_a_value(self):
        """The same for the other type in the catalog."""
        brain = self.catalog.unrestrictedSearchResults(portal_type=GROUP_PORTAL_TYPE)[0]

        assert [name for name in GROUP_METADATA if not getattr(brain, name, None)] == []

    def test_every_declared_column_is_classified(self):
        """A column absent from both tuples is invisible to ``core.doctor``,
        which checks each type against the columns that mean something for
        it. Adding one to the XML and stopping there produces a column
        nothing ever compares."""
        assert set(PROFILE_METADATA) | set(GROUP_METADATA) == set(self.catalog.schema())


class TestNothingLeaksIntoAnotherCatalog:
    """An indexer of ours answers where enumeration reads, and nowhere else.

    ``@indexer(IUserProfile)`` does not register for one argument: it registers
    for ``(IUserProfile, IZCatalog)``, which is every catalog in the site. That
    is why the leak in #38 was invisible -- the declaration looks narrower than
    it is.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, portal, catalog, make_profile) -> None:
        self.catalog = catalog
        self.site = api.portal.get_tool("portal_catalog")
        self.profile = make_profile("alice", fullname="Alice Liddell")

    def shared(self) -> set[str]:
        """Return the index names both catalogs declare.

        :returns: The overlap.
        """
        return set(self.catalog.indexes()) & set(self.site.indexes())

    def test_the_catalogs_do_share_index_names(self):
        """The premise. Were the overlap empty there would be nothing to leak
        into and the rest of this class would pass for the wrong reason."""
        assert self.shared() == {
            "SearchableText",
            "path",
            "portal_type",
            "review_state",
            "sortable_title",
        }

    def test_the_shared_indexes_still_answer_in_the_site_catalog(self):
        """What a scoping mistake costs, stated as behaviour: a Profile that
        the site catalog can no longer place, type, filter or sort."""
        data = index_data(self.site, PROFILE_PORTAL_TYPE)

        assert [name for name in self.shared() if not data.get(name)] == []

    def test_every_indexer_we_register_names_our_catalog(self):
        """The constraint itself, over every registration rather than over the
        names that happen to overlap today: the site catalog gains indexes as
        Plone does, and an indexer of ours must not become an answer there
        because somebody else added a name."""
        stray = sorted(
            (registration.name, registration.factory.callable.__name__)
            for registration in our_indexers()
            if registration.required[1] is not OUR_CATALOG
            and registration.factory is not site_searchable_text_index
        )

        assert stray == []

    def test_the_one_exception_is_declared_here(self):
        """``site_searchable_text_index`` is exempt above, so its exemption is
        pinned rather than assumed: it is the deliberate site-search answer,
        and it is bound to every catalog on purpose."""
        exceptions = [
            registration
            for registration in our_indexers()
            if registration.required[1] is not OUR_CATALOG
        ]

        assert [r.factory for r in exceptions] == [site_searchable_text_index]
        assert exceptions[0].name == "SearchableText"
        assert exceptions[0].required[1] is IZCatalog
