from . import PROFILE_ID
from pas.plugins.identity.content.catalog import CATALOG_ID
from pas.plugins.identity.content.catalog import INDEXES
from pas.plugins.identity.content.catalog import METADATA
from pas.plugins.identity.content.catalog import PROFILE_PORTAL_TYPE
from pas.plugins.identity.content.interfaces import IProfileSettings
from plone import api
from zope.schema import getFieldNames

import pytest


pytestmark = pytest.mark.portal(profiles=[PROFILE_ID])


class TestProfileInstall:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, catalog) -> None:
        self.portal = portal
        self.catalog = catalog

    def test_catalog_tool_present(self):
        """The dedicated self.catalog is added by toolset.xml."""
        assert self.catalog.getId() == CATALOG_ID

    def test_indexes_created(self):
        """Every declared index exists; GenericSetup cannot do this for us."""
        assert set(self.catalog.indexes()) >= {name for name, _ in INDEXES}

    def test_metadata_created(self):
        """Brains carry the whole property sheet."""
        assert set(self.catalog.schema()) >= set(METADATA)

    def test_type_registered(self):
        """The Profile FTI is installed."""
        types = api.portal.get_tool("portal_types")
        assert PROFILE_PORTAL_TYPE in types.objectIds()

    def test_workflow_bound(self):
        """Profiles get the three-state workflow."""
        workflows = api.portal.get_tool("portal_workflow")
        chain = workflows.getChainForPortalType(PROFILE_PORTAL_TYPE)
        assert chain == ("identity_profile_workflow",)

    @pytest.mark.no_profile_container
    def test_container_not_created(self):
        """Install deliberately leaves it to first login, or to an operator
        who knows where they want it. See ``post_install``."""
        assert "identity-profiles" not in self.portal.objectIds()


class TestProfileSettings:
    """The profile imports its settings schema, so the two cannot drift."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal) -> None:
        self.portal = portal

    @pytest.mark.parametrize("name", getFieldNames(IProfileSettings))
    def test_record_exists(self, name: str):
        """Every field in the schema is a record the profile created."""
        record = f"pas.plugins.identity.{name}"

        assert api.portal.get_registry_record(record, default=None) is not None

    @pytest.mark.parametrize(
        "name,expected",
        [
            ("profile_container_parent", ""),
            ("profile_container_id", "identity-profiles"),
            ("profile_container_title", "Identity Profiles"),
            ("profile_container_type", "Folder"),
            ("profile_enumeration_states", ("incomplete", "complete")),
            ("group_enumeration_states", ("active",)),
        ],
    )
    def test_default_value(self, name: str, expected):
        """The shipped defaults. Portraits being off is the load-bearing one:
        no site should acquire a server-side fetch by upgrading."""
        assert (
            api.portal.get_registry_record(f"pas.plugins.identity.{name}") == expected
        )
