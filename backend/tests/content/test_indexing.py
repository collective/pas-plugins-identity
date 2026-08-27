from . import PROFILE_ID
from pas.plugins.identity.content.catalog import all_brains
from plone import api
from zope.lifecycleevent import modified

import pytest


pytestmark = pytest.mark.portal(profiles=[PROFILE_ID])


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
        assert brain.review_state == "incomplete"

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
