"""Version 1003: people are ordered by name.

The index half, which no XML can carry. Re-importing ``identity-catalog``
creates the index and leaves it empty, exactly as adding one in Python would.
A site that upgraded and stopped there would have the index, no error, and a
membership listing ordered by whatever the catalog happened to return.
"""

from pas.plugins.identity.core.catalog import PROFILE_PORTAL_TYPE
from plone import api
from unittest.mock import patch

import pytest


class TestOrderedByName:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, catalog, setup_tool, upgrade_from, make_profile) -> None:
        self.catalog = catalog
        self.setup_tool = setup_tool
        self.upgrade_from = upgrade_from
        self.make_profile = make_profile

    def test_the_index_exists_after_the_upgrade(self):
        # Removing it first is what makes this a test of the upgrade rather
        # than of the install: a fresh test site already has the index.
        self.catalog.delIndex("sortable_title")
        assert "sortable_title" not in self.catalog.indexes()

        self.upgrade_from("1002")

        assert "sortable_title" in self.catalog.indexes()

    def test_the_index_is_filled_rather_than_merely_created(self):
        """The whole reason this is a handler and not an ``upgradeDepends``.
        An empty index sorts nothing and reports no error."""
        self.make_profile("zoe", fullname="Zoe Zeta")
        self.make_profile("alice", fullname="Alice Liddell")
        self.catalog.delIndex("sortable_title")

        self.upgrade_from("1002")

        # `userid`, not `getId`: this catalog's columns are declared in
        # `identity-catalog.xml` and `getId` is not among them, so asking for
        # it acquires the catalog's own method and compares a bound method
        # against a string.
        ordered = [
            brain.userid
            for brain in self.catalog.unrestrictedSearchResults(
                portal_type=PROFILE_PORTAL_TYPE, sort_on="sortable_title"
            )
        ]
        assert ordered == ["alice", "zoe"], ordered

    def test_the_site_catalog_entry_is_refreshed(self):
        """The words changed, not the index. A Profile already catalogued in
        `portal_catalog` keeps what the previous indexer wrote until something
        asks again, and nothing does that on its own."""
        self.make_profile("alice", fullname="Alice Liddell")
        site = api.portal.get_tool("portal_catalog")

        # Put the old answer back, which is what an upgraded site really holds.
        brain = site.unrestrictedSearchResults(
            portal_type=PROFILE_PORTAL_TYPE, userid="alice"
        )[0]
        site._catalog.indexes["SearchableText"].unindex_object(brain.getRID())
        assert not site.unrestrictedSearchResults(SearchableText="Liddell")

        self.upgrade_from("1002")

        assert site.unrestrictedSearchResults(SearchableText="Liddell")

    def test_a_missing_index_after_the_import_is_loud(self):
        """A reindex against an index that was never created succeeds and does
        nothing, so the step refuses rather than reporting success."""
        from pas.plugins.identity.upgrades.v1003 import add_sortable_title

        self.catalog.delIndex("sortable_title")
        with (
            patch.object(
                self.setup_tool, "runImportStepFromProfile", return_value=None
            ),
            pytest.raises(ValueError, match="still missing"),
        ):
            add_sortable_title(self.setup_tool)
