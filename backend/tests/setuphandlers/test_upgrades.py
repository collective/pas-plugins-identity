"""The upgrade steps, and that a site can actually reach them.

An upgrade step is three things that have to agree: a profile version a site
can be behind, ZCML that GenericSetup has read, and a handler or an import
step that does the work. Any one of them alone is silent -- a step whose
package is never included does not appear in the control panel and does not
run, and nothing reports its absence -- so these assert the registration and
the effect separately.
"""

from pas.plugins.identity.core.catalog import GROUP_PORTAL_TYPE
from pas.plugins.identity.core.catalog import PROFILE_PORTAL_TYPE
from pas.plugins.identity.core.catalog import query_catalog
from plone import api
from unittest.mock import patch

import pytest


#: The profile every version here belongs to.
PROFILE = "pas.plugins.identity:default"


@pytest.fixture
def setup_tool(portal):
    """Return the setup tool.

    :param portal: The Plone site.
    :returns: ``portal_setup``.
    """
    return api.portal.get_tool("portal_setup")


class TestTheStepIsRegistered:
    """That GenericSetup knows about it at all.

    Registration is the half the effect cannot prove. ``upgrades`` is included
    from ``profiles.zcml`` and has been all along, but each version package
    under it has to be included in turn -- and a version left out of
    ``upgrades/configure.zcml`` is a step that does not appear in the control
    panel, does not run, and is reported by nothing.
    """

    def test_a_site_at_1000_is_offered_the_step(self, setup_tool):
        """The question the add-ons control panel asks."""
        setup_tool.setLastVersionForProfile(PROFILE, "1000")

        upgrades = setup_tool.listUpgrades(PROFILE)

        assert upgrades, "No upgrade offered to a site at 1000"
        dests = {
            step.get("dest")
            for group in upgrades
            for step in (group if isinstance(group, list) else [group])
        }
        # Every version, not merely the first: a package left out of
        # ``upgrades/configure.zcml`` drops out of exactly this list.
        assert {
            ("1001",),
            ("1002",),
            ("1003",),
            ("1004",),
            ("1005",),
            ("1006",),
            ("1007",),
        } <= dests, dests

    def test_a_site_at_the_latest_version_is_offered_nothing(self, setup_tool):
        """The other half: an upgrade that keeps being offered after it has
        run is one nobody can tell has run."""
        assert setup_tool.listUpgrades(PROFILE) == []


class TestTheStepDoesTheWork:
    """That running it leaves the FTI able to hold a group.

    The reason the step exists: an FTI is a persistent object written at
    install, so a site installed before containment keeps an empty
    ``allowed_content_types`` and offers nothing in the add menu inside a
    group, with nothing to say why.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, portal, setup_tool) -> None:
        self.portal = portal
        self.setup_tool = setup_tool
        self.types = api.portal.get_tool("portal_types")

    def test_the_fti_allows_a_group_inside_a_group(self):
        """The state a site has to end up in."""
        fti = self.types[GROUP_PORTAL_TYPE]

        assert fti.allowed_content_types == (GROUP_PORTAL_TYPE,)
        assert fti.filter_content_types is True

    def test_the_upgrade_restores_it_on_a_site_that_lost_it(self):
        """The upgrade, driven against exactly the state it exists for: the
        FTI a site installed before containment actually has."""
        fti = self.types[GROUP_PORTAL_TYPE]
        fti.allowed_content_types = ()
        assert fti.allowed_content_types == ()

        self.setup_tool.setLastVersionForProfile(PROFILE, "1000")
        self.setup_tool.upgradeProfile(PROFILE)

        assert self.types[GROUP_PORTAL_TYPE].allowed_content_types == (
            GROUP_PORTAL_TYPE,
        )

    def test_the_upgrade_moves_the_version_forward(self):
        """A step that does the work and leaves the version behind runs again
        on every restart of the control panel."""
        self.setup_tool.setLastVersionForProfile(PROFILE, "1000")

        self.setup_tool.upgradeProfile(PROFILE)

        assert self.setup_tool.getLastVersionForProfile(PROFILE) == ("1007",)


class TestV1002PutsTheFieldsOnBehaviors:
    """The FTI half, which ``typeinfo`` carries.

    An FTI is a persistent object written at install, so a site installed
    before this keeps the old behaviors list: the email tab would not exist
    and the fields that moved would be missing from the form rather than
    relocated.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, portal, setup_tool) -> None:
        self.portal = portal
        self.setup_tool = setup_tool
        self.types = api.portal.get_tool("portal_types")

    def test_the_upgrade_restores_them_on_a_site_that_lacks_them(self):
        fti = self.types["UserProfile"]
        fti.behaviors = ("plone.shortname", "plone.versioning")

        self.setup_tool.setLastVersionForProfile(PROFILE, "1001")
        self.setup_tool.upgradeProfile(PROFILE)

        behaviors = self.types["UserProfile"].behaviors
        assert "pas.plugins.identity.email_addresses" in behaviors
        assert "pas.plugins.identity.profile_details" in behaviors


class TestV1003OrdersPeopleByName:
    """The index half, which no XML can carry.

    Re-importing ``identity-catalog`` creates the index and leaves it empty,
    exactly as adding one in Python would. A site that upgraded and stopped
    there would have the index, no error, and a membership listing ordered by
    whatever the catalog happened to return.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, portal, setup_tool, container) -> None:
        self.portal = portal
        self.setup_tool = setup_tool
        self.container = container
        self.catalog = query_catalog()

    def make_profile(self, userid: str, fullname: str) -> object:
        """Create one Profile in the configured container.

        Inline rather than through the ``make_profile`` fixture, which lives in
        ``tests/core/conftest.py`` and is not visible here. Widening its scope
        to reach this module would change every test under ``tests/core`` to
        make one upgrade test shorter. The container comes from this suite's
        own fixture, which creates it the way a first login does.

        :param userid: The userid, which is also the object id.
        :param fullname: The name the Profile is titled and sorted by.
        :returns: The Profile.
        """
        # Elevated: adding a Profile is held to a permission of its own, and
        # this suite starts from a site that has only been installed.
        with api.env.adopt_roles(["Manager"]):
            return api.content.create(
                container=self.container,
                type=PROFILE_PORTAL_TYPE,
                id=userid,
                userid=userid,
                login=f"{userid}@example.com",
                fullname=fullname,
            )

    def _upgrade_from(self, version: str) -> None:
        """Run the upgrade machinery as a site at ``version`` would.

        :param version: The profile version the site is pretending to be at.
        """
        self.setup_tool.setLastVersionForProfile(PROFILE, version)
        self.setup_tool.upgradeProfile(PROFILE)

    def test_the_index_exists_after_the_upgrade(self):
        # Removing it first is what makes this a test of the upgrade rather
        # than of the install: a fresh test site already has the index.
        self.catalog.delIndex("sortable_title")
        assert "sortable_title" not in self.catalog.indexes()

        self._upgrade_from("1002")

        assert "sortable_title" in self.catalog.indexes()

    def test_the_index_is_filled_rather_than_merely_created(self):
        """The whole reason this is a handler and not an ``upgradeDepends``.
        An empty index sorts nothing and reports no error."""
        self.make_profile("zoe", fullname="Zoe Zeta")
        self.make_profile("alice", fullname="Alice Liddell")
        self.catalog.delIndex("sortable_title")

        self._upgrade_from("1002")

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

        self._upgrade_from("1002")

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
