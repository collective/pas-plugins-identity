"""The layer's code loaded, its profile not applied (§4.9, I5).

Every site running this add-on without the ``profile`` GenericSetup profile is
in this state: the ZCML is loaded, the subscribers are registered, and there is
no catalog. Nothing here may raise -- a core-only site must not pay for an
extra it did not install.

These tests deliberately use the plain ``integration`` layer rather than the
``portal`` fixture of this package, which applies the profile.
"""

from pas.plugins.identity.profile import indexing
from pas.plugins.identity.profile import setuphandlers
from pas.plugins.identity.profile import subscribers
from pas.plugins.identity.profile.catalog import CATALOG_ID
from pas.plugins.identity.profile.catalog import query_catalog
from pas.plugins.identity.profile.pas import IdentityProfilePlugin
from pas.plugins.identity.profile.pas import PLUGIN_ID
from plone import api
from plone.app.testing import TEST_USER_ID

import pytest


@pytest.fixture
def core_portal(integration):
    """A site where the ``[profile]`` profile was never applied.

    :param integration: The integration layer.
    :returns: The Plone site.
    """
    return integration["portal"]


class FakeEvent:
    """Stand-in for a lifecycle event.

    The handlers only ever read ``oldParent`` and ``newParent``; building a
    real event would need a real containment change, which is the thing under
    test rather than a precondition of it.
    """

    def __init__(self, old_parent=None, new_parent=None) -> None:
        """Record the two parents.

        :param old_parent: Where the object was.
        :param new_parent: Where the object is going.
        """
        self.oldParent = old_parent
        self.newParent = new_parent


class TestCatalogLookup:
    def test_no_catalog_in_a_core_site(self, core_portal):
        """The tool simply is not there."""
        assert CATALOG_ID not in core_portal.objectIds()

    def test_query_catalog_answers_none(self, core_portal):
        """ "Not installed here" is an answer, not an exception."""
        assert query_catalog() is None

    def test_get_catalog_still_raises(self, core_portal):
        """Code that requires the layer should hear about it."""
        with pytest.raises(api.exc.InvalidParameterError):
            api.portal.get_tool(CATALOG_ID)


class TestSubscribersAreInert:
    def test_moved_is_a_no_op(self, core_portal):
        """A Profile appearing in a core site indexes nowhere, quietly."""
        indexing.profile_moved(core_portal, FakeEvent(new_parent=core_portal))

    def test_will_be_moved_is_a_no_op(self, core_portal):
        """Same on the way out."""
        indexing.profile_will_be_moved(core_portal, FakeEvent(old_parent=core_portal))

    def test_modified_is_a_no_op(self, core_portal):
        """Same on edit."""
        indexing.profile_modified(core_portal, FakeEvent())


class TestPluginIsInert:
    """The plugin class itself, in a site that never installed the layer.

    It is not registered there, so these instantiate it directly: the point is
    that the code answers "nothing here" rather than raising, which is what a
    misconfigured site -- plugin installed, profile removed -- would hit.
    """

    def test_enumeration_returns_nothing(self, core_portal):
        """No catalog, no users to enumerate."""
        assert IdentityProfilePlugin().enumerateUsers() == ()

    def test_properties_return_none(self, core_portal):
        """And no property sheet to offer."""
        plugin = IdentityProfilePlugin()

        assert (
            plugin.getPropertiesForUser(core_portal.acl_users.getUserById(TEST_USER_ID))
            is None
        )


class TestSubscribersAreInertToo:
    """First login in a core-only site must not go looking for a container."""

    def test_get_profile_answers_none(self, core_portal):
        """Nothing to find, and no exception on the way to finding nothing."""
        assert subscribers.get_profile("alice") is None

    def test_ensure_profile_creates_nothing(self, core_portal):
        """A login in a core-only site must not mint content."""
        assert subscribers.ensure_profile("alice", "alice", {}) is None
        assert "identity-profiles" not in core_portal.objectIds()


class TestUninstallWithoutAPlugin:
    def test_removing_an_absent_plugin_is_a_no_op(self, core_portal):
        """Re-running the uninstall profile must not fail on the second pass."""
        acl_users = api.portal.get_tool("acl_users")

        setuphandlers.uninstall_plugin(acl_users)

        assert PLUGIN_ID not in acl_users.objectIds()


class TestRebuildStep:
    def test_rebuild_without_a_catalog_is_a_no_op(self, core_portal):
        """The import step runs in sites that never installed the layer."""

        class Context:
            """Minimal GenericSetup import context."""

            def readDataFile(self, name: str) -> str:
                """Pretend this package's profile is being imported.

                :param name: Marker file name.
                :returns: Marker content.
                """
                return "marker"

        setuphandlers.rebuild_catalog(Context())
