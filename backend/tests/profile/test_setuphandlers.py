"""Install handlers that can run twice (§4.9).

Re-importing a GenericSetup profile is routine -- it is how an operator picks
up a new registry record after an upgrade -- so every handler here has to be
idempotent. The interesting failure is not an exception; it is a second
lexicon, or a duplicated metadata column, quietly doubling the size of every
brain.
"""

from pas.plugins.identity.profile import container as container_module
from pas.plugins.identity.profile import setuphandlers
from pas.plugins.identity.profile.catalog import INDEXES
from pas.plugins.identity.profile.catalog import METADATA
from pas.plugins.identity.profile.catalog import PROFILE_PORTAL_TYPE
from plone import api
from plone.app.dexterity.behaviors.exclfromnav import IExcludeFromNavigation
from plone.dexterity.fti import DexterityFTI

import pytest


class Context:
    """Minimal GenericSetup import context.

    :param marker: What ``readDataFile`` should return; ``None`` means the
        profile being imported is somebody else's.
    """

    def __init__(self, marker: str | None = "marker") -> None:
        """Store the marker.

        :param marker: Marker file content, or ``None``.
        """
        self.marker = marker

    def readDataFile(self, name: str) -> str | None:
        """Return the marker.

        :param name: Marker file name.
        :returns: The configured marker.
        """
        return self.marker


class TestIdempotence:
    def test_lexicon_is_not_duplicated(self, catalog):
        """A second import must not add a second lexicon."""
        setuphandlers.add_lexicon(catalog)

        assert [
            obj_id
            for obj_id in catalog.objectIds()
            if obj_id == setuphandlers.LEXICON_ID
        ] == [setuphandlers.LEXICON_ID]

    def test_indexes_are_not_duplicated(self, catalog):
        """Indexes are created once."""
        before = sorted(catalog.indexes())

        setuphandlers.add_indexes(catalog)

        assert sorted(catalog.indexes()) == before

    def test_metadata_is_not_duplicated(self, catalog):
        """Columns are created once; a duplicate would bloat every brain."""
        before = sorted(catalog.schema())

        setuphandlers.add_metadata(catalog)

        assert sorted(catalog.schema()) == before

    def test_post_install_runs_twice(self, portal, catalog):
        """The whole handler, not just its parts."""
        setuphandlers.post_install(Context())

        assert set(catalog.indexes()) >= {name for name, _ in INDEXES}
        assert set(catalog.schema()) >= set(METADATA)


class TestRebuildGuard:
    def test_runs_for_our_profile(self, portal, catalog):
        """With the marker present, the rebuild happens."""
        with api.env.adopt_roles(["Manager"]):
            api.content.create(
                container=portal["identity-profiles"],
                type=PROFILE_PORTAL_TYPE,
                id="alice",
                userid="alice",
                login="alice@example.com",
            )
        catalog.manage_catalogClear()

        setuphandlers.rebuild_catalog(Context())

        assert catalog.unrestrictedSearchResults(userid="alice")

    def test_skipped_for_another_profile(self, portal, catalog):
        """Installing an unrelated add-on must not touch this catalog."""
        with api.env.adopt_roles(["Manager"]):
            api.content.create(
                container=portal["identity-profiles"],
                type=PROFILE_PORTAL_TYPE,
                id="alice",
                userid="alice",
                login="alice@example.com",
            )
        catalog.manage_catalogClear()

        setuphandlers.rebuild_catalog(Context(marker=None))

        assert not catalog.unrestrictedSearchResults(userid="alice")


class TestPostUninstall:
    def test_leaves_content_alone(self, portal):
        """It logs a decision; it does not delete anybody's data."""
        setuphandlers.post_uninstall(Context())

        assert "identity-profiles" in portal.objectIds()


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
    def test_created_without_exclude_from_nav(self, portal, plain_container_type):
        """A custom container type is used as-is, not decorated blindly."""
        api.portal.set_registry_record(
            container_module.TYPE_RECORD, plain_container_type
        )
        api.portal.set_registry_record(container_module.ID_RECORD, "people")

        with api.env.adopt_roles(["Manager"]):
            created = container_module.get_container(create=True)

        assert created.portal_type == plain_container_type
        assert not IExcludeFromNavigation.providedBy(created)
