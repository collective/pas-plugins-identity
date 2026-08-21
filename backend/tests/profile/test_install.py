from pas.plugins.identity.profile.catalog import CATALOG_ID
from pas.plugins.identity.profile.catalog import INDEXES
from pas.plugins.identity.profile.catalog import METADATA
from pas.plugins.identity.profile.catalog import PROFILE_PORTAL_TYPE
from plone import api


class TestProfileInstall:
    def test_catalog_tool_present(self, catalog):
        """The dedicated catalog is added by toolset.xml."""
        assert catalog.getId() == CATALOG_ID

    def test_indexes_created(self, catalog):
        """Every declared index exists; GenericSetup cannot do this for us."""
        assert set(catalog.indexes()) >= {name for name, _ in INDEXES}

    def test_metadata_created(self, catalog):
        """Brains carry the whole property sheet (C6)."""
        assert set(catalog.schema()) >= set(METADATA)

    def test_type_registered(self, portal):
        """The Profile FTI is installed."""
        types = api.portal.get_tool("portal_types")
        assert PROFILE_PORTAL_TYPE in types.objectIds()

    def test_workflow_bound(self, portal):
        """Profiles get the three-state workflow."""
        workflows = api.portal.get_tool("portal_workflow")
        chain = workflows.getChainForPortalType(PROFILE_PORTAL_TYPE)
        assert chain == ("identity_profile_workflow",)

    def test_container_created(self, portal):
        """Install creates the configured container."""
        assert "identity-profiles" in portal.objectIds()
