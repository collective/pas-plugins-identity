from Acquisition import aq_base
from contextlib import contextmanager
from OFS.event import ObjectWillBeRemovedEvent
from pas.plugins.identity.core.catalog import all_brains
from pas.plugins.identity.core.catalog import catalog_for
from pas.plugins.identity.core.catalog import query_catalog
from pas.plugins.identity.core.indexers import profile_moved
from pas.plugins.identity.core.indexers import profile_will_be_moved
from plone import api
from zope.component.hooks import getSite
from zope.component.hooks import setSite
from zope.lifecycleevent import modified
from zope.lifecycleevent import ObjectAddedEvent

import pytest


@pytest.fixture
def container(portal):
    """The configured Profile container.

    :param portal: The Plone site.
    :returns: The container.
    """
    return portal["identity-profiles"]


class TestIndexingLifecycle:
    @pytest.fixture(autouse=True)
    def _setup(
        self, portal, catalog, container, make_profile, allow_principals
    ) -> None:
        self.portal = portal
        self.allow_principals = allow_principals
        self.catalog = catalog
        self.container = container
        self.make_profile = make_profile

    def test_create_indexes(self):
        """A new Profile lands in the dedicated self.catalog."""
        self.make_profile("alice")

        brains = self.catalog.unrestrictedSearchResults(userid="alice")

        assert len(brains) == 1

    def test_metadata_is_populated(self):
        """The brain carries the property sheet, so 6b never wakes the object."""
        self.make_profile("alice", fullname="Alice Liddell", email="alice@example.com")

        brain = self.catalog.unrestrictedSearchResults(userid="alice")[0]

        assert brain.fullname == "Alice Liddell"
        assert brain.email == "alice@example.com"
        # Complete rather than incomplete: this profile carries an email, and
        # the completeness subscriber reconciles the state when it is added.
        assert brain.review_state == "complete"

    def test_login_is_folded(self):
        """Login names are case-insensitive; FieldIndex is not."""
        self.make_profile("alice", login="Alice@Example.COM")

        assert self.catalog.unrestrictedSearchResults(login="alice@example.com")
        assert not self.catalog.unrestrictedSearchResults(login="Alice@Example.COM")

    def test_modify_reindexes(self):
        """Editing a field updates the metadata the plugins read."""
        profile = self.make_profile("alice")
        profile.fullname = "Alice Liddell"

        modified(profile)

        brain = self.catalog.unrestrictedSearchResults(userid="alice")[0]
        assert brain.fullname == "Alice Liddell"

    def test_transition_reindexes(self):
        """A transition changes review_state and nothing else notices."""
        profile = self.make_profile("alice")

        api.content.transition(obj=profile, transition="complete")

        brain = self.catalog.unrestrictedSearchResults(userid="alice")[0]
        assert brain.review_state == "complete"

    def test_rename_moves_the_entry(self):
        """A rename must not leave the old path behind."""
        profile = self.make_profile("alice")
        old_path = "/".join(profile.getPhysicalPath())

        api.content.rename(obj=profile, new_id="alice-renamed")

        paths = [b.getPath() for b in all_brains(self.catalog)]
        assert old_path not in paths
        container_path = "/".join(self.container.getPhysicalPath())
        assert paths == [f"{container_path}/alice-renamed"]

    def test_move_out_of_the_container_keeps_it_indexed(self):
        """The catalog is site-wide: reorganising content is not a logout."""
        profile = self.make_profile("alice")
        target = self.allow_principals(
            api.content.create(
                container=self.portal, type="Folder", id="elsewhere", title="Elsewhere"
            )
        )
        api.content.move(source=profile, target=target)

        brains = self.catalog.unrestrictedSearchResults(userid="alice")
        assert len(brains) == 1
        assert brains[0].getPath().endswith("/elsewhere/alice")

    def test_delete_unindexes(self):
        """A deleted Profile leaves no brain behind."""
        profile = self.make_profile("alice")
        api.content.delete(obj=profile)

        assert not self.catalog.unrestrictedSearchResults(userid="alice")


