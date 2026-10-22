"""Version 1011 reaches the Profiles a site already has.

The login and group membership of a Profile moved behind ``View Account
Details``. A workflow import does not touch existing content, so every Profile
a site already has keeps the permission map it was last transitioned with, and
the new permission is unmanaged on all of them. Unmanaged is not "nobody
holds it": it is "acquired from the container", which here is the site's
rolemap, so the owner of a Profile would not hold it until the upgrade maps it.

``test_the_state_a_pre_upgrade_site_is_in`` asserts that premise before the
rest assert the cure, so a step that did nothing would not pass by accident.
"""

from AccessControl import getSecurityManager
from pas.plugins.identity.core.catalog import PROFILE_PORTAL_TYPE
from plone import api

import pytest


#: The profile the step belongs to.
PROFILE = "pas.plugins.identity:default"

#: The permission version 1011 introduces.
VIEW_ACCOUNT = "pas.plugins.identity: View Account Details"


class TestV1011GuardsTheAccountDetails:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, acl_users) -> None:
        self.setup_tool = api.portal.get_tool("portal_setup")
        acl_users.source_users.addUser("boss", "boss", "placeholder-password")
        api.user.grant_roles(username="boss", roles=["Site Administrator"])
        acl_users.source_users.addUser("alice", "alice", "placeholder-password")
        api.user.grant_roles(username="alice", roles=["Member"])
        acl_users.source_users.addUser("bob", "bob", "placeholder-password")
        api.user.grant_roles(username="bob", roles=["Member"])
        self.profile = api.content.create(
            container=portal["identity-profiles"],
            type=PROFILE_PORTAL_TYPE,
            id="alice",
            userid="alice",
            login="alice@example.com",
            fullname="Alice Liddell",
        )

    def _may(self, userid: str) -> bool:
        """Report whether a user may read the account details of the profile.

        :param userid: The user to check as.
        :returns: Whether the permission is held.
        """
        with api.env.adopt_user(username=userid):
            return bool(
                getSecurityManager().checkPermission(VIEW_ACCOUNT, self.profile)
            )

    def _unmanage(self) -> None:
        """Put the permission back the way a pre-1011 site has it."""
        self.profile.manage_permission(VIEW_ACCOUNT, roles=[], acquire=1)

    def _upgrade(self) -> None:
        """Run the profile's upgrade steps from 1010."""
        self.setup_tool.setLastVersionForProfile(PROFILE, "1010")
        self.setup_tool.upgradeProfile(PROFILE)

    def test_the_state_a_pre_upgrade_site_is_in(self):
        """The premise. Unmanaged, the permission acquires the site rolemap:
        Site Administrator holds it and the owner does not. If that were not
        so, the owner assertion below would pass without the handler."""
        self._unmanage()

        assert self._may("boss") is True
        assert self._may("alice") is False

    def test_the_owner_may_read_their_own_login_after_the_upgrade(self):
        self._unmanage()

        self._upgrade()

        assert self._may("alice") is True

    def test_and_site_administrators_keep_it(self):
        self._unmanage()

        self._upgrade()

        assert self._may("boss") is True

    def test_and_a_member_still_may_not_in_an_incomplete_profile(self):
        """The upgrade maps the roles the workflow names. It does not open
        the login to every signed-in user of an incomplete Profile."""
        self._unmanage()

        self._upgrade()

        assert self._may("bob") is False
