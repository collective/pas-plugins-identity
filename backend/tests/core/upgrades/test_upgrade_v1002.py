"""Version 1002 reaches the Profiles a site already has.

Here rather than in ``tests/setuphandlers`` because it needs a Profile, and a
Profile needs the container -- which the setuphandlers layer's bare site has no
addable folderish type for. The registration half of this step lives there;
this is the effect half.

The step exists because a workflow import does not touch existing content.
``Products.CMFCore.exportimport.workflow.importWorkflowTool`` never calls
``updateRoleMappings``, so every Profile a site already has keeps the
permission map it was last transitioned with, and the new permission is
unmanaged on all of them. Unmanaged is not "nobody holds it": it is "acquired
from the container", which is the one place this package deliberately grants
it to Site Administrator as well.

Without the handler the upgrade would read as applied and change nothing,
which is why ``test_the_state_a_pre_upgrade_site_is_in`` asserts the premise
before the rest assert the cure.
"""

from AccessControl import getSecurityManager
from pas.plugins.identity.core.catalog import PROFILE_PORTAL_TYPE
from plone import api

import pytest


#: The profile the step belongs to.
PROFILE = "pas.plugins.identity:default"

#: The permission version 1002 introduces.
EDIT_LOGIN = "pas.plugins.identity: Edit Profile Login"


class TestV1002RestrictsTheLogin:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, acl_users) -> None:
        self.portal = portal
        self.setup_tool = api.portal.get_tool("portal_setup")
        acl_users.source_users.addUser("boss", "boss", "placeholder-password")
        api.user.grant_roles(username="boss", roles=["Site Administrator"])
        self.profile = api.content.create(
            container=portal["identity-profiles"],
            type=PROFILE_PORTAL_TYPE,
            id="alice",
            userid="alice",
            login="alice@example.com",
            fullname="Alice Liddell",
            emails=("alice@example.com",),
        )

    def _may(self, userid: str) -> bool:
        """Report whether a user may write the login on the profile.

        :param userid: The user to check as.
        :returns: Whether the permission is held.
        """
        with api.env.adopt_user(username=userid):
            return bool(getSecurityManager().checkPermission(EDIT_LOGIN, self.profile))

    def _unmanage(self) -> None:
        """Put the permission back the way a pre-1002 site has it."""
        self.profile.manage_permission(EDIT_LOGIN, roles=[], acquire=1)

    def _upgrade(self) -> None:
        """Run the profile's upgrade steps from 1001."""
        self.setup_tool.setLastVersionForProfile(PROFILE, "1001")
        self.setup_tool.upgradeProfile(PROFILE)

    def test_the_state_a_pre_upgrade_site_is_in(self):
        """The premise. If an acquired permission did not reach a Site
        Administrator, the two tests below would pass without the handler."""
        self._unmanage()

        assert self._may("boss") is True

    def test_the_upgrade_takes_it_away(self):
        self._unmanage()

        self._upgrade()

        assert self._may("boss") is False

    def test_and_leaves_it_with_a_manager(self):
        """The other half: a login nobody may change is a login nobody may
        correct."""
        self._unmanage()
        api.user.create(
            email="root@example.com",
            username="root",
            password="root-placeholder-password",
            roles=("Manager",),
        )

        self._upgrade()

        assert self._may("root") is True
