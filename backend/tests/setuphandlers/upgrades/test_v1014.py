"""Version 1014: ``default`` split into ``core`` and ``contenttypes``.

Driven against the state a site installed before the split is in: everything
both profiles install is there, GenericSetup has no record of either, and the
site carries no marker.
"""

from . import PROFILE
from pas.plugins.identity import PACKAGE_NAME
from pas.plugins.identity.core.interfaces import IUsersAsContent
from pas.plugins.identity.core.pas import EXTRACTOR
from pas.plugins.identity.core.pas import PLUGIN_ID
from pas.plugins.identity.upgrades.v1014 import record_layer_profiles
from plone import api
from Products.GenericSetup.tool import UNKNOWN
from zope.interface import noLongerProvides

import pytest


LAYERS = (f"{PACKAGE_NAME}:core", f"{PACKAGE_NAME}:contenttypes")


@pytest.fixture
def before_the_split(portal, setup_tool):
    """Put the site back where a 1013 site is.

    :param portal: The Plone site.
    :param setup_tool: ``portal_setup``.
    :returns: The Plone site.
    """
    for profile_id in LAYERS:
        setup_tool.unsetLastVersionForProfile(profile_id)
    noLongerProvides(portal, IUsersAsContent)
    assert setup_tool.getLastVersionForProfile(LAYERS[0]) == UNKNOWN
    return portal


class TestTheLayersAreRecorded:
    @pytest.fixture(autouse=True)
    def _setup(self, before_the_split, setup_tool, upgrade_from) -> None:
        self.portal = before_the_split
        self.setup = setup_tool
        api.portal.set_registry_record("pas.plugins.identity.audit_max_days", 7)
        upgrade_from("1013")

    @pytest.mark.parametrize("profile_id", LAYERS)
    def test_the_profile_is_installed(self, profile_id: str):
        """At its own version, read from its own metadata."""
        assert self.setup.getLastVersionForProfile(profile_id) == ("1000",)

    def test_the_site_is_marked(self):
        assert IUsersAsContent.providedBy(self.portal)

    def test_nothing_was_reimported(self):
        """A step that re-imported the profiles would put every shipped value
        back over what the site chose; this one only records."""
        assert (
            api.portal.get_registry_record("pas.plugins.identity.audit_max_days") == 7
        )


class TestAKnownVersionIsKept:
    """A site that already knows one of the two keeps that version."""

    @pytest.fixture(autouse=True)
    def _setup(self, before_the_split, setup_tool, upgrade_from) -> None:
        self.setup = setup_tool
        setup_tool.setLastVersionForProfile(LAYERS[0], "1007")
        upgrade_from("1013")

    def test_the_known_version_stays(self):
        assert self.setup.getLastVersionForProfile(LAYERS[0]) == ("1007",)

    def test_the_unknown_one_is_recorded(self):
        assert self.setup.getLastVersionForProfile(LAYERS[1]) == ("1000",)


#: Every version a site could be at before the split.
PUBLISHED = [str(version) for version in range(1000, 1014)]


class TestFromEveryPublishedVersion:
    """A site is upgraded from wherever it was, not from 1013 only.

    The whole chain runs, and every earlier step that imports a part of the
    old ``default`` profile now imports it from the layer that owns it. A
    step pointing at a file that moved fails here, for the version that
    still runs it.
    """

    @pytest.mark.parametrize("version", PUBLISHED)
    def test_the_site_lands_on_the_split(
        self, version, before_the_split, setup_tool, upgrade_from
    ):
        upgrade_from(version)

        assert setup_tool.getLastVersionForProfile(PROFILE) == ("1014",)
        assert [setup_tool.getLastVersionForProfile(p) for p in LAYERS] == [
            ("1000",),
            ("1000",),
        ]
        assert IUsersAsContent.providedBy(before_the_split)


class TestAfterTheUpgrade:
    """What an operator sees, and what a returning user gets."""

    @pytest.fixture(autouse=True)
    def _setup(self, before_the_split, setup_tool, upgrade_from) -> None:
        self.portal = before_the_split
        self.setup = setup_tool
        upgrade_from("1013")

    def test_the_add_ons_panel_has_nothing_to_do(self, installer):
        info = installer.upgrade_info(PACKAGE_NAME)

        assert installer.is_product_installed(PACKAGE_NAME)
        assert not info["available"]

    @pytest.mark.parametrize("profile_id", LAYERS)
    def test_no_layer_has_an_upgrade_pending(self, profile_id: str):
        assert self.setup.listUpgrades(profile_id) == []

    def test_running_the_step_again_changes_nothing(self):
        record_layer_profiles(self.setup)

        assert [self.setup.getLastVersionForProfile(p) for p in LAYERS] == [
            ("1000",),
            ("1000",),
        ]
        assert IUsersAsContent.providedBy(self.portal)

    def test_a_returning_user_is_still_a_profile(self, make_profile):
        """The marker is what tells a login which way to go. Without it, a
        returning user of one of these sites would be given a
        ``source_users`` row beside their Profile."""
        acl_users = api.portal.get_tool("acl_users")
        plugin = acl_users[PLUGIN_ID]
        make_profile("ericof", "Érico Andrei")
        plugin.link("ericof", "dex", "subject-1", {"email": "erico@plone.org"})

        result = plugin.authenticateCredentials({
            "extractor": EXTRACTOR,
            "provider": "dex",
            "subject": "subject-1",
            "claims": {"email": "erico@plone.org", "fullname": "Érico Andrei"},
        })

        assert result == ("ericof", "ericof")
        assert "ericof" not in acl_users.source_users.getUserIds()
        assert "ericof" not in plugin.placeholder_passwords
