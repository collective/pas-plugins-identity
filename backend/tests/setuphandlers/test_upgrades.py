"""The upgrade steps, and that a site can actually reach them.

An upgrade step is three things that have to agree: a profile version a site
can be behind, ZCML that GenericSetup has read, and a handler or an import
step that does the work. Any one of them alone is silent -- a step whose
package is never included does not appear in the control panel and does not
run, and nothing reports its absence -- so these assert the registration and
the effect separately.
"""

from pas.plugins.identity.core.catalog import GROUP_PORTAL_TYPE
from plone import api

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
        assert any(
            step.get("dest") == ("1001",)
            for group in upgrades
            for step in (group if isinstance(group, list) else [group])
        )

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

        assert self.setup_tool.getLastVersionForProfile(PROFILE) == ("1001",)