class TestSearchableText:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, catalog, make_profile) -> None:
        self.portal = portal
        self.catalog = catalog
        self.make_profile = make_profile

    def test_covers_name_login_and_email(self):
        """Enough to find a user, and no more."""
        self.make_profile(
            "alice",
            fullname="Alice Liddell",
            email="alice@example.com",
            description="Fond of white rabbits",
        )

        assert self.catalog.unrestrictedSearchResults(SearchableText="Liddell")
        assert not self.catalog.unrestrictedSearchResults(SearchableText="rabbits")


class TestWithNoCurrentSite:
    """The catalog lookup, when nothing has called ``setSite``.

    Two operators reach this and neither is doing anything exotic: a
    ``zconsole`` script that works on ``app`` directly, and deleting a Plone
    site from the Zope root -- which is what ``DELETE_EXISTING=1 make
    create-site`` does, and which failed with a ``CannotGetPortalError``
    naming neither the site nor the catalog as soon as the site held one
    Profile.

    The handlers are called directly rather than through a real deletion.
    Unsetting the current site inside an integration layer takes unrelated
    Plone machinery with it -- the types tool is looked up the same way -- so
    a test that deleted content here would fail for a reason that has nothing
    to do with this one. The end-to-end case is the ``make`` target above.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, portal, catalog, container, make_profile) -> None:
        self.portal = portal
        self.catalog = catalog
        self.container = container
        self.make_profile = make_profile

    @staticmethod
    @contextmanager
    def no_current_site():
        """Unset the current site for the duration of a block.

        A context manager rather than a fixture, because the content each
        test acts on has to be *created* first and creating content needs the
        site the block is about to take away.

        :yields: Nothing; the site is restored afterwards.
        """
        site = getSite()
        setSite(None)
        try:
            yield
        finally:
            setSite(site)

    def test_the_catalog_is_found_through_the_object(self):
        """The fix, at its smallest. ``query_catalog`` cannot answer this and
        is not asked to."""
        profile = self.make_profile("alice")

        with self.no_current_site():
            # ``aq_base`` on both sides: acquisition hands back a fresh
            # wrapper each time, so ``is`` on the wrappers proves nothing.
            assert aq_base(catalog_for(profile)) is aq_base(self.catalog)

    def test_asking_the_current_site_answers_nothing_and_does_not_raise(self):
        """It used to raise, and the exception came out of a subscriber and
        took the whole deletion with it. ``None`` is the right answer to "the
        catalog of no site", and it is now the one given."""
        with self.no_current_site():
            assert query_catalog() is None

    def test_unindexing_still_happens(self):
        """Not raising is only half of it. Answering ``None`` would also not
        raise, and would leave a catalog entry behind for an object that is
        gone -- a finding the consistency check reports and nothing cleans."""
        profile = self.make_profile("alice")
        assert len(self.catalog.unrestrictedSearchResults(userid="alice")) == 1

        with self.no_current_site():
            profile_will_be_moved(
                profile, ObjectWillBeRemovedEvent(profile, self.container, "alice")
            )

        assert not self.catalog.unrestrictedSearchResults(userid="alice")

    def test_indexing_still_happens(self):
        """The other side of the same lookup."""
        profile = self.make_profile("alice")

        with self.no_current_site():
            profile_will_be_moved(
                profile, ObjectWillBeRemovedEvent(profile, self.container, "alice")
            )
            assert not self.catalog.unrestrictedSearchResults(userid="alice")

            profile_moved(profile, ObjectAddedEvent(profile, self.container, "alice"))

        assert len(self.catalog.unrestrictedSearchResults(userid="alice")) == 1

    def test_an_object_outside_a_site_is_not_filed_anywhere(self):
        """``catalog_for`` answers about the object, so an object with no site
        above it has no catalog -- rather than borrowing whichever site the
        thread happens to be in."""
        profile = self.make_profile("alice")

        assert catalog_for(aq_base(profile)) is None
