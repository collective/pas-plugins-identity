from pas.plugins.identity.profile.catalog import all_brains
from pas.plugins.identity.profile.catalog import PROFILE_PORTAL_TYPE
from plone import api
from zope.lifecycleevent import modified

import pytest


@pytest.fixture
def container(portal):
    """The configured Profile container.

    :param portal: The Plone site.
    :returns: The container.
    """
    return portal["identity-profiles"]


@pytest.fixture
def make_profile(container):
    """Return a factory for Profiles in the configured container.

    :param container: The Profile container.
    :returns: Callable taking a userid and extra field values.
    """

    def factory(userid: str, **kwargs) -> object:
        with api.env.adopt_roles(["Manager"]):
            return api.content.create(
                container=container,
                type=PROFILE_PORTAL_TYPE,
                id=userid,
                userid=userid,
                login=kwargs.pop("login", userid),
                **kwargs,
            )

    return factory


class TestIndexingLifecycle:
    def test_create_indexes(self, catalog, make_profile):
        """A new Profile lands in the dedicated catalog."""
        make_profile("alice")

        brains = catalog.unrestrictedSearchResults(userid="alice")

        assert len(brains) == 1

    def test_metadata_is_populated(self, catalog, make_profile):
        """The brain carries the property sheet, so 6b never wakes the object."""
        make_profile("alice", fullname="Alice Liddell", email="alice@example.com")

        brain = catalog.unrestrictedSearchResults(userid="alice")[0]

        assert brain.fullname == "Alice Liddell"
        assert brain.email == "alice@example.com"
        assert brain.review_state == "incomplete"

    def test_login_is_folded(self, catalog, make_profile):
        """Login names are case-insensitive; FieldIndex is not."""
        make_profile("alice", login="Alice@Example.COM")

        assert catalog.unrestrictedSearchResults(login="alice@example.com")
        assert not catalog.unrestrictedSearchResults(login="Alice@Example.COM")

    def test_modify_reindexes(self, catalog, make_profile):
        """Editing a field updates the metadata the plugins read."""
        profile = make_profile("alice")
        profile.fullname = "Alice Liddell"

        modified(profile)

        brain = catalog.unrestrictedSearchResults(userid="alice")[0]
        assert brain.fullname == "Alice Liddell"

    def test_transition_reindexes(self, catalog, make_profile):
        """A transition changes review_state and nothing else notices."""
        profile = make_profile("alice")

        with api.env.adopt_roles(["Manager"]):
            api.content.transition(obj=profile, transition="complete")

        brain = catalog.unrestrictedSearchResults(userid="alice")[0]
        assert brain.review_state == "complete"

    def test_rename_moves_the_entry(self, catalog, make_profile, container):
        """A rename must not leave the old path behind."""
        profile = make_profile("alice")
        old_path = "/".join(profile.getPhysicalPath())

        with api.env.adopt_roles(["Manager"]):
            api.content.rename(obj=profile, new_id="alice-renamed")

        paths = [b.getPath() for b in all_brains(catalog)]
        assert old_path not in paths
        container_path = "/".join(container.getPhysicalPath())
        assert paths == [f"{container_path}/alice-renamed"]

    def test_move_out_of_the_container_keeps_it_indexed(
        self, catalog, portal, make_profile
    ):
        """The catalog is site-wide: reorganising content is not a logout."""
        profile = make_profile("alice")
        with api.env.adopt_roles(["Manager"]):
            target = api.content.create(
                container=portal, type="Folder", id="elsewhere", title="Elsewhere"
            )
            api.content.move(source=profile, target=target)

        brains = catalog.unrestrictedSearchResults(userid="alice")
        assert len(brains) == 1
        assert brains[0].getPath().endswith("/elsewhere/alice")

    def test_delete_unindexes(self, catalog, make_profile):
        """A deleted Profile leaves no brain behind."""
        profile = make_profile("alice")
        with api.env.adopt_roles(["Manager"]):
            api.content.delete(obj=profile)

        assert not catalog.unrestrictedSearchResults(userid="alice")


class TestSearchableText:
    def test_covers_name_login_and_email(self, catalog, make_profile):
        """Enough to find a user, and no more (§4.7)."""
        make_profile(
            "alice",
            fullname="Alice Liddell",
            email="alice@example.com",
            description="Fond of white rabbits",
        )

        assert catalog.unrestrictedSearchResults(SearchableText="Liddell")
        assert not catalog.unrestrictedSearchResults(SearchableText="rabbits")
