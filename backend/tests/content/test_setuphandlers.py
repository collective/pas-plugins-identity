"""Install handlers that can run twice.

Re-importing a GenericSetup profile is routine -- it is how an operator picks
up a new registry record after an upgrade -- so every handler here has to be
idempotent. The interesting failure is not an exception; it is a second
lexicon, or a duplicated metadata column, quietly doubling the size of every
brain.
"""

from . import PROFILE_ID
from pas.plugins.identity.content import container as container_module
from pas.plugins.identity.content import setuphandlers
from pas.plugins.identity.content.catalog import INDEXES
from pas.plugins.identity.content.catalog import METADATA
from pas.plugins.identity.content.catalog import PROFILE_PORTAL_TYPE
from plone import api
from plone.app.dexterity.behaviors.exclfromnav import IExcludeFromNavigation
from plone.dexterity.fti import DexterityFTI

import pytest


pytestmark = pytest.mark.portal(profiles=[PROFILE_ID])


class Context:
    """Stand-in for the setup tool a post handler is called with.

    The handlers here take it and never use it: GenericSetup decides whether
    a profile runs, so there is nothing left for a handler to ask.
    """


class TestIdempotence:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, catalog) -> None:
        self.portal = portal
        self.catalog = catalog

    def test_lexicon_is_not_duplicated(self):
        """A second import must not add a second lexicon."""
        setuphandlers.add_lexicon(self.catalog)

        assert [
            obj_id
            for obj_id in self.catalog.objectIds()
            if obj_id == setuphandlers.LEXICON_ID
        ] == [setuphandlers.LEXICON_ID]

    def test_indexes_are_not_duplicated(self):
        """Indexes are created once."""
        before = sorted(self.catalog.indexes())

        setuphandlers.add_indexes(self.catalog)

        assert sorted(self.catalog.indexes()) == before

    def test_metadata_is_not_duplicated(self):
        """Columns are created once; a duplicate would bloat every brain."""
        before = sorted(self.catalog.schema())

        setuphandlers.add_metadata(self.catalog)

        assert sorted(self.catalog.schema()) == before

    def test_post_install_runs_twice(self):
        """The whole handler, not just its parts."""
        setuphandlers.post_install(Context())

        assert set(self.catalog.indexes()) >= {name for name, _ in INDEXES}
        assert set(self.catalog.schema()) >= set(METADATA)


class TestRebuild:
    """The rebuild is its own profile, so "did somebody ask for it" is
    answered by GenericSetup rather than by a marker file this package used
    to ship and a guard that read it."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, catalog) -> None:
        self.portal = portal
        self.catalog = catalog

    def test_indexes_every_profile_again(self):
        api.content.create(
            container=self.portal["identity-profiles"],
            type=PROFILE_PORTAL_TYPE,
            id="alice",
            userid="alice",
            login="alice@example.com",
        )
        self.catalog.manage_catalogClear()

        setuphandlers.rebuild_catalog(Context())

        assert self.catalog.unrestrictedSearchResults(userid="alice")

    def test_is_registered_as_a_profile(self):
        """The registration is the guard now: a site-wide import step would
        run during every add-on installation in the site, and clearing an
        innocent catalog is not something to leave to a marker file."""
        setup_tool = api.portal.get_tool("portal_setup")
        profile_id = "pas.plugins.identity:rebuild-profile-catalog"

        assert setup_tool.getProfileInfo(profile_id)

    def test_no_import_step_claims_the_rebuild(self):
        """What made the marker file necessary in the first place."""
        setup_tool = api.portal.get_tool("portal_setup")

        assert "pas.plugins.identity.rebuild-profile-catalog" not in (
            setup_tool.getSortedImportSteps()
        )


class TestPostUninstall:
    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal

    def test_leaves_content_alone(self):
        """It logs a decision; it does not delete anybody's data."""
        setuphandlers.post_uninstall(Context())

        assert "identity-profiles" in self.portal.objectIds()


@pytest.fixture
def plain_container_type(portal):
    """Register a container type with none of the standard behaviors.

    A project is free to point ``profile_container_type`` at its own folderish
    type, and that type need not carry ``exclude_from_nav``. Building one here
    is the only way to exercise that path honestly -- every type Plone ships
    has the metadata behaviors.

    :param portal: The Plone site.
    :returns: The portal type name.
    """
    types = api.portal.get_tool("portal_types")
    fti = DexterityFTI("PlainContainer")
    fti.klass = "plone.dexterity.content.Container"
    fti.behaviors = ()
    fti.global_allow = True
    fti.filter_content_types = False
    types._setObject("PlainContainer", fti)
    return "PlainContainer"


class TestContainerTypeWithoutBehaviors:
    def test_created_without_exclude_from_nav(self, plain_container_type):
        """A custom container type is used as-is, not decorated blindly."""
        api.portal.set_registry_record(
            container_module.TYPE_RECORD, plain_container_type
        )
        api.portal.set_registry_record(container_module.ID_RECORD, "people")

        created = container_module.get_container(create=True)

        assert created.portal_type == plain_container_type
        assert not IExcludeFromNavigation.providedBy(created)
