"""That GenericSetup knows about every step, and moves a site forward.

Registration is the half the effect cannot prove. ``upgrades`` is included
from ``profiles.zcml`` and has been all along, but each version package under
it has to be included in turn -- and a version left out of
``upgrades/configure.zcml`` is a step that does not appear in the control
panel, does not run, and is reported by nothing.
"""

from . import PROFILE


#: The version a site ends at once every step has run.
LATEST = "1009"


class TestTheStepsAreRegistered:
    def test_a_site_at_1000_is_offered_every_step(self, setup_tool):
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
        assert {(f"{version}",) for version in range(1001, int(LATEST) + 1)} <= dests, (
            dests
        )

    def test_a_site_at_the_latest_version_is_offered_nothing(self, setup_tool):
        """The other half: an upgrade that keeps being offered after it has
        run is one nobody can tell has run."""
        assert setup_tool.listUpgrades(PROFILE) == []


class TestTheVersionMovesForward:
    def test_the_upgrade_ends_at_the_latest_version(self, setup_tool, upgrade_from):
        """A step that does the work and leaves the version behind runs again
        on every restart of the control panel."""
        upgrade_from("1000")

        assert setup_tool.getLastVersionForProfile(PROFILE) == (LATEST,)
